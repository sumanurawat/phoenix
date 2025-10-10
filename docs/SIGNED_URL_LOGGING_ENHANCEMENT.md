# Signed URL Generation: Logging Enhancement & Cloud Run Fix

**Date:** October 10, 2025  
**Status:** ✅ Deployed to Production  
**Commit:** 63abdf1

## Problem Summary

After deploying signed URL IAM fallback logic, production logs showed:
- **500 errors** when attempting to generate signed URLs for video clips
- **401 errors** from browsers trying to fetch clips without session cookies
- Root cause: IAM `signBytes` API was receiving `"default"` as an invalid service account ID

### Error Pattern
```
ERROR:services.reel_storage_service:Failed to generate signed URL with IAM signer: 
Error calling the IAM signBytes API: b'{\n  "error": {\n    "code": 400,\n    
"message": "Invalid form of account ID default. Should be [Gaia ID |Email |Unique ID |] 
of the account",\n    "status": "INVALID_ARGUMENT"\n  }\n}\n'
```

## Root Cause

Cloud Run credentials expose `credentials.service_account_email` but return the literal string `"default"` instead of the actual service account email. The IAM signBytes API rejects this placeholder value.

## Solution Implemented

### 1. Service Account Email Resolution
Enhanced `_generate_signed_url_with_iam()` to:
- Detect `"default"` as an invalid placeholder
- Check `GOOGLE_SERVICE_ACCOUNT_EMAIL` environment variable override
- Fetch actual email from GCE metadata server
- Validate email contains `@` before proceeding

```python
if service_account_email in (None, "default", ""):
    # Allow explicit override via environment for edge deployments
    service_account_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")

# Some credential types (notably on Cloud Run) expose "default" as a
# placeholder service account email. Treat that the same as missing.
if service_account_email in (None, "default", ""):
    service_account_email = self._get_compute_engine_service_account()

if not service_account_email or "@" not in service_account_email:
    logger.error(
        "[IAM Signing] Cannot determine service account email for IAM signing; got %s",
        service_account_email or "<empty>"
    )
    return None
```

### 2. Comprehensive Diagnostic Logging

Added detailed logging with `[IAM Signing]` prefix to track:

#### Credential Flow
```python
logger.info(f"[IAM Signing] Starting IAM-based URL signing for blob: {blob_path}")
logger.debug(f"[IAM Signing] Default credentials type: {type(credentials).__name__}, project: {project_id}")
```

#### Service Account Resolution
```python
logger.debug(f"[IAM Signing] Retrieved service_account_email from credentials: {email}")
logger.info(f"[IAM Signing] Service account email is placeholder or missing: '{email}', checking env override")
logger.info(f"[IAM Signing] Attempting to fetch service account from metadata server")
```

#### Signing Process
```python
logger.debug(f"[IAM Signing] Creating IAM signer with service account: {email}")
logger.debug(f"[IAM Signing] Credentials refreshed, token valid: {bool(credentials.token)}")
logger.info(f"[IAM Signing] Successfully generated signed URL for {blob_path}")
```

#### Error Context
```python
logger.error(f"[IAM Signing] Failed to generate signed URL with IAM signer: {e}", exc_info=True)
logger.warning(f"IAM signBlob failed for {blob_path}: {iam_error}", exc_info=True)
```

### 3. Fallback Chain Logging

Each signing method now logs its attempt and result:
1. **Default credentials** - logs success or exception type
2. **IAM API** - detailed credential resolution and signing steps
3. **Service account file** - file path check and signing attempt
4. **Final failure** - clear error when all methods exhausted

## Files Modified

- **`services/reel_storage_service.py`**
  - Enhanced `generate_signed_url()` with step-by-step logging
  - Fixed `_generate_signed_url_with_iam()` to handle `"default"` placeholder
  - Added `[IAM Signing]` prefix to all IAM-related logs
  - Improved `_get_compute_engine_service_account()` logging

## Deployment

```bash
git add services/reel_storage_service.py
git commit -m "Fix Cloud Run signed URL generation and add comprehensive logging"
git push origin main
```

- **Trigger:** Push to main branch
- **Platform:** Google Cloud Run
- **Expected downtime:** None (rolling deployment)

## Testing After Deployment

### Success Indicators
1. Logs show `[IAM Signing] Retrieved service account from metadata: xxx@xxx.iam.gserviceaccount.com`
2. Logs show `[IAM Signing] Successfully generated signed URL for reel-maker/...`
3. No more `Invalid form of account ID default` errors
4. Video clips load successfully in Reel Maker UI

