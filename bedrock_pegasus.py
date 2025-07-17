#!/usr/bin/env python3
"""
Amazon Bedrock TwelveLabs Pegasus 1.2 + Claude 3.7 Sonnet 비디오 분석
S3 MP4 영상을 Pegasus로 분석하고 Claude로 카테고라이징하여 JSON 저장
"""

import boto3
import json
import base64
import tempfile
import subprocess
import os
import sys
import argparse
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
import logging

# 설정 파일 import
try:
    from config import (
        AWS_REGION, PEGASUS_MODEL_ID, CLAUDE_MODEL_ID, 
        PROFESSIONAL_ANALYSIS_PROMPT, VIDEO_COMPRESSION_SETTINGS,
        OUTPUT_SETTINGS, DEFAULT_S3_URIS
    )
except ImportError:
    print("❌ config.py 파일을 찾을 수 없습니다. config.py 파일이 같은 디렉토리에 있는지 확인하세요.")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BedrockPegasusAnalyzer:
    def __init__(self, region=None):
        """
        Bedrock Pegasus + Claude 분석기 초기화
        
        Args:
            region (str): AWS 리전 (기본값: config.py의 AWS_REGION)
        """
        self.region = region or AWS_REGION
        self.pegasus_model_id = PEGASUS_MODEL_ID
        self.claude_model_id = CLAUDE_MODEL_ID
        self.compression_settings = VIDEO_COMPRESSION_SETTINGS
        
        # AWS 클라이언트 초기화
        try:
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.region
            )
            self.s3_client = boto3.client(
                service_name='s3',
                region_name=self.region
            )
            logger.info(f"AWS 클라이언트 초기화 완료 (리전: {self.region})")
            logger.info(f"Pegasus 모델 ID: {self.pegasus_model_id}")
            logger.info(f"Claude 모델 ID: {self.claude_model_id}")
        except NoCredentialsError:
            logger.error("AWS 자격 증명을 찾을 수 없습니다. AWS CLI 설정을 확인하세요.")
            raise
        except Exception as e:
            logger.error(f"AWS 클라이언트 초기화 실패: {str(e)}")
            raise

    def compress_video_if_needed(self, input_path):
        """
        비디오 파일이 너무 크면 압축
        
        Args:
            input_path (str): 입력 비디오 파일 경로
            
        Returns:
            str: 압축된 비디오 파일 경로
        """
        try:
            settings = self.compression_settings
            max_size_mb = settings["max_size_mb"]
            
            # 파일 크기 확인
            file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
            logger.info(f"원본 비디오 크기: {file_size_mb:.2f} MB")
            
            if file_size_mb <= max_size_mb:
                logger.info("압축이 필요하지 않습니다.")
                return input_path
            
            # ffmpeg 사용 가능 여부 확인
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("ffmpeg를 찾을 수 없습니다. 비디오 압축을 위해 ffmpeg 설치가 필요합니다.")
                logger.info("설치 방법: brew install ffmpeg (macOS) 또는 apt-get install ffmpeg (Ubuntu)")
                return input_path
            
            # 임시 출력 파일 생성
            output_path = input_path.replace('.mp4', '_compressed.mp4')
            
            # 압축 명령어 실행
            logger.info("비디오 압축 중... (시간이 걸릴 수 있습니다)")
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vcodec', 'libx264',
                '-crf', str(settings["crf"]),
                '-preset', settings["preset"],
                '-vf', f'scale={settings["resolution"]}',
                '-r', str(settings["framerate"]),
                '-t', str(settings["duration_seconds"]),
                '-y',  # 덮어쓰기
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                compressed_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"압축 완료! 압축된 크기: {compressed_size_mb:.2f} MB")
                return output_path
            else:
                logger.error(f"비디오 압축 실패: {result.stderr}")
                return input_path
                
        except Exception as e:
            logger.error(f"비디오 압축 중 오류: {str(e)}")
            return input_path

    def download_and_prepare_video(self, s3_uri):
        """
        S3에서 비디오를 다운로드하고 필요시 압축하여 base64로 인코딩
        
        Args:
            s3_uri (str): S3 URI
            
        Returns:
            str: base64 인코딩된 비디오 데이터
        """
        temp_file_path = None
        compressed_file_path = None
        
        try:
            # S3 URI 파싱
            if not s3_uri.startswith('s3://'):
                raise ValueError("올바른 S3 URI 형식이 아닙니다 (s3://bucket/key)")
            
            uri_parts = s3_uri[5:].split('/', 1)
            bucket = uri_parts[0]
            key = uri_parts[1] if len(uri_parts) > 1 else ''
            
            logger.info(f"S3에서 비디오 다운로드 중: {bucket}/{key}")
            
            # 임시 파일에 다운로드
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                self.s3_client.download_fileobj(bucket, key, temp_file)
                temp_file_path = temp_file.name
            
            # 파일 크기 확인 및 압축
            compressed_file_path = self.compress_video_if_needed(temp_file_path)
            
            # base64 인코딩
            with open(compressed_file_path, 'rb') as video_file:
                video_bytes = video_file.read()
                
            final_size_mb = len(video_bytes) / (1024 * 1024)
            logger.info(f"최종 비디오 크기: {final_size_mb:.2f} MB")
            
            if final_size_mb > 100:
                raise ValueError(f"비디오 크기가 여전히 너무 큽니다: {final_size_mb:.2f} MB > 100 MB")
            
            encoded_video = base64.b64encode(video_bytes).decode('utf-8')
            logger.info("비디오 base64 인코딩 완료")
            
            return encoded_video
            
        except Exception as e:
            logger.error(f"비디오 준비 실패: {str(e)}")
            raise
        finally:
            # 임시 파일 정리
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                if compressed_file_path and compressed_file_path != temp_file_path and os.path.exists(compressed_file_path):
                    os.unlink(compressed_file_path)
            except:
                pass

    def analyze_video_with_pegasus(self, video_base64, prompt=None):
        """
        Pegasus를 사용하여 비디오 분석
        
        Args:
            video_base64 (str): base64 인코딩된 비디오 데이터
            prompt (str): 분석 프롬프트 (기본값: config의 PROFESSIONAL_ANALYSIS_PROMPT)
            
        Returns:
            str: Pegasus 분석 결과 텍스트
        """
        if prompt is None:
            prompt = PROFESSIONAL_ANALYSIS_PROMPT
            
        try:
            logger.info("🎬 Pegasus로 비디오 분석 시작...")
            
            request_body = {
                "inputPrompt": prompt,
                "mediaSource": {
                    "base64String": video_base64
                }
            }
            
            # 요청 크기 확인
            request_size_mb = len(json.dumps(request_body)) / (1024 * 1024)
            logger.info(f"요청 크기: {request_size_mb:.2f} MB")
            
            # Pegasus 모델 호출
            response = self.bedrock_runtime.invoke_model(
                modelId=self.pegasus_model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            pegasus_output = response_body.get('message', '')
            
            logger.info("✅ Pegasus 비디오 분석 완료!")
            logger.info(f"Pegasus 출력 길이: {len(pegasus_output)} 문자")
            
            return pegasus_output
            
        except Exception as e:
            logger.error(f"Pegasus 비디오 분석 실패: {str(e)}")
            raise

    def categorize_with_claude(self, pegasus_output):
        """
        Claude 3.7 Sonnet을 사용하여 Pegasus 출력을 카테고라이징
        
        Args:
            pegasus_output (str): Pegasus 분석 결과
            
        Returns:
            dict: 카테고라이징된 JSON 결과
        """
        try:
            logger.info("🤖 Claude로 카테고라이징 시작...")
            
            # Claude용 프롬프트 생성
            claude_prompt = f"""
다음은 비디오 분석 AI(Pegasus)가 분석한 영상 내용입니다. 이 내용을 바탕으로 아래 JSON 형식으로 카테고라이징해주세요.

=== Pegasus 분석 결과 ===
{pegasus_output}

=== 요청사항 ===
위 분석 결과를 바탕으로 다음 JSON 형식으로 정리해주세요:

{{
  "video_type": "공사현장" | "교육영상" | "기타",
  "construction_info": {{
    "work_type": ["토공", "교량공", "도배공", "기타작업명"],
    "equipment": {{
      "excavator": 댓수,
      "loader": 댓수,
      "dump_truck": 댓수,
      "기타장비명": 댓수
    }},
    "filming_technique": ["Bird View", "Oblique View", "Tracking View", "CCTV", "1인칭", "360도", "기타기법"]
  }},
  "educational_info": {{
    "content_type": "교육내용설명",
    "subtitle_content": "자막내용요약",
    "slide_content": "슬라이드내용요약"
  }},
  "general_info": {{
    "duration_analyzed": "분석된시간",
    "main_activities": ["주요활동1", "주요활동2"],
    "key_observations": ["주요관찰사항1", "주요관찰사항2"]
  }},
  "confidence_score": 0.0-1.0,
  "summary": "전체요약"
}}

주의사항:
1. 공사현장이 아닌 경우 construction_info는 null로 설정
2. 교육영상이 아닌 경우 educational_info는 null로 설정
3. 확실하지 않은 정보는 "불명확" 또는 null로 표시
4. 장비 댓수는 정확한 숫자만 기입 (추정치는 "약 N대" 형식)
5. confidence_score는 분석 결과의 신뢰도 (0.0-1.0)

JSON만 응답해주세요:
"""

            # Claude 모델 호출
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": claude_prompt
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.1,
                "anthropic_version": "bedrock-2023-05-31"
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            claude_output = response_body['content'][0]['text']
            
            logger.info("✅ Claude 카테고라이징 완료!")
            
            # JSON 파싱 시도
            try:
                # JSON 부분만 추출 (```json 태그 제거)
                if '```json' in claude_output:
                    json_start = claude_output.find('```json') + 7
                    json_end = claude_output.find('```', json_start)
                    json_text = claude_output[json_start:json_end].strip()
                elif '{' in claude_output:
                    json_start = claude_output.find('{')
                    json_end = claude_output.rfind('}') + 1
                    json_text = claude_output[json_start:json_end]
                else:
                    json_text = claude_output
                
                categorized_result = json.loads(json_text)
                logger.info("✅ JSON 파싱 성공!")
                return categorized_result
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {str(e)}")
                logger.error(f"Claude 원본 출력: {claude_output}")
                # 파싱 실패 시 원본 텍스트 반환
                return {
                    "error": "JSON 파싱 실패",
                    "raw_claude_output": claude_output,
                    "parse_error": str(e)
                }
            
        except Exception as e:
            logger.error(f"Claude 카테고라이징 실패: {str(e)}")
            raise

    def analyze_video(self, s3_uri, custom_prompt=None):
        """
        전체 비디오 분석 프로세스 실행
        
        Args:
            s3_uri (str): S3 비디오 URI
            custom_prompt (str): 사용자 정의 프롬프트 (선택사항)
            
        Returns:
            dict: 최종 분석 결과
        """
        try:
            logger.info("=== Pegasus + Claude 비디오 분석 시작 ===")
            logger.info(f"S3 URI: {s3_uri}")
            
            # 1. 비디오 다운로드 및 준비
            logger.info("📹 비디오 다운로드 및 준비 중...")
            video_base64 = self.download_and_prepare_video(s3_uri)
            
            # 2. Pegasus로 비디오 분석
            pegasus_result = self.analyze_video_with_pegasus(video_base64, custom_prompt)
            
            # 3. Claude로 카테고라이징
            categorized_result = self.categorize_with_claude(pegasus_result)
            
            # 4. 최종 결과 구성
            final_result = {
                "analysis_session": {
                    "timestamp": datetime.now().isoformat(),
                    "s3_uri": s3_uri,
                    "pegasus_model_id": self.pegasus_model_id,
                    "claude_model_id": self.claude_model_id,
                    "region": self.region,
                    "custom_prompt_used": custom_prompt is not None
                },
                "pegasus_raw_output": pegasus_result,
                "categorized_analysis": categorized_result,
                "processing_info": {
                    "pegasus_output_length": len(pegasus_result),
                    "analysis_completed": True
                }
            }
            
            logger.info("=== 전체 분석 완료 ===")
            return final_result
            
        except Exception as e:
            logger.error(f"비디오 분석 실패: {str(e)}")
            raise

    def save_results_to_json(self, results, output_file=None):
        """
        분석 결과를 JSON 파일로 저장
        
        Args:
            results (dict): 분석 결과
            output_file (str): 출력 파일명 (기본값: 자동 생성)
            
        Returns:
            str: 저장된 파일명
        """
        try:
            if output_file is None:
                timestamp = datetime.now().strftime(OUTPUT_SETTINGS["timestamp_format"])
                output_file = f"{OUTPUT_SETTINGS['analysis_results_prefix']}_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 분석 결과가 저장되었습니다: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"JSON 파일 저장 실패: {str(e)}")
            raise


def get_s3_uri_from_user():
    """사용자로부터 S3 URI 입력 받기"""
    print("\n📹 비디오 입력 방법을 선택하세요:")
    print("1. S3 URI 직접 입력")
    print("2. 기본 예시 중 선택")
    
    while True:
        choice = input("\n선택 (1 또는 2): ").strip()
        
        if choice == "1":
            while True:
                s3_uri = input("\nS3 URI를 입력하세요 (예: s3://bucket/path/video.mp4): ").strip()
                if s3_uri.startswith('s3://') and s3_uri.count('/') >= 3:
                    return s3_uri
                else:
                    print("❌ 올바른 S3 URI 형식이 아닙니다. 다시 입력해주세요.")
        
        elif choice == "2":
            print("\n기본 예시 비디오:")
            for i, uri in enumerate(DEFAULT_S3_URIS, 1):
                print(f"{i}. {uri}")
            
            while True:
                try:
                    idx = int(input(f"\n선택 (1-{len(DEFAULT_S3_URIS)}): ").strip()) - 1
                    if 0 <= idx < len(DEFAULT_S3_URIS):
                        return DEFAULT_S3_URIS[idx]
                    else:
                        print(f"❌ 1부터 {len(DEFAULT_S3_URIS)} 사이의 숫자를 입력해주세요.")
                except ValueError:
                    print("❌ 숫자를 입력해주세요.")
        
        else:
            print("❌ 1 또는 2를 입력해주세요.")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='Amazon Bedrock TwelveLabs Pegasus 1.2 + Claude 3.7 Sonnet Video Analysis')
    parser.add_argument('--s3-uri', type=str, help='S3 URI of the video to analyze')
    parser.add_argument('--region', type=str, help=f'AWS region (default: {AWS_REGION})')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode for S3 URI input')
    parser.add_argument('--custom-prompt', type=str, help='Custom analysis prompt (overrides default)')
    
    args = parser.parse_args()
    
    try:
        print("🚀 Pegasus + Claude 3.7 Sonnet 비디오 분석 시작!")
        print("="*80)
        
        # S3 URI 결정
        if args.s3_uri:
            s3_uri = args.s3_uri
        elif args.interactive or not args.s3_uri:
            s3_uri = get_s3_uri_from_user()
        else:
            s3_uri = DEFAULT_S3_URIS[0]  # 기본값
        
        print(f"📹 비디오: {s3_uri}")
        print(f"🎬 1단계: TwelveLabs Pegasus 1.2 - 비디오 분석")
        print(f"🤖 2단계: Claude 3.7 Sonnet - 카테고라이징")
        if args.custom_prompt:
            print(f"📝 사용자 정의 프롬프트 사용")
        print("="*80)
        
        # 분석기 인스턴스 생성
        analyzer = BedrockPegasusAnalyzer(region=args.region)
        
        # 비디오 분석 실행
        results = analyzer.analyze_video(s3_uri, args.custom_prompt)
        
        # JSON 파일로 저장
        output_file = analyzer.save_results_to_json(results)
        
        # 결과 요약 출력
        print(f"\n{'🎉'*40}")
        print("🎊 비디오 분석이 완료되었습니다! 🎊")
        print(f"{'🎉'*40}")
        
        # 카테고라이징 결과 미리보기
        if 'categorized_analysis' in results and 'error' not in results['categorized_analysis']:
            cat_result = results['categorized_analysis']
            print(f"📊 비디오 유형: {cat_result.get('video_type', '불명')}")
            if cat_result.get('video_type') == '공사현장':
                print(f"🏗️  작업 유형: {', '.join(cat_result.get('construction_info', {}).get('work_type', []))}")
                equipment = cat_result.get('construction_info', {}).get('equipment', {})
                if equipment:
                    print(f"🚜 투입 장비: {', '.join([f'{k}({v}대)' for k, v in equipment.items() if v > 0])}")
            print(f"📝 요약: {cat_result.get('summary', '요약 없음')[:100]}...")
        
        print(f"📄 상세 결과 파일: {output_file}")
        print(f"{'🎉'*40}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 분석이 중단되었습니다.")
    except Exception as e:
        logger.error(f"메인 실행 오류: {str(e)}")
        print(f"\n❌ 오류 발생: {str(e)}")
        print("\n🔧 해결 방법:")
        print("1. AWS 자격 증명 확인: aws configure list")
        print("2. Bedrock 모델 액세스 권한 확인 (Pegasus + Claude)")
        print("3. S3 버킷 및 객체 액세스 권한 확인")
        print("4. ffmpeg 설치 확인: ffmpeg -version")
        print("5. 네트워크 연결 상태 확인")
        print("6. config.py 파일 존재 여부 확인")


if __name__ == "__main__":
    main()
