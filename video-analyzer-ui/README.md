# Bedrock Pegasus Video Analyzer UI

Amazon Bedrock의 TwelveLabs Pegasus 1.2 모델과 Claude 3.7 Sonnet을 활용한 **현대적인 웹 기반 비디오 분석 인터페이스**입니다.

## 🎯 주요 기능

### 📁 **스마트 파일 처리**
- **드래그 앤 드롭 업로드**: MP4, MOV, AVI, WebM 파일 지원
- **S3 URI 입력**: 기존 S3 저장 비디오 직접 접근
- **자동 크기 최적화**: 70MB 이상 파일 자동 S3 업로드
- **실시간 인코딩**: FFmpeg 기반 비디오 압축 (선택사항)

### 🤖 **이중 AI 분석**
- **기본 테스트**: 3개 프롬프트로 일반적인 비디오 분석
- **전문 분석**: Pegasus + Claude를 활용한 건설/교육 영상 전문 분석
- **실시간 프롬프트 편집**: 분석 질문을 자유롭게 수정
- **구조화된 결과**: JSON 형태의 상세한 분석 결과

### 🎨 **현대적인 UI/UX**
- **다크 테마**: 눈에 편안한 전문적인 디자인
- **글래스모피즘**: 반투명 카드와 백드롭 블러 효과
- **실시간 진행률**: 업로드, 인코딩, 분석 각 단계별 시각적 피드백
- **설정 모달**: AWS 설정 및 압축 옵션 실시간 조정

## 🏗️ 아키텍처

```
Frontend (React + TypeScript)
├── 파일 입력 (탭 기반)
│   ├── 드래그 앤 드롭 업로드
│   └── S3 URI 입력
├── 분석 모드 선택
│   ├── 기본 테스트 (3개 프롬프트)
│   └── 전문 분석 (Pegasus + Claude)
├── 실시간 진행률 표시
│   ├── 업로드 진행률 (원형)
│   ├── 인코딩 진행률 (모달)
│   └── 분석 진행률 (단계별)
└── 결과 뷰어
    ├── JSON 구조화 표시
    ├── 복사/다운로드 기능
    └── 분석 통계

Backend (FastAPI + Python)
├── 파일 업로드 핸들러
│   ├── 크기별 자동 처리
│   └── S3 업로드 관리
├── 비디오 인코딩 (FFmpeg)
├── Bedrock 통합
│   ├── Pegasus 1.2 분석
│   └── Claude 3.7 Sonnet 구조화
└── 백그라운드 태스크 관리
```

## 🚀 빠른 시작

### 사전 요구사항

1. **Node.js 18+** 및 **pnpm**
2. **Python 3.8+**
3. **AWS 자격 증명** 설정 (`aws configure`)
4. **Bedrock 모델 액세스**: TwelveLabs Pegasus 1.2 + Claude 3.7 Sonnet
5. **S3 버킷** (큰 파일 처리용)
6. **ffmpeg** (선택사항, 비디오 인코딩용)

### 설치 및 실행

```bash
# 1. 프로젝트 디렉토리로 이동
cd video-analyzer-ui

# 2. 개발 서버 시작 (백엔드 + 프론트엔드)
./start-dev.sh
```

서비스가 시작되면:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000


### 수동 실행 (개발용)

#### 백엔드 서버
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

#### 프론트엔드 서버
```bash
cd frontend
pnpm install
pnpm run dev
```

## 📁 프로젝트 구조

```
video-analyzer-ui/
├── frontend/                    # React 프론트엔드
│   ├── src/
│   │   ├── components/         # React 컴포넌트
│   │   │   ├── VideoUpload.tsx      # 파일 업로드 (탭 기반)
│   │   │   ├── AnalysisResults.tsx  # 결과 표시
│   │   │   └── SettingsModal.tsx    # 설정 모달
│   │   ├── hooks/              # 커스텀 훅
│   │   │   └── useAnalysis.ts       # 분석 상태 관리
│   │   ├── services/           # API 서비스
│   │   │   └── api.ts              # API 클라이언트
│   │   ├── types/              # TypeScript 타입
│   │   └── App.tsx             # 메인 앱
│   ├── package.json
│   └── tailwind.config.js
├── backend/                     # FastAPI 백엔드
│   ├── main.py                 # 메인 서버 파일
│   ├── video_encoder.py        # 비디오 인코딩
│   ├── backend.log             # 서버 로그
│   └── requirements.txt
├── start-dev.sh                # 개발 서버 시작 스크립트
└── README.md
```

## 🎨 UI 컴포넌트

### 1. VideoUpload (탭 기반 입력)
- **파일 업로드 탭**: 드래그 앤 드롭 인터페이스
- **S3 URI 탭**: 기존 S3 비디오 직접 접근
- **파일 유효성 검사**: 타입, 크기 자동 검증
- **업로드 진행률**: 원형 진행률 표시

