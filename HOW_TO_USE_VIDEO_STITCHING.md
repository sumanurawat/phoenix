# How to Use Video Stitching

Quick guide to combining your video clips into a single reel.

## Prerequisites

✅ Generate at least 2 video clips in your project  
✅ Clips must be in "Ready" state (successfully generated)

## Step-by-Step Guide

### 1. Generate Your Clips

First, create and generate your video clips:

1. Go to http://localhost:8080/reel-maker
2. Create or open a project
3. Add 2 or more prompts in the prompt editor
4. Click "Generate clips"
5. Wait for all clips to complete (you'll see video players appear)

### 2. Access the Stitch Panel

Once your clips are ready:

1. Scroll down below the "Scenes" section
2. You'll see a new section called "Combined Reel"
3. It will show: "Ready to combine X clips into one video"

### 3. Start Stitching

1. Click the **"Stitch X Clips"** button
2. The button will show "Starting..." briefly
3. Then you'll see: "Stitching in progress..." with a spinner
4. A helpful message explains what's happening

### 4. Wait for Processing

**What's happening behind the scenes**:
- Downloading all clips from cloud storage
- Combining them with FFmpeg (professional video tool)
- Uploading the final reel back to cloud storage

**How long?** Typically 20-40 seconds for 3 short clips (8 seconds each)

**Auto-refresh**: The page automatically checks for completion every few seconds

### 5. Watch Your Reel!

When stitching completes:

1. 🎬 A video player appears showing your combined reel
2. 📥 Click "Download Full Reel" to save it
3. 🔄 Click "Re-stitch" if you want to regenerate it

## Troubleshooting

### "Generate at least 2 clips to create a combined reel"
- You need at least 2 clips before stitching
- Generate more clips first

### "Stitching already in progress"
- Another stitch job is running
- Wait for it to complete
- The page will auto-update when done

### Stitching takes a long time
- Normal for longer clips or many clips
- Check your internet connection
- FFmpeg processing is CPU-intensive

### Video won't play
- Try downloading and playing locally
- Check browser console for errors
- Ensure video player supports MP4/H.264

## Technical Details

**Output Format**:
- Codec: H.264 (highly compatible)
- Audio: AAC 128kbps
- Container: MP4
- Optimized for streaming

**Quality Settings**:
- Preset: medium (balanced speed/quality)
- CRF: 23 (high quality)
- Maintains original resolution

**File Location** (in cloud storage):
```
reel-maker/
  {your-user-id}/
    {project-id}/
      stitched/
        reel_full_{timestamp}.mp4
```

## FAQ

**Q: Can I change the order of clips?**  
A: Not yet - clips are stitched in the order they appear

**Q: Can I add transitions?**  
A: Not yet - clips are concatenated directly

**Q: Does it cost money?**  
A: Yes, cloud storage and bandwidth costs apply (minimal for most users)

**Q: Can I delete the stitched video?**  
A: Yes, delete the project to remove all associated videos

**Q: What if one clip failed to generate?**  
A: Only successfully generated clips will be included in the stitch

**Q: Can I re-stitch after editing?**  
A: Yes! Click "Re-stitch" to create a new combined video

**Q: What happens to old stitched videos when I re-stitch?**  
A: They remain in storage but the project references the newest one

## Next Steps

After stitching your reel:

1. **Download** it for local editing or sharing
2. **Share** the reel (future feature: shareable links)
3. **Create** a new project for your next reel
4. **Experiment** with different clip combinations

---

**Need Help?** Check the logs or contact support if you encounter issues!