### Monitoring Commands
```bash
# Watch for successful signed URL generation
gcloud logging read 'resource.type="cloud_run_revision" 
  AND resource.labels.service_name="phoenix" 
  AND textPayload:"[IAM Signing] Successfully generated"' \
  --limit=10 --project=phoenix-project-386

# Check for any IAM signing errors
gcloud logging read 'resource.type="cloud_run_revision" 
  AND resource.labels.service_name="phoenix" 
  AND textPayload:"[IAM Signing]" 
  AND severity>=ERROR' \
  --limit=20 --project=phoenix-project-386

# Monitor clip streaming requests
gcloud logging read 'resource.type="cloud_run_revision" 
  AND resource.labels.service_name="phoenix" 
  AND httpRequest.requestUrl=~"/api/reel/projects/.*/clips/"' \
  --limit=20 --project=phoenix-project-386
```

## Known Limitations

### 401 Responses Still Expected
The 401 errors from browsers are **not fixed** and are **expected behavior**:
- HTML `<video>` tags don't send session cookies with range requests
- Browsers make preflight OPTIONS requests without credentials
- Current design: redirect to signed URL to bypass auth

**If 401s become a UX issue**, consider:
- Return signed URL in JSON response instead of redirect
- Frontend uses `fetch(..., { credentials: 'include' })` to get URL
- Or implement token-based auth for video streaming

## Log Analysis Guide

### Normal Successful Flow
```
INFO: Generating signed URL for blob: reel-maker/.../sample_0.mp4
INFO: Default credentials don't support signing (NotImplementedError), trying IAM API fallback
INFO: Attempting IAM signBlob API for reel-maker/.../sample_0.mp4
INFO: [IAM Signing] Starting IAM-based URL signing for blob: reel-maker/.../sample_0.mp4
DEBUG: [IAM Signing] Default credentials type: _DefaultCredentials, project: phoenix-project-386
INFO: [IAM Signing] Service account email is placeholder or missing: 'default', checking env override
INFO: [IAM Signing] Attempting to fetch service account from metadata server
INFO: [IAM Signing] Retrieved service account from metadata: phoenix@phoenix-project-386.iam.gserviceaccount.com
INFO: [IAM Signing] Using service account phoenix@phoenix-project-386.iam.gserviceaccount.com for IAM signing
DEBUG: [IAM Signing] Creating IAM signer with service account: phoenix@...
DEBUG: [IAM Signing] Credentials refreshed, token valid: True
INFO: [IAM Signing] Successfully generated signed URL for reel-maker/.../sample_0.mp4
INFO: Successfully generated signed URL using IAM API for reel-maker/.../sample_0.mp4
```

### Error Patterns to Watch

#### Metadata Server Unreachable
```
WARNING: [IAM Signing] Failed to get service account from metadata: [connection error]
ERROR: [IAM Signing] Cannot determine service account email for IAM signing; got <empty>
```
**Fix:** Check Cloud Run service account permissions

#### IAM API Permission Denied
```
ERROR: [IAM Signing] Failed to generate signed URL with IAM signer: 403 Permission denied
```
**Fix:** Grant `iam.serviceAccounts.signBlob` permission to Cloud Run service account

#### Blob Not Found
```
ERROR: Blob does not exist: reel-maker/...
ERROR: api.reel_routes:Failed to generate signed URL for reel-maker/...
```
**Fix:** Check GCS bucket permissions or verify clip was uploaded

## Environment Variables

### Optional Configuration
- **`GOOGLE_SERVICE_ACCOUNT_EMAIL`** - Override service account email detection
  - Use case: Non-GCP environments or custom service accounts
  - Format: `service-account@project-id.iam.gserviceaccount.com`
  - Example: `export GOOGLE_SERVICE_ACCOUNT_EMAIL="custom-sa@phoenix.iam.gserviceaccount.com"`

## Impact

- **User experience:** Video clips will now load successfully in Reel Maker
- **Server load:** Reduced (signed URLs allow direct GCS streaming)
- **Debugging:** Much easier with detailed credential flow logs
- **Reliability:** Automatic fallback to metadata server prevents failures

## Next Steps

1. **Monitor production logs** for 24 hours to confirm fix
2. **Test video playback** in Reel Maker UI
3. **Consider token-based auth** if 401s cause UX friction
4. **Document findings** for future Cloud Run credential issues

## Related Documents

- `docs/SIGNED_URL_FIX_SUMMARY.md` - Original signed URL implementation
- `docs/CREDENTIAL_MANAGEMENT_REVIEW.md` - Security compliance review
- `REEL_MAKER_TROUBLESHOOTING.md` - Video streaming troubleshooting guide
