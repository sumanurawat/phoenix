# Phoenix Server Issues Report
**Generated**: October 9, 2025
**Time Window**: Last 4 hours
**Total Logs Analyzed**: 100 entries (5 ERRORs, 95 WARNINGs)

---

## 🚨 Critical Issues

### 1. **500 Internal Server Error on Stitched Video Streaming**
**Severity**: CRITICAL
**Count**: 5 errors in last hour
**Affected Endpoint**: `/api/reel/projects/{project_id}/clips/{clip_path}`

#### Pattern:
```
GET /api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/reel-maker/.../stitched/stitched_Y9uaCX6yIQOxu882uBhX.mp4
Status: 500
Latency: 1.4s - 4.1s (extremely high!)
```

#### Root Cause Analysis:
1. **High latency** (1-4 seconds) suggests GCS blob operations are slow
2. `blob.reload()` call may be timing out
3. Large stitched video files causing memory/streaming issues
4. Response size warnings: "Response size was too large"

#### Files Affected:
- `api/reel_routes.py:937-1062` (stream_clip function)

---

### 2. **401 Unauthorized on Video Clip Access**
**Severity**: HIGH
**Count**: 75+ warnings in last 4 hours
**Affected Endpoints**: All video clip URLs

#### Pattern:
```
GET /api/reel/projects/{project_id}/clips/reel-maker/.../raw/*/sample_0.mp4
Status: 401 Unauthorized
```

#### Root Cause Analysis:
1. Frontend constructs URL: `/api/reel/projects/{id}/clips/{full_gcs_path}`
2. Backend requires authentication via `@login_required` decorator
3. **Possible issue**: Session expired or cookie not sent with video requests
4. Browser may not send cookies on `<video>` tag src requests

#### Affected Code:
- Frontend: `frontend/reel-maker/src/components/SceneList.tsx:54-56`
- Backend: `api/reel_routes.py:937-976`

---

### 3. **Truncated Response / Timeouts**
**Severity**: MEDIUM
**Count**: 3 occurrences

#### Message:
```
"Truncated response body. Usually implies that the request timed out
or the application exited before the response was finished."
```

#### Likely Causes:
- Cloud Run request timeout (default 5 minutes)
- Memory exhaustion during video streaming
- Worker process crashes

---

### 4. **Missing Favicon**
**Severity**: LOW
**Count**: Multiple 404s

#### Pattern:
```
GET /favicon.ico
Status: 404
```

---

## 📊 Statistics Summary

| Issue Type | Count | Percentage |
|-----------|-------|------------|
| 401 Unauthorized (Videos) | 75+ | 75% |
| 500 Server Error (Stitched) | 5 | 5% |
| Truncated Responses | 3 | 3% |
| 404 Favicon | 2 | 2% |
| Response Too Large Warnings | 4 | 4% |

---

## 🔧 Recommended Fixes

### Priority 1: Fix 500 Errors on Stitched Video Streaming

**Issue**: `blob.reload()` and large file streaming causing crashes

**Solutions**:
1. **Remove `blob.reload()` call** - Get size from blob metadata without reload
2. **Implement signed URLs** - Let GCS handle streaming directly
3. **Add try-catch around blob operations** - Graceful degradation
4. **Increase timeout** for video streaming routes
5. **Add response size limits** or use streaming properly

**Code Changes Needed**:
```python
# Option 1: Use blob metadata (no reload)
blob = bucket.blob(clip_path)
if not blob.exists():
    return 404
file_size = blob.size  # Already available without reload!

# Option 2: Use signed URLs (preferred for large files)
signed_url = blob.generate_signed_url(
    version="v4",
    expiration=timedelta(hours=1),
    method="GET"
)
return redirect(signed_url)
```

### Priority 2: Fix 401 Unauthorized Errors

**Issue**: Session cookies not sent with `<video>` tag requests

**Solutions**:
1. **Use signed URLs** instead of session-based auth for video streaming
2. **Add CORS credentials** if needed
3. **Include auth token in URL** (less secure but works)
4. **Use backend proxy** that adds auth (current approach, but needs fixing)

**Recommended Approach**:
```python
@reel_bp.route('/projects/<project_id>/clips/<path:clip_path>/url', methods=['GET'])
@login_required
def get_clip_signed_url(project_id, clip_path):
    """Get a short-lived signed URL for video streaming"""
    # Verify ownership
    project = reel_project_service.get_project(project_id, user_id)
    if not project:
        return 401

    # Generate signed URL (1 hour expiration)
    blob = bucket.blob(clip_path)
    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=1),
        method="GET"
    )

    return jsonify({"url": signed_url})
```

**Frontend Changes**:
```typescript
// Fetch signed URL first, then use in <video> tag
const response = await fetch(`/api/reel/projects/${id}/clips/${clipPath}/url`);
const { url } = await response.json();
// Use signed URL in video player
<video src={url} />
```

### Priority 3: Optimize Video Streaming

**Solutions**:
1. **Enable Cloud CDN** on Cloud Run for video caching
2. **Use Cloud Storage signed URLs** with CDN
3. **Implement progressive streaming** (HTTP range requests working, but optimize)
4. **Add video transcoding** to reduce file sizes

### Priority 4: Add Favicon

**Simple fix**:
```bash
# Add a favicon.ico to static folder
cp path/to/favicon.ico static/favicon.ico
```

Update `templates/base.html`:
```html
<link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}">
```

---

## 🎯 Implementation Priority

1. **Immediate** (today): Fix 500 errors using signed URLs
2. **Short-term** (this week): Fix 401 errors with signed URL approach
3. **Medium-term**: Enable Cloud CDN, optimize streaming
4. **Low-priority**: Add favicon

---

## 📈 Monitoring Recommendations

1. **Set up log-based alerts** for:
   - 500 errors on `/api/reel/` endpoints
   - High latency (>2s) on video streaming
   - Truncated response warnings

2. **Add custom metrics**:
   - Video streaming success rate
   - Average streaming latency
   - GCS blob operation performance

3. **Create dashboard** showing:
   - Error rates by endpoint
   - Video streaming health
   - User session issues

---

## 🔍 How to Monitor Going Forward

### Fetch Latest Logs:
```bash
# Last 2 hours, errors and warnings
python scripts/fetch_logs.py

# Last 6 hours, errors only
python scripts/fetch_logs.py --hours 6 --severity ERROR

# Search for specific issues
python scripts/fetch_logs.py --search "video" --save-json

# Check staging environment
python scripts/fetch_logs.py --environment staging
```

### Set Up Alerts:
```bash
# Create log-based metric in GCP
gcloud logging metrics create video_streaming_errors \
  --description="500 errors on video streaming" \
  --log-filter='severity="ERROR" AND resource.type="cloud_run_revision" AND httpRequest.requestUrl=~"/api/reel/.*\.mp4"'
```

---

## 📝 Next Steps

1. Review this report
2. Prioritize fixes based on user impact
3. Implement signed URL approach for video streaming
4. Test thoroughly in staging
5. Deploy to production
6. Monitor logs for improvement

---

**Report Generated By**: GCP Log Fetcher Script
**Log Files**:
- `temp_logs/logs_2025-10-09_18-45-01.txt`
- `temp_logs/logs_2025-10-09_18-45-41.json`
