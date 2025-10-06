# Veo API "No Video Outputs" Issue - Complete Analysis

**Date:** October 6, 2025  
**Error:** `RuntimeError: Generation completed but no video outputs were returned`  
**Impact:** Reel Maker video generation failing in production  
**Status:** Debug enhancements deployed, awaiting diagnostic logs

---

## Executive Summary

The Veo API is completing video generation operations successfully (`done: true`) but returning no video outputs in the expected response structure. This prevents clips from being created, causing the entire reel generation process to fail.

**Immediate Action:** Enhanced logging has been added to capture the actual API response structure so we can identify and fix the root cause.

---

## Technical Details

### Error Flow
1. User triggers video generation via `/api/reel/projects/{id}/generate`
2. `reel_generation_service.py` calls Veo API with proper parameters
3. API operation completes (polling returns `done: true`)
4. Response parsing finds no videos in `response.videos[]` array
5. Error raised: "Generation completed but no video outputs were returned"

### Expected API Response Structure
```json
{
  "name": "projects/.../operations/...",
  "done": true,
  "response": {
    "videos": [
      {
        "gcsUri": "gs://bucket/path/video.mp4"
      }
    ]
  }
}
```

### What We're Getting (Unknown - To Be Determined)
The response structure is not matching expectations. Possible scenarios:

1. **Error not detected**: `response.error` exists but we weren't checking for it
2. **Format change**: Videos are under a different field (e.g., `predictions`)
3. **Empty response**: API is returning success but with no data
4. **Permission issue**: Storage write fails silently

---

## Changes Implemented

### 1. Enhanced Response Parsing (`veo_video_generation_service.py`)

```python
# Before: No error checking on completed operations
if op.get("done"):
    response = op.get("response", {})
    videos = response.get("videos", [])
    # Parse videos...

# After: Comprehensive checking and logging
if op.get("done"):
    # Check for error field
    if "error" in op:
        logger.error("Veo operation failed: %s", op["error"])
        return VeoOperationResult(success=False, error=...)
    
    # Log response structure
    if not videos:
        logger.warning("Response keys: %s", response.keys())
        logger.info("Metadata: %s", op.get("metadata"))
        logger.error("Full response: %s", json.dumps(op)[:5000])
    
    # Try alternative formats
    if "predictions" in response:
        # Extract from predictions...
```

### 2. Request Tracking (`veo_video_generation_service.py`, `reel_generation_service.py`)

```python
# Log the storage URI and full request
logger.info("Generating with storage_uri: %s", storage_uri)
logger.info("Request: model=%s duration=%s storageUri=%s", ...)
logger.debug("Request body: %s", json.dumps(body))
```

### 3. Detailed Error Messages (`reel_generation_service.py`)

```python
# Before: Generic error message
raise RuntimeError("Generation completed but no video outputs were returned")

# After: Detailed diagnostic info
logger.error(
    "No outputs returned. GCS URIs: %s, Video bytes: %d, Local paths: %s",
    result.gcs_uris, len(result.video_bytes), result.local_paths
)
raise RuntimeError(
    "Generation completed but no video outputs were returned. "
    "This may indicate an API error or unexpected response format."
)
```

---

## Diagnostic Checklist

### When Reviewing Logs, Check:

- [ ] **Error field present?** Look for `error.message` in operation response
- [ ] **Response structure** What keys are in the `response` object?
- [ ] **Metadata** Does `operation.metadata` contain useful info?
- [ ] **Storage URI** Is the `storageUri` parameter formatted correctly?
- [ ] **Request parameters** Are all required fields present and valid?
- [ ] **Alternative fields** Does response have `predictions` or other video containers?

### Potential Root Causes Matrix

| Symptom | Root Cause | Solution |
|---------|------------|----------|
| `error.message: "Permission denied"` | Service account lacks storage access | Grant `roles/storage.objectAdmin` |
| `error.message: "Quota exceeded"` | Veo API rate limit hit | Request quota increase |
| `error.code: 404` | Bucket doesn't exist | Create bucket or fix path |
| Response has `predictions` field | API format changed | Update parsing to use `predictions` |
| Empty response, no error | API bug or unsupported model | Try different model or contact support |
| `storageUri` malformed | Path construction issue | Fix `_build_storage_uri` method |

---

## Testing After Deployment

### Step 1: Trigger Generation
```bash
# Via UI or API
curl -X POST https://phoenix-234619602247.us-central1.run.app/api/reel/projects/{id}/generate \
  -H "Authorization: Bearer {token}" \
  -d '{"prompts": ["test prompt"]}'
```

### Step 2: Check Logs
```bash
# Via VS Code task or command line
./venv/bin/python scripts/fetch_logs.py --hours 1 --severity ERROR

# Look for these patterns:
# - "Veo operation completed"
# - "Response keys: [...]"
# - "Full operation response: {...}"
```

### Step 3: Analyze Response
Extract the logged response and examine:
```json
{
  "done": true,
  "response": {
    // What fields are actually here?
  },
  "metadata": {
    // Any diagnostic info?
  }
}
```

---

## Known Good Configuration

### Request Parameters (Working Before)
- **Model**: `veo-3.0-fast-generate-001`
- **Duration**: 8 seconds
- **Aspect Ratio**: `9:16` (portrait) or `16:9` (landscape)
- **Sample Count**: 1
- **Storage URI**: `gs://phoenix-videos/reel-maker/{userId}/{projectId}/{jobId}/prompt_{index}/`
- **Compression**: `optimized`

### Service Account Permissions Required
- `roles/aiplatform.user` - Vertex AI access
- `roles/storage.objectAdmin` - GCS write access
- `roles/logging.logWriter` - Write logs

---

## Resolution Paths

### Path A: API Format Changed
**If** logs show `predictions` field:
1. Update `veo_video_generation_service.py` line ~230
2. Parse `predictions` array instead of `videos`
3. Deploy and test

### Path B: Permission Issue
**If** logs show permission error:
1. Grant storage permissions to service account
2. Verify bucket exists and is accessible
3. Test again

### Path C: API Error
**If** logs show API error message:
1. Address the specific error (quota, rate limit, etc.)
2. May need to contact Google Cloud support
3. Document the issue and resolution

### Path D: Unknown Issue
**If** logs don't reveal cause:
1. Create minimal reproduction script
2. Test with Google's official examples
3. Open support ticket with Google Cloud
4. Consider temporary fallback to local video generation

---

## Success Metrics

✅ **Issue Resolved When:**
- Generation completes without errors
- Videos appear in GCS bucket
- Clips are accessible in the UI
- Stitching can proceed

📊 **Monitoring:**
- Watch error rate in Cloud Logging
- Check generation success rate metric
- Monitor GCS bucket for new videos

---

## Files Changed
- `services/veo_video_generation_service.py` - Response parsing & logging
- `services/reel_generation_service.py` - Error handling & logging
- `VEO_API_RESPONSE_DEBUG.md` - Debugging guide
- `VEO_API_DEBUG_ENHANCEMENT.md` - Change summary
- `VEO_FIX_QUICKREF.md` - Quick reference
- `VEO_COMPLETE_ANALYSIS.md` - This file

## Related Documentation
- `REEL_MAKER_TROUBLESHOOTING.md` - General troubleshooting
- `CLOUD_RUN_JOBS_SETUP.md` - Infrastructure setup
- `.github/copilot-instructions.md` - Architecture overview

---

**Next Action:** Deploy changes and trigger test generation to capture diagnostic logs.
