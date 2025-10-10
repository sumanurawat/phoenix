# Reel Maker Video Authentication Fix

**Date**: October 10, 2025  
**Issue**: Videos returning 401 Unauthorized errors despite user being logged in  
**Root Cause**: HTML `<video>` tags don't send session cookies by default  
**Status**: ✅ **FIXED**

---

## Problem Analysis

### The Issue
After fixing the IAM signBlob permissions, videos were still failing to load with 401 Unauthorized errors:

```
GET /api/reel/projects/Y9uaCX6yIQOxu882uBhX/clips/...mp4 -> 401 Unauthorized
```

### Root Cause
The `stream_clip` endpoint in `api/reel_routes.py` requires authentication via `@login_required` decorator. The original implementation redirected to a signed GCS URL:

```python
@reel_bp.route('/projects/<project_id>/clips/<path:clip_path>', methods=['GET'])
@login_required
def stream_clip(project_id, clip_path):
    # ... authentication and ownership checks ...
    signed_url = reel_storage_service.generate_signed_url(...)
    return redirect(signed_url)  # ❌ This was the problem
```

**The browser behavior:**
1. React sets video src to `/api/reel/projects/{id}/clips/{path}`
2. `<video>` tag makes GET request **WITHOUT session cookies** (browser security)
3. Flask's `@login_required` sees no session → returns 401
4. Video fails to load

This is a well-known limitation: HTML media elements (`<video>`, `<audio>`, `<img>`) don't automatically include credentials (cookies) when fetching resources.

---

## Solution Implemented

### 1. Change API Endpoint to Return JSON ✅

**File**: `api/reel_routes.py`

Changed from redirect to JSON response:

```python
# Return the signed URL as JSON for the frontend to use
# This avoids cookie/session issues with <video> tags
return jsonify({
    "success": True,
    "url": signed_url
})
```

Now the endpoint:
- Still requires authentication (`@login_required`)
- Still validates project ownership
- Returns JSON with the signed URL instead of redirecting

### 2. Create Video URL Helper ✅

**File**: `static/reel_maker/components/video-url-helper.js`

A JavaScript module that:
- Fetches signed URLs using `fetch()` with `credentials: 'same-origin'`
- Caches signed URLs for 1.5 hours (they expire at 2 hours)
- Automatically initializes video elements with proper signed URLs
- Provides `window.ReelMakerVideoHelper` API

**Key functions:**
```javascript
// Fetch signed URL with session credentials
async function fetchSignedUrl(projectId, clipPath) {
    const response = await fetch(`/api/reel/projects/${projectId}/clips/${clipPath}`, {
        credentials: 'same-origin', // ✅ Includes session cookies
        headers: { 'Accept': 'application/json' }
    });
    const data = await response.json();
    return data.url; // GCS signed URL
}

// Initialize video element with signed URL
async function initializeVideoElement(videoElement, projectId, clipPath) {
    const signedUrl = await fetchSignedUrl(projectId, clipPath);
    videoElement.src = signedUrl + '#t=0.1';
}
```

### 3. Create Video Element Patcher ✅

**File**: `static/reel_maker/components/video-patcher.js`

Since React is minified and we can't easily modify it, this patcher:
- Observes DOM for new `<video>` elements created by React
- Extracts projectId and clipPath from the original src URL
- Adds `data-project-id` and `data-clip-path` attributes
- Clears the invalid src to prevent 401 errors
- Calls `ReelMakerVideoHelper` to fetch and set signed URL

**How it works:**
```javascript
// React creates: <video><source src="/api/reel/projects/{id}/clips/{path}"/></video>
// Patcher transforms to: <video data-project-id="{id}" data-clip-path="{path}"></video>
// Then fetches signed URL and sets: <video src="https://storage.googleapis.com/...signed..."></video>
```

### 4. Update Template ✅

**File**: `templates/reel_maker.html`

Added script tags in correct order:
```html
<script src="video-url-helper.js"></script>  <!-- Must load first -->
<script src="video-patcher.js"></script>      <!-- Then patcher -->
<script type="module" src="main.js" defer></script>  <!-- React loads last -->
```

---

## How It Works Now

### Request Flow

1. **Page Load**
   - User loads `/reel-maker` (authenticated)
   - React renders video elements with API endpoint as src

2. **Video Patcher Intercepts**
   - Detects new `<video>` elements
   - Parses `/api/reel/projects/{id}/clips/{path}` from src
   - Removes the src (prevents 401 request)
   - Adds data attributes

3. **Video URL Helper Fetches Signed URL**
   - Makes authenticated `fetch()` request to API endpoint
   - **Session cookies are included** (unlike `<video>` tag)
   - Receives JSON: `{"success": true, "url": "https://storage.googleapis.com/..."}`

4. **Video Plays**
   - Sets signed URL on video element
   - Video loads directly from GCS
   - No authentication needed (URL is pre-signed)