### 2. AnalysisResults
- **실시간 분석 진행률**: 단계별 상태 표시
- **구조화된 JSON 결과**: 보기 좋은 형태로 표시
- **결과 관리**: 복사, 다운로드, 통계 기능

### 3. SettingsModal
- **AWS 설정**: 리전, 모델 ID, S3 버킷
- **압축 설정**: 파일 크기, 품질, 해상도
- **실시간 적용**: 설정 변경 즉시 반영

## 🔧 기술 스택

### Frontend
- **React 18** + **TypeScript**
- **Vite** (빌드 도구)
- **Tailwind CSS** (다크 테마)
- **Headless UI** (접근성 컴포넌트)
- **Heroicons** (아이콘)
- **React Query** (서버 상태 관리 및 캐싱)
- **React Dropzone** (파일 업로드)

### Backend
- **FastAPI** (Python 웹 프레임워크)
- **boto3** (AWS SDK)
- **ffmpeg** (비디오 인코딩)
- **asyncio** (비동기 처리)
- **Pydantic** (데이터 검증)

## 📡 API 엔드포인트

### 기본 API
```
GET  /                          # 서버 상태 확인
GET  /api/config                # 설정 조회
PUT  /api/config                # 설정 업데이트
```

### 파일 처리
```
POST /api/upload                # 비디오 파일 업로드
GET  /api/encoding-progress/{id} # 인코딩 진행률 조회
GET  /api/files/{id}/status     # 파일 상태 확인
```

### 분석 API
```
POST /api/analyze/basic         # 기본 분석 시작
POST /api/analyze/professional  # 전문 분석 시작
GET  /api/analysis/{id}/status  # 분석 상태 조회
```

### S3 URI 처리
```
POST /api/s3-uri/validate       # S3 URI 유효성 검사
POST /api/s3-uri/analyze        # S3 URI 직접 분석
```

## 🎯 사용 방법

### 기본 워크플로우
1. **파일 선택**: 드래그 앤 드롭 또는 S3 URI 입력
2. **분석 모드 선택**: 기본 테스트 또는 전문 분석
3. **프롬프트 편집**: 필요시 분석 질문 수정
4. **Analyze 버튼 클릭**: 업로드 → 인코딩 → 분석 순차 진행
5. **실시간 진행률 확인**: 각 단계별 시각적 피드백
6. **결과 확인**: 구조화된 JSON 결과 및 다운로드

### 파일 크기별 처리
- **≤ 70MB**: Base64 인코딩으로 직접 전송
- **> 70MB**: 자동 S3 업로드 후 S3 URI 사용
- **인코딩 필요시**: FFmpeg로 압축 후 재평가

## 🔍 개발 및 디버깅

### 로그 확인
```bash
# 백엔드 로그
tail -f backend/backend.log

# 프론트엔드 로그
tail -f frontend/frontend.log

# 브라우저 개발자 도구
# F12 → Console 탭에서 상세 로그 확인
```

### API 테스트
```bash
# API 문서 확인
open http://localhost:8000/docs

# 설정 확인
curl http://localhost:8000/api/config

# 파일 업로드 테스트
curl -X POST -F "video=@sample.mp4" http://localhost:8000/api/upload
```

### 디버깅 팁
- **Console 로그**: 각 단계별 상세한 상태 정보
- **Network 탭**: API 요청/응답 확인
- **Application 탭**: 로컬 스토리지 상태 확인

## ⚙️ 설정 및 커스터마이징

### 환경변수
```bash
# AWS 설정
export AWS_REGION=us-west-2
export AWS_ACCOUNT_ID=your-account-id

# S3 버킷 설정
export VIDEO_ANALYSIS_BUCKET=bedrock-pegasus-video-temp

# 모델 ID 설정
export PEGASUS_MODEL_ID=us.twelvelabs.pegasus-1-2-v1:0
export CLAUDE_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0
```

### 압축 설정 커스터마이징
```python
# backend/main.py에서 수정
VIDEO_COMPRESSION_SETTINGS = {
    "max_size_mb": 70,        # 목표 파일 크기
    "crf": 30,                # 품질 (낮을수록 고품질)
    "preset": "fast",         # 인코딩 속도
    "resolution": "854:480",  # 해상도
    "framerate": 12           # 프레임레이트
}
```

## 🚧 알려진 제한사항

1. **파일 크기**: Bedrock Base64 제한 (100MB)
2. **동시 분석**: 현재 1개 파일만 동시 분석 가능
3. **결과 저장**: 서버 재시작 시 결과 초기화 (메모리 저장)
4. **ffmpeg 의존성**: 인코딩 기능은 ffmpeg 설치 필요

