import React, { useState } from 'react';
import { Tab } from '@headlessui/react';
import { 
  DocumentArrowDownIcon, 
  ClipboardDocumentIcon,
  CheckIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon 
} from '@heroicons/react/24/outline';
import type { AnalysisResult, AnalysisProgress } from '../types';

interface AnalysisResultsProps {
  result: AnalysisResult | null;
  progress: AnalysisProgress | null;
  isAnalyzing: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export const AnalysisResults: React.FC<AnalysisResultsProps> = ({
  result,
  progress,
  isAnalyzing,
}) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const copyToClipboard = async (text: string, index?: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index ?? 0);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const downloadJson = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // 분석 진행 중 UI
  if (isAnalyzing || progress) {
    return (
      <div className="w-full">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
          <div className="flex items-center justify-center mb-6">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
          
          {progress && (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm font-medium text-white mb-1">
                  <span>{progress.stage}</span>
                  <span>{progress.percentage}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress.percentage}%` }}
                  ></div>
                </div>
              </div>
              
              <p className="text-sm text-gray-400 text-center">
                {progress.message}
              </p>
            </div>
          )}
          
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-400">
              분석이 완료될 때까지 잠시만 기다려주세요...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // 결과 없음
  if (!result) {
    return (
      <div className="w-full">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-8 text-center">
          <InformationCircleIcon className="mx-auto h-12 w-12 text-gray-500 mb-4" />
          <p className="text-gray-400">
            비디오를 업로드하고 "Analyze" 버튼을 클릭하여 분석을 시작하세요.
          </p>
        </div>
      </div>
    );
  }

  // 에러 상태
  if (result.status === 'error') {
    return (
      <div className="w-full">
        <div className="bg-red-500/20 border border-red-400/50 rounded-lg p-6">
          <div className="flex items-center mb-4">
            <ExclamationTriangleIcon className="h-6 w-6 text-red-400 mr-2" />
            <h4 className="text-lg font-medium text-red-300">분석 실패</h4>
          </div>
          <p className="text-red-200">
            {result.error || '알 수 없는 오류가 발생했습니다.'}
          </p>
        </div>
      </div>
    );
  }

  // 성공 결과 표시
  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <CheckIcon className="h-5 w-5 text-green-400" />
          <span className="text-sm text-green-400">분석 완료</span>
        </div>
      </div>

      {/* 결과 메타데이터 */}
      <div className="bg-gray-800/50 rounded-lg p-4 mb-6 border border-gray-700/50">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">파일명:</span>
            <span className="ml-2 text-gray-200">{result.filename}</span>
          </div>
          <div>
            <span className="text-gray-400">분석 모드:</span>
            <span className="ml-2 text-gray-200">
              {result.analysis_mode === 'basic' ? '기본 테스트' : '전문 분석'}
            </span>
          </div>
          <div>
            <span className="text-gray-400">분석 시간:</span>
            <span className="ml-2 text-gray-200">
              {new Date(result.timestamp).toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-gray-400">결과 ID:</span>
            <span className="ml-2 text-gray-200 font-mono text-xs">{result.id}</span>
          </div>
        </div>
      </div>

      {/* 결과 내용 */}
      {result.analysis_mode === 'basic' && result.results?.basic_results ? (
        <Tab.Group>
          <Tab.List className="flex space-x-1 rounded-xl bg-gray-800/50 p-1 mb-4">
            {result.results.basic_results.map((_, index) => (
              <Tab
                key={index}
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
                결과 {index + 1}
              </Tab>
            ))}
          </Tab.List>
          <Tab.Panels>
            {result.results.basic_results.map((basicResult, index) => (
              <Tab.Panel key={index} className="rounded-xl">
                <div className="border border-gray-700/50 rounded-lg bg-gray-800/30">
                  <div className="bg-gray-800/50 px-4 py-3 border-b border-gray-700/50 flex justify-between items-center rounded-t-lg">
                    <h4 className="text-sm font-medium text-white">
                      프롬프트 {index + 1}
                    </h4>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => copyToClipboard(basicResult.response, index)}
                        className="inline-flex items-center px-2 py-1 border border-gray-600/50 shadow-sm text-xs font-medium rounded text-gray-300 bg-gray-800/70 hover:bg-gray-700/90 transition-colors"
                      >
                        {copiedIndex === index ? (
                          <>
                            <CheckIcon className="h-3 w-3 mr-1" />
                            복사됨
                          </>
                        ) : (
                          <>
                            <ClipboardDocumentIcon className="h-3 w-3 mr-1" />
                            복사
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => downloadJson(basicResult, `analysis_result_${index + 1}.json`)}
                        className="inline-flex items-center px-2 py-1 border border-gray-600/50 shadow-sm text-xs font-medium rounded text-gray-300 bg-gray-800/70 hover:bg-gray-700/90 transition-colors"
                      >
                        <DocumentArrowDownIcon className="h-3 w-3 mr-1" />
                        다운로드
                      </button>
                    </div>
                  </div>
                  
                  <div className="p-4">
                    <div className="mb-4">
                      <h5 className="text-xs font-medium text-gray-400 mb-2">프롬프트:</h5>
                      <p className="text-sm text-gray-300 bg-gray-800/50 p-3 rounded border border-gray-700/50">
                        {basicResult.prompt}
                      </p>
                    </div>
                    
                    <div>
                      <h5 className="text-xs font-medium text-gray-400 mb-2">응답:</h5>
                      <div className="bg-gray-800/50 p-3 rounded max-h-96 overflow-y-auto border border-gray-700/50">
                        <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                          {basicResult.response}
                        </pre>
                      </div>
                    </div>
                  </div>
                </div>
              </Tab.Panel>
            ))}
          </Tab.Panels>
        </Tab.Group>
      ) : result.analysis_mode === 'professional' && result.results?.professional_result ? (
        <div className="border border-gray-700/50 rounded-lg bg-gray-800/30">
          <div className="bg-gray-800/50 px-4 py-3 border-b border-gray-700/50 flex justify-between items-center rounded-t-lg">
            <h4 className="text-sm font-medium text-white">전문 분석 결과</h4>
            <div className="flex space-x-2">
              <button
                onClick={() => copyToClipboard(JSON.stringify(result.results?.professional_result, null, 2))}
                className="inline-flex items-center px-2 py-1 border border-gray-600/50 shadow-sm text-xs font-medium rounded text-gray-300 bg-gray-800/70 hover:bg-gray-700/90 transition-colors"
              >
                {copiedIndex === 0 ? (
                  <>
                    <CheckIcon className="h-3 w-3 mr-1" />
                    복사됨
                  </>
                ) : (
                  <>
                    <ClipboardDocumentIcon className="h-3 w-3 mr-1" />
                    복사
                  </>
                )}
              </button>
              <button
                onClick={() => downloadJson(result.results?.professional_result, 'professional_analysis_result.json')}
                className="inline-flex items-center px-2 py-1 border border-gray-600/50 shadow-sm text-xs font-medium rounded text-gray-300 bg-gray-800/70 hover:bg-gray-700/90 transition-colors"
              >
                <DocumentArrowDownIcon className="h-3 w-3 mr-1" />
                다운로드
              </button>
            </div>
          </div>
          
          <div className="p-4">
            <div className="bg-gray-800/50 p-3 rounded max-h-96 overflow-y-auto border border-gray-700/50">
              <pre className="text-sm text-gray-300">
                {JSON.stringify(result.results.professional_result, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-500/20 border border-yellow-400/50 rounded-lg p-4">
          <p className="text-yellow-200">결과 데이터를 표시할 수 없습니다.</p>
        </div>
      )}
    </div>
  );
};
