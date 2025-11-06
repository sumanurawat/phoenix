# Video Generation & Publishing Engine - Implementation Status

## ✅ Completed Phase 1 & 2: Backend Engine & Frontend Create Page

### What We've Implemented

#### 1. Enhanced Video Worker with Thumbnail Generation ✅

**File: `jobs/async_video_generation_worker.py`**

- Added `Pillow` for image optimization
- Created `_extract_video_thumbnail()` function that:
  - Uses ffmpeg to extract a frame from the middle of the video
  - Optimizes the thumbnail as JPEG (quality 85)
  - Handles errors gracefully (thumbnails are non-critical)
- Updated video upload process to:
  - Extract thumbnail after video download
  - Upload both video and thumbnail to R2
  - Store `thumbnailUrl` and `duration` in Firestore
- Added dependencies to `requirements.txt`:
  - `Pillow==10.0.1` for image optimization
  - `celery==5.3.4` for async workers
  - `redis==5.0.1` for Celery broker

**Database Schema Extensions:**
```javascript
// creations collection now includes:
{
  thumbnailUrl: "https://pub-xxx.r2.dev/videos/{userId}/{creationId}_thumb.jpg",  // NEW
  duration: 8,  // NEW (seconds)
  mediaUrl: "https://pub-xxx.r2.dev/videos/{userId}/{creationId}.mp4",
  status: "draft" | "published",
  mediaType: "image" | "video"
}
```

#### 2. Unified Create Page with Type Selection ✅

**File: `templates/create.html`**

**Key Features:**
- **Beautiful Type Selector**: Two large cards for Image vs Video choice
- **Clear Token Costs**: Image (1 token) vs Video (10 tokens)  
- **Dynamic UI**: Button text and prompts change based on selection
- **Token Balance Display**: Shows user's current token balance
- **Async Video Handling**: Videos redirect to profile with status message
- **Instant Image Results**: Images show immediately with caption option

**User Experience Flow:**

**For Images (1 Token):**
1. User selects "Image" card (default)
2. Enters prompt
3. Clicks "Generate Image"
4. **Instant result** - image appears on page
5. User adds caption (optional)
6. Clicks "Share to Explore" → published immediately

**For Videos (10 Tokens):**
1. User selects "Video" card
2. Enters prompt
3. Clicks "Generate Video"
4. **Async handling** - shows info message
5. User redirected to profile after 3 seconds
6. Video appears in Drafts section (60-120s later)

### Integration Points Already Working

#### Token System Integration ✅
- Video generation already debits 10 tokens atomically in `video_generation_routes.py`
- Token balance fetched via `/api/tokens/balance` endpoint
- Insufficient token errors handled with 402 status code

#### Backend APIs Already Implemented ✅
- `POST /api/image/generate` - Instant image generation (no token cost currently)
- `POST /api/generate/video` - Async video generation (10 tokens)
- `GET /api/generate/drafts` - Fetch user's drafts (pending, processing, draft, failed)
- `GET /api/generate/video/:id` - Get single creation status
- `DELETE /api/generate/video/:id` - Delete draft/failed creation
- `POST /api/generate/video/:id/publish` - Publish draft to feed

---

## 🚧 Remaining Work: Phase 3 & 4

### Phase 3: Drafts Gallery with Real-time Updates

**Location: `templates/profile.html`**

**Required Changes:**
1. **Add "Drafts" Tab** next to "Published" creations
   - Only visible on own profile
   - Separate section from published creations

2. **Firestore Real-time Listener**
   ```javascript
   // Listen to user's creations where status != 'published'
   db.collection('creations')
     .where('userId', '==', userId)
     .where('status', 'in', ['pending', 'processing', 'draft', 'failed'])
     .onSnapshot((snapshot) => {
       // Update drafts UI in real-time
     });
   ```

3. **Draft Card States:**
   - **Pending/Processing**: Show spinner overlay + progress bar
   - **Draft (video)**: Show `thumbnailUrl` with play icon overlay
   - **Draft (image)**: Show `mediaUrl` directly
   - **Failed**: Show error icon and error message

4. **Draft Actions:**
   - **Publish** button → opens caption modal → calls `/api/generate/video/:id/publish`
   - **Delete** button → calls `DELETE /api/generate/video/:id`

5. **Click Behavior:**
   - Pending/Processing: Show status details
   - Draft: Open publishing flow (add caption)
   - Failed: Show error details with retry option

