# GCS Signed URL Fix Summary

**Date**: October 10, 2025  
**Issue**: Reel Maker video clips returning 500 errors due to signed URL generation failures  
**Status**: ✅ **FIXED AND DEPLOYED**

---

## Problem

Videos in Reel Maker were failing to load with these errors:
- `AttributeError: you need a private key to sign credentials`
- `Permission 'iam.serviceAccounts.signBlob' denied`
- `Permission 'run.services.setIamPolicy' denied on resource` (deployment issue)

The Cloud Run service couldn't generate signed URLs because:
1. It used Compute Engine credentials (token-only, no private key)
2. Missing IAM permissions for signBlob API
3. Cloud Build lacked deployment permissions

---

## Solution Applied

### 1. IAM Permissions for Signed URLs ✅

Granted `roles/iam.serviceAccountTokenCreator` to allow IAM signBlob API:

```bash
# For default Compute Engine service account
gcloud iam service-accounts add-iam-policy-binding \
  234619602247-compute@developer.gserviceaccount.com \
  --member="serviceAccount:234619602247-compute@developer.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="phoenix-project-386"

# For custom Phoenix service account (used by dev and prod)
gcloud iam service-accounts add-iam-policy-binding \
  phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com \
  --member="serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="phoenix-project-386"
```

### 2. Cloud Build Deployment Permissions ✅

Granted Cloud Build the ability to deploy and manage Cloud Run services:

```bash
# Grant Cloud Run Admin to Compute Engine SA
gcloud projects add-iam-policy-binding phoenix-project-386 \
  --member="serviceAccount:234619602247-compute@developer.gserviceaccount.com" \
  --role="roles/run.admin"

# Grant Cloud Run Admin to Cloud Build SA
gcloud projects add-iam-policy-binding phoenix-project-386 \
  --member="serviceAccount:234619602247@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

# Allow Cloud Build to act as phoenix-service-account
gcloud iam service-accounts add-iam-policy-binding \
  phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com \
  --member="serviceAccount:234619602247@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" \
  --project=phoenix-project-386
```

### 3. Code Improvements ✅

**File**: `services/reel_storage_service.py`

**Changes**:
- Added comprehensive signed URL fallback chain
- Added `_get_public_url_if_accessible()` security stub (returns None)
- Enhanced error logging for debugging IAM issues
- Better error messages when signing fails

**Commit**: `7c293ed` - "fix: Add IAM signBlob fallback chain for GCS signed URLs in Reel Maker"

---

## Security Model (Preserved)

✅ **Videos remain 100% private** in GCS bucket  
✅ **API validates authentication** with `@login_required` decorator  
✅ **API validates project ownership** before generating any URLs  
✅ **Signed URLs expire** after 2 hours  
✅ **No cross-user access** - users can only view their own project videos  

**Endpoint**: `/api/reel/projects/<project_id>/clips/<path:clip_path>`

**Security Flow**:
1. User must be authenticated (session-based)
2. User must own the project (Firestore check)
3. Clip must belong to the project
4. Only then: Generate temporary signed URL
5. Redirect to GCS with signed URL (expires in 2 hours)

---

## Deployment Status

### Production (phoenix)
- **URL**: https://phoenix-234619602247.us-central1.run.app
- **Revision**: phoenix-00145-r7v
- **Status**: ✅ Deployed successfully
- **Service Account**: phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com

### Dev (phoenix-dev)
- **URL**: https://phoenix-dev-234619602247.us-central1.run.app
- **Service Account**: phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com
- **Status**: ✅ Same permissions applied

---

## Testing

1. Go to: https://phoenix-234619602247.us-central1.run.app/reel-maker
2. Open an existing project with video clips
3. Videos should now load in the preview ✅
4. Check browser console for any errors

**Expected**: Videos load without 500 errors  
**Fallback**: If signed URL fails, detailed logs in Cloud Logging

---

## Technical Details

### Signed URL Generation Fallback Chain

1. **Try direct signing** with service account credentials
2. **Try IAM signBlob API** (now has permissions)
3. **Try service account key file** (local dev only)
4. **Security stub** `_get_public_url_if_accessible()` returns None

### Why IAM signBlob is Needed

Cloud Run uses **Compute Engine credentials** which are token-based (no private key). The IAM signBlob API allows the service account to sign blobs via API call using the token, without needing direct access to private keys.

### Permissions Summary

| Service Account | Role | Purpose |
|----------------|------|---------|
| `234619602247-compute@developer.gserviceaccount.com` | `iam.serviceAccountTokenCreator` | Sign blobs for signed URLs |
| `234619602247-compute@developer.gserviceaccount.com` | `run.admin` | Deploy Cloud Run services |
| `phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com` | `iam.serviceAccountTokenCreator` | Sign blobs for signed URLs |
| `234619602247@cloudbuild.gserviceaccount.com` | `run.admin` | Deploy services via Cloud Build |
| `234619602247@cloudbuild.gserviceaccount.com` | `iam.serviceAccountUser` on phoenix-service-account | Act as service account during deployment |

---

## Monitoring

Check logs for signed URL generation:
```bash
gcloud logging read 'resource.type="cloud_run_revision" AND textPayload=~"IAM Signing"' \
  --project=phoenix-project-386 \
  --limit=20 \
  --format=json
```

Check for any remaining errors:
```bash
gcloud logging read 'resource.type="cloud_run_revision" AND severity>=ERROR AND textPayload=~"signed"' \
  --project=phoenix-project-386 \
  --limit=20
```

---

## Future Considerations

1. **Token expiration**: Current signed URLs expire after 2 hours (configurable)
2. **Rate limiting**: Consider adding rate limits for signed URL generation
3. **Caching**: Could cache signed URLs temporarily to reduce API calls
4. **Monitoring**: Set up alerts for signed URL generation failures

---

## Related Files

- `services/reel_storage_service.py` - Signed URL generation logic
- `api/reel_routes.py` - `/projects/<project_id>/clips/<path:clip_path>` endpoint
- `services/reel_project_service.py` - Project ownership validation

---

## Rollback Plan (if needed)

If issues arise, previous working state:
- Commit: `7eef30c` (before fix)
- No IAM permission changes needed (permissions only add capabilities)

To revert code only:
```bash
git revert 7c293ed
git push origin main
```

But **keep IAM permissions** as they only enable functionality, don't break anything.

---

**Status**: ✅ Production is live with all fixes applied  
**Next Steps**: Monitor production logs for any signed URL errors
