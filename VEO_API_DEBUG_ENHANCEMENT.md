# Veo API Debug Enhancement - October 6, 2025

## Problem
Production error: `RuntimeError: Generation completed but no video outputs were returned`

The Veo API operation completes successfully but returns no video outputs in the response, causing reel generation to fail.

## Changes Made

### 1. Enhanced Error Detection in `veo_video_generation_service.py`

#### Error Field Checking
- Added explicit check for `error` field in completed operations
- Log the error message and full error response for debugging
- Return proper `VeoOperationResult` with error details

#### Response Structure Logging
When no videos are found:
- Log all response keys to understand the structure
- Log operation metadata if present (may contain diagnostic info)
- Log full operation response (truncated to 5000 chars) for analysis

#### Alternative Response Format Support
- Check for `predictions` field as an alternative to `videos`
- Try to extract `gcsUri` or `videoUrl` from predictions array
- Supports potential API format changes

#### Request Logging
- Log the `storage_uri` parameter being sent
- Log full request body at DEBUG level
- Helps verify the request is properly formatted

### 2. Improved Error Messages in `reel_generation_service.py`

#### Better Error Logging
- Log detailed information when no outputs are returned:
  - GCS URIs list
  - Count of video bytes
  - Local paths
- More descriptive error message mentioning API format issues

#### Request Tracking
- Log the storage URI being used for each generation
- Helps correlate requests with API responses

## Files Modified

1. `/services/veo_video_generation_service.py`
   - Lines ~193-200: Enhanced request logging
   - Lines ~218-255: Improved response parsing with fallbacks
   
2. `/services/reel_generation_service.py`
   - Lines ~431-434: Added storage URI logging
   - Lines ~456-470: Enhanced error logging with details

## Testing Strategy

### Immediate Next Steps
1. Deploy these changes to production
2. Trigger a new reel generation request
3. Analyze the enhanced logs to understand:
   - What the actual API response structure is
   - Whether there are error messages we're missing
   - If the `predictions` field or other alternatives exist

### Expected Log Output
```
INFO: Generating video for prompt 0 with storage_uri: gs://phoenix-videos/reel-maker/user123/project456/job789/prompt_0/
INFO: Submitting Veo generation request model=veo-3.0-fast-generate-001 duration=8 sampleCount=1 storageUri=gs://...
DEBUG: Request body: {...}
INFO: Veo operation completed. Operation name: projects/.../operations/...
WARNING: Veo operation completed but no videos in response. Response keys: [...]
INFO: Operation metadata: {...}
ERROR: Full operation response: {...}
```

### Success Criteria
After deploying, we should be able to:
1. See the exact API response structure
2. Identify why videos aren't being returned
3. Determine if it's a:
   - Permission issue
   - API format change
   - Storage URI formatting problem
   - Quota/rate limit issue

## Potential Root Causes (To Be Confirmed)

### 1. API Format Change
- Google may have changed the response structure
- `predictions` might be the new field name
- Different nesting of the video outputs

### 2. Storage Permissions
- Service account may lack write access to the storage bucket
- The API can't write to the specified storage URI
- Bucket doesn't exist or is in wrong region

### 3. API Access Issues
- Veo API quota exceeded
- Model not available in the region
- API access revoked or restricted

### 4. Request Format Issues
- Storage URI format incorrect (needs trailing slash? different format?)
- Parameters incompatible with each other
- Model-specific requirements not met

## Rollback Plan
If these changes cause issues:
```bash
git revert <commit-hash>
```

The changes are purely additive (logging and error handling), so they shouldn't break existing functionality.

## Follow-up Actions

Once we have the logs:

1. **If response structure is different**: Update parsing logic to match new format
2. **If permissions issue**: Grant storage access to service account
3. **If API access issue**: Contact Google Cloud support
4. **If request format issue**: Adjust how we build the storage_uri parameter

## Related Documentation
- `VEO_API_RESPONSE_DEBUG.md` - Detailed debugging guide
- `.github/copilot-instructions.md` - Architecture overview
- `services/veo_video_generation_service.py` - Service implementation
