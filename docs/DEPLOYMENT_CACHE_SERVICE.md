# Cache Service Deployment Guide - friedmomo.com

## Quick Fix: OAuth Login on Production

This guide fixes the "Internal Server Error" on Google OAuth callback at friedmomo.com.

---

## Problem Summary

**Error:** `AttributeError: 'Request' object has no attribute 'app'` at line 261 in `api/auth_routes.py`

**Root Cause:**
1. **Immediate bug:** Used `request.app.config` instead of `current_app.config`
2. **Deeper issue:** Filesystem sessions don't persist on Cloud Run (ephemeral containers)

**Solution:**
1. Fixed the AttributeError (✅ Done)
2. Implemented Firestore-backed sessions via cache service (✅ Done)

---

## Deployment Steps

### Step 1: Verify Changes

Files modified:
```bash
# Check the changes
git status

# Should show:
# modified:   api/auth_routes.py (fixed request.app → current_app)
# modified:   app.py (added CacheSessionInterface)
# new file:   services/cache_service/* (new service)
```

### Step 2: Test Locally (Optional)

```bash
cd /Users/sumanurawat/documents/github/phoenix

# Set environment variables
export GOOGLE_CLOUD_PROJECT=phoenix-project-386
export CACHE_BACKEND=firestore
export CACHE_COLLECTION_NAME=cache_sessions

# Run locally
python app.py

# Test login at http://localhost:8080
```

### Step 3: Deploy to Cloud Run

```bash
cd /Users/sumanurawat/documents/github/phoenix

# Deploy
gcloud run deploy phoenix \
  --source . \
  --region us-central1 \
  --project phoenix-project-386 \
  --set-env-vars CACHE_BACKEND=firestore,CACHE_COLLECTION_NAME=cache_sessions
```

**Expected output:**
```
Building using Dockerfile and deploying container to Cloud Run service [phoenix]
✓ Deploying... Done.
  ✓ Creating Revision...
  ✓ Routing traffic...
Done.
Service [phoenix] revision [phoenix-00XXX-xxx] has been deployed and is serving 100 percent of traffic.
Service URL: https://phoenix-hpbuj2rr6q-uc.a.run.app
```

### Step 4: Verify Firestore Collection

Check that the collection was created:

```bash
# List collections
gcloud firestore collections list --project=phoenix-project-386

# Should include: cache_sessions
```

Or visit Firebase Console:
https://console.firebase.google.com/project/phoenix-project-386/firestore

You should see a `cache_sessions` collection (it will be empty until first login).

### Step 5: Test OAuth Login

1. Go to https://friedmomo.com
2. Click "Login with Google"
3. Complete OAuth flow
4. You should be redirected back successfully ✅

### Step 6: Verify Session in Firestore

After successful login, check Firestore:

```bash
# Check session documents
gcloud firestore documents list cache_sessions --project=phoenix-project-386
```

Or in Firebase Console, you should see documents like:
```
cache_sessions/
  └─ friedmomo:session:abc123-def456/
      ├─ data: {...}
      ├─ created_at: Timestamp
      ├─ expires_at: Timestamp
      └─ last_accessed: Timestamp
```

---

## Environment Variables

Set these in Cloud Run:

| Variable | Value | Description |
|----------|-------|-------------|
| `CACHE_BACKEND` | `firestore` | Use Firestore as session backend |
| `CACHE_COLLECTION_NAME` | `cache_sessions` | Collection name for sessions |
| `GOOGLE_CLOUD_PROJECT` | `phoenix-project-386` | GCP project ID (auto-set) |

**To update env vars:**
```bash
gcloud run services update phoenix \
  --set-env-vars CACHE_BACKEND=firestore \
  --region us-central1 \
  --project phoenix-project-386
```

---

## Monitoring & Verification

### Check Logs for Errors

```bash
# View recent logs
gcloud run services logs read phoenix \
  --region us-central1 \
  --project phoenix-project-386 \
  --limit 50

# Filter for cache-related logs
gcloud run services logs read phoenix \
  --region us-central1 \
  --project phoenix-project-386 \
  --limit 100 | grep cache_service
```

### Verify TTL Policy

Check if TTL policy is active:

```bash
gcloud alpha firestore fields describe expires_at \
  --collection-group=cache_sessions \
  --project=phoenix-project-386
```

