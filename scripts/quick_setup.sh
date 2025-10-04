#!/bin/bash
set -e

# Quick Setup Script for Cloud Run Jobs
# This script provides a one-command setup for the entire jobs system

echo "🚀 Phoenix Cloud Run Jobs - Quick Setup"
echo "======================================"

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"phoenix-project-386"}
REGION=${GCP_REGION:-"us-central1"}

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if running from correct directory
if [ ! -f "app.py" ] || [ ! -d "jobs" ]; then
    echo "❌ Error: Please run this script from the Phoenix project root directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

missing_deps=()

if ! command_exists gcloud; then
    missing_deps+=("gcloud CLI")
fi

if ! command_exists docker; then
    missing_deps+=("Docker")
fi

if ! command_exists curl; then
    missing_deps+=("curl")
fi

if ! command_exists jq; then
    missing_deps+=("jq")
fi

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo "❌ Missing dependencies:"
    printf '%s\n' "${missing_deps[@]}"
    echo ""
    echo "Please install the missing dependencies and try again."
    exit 1
fi

echo "✅ All prerequisites found"
echo ""

# Check authentication
echo "🔐 Checking Google Cloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
    echo "❌ Not authenticated with gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

echo "✅ Google Cloud authenticated"
echo ""

# Set project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID
echo ""

# Step 1: Cloud infrastructure setup
echo "☁️ Step 1: Setting up Cloud infrastructure..."
if ./scripts/setup_job_queue.sh; then
    echo "✅ Cloud infrastructure setup complete"
else
    echo "❌ Failed to setup Cloud infrastructure"
    exit 1
fi
echo ""

# Step 2: Build and deploy jobs
echo "🔨 Step 2: Building and deploying jobs..."
if ./scripts/deploy_jobs.sh; then
    echo "✅ Jobs deployed successfully"
else
    echo "❌ Failed to deploy jobs"
    exit 1
fi
echo ""

# Step 3: Install Python dependencies (if needed)
echo "🐍 Step 3: Checking Python dependencies..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing/updating dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

echo "✅ Python dependencies ready"
echo ""

# Step 4: Start local application
echo "🎬 Step 4: Starting Phoenix application..."

# Check if app is already running
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "⚠️ Application already running on port 8080"
    echo "Skipping startup..."
else
    echo "Starting application in background..."

    # Start app in background
    nohup python app.py > logs/app.log 2>&1 &
    app_pid=$!

    echo "Application PID: $app_pid"
    echo "Waiting for startup..."

    # Wait for app to start (max 30 seconds)
    for i in {1..30}; do
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo "✅ Application started successfully"
            break
        fi
        sleep 1
        echo -n "."
    done

    if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "❌ Application failed to start within 30 seconds"
        echo "Check logs: tail -f logs/app.log"
        exit 1
    fi
fi
echo ""

# Step 5: Run basic tests
echo "🧪 Step 5: Running basic tests..."
if ./scripts/test_job_execution.sh api; then
    echo "✅ Basic tests passed"
else
    echo "❌ Basic tests failed"
    echo "System may still work, but check the logs"
fi
echo ""

# Summary
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📋 What was set up:"
echo "  ✅ Cloud Tasks queue: reel-jobs-queue"
echo "  ✅ Service account: reel-jobs-sa"
echo "  ✅ Cloud Run Job: reel-stitching-job"
echo "  ✅ Phoenix application running on localhost:8080"
echo ""
echo "🔧 Next steps:"
echo "  1. Test stitching: ./scripts/test_job_execution.sh stitching"
echo "  2. Open Reel Maker: http://localhost:8080/reel-maker"
echo "  3. Create a project and add clips"
echo "  4. Click 'Stitch Clips' to test the job system"
echo ""
echo "📚 Useful commands:"
echo "  # Monitor job executions"
echo "  gcloud run jobs executions list --region=$REGION"
echo ""
echo "  # View job logs"
echo "  gcloud run jobs executions logs <EXECUTION_NAME> --region=$REGION"
echo ""
echo "  # Check queue status"
echo "  gcloud tasks queues describe reel-jobs-queue --location=$REGION"
echo ""
echo "  # Stop local app"
echo "  pkill -f 'python app.py'"
echo ""
echo "📖 Documentation:"
echo "  - Architecture: docs/CLOUD_RUN_JOBS_ARCHITECTURE.md"
echo "  - Testing Guide: docs/CLOUD_RUN_JOBS_TESTING.md"
echo ""

# Save important info to file
cat > .jobs_setup_info << EOF
Phoenix Cloud Run Jobs Setup
============================
Setup Date: $(date)
Project ID: $PROJECT_ID
Region: $REGION

Components:
- Queue: reel-jobs-queue
- Service Account: reel-jobs-sa@$PROJECT_ID.iam.gserviceaccount.com
- Job: reel-stitching-job
- App: http://localhost:8080

Test Commands:
- API tests: ./scripts/test_job_execution.sh api
- Full test: ./scripts/test_job_execution.sh stitching
- Direct test: ./scripts/test_job_execution.sh direct

Monitoring:
- Job executions: gcloud run jobs executions list --region=$REGION
- Queue status: gcloud tasks queues describe reel-jobs-queue --location=$REGION
- App logs: tail -f logs/app.log
EOF

echo "💾 Setup info saved to: .jobs_setup_info"
echo ""
echo "Ready to rock! 🚀"