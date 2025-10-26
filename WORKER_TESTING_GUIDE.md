# Worker Testing Guide

## Current Worker Status ✅

**Service:** `phoenix-video-worker`
**Status:** `Ready: True`
**Revision:** `phoenix-video-worker-00006-xvp`
**Celery:** Connected to Redis at `10.95.244.51:6379`
**Registered Tasks:**
- `jobs.async_video_generation_worker.generate_video_task`
- `jobs.async_video_generation_worker.cleanup_orphaned_processing`

---

## Architecture Overview

### How It Works

```
User Request (Frontend)
    ↓
POST /api/generate/video (API Service)
    ↓
1. Debit tokens (atomic transaction)
2. Create 'creation' document (status: pending)
3. Queue Celery task → Redis
4. Return 202 Accepted immediately
    ↓
Redis Queue (10.95.244.51:6379)
    ↓
Celery Worker (phoenix-video-worker)
    ↓
1. Update status → processing
2. Call Veo API (60-120s)
3. Upload video to R2
4. Update status → draft (with mediaUrl)
    ↓
User polls /api/generate/drafts
    ↓
See: pending → processing → draft
```

### Scaling Behavior

| Metric | Value | Meaning |
|--------|-------|---------|
| Min instances | 1 | Always 1 worker running (costs ~$50/month) |
| Max instances | 10 | Can scale to 10 workers under load |
| Concurrency | 1 | Each worker processes 1 video at a time |
| Timeout | 3600s | 1 hour max per task |

**Example Scaling:**
- 1 video queued → 1 worker (min instance)
- 3 videos queued → 3 workers spin up
- 10 videos queued → 10 workers (max)
- Videos complete → scales back to 1 worker

---

## Cost Breakdown

### Fixed Costs (Monthly)

| Resource | Cost | Details |
|----------|------|---------|
| Worker (min=1) | $50-60 | 4Gi RAM + 2 vCPU always running |
| Redis (1GB BASIC) | $40 | Memorystore instance |
| VPC Connector | $10 | Network connectivity |
| **Total Fixed** | **~$100-110** | Even with 0 videos generated |

### Variable Costs (Per Video)

| Resource | Cost | Details |
|----------|------|---------|
| Veo API | $0.32 | Video generation (8s @ $0.04/second) |
| Worker compute | $0.02 | ~90s processing time |
| R2 storage | $0.00003 | Cloudflare R2 (negligible) |
| **Total Per Video** | **~$0.36** | At scale |

### Cost Optimization

**Option 1: Current Setup (min=1) - Recommended for Production**
- ✅ Instant processing (no cold start)
- ✅ Worker always listening to queue
- ❌ Costs ~$100/month even with no usage

**Option 2: Min=0 - Cost-Optimized**
```bash
gcloud run services update phoenix-video-worker \
  --min-instances=0 \
  --region=us-central1 \
  --project=phoenix-project-386
```
- ✅ Save ~$50/month worker cost
- ❌ Cold start delay: 30-60 seconds for first task after idle
- ❌ Worker stops polling when no tasks (may miss tasks temporarily)

---

## Testing the Worker

### Test 1: Check Worker is Running

```bash
# Check service status
gcloud run services describe phoenix-video-worker \
  --region=us-central1 \
  --project=phoenix-project-386 \
  --format="value(status.conditions[0].status)"

# Expected: True
```

### Test 2: Check Celery Logs

```bash
# View worker logs
gcloud run services logs read phoenix-video-worker \
  --region=us-central1 \
  --limit=50 \
  --project=phoenix-project-386

# Look for:
# ✅ "celery@localhost v5.4.0"
# ✅ "transport: redis://10.95.244.51:6379/0"
# ✅ "registered: generate_video_task, cleanup_orphaned_processing"
```

### Test 3: Submit Test Video Generation (Requires Auth)

**Prerequisites:**
- Firebase auth token
- User with sufficient token balance (10 tokens)

**API Request:**
```bash
# Get your Firebase ID token first (from browser/app)
FIREBASE_TOKEN="your-firebase-id-token-here"

# Submit video generation
curl -X POST https://phoenix-hpbuj2rr6q-uc.a.run.app/api/generate/video \
  -H "Authorization: Bearer $FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene sunset over mountains",
    "aspectRatio": "9:16",
    "duration": 8
  }'

# Expected Response (202 Accepted):
{
  "success": true,
  "creationId": "uuid-here",
  "cost": 10,
  "status": "pending",
  "estimatedTime": "60-120 seconds"
}
```