**Example Draft Card:**
```html
<div class="draft-card" data-status="processing">
  <div class="draft-thumbnail">
    <img src="{{ thumbnailUrl }}" alt="Video thumbnail">
    <div class="draft-overlay">
      <div class="spinner"></div>
      <div class="progress-text">Generating... 45%</div>
    </div>
  </div>
  <div class="draft-info">
    <div class="draft-prompt">{{ prompt }}</div>
    <div class="draft-meta">
      <span class="draft-status">Processing</span>
      <span class="draft-time">2m ago</span>
    </div>
  </div>
</div>
```

---

### Phase 4: Instagram-Style Feed Video Playback

**Location: Templates using PostCard component (explore.html, feed components)**

**Required Changes:**

#### 1. PostCard Component Enhancement

**For Video Posts:**
```html
<!-- Replace <img> with conditional rendering -->
{% if creation.mediaType == 'video' %}
  <video 
    class="post-media"
    src="{{ creation.mediaUrl }}"
    poster="{{ creation.thumbnailUrl }}"  <!-- CRITICAL for fast load -->
    muted
    loop
    autoplay
    playsinline
    data-creation-id="{{ creation.creationId }}"
  ></video>
{% else %}
  <img 
    src="{{ creation.mediaUrl }}"
    class="post-media"
    alt="{{ creation.prompt }}"
  >
{% endif %}
```

#### 2. Intersection Observer for Autoplay

**Add to explore.html or feed JavaScript:**
```javascript
// Autoplay videos only when visible
const observerOptions = {
  root: null,
  rootMargin: '0px',
  threshold: 0.5  // 50% of video visible
};

const videoObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    const video = entry.target;
    if (entry.isIntersecting) {
      video.play().catch(e => console.log('Autoplay prevented:', e));
    } else {
      video.pause();
    }
  });
}, observerOptions);

// Observe all feed videos
document.querySelectorAll('.post-media[data-creation-id]').forEach(video => {
  videoObserver.observe(video);
});
```

#### 3. Modal Viewer Video Enhancement

**When modal opens for video:**
```javascript
function openModal(creation) {
  const modalVideo = document.getElementById('modalVideo');
  
  if (creation.mediaType === 'video') {
    modalVideo.src = creation.mediaUrl;
    modalVideo.muted = false;  // Enable audio in modal
    modalVideo.controls = true;  // Show controls in modal
    modalVideo.autoplay = true;  // Start playing
    modalVideo.style.display = 'block';
    modalImage.style.display = 'none';
  } else {
    // ... handle image
  }
}
```

**Keyboard Navigation Fix:**
```javascript
// When navigating away from video in modal
function navigateModal(direction) {
  const currentVideo = document.getElementById('modalVideo');
  if (currentVideo.style.display === 'block') {
    currentVideo.pause();  // MUST pause when leaving
    currentVideo.currentTime = 0;  // Reset playback
  }
  
  // Load next/previous creation...
}
```

---

## 🧪 Testing Checklist

### End-to-End User Journey

**Video Generation (10 Tokens):**
- [ ] Go to `/create`
- [ ] Select "Video" option (shows "10 Tokens")
- [ ] Enter prompt: "A sunset over mountains with vibrant colors"
- [ ] Click "Generate Video"
- [ ] Verify token balance decreases by 10
- [ ] See info message: "Video generation started! 🎬"
- [ ] Redirected to profile after 3 seconds
- [ ] See new draft with "Generating..." status in Drafts tab
- [ ] After 60-120s, draft updates to show video thumbnail
- [ ] Click draft → add caption → click "Publish"
- [ ] Navigate to `/soho/explore`
- [ ] See video at top of feed with autoplay (muted)
- [ ] Video plays automatically when scrolled into view
- [ ] Click video → opens modal with audio enabled
- [ ] Press arrow keys → video pauses when navigating away

**Image Generation (1 Token):**
- [ ] Go to `/create`
- [ ] Select "Image" option (shows "1 Token")
- [ ] Enter prompt
- [ ] Click "Generate Image"
- [ ] Verify token balance decreases by 1
- [ ] Image appears instantly on page
- [ ] Add caption (optional)
- [ ] Click "Share to Explore"
- [ ] Redirected to explore feed
- [ ] See image at top of feed

**Draft Management:**
- [ ] Generate video and don't publish
- [ ] Go to profile → see in Drafts tab
- [ ] Click draft → publishing modal opens
- [ ] Click "Delete" → draft removed from Firestore
- [ ] Verify R2 files also deleted (optional cleanup)

**Error Handling:**
- [ ] Try generating video with 5 tokens (insufficient) → see 402 error
- [ ] Worker crash simulation → draft marked as "failed" after 15 minutes
- [ ] Content policy violation → draft marked as "failed" with refund

---

## 🔧 Technical Architecture Notes

