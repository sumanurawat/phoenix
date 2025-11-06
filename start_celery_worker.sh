#!/bin/bash
# Start Celery Worker for Phoenix
# Handles async video/image generation

set -e  # Exit on error

echo "🚀 Starting Celery Worker for Phoenix..."

# Activate virtual environment
source venv/bin/activate

# Export Google Cloud project ID (needed for Firestore initialization)
export GOOGLE_CLOUD_PROJECT="phoenix-project-386"
export PROJECT_ID="phoenix-project-386"

# Load environment variables from .env if present
if [ -f .env ]; then
    echo "📄 Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
fi

# Kill any existing Celery workers
echo "🧹 Cleaning up existing Celery workers..."
pkill -9 -f "celery.*worker" 2>/dev/null || echo "No existing workers found"
sleep 2

# Start Celery worker with proper logging
echo "✅ Starting Celery worker..."
celery -A celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=solo \
    --logfile=celery_worker.log \
    --pidfile=celery_worker.pid &

CELERY_PID=$!
echo "✅ Celery worker started with PID: $CELERY_PID"
echo "📋 Log file: celery_worker.log"
echo ""
echo "To monitor logs: tail -f celery_worker.log"
echo "To stop worker: pkill -9 -f 'celery.*worker'"
