#!/bin/bash
#
# Deploy Video Stitching Cloud Run Job
# This script builds and deploys the video stitching job to Google Cloud Run
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-phoenix-project-386}"
REGION="${GCP_REGION:-us-central1}"
JOB_NAME="reel-stitching-job"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}"
SERVICE_ACCOUNT="phoenix-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "${GREEN}🚀 Deploying Video Stitching Cloud Run Job${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job Name: ${JOB_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install it first.${NC}"
    exit 1
fi

# Set project
echo -e "\n${YELLOW}📋 Setting GCP project...${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "\n${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudtasks.googleapis.com \
    storage.googleapis.com \
    firestore.googleapis.com \
    --project ${PROJECT_ID}

# Build the Docker image using Cloud Build
echo -e "\n${YELLOW}🏗️  Building Docker image with Cloud Build...${NC}"
echo "Using optimized build config: jobs/video_stitching/cloudbuild.yaml"

gcloud builds submit \
    --config jobs/video_stitching/cloudbuild.yaml \
    --project ${PROJECT_ID}

# Deploy or update the Cloud Run Job
echo -e "\n${YELLOW}🚀 Deploying Cloud Run Job...${NC}"

# Check if job exists
if gcloud run jobs describe ${JOB_NAME} --region ${REGION} --project ${PROJECT_ID} &>/dev/null; then
    echo "Job exists, updating..."
    COMMAND="update"
else
    echo "Job doesn't exist, creating..."
    COMMAND="create"
fi

gcloud run jobs ${COMMAND} ${JOB_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --max-retries 3 \
    --task-timeout 15m \
    --memory 4Gi \
    --cpu 2 \
    --parallelism 1 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars "GCP_REGION=${REGION}" \
    --set-env-vars "VIDEO_STORAGE_BUCKET=phoenix-videos" \
    --set-env-vars "JOB_TIMEOUT_MINUTES=15" \
    --set-env-vars "MAX_RETRY_ATTEMPTS=3" \
    --service-account ${SERVICE_ACCOUNT} \
    --execute-now=false

# Create Cloud Tasks queue if it doesn't exist
echo -e "\n${YELLOW}📥 Setting up Cloud Tasks queue...${NC}"
if ! gcloud tasks queues describe reel-jobs-queue --location ${REGION} --project ${PROJECT_ID} &>/dev/null; then
    echo "Creating Cloud Tasks queue..."
    gcloud tasks queues create reel-jobs-queue \
        --location ${REGION} \
        --project ${PROJECT_ID} \
        --max-concurrent-dispatches 5 \
        --max-attempts 3 \
        --max-retry-duration 1h
else
    echo "Cloud Tasks queue already exists."
fi

# Test the job (optional)
if [ "$1" == "--test" ]; then
    echo -e "\n${YELLOW}🧪 Running test execution...${NC}"
    gcloud run jobs execute ${JOB_NAME} \
        --region ${REGION} \
        --project ${PROJECT_ID} \
        --wait
fi

echo -e "\n${GREEN}✅ Deployment complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Job URL: https://console.cloud.google.com/run/jobs/details/${REGION}/${JOB_NAME}?project=${PROJECT_ID}"
echo ""
echo "To execute the job manually:"
echo "  gcloud run jobs execute ${JOB_NAME} --region ${REGION} --project ${PROJECT_ID}"
echo ""
echo "To view logs:"
echo "  gcloud logging read 'resource.type=\"cloud_run_job\" resource.labels.job_name=\"${JOB_NAME}\"' --limit 50 --project ${PROJECT_ID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
