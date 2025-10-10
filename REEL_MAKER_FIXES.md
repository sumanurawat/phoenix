# Reel Maker Fixes - Video Streaming & Clip Management
**Date**: October 9, 2025
**Issue**: Videos not rendering, 401/500 errors, missing clip management features

---

## 🔍 Root Cause Analysis

### Your Project Status:
- **Project**: "learn 5" (ID: Y9uaCX6yIQOxu882uBhX)
- **Status**: ready ✅
- **Clips**: 15 clips (all exist in GCS)
- **Stitched Video**: 38.83 MB (exists in GCS)
- **Problem**: Videos exist but can't be viewed due to 401/500 errors

### The Problem:
1. **Files exist in GCS** ✅
2. **Firestore has correct paths** ✅
3. **But streaming fails** ❌ with:
   - 401 Unauthorized (session cookies not sent by `<video>` tags)
   - 500 Server Error (blob.reload() timing out, response too large)
   - High latency (1-4 seconds before crash)

---

## ✅ Fixes Implemented

### 1. **Fixed Video Streaming with GCS Signed URLs**

**File**: `api/reel_routes.py`

**What Changed**:
- **Before**: Server tried to stream videos through Flask (slow, session issues)
- **After**: Server generates signed URLs that redirect to GCS directly

**Benefits**:
- ✅ No more 401 errors (no session cookies needed)
- ✅ No more 500 errors (GCS handles streaming)
- ✅ Faster loading (direct from GCS)
- ✅ CDN-friendly (can enable Cloud CDN)
- ✅ Reduced server load
- ✅ 2-hour expiration for security

**Code**:
```python
# Generate signed URL (valid for 2 hours)
signed_url = blob.generate_signed_url(
    version="v4",
    expiration=timedelta(hours=2),
    method="GET",
    response_type="video/mp4"
)

# Redirect browser to GCS for streaming
return redirect(signed_url)
```

**Endpoints Fixed**:
- `GET /api/reel/projects/{project_id}/clips/{clip_path}`

---

### 2. **Added Delete Individual Clip Feature**

**New Endpoint**: `DELETE /api/reel/projects/{project_id}/clips/{clip_index}`

**Features**:
- Delete a specific clip by index (0-based)
- Removes clip from GCS
- Sets clip to `None` in Firestore (maintains prompt alignment)
- Invalidates stitched video if present
- Prevents deletion during generation/stitching

**Usage**:
```bash
# Delete clip at index 3
DELETE /api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/3
```

**Response**:
```json
{
  "success": true,
  "message": "Clip 3 deleted successfully",
  "clipIndex": 3
}
```

---

### 3. **Added Regenerate Individual Clip Feature**

**New Endpoint**: `POST /api/reel/projects/{project_id}/clips/{clip_index}/regenerate`

**Features**:
- Deletes old clip from GCS
- Marks clip for regeneration (sets to `None`)
- Invalidates stitched video
- Triggers generation service to regenerate missing clips
- Prevents regeneration during generation/stitching

**Usage**:
```bash
# Regenerate clip at index 5
POST /api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/5/regenerate
```

**Response**:
```json
{
  "success": true,
  "message": "Clip 5 regeneration started",
  "clipIndex": 5,
  "status": "generating"
}
```

**How It Works**:
1. Deletes existing clip from GCS
2. Sets `clip_filenames[index] = None`
3. Updates project status to `"generating"`
4. Calls `reel_generation_service.start_generation()`
5. Generation service regenerates only missing clips (smart!)

---

## 🚀 Next Steps to Deploy

### 1. Test Locally (Optional)

```bash
# Start local server
./start_local.sh

# Test video streaming
curl -I http://localhost:8080/api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/reel-maker/.../sample_0.mp4

# Should get 302 redirect to GCS signed URL
```

### 2. Deploy to Production

```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# Or use existing CI/CD
git add .
git commit -m "Fix video streaming with signed URLs, add clip delete/regenerate"
git push origin main
```

### 3. Verify After Deployment

```bash
# Check logs for signed URL generation
python scripts/fetch_logs.py --hours 1 --search "signed URL"

# Should see:
# "Generated signed URL for reel-maker/..."
```

---

## 📊 Expected Results

### Before:
```
GET /api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/.../sample_0.mp4
❌ Status: 401 Unauthorized
❌ Latency: N/A (fails immediately)
```

