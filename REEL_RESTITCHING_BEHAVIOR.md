# Re-Stitching Process Analysis

## Question
When calling the re-stitching job, are we:
1. **Deleting the old file and putting new one in same location?**
2. **Putting it in a new location and updating the frontend reference?**

## Answer: **Option 1 - Overwriting in the Same Location** ✅

The re-stitching process **OVERWRITES** the existing file at the same GCS path without explicitly deleting it first.

---

## Detailed Flow Analysis

### Step 1: Output Path Generation
**File:** `api/reel_routes.py` (Line 774)

```python
# Build output path using the naming convention from video_stitching_service
output_path = f"reel-maker/{user_id}/{project_id}/stitched/stitched_{project_id}.mp4"
```

**Key Point:** 
- The output path is **deterministic** and **always the same** for a given project
- Pattern: `reel-maker/{user_id}/{project_id}/stitched/stitched_{project_id}.mp4`
- Example: `reel-maker/7Vd9KHo2rnOG36VjWTa70Z69o4k2/Y9uaCX6yIQOxu882uBhX/stitched/stitched_Y9uaCX6yIQOxu882uBhX.mp4`

**No timestamp, no unique ID, no version number - just the project ID.**

---

### Step 2: Cloud Run Job Execution
**File:** `jobs/video_stitching/main.py` (Line 157-161)

```python
upload_success = await self.gcs_client.upload_file(
    self.local_output_file,
    payload.output_path,  # Same path as before!
    content_type="video/mp4",
    progress_callback=self._on_upload_progress
)
```

---

### Step 3: GCS Upload Operation
**File:** `jobs/base/gcs_client.py` (Line 86-130)

```python
async def upload_file(
    self,
    local_path: str,
    gcs_path: str,
    content_type: Optional[str] = None,
    progress_callback: Optional[callable] = None
) -> bool:
    # ...
    blob = self.bucket.blob(blob_name)
    
    # Set content type
    if content_type:
        blob.content_type = content_type
    
    # Upload file - THIS OVERWRITES if file exists
    await self._async_operation(blob.upload_from_filename, local_path)
```

**Critical Detail:**
- `blob.upload_from_filename()` **OVERWRITES** existing files by default
- No `if_generation_match` or existence check is used
- GCS treats this as a new version of the object (if versioning enabled)

---

### Step 4: Firestore Update
**File:** `jobs/video_stitching/main.py` (Line 173)

```python
# Step 5: Update project in Firestore
await self._update_project_status(payload.project_id, payload.output_path)
```

**File:** `services/reel_project_service.py` (Line 253-255)

```python
def update_project_stitched_file(self, project_id: str, user_id: str, stitched_filename: str) -> bool:
    """Convenience method to update stitched filename."""
    return self.update_project(project_id, user_id, stitched_filename=stitched_filename)
```

**Key Point:**
- The `stitched_filename` field in Firestore is updated with the **same path** as before
- Frontend doesn't need to know the path changed (because it didn't!)
- Browser cache may serve old video unless cache is busted

---

## What Actually Happens During Re-Stitch

### Timeline

1. **User clicks "Re-stitch"**
   - Old stitched file: `stitched_Y9uaCX6yIQOxu882uBhX.mp4` (exists in GCS)
   - Project status: `ready` → `stitching`

2. **Cloud Run Job starts**
   - Downloads all clips to temp directory
   - Runs FFmpeg to create new stitched video
   - Creates local file: `/tmp/job_xyz/stitched_output.mp4`

3. **Upload to GCS**
   - Target path: `stitched_Y9uaCX6yIQOxu882uBhX.mp4` (**SAME AS BEFORE**)
   - GCS operation: **OVERWRITE** (not delete + create)
   - Old file is replaced atomically
   - If versioning is enabled, old version is preserved

4. **Firestore update**
   - `stitched_filename` = `reel-maker/.../stitched_Y9uaCX6yIQOxu882uBhX.mp4` (unchanged)
   - Project status: `stitching` → `ready`

5. **Frontend behavior**
   - Same URL is used to access the video
   - **Browser cache may show old video!** ⚠️
   - User may need to hard refresh (Cmd+Shift+R)

---

## Implications

### ✅ Advantages of Overwriting
1. **Simple implementation** - No need to track multiple versions
2. **No orphaned files** - Old file is automatically replaced
3. **Frontend doesn't change** - Same URL continues to work
4. **Storage efficient** - Only one copy exists at a time
5. **No cleanup needed** - Old file is gone

### ⚠️ Potential Issues

#### Issue 1: Browser Caching
**Problem:**
- Browsers cache video files aggressively
- After re-stitch, browser may serve old cached version
- User sees old video even though new one exists

**Current Behavior:**
```
GET /api/reel/projects/{id}/clips/...stitched_Y9uaCX6yIQOxu882uBhX.mp4
Cache-Control: public, max-age=3600  # 1 hour cache!
```

