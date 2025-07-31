import React, { useState } from 'react';
import { Tab } from '@headlessui/react';
import { PencilIcon, EyeIcon } from '@heroicons/react/24/outline';
import type { AnalysisMode, BasicPrompts } from '../types';

interface PromptEditorProps {
  analysisMode: AnalysisMode;
  basicPrompts: BasicPrompts;
  professionalPrompt: string;
  onBasicPromptsChange: (prompts: BasicPrompts) => void;
  onProfessionalPromptChange: (prompt: string) => void;
  disabled?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export const PromptEditor: React.FC<PromptEditorProps> = ({
  analysisMode,
  basicPrompts,
  professionalPrompt,
  onBasicPromptsChange,
  onProfessionalPromptChange,
  disabled = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);

  const handleBasicPromptChange = (key: keyof BasicPrompts, value: string) => {
    onBasicPromptsChange({
      ...basicPrompts,
      [key]: value,
    });
  };

  const resetToDefaults = () => {
    if (analysisMode === 'basic') {
      onBasicPromptsChange({
        prompt1: "이 비디오에 대해 자세히 설명해주세요. 주요 장면과 내용을 요약해주세요.",
        prompt2: "비디오에서 어떤 작업이나 활동이 진행되고 있나요? 구체적으로 설명해주세요.",
        prompt3: "이 비디오의 주요 하이라이트와 중요한 순간들을 찾아주세요.",
      });
    } else {
      onProfessionalPromptChange(
        "이 비디오의 영상에 대한 정보를 자세히 확인하세요. 공사 현장 영상인 경우, 작업 내용(토공, 교량공, 도배공 등)이 무엇인지, 투입장비(excavator, loader, dump truck 등)의 종류와 댓수, 어떤 기법으로 촬영(Bird View, Oblique View, Tracking View, CCTV, 1인칭, 360도 등)한 것인지를 확인합니다. 교육 동영상 등의 경우 어떤 내용의 영상인지 (영상의 자막이나 슬라이드 내용도 참고) 확인 합니다."
      );
    }
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-white">
          프롬프트 설정 ({analysisMode === 'basic' ? '기본 테스트' : '전문 분석'})
        </h3>
        <div className="flex space-x-2">
          <button
            onClick={() => setIsEditing(!isEditing)}
            disabled={disabled}
            className={`
              inline-flex items-center px-3 py-1.5 border border-gray-600/50 shadow-sm text-sm font-medium rounded-md transition-all duration-200
              ${disabled 
                ? 'text-gray-500 bg-gray-700/50 cursor-not-allowed' 
                : 'text-gray-300 bg-gray-800/70 hover:bg-gray-700/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-gray-900'
              }
            `}
          >
            {isEditing ? (
              <>
                <EyeIcon className="h-4 w-4 mr-1" />
                미리보기
              </>
            ) : (
              <>
                <PencilIcon className="h-4 w-4 mr-1" />
                편집
              </>
            )}
          </button>
          <button
            onClick={resetToDefaults}
            disabled={disabled}
            className={`
              inline-flex items-center px-3 py-1.5 border border-gray-600/50 shadow-sm text-sm font-medium rounded-md transition-all duration-200
              ${disabled 
                ? 'text-gray-500 bg-gray-700/50 cursor-not-allowed' 
                : 'text-gray-300 bg-gray-800/70 hover:bg-gray-700/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-gray-900'
              }
            `}
          >
            기본값 복원
          </button>
        </div>
      </div>

      {analysisMode === 'basic' ? (
        <Tab.Group>
          <Tab.List className="flex space-x-1 rounded-xl bg-gray-800/50 p-1">
            {['프롬프트 1', '프롬프트 2', '프롬프트 3'].map((tab) => (
              <Tab
                key={tab}
                className={({ selected }) =>
                  classNames(
                    'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all duration-200',
                    'ring-white ring-opacity-60 ring-offset-2 ring-offset-gray-900 focus:outline-none focus:ring-2',
                    selected
                      ? 'bg-gray-700 text-white shadow-lg'
                      : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-300'
                  )
                }
              >
                {tab}
              </Tab>
            ))}
          </Tab.List>
          <Tab.Panels className="mt-4">
            {[
              { key: 'prompt1' as keyof BasicPrompts, value: basicPrompts.prompt1 },
              { key: 'prompt2' as keyof BasicPrompts, value: basicPrompts.prompt2 },
              { key: 'prompt3' as keyof BasicPrompts, value: basicPrompts.prompt3 },
            ].map((prompt, promptIndex) => (
              <Tab.Panel key={promptIndex} className="rounded-xl bg-gray-800/30 p-3">
                {isEditing ? (
                  <textarea
                    value={prompt.value}
                    onChange={(e) => handleBasicPromptChange(prompt.key, e.target.value)}
                    disabled={disabled}
                    rows={6}
                    className={`
                      w-full rounded-md bg-gray-800/50 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-blue-500 focus:ring-blue-500
                      ${disabled ? 'bg-gray-700/50 cursor-not-allowed opacity-50' : ''}
                    `}
                    placeholder={`프롬프트 ${promptIndex + 1}을 입력하세요...`}
                  />
                ) : (
                  <div className="bg-gray-800/50 rounded-md p-4 min-h-[120px] border border-gray-700/50">
                    <p className="text-sm text-gray-300 whitespace-pre-wrap">
                      {prompt.value || `프롬프트 ${promptIndex + 1}이 비어있습니다.`}
                    </p>
                  </div>
                )}
              </Tab.Panel>
            ))}
          </Tab.Panels>
        </Tab.Group>
      ) : (
        <div className="space-y-4">
          <div className="bg-blue-500/20 border border-blue-400/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-300 mb-2">전문 분석 프롬프트</h4>
            <p className="text-xs text-blue-200">
              이 프롬프트는 Pegasus 1.2 모델에 전달되어 비디오를 분석합니다. 
              분석 결과는 Claude 3.7 Sonnet이 구조화된 JSON으로 변환합니다.
            </p>
          </div>
          
          {isEditing ? (
            <textarea
              value={professionalPrompt}
              onChange={(e) => onProfessionalPromptChange(e.target.value)}
              disabled={disabled}
              rows={8}
              className={`
                w-full rounded-md bg-gray-800/50 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-blue-500 focus:ring-blue-500
                ${disabled ? 'bg-gray-700/50 cursor-not-allowed opacity-50' : ''}
              `}
              placeholder="전문 분석 프롬프트를 입력하세요..."
            />
          ) : (
            <div className="bg-gray-800/50 rounded-md p-4 min-h-[160px] border border-gray-700/50">
              <p className="text-sm text-gray-300 whitespace-pre-wrap">
                {professionalPrompt || '전문 분석 프롬프트가 비어있습니다.'}
              </p>
            </div>
          )}
        </div>
      )}

      {/* 프롬프트 가이드 */}
      <div className="mt-4 p-4 bg-yellow-500/20 border border-yellow-400/50 rounded-lg">
        <h4 className="text-sm font-medium text-yellow-300 mb-2">💡 프롬프트 작성 가이드</h4>
        <div className="text-xs text-yellow-200 space-y-1">
          {analysisMode === 'basic' ? (
            <>
              <p>• 각 프롬프트는 서로 다른 관점에서 비디오를 분석합니다</p>
              <p>• 구체적이고 명확한 질문을 작성하세요</p>
              <p>• 비디오의 특정 요소(장면, 객체, 활동 등)에 집중하세요</p>
            </>
          ) : (
            <>
              <p>• 건설현장: 작업 유형, 장비, 촬영 기법을 명시하세요</p>
              <p>• 교육영상: 자막, 슬라이드 내용 분석을 요청하세요</p>
              <p>• 구체적인 정보 추출 항목을 나열하세요</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
