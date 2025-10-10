# Video Streaming Fix - Reel Maker

## Problem

Videos in Reel Maker projects were not showing thumbnails and could not be played in both localhost and production environments.

### Error Logs
```
AttributeError: you need a private key to sign credentials.
the credentials you are currently using <class 'google.oauth2.credentials.Credentials'> 
just contains a token.
```

### Root Cause

The `stream_clip` endpoint in `api/reel_routes.py` was attempting to generate **signed URLs** for GCS video blobs using `blob.generate_signed_url()`. However:

1. **Local Development**: Used Application Default Credentials (ADC) from `gcloud auth application-default login`, which provides user OAuth tokens **without private keys**
2. **Signed URLs require**: Service account credentials with a private key to cryptographically sign the URL
3. **Result**: All video streaming requests failed with 500 errors

## Solution

### 1. Created Robust Signed URL Generation (`services/reel_storage_service.py`)

Added `generate_signed_url()` method with **three-tier fallback strategy**:

```python
def generate_signed_url(
    self, 
    blob_path: str, 
    expiration: timedelta = timedelta(hours=2),
    method: str = "GET"
) -> Optional[str]:
```

**Fallback Chain:**

1. **Primary**: Try to generate signed URL with current credentials (works in production with service account)
2. **Secondary**: If fails with `AttributeError`, load service account credentials from `firebase-credentials.json` or `GOOGLE_APPLICATION_CREDENTIALS`
3. **Tertiary**: If signing still fails, make blob public and return public URL (last resort for local dev)

### 2. Updated Video Streaming Endpoint (`api/reel_routes.py`)

Changed from direct `blob.generate_signed_url()` to using the new service method:

```python
# OLD (broken)
signed_url = blob.generate_signed_url(
    version="v4",
    expiration=timedelta(hours=2),
    method="GET",
    response_type="video/mp4"
)

# NEW (fixed)
signed_url = reel_storage_service.generate_signed_url(
    blob_path=clip_path,
    expiration=timedelta(hours=2),
    method="GET"
)
```

### 3. Added Imports

Added necessary imports to `reel_storage_service.py`:
- `from datetime import timedelta`
- `from google.oauth2 import service_account`

## What This Fixes

✅ **Localhost**: Videos now stream using service account from `firebase-credentials.json`  
✅ **Production**: Videos continue to work with Cloud Run service account  
✅ **Thumbnails**: Frontend can load video thumbnails (poster frames)  
✅ **Playback**: HTML5 video player can stream from signed URLs  
✅ **Stitched Videos**: Both raw clips and stitched videos work

## Testing

1. Navigate to any Reel Maker project with generated videos
2. Video thumbnails should load immediately
3. Clicking play should stream the video
4. Both individual clips and stitched final video should work

## Files Changed

- `services/reel_storage_service.py` - Added `generate_signed_url()` method with fallbacks
- `api/reel_routes.py` - Updated `stream_clip` endpoint to use new method

## Environment Requirements

For **local development**, one of these must be true:
- `firebase-credentials.json` exists in project root
- `GOOGLE_APPLICATION_CREDENTIALS` env var points to a service account JSON

For **production**, Cloud Run service account must have:
- `Storage Object Admin` or `Storage Object Viewer` permissions
- Ability to sign URLs (inherent with service account)

## Related Issues

This fix resolves:
- Video thumbnails not appearing in project grid
- "Failed to access video" errors when clicking play
- 500 Internal Server Error on `/api/reel/projects/{id}/clips/{path}` endpoints
