#!/bin/bash

set -euo pipefail

# Script to clean port 8080 and start the Phoenix AI Platform
echo "=== Phoenix AI Platform Startup ==="

# Check if .env file exists, warn if not
if [ ! -f .env ]; then
    echo "WARNING: .env file not found. Make sure your API keys are set."
fi

# Check if virtual environment is activated, if not, activate it
if [[ "${VIRTUAL_ENV:-}" == "" ]]; then
    echo "Virtual environment not detected. Activating venv..."
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo "✅ Virtual environment activated: $(which python)"
    else
        echo "❌ ERROR: venv directory not found. Please create a virtual environment first:"
        echo "   python3 -m venv venv"
        echo "   source venv/bin/activate"
        echo "   pip install -r requirements.txt"
        exit 1
    fi
else
    echo "✅ Virtual environment already active: $VIRTUAL_ENV"
fi

echo "Checking if port 8080 is in use..."

# Find processes using port 8080 (lsof exits 1 when nothing is found; ignore)
PIDS=$(lsof -ti tcp:8080 || true)

if [ -n "$PIDS" ]; then
    echo "Port 8080 is in use by process(es): $PIDS"
    echo "Killing process(es)..."
    # Process each PID separately
    for PID in $PIDS; do
        echo "Killing process $PID"
        kill -9 $PID
    done
    echo "Process(es) killed."
else
    echo "Port 8080 is not in use."
fi

echo "Creating session directory if it doesn't exist..."
mkdir -p ./flask_session

# Check and start Redis if not running
echo "Checking Redis status..."
if ! redis-cli ping >/dev/null 2>&1; then
    echo "⚠️  Redis is not running. Starting Redis..."
    if command -v redis-server >/dev/null 2>&1; then
        # Start Redis in background
        redis-server --daemonize yes --port 6379
        # Wait a moment for Redis to start
        sleep 1
        if redis-cli ping >/dev/null 2>&1; then
            echo "✅ Redis started successfully on port 6379"
        else
            echo "❌ Failed to start Redis. Video generation will not work."
            echo "   You can install Redis with: brew install redis"
        fi
    else
        echo "❌ Redis not installed. Video generation will use graceful fallback."
        echo "   To enable video generation, install Redis: brew install redis"
        echo "   (Image generation and other features will work normally)"
    fi
else
    echo "✅ Redis already running on port 6379"
fi

# Start Celery worker in background if Redis is available
if redis-cli ping >/dev/null 2>&1; then
    echo "Starting Celery worker for video generation..."
    export GOOGLE_CLOUD_PROJECT=phoenix-project-386
    # Kill any existing Celery workers first
    pkill -f "celery.*worker" || true
    sleep 1
    # Start worker in background and redirect output to log file
    celery -A celery_app worker --loglevel=info --concurrency=2 --pool=solo \
        > celery_worker.log 2>&1 &
    CELERY_PID=$!
    echo "✅ Celery worker started (PID: $CELERY_PID, logs: celery_worker.log)"
    echo "   Tail logs with: tail -f celery_worker.log"
else
    echo "⚠️  Skipping Celery worker (Redis not available)"
fi

# Build Reel Maker frontend bundle so Flask can serve the latest assets
FRONTEND_DIR="frontend/reel-maker"
if [ -d "$FRONTEND_DIR" ]; then
    echo ""
    echo "=== Preparing Reel Maker frontend ==="
    if ! command -v npm >/dev/null 2>&1; then
        echo "❌ ERROR: npm is required to build the frontend. Please install Node.js (includes npm) and rerun this script."
        exit 1
    fi

    pushd "$FRONTEND_DIR" >/dev/null

    if [ ! -d "node_modules" ]; then
        echo "📦 Installing frontend dependencies (first run only)..."
        npm install
    else
        echo "✅ Frontend dependencies already present. Skipping npm install."
    fi

    echo "🔨 Building React bundle..."
    npm run build

    popd >/dev/null
    echo "✅ Frontend assets ready in static/reel_maker/"
    echo ""
else
    echo "⚠️  Frontend directory $FRONTEND_DIR not found. Skipping React build."
    echo ""
fi

echo "=== Starting Phoenix AI Platform ==="
echo "📝 Note: You'll see initialization logs twice due to Flask debug mode auto-reloader"
echo "🌐 Server will be available at: http://localhost:8080"
echo "🎬 Reel Maker: http://localhost:8080/reel-maker"
echo ""
echo "Press Ctrl+C to stop the server"
echo "─────────────────────────────────────────────────────────"
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    # Kill Celery worker if running
    pkill -f "celery.*worker" || true
    # Keep Redis running (it's a system service)
    echo "✅ Cleanup complete"
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup SIGINT SIGTERM

python app.py

# Cleanup on normal exit
cleanup