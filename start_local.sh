#!/bin/bash

set -euo pipefail

# Colors for beautiful output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script to clean ports and start the Phoenix AI Platform (Backend + SOHO Frontend)
echo -e "${BOLD}${PURPLE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║           🚀 PHOENIX AI PLATFORM + SOHO 🎨                ║"
echo "║                                                            ║"
echo "║              Starting Full Stack Application...            ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if .env file exists, warn if not
echo -e "${CYAN}[1/8] Checking environment configuration...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  WARNING: .env file not found. Make sure your API keys are set.${NC}"
else
    echo -e "${GREEN}✅ Environment file found${NC}"
fi

# Check if virtual environment is activated, if not, activate it
echo -e "${CYAN}[2/8] Setting up Python environment...${NC}"
if [[ "${VIRTUAL_ENV:-}" == "" ]]; then
    echo "  Virtual environment not detected. Activating venv..."
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✅ Virtual environment activated: $(which python)${NC}"
    else
        echo -e "${RED}❌ ERROR: venv directory not found. Please create a virtual environment first:${NC}"
        echo "   python3 -m venv venv"
        echo "   source venv/bin/activate"
        echo "   pip install -r requirements.txt"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Virtual environment already active${NC}"
fi

echo -e "${CYAN}[3/8] Cleaning ports (8080 for Backend, 5173 for Frontend)...${NC}"

# Find and kill processes using port 8080 (Backend)
PIDS_8080=$(lsof -ti tcp:8080 || true)
if [ -n "$PIDS_8080" ]; then
    echo "  Port 8080 is in use. Killing processes..."
    for PID in $PIDS_8080; do
        kill -9 $PID 2>/dev/null || true
    done
    echo -e "${GREEN}✅ Port 8080 cleared${NC}"
else
    echo -e "${GREEN}✅ Port 8080 is available${NC}"
fi

# Find and kill processes using port 5173 (Frontend dev server)
PIDS_5173=$(lsof -ti tcp:5173 || true)
if [ -n "$PIDS_5173" ]; then
    echo "  Port 5173 is in use. Killing processes..."
    for PID in $PIDS_5173; do
        kill -9 $PID 2>/dev/null || true
    done
    echo -e "${GREEN}✅ Port 5173 cleared${NC}"
else
    echo -e "${GREEN}✅ Port 5173 is available${NC}"
fi

echo "  Creating session directory..."
mkdir -p ./flask_session
echo -e "${GREEN}✅ Session directory ready${NC}"

# Check and start Redis if not running
echo -e "${CYAN}[4/8] Checking Redis (required for video generation)...${NC}"
if ! redis-cli ping >/dev/null 2>&1; then
    echo "  ⚠️  Redis is not running. Starting Redis..."
    if command -v redis-server >/dev/null 2>&1; then
        # Start Redis in background
        redis-server --daemonize yes --port 6379 >/dev/null 2>&1
        # Wait a moment for Redis to start
        sleep 1
        if redis-cli ping >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis started successfully (Port: 6379)${NC}"
        else
            echo -e "${RED}❌ Failed to start Redis. Video generation will not work.${NC}"
            echo -e "${YELLOW}   Install with: brew install redis${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Redis not installed. Video generation will use graceful fallback.${NC}"
        echo -e "${YELLOW}   To enable video generation, install Redis: brew install redis${NC}"
        echo -e "${GREEN}   (Image generation and other features will work normally)${NC}"
    fi
else
    echo -e "${GREEN}✅ Redis already running (Port: 6379)${NC}"
fi

# Start Celery worker in background if Redis is available
echo -e "${CYAN}[5/8] Starting Celery worker for async video generation...${NC}"
if redis-cli ping >/dev/null 2>&1; then
    export GOOGLE_CLOUD_PROJECT=phoenix-project-386
    # Kill any existing Celery workers first
    pkill -f "celery.*worker" >/dev/null 2>&1 || true
    sleep 1
    # Start worker in background and redirect output to log file
    celery -A celery_app worker --loglevel=info --concurrency=2 --pool=solo \
        > celery_worker.log 2>&1 &
    CELERY_PID=$!
    echo -e "${GREEN}✅ Celery worker started (PID: $CELERY_PID)${NC}"
    echo -e "${BLUE}   📝 Worker logs: celery_worker.log${NC}"
    echo -e "${BLUE}   📝 Tail logs: tail -f celery_worker.log${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping Celery worker (Redis not available)${NC}"
fi

# Check if npm is available (required for both frontends)
echo -e "${CYAN}[6/8] Preparing frontend applications...${NC}"
if ! command -v npm >/dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: npm is required. Please install Node.js and rerun this script.${NC}"
    exit 1
