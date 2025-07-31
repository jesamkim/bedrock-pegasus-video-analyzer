import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, VideoCameraIcon, LinkIcon, XMarkIcon } from '@heroicons/react/24/outline';
import type { UploadProgress } from '../types';

interface VideoUploadProps {
  onFileSelect: (file: File) => void;
  onS3UriSelect: (uri: string) => void;
  uploadProgress: UploadProgress | null;
  encodingProgress: EncodingProgress | null;
  isUploading: boolean;
  isEncoding: boolean;
  selectedFile: File | null;
  selectedS3Uri: string | null;
}

interface EncodingProgress {
  percentage: number;
  stage: string;
  message: string;
}

export const VideoUpload: React.FC<VideoUploadProps> = ({
  onFileSelect,
  onS3UriSelect,
  uploadProgress,
  encodingProgress,
  isUploading,
  isEncoding,
  selectedFile,
  selectedS3Uri,
}) => {
  const [inputMode, setInputMode] = useState<'upload' | 's3uri'>('upload');
  const [s3UriInput, setS3UriInput] = useState('');
  const [s3UriError, setS3UriError] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      console.log('📁 File selected (not uploaded yet):', {
        name: file.name,
        size: `${(file.size / 1024 / 1024).toFixed(2)}MB`,
        type: file.type
      });
      onFileSelect(acceptedFiles[0]);
      setS3UriInput('');
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/mp4': ['.mp4'],
      'video/quicktime': ['.mov'],
      'video/x-msvideo': ['.avi'],
      'video/webm': ['.webm'],
    },
    maxFiles: 1,
    maxSize: 2 * 1024 * 1024 * 1024, // 2GB
    disabled: isUploading || isEncoding,
  });

  const validateS3Uri = (uri: string): boolean => {
    const s3UriPattern = /^s3:\/\/[a-z0-9.-]+\/.*\.(mp4|mov|avi|webm)$/i;
    return s3UriPattern.test(uri);
  };

  const handleS3UriSubmit = async () => {
    const trimmedUri = s3UriInput.trim();
    
    if (!trimmedUri) {
      setS3UriError('S3 URI를 입력해주세요.');
      return;
    }

    if (!validateS3Uri(trimmedUri)) {
      setS3UriError('올바른 S3 URI 형식이 아닙니다. (예: s3://bucket-name/video.mp4)');
      return;
    }

    try {
      setS3UriError('');
      console.log('Validating S3 URI:', trimmedUri);
      await onS3UriSelect(trimmedUri);
    } catch (error) {
      console.error('S3 URI validation error:', error);
      setS3UriError(`S3 URI 검증 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
    }
  };

  const clearSelection = () => {
    setS3UriInput('');
    setS3UriError('');
    onS3UriSelect('');
    onFileSelect(null as any);
  };

  return (
    <div className="w-full">
      {/* 인코딩 진행률 모달 */}
      {isEncoding && encodingProgress && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-2xl p-8 max-w-md w-full mx-4 border border-gray-700">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-6 relative">
                <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="35"
                    stroke="currentColor"
                    strokeWidth="6"
                    fill="transparent"
                    className="text-gray-700"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="35"
                    stroke="currentColor"
                    strokeWidth="6"
                    fill="transparent"
                    strokeDasharray={`${2 * Math.PI * 35}`}
                    strokeDashoffset={`${2 * Math.PI * 35 * (1 - encodingProgress.percentage / 100)}`}
                    className="text-blue-500 transition-all duration-300"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-semibold text-blue-400">
                    {encodingProgress.percentage}%
                  </span>
                </div>
              </div>
              
              <h3 className="text-xl font-semibold text-white mb-2">
                비디오 인코딩 중
              </h3>
              <p className="text-gray-400 mb-4">
                {encodingProgress.stage}
              </p>
              <p className="text-sm text-gray-500">
                {encodingProgress.message}
              </p>
              
              <div className="mt-6 p-3 bg-yellow-500/20 border border-yellow-400/50 rounded-lg">
                <p className="text-xs text-yellow-200">
                  💡 비디오를 30MB 이하로 압축하여 최적화하고 있습니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 입력 모드 선택 */}
      <div className="flex space-x-1 mb-4 bg-gray-800/50 rounded-lg p-1">
        <button
          onClick={() => setInputMode('upload')}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200 ${
            inputMode === 'upload'
              ? 'bg-blue-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-gray-300 hover:bg-gray-700/50'
          }`}
        >
          <CloudArrowUpIcon className="h-4 w-4 inline mr-2" />
          파일 업로드
        </button>
        <button
          onClick={() => setInputMode('s3uri')}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200 ${
            inputMode === 's3uri'
              ? 'bg-green-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-gray-300 hover:bg-gray-700/50'
          }`}
        >
          <LinkIcon className="h-4 w-4 inline mr-2" />
          S3 URI
        </button>
      </div>

      {inputMode === 'upload' ? (
        /* 파일 업로드 모드 */
        <div>
          <div
            {...getRootProps()}
            className={`
              relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300
              ${isDragActive 
                ? 'border-blue-400 bg-blue-500/10 shadow-lg shadow-blue-500/20' 
                : 'border-gray-600 hover:border-gray-500 bg-gray-900/30'
              }
              ${isUploading || isEncoding ? 'cursor-not-allowed opacity-50' : ''}
            `}
          >
            <input {...getInputProps()} />
            
            {/* 업로드 진행률 표시 */}
            {uploadProgress && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900/90 rounded-xl backdrop-blur-sm">
                <div className="text-center">
                  <div className="w-32 h-32 mx-auto mb-4 relative">
                    <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="transparent"
                        className="text-gray-700"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="transparent"
                        strokeDasharray={`${2 * Math.PI * 40}`}
                        strokeDashoffset={`${2 * Math.PI * 40 * (1 - uploadProgress.percentage / 100)}`}
                        className="text-blue-500 transition-all duration-300"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-2xl font-semibold text-blue-400">
                        {uploadProgress.percentage}%
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-300">
                    업로드 중... ({Math.round(uploadProgress.loaded / 1024 / 1024)}MB / {Math.round(uploadProgress.total / 1024 / 1024)}MB)
                  </p>
                </div>
              </div>
            )}

            {/* 기본 업로드 UI */}
            {!uploadProgress && (
              <>
                {selectedFile ? (
                  <div className="space-y-4">
                    <VideoCameraIcon className="mx-auto h-16 w-16 text-green-400" />
                    <div>
                      <p className="text-lg font-medium text-white">{selectedFile.name}</p>
                      <p className="text-sm text-gray-400">
                        크기: {Math.round(selectedFile.size / 1024 / 1024)}MB
                      </p>
                      <p className="text-sm text-green-400 mt-2">
                        ✓ 파일이 선택되었습니다. 다른 파일을 선택하려면 클릭하세요.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <CloudArrowUpIcon className="mx-auto h-16 w-16 text-gray-500" />
                    <div>
                      <p className="text-lg font-medium text-white">
                        {isDragActive ? '파일을 여기에 놓으세요' : '비디오 파일을 업로드하세요'}
                      </p>
                      <p className="text-sm text-gray-400">
                        MP4, MOV, AVI, WebM 파일을 드래그하거나 클릭하여 선택하세요
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        최대 파일 크기: 2GB (자동으로 30MB 이하로 압축됩니다)
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      ) : (
        /* S3 URI 입력 모드 */
        <div className="space-y-4">
          <div className="bg-gray-900/30 border-2 border-gray-600 rounded-xl p-6">
            <div className="flex items-center mb-4">
              <LinkIcon className="h-6 w-6 text-green-400 mr-2" />
              <h3 className="text-lg font-medium text-white">S3 URI 입력</h3>
            </div>
            
            <div className="space-y-3">
              <input
                type="text"
                value={s3UriInput}
                onChange={(e) => {
                  setS3UriInput(e.target.value);
                  setS3UriError('');
                }}
                placeholder="s3://your-bucket/path/to/video.mp4"
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-green-500 focus:ring-green-500"
                disabled={isUploading || isEncoding}
              />
              
              {s3UriError && (
                <p className="text-sm text-red-400">{s3UriError}</p>
              )}
              
              <button
                onClick={handleS3UriSubmit}
                disabled={isUploading || isEncoding || !s3UriInput.trim()}
                className={`w-full py-3 px-4 rounded-lg font-medium transition-all duration-200 ${
                  s3UriInput.trim() && !isUploading && !isEncoding
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-gray-700 text-gray-400 cursor-not-allowed'
                }`}
              >
                {isUploading ? '검증 중...' : 'S3 URI 확인'}
              </button>
            </div>
          </div>
          
          <div className="bg-blue-500/20 border border-blue-400/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-300 mb-2">💡 S3 URI 사용 가이드</h4>
            <ul className="text-xs text-blue-200 space-y-1">
              <li>• 형식: s3://bucket-name/path/to/video.mp4</li>
              <li>• 지원 형식: MP4, MOV, AVI, WebM</li>
              <li>• 최대 크기: 2GB, 최대 길이: 1시간</li>
              <li>• AWS 계정에서 해당 S3 객체에 접근 권한이 필요합니다</li>
            </ul>
          </div>
        </div>
      )}

      {/* 선택된 항목 표시 */}
      {(selectedFile || selectedS3Uri) && !uploadProgress && (
        <div className="mt-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700/50">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-white mb-2">선택된 비디오</h4>
              {selectedFile ? (
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">파일명:</span>
                    <span className="ml-2 text-gray-200">{selectedFile.name}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">크기:</span>
                    <span className="ml-2 text-gray-200">{Math.round(selectedFile.size / 1024 / 1024)}MB</span>
                  </div>
                  <div>
                    <span className="text-gray-400">타입:</span>
                    <span className="ml-2 text-gray-200">{selectedFile.type}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">처리 방식:</span>
                    <span className="ml-2 text-blue-300">자동 인코딩</span>
                  </div>
                </div>
              ) : (
                <div className="text-sm">
                  <div className="mb-2">
                    <span className="text-gray-400">S3 URI:</span>
                    <span className="ml-2 text-gray-200 font-mono text-xs break-all">{selectedS3Uri}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">처리 방식:</span>
                    <span className="ml-2 text-green-300">직접 접근</span>
                  </div>
                </div>
              )}
            </div>
            
            <button
              onClick={clearSelection}
              className="p-2 text-gray-400 hover:text-gray-300 hover:bg-gray-700/50 rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
