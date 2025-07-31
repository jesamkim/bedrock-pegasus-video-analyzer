import React from 'react';
import { RadioGroup } from '@headlessui/react';
import { CheckCircleIcon } from '@heroicons/react/24/solid';
import type { AnalysisMode } from '../types';

interface AnalysisModeSelectorProps {
  selectedMode: AnalysisMode;
  onModeChange: (mode: AnalysisMode) => void;
  disabled?: boolean;
}

const analysisOptions = [
  {
    id: 'basic' as AnalysisMode,
    title: '기본 테스트',
    description: '3개 시나리오로 일반적인 비디오 분석',
    features: [
      'TwelveLabs Pegasus 1.2 모델 사용',
      '3개 프롬프트 자동 순차 실행',
      '일반적인 비디오 분석 및 요약',
      'JSON 결과 파일 저장',
    ],
    icon: '🔍',
    color: 'blue',
  },
  {
    id: 'professional' as AnalysisMode,
    title: '전문 분석',
    description: 'Pegasus + Claude를 활용한 전문 분석',
    features: [
      'Pegasus 1.2 → 비디오 분석',
      'Claude 3.7 Sonnet → 결과 카테고라이징',
      '공사현장/교육영상 전문 분석',
      '구조화된 JSON 출력',
    ],
    icon: '🎯',
    color: 'green',
  },
];

export const AnalysisModeSelector: React.FC<AnalysisModeSelectorProps> = ({
  selectedMode,
  onModeChange,
  disabled = false,
}) => {
  return (
    <div className="w-full">
      <RadioGroup value={selectedMode} onChange={onModeChange} disabled={disabled}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {analysisOptions.map((option) => (
            <RadioGroup.Option
              key={option.id}
              value={option.id}
              className={({ active, checked }) =>
                `${active ? 'ring-2 ring-offset-2 ring-blue-500 ring-offset-gray-900' : ''}
                ${checked 
                  ? option.color === 'blue' 
                    ? 'bg-blue-500/20 border-blue-400 ring-2 ring-blue-500' 
                    : 'bg-green-500/20 border-green-400 ring-2 ring-green-500'
                  : 'bg-gray-800/50 border-gray-600'
                }
                ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:bg-gray-700/50'}
                relative border rounded-xl px-6 py-4 shadow-lg focus:outline-none transition-all duration-200`
              }
            >
              {({ checked }) => (
                <>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="text-2xl mr-3">{option.icon}</div>
                      <div className="text-sm">
                        <RadioGroup.Label as="p" className="font-medium text-white">
                          {option.title}
                        </RadioGroup.Label>
                        <RadioGroup.Description as="p" className="text-gray-400">
                          {option.description}
                        </RadioGroup.Description>
                      </div>
                    </div>
                    {checked && (
                      <CheckCircleIcon 
                        className={`h-5 w-5 ${
                          option.color === 'blue' ? 'text-blue-400' : 'text-green-400'
                        }`} 
                      />
                    )}
                  </div>
                  
                  <div className="mt-4">
                    <ul className="text-xs text-gray-400 space-y-1">
                      {option.features.map((feature, index) => (
                        <li key={index} className="flex items-center">
                          <span className="w-1 h-1 bg-gray-500 rounded-full mr-2"></span>
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </RadioGroup.Option>
          ))}
        </div>
      </RadioGroup>
      
      {/* 선택된 모드에 대한 추가 정보 */}
      <div className="mt-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700/50">
        <h4 className="text-sm font-medium text-white mb-2">
          {selectedMode === 'basic' ? '기본 테스트 모드' : '전문 분석 모드'} 정보
        </h4>
        <div className="text-sm text-gray-400">
          {selectedMode === 'basic' ? (
            <div className="space-y-2">
              <p>• <strong className="text-gray-300">처리 시간:</strong> 약 2-3분 (비디오 길이에 따라 변동)</p>
              <p>• <strong className="text-gray-300">출력 형태:</strong> 3개의 개별 JSON 결과 파일</p>
              <p>• <strong className="text-gray-300">적합한 용도:</strong> 일반적인 비디오 내용 파악 및 요약</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p>• <strong className="text-gray-300">처리 시간:</strong> 약 3-5분 (2단계 AI 파이프라인)</p>
              <p>• <strong className="text-gray-300">출력 형태:</strong> 구조화된 단일 JSON 결과</p>
              <p>• <strong className="text-gray-300">적합한 용도:</strong> 건설현장/교육영상 전문 분석</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
