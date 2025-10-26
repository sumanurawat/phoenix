# 🎯 Final Build Plan - Image-Based Social Platform

## **CURRENT STATE ANALYSIS**

### ✅ What's Already Working:
1. **Backend APIs (100% Complete)**
   - `POST /api/image/generate` - Generate images (Imagen 3)
   - `GET /api/users/<username>` - Get user profile
   - `GET /api/users/<username>/creations` - Get user's published images
   - `GET /api/feed/explore` - Get explore feed
   - `POST /api/creations/:id/like` - Like system
   - `GET /api/tokens/balance` - Token balance
   - `POST /api/users/set-username` - Username claiming

2. **Frontend Pages (Partially Complete)**
   - ✅ `/username-setup` - Username onboarding (DONE)
   - ✅ `/explore` - Social feed with likes (DONE)
   - ✅ `/buy-tokens` - Token purchase (EXISTS)
   - ⏳ `/create` - Image generation (TODO)
   - ⏳ `/users/<username>` - Public profile (TODO)
   - ⏳ Navigation (TODO)

3. **Database & Infrastructure**
   - ✅ Firestore collections configured
   - ✅ Firestore security rules deployed
   - ✅ Firestore indexes deployed
   - ✅ R2 storage configured
   - ✅ Cloud Run deployment ready

### ❌ What's Missing (To Complete MVP):
1. "Create" page for image generation
2. Public profile page
3. Navigation bar
4. Adapt explore feed for images (currently expects videos)
5. Adapt like system for images (currently expects creations)

---

## **STRATEGIC DECISION: Creations vs Images**

### **Problem:** Two Database Collections

**Current:**
```javascript
// For videos (Phase 3/4)
creations/
  creationId: "uuid"
  status: "published"
  mediaUrl: "video.mp4"
  aspectRatio: "9:16"
  duration: 8

// For images (existing)
image_generations/
  image_id: "uuid"
  image_url: "image.png"
  aspect_ratio: "9:16"
```

### **Solution: Use ONE Collection for Social Platform**

**Option A: Use `creations` for everything** ⭐ RECOMMENDED
- Already has social features (likes, explore feed)
- Already has username denormalization
- Already has Firestore indexes
- Works with existing explore page
- Easy to add videos later

**Option B: Migrate to `image_generations`**
- Need to rebuild explore feed
- Need to rebuild like system
- Need new indexes
- More work, same result

### **DECISION: Use `creations` collection for images!**

**Why:**
- ✅ Explore feed already queries `creations`
- ✅ Likes already reference `creations`
- ✅ All indexes already exist
- ✅ Just need to adapt generation API

**Changes needed:**
- Image generation API should create `creation` document (not `image_generations`)
- Set `mediaType: "image"` to distinguish from videos
- Keep same schema structure

---

## **UPDATED DATABASE SCHEMA**

### **Creations Collection (Images & Videos):**
```javascript
creations/
  creationId: "uuid"
  userId: "7Vd9KHo..."
  username: "sumanurawat12"        // Denormalized for feed

  // Content
  mediaType: "image"                // or "video"
  mediaUrl: "https://r2.../image.png"
  prompt: "A serene sunset"
  caption: "My first creation!"

  // Image-specific (when mediaType = "image")
  aspectRatio: "9:16"
  generationTimeSeconds: 3.45

  // Video-specific (when mediaType = "video")
  // aspectRatio: "9:16"
  // duration: 8

  // Social
  status: "published"               // For images: always "published" immediately
  likeCount: 5

  // Timestamps
  createdAt: timestamp
  publishedAt: timestamp            // Same as createdAt for images
  updatedAt: timestamp
```

**Benefits:**
- ✅ One feed shows both images and videos
- ✅ One like system works for both
- ✅ One profile page shows all creations
- ✅ Easy to add videos later

---

## **DETAILED BUILD PLAN**

### **Phase 1: Adapt Image Generation to Use Creations Collection**

**Goal:** Make image generation create `creation` documents instead of `image_generations`

**Files to Modify:**
1. `api/image_routes.py`

**Changes:**
```python
# BEFORE (current):
db.collection('image_generations').add({...})

# AFTER (new):
creation_ref = db.collection('creations').document(image_id)
creation_ref.set({
    'creationId': image_id,
    'userId': user_id,
    'username': username,  # Get from user doc
    'mediaType': 'image',
    'mediaUrl': image_url,
    'prompt': prompt,
    'caption': '',  # Empty initially
    'aspectRatio': '9:16',
    'generationTimeSeconds': generation_time,
    'status': 'published',  # Images are published immediately!
    'likeCount': 0,
    'createdAt': firestore.SERVER_TIMESTAMP,
    'publishedAt': firestore.SERVER_TIMESTAMP,
    'updatedAt': firestore.SERVER_TIMESTAMP
})
```

