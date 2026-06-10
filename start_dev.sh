#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# InsightFlow AI — Local Development Startup Script
# Run: chmod +x start_dev.sh && ./start_dev.sh
# ─────────────────────────────────────────────────────────────
set -e

echo "🧠 Starting InsightFlow AI development environment..."
echo ""

# ── Check prerequisites ──────────────────────────────────────
check_command() {
  if ! command -v "$1" &>/dev/null; then
    echo "❌ $1 is not installed. Please install it first."
    exit 1
  fi
}

check_command python3
check_command node
check_command npm

# ── Python virtual environment ───────────────────────────────
if [ ! -d "backend/venv" ]; then
  echo "📦 Creating Python virtual environment..."
  python3 -m venv backend/venv
fi

echo "📦 Installing Python dependencies..."
source backend/venv/bin/activate
pip install -r backend/requirements.txt -q

# ── .env check ───────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "⚠️  .env file not found. Copying from .env.example..."
  cp .env.example .env
  echo "✏️  Please edit .env and add your GEMINI_API_KEY, then re-run."
  exit 1
fi

# ── Storage directories ──────────────────────────────────────
mkdir -p backend/storage/raw_documents backend/storage/processed_documents backend/storage/metadata backend/chroma_data

# ── Frontend dependencies ────────────────────────────────────
if [ ! -d "frontend/node_modules" ]; then
  echo "📦 Installing frontend dependencies..."
  npm install --prefix frontend -q
fi

# ── Start services ───────────────────────────────────────────
echo ""
echo "🚀 Starting services..."
echo ""

# Backend (FastAPI)
echo "▶ Backend:  http://localhost:8000"
echo "▶ API Docs: http://localhost:8000/docs"
(cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Frontend (Vite)
echo "▶ Frontend: http://localhost:5173"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "✅ InsightFlow AI is running!"
echo "   → Frontend: http://localhost:5173"
echo "   → Backend:  http://localhost:8000"
echo "   → API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Services stopped.'; exit 0" INT TERM
wait
