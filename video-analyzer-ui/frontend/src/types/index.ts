// 분석 모드 타입
export type AnalysisMode = 'basic' | 'professional';

// 분석 상태 타입
export type AnalysisStatus = 'idle' | 'uploading' | 'encoding' | 'analyzing' | 'completed' | 'error';

// 기본 테스트 프롬프트
export interface BasicPrompts {
  prompt1: string;
  prompt2: string;
  prompt3: string;
}

// 비디오 압축 설정
export interface VideoCompressionSettings {
  max_size_mb: number;
  crf: number;
  preset: string;
  resolution: string;
  framerate: number;
  duration_seconds?: number;
}

// 앱 설정
export interface AppConfig {
  aws_region: string;
  pegasus_model_id: string;
  claude_model_id: string;
  video_compression_settings: VideoCompressionSettings;
  test_video_compression_settings: VideoCompressionSettings;
}

// 분석 결과
export interface AnalysisResult {
  id: string;
  filename: string;
  analysis_mode: AnalysisMode;
  timestamp: string;
  status: AnalysisStatus;
  results?: {
    basic_results?: Array<{
      prompt: string;
      response: string;
    }>;
    professional_result?: {
      video_type: string;
      construction_info?: {
        work_type: string[];
        equipment: Record<string, number | string>;
        filming_technique?: string[];
      };
      educational_info?: {
        content_type: string;
        slide_content?: string;
      };
      confidence_score: number;
    };
  };
  error?: string;
}

// 업로드 진행 상태
export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

// 인코딩 진행 상태
export interface EncodingProgress {
  percentage: number;
  stage: string;
  message: string;
}

// 분석 진행 상태
export interface AnalysisProgress {
  stage: string;
  percentage: number;
  message: string;
}

// API 응답 타입
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 비디오 입력 소스
export interface VideoSource {
  type: 'file' | 's3uri';
  file?: File;
  s3Uri?: string;
}

// 앱 상태
export interface AppState {
  // 파일 관련
  videoSource: VideoSource | null;
  uploadProgress: UploadProgress | null;
  encodingProgress: EncodingProgress | null;
  
  // 프롬프트 관련
  basicPrompts: BasicPrompts;
  professionalPrompt: string;
  
  // 분석 관련
  analysisMode: AnalysisMode;
  analysisStatus: AnalysisStatus;
  analysisProgress: AnalysisProgress | null;
  
  // 결과 관련
  results: AnalysisResult[];
  currentResult: AnalysisResult | null;
  
  // 설정 관련
  config: AppConfig;
}