**Monitor Progress:**
```bash
# Poll drafts endpoint
curl https://phoenix-hpbuj2rr6q-uc.a.run.app/api/generate/drafts \
  -H "Authorization: Bearer $FIREBASE_TOKEN"

# Watch status transition:
# 1. status: "pending"  (queued in Redis)
# 2. status: "processing", progress: 0.0 - 1.0  (worker running)
# 3. status: "draft", mediaUrl: "https://..."  (success!)
# OR
# 3. status: "failed", error: "..."  (failure, tokens refunded)
```

### Test 4: Monitor Worker Activity

```bash
# Follow worker logs in real-time
gcloud run services logs read phoenix-video-worker \
  --region=us-central1 \
  --project=phoenix-project-386 \
  --follow

# During video generation, you'll see:
# 🎬 Starting video generation for creation: <id>
# 🎨 Veo generation took 90.5s
# 📤 Uploading video to R2...
# ✅ Video generation completed
```

### Test 5: Check Firestore State

1. Go to Firebase Console → Firestore
2. Navigate to `creations` collection
3. Find your creation document
4. Watch fields update in real-time:
   - `status`: "pending" → "processing" → "draft"
   - `progress`: 0.0 → 0.3 → 0.5 → 0.8 → 1.0
   - `mediaUrl`: appears when status="draft"
   - `workerStartedAt`: timestamp when worker picked up task

---

## Troubleshooting

### Issue: Worker logs show "Cannot connect to Redis"

**Cause:** VPC connector not configured
**Fix:**
```bash
gcloud run services update phoenix-video-worker \
  --vpc-connector=phoenix-vpc-connector \
  --vpc-egress=private-ranges-only \
  --region=us-central1 \
  --project=phoenix-project-386
```

### Issue: Tasks stuck in "pending" status

**Checks:**
1. Is worker running?
   ```bash
   gcloud run services describe phoenix-video-worker --region=us-central1 --project=phoenix-project-386
   ```

2. Is worker connected to Redis?
   ```bash
   gcloud run services logs read phoenix-video-worker --region=us-central1 --limit=20
   # Look for "transport: redis://..."
   ```

3. Is Redis accessible?
   ```bash
   gcloud redis instances describe phoenix-cache-prod --region=us-central1
   # Status should be READY
   ```

### Issue: Worker crashes or restarts

**Check logs:**
```bash
gcloud run services logs read phoenix-video-worker \
  --region=us-central1 \
  --limit=100 \
  --project=phoenix-project-386 \
  | grep -i "error\|traceback\|exception"
```

**Common causes:**
- Firebase not initialized → Fixed with lazy initialization
- R2 credentials invalid → Check secrets in Secret Manager
- Veo API quota exceeded → Check Vertex AI quotas
- Out of memory → Increase `--memory` (currently 4Gi)

---

## Monitoring Commands

```bash
# Check worker health
gcloud run services describe phoenix-video-worker \
  --region=us-central1 --project=phoenix-project-386

# View recent logs
gcloud run services logs read phoenix-video-worker \
  --region=us-central1 --limit=50

# Check Redis status
gcloud redis instances describe phoenix-cache-prod --region=us-central1

# List active instances
gcloud run revisions list \
  --service=phoenix-video-worker \
  --region=us-central1 \
  --project=phoenix-project-386

# Check VPC connector
gcloud compute networks vpc-access connectors describe phoenix-vpc-connector \
  --region=us-central1
```

---

## Production Checklist

Before going live:

- [ ] Test video generation end-to-end
- [ ] Verify token debit/refund works
- [ ] Test failure scenarios (invalid prompts, API errors)
- [ ] Monitor worker logs for errors
- [ ] Set up alerting for worker failures
- [ ] Decide on min-instances (0 vs 1) based on budget/latency tradeoff
- [ ] Test concurrent video generation (queue multiple)
- [ ] Verify cleanup task runs (check Firestore for orphaned "processing" states)
- [ ] Test publish-to-feed flow
- [ ] Monitor costs in GCP billing

---

## Next Steps

1. **Frontend Integration**: Update UI to:
   - Poll `/api/generate/drafts` every 2-3 seconds
   - Show progress bar (use `progress` field)
   - Display estimated time remaining
   - Show all states: pending, processing, draft, failed

2. **Monitoring**: Set up Cloud Monitoring alerts for:
   - Worker service crashes
   - Redis connection errors
   - High task failure rate (>5%)
   - Orphaned processing states

3. **Cost Optimization**: Decide on:
   - Keep min=1 for instant processing?
   - Or set min=0 to save $50/month (adds 30-60s cold start)?

4. **Scale Testing**: Test with:
   - 5 concurrent video generations
   - 10 concurrent (max instances)
   - Monitor autoscaling behavior
