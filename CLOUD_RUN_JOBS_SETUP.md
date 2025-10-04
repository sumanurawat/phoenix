# Cloud Run Jobs Setup Guide

## Overview

Your Reel Maker uses **Cloud Run Jobs** to process video stitching in the cloud. Even when running the Flask app locally, it triggers real cloud jobs in GCP.

## The Problem You Experienced

You saw this behavior:
- ✅ Flask app running locally
- ✅ "Using Cloud Run Jobs for stitching" message
- ✅ Job ID created in Firestore
- ❌ Job stuck in "queued" status
- ❌ No actual processing happening

**Root Cause**: The Cloud Run Job (`reel-stitching-job`) doesn't exist in your GCP project yet!

## Architecture

```
┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│   Local      │      │   Cloud     │      │  Cloud Run   │
│   Flask      │─────>│   Tasks     │─────>│    Job       │
│   (8080)     │      │   Queue     │      │  (GCP)       │
└──────────────┘      └─────────────┘      └──────────────┘
       │                                            │
       │                                            │
       └────────────> Firestore <──────────────────┘
                    (Job Status)
```

### How It Works

1. **User clicks "Stitch"** in Reel Maker UI
2. **Flask API** (`localhost:8080`) receives request
3. **Job Orchestrator** creates Firestore record with status "queued"
4. **Cloud Tasks** enqueues the job
5. **Cloud Run Job** (in GCP) picks up the task and processes it
6. **Firestore** updates with progress/completion status
7. **Frontend** polls Firestore and shows progress

## Prerequisites

### 1. GCP Project Setup
- Project ID: `phoenix-project-386`
- Region: `us-central1`
- Billing enabled

### 2. Required APIs
- Cloud Run API
- Cloud Build API
- Cloud Tasks API
- Cloud Storage API
- Firestore API

### 3. Service Account
Create a service account with these roles:
```bash
gcloud iam service-accounts create phoenix-cloud-run \
    --display-name="Phoenix Cloud Run Service Account" \
    --project=phoenix-project-386

gcloud projects add-iam-policy-binding phoenix-project-386 \
    --member="serviceAccount:phoenix-cloud-run@phoenix-project-386.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

gcloud projects add-iam-policy-binding phoenix-project-386 \
    --member="serviceAccount:phoenix-cloud-run@phoenix-project-386.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding phoenix-project-386 \
    --member="serviceAccount:phoenix-cloud-run@phoenix-project-386.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### 4. Storage Bucket
Create the video storage bucket:
```bash
gsutil mb -p phoenix-project-386 -l us-central1 gs://phoenix-videos
gsutil iam ch serviceAccount:phoenix-cloud-run@phoenix-project-386.iam.gserviceaccount.com:objectAdmin gs://phoenix-videos
```

## Deployment

### Quick Deploy

```bash
cd /Users/sumanurawat/Documents/GitHub/phoenix
./deploy_stitching_job.sh
```

This script will:
1. ✅ Enable required GCP APIs
2. ✅ Build Docker image with Cloud Build
3. ✅ Deploy Cloud Run Job
4. ✅ Create Cloud Tasks queue
5. ✅ Configure all necessary settings

### Deploy with Test

To deploy AND run a test execution:
```bash
./deploy_stitching_job.sh --test
```

### Manual Deployment

If you prefer manual control:

```bash
# 1. Set project
gcloud config set project phoenix-project-386

# 2. Build image
gcloud builds submit \
    --tag gcr.io/phoenix-project-386/reel-stitching-job:latest \
    -f jobs/video_stitching/Dockerfile \
    .

# 3. Deploy job
gcloud run jobs create reel-stitching-job \
    --image gcr.io/phoenix-project-386/reel-stitching-job:latest \
    --region us-central1 \
    --max-retries 3 \
    --task-timeout 15m \
    --memory 4Gi \
    --cpu 2 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=phoenix-project-386" \
    --set-env-vars "VIDEO_STORAGE_BUCKET=phoenix-videos" \
    --service-account phoenix-cloud-run@phoenix-project-386.iam.gserviceaccount.com

# 4. Create Cloud Tasks queue
gcloud tasks queues create reel-jobs-queue \
    --location us-central1 \
    --max-concurrent-dispatches 5
```

## Verification

### Check Job Exists
```bash
gcloud run jobs list --region us-central1 --project phoenix-project-386
```

Expected output:
```
JOB                    REGION        CREATED
reel-stitching-job     us-central1   2025-10-03
```

### View Job Details
```bash
gcloud run jobs describe reel-stitching-job \
    --region us-central1 \
    --project phoenix-project-386
