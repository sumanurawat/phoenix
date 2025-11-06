# Video Generation Queue Outage Fix - Implementation Summary

## Problem Identified

**Error**: `ConnectionRefusedError: [Errno 61] Connection refused` when attempting video generation via `/api/generate/video` endpoint.

**Root Cause**: 
- The application uses **Celery + Redis** for asynchronous video generation jobs
- Redis broker is **not running** on localhost:6379 during local development
- When Celery attempts to enqueue a video generation task, it fails to connect to Redis
- The error was **unhandled**, resulting in:
  - HTTP 500 error to the user
  - **Tokens debited but not refunded** (user loses tokens with no video)
  - Creation document stuck in `pending` state forever

## Solution Implemented

Added graceful degradation to `api/video_generation_routes.py` with automatic token refund:

### 1. Import Redis exception handlers
```python
from kombu.exceptions import OperationalError as KombuOperationalError
from redis.exceptions import ConnectionError as RedisConnectionError
```

### 2. Created rollback helper
```python
def _handle_enqueue_failure(user_id, creation_id, queue_error):
    """Rollback token debit and mark creation as failed when queue is down."""
    # Atomically:
    # - Refund VIDEO_GENERATION_COST tokens to user
    # - Revert totalTokensSpent counter
    # - Update creation status to 'failed' with error details
    # - Record refund transaction for audit trail
```

### 3. Wrapped queue submission with try-catch
```python
try:
    task = generate_video_task.apply_async(args=[creation_id], ...)
    logger.info(f"🚀 Enqueued video generation job: {task.id}")
except (RedisConnectionError, KombuOperationalError) as queue_error:
    _handle_enqueue_failure(user_id, creation_id, queue_error)
    return jsonify({
        'success': False,
        'error': 'Video generation queue is unavailable. Start Redis and retry.',
        'refunded': True,
        'details': 'The video generation service is temporarily unavailable. Your tokens have been refunded automatically.'
    }), 503  # Service Unavailable
```

## User Experience Improvements

### Before Fix
- ❌ Cryptic "Internal server error" (HTTP 500)
- ❌ Tokens debited but not refunded
- ❌ Creation stuck in `pending` state
- ❌ No indication of what went wrong

### After Fix
- ✅ Clear error message: "Video generation queue is unavailable"
- ✅ Automatic token refund via atomic transaction
- ✅ Creation marked as `failed` with `queueErrorCode` for diagnostics
- ✅ HTTP 503 (Service Unavailable) indicates temporary infrastructure issue
- ✅ User can retry after starting Redis

## How to Run Video Generation Locally

### Option 1: Start Redis (Recommended for testing video feature)

```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Or run manually in foreground:
redis-server
```

### Option 2: Use Without Video Generation
- Video generation will show graceful error message
- Image generation (1 token) works without Redis
- All other features work normally
- Tokens are refunded automatically if video generation fails

### Option 3: Production (Cloud Run)
- Redis runs via **Google Cloud Memorystore**
- Configured via `REDIS_HOST` and `REDIS_PORT` secrets
- Worker runs as separate Cloud Run service (`run_worker.py`)

## Files Changed

1. **`api/video_generation_routes.py`**
   - Added Redis exception imports
   - Added `QUEUE_UNAVAILABLE_ERROR` constant
   - Added `_handle_enqueue_failure()` helper function
   - Wrapped `apply_async()` in try-catch with rollback logic

## Testing the Fix

### Test 1: Verify graceful failure
```bash
# Without Redis running:
curl -X POST http://localhost:8080/api/generate/video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test video"}' \
  -c cookies.txt

# Expected response:
# HTTP 503 Service Unavailable
# {
#   "success": false,
#   "error": "Video generation queue is unavailable. Start Redis and retry.",
#   "refunded": true,
#   "details": "...tokens have been refunded..."
# }
```

### Test 2: Verify token refund
1. Check token balance before request
2. Attempt video generation (fails due to no Redis)
3. Check token balance after → should be same as before (refunded)
4. Check creation document → status should be `failed`, `refunded: true`

### Test 3: Verify with Redis running
```bash
# Start Redis:
redis-server

# Start Celery worker (separate terminal):
celery -A celery_app worker --loglevel=info

# Generate video:
curl -X POST http://localhost:8080/api/generate/video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "red dragon breathing fire"}' \
  -c cookies.txt

# Expected: HTTP 202 Accepted, job enqueued successfully
```

## Architecture Notes

### Why Celery + Redis?
- Video generation via Google Veo takes **60-120 seconds**
- Cannot block HTTP request that long (Cloud Run has timeouts)
- Celery runs jobs asynchronously in background worker
- Redis acts as message broker between Flask app and Celery worker

### Alternative Approaches (Not Implemented)
1. **Synchronous video generation** - Would timeout on Cloud Run
2. **Cloud Tasks** - Requires additional GCP setup, more complex locally
3. **Firestore-only queue** - No built-in retry/failure handling
4. **In-memory queue** - Not production-ready, doesn't persist across restarts

### Production Architecture
```
User Request → Flask API (Cloud Run)
                  ↓ (enqueue via Redis)
            Celery Worker (Cloud Run Service)
                  ↓ (generate)
            Google Veo API → Cloudflare R2 Storage
                  ↓ (update)
            Firestore (status: draft, mediaUrl)
                  ↓ (poll)
            User sees completed video
```

## Monitoring and Debugging

### Check Redis status
```bash
# Is Redis running?
redis-cli ping
# Expected: PONG

# Check connection:
redis-cli -h localhost -p 6379 INFO
```

### Check Celery worker status
```bash
# In separate terminal:
celery -A celery_app inspect active

# If no active tasks:
celery -A celery_app inspect stats
```

### Check Firestore for failed creations
```javascript
// In Firebase console or using SDK:
db.collection('creations')
  .where('status', '==', 'failed')
  .where('queueErrorCode', '==', 'redis_connection_refused')
  .get()
```

## Next Steps (Optional Enhancements)

1. **Add Redis health check endpoint** (`/api/health/redis`)
2. **Add frontend warning banner** when video generation unavailable
3. **Add admin dashboard** showing queue status
4. **Add retry mechanism** for transient Redis failures (already exists for Celery tasks)
5. **Add metrics** for queue failure rate

## Related Documentation

- `celery_app.py` - Celery configuration
- `jobs/async_video_generation_worker.py` - Video generation worker
- `run_worker.py` - Worker wrapper for Cloud Run
- `infrastructure/gcp/redis-memorystore.sh` - Production Redis setup
- `PHASE_3_HANDOFF.md` - Video generation architecture overview

---

**Status**: ✅ **FIX DEPLOYED** - Video generation now handles Redis outages gracefully with automatic token refunds.