fi

# Build Reel Maker frontend bundle (legacy)
REEL_MAKER_DIR="frontend/reel-maker"
if [ -d "$REEL_MAKER_DIR" ]; then
    echo "  📦 Building Reel Maker (legacy)..."
    pushd "$REEL_MAKER_DIR" >/dev/null

    if [ ! -d "node_modules" ]; then
        echo "     Installing dependencies..."
        npm install --silent
    fi

    npm run build --silent
    popd >/dev/null
    echo -e "${GREEN}  ✅ Reel Maker built (served at /reel-maker)${NC}"
else
    echo -e "${YELLOW}  ⚠️  Reel Maker not found. Skipping.${NC}"
fi

# Prepare SOHO frontend (new React app)
SOHO_DIR="frontend/soho"
if [ -d "$SOHO_DIR" ]; then
    echo "  🎨 Preparing SOHO frontend..."
    pushd "$SOHO_DIR" >/dev/null

    if [ ! -d "node_modules" ]; then
        echo "     Installing dependencies (first run only)..."
        npm install --silent
    fi

    popd >/dev/null
    echo -e "${GREEN}  ✅ SOHO frontend ready (will run on port 5173)${NC}"
else
    echo -e "${YELLOW}  ⚠️  SOHO frontend not found at $SOHO_DIR${NC}"
fi

echo ""

echo -e "${CYAN}[7/8] Starting Backend API Server...${NC}"
echo -e "${GREEN}  ✅ Flask will start on port 8080${NC}"

echo -e "${CYAN}[8/8] Starting SOHO Frontend Dev Server...${NC}"
if [ -d "$SOHO_DIR" ]; then
    echo -e "${GREEN}  ✅ Vite will start on port 5173${NC}"
else
    echo -e "${YELLOW}  ⚠️  SOHO frontend not available${NC}"
fi

echo ""
echo -e "${BOLD}${GREEN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║                  🎉 STARTUP COMPLETE! 🎉                  ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BOLD}${CYAN}📍 OPEN THESE URLS IN YOUR BROWSER:${NC}"
echo ""
echo -e "${BOLD}${PURPLE}  🚀 SOHO FRONTEND (NEW UI)${NC}"
echo -e "${GREEN}     ➜ http://localhost:5173${NC}"
echo -e "${BLUE}     (React + Vite dev server with hot reload)${NC}"
echo ""
echo -e "${BOLD}${PURPLE}  🔧 BACKEND API${NC}"
echo -e "${GREEN}     ➜ http://localhost:8080${NC}"
echo -e "${BLUE}     (Flask backend serving all APIs)${NC}"
echo ""
echo -e "${BOLD}${PURPLE}  🎬 REEL MAKER (LEGACY)${NC}"
echo -e "${GREEN}     ➜ http://localhost:8080/reel-maker${NC}"
echo -e "${BLUE}     (Existing video generation interface)${NC}"
echo ""
echo -e "${BOLD}${YELLOW}📊 SERVICES RUNNING:${NC}"
echo -e "  • Backend API:      Port 8080"
echo -e "  • SOHO Frontend:    Port 5173"
echo -e "  • Redis:            Port 6379"
echo -e "  • Celery Worker:    Background (logs: celery_worker.log)"
echo ""
echo -e "${BOLD}${YELLOW}📝 LOGS:${NC}"
echo -e "  • Celery logs:  ${BLUE}tail -f celery_worker.log${NC}"
echo -e "  • Backend logs: Below this message"
echo -e "  • Frontend logs: Check Vite terminal output"
echo ""
echo -e "${BOLD}${RED}🛑 TO STOP: Press Ctrl+C${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down services...${NC}"
    # Kill Celery worker if running
    pkill -f "celery.*worker" >/dev/null 2>&1 || true
    # Kill frontend dev server
    pkill -f "vite.*soho" >/dev/null 2>&1 || true
    # Kill any remaining processes on our ports
    lsof -ti tcp:8080 | xargs kill -9 2>/dev/null || true
    lsof -ti tcp:5173 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup complete${NC}"
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup SIGINT SIGTERM

# Start SOHO frontend in background if it exists
if [ -d "$SOHO_DIR" ]; then
    echo -e "${BLUE}[FRONTEND] Starting SOHO dev server...${NC}"
    cd "$SOHO_DIR"
    npm run dev > ../../soho_frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ../..
    echo -e "${GREEN}[FRONTEND] Started with PID: $FRONTEND_PID${NC}"
    echo ""
fi

# Start Flask backend in foreground (so we can see logs)
echo -e "${BLUE}[BACKEND] Starting Flask API...${NC}"
echo ""
python app.py

# Cleanup on normal exit
cleanup