**Estimated Time:** 15 minutes

---

### **Phase 2: Build "Create" Page**

**Goal:** Beautiful, Sora-inspired UI for generating images

**File to Create:** `templates/create.html`

**Features:**
- Centered card design (max 600px width)
- Large text area for prompt
- Character counter (max 500 chars)
- "Generate Image" button
- Shows token cost (FREE for now, or set cost later)
- Loading state with spinner
- Success: Show generated image with caption input
- Error handling

**UI Flow:**
```
1. User enters prompt
2. Clicks "Generate Image"
3. Button shows loading spinner (3-5 seconds)
4. Image appears below with:
   - Generated image display
   - Caption input field
   - "Share to Explore" button
5. User adds caption
6. Clicks "Share" → Redirects to /explore
```

**API Calls:**
```javascript
// Generate
POST /api/image/generate
Body: { prompt: "..." }
Response: { success: true, image: {...} }

// Update caption (optional - or just set in frontend)
PATCH /api/creations/:id
Body: { caption: "..." }
```

**Estimated Time:** 45 minutes

---

### **Phase 3: Build Public Profile Page**

**Goal:** User gallery showing all published creations

**File to Create:** `templates/profile.html`
**Route to Add:** `app.py` - `@app.route('/users/<username>')`

**Features:**
- Header section:
  - Profile avatar (first letter of username in circle)
  - Username @handle
  - Bio
  - Stats: X creations, Y tokens earned (from tips - future)
- Grid of published images/videos (3 columns)
- Like counts on each
- Click image → Opens modal/lightbox
- Empty state if no creations

**API Calls:**
```javascript
GET /api/users/<username>
Response: { user: { username, bio, displayName, ... } }

GET /api/users/<username>/creations
Response: { creations: [...], nextCursor: "..." }
```

**Estimated Time:** 45 minutes

---

### **Phase 4: Add Navigation**

**Goal:** Consistent navigation across all pages

**File to Modify:** `templates/base.html`

**Navigation Items:**
```
Logo | Create | Explore | [Token Balance] | [Profile Avatar ▼]
                                              ├─ My Profile
                                              ├─ Buy Tokens
                                              ├─ Transaction History
                                              └─ Logout
```

**Responsive:**
- Desktop: Full nav bar
- Mobile: Hamburger menu

**Estimated Time:** 30 minutes

---

### **Phase 5: Update Explore Feed for Images**

**Goal:** Make explore feed display images properly

**File to Modify:** `templates/explore.html`

**Changes:**
```javascript
// BEFORE (video player):
<video controls>
  <source src="${creation.mediaUrl}" type="video/mp4">
</video>

// AFTER (conditional rendering):
if (creation.mediaType === 'image') {
  <img src="${creation.mediaUrl}" alt="${creation.prompt}">
} else {
  <video controls>
    <source src="${creation.mediaUrl}" type="video/mp4">
  </video>
}
```

**Estimated Time:** 15 minutes

---

### **Phase 6: Add Caption Editing (Optional Enhancement)**

**Goal:** Let users add/edit captions after generation

**Options:**

**Option A: Inline on Create Page** (Recommended for MVP)
- After image generates, show caption input immediately
- No separate modal needed
- User fills caption and clicks "Share"
- Already part of Create page design

**Option B: Separate Modal**
- After generation, show "Add Caption" button
- Opens modal with caption input
- More clicks, but cleaner separation

**Estimated Time:** Already included in Create page (Phase 2)

---

### **Phase 7: Testing & Fixes**

**Goal:** Complete end-to-end testing

**Test Scenarios:**

1. **New User Journey:**
   - Sign up with new email
   - Redirected to username setup
   - Claim username "test_user_123"
   - Redirected to explore (empty state)
   - Click "Create" in nav
   - Generate image: "A serene mountain sunset"
   - Add caption: "My first creation!"
   - Click "Share to Explore"
   - Image appears on explore feed
   - Like own creation (should work)
   - Visit own profile
   - See creation in grid

2. **Second User Journey:**
   - Sign up with different email
   - Claim username "test_viewer_456"
   - Visit explore
   - See first user's image
   - Like the image
   - Visit first user's profile `/users/test_user_123`
   - See their creation

3. **Edge Cases:**
   - Try to claim taken username (should fail)
   - Generate image with empty prompt (should error)
   - Try to share without caption (should work - caption optional)
   - Refresh page after liking (like should persist)

