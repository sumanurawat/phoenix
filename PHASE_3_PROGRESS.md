# Phase 3 Implementation Progress

**Date:** October 25, 2025
**Status:** 🟡 **READY FOR PROVISIONING & DEPLOYMENT**

---

## ✅ Completed Components

### 1. Infrastructure Scripts
- ✅ `infrastructure/gcp/redis-memorystore.sh` - Production-grade provisioning script
- ✅ `infrastructure/README.md` - Complete infrastructure documentation
- ✅ Cost tracking labels configured (`app=phoenix,service=X,phase=3`)

### 2. Backend Implementation
- ✅ `jobs/async_video_generation_worker.py` - Worker with Sora-style state management
- ✅ `api/video_generation_routes.py` - 5 endpoints for complete drafts experience
- ✅ Atomic token transactions with refund logic
- ✅ Idempotent operations (safe to retry)
- ✅ Comprehensive error handling (permanent vs transient failures)

### 3. Dependencies
- ✅ Added `celery==5.4.0` to requirements.txt
- ✅ Added `redis==5.2.1` to requirements.txt

---

## 📋 API Endpoints Implemented

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/generate/video` | POST | Create video generation (debit tokens, queue job) |
| `/api/generate/drafts` | GET | List all creations (Sora-style) |
| `/api/generate/video/<id>` | GET | Get single creation status |
| `/api/generate/video/<id>` | DELETE | Delete draft/failed creation |
| `/api/generate/video/<id>/publish` | POST | Publish draft to feed |

---

## 🎯 State Management (Sora-Style)

```
User submits prompt
   ↓
pending (visible in drafts, tokens debited)
   ↓
processing (worker started, progress updates)
   ↓
draft (success - ready to publish) ✅
   OR
failed (error shown, tokens refunded) 💰
```

**Key Features:**
- ✅ All states visible in drafts until deleted
- ✅ Failed generations show error message
- ✅ Automatic token refunds for failures
- ✅ Progress tracking during processing
- ✅ No orphaned "processing" states (worker always updates)

---

## 🚧 Pending Implementation

### 1. Celery App Configuration
**File:** `celery_app.py`

**Status:** Documented in `PHASE_3_IMPLEMENTATION_PLAN.md` (lines 153-196)

**Next Steps:**
```bash
# Create celery_app.py with Redis configuration
# Integrate with Flask app context
```

### 2. Flask Integration
**File:** `app.py`

**Changes Needed:**
1. Import `celery_app`
2. Register `video_generation_bp` blueprint
3. Initialize Celery with Flask app context

**Code Snippet:**
```python
from celery_app import celery_app
from api.video_generation_routes import video_generation_bp

app.register_blueprint(video_generation_bp)
```

### 3. Cloud Build Configuration
**File:** `cloudbuild.yaml`

**Changes Needed:**
1. Add worker service deployment step
2. Configure Redis secrets
3. Set worker resource limits (2 CPU, 4GB RAM)

**Status:** Documented in `PHASE_3_IMPLEMENTATION_PLAN.md` (lines 590-667)

### 4. Firestore Rules
**File:** `firestore.rules`

**Changes Needed:**
```javascript
match /creations/{creationId} {
  // Users can read their own creations
  allow read: if request.auth != null
    && request.auth.uid == resource.data.userId;

  // Only backend can create/update
  allow create, update: if false;

  // Users can delete draft/failed creations
  allow delete: if request.auth != null
    && request.auth.uid == resource.data.userId
    && resource.data.status in ['draft', 'failed'];
}
```

---

## 🚀 Deployment Checklist

### Step 1: Provision Infrastructure
```bash
chmod +x infrastructure/gcp/redis-memorystore.sh
./infrastructure/gcp/redis-memorystore.sh
```

**Expected Output:**
- Redis instance created: `phoenix-cache-prod`
- Connection details: `REDIS_HOST` and `REDIS_PORT`

### Step 2: Store Redis Credentials
```bash
# Get connection details from provisioning output
REDIS_HOST="<from output>"
REDIS_PORT="<from output>"

# Store in Secret Manager
echo -n "$REDIS_HOST" | gcloud secrets create phoenix-redis-host --data-file=-
echo -n "$REDIS_PORT" | gcloud secrets create phoenix-redis-port --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding phoenix-redis-host \
  --member="serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding phoenix-redis-port \
  --member="serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 3: Create Celery App
```bash
# Create celery_app.py from plan
cp PHASE_3_IMPLEMENTATION_PLAN.md celery_app.py
# (Extract code from lines 153-196)
```

### Step 4: Update Flask App
```bash
# Add blueprint registration to app.py
# Add Celery integration
```

