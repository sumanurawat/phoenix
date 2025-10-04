#!/bin/bash
set -e

# Deploy Cloud Run Jobs for Reel Maker
# This script builds and deploys all job containers

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"phoenix-project-386"}
REGION=${GCP_REGION:-"us-central1"}

echo "🚀 Deploying Cloud Run Jobs for Reel Maker"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Check prerequisites
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    exit 1
fi

# Verify we're in the right directory
if [ ! -f "app.py" ] || [ ! -d "jobs" ]; then
    echo "❌ Error: Please run this script from the Phoenix project root directory"
    exit 1
fi

# Configure Docker for GCR
echo "🔧 Configuring Docker for Google Container Registry..."
gcloud auth configure-docker

# Set project
gcloud config set project $PROJECT_ID

# Function to build and push image
build_and_push() {
    local job_name=$1
    local job_dir=$2
    local image_name="gcr.io/$PROJECT_ID/$job_name:latest"

    echo ""
    echo "📦 Building $job_name..."
    echo "Job directory: $job_dir"
    echo "Image: $image_name"

    # Check if Dockerfile exists
    if [ ! -f "$job_dir/Dockerfile" ]; then
        echo "❌ Error: Dockerfile not found in $job_dir"
        return 1
    fi

    # Build image
    echo "🔨 Building Docker image..."
    docker build -t $image_name -f "$job_dir/Dockerfile" .

    # Push image
    echo "📤 Pushing image to GCR..."
    docker push $image_name

    echo "✅ Successfully built and pushed $job_name"
    return 0
}

# Function to deploy Cloud Run Job
deploy_job() {
    local job_name=$1
    local config_file=$2

    echo ""
    echo "☁️ Deploying Cloud Run Job: $job_name"

    if [ ! -f "$config_file" ]; then
        echo "❌ Error: Configuration file not found: $config_file"
        return 1
    fi

    # Replace placeholder values in config
    temp_config="/tmp/${job_name}-config.yaml"
    sed "s/\$PROJECT_ID/$PROJECT_ID/g; s/\$REGION/$REGION/g" "$config_file" > "$temp_config"

    # Deploy or update the job
    echo "📋 Deploying job configuration..."
    gcloud run jobs replace "$temp_config" --region=$REGION

    # Clean up temp file
    rm "$temp_config"

    echo "✅ Successfully deployed $job_name"
    return 0
}

# Build and deploy jobs
jobs_built=0
jobs_deployed=0

echo ""
echo "🏗️ Building job images..."

# Video Stitching Job
if build_and_push "reel-stitching-job" "jobs/video_stitching"; then
    ((jobs_built++))

    if deploy_job "reel-stitching-job" "config/cloud_run_jobs/video-stitching.yaml"; then
        ((jobs_deployed++))
    fi
fi

# Future: Video Generation Job
# if build_and_push "reel-generation-job" "jobs/video_generation"; then
#     ((jobs_built++))
#
#     if deploy_job "reel-generation-job" "config/cloud_run_jobs/video-generation.yaml"; then
#         ((jobs_deployed++))
#     fi
# fi

echo ""
echo "📊 Deployment Summary:"
echo "  🔨 Images built: $jobs_built"
echo "  ☁️ Jobs deployed: $jobs_deployed"

if [ $jobs_deployed -gt 0 ]; then
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📋 Deployed Jobs:"
    gcloud run jobs list --region=$REGION --filter="metadata.name:reel-"

    echo ""
    echo "🔧 Testing Commands:"
    echo "  Test video stitching: ./scripts/test_job_execution.sh stitching"
    echo "  Monitor jobs: gcloud run jobs executions list --region=$REGION"
    echo "  View logs: gcloud logging read 'resource.type=\"cloud_run_job\"' --limit=50"

else
    echo "❌ No jobs were deployed successfully"
    exit 1
fi

echo ""
echo "📚 Useful Commands:"
echo "  # List all jobs"
echo "  gcloud run jobs list --region=$REGION"
echo ""
echo "  # Get job details"
echo "  gcloud run jobs describe reel-stitching-job --region=$REGION"
echo ""
echo "  # View job executions"
echo "  gcloud run jobs executions list --region=$REGION"
echo ""
echo "  # View execution logs"
echo "  gcloud run jobs executions logs <EXECUTION_NAME> --region=$REGION"
echo ""
echo "  # Update job (after code changes)"
echo "  ./scripts/deploy_jobs.sh"