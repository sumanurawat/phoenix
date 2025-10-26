# 📸 Image vs Video Generation - How They Work

## **KEY DIFFERENCES:**

### **Image Generation (Imagen 3)** - SYNCHRONOUS
**How it works:**
1. User clicks "Generate Image" on frontend
2. API call: `POST /api/image/generate`
3. **Runs immediately in the API request** (blocks for 2-5 seconds)
4. Imagen 3 generates image
5. Uploads to R2 storage
6. **Returns immediately** with image URL
7. Saves to `image_generations` collection in Firestore

**No Cloud Run Job:** Runs directly in the main API server (fast enough!)

**Response Time:** 2-5 seconds (user waits)

**Database:** `image_generations` collection
```javascript
{
  image_id: "uuid",
  user_id: "7Vd9KHo...",
  prompt: "A serene sunset",
  image_url: "https://r2.../image.png",
  gcs_uri: "gs://...",
  base64_data: "base64...",
  timestamp: "2025-10-26T...",
  generation_time_seconds: 3.45,
  model: "imagen-3.0-generate-001"
}
```

**Cost:** FREE (no tokens deducted currently - could add later)

---

### **Video Generation (Google Veo)** - ASYNCHRONOUS
**How it works:**
1. User clicks "Generate Video" on frontend
2. API call: `POST /api/generate/video`
3. **Debits 10 tokens** atomically
4. Creates `creation` document with status "pending"
5. **Enqueues Celery task** (doesn't wait)
6. **Returns immediately** (202 Accepted)
7. User sees "Generating..." in their Drafts

**Background Process (separate Cloud Run service):**
8. Celery worker picks up task
9. Calls Google Veo API (60-120 seconds!)
10. Polls for completion
11. Downloads video
12. Uploads to R2 storage
13. Updates status: "pending" → "processing" → "draft"
14. If fails: marks as "failed" and **refunds 10 tokens**

**Response Time:** 60-120 seconds (user doesn't wait!)

**Database:** `creations` collection
```javascript
{
  creationId: "uuid",
  userId: "7Vd9KHo...",
  username: "sumanurawat12",
  prompt: "A serene sunset",
  aspectRatio: "9:16",
  duration: 8,
  cost: 10,
  status: "draft", // pending → processing → draft → published
  mediaUrl: "https://r2.../video.mp4",
  caption: "",
  likeCount: 0,
  createdAt: timestamp,
  publishedAt: null
}
```

**Cost:** 10 tokens (deducted upfront, refunded if fails)

---

## **WHY THE DIFFERENCE?**

**Images are fast (2-5 seconds):**
- Can run synchronously in API request
- User doesn't mind waiting
- No need for background worker

**Videos are slow (60-120 seconds):**
- MUST run asynchronously
- User would timeout waiting
- Need Celery + Redis + separate Cloud Run service
- More complex (polling, retries, refunds)

---

## **FOR THE SOCIAL PLATFORM PRD:**

### **Phase 1: Start with Images Only** ✅ RECOMMENDED
- Simpler (no background workers to test)
- Faster user feedback
- Lower cost (free for now)
- Still visual and shareable

**User Journey:**
1. User goes to "Create" page
2. Enters prompt
3. Clicks "Generate Image"
4. **Waits 3-5 seconds** (shows loading spinner)
5. Image appears immediately
6. User adds caption
7. Clicks "Share"
8. Image appears on Explore feed
9. Other users can like it

### **Phase 2: Add Videos Later** (Optional)
Once images are working, add video option:
- Same "Create" page, add "Image" vs "Video" toggle
- Videos go to "Drafts" (async)
- Images show immediately (sync)

---

## **RECOMMENDATION FOR MVP:**

**Build with Images FIRST:**

**Why:**
1. ✅ **Simpler** - No background worker complexity
2. ✅ **Faster** - Immediate gratification for users
3. ✅ **Cheaper** - No video generation costs during testing
4. ✅ **More reliable** - No worker failures, no refund logic
5. ✅ **Same UX** - Still visual, still shareable, still likeable

**Then add videos later:**
- Once platform is proven
- Once you have revenue
- Once infrastructure is stable

---

## **UPDATED PRD RECOMMENDATION:**

### **MVP Launch (Images):**
- "Create" page → Image generation (Imagen 3)
- Immediate results (no Drafts page needed!)
- Publish directly to Explore feed
- Likes, profiles, usernames (all work the same)

### **Pages to Build:**
1. ✅ "Create" page - Prompt input, "Generate Image" button
2. ❌ ~~Drafts page~~ (not needed for sync images!)
3. ✅ Publishing modal - Add caption after image loads
4. ✅ Profile page - User's published images
5. ✅ Explore feed - Already built! (works for images too)
6. ✅ Navigation - Links between pages

**Total pages: 4 instead of 5!**

---

## **SHOULD YOU USE IMAGES OR VIDEOS?**

| Feature | Images (Imagen 3) | Videos (Veo) |
|---------|------------------|--------------|
| **Generation Time** | 2-5 seconds | 60-120 seconds |
| **User Experience** | Instant | Must wait in drafts |
| **Complexity** | Simple API call | Background worker |
| **Infrastructure** | Main API only | API + Worker + Redis |
| **Cost** | Free (for now) | 10 tokens |
| **Error Handling** | Simple | Complex (refunds!) |
| **Reliability** | High | Medium (worker can fail) |
| **Testing** | Easy | Harder |
| **MVP Speed** | ✅ Launch today | ⏳ 1-2 extra days |

**My Recommendation: START WITH IMAGES! 📸**

Benefits:
- ✅ Ship faster (today!)
- ✅ Simpler architecture
- ✅ More reliable
- ✅ Lower cost during beta
- ✅ Still achieves social media vision
- ✅ Can add videos in v2

---

## **DECISION TIME:**

**Option A: Images Only (Recommended)** ⭐
- Build Create page (image generation)
- No Drafts page needed
- Ship TODAY
- Add videos later when proven

**Option B: Videos Only**
- Build Create page (video generation)
- Build Drafts page (show pending videos)
- Build Publishing flow
- Test background worker
- Ship in 1-2 days

**Option C: Both (Not Recommended for MVP)**
- Most complex
- Most testing needed
- Slower to ship

**What would you like to do?** I recommend Option A (images) for fastest launch, then add videos in v2 once you have users!
