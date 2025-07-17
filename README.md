# Amazon Bedrock TwelveLabs Pegasus 1.2 비디오 분석

Amazon Bedrock의 TwelveLabs Pegasus 1.2 모델을 사용하여 S3에 저장된 MP4 비디오를 분석하는 프로젝트입니다.

## 시작하기

### 프로젝트 클론
```bash
# 프로젝트 클론
git clone https://github.com/jesamkim/bedrock-pegasus-video-analyzer.git

# 프로젝트 디렉토리로 이동
cd bedrock-pegasus-video-analyzer

# 파일 구조 확인
ls -la
```

## 처리 플로우

### 전체 아키텍처
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   S3 Bucket     │    │   Your Local     │    │   Amazon Bedrock    │
│                 │    │   Environment    │    │                     │
│   MP4 Videos    │───▶│   Python App     │───▶│    AI Models        │
│                 │    │                  │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                │                         │
                                ▼                         ▼
                       ┌──────────────────┐    ┌─────────────────────┐
                       │     Results      │    │    JSON Output      │
                       │                  │    │                     │
                       │  Compressed      │◀───│  Structured Data    │
                       │  Videos + Logs   │    │                     │
                       └──────────────────┘    └─────────────────────┘
```

### 기본 테스트 플로우 (bedrock_pegasus_test.py)
```
S3 Video Input
        │
        ▼
Video Compression (if needed)
   • Max 70MB
   • 60 seconds
   • 480p, 12fps
        │
        ▼
TwelveLabs Pegasus 1.2
   • Scenario 1: General Analysis
   • Scenario 2: Detailed Summary  
   • Scenario 3: Technical Review
        │
        ▼
JSON Results
   • 3 separate files
   • Timestamp included
   • Raw analysis data
```

### 전문 분석 플로우 (bedrock_pegasus.py)
```
S3 Video Input
        │
        ▼
Video Compression (if needed)
   • Max 70MB, 60 seconds
   • 480p, 12fps
        │
        ▼
Stage 1: TwelveLabs Pegasus 1.2
   • Video → Text Analysis
   • Construction/Education Focus
        │
        ▼
Stage 2: Claude 3.7 Sonnet
   • Text → Structured JSON
   • Categorization & Classification
        │
        ▼
Professional Output
   • Video Type Classification
   • Equipment Detection
   • Work Type Identification
   • Confidence Scoring
```

## 두 가지 분석 방식 제공

### 1. **기본 테스트** (`bedrock_pegasus_test.py`)
- 3개 시나리오 자동 순차 실행
- JSON 결과 파일 저장
- 일반적인 비디오 분석 및 요약

### 2. **전문 분석** (`bedrock_pegasus.py`)
- **Pegasus 1.2** → 비디오 분석
- **Claude 3.7 Sonnet** → 결과 카테고라이징
- 공사현장/교육영상 전문 분석
- 구조화된 JSON 출력

## 프로젝트 구조

```
bedrock-pegasus-video-analyzer/
├── config.py                       # 설정 파일 (사용자 수정 가능)
├── bedrock_pegasus_test.py         # 기본 테스트 (3개 시나리오)
├── bedrock_pegasus.py              # 전문 분석 (Pegasus + Claude)
├── requirements.txt                # Python 의존성 패키지
└── README.md                       # 이 파일
```

## 빠른 시작

### 사전 요구사항
1. **AWS 자격 증명**: `aws configure`
2. **Bedrock 모델 액세스**: TwelveLabs Pegasus 1.2 + Claude 3.7 Sonnet
3. **Python 의존성**: `pip3 install -r requirements.txt`
4. **ffmpeg**: `brew install ffmpeg` (macOS) 또는 `apt-get install ffmpeg` (Ubuntu)

### 실행 방법

#### 기본 테스트 (3개 시나리오)
```bash
# S3 URI 직접 지정
python3 bedrock_pegasus_test.py --s3-uri "s3://your-bucket/video.mp4"

# 대화형 모드 (S3 URI 선택)
python3 bedrock_pegasus_test.py --interactive

# 기본 예시 비디오 사용
python3 bedrock_pegasus_test.py
```

#### 전문 분석 (Pegasus 1.2 + Claude 3.7 Sonnet)
```bash
# S3 URI 직접 지정
python3 bedrock_pegasus.py --s3-uri "s3://your-bucket/video.mp4"

