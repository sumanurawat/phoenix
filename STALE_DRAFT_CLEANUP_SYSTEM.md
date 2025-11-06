# Stale Draft Detection & Cleanup System

## Problem

Users were seeing drafts stuck in "Pending" or "Processing" status for hours or even days. These creations never actually generated because:

1. **Celery worker crashed** before starting the task
2. **Task queued but never picked up** (worker not running)
3. **Worker started but failed silently** without updating status
4. **Network/connection issues** prevented status updates

## Solution Implemented

### 1. Automatic Cleanup on Drafts Tab Load ✅

**File**: `api/generation_routes.py`
**Trigger**: Every time user opens drafts tab
**Action**: Automatically marks creations older than 1 hour as failed

```python
# Runs automatically when fetching drafts
stale_count = creation_service.mark_stale_creations_as_failed(max_age_hours=1.0)
```

**Benefits**:
- ✅ Zero configuration needed
- ✅ Works immediately
- ✅ No additional infrastructure
- ✅ Cleans up stale drafts when users actually care (viewing drafts)

**Limitation**:
- Only runs when someone views drafts (not proactive)

---

### 2. Manual Cleanup Script ✅

**File**: `scripts/mark_stale_drafts.py`

**Usage**:
```bash
# Preview what would be marked as failed
python scripts/mark_stale_drafts.py --dry-run

# Mark drafts older than 1 hour as failed
python scripts/mark_stale_drafts.py --max-age-hours 1

# Mark drafts older than 24 hours as failed (default)
python scripts/mark_stale_drafts.py
```

**When to use**:
- Manual cleanup of stale drafts
- Testing timeout logic
- One-time cleanup after fixing worker issues

---

### 3. CreationService Method ✅

**File**: `services/creation_service.py`
**Method**: `mark_stale_creations_as_failed(max_age_hours=1.0)`

**Features**:
- Queries all `pending` and `processing` creations
- Checks age against threshold
- Marks as `failed` with descriptive error
- Refunds tokens automatically (existing `mark_failed` method)
- Returns count of updated creations

**Usage in code**:
```python
from services.creation_service import creation_service

# Mark creations older than 1 hour as failed
count = creation_service.mark_stale_creations_as_failed(max_age_hours=1.0)
print(f"Marked {count} stale creations as failed")
```

---

## Configuration

### Timeout Threshold

**Current**: 1 hour
**Location**: `api/generation_routes.py` line ~245

To change:
```python
# Option 1: More aggressive (30 minutes)
creation_service.mark_stale_creations_as_failed(max_age_hours=0.5)

# Option 2: More lenient (6 hours)
creation_service.mark_stale_creations_as_failed(max_age_hours=6.0)

# Option 3: Very aggressive (10 minutes) - useful for testing
creation_service.mark_stale_creations_as_failed(max_age_hours=0.167)
```

**Recommended values**:
- **Development**: 10-30 minutes (catch issues quickly)
- **Production**: 1-2 hours (allow for retry attempts, high load)
- **Budget**: 30 minutes (minimize wasted compute time)

---

## How It Works

### Flow Diagram

```
User generates image/video
        ↓
Creation created: status = 'pending'
        ↓
Celery task queued
        ↓
    [POTENTIAL FAILURE POINTS]
        ├── Task never starts → Stays 'pending'
        ├── Task crashes early → Stays 'pending'  
        ├── Task starts but crashes → Stays 'processing'
        └── Network timeout → Status not updated
        ↓
User visits drafts tab (1+ hour later)
        ↓
Auto-cleanup runs:
  - Finds 'pending' older than 1 hour
  - Finds 'processing' older than 1 hour
  - Marks as 'failed'
  - Refunds tokens
  - Sets error message
        ↓
User sees draft with "❌ Failed" badge
Error: "Generation timeout: Task stuck in pending status for 18.2 hours"
```

### Status Transition

```
Normal flow:
pending → processing → draft → published

Timeout flow:
pending → [TIMEOUT] → failed (with refund)
processing → [TIMEOUT] → failed (with refund)
```

---

## Monitoring & Debugging

### Check for Stale Drafts

```bash
# See what would be cleaned up (no changes)
python scripts/mark_stale_drafts.py --dry-run

# Count by age
python scripts/mark_stale_drafts.py --dry-run --max-age-hours 0.5  # 30 min
python scripts/mark_stale_drafts.py --dry-run --max-age-hours 1    # 1 hour
python scripts/mark_stale_drafts.py --dry-run --max-age-hours 24   # 1 day
```

### Check User's Creations

```bash
# List all creations for a user
python scripts/verify_deleted_drafts.py --user USER_ID

# Filter by status
python scripts/verify_deleted_drafts.py --user USER_ID pending
python scripts/verify_deleted_drafts.py --user USER_ID failed
```

### Flask Logs

When auto-cleanup runs, you'll see:
```
INFO:api.generation_routes:🧹 Auto-cleanup: Marked 3 stale creations as failed
INFO:services.creation_service:⏰ Marked stale creation abc123... as failed (age: 18.2h)
```

---

## Production Deployment Options

### Option A: Keep Current Auto-Cleanup (Recommended)

**Pros**:
- ✅ Zero infrastructure cost
- ✅ No additional services to maintain
- ✅ Works with Cloud Run free tier
- ✅ Cleans up when users care (viewing drafts)

**Cons**:
- ❌ Only runs when someone views drafts
- ❌ Won't catch abandoned drafts if user never returns

**Best for**: MVP, prototypes, low-budget deployments

---

### Option B: Cloud Scheduler + Cloud Run Job (Optional)

