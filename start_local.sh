#!/bin/bash

set -euo pipefail

# Script to clean port 8080 and start the Phoenix AI Platform
echo "=== Phoenix AI Platform Startup ==="

# Check if .env file exists, warn if not
if [ ! -f .env ]; then
    echo "WARNING: .env file not found. Make sure your API keys are set."
fi

# Check if virtual environment is activated, if not, activate it
if [[ "$VIRTUAL_ENV" == "" ]]; then
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

echo "Note: Flask session directory no longer needed (using cookie-based sessions)"

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

python app.py