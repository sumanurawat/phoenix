# Progress Monitoring Test Guide

**Quick guide to test real-time progress monitoring in both scenarios**

---

## ✅ Scenario 1: Manual Stitch (User Action)

### Steps:
1. Navigate to Reel Maker page
2. Create a new project
3. Add 3-5 prompts and save
4. Click "Generate Clips" and wait for completion
5. **Click "Stitch Clips" button**
6. ✨ **Progress monitor should appear automatically**

### Expected Behavior:
- Progress monitor appears below the Combined Reel section
- Real-time logs stream in every 2 seconds
- Progress bar updates from 0% → 100%
- Stages: Validation → Preparation → Analysis → Stitching → Complete
- FFmpeg metrics show FPS, speed, ETA
- Monitor auto-hides after 2 seconds on completion

### Console Log:
```
🎬 Starting progress monitoring for stitch job: job_abc123
```

---

## ✅ Scenario 2: Auto-Stitch (After Generation)

### Steps:
1. Navigate to Reel Maker page
2. Create a new project
3. Add 3-5 prompts and save
4. Click "Generate Clips"
5. **Wait for generation to complete** (clips will auto-generate)
6. ✨ **Stitching triggers automatically** (no button click needed)
7. ✨ **Progress monitor should appear automatically via SSE**

### Expected Behavior:
- After last clip finishes, auto-stitch begins
- SSE event `stitching.started` is received
- Progress monitor appears automatically
- Same real-time progress as manual stitch
- Monitor shows all stages and metrics
- Auto-hides on completion

### Console Log:
```
🎬 Auto-stitch detected, starting progress monitoring: job_xyz789
```

---

## 🔍 Debugging

### Check Browser Console:
```javascript
// Should see:
"🎬 Starting progress monitoring for stitch job: job_abc123"

// Or for auto-stitch:
"🎬 Auto-stitch detected, starting progress monitoring: job_xyz789"
```

### Check Network Tab:
1. **Manual Stitch**:
   - `POST /api/reel/projects/{id}/stitch` → Returns `jobId`
   - `GET /api/reel/projects/{id}/jobs/{jobId}/progress?since=0`
   - Subsequent polls every 2 seconds

2. **Auto-Stitch**:
   - SSE connection to `/api/reel/projects/{id}/events`
   - Event: `stitching.started` with `jobId` and `projectId`
   - Then same progress polling as manual

### Check Firestore:
```
Collections:
  reel_jobs/
    {job_id}/
      progress_logs/    ← Should see logs being created
        00001: { message: "Validating...", progress: 5, ... }
        00002: { message: "Downloading...", progress: 15, ... }
        00003: { message: "Stitching...", progress: 45, ... }
```

---

## 🐛 Troubleshooting

### Progress Monitor Not Appearing (Manual):
1. Check if `integration-example.js` is loaded
2. Verify fetch interceptor is working:
   ```javascript
   console.log('Original fetch:', window.fetch.toString())
   ```
3. Check if jobId is returned from API
4. Look for JavaScript errors in console

### Progress Monitor Not Appearing (Auto):
1. Check SSE connection is active:
   ```javascript
   // In console, after generation starts:
   performance.getEntriesByType('resource')
     .filter(r => r.name.includes('/events'))
   ```
2. Verify `stitching.started` event is received
3. Check if EventSource wrapper is applied
4. Verify generation actually triggers auto-stitch

### Logs Not Updating:
1. Check Firestore rules allow read access
2. Verify job is actually running (check Cloud Run logs)
3. Check progress API endpoint returns data:
   ```bash
   curl http://localhost:8080/api/reel/projects/PROJECT_ID/jobs/JOB_ID/progress
   ```

### Firestore Permission Denied:
```javascript
// Check if authenticated:
fetch('/api/reel/projects/PROJECT_ID/jobs/JOB_ID/progress', {
  credentials: 'include'
})
```

---

## 📊 Success Indicators

### ✅ Working Correctly When You See:
- [ ] Monitor appears within 1 second of trigger
- [ ] Logs stream in every 2 seconds
- [ ] Progress bar animates smoothly
- [ ] Stage badges change color
- [ ] FFmpeg metrics show speed/FPS/ETA
- [ ] Final message shows "✅ Stitching completed successfully"
- [ ] Monitor auto-hides after 2 seconds
- [ ] Page refreshes to show stitched video

### ❌ Not Working If:
- Monitor never appears
- Logs don't update
- Progress stuck at 0%
- No FFmpeg metrics
- Monitor doesn't hide after completion

---

## 🚀 Quick Local Test

```bash
# 1. Start the app
./start_local.sh

# 2. Open browser to Reel Maker
open http://localhost:8080/reel-maker

# 3. Create project, add prompts, generate clips

# 4. Test manual stitch:
#    - Click "Stitch Clips"
#    - Monitor should appear

# 5. Test auto-stitch:
#    - Create new project
#    - Generate clips
#    - Wait for auto-stitch to trigger
#    - Monitor should appear via SSE
```

---

## 📝 Expected Log Sequence

Both scenarios should show these logs in order:

```
1. 🚀 Validating 15 input video files
2. ✅ Validated 15 videos successfully
3. 🚀 Preparing video file list for concatenation
4. ✅ Created concat file with 15 entries
5. 🚀 Analyzing video properties (resolution, framerate, duration)
6. ✅ Analysis complete: 45.0s total, 30fps
7. 🚀 Building FFmpeg command with encoding settings
8. ✅ FFmpeg command ready: optimized compression, portrait orientation
9. 🚀 Starting FFmpeg video stitching process
10. Stitching video: 25.5% | 30.5 fps | 1.8x speed | ~15s remaining
11. Stitching video: 50.2% | 30.5 fps | 1.8x speed | ~8s remaining
12. Stitching video: 75.8% | 30.5 fps | 1.8x speed | ~3s remaining
13. ✅ FFmpeg stitching completed successfully
14. 🚀 Validating stitched output video
15. ✅ Output validated: 12.5MB, 45.2s
```

---

## 🎯 Performance Benchmarks

| Metric | Expected Value |
|--------|---------------|
| Monitor Appearance Time | < 1 second |
| Log Update Frequency | Every 2 seconds |
| Progress Bar Smoothness | 60 FPS |
| API Response Time | < 200ms |
| Total Overhead | < 50ms per poll |
| Memory Usage | < 10 MB |

---

**Last Updated**: October 3, 2025
