import React, { useState, useEffect } from 'react';
import { Dialog } from '@headlessui/react';
import { XMarkIcon, CogIcon, CheckIcon } from '@heroicons/react/24/outline';
import { configApi } from '../services/api';
import type { AppConfig } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 설정 로드
  useEffect(() => {
    if (isOpen) {
      loadConfig();
    }
  }, [isOpen]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await configApi.getConfig();
      if (response.success && response.data) {
        setConfig(response.data);
      } else {
        setError('설정을 불러올 수 없습니다.');
      }
    } catch (err) {
      setError('설정 로드 중 오류가 발생했습니다.');
      console.error('Config load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;

    try {
      setSaving(true);
      setError(null);
      
      const response = await configApi.updateConfig(config);
      if (response.success) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } else {
        setError('설정 저장에 실패했습니다.');
      }
    } catch (err) {
      setError('설정 저장 중 오류가 발생했습니다.');
      console.error('Config save error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (field: keyof AppConfig, value: string) => {
    if (!config) return;
    
    setConfig({
      ...config,
      [field]: value
    });
  };

  const handleCompressionSettingChange = (field: string, value: string | number) => {
    if (!config) return;
    
    setConfig({
      ...config,
      video_compression_settings: {
        ...config.video_compression_settings,
        [field]: typeof value === 'string' ? parseInt(value) || 0 : value
      }
    });
  };

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      {/* 배경 오버레이 */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" aria-hidden="true" />
      
      {/* 모달 컨테이너 */}
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="bg-gray-800 rounded-2xl shadow-2xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
          {/* 헤더 */}
          <div className="flex items-center justify-between p-6 border-b border-gray-700">
            <div className="flex items-center">
              <CogIcon className="h-6 w-6 text-blue-400 mr-3" />
              <Dialog.Title className="text-xl font-semibold text-white">
                시스템 설정
              </Dialog.Title>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-300 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {/* 콘텐츠 */}
          <div className="p-6">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <span className="ml-3 text-gray-300">설정을 불러오는 중...</span>
              </div>
            ) : error ? (
              <div className="bg-red-500/20 border border-red-400/50 rounded-lg p-4 mb-6">
                <p className="text-red-300">{error}</p>
                <button
                  onClick={loadConfig}
                  className="mt-2 text-sm text-red-200 hover:text-red-100 underline"
                >
                  다시 시도
                </button>
              </div>
            ) : config ? (
              <div className="space-y-6">
                {/* AWS 설정 */}
                <div>
                  <h3 className="text-lg font-medium text-white mb-4">AWS 설정</h3>
                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        AWS 리전
                      </label>
                      <input
                        type="text"
                        value={config.aws_region}
                        onChange={(e) => handleInputChange('aws_region', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:ring-blue-500"
                        placeholder="us-west-2"
                      />
                    </div>
                  </div>
                </div>

                {/* 모델 설정 */}
                <div>
                  <h3 className="text-lg font-medium text-white mb-4">AI 모델 설정</h3>
                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Pegasus 모델 ID
                      </label>
                      <input
                        type="text"
                        value={config.pegasus_model_id}
                        onChange={(e) => handleInputChange('pegasus_model_id', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:ring-blue-500 font-mono text-sm"
                        placeholder="us.twelvelabs.pegasus-1-2-v1:0"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Claude 모델 ID
                      </label>
                      <input
                        type="text"
                        value={config.claude_model_id}
                        onChange={(e) => handleInputChange('claude_model_id', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:ring-blue-500 font-mono text-sm"
                        placeholder="us.anthropic.claude-3-7-sonnet-20250219-v1:0"
                      />
                    </div>
                  </div>
                </div>

                {/* 비디오 압축 설정 */}
                <div>
                  <h3 className="text-lg font-medium text-white mb-4">비디오 압축 설정</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        최대 크기 (MB)
                      </label>
                      <input
                        type="number"
                        value={config.video_compression_settings.max_size_mb}
                        onChange={(e) => handleCompressionSettingChange('max_size_mb', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:ring-blue-500"
                        min="1"
                        max="100"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        프레임레이트 (fps)
                      </label>
                      <input
                        type="number"
                        value={config.video_compression_settings.framerate}
                        onChange={(e) => handleCompressionSettingChange('framerate', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:ring-blue-500"
                        min="1"
                        max="60"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        CRF (품질)
                      </label>
                      <input
                        type="number"
                        value={config.video_compression_settings.crf}
                        onChange={(e) => handleCompressionSettingChange('crf', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:ring-blue-500"
                        min="18"
                        max="51"
                      />
                      <p className="text-xs text-gray-500 mt-1">낮을수록 고품질 (18-28 권장)</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        해상도
                      </label>
                      <input
                        type="text"
                        value={config.video_compression_settings.resolution}
                        onChange={(e) => handleCompressionSettingChange('resolution', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:ring-blue-500"
                        placeholder="854:480"
                      />
                    </div>
                  </div>
                </div>

                {/* 시스템 정보 */}
                <div>
                  <h3 className="text-lg font-medium text-white mb-4">시스템 정보</h3>
                  <div className="bg-gray-700/50 rounded-lg p-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Base64 제한:</span>
                      <span className="text-gray-200">36MB</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">S3 버킷:</span>
                      <span className="text-gray-200 font-mono">bedrock-pegasus-video-temp</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">최대 비디오 크기:</span>
                      <span className="text-gray-200">2GB</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          {/* 푸터 */}
          <div className="flex items-center justify-between p-6 border-t border-gray-700">
            <div className="flex items-center">
              {saved && (
                <div className="flex items-center text-green-400 text-sm">
                  <CheckIcon className="h-4 w-4 mr-1" />
                  저장되었습니다
                </div>
              )}
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !config}
                className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 ${
                  saving || !config
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {saving ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div>
                    저장 중...
                  </>
                ) : (
                  '저장'
                )}
              </button>
            </div>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
};
