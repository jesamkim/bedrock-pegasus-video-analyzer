#!/usr/bin/env python3
"""
Amazon Bedrock TwelveLabs Pegasus 1.2 Video Analysis Test ✅
S3 MP4 영상을 분석하는 성공한 테스트 스크립트 - 자동 실행 및 JSON 출력
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
        AWS_REGION, PEGASUS_MODEL_ID, DEFAULT_TEST_PROMPTS,
        TEST_VIDEO_COMPRESSION_SETTINGS, OUTPUT_SETTINGS, DEFAULT_S3_URIS
    )
except ImportError:
    print("❌ config.py 파일을 찾을 수 없습니다. config.py 파일이 같은 디렉토리에 있는지 확인하세요.")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BedrockPegasusTest:
    def __init__(self, region=None):
        """
        Bedrock Pegasus 테스트 클래스 초기화
        
        Args:
            region (str): AWS 리전 (기본값: config.py의 AWS_REGION)
        """
        self.region = region or AWS_REGION
        self.model_id = PEGASUS_MODEL_ID
        self.compression_settings = TEST_VIDEO_COMPRESSION_SETTINGS
        
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
            logger.info(f"사용할 모델 ID: {self.model_id}")
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

    def analyze_video_with_invoke_api(self, video_base64, prompt):
        """
        Invoke API를 사용하여 비디오 분석 (Inference Profile 사용)
        
        Args:
            video_base64 (str): base64 인코딩된 비디오 데이터
            prompt (str): 분석 프롬프트
            
        Returns:
            dict: Bedrock 응답
        """
        try:
            logger.info("Invoke API로 비디오 분석 시작...")
            
            request_body = {
                "inputPrompt": prompt,
                "mediaSource": {
                    "base64String": video_base64
                }
            }
            
            # 요청 크기 확인
            request_size_mb = len(json.dumps(request_body)) / (1024 * 1024)
            logger.info(f"요청 크기: {request_size_mb:.2f} MB")
            
            # Inference Profile ID 사용
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            logger.info("✅ 비디오 분석 완료!")
            
            return response_body
            
        except Exception as e:
            logger.error(f"Invoke API 비디오 분석 실패: {str(e)}")
            raise

    def run_single_test(self, s3_uri, prompt, test_number):
        """
        단일 테스트 실행 (JSON 결과 반환용)
        
        Args:
            s3_uri (str): S3 비디오 URI
            prompt (str): 분석 프롬프트
            test_number (int): 테스트 번호
            
        Returns:
            dict: 테스트 결과
        """
        try:
            logger.info(f"=== 테스트 {test_number} 시작 ===")
            logger.info(f"프롬프트: {prompt}")
            
            # 비디오 분석
            response = self.analyze_video_with_invoke_api(self.video_base64, prompt)
            
            # 결과 구조화
            result = {
                "test_number": test_number,
                "prompt": prompt,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "response": {
                    "message": response.get('message', ''),
                    "stopReason": response.get('stopReason', ''),
                    "raw_response": response
                }
            }
            
            logger.info(f"✅ 테스트 {test_number} 성공!")
            return result
            
        except Exception as e:
            logger.error(f"❌ 테스트 {test_number} 실패: {str(e)}")
            return {
                "test_number": test_number,
                "prompt": prompt,
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    def run_all_tests(self, s3_uri, test_prompts=None):
        """
        모든 테스트를 자동으로 실행하고 결과를 JSON으로 저장
        
        Args:
            s3_uri (str): S3 비디오 URI
            test_prompts (list): 테스트 프롬프트 목록
            
        Returns:
            dict: 전체 테스트 결과
        """
        if test_prompts is None:
            test_prompts = DEFAULT_TEST_PROMPTS
            
        try:
            logger.info("=== Bedrock Pegasus 1.2 자동 비디오 분석 테스트 시작 ===")
            logger.info(f"S3 URI: {s3_uri}")
            logger.info(f"Inference Profile ID: {self.model_id}")
            logger.info(f"총 테스트 수: {len(test_prompts)}")
            
            # 1. 비디오 다운로드 및 준비 (한 번만 수행)
            logger.info("🎬 비디오 다운로드 및 준비 중...")
            self.video_base64 = self.download_and_prepare_video(s3_uri)
            
            # 2. 전체 결과 구조 초기화
            overall_result = {
                "test_session": {
                    "timestamp": datetime.now().isoformat(),
                    "s3_uri": s3_uri,
                    "model_id": self.model_id,
                    "region": self.region,
                    "total_tests": len(test_prompts)
                },
                "test_results": [],
                "summary": {
                    "successful_tests": 0,
                    "failed_tests": 0,
                    "total_execution_time": None
                }
            }
            
            start_time = datetime.now()
            
            # 3. 각 테스트 자동 실행
            for i, prompt in enumerate(test_prompts, 1):
                print(f"\n{'🎯'*10} 테스트 {i}/{len(test_prompts)} {'🎯'*10}")
                print(f"📋 프롬프트: {prompt}")
                print("-"*80)
                
                # 테스트 실행
                result = self.run_single_test(s3_uri, prompt, i)
                overall_result["test_results"].append(result)
                
                # 결과 출력
                if result["status"] == "success":
                    overall_result["summary"]["successful_tests"] += 1
                    print(f"📝 응답: {result['response']['message']}")
                    print(f"✅ 테스트 {i} 성공!")
                else:
                    overall_result["summary"]["failed_tests"] += 1
                    print(f"❌ 테스트 {i} 실패: {result['error']}")
                
                print("-"*80)
            
            # 4. 실행 시간 계산
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            overall_result["summary"]["total_execution_time"] = f"{execution_time:.2f} seconds"
            
            logger.info("=== 모든 테스트 완료 ===")
            return overall_result
            
        except Exception as e:
            logger.error(f"전체 테스트 실행 실패: {str(e)}")
            raise

    def save_results_to_json(self, results, output_file=None):
        """
        테스트 결과를 JSON 파일로 저장
        
        Args:
            results (dict): 테스트 결과
            output_file (str): 출력 파일명 (기본값: 자동 생성)
        """
        try:
            if output_file is None:
                timestamp = datetime.now().strftime(OUTPUT_SETTINGS["timestamp_format"])
                output_file = f"{OUTPUT_SETTINGS['test_results_prefix']}_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 테스트 결과가 저장되었습니다: {output_file}")
            print(f"\n📄 테스트 결과 파일: {output_file}")
            
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
    parser = argparse.ArgumentParser(description='Amazon Bedrock TwelveLabs Pegasus 1.2 Video Analysis Test')
    parser.add_argument('--s3-uri', type=str, help='S3 URI of the video to analyze')
    parser.add_argument('--region', type=str, help=f'AWS region (default: {AWS_REGION})')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode for S3 URI input')
    
    args = parser.parse_args()
    
    try:
        print("🚀 Amazon Bedrock TwelveLabs Pegasus 1.2 자동 테스트 시작!")
        print("="*80)
        
        # S3 URI 결정
        if args.s3_uri:
            s3_uri = args.s3_uri
        elif args.interactive or not args.s3_uri:
            s3_uri = get_s3_uri_from_user()
        else:
            s3_uri = DEFAULT_S3_URIS[0]  # 기본값
        
        print(f"📹 비디오: {s3_uri}")
        print(f"🤖 모델: TwelveLabs Pegasus 1.2")
        print(f"📊 테스트 수: {len(DEFAULT_TEST_PROMPTS)}")
        print("="*80)
        
        # 테스트 인스턴스 생성
        tester = BedrockPegasusTest(region=args.region)
        
        # 모든 테스트 자동 실행
        results = tester.run_all_tests(s3_uri)
        
        # JSON 파일로 저장
        output_file = tester.save_results_to_json(results)
        
        # 요약 출력
        print(f"\n{'🎉'*40}")
        print("🎊 모든 테스트가 완료되었습니다! 🎊")
        print(f"{'🎉'*40}")
        print(f"📊 성공: {results['summary']['successful_tests']}/{results['test_session']['total_tests']}")
        print(f"⏱️  실행 시간: {results['summary']['total_execution_time']}")
        print(f"📄 결과 파일: {output_file}")
        print(f"{'🎉'*40}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        logger.error(f"메인 실행 오류: {str(e)}")
        print(f"\n❌ 오류 발생: {str(e)}")
        print("\n🔧 해결 방법:")
        print("1. AWS 자격 증명 확인: aws configure list")
        print("2. Bedrock 모델 액세스 권한 확인")
        print("3. S3 버킷 및 객체 액세스 권한 확인")
        print("4. ffmpeg 설치 확인: ffmpeg -version")
        print("5. 네트워크 연결 상태 확인")
        print("6. config.py 파일 존재 여부 확인")


if __name__ == "__main__":
    main()