**Solution Options:**
1. Add cache-busting query parameter: `?v=timestamp`
2. Use `Cache-Control: no-cache` for stitched videos
3. Use ETags based on file modification time
4. Clear cache on project update

#### Issue 2: No Version History
**Problem:**
- If new stitch fails/is corrupted, old version is lost
- Can't compare old vs new output
- Can't roll back to previous version

**Current Mitigation:**
- None - old file is permanently replaced

#### Issue 3: Race Conditions
**Problem:**
- If two re-stitch jobs run simultaneously (shouldn't happen, but...)
- Both will overwrite the same file
- Result is non-deterministic

**Current Protection:**
```python
# Check for existing jobs
if not force_restart:
    existing_job = self._get_active_job(project_id, "video_stitching")
    if existing_job and existing_job.status in ["queued", "running"]:
        raise JobAlreadyRunningError(...)
```

#### Issue 4: No Comparison UI
**Problem:**
- User can't compare old vs new stitched video
- Can't see if orientation fix actually worked
- No way to verify improvements

---

## Comparison: Current vs Alternative Approaches

### Current Approach: Overwrite Same File
```
First stitch:  stitched_PROJECT_ID.mp4
Second stitch: stitched_PROJECT_ID.mp4 (overwrites)
Third stitch:  stitched_PROJECT_ID.mp4 (overwrites)
```

### Alternative 1: Timestamped Files
```
First stitch:  stitched_PROJECT_ID_1728517200.mp4
Second stitch: stitched_PROJECT_ID_1728520800.mp4
Third stitch:  stitched_PROJECT_ID_1728524400.mp4

Firestore: stitched_filename updates to latest
Frontend: URL changes, no cache issues
Old files: Remain in GCS (need cleanup)
```

### Alternative 2: Version Numbers
```
First stitch:  stitched_PROJECT_ID_v1.mp4
Second stitch: stitched_PROJECT_ID_v2.mp4
Third stitch:  stitched_PROJECT_ID_v3.mp4

Firestore: Track version number + filename
Frontend: Can show version history
Old files: Remain in GCS (need cleanup or lifecycle policy)
```

### Alternative 3: GCS Object Versioning
```
All stitches:  stitched_PROJECT_ID.mp4 (same name)
GCS:          Maintains generation numbers internally
Frontend:     Can access specific versions via generation param
Automatic:    Old versions auto-deleted after N days (lifecycle policy)
```

---

## Recommendation: Add Cache-Busting

### Minimal Fix (Immediate)
Add a cache-busting parameter to the video URL:

**File:** Frontend JavaScript (reel_maker component)
```javascript
// When loading stitched video
const videoUrl = `/api/reel/projects/${projectId}/clips/${stitchedFilename}?v=${project.updatedAt}`;
```

**File:** `api/reel_routes.py` (Line 945)
```python
# Modify cache header for stitched videos
if is_stitched:
    # Stitched videos can be re-generated, so use shorter cache
    response.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes
else:
    # Raw clips never change
    response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour
```

### Medium-term Fix
Enable GCS Object Versioning for the videos bucket:
```bash
gsutil versioning set on gs://phoenix-videos
gsutil lifecycle set lifecycle.json gs://phoenix-videos
```

**lifecycle.json:**
```json
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {
        "numNewerVersions": 2,
        "isLive": false
      }
    }
  ]
}
```

This keeps:
- Current version (live)
- 2 previous versions (non-live)
- Auto-deletes older versions

---

## Current Production Behavior

### For "learn 5" Project

**First Stitch (21:25 UTC):**
- Output: `reel-maker/7Vd9KHo2rnOG36VjWTa70Z69o4k2/Y9uaCX6yIQOxu882uBhX/stitched/stitched_Y9uaCX6yIQOxu882uBhX.mp4`
- Result: Portrait mode (WRONG)
- Size: ~38MB

**Second Stitch (22:00 UTC):**
- Output: **SAME PATH** (overwrote first file)
- Result: Landscape mode (CORRECT)
- Size: 38.8MB

**What User Sees:**
- If browser cached first video → Old portrait video
- If browser refetches → New landscape video
- **Cache is determined by:**
  - `Cache-Control: public, max-age=3600`
  - First access time
  - Browser cache policy

**To See New Video:**
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- Clear cache
- Wait 1 hour for cache to expire
- Open in incognito/private window

---

## Summary

**Answer to Original Question:**

✅ **We overwrite the same file**
- Same GCS path: `stitched_{project_id}.mp4`
- Same Firestore field: `stitched_filename`
- Same frontend URL

❌ **We do NOT:**
- Explicitly delete the old file first
- Create a new unique filename
- Update the frontend reference (it stays the same)

**Overwriting happens via:**
- `blob.upload_from_filename()` which replaces existing objects
- GCS atomic write operation
- No explicit delete call needed

**Cache-busting needed:**
- Add `?v={timestamp}` to video URLs
- Or reduce `Cache-Control` max-age for stitched videos
- Or implement proper versioning system