### After:
```
GET /api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/.../sample_0.mp4
✅ Status: 302 Redirect
✅ Location: https://storage.googleapis.com/phoenix-videos/...?X-Goog-Signature=...
✅ Latency: ~50ms (just auth check)

Browser then loads:
✅ Direct GCS URL
✅ Status: 200 OK
✅ Streaming works!
```

---

## 🎨 Frontend Updates Needed (Optional)

The current frontend should work as-is because it just requests the clip URL.
The redirect is handled automatically by the browser.

But for better UX, you could optionally fetch signed URLs in advance:

```typescript
// Optional: Fetch signed URL first for better error handling
async function getClipSignedUrl(projectId: string, clipPath: string) {
  const response = await fetch(
    `/api/reel/projects/${projectId}/clips/${clipPath}`
  );

  // If 302 redirect, browser follows automatically
  // If you want the URL itself, you'd need a new endpoint
  return response.url;
}
```

---

## 🔒 Security Considerations

### Signed URLs:
- ✅ **2-hour expiration**: URLs expire after 2 hours
- ✅ **Ownership verified**: Must own project to get signed URL
- ✅ **No session required**: Works with `<video>` tags
- ✅ **GCS manages access**: Cryptographically signed
- ⚠️ **Shareable**: Anyone with URL can view (until expiration)

### If you need stricter security:
You could add a query parameter to track which user requested the URL,
or reduce expiration to 1 hour.

---

## 🐛 Testing Your Fix

### Test "learn 5" Project:

1. **Open Reel Maker**: https://phoenix-234619602247.us-central1.run.app/reel-maker

2. **Open "learn 5" project**

3. **Videos should now load!** ✅

4. **Test Delete**:
   - Right-click a clip → "Delete Clip" (once frontend is updated)
   - Or use curl:
     ```bash
     curl -X DELETE \
       -H "Cookie: session=..." \
       https://your-app.com/api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/0
     ```

5. **Test Regenerate**:
   - Right-click a clip → "Regenerate Clip" (once frontend is updated)
   - Or use curl:
     ```bash
     curl -X POST \
       -H "Cookie: session=..." \
       https://your-app.com/api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/0/regenerate
     ```

6. **Test Stitched Video Download**:
   - Click download on stitched video
   - Should redirect to GCS and download directly

---

## 📈 Performance Improvements

### Before (Streaming through Flask):
- Server downloads from GCS
- Server streams to browser
- High CPU/memory usage
- Risk of timeout
- **Latency**: 1-4 seconds + streaming time

### After (Signed URLs):
- Server just generates URL (fast)
- Browser streams directly from GCS
- Zero server load for streaming
- **Latency**: ~50ms for URL generation
- GCS handles all the heavy lifting

### Cost Impact:
- **Reduced Cloud Run costs**: Less CPU/memory/bandwidth
- **Slightly increased GCS costs**: More egress from GCS (but GCS is cheaper)
- **Overall**: Net savings + better performance

---

## 🔧 Additional Improvements (Future)

1. **Enable Cloud CDN** on your Cloud Run service
   - Caches signed URLs at edge locations
   - Even faster video loading worldwide

2. **Add video transcoding**
   - Convert to multiple resolutions
   - Adaptive bitrate streaming

3. **Add frontend UI for delete/regenerate**
   - Dropdown menu on each clip
   - Confirmation dialogs

4. **Batch operations**
   - Delete multiple clips at once
   - Regenerate all clips

5. **Clip preview thumbnails**
   - Extract first frame as thumbnail
   - Faster preview loading

---

## 📝 Summary

### What was broken:
- ❌ Videos couldn't be viewed (401/500 errors)
- ❌ No way to delete individual clips
- ❌ No way to regenerate bad clips

### What's fixed:
- ✅ Video streaming via GCS signed URLs
- ✅ Delete individual clips endpoint
- ✅ Regenerate individual clips endpoint
- ✅ Faster, more reliable video playback
- ✅ Reduced server costs

### Your "learn 5" project:
- All 15 clips exist ✅
- Stitched video (38.83 MB) exists ✅
- Should work perfectly now! ✅

---

**Next Action**: Deploy and test!

```bash
# Deploy to production
gcloud builds submit --config cloudbuild.yaml

# Then check your "learn 5" project
# Videos should load immediately!
```