Expected output:
```
name: projects/phoenix-project-386/databases/(default)/collectionGroups/cache_sessions/fields/expires_at
ttlConfig:
  state: ACTIVE
```

### Monitor Session Count

```bash
# Count active sessions
gcloud firestore documents list cache_sessions \
  --project=phoenix-project-386 \
  --format="value(name)" | wc -l
```

### Check Firestore Usage & Cost

Visit: https://console.cloud.google.com/firestore/usage?project=phoenix-project-386

Monitor:
- Read operations
- Write operations
- Storage used
- Estimated cost

---

## Rollback Plan (If Needed)

If deployment causes issues, rollback to previous revision:

```bash
# List revisions
gcloud run revisions list \
  --service phoenix \
  --region us-central1 \
  --project phoenix-project-386

# Rollback to previous revision
gcloud run services update-traffic phoenix \
  --to-revisions phoenix-00252-xxx=100 \
  --region us-central1 \
  --project phoenix-project-386
```

---

## Testing Checklist

After deployment, verify:

- [ ] OAuth login works (Google sign-in)
- [ ] Session persists across requests
- [ ] User can access authenticated pages
- [ ] Logout clears session
- [ ] No errors in Cloud Run logs
- [ ] Firestore shows session documents
- [ ] TTL policy is active

---

## Cost Monitoring

**Expected monthly cost for cache service:**

For 10K daily active users:
- Firestore reads: ~12M/month → ~$7
- Firestore writes: ~3M/month → ~$5
- **Total: ~$12/month**

**Set up budget alerts:**

1. Go to https://console.cloud.google.com/billing/budgets
2. Create budget for "Cloud Firestore"
3. Set alert at $20/month (gives buffer)
4. Get notified if costs spike

---

## Next Steps (Future Optimizations)

### 1. Add Session Analytics

Track session metrics:
```python
# Count active sessions by hour
# Monitor session duration
# Track login failures
```

### 2. Implement Session Cleanup Endpoint

Create API endpoint for manual cleanup:
```python
@app.route('/api/internal/cleanup-sessions', methods=['POST'])
def cleanup_sessions():
    cache = get_cache_service()
    deleted = cache.cleanup_expired()
    return jsonify({"deleted": deleted})
```

Schedule with Cloud Scheduler:
```bash
gcloud scheduler jobs create http cleanup-sessions \
  --schedule="0 2 * * *" \
  --uri="https://friedmomo.com/api/internal/cleanup-sessions" \
  --http-method=POST \
  --project=phoenix-project-386
```

### 3. Consider Redis Migration

When traffic grows to >50K users/day, migrate to Redis:
1. Set up Cloud Memorystore (Redis)
2. Change env var: `CACHE_BACKEND=redis`
3. Add Redis connection vars
4. Deploy (zero code changes!)

---

## Troubleshooting

### Issue: Still getting 500 error

**Check logs:**
```bash
gcloud run services logs read phoenix --limit 100 | grep ERROR
```

**Common causes:**
1. Firestore permissions not set
2. TTL policy not active yet
3. Import errors in cache service

**Solution:**
```bash
# Grant Firestore permissions to Cloud Run service account
gcloud projects add-iam-policy-binding phoenix-project-386 \
  --member="serviceAccount:234619602247-compute@developer.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### Issue: Sessions expire immediately

**Check TTL policy:**
```bash
gcloud alpha firestore fields describe expires_at \
  --collection-group=cache_sessions \
  --project=phoenix-project-386
```

**If not active, manually configure in Firebase Console:**
1. Go to Firestore → Collections → cache_sessions
2. Click "Manage" → "TTL policy"
3. Set field: `expires_at`
4. Save

### Issue: High Firestore costs

**Check usage:**
```bash
# Get operation counts
gcloud monitoring time-series list \
  --filter='metric.type="firestore.googleapis.com/document/read_count"' \
  --project=phoenix-project-386
```

**Solutions:**
1. Reduce session reads (implement client-side caching)
2. Increase session TTL (fewer writes)
3. Migrate to Redis (fixed cost)

---

## Support

**Logs:** https://console.cloud.google.com/run/detail/us-central1/phoenix/logs?project=phoenix-project-386

**Firestore:** https://console.firebase.google.com/project/phoenix-project-386/firestore

**Cloud Run:** https://console.cloud.google.com/run?project=phoenix-project-386

**Questions:** Contact Phoenix AI Platform team

---

**Last Updated:** 2025-11-16
