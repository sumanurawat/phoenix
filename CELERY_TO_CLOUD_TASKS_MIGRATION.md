# Celery to Cloud Tasks Migration - Progress Report

## 🎯 Objective
Migrate from persistent Celery/Redis architecture to serverless Cloud Tasks + Cloud Run Jobs for AI generation.

**Benefits:**
- **Cost Savings**: ~$43/month (Redis + VPC + persistent worker elimination)
- **Scalability**: Jobs scale to thousands vs. single Redis broker limitation
- **Simplification**: No VPC connector, no persistent workers, no Redis maintenance
- **Resource Specialization**: Separate jobs for images (small/cheap) vs video (large/expensive)

---

## ✅ Completed (Phase 1)

### 1. Infrastructure Provisioning
- ✅ Created `infrastructure/gcp/provision_generation_jobs.sh`
- ✅ Provisioned Cloud Tasks queues:
  - `video-generation-queue` (10 dispatches/sec, 5 concurrent)
  - `image-generation-queue` (20 dispatches/sec, 10 concurrent)
- ✅ Configured IAM permissions for task enqueueing and job invocation

### 2. Video Generation Job
- ✅ Created `jobs/video_generation_job/main.py`
  - Implements money-safe contract (tokens debited upfront, refunded on failure)
  - Handles Veo API calls with proper error handling
  - Extracts thumbnails using ffmpeg
  - Uploads to Cloudflare R2
  - Updates Firestore state (pending → processing → draft/failed)
- ✅ Created `jobs/video_generation_job/Dockerfile`
  - Python 3.11-slim base
  - Includes ffmpeg for thumbnail extraction
  - 4GB RAM, 2 CPU configuration
- ✅ Created `jobs/video_generation_job/requirements.txt`

---

## 🚧 In Progress (Phase 2)

### 3. Image Generation Job (Next)
**TODO**: Create `jobs/image_generation_job/`
- [ ] `main.py` - Simpler than video (no ffmpeg, faster generation)
- [ ] `Dockerfile` - Lighter weight (1GB RAM, 1 CPU)
- [ ] `requirements.txt`

**Implementation Notes:**
- Image generation is simpler: no thumbnail extraction needed
- Uses `ImageGenerationService` (already exists)
- Uploads to R2 directly
- 1 token cost vs. 10 for video

---

## 📋 Remaining Tasks (Phase 3)

### 4. API Refactoring
**File**: `api/generation_routes.py` or `api/video_generation_routes.py`

**Changes Needed:**
1. Remove Celery imports:
   ```python
   # REMOVE:
   from celery_app import celery_app
   from jobs.async_video_generation_worker import generate_video_task

   # ADD:
   from google.cloud import tasks_v2
   from services.job_orchestrator import JobOrchestrator
   ```

2. Replace Celery task enqueueing:
   ```python
   # REMOVE:
   task = generate_video_task.apply_async(
       args=[creation_id],
       task_id=creation_id,
       countdown=2
   )

   # REPLACE WITH:
   job_orchestrator = JobOrchestrator()
   task = job_orchestrator.enqueue_job(
       queue_name="video-generation-queue",
       job_url="https://VIDEO_JOB_URL/execute",  # Cloud Run Job URL
       payload={"creationId": creation_id}
   )
   ```

3. Similar changes for image generation endpoint

**Critical**: The API still debits tokens upfront! Only the worker execution changes.

---

### 5. Cloud Build Configuration
**File**: `cloudbuild.yaml`

**Changes Needed:**
1. **ADD** build steps for new jobs:
   ```yaml
   # Build video generation job
   - name: 'gcr.io/cloud-builders/docker'
     args: ['build', '-t', 'gcr.io/$PROJECT_ID/video-generation-job', '-f', 'jobs/video_generation_job/Dockerfile', '.']

   - name: 'gcr.io/cloud-builders/docker'
     args: ['push', 'gcr.io/$PROJECT_ID/video-generation-job']

   # Deploy video generation job
   - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
     args:
       - 'gcloud'
       - 'run'
       - 'jobs'
       - 'deploy'
       - 'video-generation-job'
       - '--image=gcr.io/$PROJECT_ID/video-generation-job'
       - '--region=us-central1'
       - '--cpu=2'
       - '--memory=4Gi'
       - '--timeout=600'
       - '--max-retries=2'

   # Repeat for image generation job (with 1CPU/1Gi)
   ```

2. **REMOVE** Celery worker deployment steps
3. **REMOVE** `run_worker.py` execution from main service

---

### 6. Testing Plan
1. **Local Testing** (optional):
   - Test job logic by running `main.py` with test payload

2. **Production Testing**:
   - Deploy to production
   - Create test video generation → verify it completes
   - Create test image generation → verify it completes
   - Test failure scenarios (bad prompt) → verify refund works
   - Verify drafts UI shows all states correctly

3. **Load Testing**:
   - Create multiple concurrent requests
   - Verify jobs scale horizontally
   - Check Cloud Tasks queue metrics

---