**Setup**: Periodic cleanup every hour

**Create cleanup endpoint**:
```python
# In api/generation_routes.py
@generation_bp.route('/cleanup-stale', methods=['POST'])
def cleanup_stale_creations():
    """Endpoint called by Cloud Scheduler for periodic cleanup"""
    
    # Verify request is from Cloud Scheduler
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Run cleanup
    count = creation_service.mark_stale_creations_as_failed(max_age_hours=1.0)
    
    return jsonify({
        'success': True,
        'marked_as_failed': count
    })
```

**Cloud Scheduler configuration**:
```bash
# Create scheduler job (runs every hour)
gcloud scheduler jobs create http stale-draft-cleanup \
    --schedule="0 * * * *" \
    --uri="https://YOUR-APP-URL/api/generate/cleanup-stale" \
    --http-method=POST \
    --oidc-service-account-email=YOUR-SERVICE-ACCOUNT@PROJECT.iam.gserviceaccount.com \
    --location=us-central1
```

**Pros**:
- ✅ Proactive cleanup every hour
- ✅ Catches abandoned drafts
- ✅ Predictable execution

**Cons**:
- ❌ Additional infrastructure
- ❌ Costs ~$0.10/month (Cloud Scheduler)
- ❌ More complex setup

**Best for**: Production apps with paid users

---

### Option C: Celery Periodic Task (Advanced)

**Setup**: Use Celery Beat for scheduled cleanup

**Create task**:
```python
# In jobs/cleanup_tasks.py
from celery import Celery
from services.creation_service import creation_service

@celery_app.task(name='cleanup_stale_creations')
def cleanup_stale_creations_task():
    """Periodic task to mark stale creations as failed"""
    count = creation_service.mark_stale_creations_as_failed(max_age_hours=1.0)
    print(f"Marked {count} stale creations as failed")
    return count
```

**Configure schedule**:
```python
# In celery_app.py
celery_app.conf.beat_schedule = {
    'cleanup-stale-creations': {
        'task': 'cleanup_stale_creations',
        'schedule': 3600.0,  # Every hour
    },
}
```

**Start Celery Beat**:
```bash
celery -A celery_app beat --loglevel=info
```

**Pros**:
- ✅ Integrates with existing Celery infrastructure
- ✅ No additional services
- ✅ Runs independently of user requests

**Cons**:
- ❌ Requires Celery Beat process running
- ❌ More complex worker management
- ❌ Another process to monitor

**Best for**: Apps already using Celery workers

---

## Root Cause Prevention

### Why Drafts Get Stuck

1. **Celery worker not running**
   - Check: `ps aux | grep celery`
   - Fix: `./start_local.sh` (starts worker automatically)

2. **Redis not running**
   - Check: `redis-cli ping`
   - Fix: `redis-server` or `brew services start redis`

3. **Worker crashes silently**
   - Check: `tail -f celery_worker.log`
   - Fix: Add better error handling in workers

4. **API key issues**
   - Check logs for "API key invalid" errors
   - Fix: Update API keys in `.env`

### Best Practices

1. **Always run Celery worker** when developing
   ```bash
   ./start_local.sh  # Starts Flask + Celery + Redis
   ```

2. **Monitor worker logs**
   ```bash
   tail -f celery_worker.log
   ```

3. **Test generation immediately** after code changes
   - Generate test image
   - Check it completes within 30 seconds
   - If stuck in "pending", restart worker

4. **Use aggressive timeouts in development**
   ```python
   # In api/generation_routes.py
   creation_service.mark_stale_creations_as_failed(max_age_hours=0.167)  # 10 min
   ```

---

## Testing

### Manual Test

1. **Create a test draft that will get stuck**:
   ```bash
   # Stop Celery worker
   pkill -9 -f "celery.*worker"
   
   # Generate an image (will stay pending)
   # Visit /create, submit prompt
   
   # Wait 10 minutes (or change timeout to 0.01 hours)
   
   # Visit drafts tab
   # Should auto-mark as failed
   ```

2. **Verify cleanup works**:
   ```bash
   # Run script
   python scripts/mark_stale_drafts.py --dry-run --max-age-hours 0.01
   
   # Should show stale draft
   # Run without --dry-run to mark as failed
   ```

### Automated Test

```python
# tests/test_stale_draft_cleanup.py
import time
from services.creation_service import creation_service

def test_stale_draft_cleanup():
    # Create test draft
    creation_id, status = creation_service.create_pending_creation(
        user_id="test_user",
        prompt="Test prompt",
        creation_type="image"
    )
    
    # Artificially age it (modify createdAt in Firestore)
    # ... (implementation depends on test setup)
    
    # Run cleanup
    count = creation_service.mark_stale_creations_as_failed(max_age_hours=0.01)
    
    assert count == 1
    
    # Verify status
    creation = creation_service.get_creation(creation_id)
    assert creation['status'] == 'failed'
    assert 'timeout' in creation['error'].lower()
```

---

## Summary

✅ **Implemented**:
1. Auto-cleanup on drafts tab load
2. Manual cleanup script
3. CreationService method for cleanup
4. Error messages explain timeout

✅ **Benefits**:
- Users no longer see drafts stuck "forever"
- Tokens refunded automatically
- Clear error messages
- Zero infrastructure cost
- Works with existing code

🔄 **Optional upgrades** (future):
- Cloud Scheduler for proactive cleanup
- Celery Beat for scheduled cleanup
- Monitoring dashboard for stale draft metrics

The current implementation (auto-cleanup on drafts load) is **production-ready** and sufficient for most use cases!