```

### List Executions
```bash
gcloud run jobs executions list \
    --job reel-stitching-job \
    --region us-central1 \
    --project phoenix-project-386
```

### Test Execute Job Manually
```bash
gcloud run jobs execute reel-stitching-job \
    --region us-central1 \
    --project phoenix-project-386 \
    --wait
```

## Monitoring

### View Real-Time Logs
```bash
gcloud logging tail \
    "resource.type=cloud_run_job AND resource.labels.job_name=reel-stitching-job" \
    --project phoenix-project-386
```

### View Recent Logs
```bash
gcloud logging read \
    "resource.type=cloud_run_job AND resource.labels.job_name=reel-stitching-job" \
    --limit 50 \
    --project phoenix-project-386
```

### GCP Console Links

- **Cloud Run Jobs**: https://console.cloud.google.com/run/jobs?project=phoenix-project-386
- **Specific Job**: https://console.cloud.google.com/run/jobs/details/us-central1/reel-stitching-job?project=phoenix-project-386
- **Cloud Tasks**: https://console.cloud.google.com/cloudtasks?project=phoenix-project-386
- **Firestore Jobs Collection**: https://console.cloud.google.com/firestore/databases/-default-/data/panel/reel_jobs?project=phoenix-project-386
- **Cloud Storage**: https://console.cloud.google.com/storage/browser/phoenix-videos?project=phoenix-project-386

## Troubleshooting

### Issue: Job stuck in "queued" status

**Cause**: Cloud Run Job not deployed or Cloud Tasks queue misconfigured

**Solution**:
1. Verify job exists: `gcloud run jobs list --region us-central1`
2. Deploy if missing: `./deploy_stitching_job.sh`
3. Check Cloud Tasks queue: `gcloud tasks queues describe reel-jobs-queue --location us-central1`

### Issue: "Service account not found" error

**Cause**: Service account doesn't exist or lacks permissions

**Solution**:
```bash
# Create service account
gcloud iam service-accounts create phoenix-cloud-run --project=phoenix-project-386

# Grant permissions (see Prerequisites section)
```

### Issue: "Permission denied" in Cloud Storage

**Cause**: Service account lacks storage permissions

**Solution**:
```bash
gsutil iam ch serviceAccount:phoenix-cloud-run@phoenix-project-386.iam.gserviceaccount.com:objectAdmin gs://phoenix-videos
```

### Issue: Build fails with "Dockerfile not found"

**Cause**: Running from wrong directory

**Solution**:
```bash
cd /Users/sumanurawat/Documents/GitHub/phoenix
./deploy_stitching_job.sh
```

### Issue: Job fails with "Firestore not initialized"

**Cause**: Missing Firebase credentials

**Solution**:
Ensure service account has Firestore permissions and credentials are properly configured.

## Cost Considerations

### Cloud Run Jobs Pricing
- **CPU**: $0.00002400 per vCPU-second
- **Memory**: $0.00000250 per GiB-second
- **Requests**: $0.40 per million

### Example Calculation (per job)
- Duration: 2 minutes (120 seconds)
- CPU: 2 vCPUs
- Memory: 4 GiB
- Cost: ~$0.012 per job

### Monthly Estimates
- 100 jobs/month: ~$1.20
- 1,000 jobs/month: ~$12.00
- 10,000 jobs/month: ~$120.00

## Development Workflow

### Local Development
When running `./start_local.sh`:
- ✅ Flask app runs locally (localhost:8080)
- ✅ Cloud Tasks client initializes
- ✅ Jobs are triggered in **real GCP Cloud Run**
- ✅ Processing happens in the cloud, not locally

### Testing Changes
To test job changes:
```bash
# 1. Make changes to jobs/video_stitching/
# 2. Redeploy
./deploy_stitching_job.sh

# 3. Test from local Flask app or manually
gcloud run jobs execute reel-stitching-job --region us-central1 --wait
```

### Production Deployment
Both Flask app AND Cloud Run Jobs need deployment:
```bash
# Deploy Flask app
gcloud builds submit --config cloudbuild.yaml

# Deploy Cloud Run Jobs
./deploy_stitching_job.sh
```

## Next Steps

1. **Deploy the job**: Run `./deploy_stitching_job.sh`
2. **Verify deployment**: Check GCP Console
3. **Test locally**: Start Flask and try stitching a reel
4. **Monitor**: Watch logs and Firestore for progress
5. **Scale**: Adjust CPU/memory based on performance

## Additional Resources

- [Cloud Run Jobs Documentation](https://cloud.google.com/run/docs/create-jobs)
- [Cloud Tasks Documentation](https://cloud.google.com/tasks/docs)
- [Firestore Documentation](https://cloud.google.com/firestore/docs)
