#!/bin/bash
set -e

# Setup Cloud Tasks Queue for Reel Maker Jobs
# This script creates the necessary Cloud Tasks queue for job orchestration

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"phoenix-project-386"}
REGION=${GCP_REGION:-"us-central1"}
QUEUE_NAME="reel-jobs-queue"

echo "🚀 Setting up Cloud Tasks Queue for Reel Maker Jobs"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Queue: $QUEUE_NAME"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
    echo "❌ Error: Not authenticated with gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Set project
echo "📋 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable cloudtasks.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Check if queue already exists
if gcloud tasks queues describe $QUEUE_NAME --location=$REGION &>/dev/null; then
    echo "✅ Queue '$QUEUE_NAME' already exists"
else
    echo "📝 Creating Cloud Tasks queue: $QUEUE_NAME"

    # Create the queue
    gcloud tasks queues create $QUEUE_NAME \
        --location=$REGION \
        --max-dispatches-per-second=10 \
        --max-concurrent-dispatches=100 \
        --max-attempts=3 \
        --min-backoff=60s \
        --max-backoff=3600s \
        --max-doublings=16

    echo "✅ Successfully created queue: $QUEUE_NAME"
fi

# Create service account for jobs
JOB_SA_NAME="reel-jobs-sa"
JOB_SA_EMAIL="$JOB_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

echo "👤 Setting up service account: $JOB_SA_NAME"

if gcloud iam service-accounts describe $JOB_SA_EMAIL &>/dev/null; then
    echo "✅ Service account already exists: $JOB_SA_EMAIL"
else
    echo "📝 Creating service account..."
    gcloud iam service-accounts create $JOB_SA_NAME \
        --display-name="Reel Maker Jobs Service Account" \
        --description="Service account for Cloud Run Jobs processing video operations"

    echo "✅ Created service account: $JOB_SA_EMAIL"
fi

# Grant necessary permissions
echo "🔐 Granting IAM permissions..."

# Storage permissions for video files
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$JOB_SA_EMAIL" \
    --role="roles/storage.objectAdmin"

# Firestore permissions for job state
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$JOB_SA_EMAIL" \
    --role="roles/datastore.user"

# Logging permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$JOB_SA_EMAIL" \
    --role="roles/logging.logWriter"

# Monitoring permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$JOB_SA_EMAIL" \
    --role="roles/monitoring.metricWriter"

# Cloud Tasks permissions for triggering jobs
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$JOB_SA_EMAIL" \
    --role="roles/cloudtasks.enqueuer"

echo "✅ Granted all necessary permissions"

# Create Cloud Run Job configuration files
echo "📄 Creating Cloud Run Job configurations..."

mkdir -p config/cloud_run_jobs

# Video Stitching Job configuration
cat > config/cloud_run_jobs/video-stitching.yaml << EOF
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: reel-stitching-job
  labels:
    cloud.googleapis.com/location: $REGION
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    spec:
      template:
        metadata:
          annotations:
            run.googleapis.com/execution-environment: gen2
            run.googleapis.com/cpu-throttling: "false"
        spec:
          serviceAccountName: $JOB_SA_EMAIL
          timeoutSeconds: 900  # 15 minutes
          containers:
          - name: stitcher
            image: gcr.io/$PROJECT_ID/reel-stitching-job:latest
            resources:
              limits:
                memory: "4Gi"
                cpu: "2000m"
              requests:
                memory: "2Gi"
                cpu: "1000m"
            env:
            - name: GOOGLE_CLOUD_PROJECT
              value: "$PROJECT_ID"
            - name: VIDEO_STORAGE_BUCKET
              value: "phoenix-videos"
            - name: JOB_TIMEOUT_MINUTES
              value: "15"
            - name: LOG_LEVEL
              value: "INFO"
          restartPolicy: Never
          maxRetries: 3
EOF

echo "✅ Created video stitching job configuration"

# Display queue information
echo ""
echo "📊 Queue Information:"
gcloud tasks queues describe $QUEUE_NAME --location=$REGION

echo ""
echo "🎉 Cloud Tasks setup completed successfully!"
echo ""
echo "📋 Summary:"
echo "  ✅ Queue created: $QUEUE_NAME"
echo "  ✅ Service account: $JOB_SA_EMAIL"
echo "  ✅ IAM permissions granted"
echo "  ✅ Job configurations created"
echo ""
echo "🔧 Next steps:"
echo "  1. Build and deploy job images: ./scripts/deploy_jobs.sh"
echo "  2. Test job execution: ./scripts/test_job_execution.sh"
echo "  3. Monitor jobs: gcloud tasks queues describe $QUEUE_NAME --location=$REGION"
echo ""
echo "📚 Documentation:"
echo "  - Queue URL: https://console.cloud.google.com/cloudtasks/queue/$REGION/$QUEUE_NAME"
echo "  - Service Account: https://console.cloud.google.com/iam-admin/serviceaccounts"