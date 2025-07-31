import axios, { type AxiosProgressEvent } from 'axios';
import type { ApiResponse, AppConfig, AnalysisResult, BasicPrompts, VideoSource, EncodingProgress } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5분 타임아웃
});

// 설정 관련 API
export const configApi = {
  getConfig: async (): Promise<ApiResponse<AppConfig>> => {
    const response = await api.get('/api/config');
    return response.data;
  },
  
  updateConfig: async (config: Partial<AppConfig>): Promise<ApiResponse<AppConfig>> => {
    const response = await api.put('/api/config', config);
    return response.data;
  },
};

// 파일 업로드 API
export const uploadApi = {
  uploadVideo: async (
    file: File,
    onProgress?: (progress: AxiosProgressEvent) => void
  ): Promise<ApiResponse<{ fileId: string; filename: string; needs_encoding: boolean }>> => {
    const formData = new FormData();
    formData.append('video', file);
    
    const response = await api.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    });
    
    return response.data;
  },

  validateS3Uri: async (s3Uri: string): Promise<ApiResponse<{ uriId: string; s3Uri: string }>> => {
    const response = await api.post('/api/validate-s3-uri', { s3Uri });
    return response.data;
  },

  getEncodingProgress: async (fileId: string): Promise<ApiResponse<EncodingProgress>> => {
    const response = await api.get(`/api/encoding-progress/${fileId}`);
    return response.data;
  },
};

// 분석 API
export const analysisApi = {
  analyzeBasic: async (
    videoSource: VideoSource,
    prompts: BasicPrompts
  ): Promise<ApiResponse<{ analysisId: string }>> => {
    const requestData: any = {
      prompts: [prompts.prompt1, prompts.prompt2, prompts.prompt3],
    };

    if (videoSource.type === 'file' && videoSource.fileId) {
      requestData.fileId = videoSource.fileId;
    } else if (videoSource.type === 's3uri' && videoSource.s3Uri) {
      requestData.s3Uri = videoSource.s3Uri;
    } else {
      throw new Error('Invalid video source');
    }

    const response = await api.post('/api/analyze/basic', requestData);
    return response.data;
  },
  
  analyzeProfessional: async (
    videoSource: VideoSource,
    prompt: string
  ): Promise<ApiResponse<{ analysisId: string }>> => {
    const requestData: any = {
      prompt,
    };

    if (videoSource.type === 'file' && videoSource.fileId) {
      requestData.fileId = videoSource.fileId;
    } else if (videoSource.type === 's3uri' && videoSource.s3Uri) {
      requestData.s3Uri = videoSource.s3Uri;
    } else {
      throw new Error('Invalid video source');
    }

    const response = await api.post('/api/analyze/professional', requestData);
    return response.data;
  },
  
  getAnalysisStatus: async (analysisId: string): Promise<ApiResponse<AnalysisResult>> => {
    const response = await api.get(`/api/analysis/${analysisId}/status`);
    return response.data;
  },
  
  getAnalysisResult: async (analysisId: string): Promise<ApiResponse<AnalysisResult>> => {
    const response = await api.get(`/api/analysis/${analysisId}/result`);
    return response.data;
  },
};

// 결과 관련 API
export const resultsApi = {
  getResults: async (): Promise<ApiResponse<AnalysisResult[]>> => {
    const response = await api.get('/api/results');
    return response.data;
  },
  
  deleteResult: async (resultId: string): Promise<ApiResponse<void>> => {
    const response = await api.delete(`/api/results/${resultId}`);
    return response.data;
  },
  
  downloadResult: async (resultId: string): Promise<Blob> => {
    const response = await api.get(`/api/results/${resultId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export default api;