### Step 5: Update Cloud Build
```bash
# Update cloudbuild.yaml with worker service
# Add Redis secrets to configuration
```

### Step 6: Update Firestore Rules
```bash
# Add creations collection rules to firestore.rules
```

### Step 7: Deploy
```bash
# Install dependencies locally first (test)
pip install -r requirements.txt

# Deploy to production
gcloud builds submit --config cloudbuild.yaml .
```

### Step 8: Verify
```bash
# Check worker is running
gcloud run services describe phoenix-video-worker --region=us-central1

# Check Redis connection
gcloud redis instances describe phoenix-cache-prod --region=us-central1

# Test video generation (use curl or Postman)
curl -X POST https://phoenix-api-prod.run.app/api/generate/video \
  -H "Authorization: Bearer $FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A serene sunset over mountains", "aspectRatio": "9:16", "duration": 8}'
```

---

## 🧪 Testing Plan

### Test 1: Successful Generation
1. POST `/api/generate/video` with valid prompt
2. Verify `202 Accepted` response
3. Check `GET /api/generate/drafts` - creation appears with `status: "pending"`
4. Wait 60-120 seconds
5. Check drafts again - status should be `"draft"` with `mediaUrl`
6. Verify video plays at R2 URL

### Test 2: Insufficient Tokens
1. Drain user's token balance
2. POST `/api/generate/video`
3. Verify `402 Payment Required` response
4. Check no creation was created
5. Check no tokens were debited

### Test 3: Content Policy Violation
1. POST with prohibited content in prompt
2. Verify `202 Accepted` (job queued)
3. Wait for processing
4. Check drafts - status should be `"failed"` with error message
5. Verify tokens were refunded
6. Verify refund transaction recorded

### Test 4: Worker Crash Recovery
1. Start generation
2. Kill worker process mid-generation
3. Wait 15 minutes
4. Run cleanup task: `cleanup_orphaned_processing`
5. Verify creation marked as failed
6. Verify tokens refunded

### Test 5: Drafts Management
1. Create 3 generations (1 success, 1 failed, 1 pending)
2. GET `/api/generate/drafts` - verify all 3 appear
3. DELETE failed creation - verify removed
4. POST publish on draft - verify appears in feed

---

## 📊 Expected Costs

| Resource | Specification | Monthly Cost |
|----------|--------------|--------------|
| Redis (Memorystore) | 1GB BASIC | ~$40 |
| Cloud Run (Worker) | 1 min instance, 4GB | ~$20 |
| Vertex AI (Veo) | Per-video | ~$0.32/video |
| Cloud Storage (Temp) | Temporary files | ~$0.01 |
| Cloudflare R2 | Video storage | $0.28/10K videos |

**Total Infrastructure:** ~$60/month + $0.32/video

**Break-even:** 8 users at $10/month

---

## 🔍 Monitoring

### Key Metrics to Track

1. **Video Generation Success Rate**
   ```
   successful_generations / total_generations
   ```

2. **Average Generation Time**
   ```
   Filter logs: "Veo generation took"
   ```

3. **Refund Rate**
   ```
   failed_generations / total_generations
   ```

4. **Worker Queue Depth**
   ```
   Redis: LLEN celery_queue
   ```

5. **Cost Per Video**
   ```
   GCP Billing filtered by labels.phase=3
   ```

### Alerts to Configure

- **High Failure Rate:** > 20% failures in 1 hour
- **Worker Down:** No heartbeat for 5 minutes
- **Queue Backlog:** > 100 pending jobs
- **High Costs:** > $100/day spend

---

## 📚 Documentation References

- **Implementation Plan:** `PHASE_3_IMPLEMENTATION_PLAN.md`
- **Infrastructure README:** `infrastructure/README.md`
- **Worker Code:** `jobs/async_video_generation_worker.py`
- **API Routes:** `api/video_generation_routes.py`
- **Provisioning Script:** `infrastructure/gcp/redis-memorystore.sh`

---

## ✅ Success Criteria

Phase 3 is **COMPLETE** when:

- [x] Infrastructure scripts created and documented
- [x] Worker implements Sora-style state management
- [x] API endpoints handle drafts/publish flow
- [x] Dependencies added to requirements.txt
- [ ] Celery app configured and integrated
- [ ] Cloud Build deploys worker service
- [ ] Firestore rules protect creations collection
- [ ] Test generation works end-to-end
- [ ] Failed generations auto-refund
- [ ] Orphaned jobs are cleaned up
- [ ] All resources properly labeled for cost tracking

**Current Status:** 60% complete - Ready for provisioning once remaining files are created

---

**Next Session:** Complete Celery integration, update Cloud Build, deploy, and test
