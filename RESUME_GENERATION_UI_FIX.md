# Resume Generation UI Fix

## Problem Statement
When video generation was interrupted (e.g., during container restarts on GCP), projects would get stuck in "generating" status with:
- Status showing "Generating clips" with spinner
- Generate button disabled and spinning
- No actual generation happening (no active SSE job)
- User unable to resume generation

## Root Cause
The UI logic was checking `projectStatus === "generating"` to determine if generation was active, but this doesn't distinguish between:
1. **Actively generating** (status="generating" + active SSE job)
2. **Stuck/interrupted** (status="generating" + NO active job)

The button was disabled in both cases, leaving users unable to resume.

## Solution Implemented

### 1. Smart State Detection in ActionToolbar.tsx
Added logic to detect three distinct states:

```typescript
// STUCK STATE: Status says "generating" but no active job
const isStuckGenerating = 
  projectStatus === "generating" && 
  !activeJob && 
  clipCount < promptCount && 
  promptCount > 0;

// ACTIVE STATE: Status says "generating" AND has active job
const isActivelyGenerating = 
  projectStatus === "generating" && 
  activeJob !== null;

// Only show spinner when truly active
const showSpinner = isActivelyGenerating || isRequestingGeneration;

// Only disable when truly active (not when stuck)
const isGenerateDisabled = 
  !canGenerate || 
  isActivelyGenerating || 
  isRequestingGeneration;
```

### 2. Conditional Resume Button
When stuck, show a distinct "Resume generation" button instead of the regular "Generate clips" button:

```tsx
{isStuckGenerating ? (
  <button 
    className="btn btn-warning" 
    disabled={isRequestingGeneration} 
    onClick={onGenerate}
    title={`Resume from ${clipCount}/${promptCount} clips`}
  >
    <i className="fa fa-rotate-right" /> Resume generation
  </button>
) : (
  <button 
    className="btn btn-primary" 
    disabled={isGenerateDisabled} 
    onClick={onGenerate}
  >
    <i className="fa fa-play" /> Generate clips
  </button>
)}
```

### 3. Contextual Status Messages
Updated status text to guide users:

- **Stuck state**: `"Generation interrupted at 9/15 clips. Click Resume to continue."`
- **Active state**: `"Rendering 9/15 clips…"`
- **Ready state**: `"Clips are ready. Stitch to combine scenes."`

### 4. Pass Required Props from App.tsx
Added `clipCount` and `promptCount` props to ActionToolbar:

```tsx
<ActionToolbar
  projectName={activeProject.title}
  projectStatus={activeProject.status}
  canGenerate={canGenerateClips}
  isRequestingGeneration={isStartingGeneration}
  onGenerate={handleGenerateClips}
  activeJob={activeJobForProject}
  clipCount={activeProject.clipFilenames?.filter(Boolean).length ?? 0}
  promptCount={activeProject.promptList?.filter(p => p.trim()).length ?? 0}
/>
```

## Backend Integration
The backend already supports smart resume via `/api/reel/projects/{id}/generate`:
- Verifies existing clips in GCS (lines 121-149 in `reel_generation_service.py`)
- Preserves valid clips
- Only regenerates missing clips
- No backend changes needed!

## Firebase State Management
Auto-reconciliation already implemented in App.tsx (lines 105-267):
- Runs on every project load
- Verifies clips exist in GCS
- Corrects status if needed
- Ensures UI always reflects true state

## User Experience Flow
1. **Generation interrupted** → Project stuck at 9/15 clips
2. **User opens project** → Auto-reconciliation verifies state
3. **UI shows**: "Generation interrupted at 9/15 clips. Click Resume to continue."
4. **User clicks "Resume generation"** → Clickable yellow button (not disabled)
5. **Backend picks up from 9/15** → Only generates missing 6 clips
6. **Generation completes** → All 15 clips ready

## Testing Scenarios
✅ **Stuck generation**: Shows resume button (clickable, yellow, rotate icon)
✅ **Active generation**: Shows generate button (disabled, spinning)
✅ **Completed generation**: Shows stitch panel
✅ **Fresh project**: Shows generate button (enabled, play icon)
✅ **Auto-reconciliation**: Runs on project load, corrects status

## Files Modified
1. `frontend/reel-maker/src/components/ActionToolbar.tsx`
   - Added `clipCount` and `promptCount` props
   - Implemented stuck state detection
   - Added conditional resume button
   - Updated status messages

2. `frontend/reel-maker/src/App.tsx`
   - Pass `clipCount` and `promptCount` to ActionToolbar
   - Auto-reconciliation already present (no changes needed)

## Configuration Changes Made Earlier
- `Dockerfile`: Increased gunicorn timeout from 300s to 3600s
- `cloudbuild.yaml`: Added `--timeout 3600` for Cloud Run

## Related Documentation
- `RESUME_GENERATION_FEATURE.md` - Overall feature documentation
- `scripts/resume_stuck_generation.py` - Manual recovery utility
- `REEL_MAKER_RECONCILIATION_SUMMARY.md` - Auto-reconciliation details
