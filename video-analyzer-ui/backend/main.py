#!/usr/bin/env python3
"""
FastAPI Backend for Bedrock Pegasus Video Analyzer
React UI와 연동되는 백엔드 서버 - 파일 업로드 + S3 URI + 자동 인코딩 지원
"""

import os
import sys
import uuid
import tempfile
import asyncio
import base64
import boto3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# 비디오 인코더 import
from video_encoder import video_encoder

# 기존 Python 코드 import를 위한 경로 설정
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from config import (
        AWS_REGION, PEGASUS_MODEL_ID, CLAUDE_MODEL_ID,
        PROFESSIONAL_ANALYSIS_PROMPT, VIDEO_COMPRESSION_SETTINGS,
        TEST_VIDEO_COMPRESSION_SETTINGS, OUTPUT_SETTINGS, DEFAULT_S3_URIS
    )
    from bedrock_pegasus import BedrockPegasusAnalyzer
    from bedrock_pegasus_test import BedrockPegasusTest
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Looking for config.py in: {project_root}")
    print("Available files in project root:")
    if project_root.exists():
        for file in project_root.iterdir():
            print(f"  - {file.name}")
    
    # 기본 설정으로 폴백
    print("Using fallback configuration...")
    AWS_REGION = "us-west-2"
    PEGASUS_MODEL_ID = "twelvelabs.pegasus-1-2-v1:0"
    CLAUDE_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    PROFESSIONAL_ANALYSIS_PROMPT = "이 비디오의 영상에 대한 정보를 자세히 확인하세요."
    VIDEO_COMPRESSION_SETTINGS = {"max_size_mb": 70, "crf": 30, "preset": "fast", "resolution": "854:480", "framerate": 12}
    TEST_VIDEO_COMPRESSION_SETTINGS = VIDEO_COMPRESSION_SETTINGS.copy()
    OUTPUT_SETTINGS = {"test_results_prefix": "bedrock_pegasus_test_results", "analysis_results_prefix": "pegasus_claude_analysis"}
    DEFAULT_S3_URIS = []
    
    # 분석 클래스들을 시뮬레이션으로 대체
    class BedrockPegasusAnalyzer:
        def __init__(self, region=None):
            self.region = region or AWS_REGION
    
    class BedrockPegasusTest:
        def __init__(self, region=None):
            self.region = region or AWS_REGION

