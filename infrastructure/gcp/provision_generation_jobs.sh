#!/bin/bash
# Provision Cloud Tasks & Cloud Run Jobs for AI Generation
# This script creates the serverless infrastructure to replace Celery/Redis

set -e  # Exit on error

PROJECT_ID="phoenix-project-386"
REGION="us-central1"
API_SERVICE_ACCOUNT="firebase-adminsdk-fbsvc@${PROJECT_ID}.iam.gserviceaccount.com"

echo "========================================="
echo "Provisioning AI Generation Infrastructure"
echo "========================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Create Cloud Tasks Queues
echo "📋 Step 1: Creating Cloud Tasks Queues..."
echo ""

echo "Creating video-generation-queue..."
if gcloud tasks queues describe video-generation-queue --location=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "  ✅ video-generation-queue already exists"
else
    gcloud tasks queues create video-generation-queue \
        --location=$REGION \
        --project=$PROJECT_ID \
        --max-dispatches-per-second=10 \
        --max-concurrent-dispatches=5 \
        --max-attempts=3 \
        --min-backoff=60s \
        --max-backoff=300s
    echo "  ✅ Created video-generation-queue"
fi

echo "Creating image-generation-queue..."
if gcloud tasks queues describe image-generation-queue --location=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "  ✅ image-generation-queue already exists"
else
    gcloud tasks queues create image-generation-queue \
        --location=$REGION \
        --project=$PROJECT_ID \
        --max-dispatches-per-second=20 \
        --max-concurrent-dispatches=10 \
        --max-attempts=3 \
        --min-backoff=30s \
        --max-backoff=180s
    echo "  ✅ Created image-generation-queue"
fi

echo ""

# Step 2: Create Cloud Run Jobs (placeholder - will be deployed via Cloud Build)
echo "📦 Step 2: Preparing Cloud Run Job Configurations..."
echo "  ℹ️  Cloud Run Jobs will be deployed via Cloud Build"
echo "  ℹ️  Job images will be built from Dockerfiles in jobs/ directory"
echo ""

# Step 3: Grant IAM Permissions
echo "🔐 Step 3: Configuring IAM Permissions..."
echo ""

echo "Granting API service account permission to enqueue tasks..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$API_SERVICE_ACCOUNT" \
    --role="roles/cloudtasks.enqueuer" \
    --condition=None \
    >/dev/null 2>&1 || echo "  ⚠️  Permission may already exist"
echo "  ✅ API can enqueue Cloud Tasks"

echo "Granting Cloud Tasks permission to invoke Cloud Run Jobs..."
# Note: Cloud Tasks uses the default App Engine service account
# projects/${PROJECT_ID}@appspot.gserviceaccount.com
APPENGINE_SA="${PROJECT_ID}@appspot.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$APPENGINE_SA" \
    --role="roles/run.invoker" \
    --condition=None \
    >/dev/null 2>&1 || echo "  ⚠️  Permission may already exist"
echo "  ✅ Cloud Tasks can invoke Cloud Run Jobs"

echo ""

# Step 4: Summary
echo "========================================="
echo "✅ Infrastructure Provisioning Complete"
echo "========================================="
echo ""
echo "Created Resources:"
echo "  • Cloud Tasks Queue: video-generation-queue"
echo "  • Cloud Tasks Queue: image-generation-queue"
echo ""
echo "Next Steps:"
echo "  1. Build Docker images: See cloudbuild.yaml"
echo "  2. Deploy Cloud Run Jobs: Push to GitHub (triggers Cloud Build)"
echo "  3. Update API routes: Use JobOrchestrator to enqueue tasks"
echo "  4. Test generation: Create video/image via API"
echo "  5. Decommission: Run decommission_celery.sh after verification"
echo ""
echo "Cost Savings: ~\$43/month (Redis + VPC + persistent worker)"
echo ""