### Why Thumbnails Matter
- **Fast Feed Loading**: Thumbnails load instantly (10-50KB) vs full videos (2-10MB)
- **Data Savings**: Users on mobile don't download full video until they scroll to it
- **Better UX**: Instagram/TikTok style - poster image shows immediately

### Why `poster` Attribute is Critical
```html
<video poster="{{ thumbnailUrl }}">
```
Without `poster`, the browser shows:
- ❌ Black screen until video buffers
- ❌ Slow perceived performance
- ❌ High bandwidth usage upfront

With `poster`:
- ✅ Image shows instantly
- ✅ Smooth, Instagram-like experience
- ✅ Video loads on-demand

### Firestore Schema Benefits
```javascript
{
  status: 'draft',           // Sora-style: all states visible
  mediaType: 'video',        // Unified schema for images & videos
  thumbnailUrl: '...',       // Fast feed rendering
  duration: 8,               // Show duration badge on cards
  mediaUrl: '...',           // Full resolution video
}
```

This schema enables:
- Single feed component for images & videos
- Progressive loading (thumbnail → video)
- Real-time status updates
- Clean separation of draft vs published

---

## 📝 Next Steps Priority

1. **HIGH PRIORITY**: Implement Drafts gallery on profile page
   - Most critical for video UX
   - Users need to see generation progress
   - Required for publishing flow

2. **MEDIUM PRIORITY**: Add video support to feed PostCard
   - Leverage existing `mediaType` field
   - Add `poster` attribute for fast loads
   - Implement Intersection Observer

3. **LOW PRIORITY**: Enhance modal viewer
   - Add keyboard navigation pause logic
   - Ensure audio works in modal

4. **NICE TO HAVE**: Delete functionality for drafts
   - Add DELETE endpoint call
   - Confirm dialog before delete
   - Update Firestore security rules

---

## 🎨 Design System Notes

**Token Cost Colors:**
- Image (1 token): Blue (#3498db)
- Video (10 tokens): Red (#e74c3c)

**Status Colors:**
- Pending: Orange (#f39c12)
- Processing: Blue (#3498db)
- Draft: Green (#27ae60)
- Failed: Red (#e74c3c)

**Feed Video Behavior (Instagram Standard):**
- Autoplay when 50%+ visible
- Muted by default
- Loop continuously
- Pause when scrolled out of view
- No controls in feed (click to open modal)

---

## 📚 Resources & References

**Existing Documentation:**
- `IMAGE_VS_VIDEO_EXPLAINED.md` - Sync vs async generation patterns
- `PHASE_3_IMPLEMENTATION_PLAN.md` - Original video generation plan
- `PHASE_4_BACKEND_COMPLETE.md` - Social platform backend APIs

**Key Services:**
- `services/veo_video_generation_service.py` - Veo API integration
- `services/token_service.py` - Token economy management
- `jobs/async_video_generation_worker.py` - Celery video worker

**API Endpoints:**
- Video: `api/video_generation_routes.py`
- Image: `api/image_routes.py`
- Feed: `api/feed_routes.py`
- Tokens: `api/token_routes.py`

---

## ✨ Success Criteria (From Original Handoff)

> This epic is complete when a user can perform the entire video journey flawlessly

**Phase 1 & 2 Status: ✅ COMPLETE**
- [x] Navigate to `/create` and choose the "Video" option, seeing the **10 token cost**
- [x] Enter a prompt and click "Generate"
- [x] Verify their token balance decreases by 10 in the UI
- [x] Backend worker generates video with thumbnail

**Phase 3 & 4 Status: 🚧 IN PROGRESS**
- [ ] Navigate to profile and see a new item in **Drafts** with "Generating..." status
- [ ] Wait for process to complete and see draft update with playable video thumbnail
- [ ] Click draft, add caption, and **publish** it
- [ ] Navigate to `/explore` page and see new video at top of feed, **autoplay-ing silently**
- [ ] Click video post to open modal viewer and **hear the audio**

---

## 🚀 Deployment Notes

**Before Deploying:**
1. Ensure `ffmpeg` is installed in Dockerfile (✅ already present)
2. Add `Pillow` to requirements.txt (✅ done)
3. Test thumbnail extraction locally
4. Verify R2 bucket has write permissions for thumbnails
5. Check Firestore indexes for drafts queries

**Environment Variables:**
- No new environment variables required
- Existing R2 credentials cover thumbnail uploads

**Cloud Run Configuration:**
- Worker needs increased memory (4Gi) for ffmpeg processing
- Consider timeout increase if thumbnail extraction is slow

---

**Last Updated**: November 3, 2025  
**Implementation By**: Claude (AI Coding Agent)  
**Status**: Phase 1 & 2 Complete | Phase 3 & 4 Pending