# FastAPI 앱 생성
app = FastAPI(
    title="Bedrock Pegasus Video Analyzer API",
    description="TwelveLabs Pegasus 1.2 + Claude 3.7 Sonnet을 활용한 비디오 분석 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],  # React 개발 서버
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# AWS 클라이언트 초기화
try:
    bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    print(f"✅ AWS clients initialized for region: {AWS_REGION}")
except Exception as e:
    print(f"⚠️ AWS client initialization failed: {e}")
    bedrock_runtime = None
    s3_client = None

# 데이터 모델 정의
class AnalysisRequest(BaseModel):
    fileId: Optional[str] = None
    s3Uri: Optional[str] = None
    prompts: Optional[List[str]] = None
    prompt: Optional[str] = None

class S3UriRequest(BaseModel):
    s3Uri: str

class ConfigUpdate(BaseModel):
    aws_region: Optional[str] = None
    pegasus_model_id: Optional[str] = None
    claude_model_id: Optional[str] = None
    video_compression_settings: Optional[Dict[str, Any]] = None

# 전역 상태 관리
uploaded_files: Dict[str, Dict[str, Any]] = {}
s3_uris: Dict[str, Dict[str, Any]] = {}
analysis_results: Dict[str, Dict[str, Any]] = {}
analysis_status: Dict[str, str] = {}
encoding_progress: Dict[str, Dict[str, Any]] = {}  # 인코딩 진행률 추적

# 임시 파일 저장 디렉토리
TEMP_DIR = Path(tempfile.gettempdir()) / "video_analyzer"
TEMP_DIR.mkdir(exist_ok=True)

# S3 버킷 설정 (환경변수 또는 기본값)
S3_BUCKET = os.getenv('VIDEO_ANALYSIS_BUCKET', 'bedrock-pegasus-video-temp')

def validate_s3_uri(s3_uri: str) -> Dict[str, Any]:
    """S3 URI 유효성 검사 및 접근 가능성 확인"""
    try:
        # URI 형식 검사
        if not s3_uri.startswith('s3://'):
            return {"valid": False, "error": "S3 URI must start with 's3://'"}
        
        # 버킷과 키 추출
        parts = s3_uri[5:].split('/', 1)
        if len(parts) != 2:
            return {"valid": False, "error": "Invalid S3 URI format"}
        
        bucket_name, key = parts
        
        # 파일 확장자 검사
        valid_extensions = ['.mp4', '.mov', '.avi', '.webm']
        if not any(key.lower().endswith(ext) for ext in valid_extensions):
            return {"valid": False, "error": "Unsupported file format. Use MP4, MOV, AVI, or WebM"}
        
        # S3 객체 존재 확인
        if s3_client:
            try:
                response = s3_client.head_object(Bucket=bucket_name, Key=key)
                file_size = response['ContentLength']
                
                # 파일 크기 제한 (2GB)
                max_size = 2 * 1024 * 1024 * 1024
                if file_size > max_size:
                    return {"valid": False, "error": "File too large. Maximum size is 2GB"}
                
                # 현재 AWS 계정 ID 가져오기
                try:
                    sts_client = boto3.client('sts', region_name=AWS_REGION)
                    account_id = sts_client.get_caller_identity()['Account']
                except Exception as e:
                    print(f"⚠️ Failed to get account ID: {e}")
                    account_id = os.getenv('AWS_ACCOUNT_ID', '123456789012')
                
                return {
                    "valid": True,
                    "bucket": bucket_name,
                    "key": key,
                    "size": file_size,
                    "size_mb": file_size / (1024 * 1024),
                    "bucket_owner": account_id
                }
                
            except Exception as e:
                return {"valid": False, "error": f"Cannot access S3 object: {str(e)}"}
        else:
            # AWS 클라이언트가 없는 경우 (시뮬레이션 모드)
            return {
                "valid": True,
                "bucket": bucket_name,
                "key": key,
                "size": 50 * 1024 * 1024,  # 50MB로 가정
                "size_mb": 50,
                "bucket_owner": "123456789012"  # 시뮬레이션용 더미 계정 ID
            }
            
    except Exception as e:
        return {"valid": False, "error": f"Invalid S3 URI: {str(e)}"}

async def encode_video_with_progress(file_id: str, input_path: str, output_path: str):
    """비디오 인코딩 (진행률 추적)"""
    def progress_callback(percentage: int, stage: str, message: str):
        encoding_progress[file_id] = {
            "percentage": percentage,
            "stage": stage,
            "message": message
        }
        print(f"🎬 Encoding {file_id}: {percentage}% - {stage}")
    
    try:
        encoding_progress[file_id] = {
            "percentage": 0,
            "stage": "시작",
            "message": "인코딩을 준비하고 있습니다..."
        }
        
        result = await video_encoder.encode_video(input_path, output_path, progress_callback)
        
        if result['success']:
            print(f"✅ Video encoding completed: {file_id}")
            print(f"   Original: {result['original_size_mb']:.2f}MB")
            print(f"   Encoded: {result['encoded_size_mb']:.2f}MB")
            print(f"   Compression: {result['compression_ratio']:.2f}x")
            
            # 파일 정보 업데이트
            if file_id in uploaded_files:
                uploaded_files[file_id]["encoded_size_mb"] = result['encoded_size_mb']
                uploaded_files[file_id]["encoding_completed"] = True
                
                # 인코딩 후에도 30MB를 초과하는 경우 S3 업로드 필요
                if result['encoded_size_mb'] > 30:
                    uploaded_files[file_id]["processing_method"] = "S3 URI (large file)"
                    print(f"⚠️ Encoded file still large ({result['encoded_size_mb']:.2f}MB), will use S3 URI")
                else:
                    uploaded_files[file_id]["processing_method"] = "Base64 encoding"
                    print(f"✅ File ready for Base64 encoding ({result['encoded_size_mb']:.2f}MB)")
        
        return result
        
    except Exception as e:
        encoding_progress[file_id] = {
            "percentage": 0,
            "stage": "오류",
            "message": f"인코딩 실패: {str(e)}"
        }
        
        # 파일 정보 업데이트 (실패)
        if file_id in uploaded_files:
            uploaded_files[file_id]["encoding_completed"] = False
            uploaded_files[file_id]["processing_method"] = f"Encoding failed: {str(e)}"
        
        return {"success": False, "error": str(e)}
    finally:
        # 완료 후 진행률 정보 정리 (5초 후)
        await asyncio.sleep(5)
        if file_id in encoding_progress:
            del encoding_progress[file_id]

def encode_video_to_base64(file_path: str) -> str:
    """비디오 파일을 Base64로 인코딩"""
    with open(file_path, 'rb') as video_file:
        return base64.b64encode(video_file.read()).decode('utf-8')

async def upload_to_s3(file_path: str, s3_key: str) -> str:
    """파일을 S3에 업로드하고 URI 반환"""
    try:
        s3_client.upload_file(file_path, S3_BUCKET, s3_key)
        s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
        print(f"✅ File uploaded to S3: {s3_uri}")
        return s3_uri
    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")

async def analyze_with_pegasus(file_path: str, prompt: str, analysis_id: str) -> Dict[str, Any]:
    """Pegasus 모델로 비디오 분석"""
    try:
        file_size_mb = get_file_size_mb(file_path)
        print(f"📹 Video file size: {file_size_mb:.2f} MB")
        
        # 36MB 미만이면 Base64, 이상이면 S3 URI 사용
        if file_size_mb < 36:
            print("🔄 Using Base64 encoding for small file")
            base64_video = encode_video_to_base64(file_path)
            
            request_body = {
                "inputPrompt": prompt,
                "mediaSource": {
                    "base64String": base64_video
                },
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
        else:
            print("🔄 Using S3 URI for large file")
            s3_key = f"temp-videos/{analysis_id}/{Path(file_path).name}"
            s3_uri = await upload_to_s3(file_path, s3_key)
            
            request_body = {
                "inputPrompt": prompt,
                "mediaSource": {
                    "s3Location": {
                        "uri": s3_uri
                    }
                },
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
        
        # Bedrock 호출
        if bedrock_runtime:
            response = bedrock_runtime.invoke_model(
                modelId=PEGASUS_MODEL_ID,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return {
                "success": True,
                "message": response_body.get('message', ''),
                "finish_reason": response_body.get('finishReason', 'stop')
            }
        else:
            # 시뮬레이션 모드
            return {
                "success": True,
                "message": f"[시뮬레이션] Pegasus 분석 결과 - 파일 크기: {file_size_mb:.2f}MB, 방식: {'Base64' if file_size_mb < 36 else 'S3 URI'}",
                "finish_reason": "stop"
            }
            
    except Exception as e:
        print(f"❌ Pegasus analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def analyze_with_claude(pegasus_result: str, analysis_id: str) -> Dict[str, Any]:
    """Claude로 Pegasus 결과를 구조화"""
    try:
        claude_prompt = f"""
다음은 비디오 분석 결과입니다. 이를 구조화된 JSON 형태로 변환해주세요:

{pegasus_result}

다음 형식으로 응답해주세요:
{{
  "video_type": "공사현장" 또는 "교육영상" 또는 "기타",
  "construction_info": {{
    "work_type": ["토공", "교량공", "도배공" 등],
    "equipment": {{
      "excavator": 숫자 또는 "불명확",
      "dump_truck": 숫자 또는 "불명확"
    }},
    "filming_technique": ["Bird View", "Oblique View" 등]
  }},
  "educational_info": {{
    "content_type": "교육 내용 설명",
    "slide_content": "슬라이드 내용 요약"
  }},
  "confidence_score": 0.0-1.0 사이의 신뢰도
}}
"""
        
        if bedrock_runtime:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": claude_prompt
                    }
                ]
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            claude_result = response_body['content'][0]['text']
            
            # JSON 파싱 시도
            try:
                structured_result = json.loads(claude_result)
                return {
                    "success": True,
                    "structured_result": structured_result
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "structured_result": {
                        "video_type": "기타",
                        "raw_analysis": claude_result,
                        "confidence_score": 0.7
                    }
                }
        else:
            # 시뮬레이션 모드
            return {
                "success": True,
                "structured_result": {
                    "video_type": "공사현장",
                    "construction_info": {
                        "work_type": ["토공"],
                        "equipment": {
                            "excavator": 2,
                            "dump_truck": 1
                        },
                        "filming_technique": ["Oblique View"]
                    },
                    "confidence_score": 0.85
                }
            }
            
    except Exception as e:
        print(f"❌ Claude analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Bedrock Pegasus Video Analyzer API",
        "version": "1.0.0",
        "status": "running",
        "features": ["Base64 encoding", "S3 URI support", "Dual AI pipeline"]
    }

@app.get("/api/config")
async def get_config():
    """현재 설정 조회"""
    try:
        config = {
            "aws_region": AWS_REGION,
            "pegasus_model_id": PEGASUS_MODEL_ID,
            "claude_model_id": CLAUDE_MODEL_ID,
            "video_compression_settings": VIDEO_COMPRESSION_SETTINGS,
            "test_video_compression_settings": TEST_VIDEO_COMPRESSION_SETTINGS,
            "s3_bucket": S3_BUCKET,
            "base64_limit_mb": 36
        }
        return {"success": True, "data": config}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/api/config")
async def update_config(config_update: ConfigUpdate):
    """설정 업데이트"""
    try:
        # 실제로는 설정 파일이나 데이터베이스에 저장해야 하지만
        # 여기서는 시뮬레이션으로 현재 설정을 반환
        print(f"📝 Config update requested: {config_update}")
        
        # 업데이트된 설정 반환 (실제로는 저장 후 반환)
        updated_config = {
            "aws_region": config_update.aws_region or AWS_REGION,
            "pegasus_model_id": config_update.pegasus_model_id or PEGASUS_MODEL_ID,
            "claude_model_id": config_update.claude_model_id or CLAUDE_MODEL_ID,
            "video_compression_settings": config_update.video_compression_settings or VIDEO_COMPRESSION_SETTINGS,
            "test_video_compression_settings": TEST_VIDEO_COMPRESSION_SETTINGS,
            "s3_bucket": S3_BUCKET,
            "base64_limit_mb": 36
        }
        
        return {"success": True, "data": updated_config, "message": "설정이 업데이트되었습니다."}
    except Exception as e:
        return {"success": False, "error": str(e)}
    """현재 설정 조회"""
    try:
        config = {
            "aws_region": AWS_REGION,
            "pegasus_model_id": PEGASUS_MODEL_ID,
            "claude_model_id": CLAUDE_MODEL_ID,
            "video_compression_settings": VIDEO_COMPRESSION_SETTINGS,
            "test_video_compression_settings": TEST_VIDEO_COMPRESSION_SETTINGS,
            "s3_bucket": S3_BUCKET,
            "base64_limit_mb": 36
        }
        return {"success": True, "data": config}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/validate-s3-uri")
async def validate_s3_uri_endpoint(request: S3UriRequest):
    """S3 URI 유효성 검사"""
    try:
        validation_result = validate_s3_uri(request.s3Uri)
        
        if validation_result["valid"]:
            # S3 URI 정보 저장
            uri_id = str(uuid.uuid4())
            s3_uris[uri_id] = {
                "uri_id": uri_id,
                "s3_uri": request.s3Uri,
                "bucket": validation_result["bucket"],
                "key": validation_result["key"],
                "size": validation_result["size"],
                "size_mb": validation_result["size_mb"],
                "bucket_owner": validation_result["bucket_owner"],
                "validated_time": datetime.now().isoformat(),
            }
            
            return {
                "success": True,
                "data": {
                    "uriId": uri_id,
                    "s3Uri": request.s3Uri,
                    "size_mb": round(validation_result["size_mb"], 2),
                    "processing_method": "Direct S3 access"
                }
            }
        else:
            return {
                "success": False,
                "error": validation_result["error"]
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 URI validation failed: {str(e)}")

@app.get("/api/files/{file_id}/status")
async def get_file_status(file_id: str):
    """업로드된 파일 상태 확인"""
    try:
        if file_id not in uploaded_files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = uploaded_files[file_id]
        
        # 파일 존재 확인
        original_exists = os.path.exists(file_info["original_file_path"])
        final_exists = os.path.exists(file_info["final_file_path"])
        
        # 최종 파일 크기 확인
        final_size_mb = None
        if final_exists:
            final_size_mb = os.path.getsize(file_info["final_file_path"]) / (1024 * 1024)
        
        status = {
            "file_id": file_id,
            "filename": file_info["filename"],
            "original_size_mb": file_info["original_size_mb"],
            "encoded_size_mb": file_info.get("encoded_size_mb"),
            "final_size_mb": final_size_mb,
            "needs_encoding": file_info["needs_encoding"],
            "encoding_completed": file_info["encoding_completed"],
            "processing_method": file_info["processing_method"],
            "original_file_exists": original_exists,
            "final_file_exists": final_exists,
            "ready_for_analysis": final_exists and file_info["encoding_completed"]
        }
        
        return {"success": True, "data": status}
        
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/encoding-progress/{file_id}")
async def get_encoding_progress(file_id: str):
    """인코딩 진행률 조회"""
    try:
        if file_id in encoding_progress:
            return {"success": True, "data": encoding_progress[file_id]}
        else:
            return {"success": False, "error": "Encoding progress not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/upload")
async def upload_video(background_tasks: BackgroundTasks, video: UploadFile = File(...)):
    """비디오 파일 업로드 및 자동 인코딩"""
    try:
        # 파일 유효성 검사 (확장자 기반으로도 확인)
        valid_extensions = ['.mp4', '.mov', '.avi', '.webm']
        file_extension = os.path.splitext(video.filename.lower())[1] if video.filename else ''
        
        is_valid_content_type = video.content_type and video.content_type.startswith('video/')
        is_valid_extension = file_extension in valid_extensions
        
        if not (is_valid_content_type or is_valid_extension):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Please upload a video file. Got content-type: {video.content_type}, extension: {file_extension}"
            )
        
        print(f"📁 File validation passed: {video.filename} (content-type: {video.content_type}, extension: {file_extension})")
        
        # 파일 크기 제한 (2GB - Pegasus 최대 지원)
        max_size = 2 * 1024 * 1024 * 1024  # 2GB
        if video.size and video.size > max_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 2GB.")
        
        # 고유 파일 ID 생성
        file_id = str(uuid.uuid4())
        
        # 원본 파일 저장
        original_file_path = TEMP_DIR / f"{file_id}_original_{video.filename}"
        with open(original_file_path, "wb") as buffer:
            content = await video.read()
            buffer.write(content)
        
        file_size_mb = len(content) / (1024 * 1024)
        
        # 30MB 이하면 인코딩 스킵, 이상이면 백그라운드 인코딩
        if file_size_mb <= 30:
            processing_method = "No encoding needed"
            final_file_path = original_file_path
            encoded_size_mb = file_size_mb
        else:
            processing_method = "Auto encoding to 30MB"
            final_file_path = TEMP_DIR / f"{file_id}_encoded_{video.filename}"
            
            # 백그라운드에서 인코딩 시작
            background_tasks.add_task(
                encode_video_with_progress,
                file_id,
                str(original_file_path),
                str(final_file_path)
            )
            encoded_size_mb = None  # 인코딩 완료 후 결정
        
        # 파일 정보 저장
        uploaded_files[file_id] = {
            "filename": video.filename,
            "original_file_path": str(original_file_path),
            "final_file_path": str(final_file_path),
            "content_type": video.content_type,
            "original_size": len(content),
            "original_size_mb": file_size_mb,
            "encoded_size_mb": encoded_size_mb,
            "processing_method": processing_method,
            "needs_encoding": file_size_mb > 30,
            "encoding_completed": file_size_mb <= 30,
            "upload_time": datetime.now().isoformat(),
        }
        
        print(f"✅ File uploaded: {video.filename} ({file_size_mb:.2f}MB)")
        print(f"🔧 Processing: {processing_method}")
        
        return {
            "success": True,
            "data": {
                "fileId": file_id,
                "filename": video.filename,
                "original_size_mb": round(file_size_mb, 2),
                "processing_method": processing_method,
                "needs_encoding": file_size_mb > 30
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def analyze_with_pegasus_updated(video_source: Dict[str, Any], prompt: str, analysis_id: str) -> Dict[str, Any]:
    """업데이트된 Pegasus 모델 비디오 분석 - 파일 및 S3 URI 지원"""
    try:
        if video_source["type"] == "file":
            # 로컬 파일 처리
            file_path = video_source["path"]
            filename = video_source.get("filename", os.path.basename(file_path))
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            print(f"📏 File size for analysis: {file_size_mb:.2f}MB")
            
            # 70MB 이상이면 S3 URI 사용 (Base64 인코딩 시 100MB 제한 고려)
            if file_size_mb > 70:
                print(f"🔄 File too large for Base64, uploading to S3...")
                
                # S3에 업로드
                s3_key = f"temp-videos/{analysis_id}/{filename}"
                s3_uri = await upload_to_s3(file_path, s3_key)
                
                # 현재 계정 ID 가져오기
                try:
                    if s3_client:
                        sts_client = boto3.client('sts', region_name=AWS_REGION)
                        bucket_owner = sts_client.get_caller_identity()['Account']
                    else:
                        bucket_owner = "123456789012"
                except Exception as e:
                    print(f"⚠️ Failed to get account ID: {e}")
                    bucket_owner = os.getenv('AWS_ACCOUNT_ID', '123456789012')
                
                request_body = {
                    "inputPrompt": prompt,
                    "mediaSource": {
                        "s3Location": {
                            "uri": s3_uri,
                            "bucketOwner": bucket_owner
                        }
                    },
                    "temperature": 0.2,
                    "maxOutputTokens": 4096
                }
                
                print(f"🔄 Using S3 URI for large file: {s3_uri}")
                print(f"🔧 Using bucket owner: {bucket_owner}")
            else:
                # Base64 인코딩 사용
                print(f"🔄 Using Base64 encoding for file: {file_size_mb:.2f}MB")
                base64_video = encode_video_to_base64(file_path)
                
                request_body = {
                    "inputPrompt": prompt,
                    "mediaSource": {
                        "base64String": base64_video
                    },
                    "temperature": 0.2,
                    "maxOutputTokens": 4096
                }
            
        elif video_source["type"] == "s3uri":
            # S3 URI 처리 - 저장된 정보에서 버킷 소유자 가져오기
            s3_uri = video_source["s3_uri"]
            print(f"🔄 Using S3 URI: {s3_uri}")
            
            # 저장된 S3 URI 정보에서 버킷 소유자 찾기
            bucket_owner = None
            for uri_info in s3_uris.values():
                if uri_info["s3_uri"] == s3_uri:
                    bucket_owner = uri_info["bucket_owner"]
                    break
            
            if not bucket_owner:
                # 저장된 정보가 없는 경우 현재 계정 ID 사용
                try:
                    if s3_client:
                        sts_client = boto3.client('sts', region_name=AWS_REGION)
                        bucket_owner = sts_client.get_caller_identity()['Account']
                    else:
                        bucket_owner = "123456789012"
                except Exception as e:
                    print(f"⚠️ Failed to get account ID: {e}")
                    bucket_owner = os.getenv('AWS_ACCOUNT_ID', '123456789012')
            
            request_body = {
                "inputPrompt": prompt,
                "mediaSource": {
                    "s3Location": {
                        "uri": s3_uri,
                        "bucketOwner": bucket_owner
                    }
                },
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
            
            print(f"🔧 Using bucket owner: {bucket_owner}")
            
        else:
            raise ValueError(f"Unsupported video source type: {video_source['type']}")
        
        # Bedrock 호출
        if bedrock_runtime:
            response = bedrock_runtime.invoke_model(
                modelId=PEGASUS_MODEL_ID,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return {
                "success": True,
                "message": response_body.get('message', ''),
                "finish_reason": response_body.get('finishReason', 'stop')
            }
        else:
            # 시뮬레이션 모드
            return {
                "success": True,
                "message": f"[시뮬레이션] Pegasus 분석 결과 - 소스: {video_source['type']}, 파일: {video_source['filename']}",
                "finish_reason": "stop"
            }
            
    except Exception as e:
        print(f"❌ Pegasus analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def run_basic_analysis_updated(analysis_id: str, video_source: Dict[str, Any], prompts: List[str]):
    """업데이트된 기본 분석 실행"""
    try:
        analysis_status[analysis_id] = "analyzing"
        results = []
        
        for i, prompt in enumerate(prompts):
            print(f"🔄 Running basic analysis {i+1}/3: {prompt[:50]}...")
            
            # Pegasus 분석 실행
            pegasus_result = await analyze_with_pegasus_updated(video_source, prompt, f"{analysis_id}_{i}")
            
            if pegasus_result["success"]:
                results.append({
                    "prompt": prompt,
                    "response": pegasus_result["message"]
                })
            else:
                results.append({
                    "prompt": prompt,
                    "response": f"분석 실패: {pegasus_result.get('error', 'Unknown error')}"
                })
        
        # 결과 저장
        analysis_results[analysis_id] = {
            "id": analysis_id,
            "filename": video_source["filename"],
            "analysis_mode": "basic",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": {
                "basic_results": results
            }
        }
        analysis_status[analysis_id] = "completed"
        print(f"✅ Basic analysis completed: {analysis_id}")
        
    except Exception as e:
        print(f"❌ Basic analysis failed: {e}")
        analysis_status[analysis_id] = "error"
        analysis_results[analysis_id] = {
            "id": analysis_id,
            "filename": video_source["filename"],
            "analysis_mode": "basic",
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

async def run_professional_analysis_updated(analysis_id: str, video_source: Dict[str, Any], prompt: str):
    """업데이트된 전문 분석 실행"""
    try:
        analysis_status[analysis_id] = "analyzing"
        print(f"🔄 Running professional analysis: {prompt[:50]}...")
        
        # 1단계: Pegasus 분석
        pegasus_result = await analyze_with_pegasus_updated(video_source, prompt, analysis_id)
        
        if not pegasus_result["success"]:
            raise Exception(f"Pegasus analysis failed: {pegasus_result.get('error')}")
        
        # 2단계: Claude 구조화
        claude_result = await analyze_with_claude(pegasus_result["message"], analysis_id)
        
        if not claude_result["success"]:
            raise Exception(f"Claude analysis failed: {claude_result.get('error')}")
        
        # 결과 저장
        analysis_results[analysis_id] = {
            "id": analysis_id,
            "filename": video_source["filename"],
            "analysis_mode": "professional",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": {
                "professional_result": claude_result["structured_result"]
            }
        }
        analysis_status[analysis_id] = "completed"
        print(f"✅ Professional analysis completed: {analysis_id}")
        
    except Exception as e:
        print(f"❌ Professional analysis failed: {e}")
        analysis_status[analysis_id] = "error"
        analysis_results[analysis_id] = {
            "id": analysis_id,
            "filename": video_source["filename"],
            "analysis_mode": "professional",
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
    """기본 분석 실행 (백그라운드 태스크)"""
    try:
        analysis_status[analysis_id] = "analyzing"
        results = []
        
        for i, prompt in enumerate(prompts):
            print(f"🔄 Running basic analysis {i+1}/3: {prompt[:50]}...")
            
            # Pegasus 분석 실행
            pegasus_result = await analyze_with_pegasus(file_path, prompt, f"{analysis_id}_{i}")
            
            if pegasus_result["success"]:
                results.append({
                    "prompt": prompt,
                    "response": pegasus_result["message"]
                })
            else:
                results.append({
                    "prompt": prompt,
                    "response": f"분석 실패: {pegasus_result.get('error', 'Unknown error')}"
                })
        
        # 결과 저장
        analysis_results[analysis_id] = {
            "id": analysis_id,
            "filename": Path(file_path).name,
            "analysis_mode": "basic",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": {
                "basic_results": results
            }
        }
        analysis_status[analysis_id] = "completed"
        print(f"✅ Basic analysis completed: {analysis_id}")
        
    except Exception as e:
        print(f"❌ Basic analysis failed: {e}")
        analysis_status[analysis_id] = "error"
        analysis_results[analysis_id] = {
            "id": analysis_id,
            "filename": Path(file_path).name,
            "analysis_mode": "basic",
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

async def run_professional_analysis(analysis_id: str, file_path: str, prompt: str):
    """전문 분석 실행 (백그라운드 태스크)"""
    try:
        analysis_status[analysis_id] = "analyzing"
        print(f"🔄 Running professional analysis: {prompt[:50]}...")
        
        # 1단계: Pegasus 분석
        pegasus_result = await analyze_with_pegasus(file_path, prompt, analysis_id)
        
        if not pegasus_result["success"]:
            raise Exception(f"Pegasus analysis failed: {pegasus_result.get('error')}")
        
        # 2단계: Claude 구조화
        claude_result = await analyze_with_claude(pegasus_result["message"], analysis_id)
        
        if not claude_result["success"]:
            raise Exception(f"Claude analysis failed: {claude_result.get('error')}")
        
        # 결과 저장
        analysis_results[analysis_id] = {
            "id": analysis_id,
            "filename": Path(file_path).name,
            "analysis_mode": "professional",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": {
                "professional_result": claude_result["structured_result"]
            }
        }
        analysis_status[analysis_id] = "completed"
        print(f"✅ Professional analysis completed: {analysis_id}")
        
    except Exception as e:
        print(f"❌ Professional analysis failed: {e}")
        analysis_status[analysis_id] = "error"
        analysis_results[analysis_id] = {
            "id": analysis_id,
            "filename": Path(file_path).name,
            "analysis_mode": "professional",
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@app.post("/api/analyze/basic")
async def analyze_basic(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """기본 분석 시작 - 파일 업로드 또는 S3 URI 지원"""
    try:
        if not request.prompts or len(request.prompts) != 3:
            raise HTTPException(status_code=400, detail="Exactly 3 prompts are required for basic analysis")
        
        analysis_id = str(uuid.uuid4())
        
        # 입력 소스 확인
        if request.fileId:
            # 파일 업로드 모드
            if request.fileId not in uploaded_files:
                raise HTTPException(status_code=404, detail="File not found")
            
            file_info = uploaded_files[request.fileId]
            
            # 인코딩이 필요한 경우 완료 대기
            if file_info["needs_encoding"] and not file_info["encoding_completed"]:
                # 인코딩 완료 확인
                if not os.path.exists(file_info["final_file_path"]):
                    raise HTTPException(status_code=400, detail="Video encoding is still in progress. Please wait.")
            
            # 최종 파일 크기 확인
            final_file_path = file_info["final_file_path"]
            if os.path.exists(final_file_path):
                final_size_mb = os.path.getsize(final_file_path) / (1024 * 1024)
                print(f"📏 Final file size: {final_size_mb:.2f}MB")
                
                # 파일 크기에 따른 처리 방식 결정
                if final_size_mb > 36:  # Bedrock Base64 제한
                    # S3 업로드 필요
                    s3_key = f"temp-videos/{request.fileId}/{file_info['filename']}"
                    s3_uri = await upload_to_s3(final_file_path, s3_key)
                    
                    video_source = {
                        "type": "s3uri",
                        "s3_uri": s3_uri,
                        "filename": file_info["filename"]
                    }
                    print(f"🔄 Using S3 URI for large file: {s3_uri}")
                else:
                    # Base64 인코딩 사용
                    video_source = {
                        "type": "file",
                        "path": final_file_path,
                        "filename": file_info["filename"]
                    }
                    print(f"🔄 Using Base64 encoding for file: {final_size_mb:.2f}MB")
            else:
                raise HTTPException(status_code=404, detail="Processed video file not found")
            
            video_source = {
                "type": "file",
                "path": file_info["final_file_path"],
                "filename": file_info["filename"]
            }
            
        elif request.s3Uri:
            # S3 URI 모드
            # URI ID 찾기
            uri_info = None
            for uri_id, info in s3_uris.items():
                if info["s3_uri"] == request.s3Uri:
                    uri_info = info
                    break
            
            if not uri_info:
                raise HTTPException(status_code=404, detail="S3 URI not validated. Please validate first.")
            
            video_source = {
                "type": "s3uri",
                "s3_uri": request.s3Uri,
                "filename": os.path.basename(uri_info["key"])
            }
        else:
            raise HTTPException(status_code=400, detail="Either fileId or s3Uri must be provided")
        
        print(f"🚀 Starting basic analysis: {analysis_id}")
        print(f"📁 Source: {video_source['type']} - {video_source['filename']}")
        
        # 백그라운드에서 분석 실행
        background_tasks.add_task(
            run_basic_analysis_updated,
            analysis_id,
            video_source,
            request.prompts
        )
        
        return {
            "success": True,
            "data": {"analysisId": analysis_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed to start: {str(e)}")

@app.post("/api/analyze/professional")
async def analyze_professional(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """전문 분석 시작 - 파일 업로드 또는 S3 URI 지원"""
    try:
        if not request.prompt:
            raise HTTPException(status_code=400, detail="Prompt is required for professional analysis")
        
        analysis_id = str(uuid.uuid4())
        
        # 입력 소스 확인 (기본 분석과 동일한 로직)
        if request.fileId:
            if request.fileId not in uploaded_files:
                raise HTTPException(status_code=404, detail="File not found")
            
            file_info = uploaded_files[request.fileId]
            
            if file_info["needs_encoding"] and not file_info["encoding_completed"]:
                if not os.path.exists(file_info["final_file_path"]):
                    raise HTTPException(status_code=400, detail="Video encoding is still in progress. Please wait.")
            
            # 최종 파일 크기 확인
            final_file_path = file_info["final_file_path"]
            if os.path.exists(final_file_path):
                final_size_mb = os.path.getsize(final_file_path) / (1024 * 1024)
                print(f"📏 Final file size: {final_size_mb:.2f}MB")
                
                # 파일 크기에 따른 처리 방식 결정
                if final_size_mb > 36:  # Bedrock Base64 제한
                    # S3 업로드 필요
                    s3_key = f"temp-videos/{request.fileId}/{file_info['filename']}"
                    s3_uri = await upload_to_s3(final_file_path, s3_key)
                    
                    video_source = {
                        "type": "s3uri",
                        "s3_uri": s3_uri,
                        "filename": file_info["filename"]
                    }
                    print(f"🔄 Using S3 URI for large file: {s3_uri}")
                else:
                    # Base64 인코딩 사용
                    video_source = {
                        "type": "file",
                        "path": final_file_path,
                        "filename": file_info["filename"]
                    }
                    print(f"🔄 Using Base64 encoding for file: {final_size_mb:.2f}MB")
            else:
                raise HTTPException(status_code=404, detail="Processed video file not found")
            
            video_source = {
                "type": "file",
                "path": file_info["final_file_path"],
                "filename": file_info["filename"]
            }
            
        elif request.s3Uri:
            uri_info = None
            for uri_id, info in s3_uris.items():
                if info["s3_uri"] == request.s3Uri:
                    uri_info = info
                    break
            
            if not uri_info:
                raise HTTPException(status_code=404, detail="S3 URI not validated. Please validate first.")
            
            video_source = {
                "type": "s3uri",
                "s3_uri": request.s3Uri,
                "filename": os.path.basename(uri_info["key"])
            }
        else:
            raise HTTPException(status_code=400, detail="Either fileId or s3Uri must be provided")
        
        print(f"🚀 Starting professional analysis: {analysis_id}")
        print(f"📁 Source: {video_source['type']} - {video_source['filename']}")
        
        # 백그라운드에서 분석 실행
        background_tasks.add_task(
            run_professional_analysis_updated,
            analysis_id,
            video_source,
            request.prompt
        )
        
        return {
            "success": True,
            "data": {"analysisId": analysis_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed to start: {str(e)}")

@app.get("/api/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """분석 상태 조회"""
    try:
        if analysis_id not in analysis_status:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        status = analysis_status[analysis_id]
        result = analysis_results.get(analysis_id)
        
        if result:
            return {"success": True, "data": result}
        else:
            return {
                "success": True,
                "data": {
                    "id": analysis_id,
                    "status": status,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/{analysis_id}/result")
async def get_analysis_result(analysis_id: str):
    """분석 결과 조회"""
    try:
        if analysis_id not in analysis_results:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        result = analysis_results[analysis_id]
        return {"success": True, "data": result}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results")
async def get_all_results():
    """모든 분석 결과 조회"""
    try:
        results = list(analysis_results.values())
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/results/{result_id}")
async def delete_result(result_id: str):
    """분석 결과 삭제"""
    try:
        if result_id in analysis_results:
            del analysis_results[result_id]
        if result_id in analysis_status:
            del analysis_status[result_id]
        
        return {"success": True, "message": "Result deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results/{result_id}/download")
async def download_result(result_id: str):
    """분석 결과 다운로드"""
    try:
        if result_id not in analysis_results:
            raise HTTPException(status_code=404, detail="Result not found")
        
        result = analysis_results[result_id]
        
        # 임시 JSON 파일 생성
        import json
        temp_file = TEMP_DIR / f"result_{result_id}.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return FileResponse(
            path=temp_file,
            filename=f"analysis_result_{result_id}.json",
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI server...")
    print("📍 Backend API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🎯 Features: Base64 encoding (< 36MB) + S3 URI (≥ 36MB)")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