### Security Maintained ✅

- API endpoint still requires `@login_required`
- API still validates project ownership
- Only authenticated users who own the project can get signed URLs
- Signed URLs expire after 2 hours
- No cross-user access possible

---

## Technical Details

### Why fetch() Works But <video> Doesn't

| Method | Credentials Sent? | Why? |
|--------|------------------|------|
| `<video src="...">` | ❌ No | Browser security - prevents CORS credential leaking |
| `fetch('...', {credentials: 'same-origin'})` | ✅ Yes | Explicit opt-in to send cookies |

### URL Caching Strategy

- **Cache Duration**: 1.5 hours (90 minutes)
- **Signed URL Expiration**: 2 hours (120 minutes)
- **Why 1.5 hours?**: Safety margin to prevent using expired URLs

**Cache Key Format**: `{projectId}:{clipPath}`

Example:
```javascript
signedUrlCache.set("Y9uaCX6yIQOxu882uBhX:reel-maker/user123/project456/raw/clip1.mp4", {
    url: "https://storage.googleapis.com/...?X-Goog-Signature=...",
    timestamp: 1728532835000
});
```

### MutationObserver Pattern

The patcher uses `MutationObserver` to detect React's dynamic DOM changes:

```javascript
const observer = new MutationObserver((mutations) => {
    mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
            if (node.tagName === 'VIDEO') {
                patchVideoElement(node);
            }
        });
    });
});

observer.observe(document.body, {
    childList: true,  // Watch for added/removed nodes
    subtree: true     // Watch entire tree
});
```

---

## Testing

### Manual Test Steps

1. **Go to Reel Maker**: https://phoenix-234619602247.us-central1.run.app/reel-maker
2. **Open existing project** with video clips
3. **Check browser console** for:
   ```
   [VideoPatcher] Initialized
   [VideoURLHelper] Initialized
   [VideoPatcher] Patching video element: /api/reel/projects/.../clips/...
   [VideoURLHelper] Fetching signed URL for ...
   [VideoURLHelper] Successfully fetched signed URL for ...
   ```
4. **Videos should load and play** ✅

### Debugging

Check if scripts loaded:
```javascript
console.log(window.ReelMakerVideoHelper); // Should exist
```

Manually fetch a signed URL:
```javascript
const url = await window.ReelMakerVideoHelper.fetchSignedUrl('projectId', 'clip/path.mp4');
console.log(url); // Should be GCS URL with signature
```

Clear cache if needed:
```javascript
window.ReelMakerVideoHelper.clearCache();
```

---

## Deployment Status

### Commits
1. `7c293ed` - IAM signBlob fallback chain (Oct 10, 2025)
2. `42bcd41` - GCS signed URL fix documentation (Oct 10, 2025)
3. `db76dbe` - **This fix: JSON endpoint + video helpers** (Oct 10, 2025)

### Production
- **URL**: https://phoenix-234619602247.us-central1.run.app
- **Status**: ✅ Deployed automatically via GitHub webhook
- **Build**: Auto-triggered on push to main

---

## Alternative Solutions Considered

### ❌ Option 1: Make Bucket Public
**Rejected**: Videos must remain private, only accessible by project owners.

### ❌ Option 2: Proxy Through Flask
**Rejected**: Would put load on Flask servers, defeats purpose of direct GCS streaming.

### ❌ Option 3: Generate Signed URLs Server-Side on Page Load
**Rejected**: Would require rebuilding React app, URLs would be embedded in HTML.

### ✅ Option 4: Fetch Signed URLs Client-Side (Implemented)
**Chosen**: Works with minified React, maintains security, leverages GCS direct streaming.

---

## Known Limitations

1. **Initial Load Delay**: Each video makes an API request before loading (cached after first fetch)
2. **React Dependency**: Relies on patching React-generated elements (fragile if React changes)
3. **Cache Memory**: Signed URLs stored in memory (cleared on page refresh)

---

## Future Enhancements

1. **Server-Side Rendering**: Generate signed URLs in initial project JSON
2. **Service Worker Caching**: Cache signed URLs across page refreshes
3. **Prefetching**: Fetch signed URLs for all clips on project load
4. **React Rebuild**: Modify React source to use data attributes natively

---

## Related Issues

- **Issue #1**: Videos returning 500 errors (fixed with IAM permissions)
- **Issue #2**: Videos returning 401 errors (fixed with this solution)

---

## Files Changed

```
api/reel_routes.py                                      # Changed redirect to JSON
static/reel_maker/components/video-url-helper.js        # New: Fetch signed URLs
static/reel_maker/components/video-patcher.js           # New: Patch React videos
templates/reel_maker.html                               # Added script tags
```

---

**Status**: ✅ Production is live with all fixes  
**Next Steps**: Monitor for any edge cases with video loading