### 7. Decommissioning (Final Step - ONLY AFTER TESTING)
**Script**: `infrastructure/gcp/decommission_celery.sh`

```bash
#!/bin/bash
# Run ONLY after new system is verified working

echo "⚠️  DECOMMISSIONING CELERY/REDIS INFRASTRUCTURE"
echo "This will delete:"
echo "  - phoenix-video-worker Cloud Run service"
echo "  - phoenix-cache-prod Redis instance (~\$25/mo)"
echo "  - VPC connector (~\$18/mo)"
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted"
    exit 1
fi

# Delete Celery worker
gcloud run services delete phoenix-video-worker \
    --region=us-central1 \
    --project=phoenix-project-386 \
    --quiet

# Delete Redis
gcloud redis instances delete phoenix-cache-prod \
    --region=us-central1 \
    --project=phoenix-project-386 \
    --quiet

# Delete VPC connector
gcloud compute networks vpc-access connectors delete phoenix-vpc-connector \
    --region=us-central1 \
    --project=phoenix-project-386 \
    --quiet

echo ""
echo "✅ Decommissioning complete"
echo "💰 Monthly savings: ~\$43"
echo ""
echo "Cleanup remaining code:"
echo "  - Remove jobs/async_video_generation_worker.py"
echo "  - Remove jobs/async_image_generation_worker.py"
echo "  - Remove celery_app.py"
echo "  - Remove run_worker.py"
echo "  - Remove celery/redis from requirements.txt"
```

---

## 🔧 Architecture Comparison

### Before (Celery/Redis)
```
User Request → API (debit tokens)
               ↓
           Celery Task → Redis Queue
                          ↓
                    Persistent Worker (always running)
                          ↓
                    Generation + R2 Upload
                          ↓
                    Update Firestore (draft/failed)
```

**Problems:**
- Redis: $25/mo fixed cost
- VPC Connector: $18/mo fixed cost
- Worker: Runs 24/7 even when idle
- Single point of failure (Redis)
- Limited scalability (one broker)

### After (Cloud Tasks + Jobs)
```
User Request → API (debit tokens)
               ↓
           Cloud Tasks Queue (serverless, $0 when idle)
               ↓
           Cloud Run Job (spins up on-demand)
               ↓
           Generation + R2 Upload
               ↓
           Update Firestore (draft/failed)
               ↓
           Job shuts down (pay per second)
```

**Benefits:**
- No fixed costs - pay per execution
- Auto-scales to thousands of jobs
- No single point of failure
- Specialized resources (image=small, video=large)
- Simpler architecture (no VPC needed)

---

## 📊 Cost Analysis

### Current Monthly Costs
- Redis (1GB): $25
- VPC Connector: $18
- Worker (always-on): ~$0 (free tier, but uses quota)
- **Total**: ~$43/month minimum

### New Monthly Costs (Projected)
- Cloud Tasks: $0.40 per million tasks
- Video Job (4GB, 2CPU): ~$0.000024/second
  - 100s video = $0.0024 per video
  - 1000 videos/month = $2.40
- Image Job (1GB, 1CPU): ~$0.000006/second
  - 30s image = $0.00018 per image
  - 5000 images/month = $0.90
- **Total**: ~$3.30/month for moderate usage

**Savings**: $39.70/month (92% reduction)

---

## ⚠️ Critical Contracts

### Money Safety (Non-Negotiable)
1. **API debits tokens UPFRONT** (before enqueueing)
2. **Job refunds on failure** (atomic Firestore transaction)
3. **Idempotent refunds** (check `refunded` flag)
4. **Job always updates state** (never leaves orphaned "processing")

### State Management
- **Server** creates `pending` → enqueues task
- **Job** updates `processing` → calls API → updates `draft` or `failed`
- **User** sees real-time status in Firestore (drafts tab)

### Error Handling
- Content policy violations → mark `failed` + refund
- Transient API errors → Cloud Tasks auto-retries (3 max)
- Unexpected errors → mark `failed` + refund

---

## 🚀 Next Actions

1. **Create image generation job** (similar to video, but simpler)
2. **Refactor API** to use Cloud Tasks instead of Celery
3. **Update cloudbuild.yaml** to build/deploy jobs
4. **Deploy to production** via GitHub push (triggers Cloud Build)
5. **Test thoroughly** (video, image, failures, refunds)
6. **Monitor for 24-48 hours** before decommissioning old system
7. **Run decommission script** to delete Redis/VPC/worker
8. **Clean up code** (remove Celery files)

---

## 📝 Notes

- Video job needs ffmpeg (included in Dockerfile)
- Image job doesn't need ffmpeg (lighter/cheaper)
- Both jobs use same R2 credentials (from secrets)
- Cloud Tasks handles retries automatically (max 3 attempts)
- Jobs timeout after 10 minutes (video) or 5 minutes (image)
- Firebase is initialized once per job execution (lazy init pattern)

---

**Status**: Phase 1 Complete ✅ | Phase 2 In Progress 🚧 | Ready for Image Job Creation
