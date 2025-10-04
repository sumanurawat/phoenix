# Intelligent Job State Management - Implementation Complete

## Problem Solved
Jobs were getting stuck in "queued" status with no way to recover, blocking new attempts and creating a poor user experience.

## Solution: Auto-Reconciliation System

### Key Features Implemented

#### 1. **Multi-Strategy State Verification**
The system now checks multiple sources of truth before blocking new jobs:

```python
def _auto_reconcile_job_state(job_id, job_data):
    # Strategy 1: Check if output exists in GCS
    if output_file_exists_in_gcs():
        mark_as_completed()
    
    # Strategy 2: Query actual Cloud Run execution status
    elif cloud_run_execution_succeeded():
        mark_as_completed()
    elif cloud_run_execution_failed():
        mark_as_failed()
    
    # Strategy 3: Check if job is stale (timeout)
    elif job_age > 15_minutes and status in ['queued', 'running']:
        mark_as_failed("Job timed out")
```

#### 2. **Automatic Reconciliation on Job Lookup**
Every time `_get_active_job()` is called (when checking for existing jobs), it automatically:
- Verifies the job state is still accurate
- Updates Firestore if state changed
- Returns `None` if job is actually complete (allowing new job to start)

#### 3. **GCS Output Verification**
- Checks if stitched video already exists in Google Cloud Storage
- If found, immediately marks job as complete
- Prevents duplicate processing

#### 4. **Cloud Run Execution Tracking**
- Stores Cloud Run execution name in Firestore when job starts
- Can query actual execution status from Cloud Run API
- Reconciles Firestore status with actual execution state

#### 5. **Stale Job Auto-Cleanup**
- Configurable timeout (default: 15 minutes)
- Auto-fails jobs stuck in queued/running too long
- Prevents indefinite blocking

#### 6. **Manual Reconciliation Endpoint**
New API endpoint for manual intervention if needed:
```
POST /api/jobs/<job_id>/reconcile
```

## Changes Made

### services/job_orchestrator.py

**New Imports:**
```python
from datetime import timedelta
from google.cloud import storage
```

**New Instance Variables:**
```python
self.gcs_client = storage.Client()
self.stale_job_timeout_minutes = 15
```

**New Methods:**
```python
_check_output_exists_in_gcs(output_path)
_get_cloud_run_execution_status(job_id)
_auto_reconcile_job_state(job_id, job_data)
```

**Modified Methods:**
```python
_get_active_job()  # Now calls auto-reconciliation
_enqueue_job()     # Now stores cloudRunExecutionName
```

### api/job_routes.py

**New Endpoint:**
```python
@job_bp.route('/<job_id>/reconcile', methods=['POST'])
def reconcile_job_state(job_id)
```

## How It Works

### Flow for New Stitching Request:

```
1. User clicks "Generate Videos Again"
2. API calls trigger_stitching_job()
3. Orchestrator calls _get_active_job(project_id)
4. **AUTO-RECONCILIATION HAPPENS:**
   a. Checks if output exists in GCS → Complete!
   b. Queries Cloud Run execution status → Update status
   c. Checks if job is stale (>15 min) → Mark failed
5. If job still active after reconciliation → 409 CONFLICT
6. If job no longer active → Create new job → Success!
```

### What Happens to Your Current Stuck Job:

When you try to stitch again:
1. System finds `job_a917c89b0943` in "queued" status
2. Auto-reconciliation kicks in:
   - Checks GCS for stitched video
   - Queries Cloud Run execution `reel-stitching-job-dm4qv`
   - Checks if job is stale (created 23:26, now past timeout)
3. Updates status appropriately
4. Returns `None` (no active job)
5. New job can proceed!

## Benefits

### For Users:
✅ No more stuck jobs blocking workflow
✅ Automatic recovery from failures
✅ Jobs complete even if Firestore missed update
✅ Clear status based on actual execution

### For Developers:
✅ No manual cleanup scripts needed
✅ Self-healing system
✅ Easy debugging with reconcile endpoint
✅ Multiple sources of truth checked

### For Operations:
✅ Reduced support burden
✅ Automatic cleanup of stale jobs
✅ Better observability
✅ Professional error handling

## Configuration

Adjust timeout in `job_orchestrator.py`:
```python
self.stale_job_timeout_minutes = 15  # Change as needed
```

## Testing

### Test Auto-Reconciliation:
1. Restart Flask server (to load new code)
2. Try to trigger stitching for project TGQ8cqrkjghfYMtIep69
3. Watch logs for reconciliation messages
4. Job should either:
   - Complete (if output found in GCS)
   - Fail (if execution failed or timed out)
   - Allow new job (if reconciled to completed/failed)

### Test Manual Reconciliation:
```bash
curl -X POST http://localhost:8080/api/jobs/job_a917c89b0943/reconcile \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <token>"
```

## Logs to Expect

```
INFO:services.job_orchestrator:Found existing job job_a917c89b0943 for project TGQ8cqrkjghfYMtIep69, reconciling state...
INFO:services.job_orchestrator:🔍 Reconciling job job_a917c89b0943 (current status: queued)
INFO:services.job_orchestrator:✅ Found completed output in GCS for job job_a917c89b0943
# OR
INFO:services.job_orchestrator:⏰ Job job_a917c89b0943 is stale (age: 16.2 minutes)
INFO:services.job_orchestrator:Job job_a917c89b0943 state updated to: failed
INFO:services.job_orchestrator:Job job_a917c89b0943 no longer active after reconciliation (status: failed)
INFO:services.job_orchestrator:Triggering stitching job for project TGQ8cqrkjghfYMtIep69
```

## Future Enhancements

1. **Scheduled Cleanup Job**
   - Cloud Scheduler to run reconciliation periodically
   - Clean up all stale jobs across all projects

2. **Webhook Integration**
   - Cloud Run Job sends webhook when complete
   - Immediate Firestore update (no polling needed)

3. **Retry Logic**
   - Smart retry for transient failures
   - Exponential backoff

4. **Analytics**
   - Track job success/failure rates
   - Alert on high failure rates

## Migration Note

No database migration needed! The system is backward compatible:
- Existing jobs without `cloudRunExecutionName` still work
- Auto-reconciliation handles all cases gracefully
- Old jobs get cleaned up automatically

## Files Modified
- `services/job_orchestrator.py` - Core reconciliation logic
- `api/job_routes.py` - Manual reconciliation endpoint

## Next Steps
1. Restart Flask server
2. Try stitching again - should work now!
3. Monitor logs for reconciliation behavior
4. Consider adding scheduled cleanup if many projects
