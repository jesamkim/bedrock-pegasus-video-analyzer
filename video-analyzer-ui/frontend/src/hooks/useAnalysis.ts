import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { analysisApi, uploadApi } from '../services/api';
import type { AnalysisMode, AnalysisStatus, AnalysisResult, BasicPrompts, UploadProgress, AnalysisProgress, EncodingProgress, VideoSource } from '../types';

export const useAnalysis = () => {
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('idle');
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [encodingProgress, setEncodingProgress] = useState<EncodingProgress | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress | null>(null);
  const [currentResult, setCurrentResult] = useState<AnalysisResult | null>(null);

  // 파일 업로드 뮤테이션 (분석 시작 시에만 실행)
  const uploadMutation = useMutation({
    mutationFn: (file: File) => 
      uploadApi.uploadVideo(file, (progressEvent) => {
        if (progressEvent.total) {
          const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress({
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage,
          });
        }
      }),
    onMutate: () => {
      console.log('📤 Starting file upload...');
      setUploadProgress({ loaded: 0, total: 0, percentage: 0 });
    },
    onSuccess: (response) => {
      console.log('📤 Upload completed:', response);
      setUploadProgress(null);
      
      // 업로드 완료 후 인코딩이 필요한 경우 인코딩 상태로 전환
      if (response.data?.needs_encoding) {
        setAnalysisStatus('encoding');
        startEncodingProgressPolling(response.data.fileId);
      } else {
        // 인코딩이 필요없으면 바로 분석 시작 가능
        console.log('✅ File ready for analysis (no encoding needed)');
        return response; // 분석 함수에서 사용할 수 있도록 반환
      }
    },
    onError: (error) => {
      console.error('❌ Upload failed:', error);
      setAnalysisStatus('error');
      setUploadProgress(null);
    },
  });

  // S3 URI 검증 뮤테이션
  const s3UriMutation = useMutation({
    mutationFn: (s3Uri: string) => uploadApi.validateS3Uri(s3Uri),
    onMutate: () => {
      setAnalysisStatus('uploading');
    },
    onSuccess: () => {
      setAnalysisStatus('idle');
    },
    onError: () => {
      setAnalysisStatus('error');
    },
  });

  // 기본 분석 뮤테이션
  const basicAnalysisMutation = useMutation({
    mutationFn: ({ videoSource, prompts }: { videoSource: VideoSource; prompts: BasicPrompts }) =>
      analysisApi.analyzeBasic(videoSource, prompts),
    onMutate: () => {
      setAnalysisStatus('analyzing');
      setAnalysisProgress({
        stage: 'Initializing analysis...',
        percentage: 0,
        message: 'Starting basic analysis with 3 prompts',
      });
    },
  });

  // 전문 분석 뮤테이션
  const professionalAnalysisMutation = useMutation({
    mutationFn: ({ videoSource, prompt }: { videoSource: VideoSource; prompt: string }) =>
      analysisApi.analyzeProfessional(videoSource, prompt),
    onMutate: () => {
      setAnalysisStatus('analyzing');
      setAnalysisProgress({
        stage: 'Initializing professional analysis...',
        percentage: 0,
        message: 'Starting Pegasus + Claude analysis pipeline',
      });
    },
  });

  // 인코딩 진행률 폴링
  const startEncodingProgressPolling = useCallback((fileId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await uploadApi.getEncodingProgress(fileId);
        if (response.success && response.data) {
          setEncodingProgress(response.data);
          
          // 인코딩 완료 확인
          if (response.data.percentage >= 100) {
            clearInterval(pollInterval);
            setEncodingProgress(null);
            setAnalysisStatus('idle');
            
            console.log('✅ Encoding completed, ready for analysis');
          }
        } else {
          // 인코딩 진행률 정보가 없으면 완료된 것으로 간주
          clearInterval(pollInterval);
          setEncodingProgress(null);
          setAnalysisStatus('idle');
          console.log('✅ Encoding progress not found, assuming completed');
        }
      } catch (error) {
        console.error('Error polling encoding progress:', error);
        clearInterval(pollInterval);
        setEncodingProgress(null);
        setAnalysisStatus('idle'); // 에러가 발생해도 분석 가능하도록 설정
      }
    }, 1000); // 1초마다 폴링

    return () => clearInterval(pollInterval);
  }, []);

  // 분석 상태 폴링
  const pollAnalysisStatus = useCallback(async (analysisId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await analysisApi.getAnalysisStatus(analysisId);
        if (response.success && response.data) {
          const result = response.data;
          
          // 진행률 업데이트
          if (result.status === 'analyzing') {
            setAnalysisProgress({
              stage: 'Processing video...',
              percentage: 50,
              message: 'AI models are analyzing your video',
            });
          }
          
          // 완료 또는 에러 시 폴링 중단
          if (result.status === 'completed' || result.status === 'error') {
            clearInterval(pollInterval);
            setAnalysisStatus(result.status);
            setAnalysisProgress(null);
            setCurrentResult(result);
          }
        }
      } catch (error) {
        console.error('Error polling analysis status:', error);
        clearInterval(pollInterval);
        setAnalysisStatus('error');
        setAnalysisProgress(null);
      }
    }, 2000); // 2초마다 폴링

    return () => clearInterval(pollInterval);
  }, []);

  // S3 URI 검증
  const validateS3Uri = useCallback(async (s3Uri: string) => {
    try {
      console.log('Starting S3 URI validation:', s3Uri);
      setAnalysisStatus('uploading'); // 검증 중 상태 표시
      
      const result = await s3UriMutation.mutateAsync(s3Uri);
      console.log('S3 URI validation result:', result);
      
      if (result.success) {
        setAnalysisStatus('idle');
        return result;
      } else {
        setAnalysisStatus('error');
        throw new Error(result.error || 'S3 URI validation failed');
      }
    } catch (error) {
      console.error('S3 URI validation error:', error);
      setAnalysisStatus('error');
      throw error;
    }
  }, [s3UriMutation]);

  // 전체 분석 프로세스 실행
  const runAnalysis = useCallback(async (
    videoSource: VideoSource,
    mode: AnalysisMode,
    prompts: BasicPrompts,
    professionalPrompt: string
  ) => {
    try {
      console.log('🚀 Starting analysis with videoSource:', videoSource);
      setAnalysisStatus('uploading');
      let analysisVideoSource = videoSource;

      // 파일 업로드가 필요한 경우
      if (videoSource.type === 'file' && videoSource.file) {
        console.log('📤 Uploading file for analysis...');
        const uploadResult = await uploadMutation.mutateAsync(videoSource.file);
        if (!uploadResult.success || !uploadResult.data) {
          throw new Error('File upload failed');
        }

        analysisVideoSource = {
          type: 'file',
          fileId: uploadResult.data.fileId
        };

        // 인코딩이 필요한 경우 완료까지 대기
        if (uploadResult.data.needs_encoding) {
          console.log('⏳ Waiting for encoding to complete...');
          
          // 인코딩 완료까지 대기
          await new Promise<void>((resolve, reject) => {
            const checkEncoding = setInterval(async () => {
              try {
                const progressResponse = await uploadApi.getEncodingProgress(uploadResult.data.fileId);
                if (progressResponse.success && progressResponse.data) {
                  setEncodingProgress(progressResponse.data);
                  
                  if (progressResponse.data.percentage >= 100) {
                    clearInterval(checkEncoding);
                    setEncodingProgress(null);
                    console.log('✅ Encoding completed, starting analysis...');
                    resolve();
                  }
                } else {
                  // 인코딩 진행률 정보가 없으면 완료된 것으로 간주
                  clearInterval(checkEncoding);
                  setEncodingProgress(null);
                  console.log('✅ Encoding progress not found, assuming completed');
                  resolve();
                }
              } catch (error) {
                clearInterval(checkEncoding);
                setEncodingProgress(null);
                console.error('❌ Encoding check failed:', error);
                reject(error);
              }
            }, 1000);
          });
        }
      }

      console.log('🔄 Starting AI analysis with source:', analysisVideoSource);
      setAnalysisStatus('analyzing');

      // 분석 시작
      let analysisResult;
      if (mode === 'basic') {
        analysisResult = await basicAnalysisMutation.mutateAsync({ 
          videoSource: analysisVideoSource, 
          prompts 
        });
      } else {
        analysisResult = await professionalAnalysisMutation.mutateAsync({ 
          videoSource: analysisVideoSource, 
          prompt: professionalPrompt 
        });
      }

      if (!analysisResult.success || !analysisResult.data) {
        throw new Error('Analysis failed to start');
      }

      console.log('✅ Analysis started with ID:', analysisResult.data.analysisId);

      // 분석 상태 폴링 시작
      const { analysisId } = analysisResult.data;
      pollAnalysisStatus(analysisId);

    } catch (error) {
      console.error('❌ Analysis error:', error);
      setAnalysisStatus('error');
      setAnalysisProgress(null);
      setEncodingProgress(null);
      setUploadProgress(null);
    }
  }, [uploadMutation, basicAnalysisMutation, professionalAnalysisMutation, pollAnalysisStatus]);

  // 상태 리셋
  const resetAnalysis = useCallback(() => {
    setAnalysisStatus('idle');
    setUploadProgress(null);
    setEncodingProgress(null);
    setAnalysisProgress(null);
    setCurrentResult(null);
  }, []);

  return {
    // 상태
    analysisStatus,
    uploadProgress,
    encodingProgress,
    analysisProgress,
    currentResult,
    
    // 액션
    runAnalysis,
    validateS3Uri,
    resetAnalysis,
    
    // 로딩 상태
    isUploading: uploadMutation.isPending,
    isEncoding: analysisStatus === 'encoding',
    isAnalyzing: basicAnalysisMutation.isPending || professionalAnalysisMutation.isPending,
  };
};
