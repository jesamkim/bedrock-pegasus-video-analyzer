import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PlayIcon, CogIcon } from '@heroicons/react/24/solid';
import { VideoUpload } from './components/VideoUpload';
import { AnalysisModeSelector } from './components/AnalysisModeSelector';
import { PromptEditor } from './components/PromptEditor';
import { AnalysisResults } from './components/AnalysisResults';
import { SettingsModal } from './components/SettingsModal';
import { useAnalysis } from './hooks/useAnalysis';
import type { AnalysisMode, BasicPrompts, VideoSource } from './types';

// React Query 클라이언트 생성
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function VideoAnalyzerApp() {
  // 상태 관리
  const [videoSource, setVideoSource] = useState<VideoSource | null>(null);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>('basic');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [basicPrompts, setBasicPrompts] = useState<BasicPrompts>({
    prompt1: "이 비디오에 대해 자세히 설명해주세요. 주요 장면과 내용을 요약해주세요.",
    prompt2: "비디오에서 어떤 작업이나 활동이 진행되고 있나요? 구체적으로 설명해주세요.",
    prompt3: "이 비디오의 주요 하이라이트와 중요한 순간들을 찾아주세요.",
  });
  const [professionalPrompt, setProfessionalPrompt] = useState(
    "이 비디오의 영상에 대한 정보를 자세히 확인하세요. 공사 현장 영상인 경우, 작업 내용(토공, 교량공, 도배공 등)이 무엇인지, 투입장비(excavator, loader, dump truck 등)의 종류와 댓수, 어떤 기법으로 촬영(Bird View, Oblique View, Tracking View, CCTV, 1인칭, 360도 등)한 것인지를 확인합니다. 교육 동영상 등의 경우 어떤 내용의 영상인지 (영상의 자막이나 슬라이드 내용도 참고) 확인 합니다."
  );

  // 분석 훅 사용
  const {
    analysisStatus,
    uploadProgress,
    encodingProgress,
    analysisProgress,
    currentResult,
    runAnalysis,
    validateS3Uri,
    resetAnalysis,
    isUploading,
    isEncoding,
    isAnalyzing,
  } = useAnalysis();

  // 파일 선택 핸들러
  const handleFileSelect = (file: File) => {
    console.log('📁 File selected:', file.name, `(${(file.size / 1024 / 1024).toFixed(2)}MB)`);
    setVideoSource({
      type: 'file',
      file: file
    });
  };

  // S3 URI 선택 핸들러
  const handleS3UriSelect = async (s3Uri: string) => {
    console.log('handleS3UriSelect called with:', s3Uri);
    
    if (!s3Uri) {
      console.log('Empty S3 URI, clearing video source');
      setVideoSource(null);
      return;
    }

    try {
      console.log('Starting S3 URI validation...');
      const result = await validateS3Uri(s3Uri);
      console.log('S3 URI validation result:', result);
      
      if (result.success) {
        console.log('Setting video source to S3 URI');
        setVideoSource({
          type: 's3uri',
          s3Uri: s3Uri
        });
      }
    } catch (error) {
      console.error('S3 URI validation failed:', error);
      // 에러는 VideoUpload 컴포넌트에서 처리
    }
  };

  // 분석 시작 핸들러
  const handleAnalyze = async () => {
    if (!videoSource) return;
    
    await runAnalysis(videoSource, analysisMode, basicPrompts, professionalPrompt);
  };

  // 새 분석 시작 핸들러
  const handleNewAnalysis = () => {
    setVideoSource(null);
    resetAnalysis();
  };

  const canAnalyze = videoSource && !isAnalyzing;
  const isProcessing = isUploading || isEncoding || isAnalyzing;

  // 디버깅을 위한 로그
  console.log('🔍 Analysis button state:', {
    videoSource: !!videoSource,
    videoSourceType: videoSource?.type,
    isUploading,
    isEncoding,
    isAnalyzing,
    canAnalyze,
    analysisStatus
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-black">
      {/* 헤더 */}
      <header className="bg-gray-900/80 backdrop-blur-sm shadow-2xl border-b border-gray-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="h-10 w-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mr-4 shadow-lg">
                <PlayIcon className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">
                  Bedrock Pegasus 비디오 분석기
                </h1>
                <p className="text-sm text-gray-400">
                  TwelveLabs Pegasus 1.2 + Claude 3.7 Sonnet을 활용한 AI 비디오 분석
                </p>
              </div>
            </div>
            <button 
              onClick={() => setIsSettingsOpen(true)}
              className="inline-flex items-center px-4 py-2 border border-gray-600/50 shadow-sm text-sm font-medium rounded-lg text-gray-300 bg-gray-800/70 hover:bg-gray-700/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 backdrop-blur-sm"
            >
              <CogIcon className="h-4 w-4 mr-2" />
              설정
            </button>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {/* 왼쪽 패널: 입력 및 설정 */}
          <div className="space-y-6">
            {/* 비디오 업로드 */}
            <div className="bg-gray-800/70 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-700/30 p-6 hover:shadow-3xl hover:border-gray-600/50 transition-all duration-300">
              <div className="flex items-center mb-4">
                <div className="h-8 w-8 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center mr-3">
                  <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-white">비디오 업로드</h2>
              </div>
              <VideoUpload
                onFileSelect={handleFileSelect}
                onS3UriSelect={handleS3UriSelect}
                uploadProgress={uploadProgress}
                encodingProgress={encodingProgress}
                isUploading={isUploading}
                isEncoding={isEncoding}
                selectedFile={videoSource?.type === 'file' ? videoSource.file || null : null}
                selectedS3Uri={videoSource?.type === 's3uri' ? videoSource.s3Uri || null : null}
              />
            </div>

            {/* 분석 모드 선택 */}
            <div className="bg-gray-800/70 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-700/30 p-6 hover:shadow-3xl hover:border-gray-600/50 transition-all duration-300">
              <div className="flex items-center mb-4">
                <div className="h-8 w-8 bg-gradient-to-br from-green-500 to-emerald-500 rounded-lg flex items-center justify-center mr-3">
                  <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-white">분석 모드</h2>
              </div>
              <AnalysisModeSelector
                selectedMode={analysisMode}
                onModeChange={setAnalysisMode}
                disabled={isProcessing}
              />
            </div>

            {/* 프롬프트 편집 */}
            <div className="bg-gray-800/70 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-700/30 p-6 hover:shadow-3xl hover:border-gray-600/50 transition-all duration-300">
              <div className="flex items-center mb-4">
                <div className="h-8 w-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center mr-3">
                  <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-white">프롬프트 설정</h2>
              </div>
              <PromptEditor
                analysisMode={analysisMode}
                basicPrompts={basicPrompts}
                professionalPrompt={professionalPrompt}
                onBasicPromptsChange={setBasicPrompts}
                onProfessionalPromptChange={setProfessionalPrompt}
                disabled={isProcessing}
              />
            </div>

            {/* 분석 버튼 */}
            <div className="flex space-x-4">
              <button
                onClick={handleAnalyze}
                disabled={!canAnalyze}
                className={`
                  flex-1 inline-flex justify-center items-center px-8 py-4 border border-transparent text-base font-semibold rounded-xl shadow-lg transition-all duration-200 transform
                  ${canAnalyze
                    ? 'text-white bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 hover:scale-105 hover:shadow-2xl focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-gray-900'
                    : 'text-gray-500 bg-gray-700 cursor-not-allowed'
                  }
                `}
              >
                {isProcessing ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-3"></div>
                    {isUploading ? '업로드 중...' : '분석 중...'}
                  </>
                ) : (
                  <>
                    <PlayIcon className="h-5 w-5 mr-3" />
                    Analyze
                  </>
                )}
              </button>

              {(currentResult || isProcessing) && (
                <button
                  onClick={handleNewAnalysis}
                  disabled={isProcessing}
                  className={`
                    px-6 py-4 border border-gray-600/50 text-base font-medium rounded-xl shadow-lg transition-all duration-200 backdrop-blur-sm
                    ${isProcessing
                      ? 'text-gray-500 bg-gray-700/50 cursor-not-allowed'
                      : 'text-gray-300 bg-gray-800/70 hover:bg-gray-700/90 hover:shadow-2xl focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-gray-900'
                    }
                  `}
                >
                  새 분석
                </button>
              )}
            </div>
          </div>

          {/* 오른쪽 패널: 결과 */}
          <div className="bg-gray-800/70 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-700/30 p-6 hover:shadow-3xl hover:border-gray-600/50 transition-all duration-300">
            <div className="flex items-center mb-4">
              <div className="h-8 w-8 bg-gradient-to-br from-orange-500 to-red-500 rounded-lg flex items-center justify-center mr-3">
                <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-white">분석 결과</h2>
            </div>
            <AnalysisResults
              result={currentResult}
              progress={analysisProgress}
              isAnalyzing={isAnalyzing}
            />
          </div>
        </div>
      </main>

      {/* 설정 모달 */}
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />

      {/* 푸터 */}
      <footer className="bg-gray-900/50 backdrop-blur-sm border-t border-gray-700/50 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center space-y-2">
            <p className="text-sm text-gray-400">
              Powered by{' '}
              <span className="font-semibold bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">Amazon Bedrock</span> •{' '}
              <span className="font-semibold bg-gradient-to-r from-green-400 to-green-600 bg-clip-text text-transparent">TwelveLabs Pegasus 1.2</span> •{' '}
              <span className="font-semibold bg-gradient-to-r from-purple-400 to-purple-600 bg-clip-text text-transparent">Claude 3.7 Sonnet</span>
            </p>
            <p className="text-xs text-gray-500">
              Developed by{' '}
              <span className="font-medium bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">jesamkim</span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <VideoAnalyzerApp />
    </QueryClientProvider>
  );
}

export default App;
