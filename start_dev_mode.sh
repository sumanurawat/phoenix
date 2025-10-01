#!/bin/bash

# Development mode: Run both frontend dev server and Flask backend concurrently
# This enables hot-reloading for React changes

set -euo pipefail

echo "=== Phoenix AI Platform - Development Mode with Hot Reload ==="
echo ""

# Check virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Activating virtual environment..."
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ ERROR: venv directory not found. Run ./start_local.sh first."
        exit 1
    fi
fi

# Check if npm is available
if ! command -v npm >/dev/null 2>&1; then
    echo "❌ ERROR: npm is required. Please install Node.js."
    exit 1
fi

# Check if frontend directory exists
FRONTEND_DIR="frontend/reel-maker"
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ ERROR: Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

# Install frontend dependencies if needed
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    pushd "$FRONTEND_DIR" >/dev/null
    npm install
    popd >/dev/null
fi

# Clean port 8080
echo "Checking port 8080..."
PIDS=$(lsof -ti tcp:8080 || true)
if [ -n "$PIDS" ]; then
    echo "Killing process(es) on port 8080: $PIDS"
    for PID in $PIDS; do
        kill -9 $PID
    done
fi

# Create session directory
mkdir -p ./flask_session

echo ""
echo "🚀 Starting development servers..."
echo "   - React dev server (Vite): http://localhost:5173"
echo "   - Flask backend: http://localhost:8080"
echo ""
echo "⚡ React changes will hot-reload automatically!"
echo "🔄 Flask will auto-restart on Python file changes"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "─────────────────────────────────────────────────────────"
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "Stopping development servers..."
    kill $(jobs -p) 2>/dev/null || true
    exit
}

trap cleanup SIGINT SIGTERM

# Start Vite dev server in background
pushd "$FRONTEND_DIR" >/dev/null
npm run dev &
VITE_PID=$!
popd >/dev/null

# Give Vite a moment to start
sleep 2

# Start Flask in foreground
python app.py

# Cleanup on normal exit
cleanup
