# Resume Generation Feature

## Problem
When a Cloud Run container is redeployed (e.g., during a code push), the in-progress background video generation threads are killed. This leaves projects stuck in "generating" status with only partial clips generated (like 9/15 clips).

## Root Cause
- **Gunicorn timeout**: 300 seconds (5 minutes) - can be hit during long generation runs
- **Container termination**: During deployments, GCP terminates old containers
- **Background threads**: Video generation runs in daemon threads that get killed on container exit
- **No persistence**: No job queue to resume incomplete work after container restart

## Solution: Resume Generation Button

Added a "Resume Generation" button that:
1. **Detects stuck projects**: Shows when `status === "generating"` but some clips are missing
2. **Calls existing endpoint**: Uses the `/api/reel/projects/{id}/generate` endpoint
3. **Smart resume**: Backend automatically skips existing clips and only generates missing ones
4. **Same job flow**: Uses identical generation flow, just continues from where it left off

### How It Works

#### Backend (Already Implemented in `reel_generation_service.py`)
```python
def start_generation(...):
    # Smart clip preservation: keep existing clips, only generate missing ones
    existing_clips = project.clip_filenames or []
    preserved_clips = []
    
    for idx in range(len(cleaned_prompts)):
        if idx < len(existing_clips) and existing_clips[idx]:
            # Verify the clip still exists in GCS
            if blob.exists():
                preserved_clips.append(clip_path)
                logger.info(f"Preserving existing clip {idx}")
            else:
                preserved_clips.append(None)  # Will regenerate
        else:
            preserved_clips.append(None)  # Need to generate
```

#### Frontend Changes
1. **New button in Action Toolbar** - Shows "Resume generation" when appropriate
2. **Status indicator** - Shows "X/Y clips complete, resume to continue"
3. **Same API call** - Just calls the existing generate endpoint again

### UI Changes

**Before:**
```
[Generate clips] [Validate prompts] [Quick iterate]
```

**After (when stuck at 9/15):**
```
[Resume generation (6 remaining)] [Generate clips] [Validate prompts]
```

### Files Modified
- `static/reel_maker/assets/main.js` - Added resume button logic to ActionToolbar component
- This document

### Testing
1. Start generating a 15-clip project
2. Deploy new code (triggering container restart)
3. Refresh page - should show "9/15 clips complete"
4. Click "Resume generation" button
5. Verify it continues from clip 10-15 without re-generating 1-9

### Future Enhancements
1. **Cloud Tasks queue** - For true background job processing that survives restarts
2. **Webhook on completion** - Notify user when generation completes
3. **Progress bar** - Real-time progress tracking in UI
4. **Auto-resume** - Automatically detect and resume stuck jobs on page load

## Related Files
- `services/reel_generation_service.py` - Generation service with smart clip preservation
- `api/reel_routes.py` - REST endpoint for triggering generation
- `static/reel_maker/assets/main.js` - Frontend React components
- `REEL_MAKER_SETUP.md` - Setup documentation
- `.github/copilot-instructions.md` - Architecture documentation
