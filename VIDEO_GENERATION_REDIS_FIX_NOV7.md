# Video Generation Redis Connection Fix - Nov 7, 2025

## Problem Summary

Video generation was completely broken in production due to **Redis connection failures**. Tasks were being queued but never processed.

## Root Causes Identified

### 1. **VPC Connector Misconfiguration** (FIXED by Claude)
- **Problem**: Cloud Run services couldn't reach Redis at private IP `10.95.244.51:6379`
- **Cause**: VPC connector `phoenix-vpc-connector` existed but wasn't attached to services
- **Fix Applied**: 
  ```bash
  gcloud run services update phoenix --vpc-connector=phoenix-vpc-connector --vpc-egress=private-ranges-only
  gcloud run services update phoenix-video-worker --vpc-connector=phoenix-vpc-connector --vpc-egress=private-ranges-only
  ```
- **Result**: ✅ Services can now reach Redis on private network

### 2. **VPC Egress Configuration Error** (FIXED by Claude)
- **Problem**: Website wouldn't load after VPC connector was attached
- **Cause**: Initial fix used `--vpc-egress=all-traffic`, routing ALL traffic through VPC (including internet)
- **Symptom**: External API calls (OpenAI, Grok) failed with "Network is unreachable"
- **Fix Applied**: Changed to `--vpc-egress=private-ranges-only`
  - ✅ Redis traffic (10.95.244.51) → goes through VPC
  - ✅ Internet traffic (APIs, etc.) → goes direct
- **Result**: ✅ Website works, APIs accessible, Redis reachable

### 3. **Worker Not Running Celery** (IN PROGRESS)
- **Problem**: `phoenix-video-worker` service was running Flask app instead of Celery worker
- **Cause**: Manual VPC connector updates overwrote the `--command` parameter
  - **Expected**: `--command=python3,run_worker.py` (runs Celery)
  - **Actual**: Default Dockerfile CMD `gunicorn app:app` (runs Flask)
- **Symptom**: Tasks queued successfully but never processed
- **Fix Applied**: 
  ```bash
  gcloud run services update phoenix-video-worker --command="python3,run_worker.py"
  ```
- **Additional Issue Found**: `run_worker.py` logs not appearing in Cloud Run
  - **Cause**: Output not being flushed/logged properly for Cloud Run
  - **Fix**: Updated `run_worker.py` with proper logging and unbuffered output
  - **Status**: Deploying now via `gcloud builds submit`

## Timeline

### Initial State (Before Fixes)
- ✅ Redis instance running at `10.95.244.51:6379`
- ✅ VPC connector `phoenix-vpc-connector` exists
- ❌ Services can't reach Redis (no VPC access)
- ❌ Celery worker not running
- ❌ All video generation failing

### After VPC Connector Fix
- ✅ Services have network access to Redis
- ❌ Website broken (all traffic routed through VPC)
- ❌ External APIs unreachable

### After VPC Egress Fix
- ✅ Website working
- ✅ External APIs accessible
- ✅ Redis reachable
- ❌ Worker still not processing (wrong command)

### After Worker Command Fix
- ✅ Command set to `python3 run_worker.py`
- ❌ No Celery logs appearing
- ❌ Tasks still not processing

### Current State (Deploying)
- 🔄 Deploying fixed `run_worker.py` with proper logging
- ⏳ Waiting for deployment to complete

## What We Didn't Change

- ❌ **No code changes to app logic**
- ❌ **No database schema changes**
- ❌ **No Redis configuration changes**
- ✅ **Only infrastructure/deployment configuration**

## Services Modified

### `phoenix` (Main App)
- **Change**: Added VPC connector with `private-ranges-only` egress
- **Revisions**: `phoenix-00206-sld` → `phoenix-00207-hwm` → `phoenix-00208-xxx`
- **Status**: ✅ Working correctly

### `phoenix-video-worker` (Celery Worker)
- **Changes**: 
  1. Added VPC connector with `private-ranges-only` egress
  2. Fixed command to `python3 run_worker.py`
  3. Deploying fixed `run_worker.py` with proper logging
- **Revisions**: `phoenix-video-worker-00035-xxx` → `00036-4gz` → `00037-wkz` → `00038-9nc` → **00039-xxx (deploying)**
- **Status**: ⏳ Deployment in progress

## Testing Checklist

Once deployment completes:

1. **Verify Worker Starts**
   ```bash
   gcloud logging read 'resource.labels.service_name="phoenix-video-worker" AND textPayload=~"Phoenix Video Worker"' --limit=5
   ```
   - Should see: `🎬 Phoenix Video Worker - Starting`

2. **Verify Celery Connects**
   ```bash
   gcloud logging read 'resource.labels.service_name="phoenix-video-worker" AND textPayload=~"celery@"' --limit=5
   ```
   - Should see: `celery@localhost ready.`
   - Should see: `Connected to redis://10.95.244.51:6379/0`

3. **Verify Task Processing**
   - Generate a new video from UI
   - Check logs for task pickup:
     ```bash
     gcloud logging read 'resource.labels.service_name="phoenix-video-worker" AND textPayload=~"Task starting"' --limit=10
     ```

4. **Verify Video Completion**
   - Wait 60-120 seconds
   - Check creation status:
     ```bash
     python3 check_video_status.py <CREATION_ID>
     ```
   - Should transition: `pending` → `processing` → `draft`

## Stuck Creations (Refunded)

These creations were stuck due to the Redis issue and have been marked as failed with tokens refunded:

1. `5964ca88-3422-4974-87e7-e03ceacb31a9` - First test (14:38 UTC)
2. `e1acb3be-09a3-4b40-869e-c4f2cc524b80` - Second test (19:09 UTC)

Users can delete these from their drafts.

## Key Learnings

1. **VPC Connector is required** for Cloud Run to access private GCP resources (Redis, Cloud SQL, etc.)
2. **Always use `private-ranges-only` egress** unless you need ALL traffic through VPC
3. **Manual service updates can override cloudbuild.yaml settings** - always redeploy via Cloud Build after manual changes
4. **Cloud Run logging requires explicit flushing** - use unbuffered output or proper logging configuration

## GCP Infrastructure

### Redis Instance
- **Name**: `phoenix-cache-prod`
- **IP**: `10.95.244.51:6379`
- **Region**: `us-central1`
- **Tier**: BASIC
- **Size**: 1GB

### VPC Connector
- **Name**: `phoenix-vpc-connector`
- **Region**: `us-central1`
- **Network**: `default`
- **IP Range**: `10.8.0.0/28`
- **Status**: READY

### Secrets
- `phoenix-redis-host` → `10.95.244.51`
- `phoenix-redis-port` → `6379`
- (No password - internal network)

## Next Steps

1. ⏳ **Wait for deployment** to complete (~5-10 minutes)
2. ✅ **Verify worker logs** appear in GCP Console
3. ✅ **Test video generation** end-to-end
4. ✅ **Monitor for 24 hours** to ensure stability
5. 📝 **Document final state** in project docs

## References

- **GCP Console**: https://console.cloud.google.com/run?project=phoenix-project-386
- **Redis Dashboard**: https://console.cloud.google.com/memorystore/redis/instances?project=phoenix-project-386
- **Logs**: https://console.cloud.google.com/logs/query?project=phoenix-project-386
- **VPC Connectors**: https://console.cloud.google.com/networking/connectors?project=phoenix-project-386
