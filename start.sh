#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=================================================================="
echo "                OMNI-AGENT LOCAL BOOTSTRAPPER"
echo "=================================================================="

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed or not in PATH."
    exit 1
fi

# Check Node version
if ! command -v npm &> /dev/null; then
    echo "[ERROR] Node/npm is not installed or not in PATH."
    exit 1
fi

# 1. Setup Backend Environment
echo "-> Checking backend virtual environment..."
if [ ! -d "backend/.venv" ]; then
    echo "Creating virtual environment in backend/.venv..."
    python3 -m venv backend/.venv
fi

echo "Bootstrapping pip and installing dependencies..."
backend/.venv/bin/python -m ensurepip --default-pip &> /dev/null || true
backend/.venv/bin/python -m pip install --upgrade pip &> /dev/null || true
backend/.venv/bin/python -m pip install -r backend/requirements.txt

# 2. Setup Frontend Environment
echo "-> Checking frontend node modules..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend npm packages..."
    cd frontend && npm install && cd ..
fi

# 3. Startup concurrent servers
echo "-> Starting local servers..."

# Define cleanup function
cleanup() {
    echo ""
    echo "=================================================================="
    echo "Stopping OmniAgent local servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Servers stopped. Goodbye!"
    echo "=================================================================="
    exit 0
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT SIGTERM

# Start Backend
echo "Starting FastAPI Backend on http://localhost:8000..."
cd backend
.venv/bin/python -m uvicorn main:app --port 8000 --reload > uvicorn.log 2>&1 &
BACKEND_PID=$!
cd ..

# Start Frontend
echo "Starting Vite Frontend on http://localhost:5173..."
cd frontend
# Inject node binary path if running in custom environment context
if [ -d "$HOME/.nvm/versions/node/v22.18.0/bin" ]; then
    export PATH="$HOME/.nvm/versions/node/v22.18.0/bin:$PATH"
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo "=================================================================="
echo "OmniAgent is up and running!"
echo "- Frontend: http://localhost:5173"
echo "- Backend: http://localhost:8000"
echo "Press Ctrl+C to stop both servers."
echo "=================================================================="

# Keep script running to monitor background tasks
wait $BACKEND_PID $FRONTEND_PID
