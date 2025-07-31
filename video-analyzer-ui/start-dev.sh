#!/bin/bash

# Bedrock Pegasus Video Analyzer UI 개발 서버 시작 스크립트

echo "🚀 Starting Bedrock Pegasus Video Analyzer UI..."

# 현재 디렉토리 확인
if [ ! -f "frontend/package.json" ] || [ ! -f "backend/main.py" ]; then
    echo "❌ Error: Please run this script from the video-analyzer-ui directory"
    exit 1
fi

# 백엔드 가상환경 확인 및 생성
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating Python virtual environment for backend..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# 프론트엔드 의존성 확인
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    pnpm install
    cd ..
fi

echo "🔧 Starting services..."

# 백엔드 서버 시작 (백그라운드)
echo "🐍 Starting FastAPI backend server on http://localhost:8000"
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

# 잠시 대기 (백엔드 서버 시작 시간)
sleep 3

# 프론트엔드 서버 시작
echo "⚛️  Starting React frontend server on http://localhost:5173"
cd frontend
pnpm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# 종료 시그널 처리
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ All services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 서비스들이 실행 중인 동안 대기
wait
