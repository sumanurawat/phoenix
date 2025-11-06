# Unified Draft-First Workflow - Quick Start Checklist

## ✅ Implementation Complete

All code changes are complete and ready for testing. Use this checklist to get started quickly.

---

## Quick Start (5 Minutes)

### 1. Start Services

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
source venv/bin/activate
celery -A celery_app.celery_app worker --loglevel=info

# Look for these tasks in output:
# ✓ jobs.async_image_generation_worker.generate_image_task
# ✓ jobs.async_video_generation_worker.generate_video_task

# Terminal 3: Flask App
./start_local.sh
```

### 2. Test Image Generation (2 Minutes)

1. Go to http://localhost:8080/create
2. Select "Image" tab
3. Enter prompt: "A beautiful sunset over mountains"
4. Click "Generate"
5. **Verify**: Immediate redirect to drafts tab
6. **Verify**: Pending card appears with shimmer animation
7. Wait 15 seconds, refresh page
8. **Verify**: Image preview appears with "Publish" button

### 3. Test Video Generation (3 Minutes)

1. Go to http://localhost:8080/create
2. Select "Video" tab
3. Enter prompt: "A cat playing with yarn"
4. Click "Generate"
5. **Verify**: Immediate redirect to drafts tab
6. **Verify**: Pending card with 🎬 icon
7. Wait 90 seconds, refresh page
8. **Verify**: Video player appears with "Publish" button

### 4. Test Failure & Refund

1. Generate image with inappropriate prompt
2. **Verify**: Failed state shows (red background)
3. Check Firestore → token_transactions
4. **Verify**: Refund entry exists

---

## Files Changed (For Code Review)

### New Files ✨
- `services/creation_service.py` - Creation lifecycle manager
- `jobs/async_image_generation_worker.py` - Image worker
- `api/generation_routes.py` - Unified endpoint

### Modified Files 📝
- `jobs/async_video_generation_worker.py` - Uses CreationService
- `app.py` - Registered generation_bp
- `templates/create.html` - Unified generate handler
- `templates/profile.html` - Enhanced drafts rendering
- `celery_app.py` - Added image task discovery

### Documentation 📚
- `UNIFIED_DRAFT_WORKFLOW_TESTING.md` - Detailed test guide
- `UNIFIED_DRAFT_WORKFLOW_IMPLEMENTATION.md` - Architecture summary

---

## Key Features Implemented

✅ **Unified Pipeline**: Both images and videos use same workflow
✅ **Atomic Tokens**: Firestore transactions prevent leaks
✅ **Instant Feedback**: Redirect to drafts in < 1 second
✅ **Visual States**: Loading animations, previews, error displays
✅ **Auto Refunds**: Failed generations refund tokens automatically
✅ **Idempotency**: Duplicate refunds prevented

---

## Monitoring Commands

```bash
# Check worker logs
tail -f celery_worker.log

# Check Flask logs
tail -f flask_app.log

# Check Redis queue
redis-cli LLEN celery

# Fetch production errors (after deploy)
./scripts/fetch_logs.py --hours 1 --severity ERROR
```

---

## Common Issues & Fixes

### "Tasks not registered"
**Problem**: Worker doesn't see new image task
**Fix**: Restart Celery worker
```bash
pkill -f "celery.*worker"
celery -A celery_app.celery_app worker --loglevel=info
```

### "Drafts stuck in pending"
**Problem**: Worker not processing tasks
**Fix**: Check worker is running and Redis is accessible
```bash
redis-cli ping  # Should return "PONG"
```

### "Tokens not refunded"
**Problem**: Worker failed silently
**Fix**: Check worker logs for exceptions
```bash
grep -i "error" celery_worker.log
```

---

## Deploy to Dev

```bash
# After successful local testing
gcloud builds submit --config cloudbuild-dev.yaml

# Monitor deployment
gcloud run services describe phoenix-dev --region=us-central1

# Check logs
./scripts/fetch_logs.py --hours 1
```

---

## What's Next?

After validation:
1. Deploy to production
2. Monitor metrics (success rate, processing time)
3. Gather user feedback
4. Plan Phase 2 (auto-refresh, progress %)

---

## Need Help?

- **Testing Guide**: See `UNIFIED_DRAFT_WORKFLOW_TESTING.md`
- **Architecture**: See `UNIFIED_DRAFT_WORKFLOW_IMPLEMENTATION.md`
- **Logs**: Check worker terminal output
- **Firestore**: Firebase Console → creations collection

---

**Status**: 🚀 Ready to test!

**Estimated Testing Time**: 15 minutes for all test cases
