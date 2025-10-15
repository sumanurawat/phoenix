# Veo API Response Debugging Guide

## Issue Summary
Production logs show: `RuntimeError: Generation completed but no video outputs were returned`

This occurs when the Veo API operation completes successfully (`done: true`) but returns no video outputs in the expected format.

## Root Cause Analysis

### Expected Response Structure
The code expects the Veo API to return:
```json
{
  "done": true,
  "response": {
    "videos": [
      {
        "gcsUri": "gs://bucket/path/video.mp4"
      }
      // or
      {
        "bytesBase64Encoded": "..."
      }
    ]
  }
}
```

### Possible Causes
1. **API Format Change**: The Veo API response structure may have changed
2. **API Error Not Captured**: The operation completed with an error that wasn't properly detected
3. **Storage URI Issues**: The `storage_uri` parameter might not be working as expected
4. **Quota/Permission Issues**: API access might be restricted or rate-limited

## Changes Made (October 6, 2025)

### 1. Enhanced Error Detection (`veo_video_generation_service.py`)
- Added check for `error` field in completed operations
- Added logging of full operation response when no videos found
- Added check for `metadata` field that might contain diagnostic info

### 2. Alternative Response Format Support
- Added fallback to check for `predictions` field (alternative API structure)
- Try to extract `gcsUri` or `videoUrl` from predictions

### 3. Improved Error Messages (`reel_generation_service.py`)
- Enhanced error logging with details about what was/wasn't returned
- Log counts of GCS URIs, video bytes, and local paths
- More descriptive error message for debugging

### 4. Additional Logging
- Log operation completion with operation name
- Log response keys when no videos found
- Log metadata if present
- Truncate full response log to 5000 chars to avoid overwhelming logs

## Debugging Steps

### Step 1: Check Production Logs
Look for these new log messages:
```
WARNING: Veo operation completed but no videos in response. Response keys: [...]
INFO: Operation metadata: {...}
ERROR: Full operation response: {...}
```

### Step 2: Verify API Access
```bash
# Check if Veo API is enabled
gcloud services list --enabled --project=phoenix-project-386 | grep aiplatform

# Check service account permissions
gcloud projects get-iam-policy phoenix-project-386 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*"
```

### Step 3: Check Storage Configuration
The code uses `storage_uri` parameter to specify where videos should be saved:
- Verify the GCS bucket exists: `gs://phoenix-videos/`
- Check bucket permissions for the service account
- Ensure the service account has `roles/storage.objectAdmin`

### Step 4: Test with Simple Request
Create a minimal test to isolate the issue:
```python
from services.veo_video_generation_service import VeoVideoGenerationService, VeoGenerationParams

veo = VeoVideoGenerationService()
params = VeoGenerationParams(
  model="veo-3.1-fast-generate-preview",
    prompt="A cat sitting on a couch",
    duration_seconds=8,
    aspect_ratio="9:16",
    storage_uri="gs://phoenix-videos/test/"
)

result = veo.start_generation(params, poll=True)
print(f"Success: {result.success}")
print(f"GCS URIs: {result.gcs_uris}")
print(f"Error: {result.error}")
```

## Expected Next Steps

1. **Reproduce in Production**: Trigger a new generation request and capture the enhanced logs
2. **Analyze Response Structure**: Review the `Full operation response` log to see actual API format
3. **Check API Documentation**: Verify if Veo API has updated its response format
4. **Test Alternative Fields**: If `predictions` or other fields are present, update code accordingly
5. **Contact Google Support**: If API has changed without notice, escalate to Google Cloud support

## Related Files
- `/Users/sumanurawat/Documents/GitHub/phoenix/services/veo_video_generation_service.py`
- `/Users/sumanurawat/Documents/GitHub/phoenix/services/reel_generation_service.py`
- `/Users/sumanurawat/Documents/GitHub/phoenix/api/reel_routes.py` (handles the `/api/reel/projects/{id}/generate` endpoint)

## Monitoring
After deploying these changes, monitor for:
- New log messages that reveal the actual response structure
- Whether the `predictions` field exists
- Any error messages in the operation response
- Metadata that might explain why videos aren't being returned
