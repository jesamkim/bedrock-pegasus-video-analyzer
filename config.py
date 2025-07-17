#!/usr/bin/env python3
"""
Amazon Bedrock Video Analysis Configuration
사용자가 수정 가능한 설정 파일
"""

# AWS 설정
AWS_REGION = "us-west-2"

# 모델 ID 설정
PEGASUS_MODEL_ID = "us.twelvelabs.pegasus-1-2-v1:0"
CLAUDE_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# 비디오 처리 설정
VIDEO_COMPRESSION_SETTINGS = {
    "max_size_mb": 70,
    "crf": 30,
    "preset": "fast",
    "resolution": "854:480",  # 480p
    "framerate": 12,
    "duration_seconds": 60    # 전문 분석용 (bedrock_pegasus.py)
}

# 기본 테스트용 (bedrock_pegasus_test.py) 비디오 처리 설정
TEST_VIDEO_COMPRESSION_SETTINGS = {
    "max_size_mb": 70,
    "crf": 30,
    "preset": "fast", 
    "resolution": "854:480",  # 480p
    "framerate": 12,
    "duration_seconds": 30    # 기본 테스트용
}

# 기본 테스트 (bedrock_pegasus_test.py) 프롬프트 (사용자 수정 가능)
DEFAULT_TEST_PROMPTS = [
    "이 비디오에 대해 자세히 설명해주세요. 주요 장면과 내용을 요약해주세요.",
    "비디오에서 어떤 작업이나 활동이 진행되고 있나요? 구체적으로 설명해주세요.",
    "이 비디오의 주요 하이라이트와 중요한 순간들을 찾아주세요."
]

# 전문 분석용 (bedrock_pegasus.py) 프롬프트 (사용자 수정 가능)
PROFESSIONAL_ANALYSIS_PROMPT = """이 비디오의 영상에 대한 정보를 자세히 확인하세요. 공사 현장 영상인 경우, 작업 내용(토공, 교량공, 도배공 등)이 무엇인지, 투입장비(excavator, loader, dump truck 등)의 종류와 댓수, 어떤 기법으로 촬영(Bird View, Oblique View, Tracking View, CCTV, 1인칭, 360도 등)한 것인지를 확인합니다. 교육 동영상 등의 경우 어떤 내용의 영상인지 (영상의 자막이나 슬라이드 내용도 참고) 확인 합니다."""

# 기본 S3 URI (예시용 - 사용자가 변경 가능)
DEFAULT_S3_URIS = [
    "s3://250717-mov/mov2/123.mp4",
    "s3://250717-mov/mov1/456.mp4"
]

# 출력 파일 설정
OUTPUT_SETTINGS = {
    "test_results_prefix": "bedrock_pegasus_test_results",
    "analysis_results_prefix": "pegasus_claude_analysis",
    "timestamp_format": "%Y%m%d_%H%M%S"
}