**Estimated Time:** 45 minutes

---

### **Phase 8: Deployment**

**Goal:** Deploy to production

**Steps:**

1. **Pre-deployment Checklist:**
   - [ ] All tests pass locally
   - [ ] Firestore indexes show "Enabled"
   - [ ] Environment variables in Secret Manager
   - [ ] R2 bucket configured with public URL
   - [ ] Stripe in test mode (switch to live later)

2. **Deploy:**
   ```bash
   # Deploy API server
   gcloud builds submit --config=cloudbuild.yaml

   # Verify deployment
   gcloud run services describe phoenix-api-server --region=us-central1

   # Check logs
   gcloud run services logs read phoenix-api-server --region=us-central1 --limit=50
   ```

3. **Post-deployment:**
   - [ ] Visit production URL
   - [ ] Test username setup
   - [ ] Test image generation
   - [ ] Test explore feed
   - [ ] Test likes
   - [ ] Test profiles

**Estimated Time:** 30 minutes

---

## **COMPLETE TIMELINE**

| Phase | Task | Time | Running Total |
|-------|------|------|---------------|
| 1 | Adapt image API to use creations | 15 min | 0:15 |
| 2 | Build Create page | 45 min | 1:00 |
| 3 | Build Profile page | 45 min | 1:45 |
| 4 | Add Navigation | 30 min | 2:15 |
| 5 | Update Explore for images | 15 min | 2:30 |
| 6 | Caption editing | 0 min | 2:30 |
| 7 | Testing & Fixes | 45 min | 3:15 |
| 8 | Deployment | 30 min | 3:45 |

**Total Estimated Time: ~4 hours**

**Buffer for unknowns: +1 hour**

**Realistic Total: 5 hours to launch** 🚀

---

## **ORDER OF EXECUTION**

### **Session 1: Backend & Core Page (1.5 hours)**
1. ✅ Phase 1: Adapt image API (15 min)
2. ✅ Phase 2: Build Create page (45 min)
3. ✅ Phase 5: Update Explore feed (15 min)
4. ☕ **Break** (15 min)

### **Session 2: Social Features (1.5 hours)**
5. ✅ Phase 3: Build Profile page (45 min)
6. ✅ Phase 4: Add Navigation (30 min)
7. ☕ **Break** (15 min)

### **Session 3: Testing & Launch (2 hours)**
8. ✅ Phase 7: Complete testing (45 min)
9. ✅ Fix any bugs found (30 min)
10. ✅ Phase 8: Deploy to production (30 min)
11. 🎉 **GO LIVE!**

---

## **SUCCESS CRITERIA**

### **MVP is Complete When:**
- ✅ User can sign up and claim username
- ✅ User can generate an image from prompt
- ✅ Image appears on explore feed immediately
- ✅ User can like images on explore feed
- ✅ User can visit other users' profiles
- ✅ User can see their own profile with all creations
- ✅ Navigation works between all pages
- ✅ Everything works on production (not just local)

---

## **FUTURE ENHANCEMENTS (Post-Launch)**

**Week 1:**
- Add token costs for image generation (5 tokens/image)
- Add signup bonus (50 free tokens)
- Add image download button
- Add share buttons (Twitter, copy link)

**Week 2:**
- Add comments on creations
- Add following system
- Add notifications

**Month 1:**
- Add video generation (async with Celery)
- Add tipping system
- Add creator monetization

---

## **RISK MITIGATION**

### **Potential Issues:**

**Issue 1: Firestore index still building**
- **Status:** Should be done by now (deployed 30+ min ago)
- **Check:** https://console.firebase.google.com/project/phoenix-project-386/firestore/indexes
- **Mitigation:** Can test locally while it builds

**Issue 2: Image generation fails**
- **Cause:** Imagen API quota, safety filters
- **Mitigation:** Proper error handling already in place
- **Fallback:** Show clear error message to user

**Issue 3: R2 storage not accessible**
- **Cause:** Bucket permissions, URL config
- **Check:** Try accessing an R2 URL directly
- **Mitigation:** Verify R2_PUBLIC_URL in environment

**Issue 4: Explore feed shows nothing**
- **Cause:** No published creations exist yet
- **Expected:** Should show empty state
- **Solution:** Generate first image to populate feed

---

## **READY TO START?**

**Next Step: Phase 1 - Adapt Image API**

This is the foundation. Once we modify the image generation API to create `creation` documents instead of `image_generations`, everything else falls into place.

**Shall we begin?** 🚀