# 사용자 정의 프롬프트 사용
python3 bedrock_pegasus.py --s3-uri "s3://bucket/video.mp4" --custom-prompt "Your custom prompt"

# 대화형 모드
python3 bedrock_pegasus.py --interactive
```

## 설정 사용자화

### config.py 수정
사용자의 환경에 맞게 `config.py` 파일을 수정할 수 있습니다:

```python
# AWS 설정
AWS_REGION = "us-west-2"  # 원하는 리전으로 변경

# 모델 ID 설정
PEGASUS_MODEL_ID = "us.twelvelabs.pegasus-1-2-v1:0"
CLAUDE_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# 비디오 압축 설정
VIDEO_COMPRESSION_SETTINGS = {
    "max_size_mb": 70,
    "duration_seconds": 60  # 분석할 비디오 길이
}

# 기본 테스트 프롬프트 (수정 가능)
DEFAULT_TEST_PROMPTS = [
    "Your custom prompt 1",
    "Your custom prompt 2",
    "Your custom prompt 3"
]

# 전문 분석 프롬프트 (수정 가능)
PROFESSIONAL_ANALYSIS_PROMPT = """Your custom analysis prompt"""
```

## 실제 분석 결과

### 전문 분석 결과 예시

#### 123.mp4 (토공 현장)
```json
{
  "video_type": "공사현장",
  "construction_info": {
    "work_type": ["토공"],
    "equipment": {
      "excavator": 3,
      "dump_truck": 2
    },
    "filming_technique": ["Oblique View"]
  },
  "confidence_score": 0.9
}
```

#### 456.mp4 (교량 교육영상)
```json
{
  "video_type": "교육영상",
  "construction_info": {
    "work_type": ["교량공"],
    "equipment": {
      "crane": "불명확",
      "dump_truck": "불명확"
    }
  },
  "educational_info": {
    "content_type": "교량 건설 과정 및 기술 교육",
    "slide_content": "GPS 위치 탐색, 철제 강관 설치, 안전도 검사..."
  },
  "confidence_score": 0.85
}
```

## 명령행 옵션

### 공통 옵션
- `--s3-uri`: S3 비디오 URI 직접 지정
- `--region`: AWS 리전 지정 (기본값: config.py의 AWS_REGION)
- `--interactive`: 대화형 모드로 S3 URI 선택

### 전문 분석 추가 옵션
- `--custom-prompt`: 사용자 정의 분석 프롬프트 사용

## 성능 지표

### 처리 성능
- **earthwork.mp4**: 271MB → 2.28MB (99.2% 압축) → 23초 처리
- **Bridge.mp4**: 8.56MB (압축 불필요) → 24초 처리
- **분석 정확도**: 비디오 유형 분류 100%, 작업 유형 식별 100%

### 기술 스택
- **1단계**: TwelveLabs Pegasus 1.2 (비디오 → 텍스트)
- **2단계**: Claude 3.7 Sonnet (텍스트 → 구조화된 JSON)
- **압축**: ffmpeg 자동 압축 (480p, 12fps)
- **출력**: 타임스탬프 포함 JSON 파일


## 사용 사례

### 건설 현장 관리
- 현장 작업 진행 상황 자동 모니터링
- 건설 투입 장비 현황 실시간 파악
- 안전 관리 및 규정 준수 확인

### 교육 및 훈련
- 건설 교육 콘텐츠 자동 분류
- 교육 자료 메타데이터 생성

### 프로젝트 관리
- 공사 단계별 진행 상황 추적
- 자원 배치 최적화
- 품질 관리 및 검증


## 문제 해결

### 일반적인 오류
1. **config.py 파일 없음**: 같은 디렉토리에 config.py 파일 확인
2. **모델 액세스 오류**: AWS 콘솔에서 Bedrock 모델 액세스 활성화
3. **S3 액세스 오류**: S3 버킷 읽기 권한 확인
4. **ffmpeg 없음**: `brew install ffmpeg` 또는 `apt-get install ffmpeg`

### 디버깅
```bash
# 상세 로그 확인
python3 bedrock_pegasus.py --s3-uri "s3://bucket/video.mp4" 2>&1 | tee debug.log

# AWS 자격 증명 확인
aws configure list

# Bedrock 모델 액세스 확인
aws bedrock list-inference-profiles --region us-west-2
```

## 참고 자료

- [TwelveLabs Pegasus 모델 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-twelvelabs.html)


---

**GitHub Repository**: `https://github.com/jesamkim/bedrock-pegasus-video-analyzer.git`

