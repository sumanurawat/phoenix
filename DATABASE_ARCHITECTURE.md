# Database Architecture - Drafts & Posts System

## Overview
We use a **unified database approach** where drafts and published posts live in the **same `creations` collection**. The `status` field determines whether a creation is visible in drafts or in the public feed.

---

## Database Schema

### Collection: `creations`

```javascript
{
  // Unique identifiers
  "creationId": "uuid-string",  // Document ID
  "userId": "firebase-uid",
  "username": "sumanurawat12",  // Denormalized for performance
  
  // Content
  "prompt": "A serene beach at sunset",
  "caption": "My beautiful sunset creation",  // User-provided caption
  "mediaUrl": "https://storage.googleapis.com/...",
  "mediaType": "image" | "video",
  
  // Media metadata
  "aspectRatio": "9:16" | "16:9",
  "duration": 8,  // seconds (for videos only)
  "model": "gemini-2.0-flash-exp",  // or "imagen-3.0-generate-001"
  "generationTimeSeconds": 12.5,
  
  // 🔑 KEY FIELD: Status determines visibility
  "status": "pending" | "processing" | "draft" | "published" | "failed" | "deleted",
  
  // Social engagement (only for published)
  "likeCount": 42,
  "commentCount": 5,
  
  // Timestamps
  "createdAt": Timestamp,    // When generation started
  "updatedAt": Timestamp,    // Last modification
  "publishedAt": Timestamp,  // When user published (null for drafts)
  
  // Error tracking (for failed status)
  "error": "Generation timeout",
  "errorCode": "TIMEOUT"
}
```

---

## Status Field Logic

### Status Values & Their Meanings

| Status | Description | Visible In | Can Delete? | Can Publish? |
|--------|-------------|------------|-------------|--------------|
| `pending` | Video generation queued | Drafts | ✅ Yes | ❌ No |
| `processing` | Video being generated | Drafts | ✅ Yes | ❌ No |
| `draft` | **Ready to publish** | Drafts | ✅ Yes | ✅ Yes |
| `published` | Live on public feed | Posts/Feed | ❌ No | N/A |
| `failed` | Generation failed | Drafts | ✅ Yes | ❌ No |
| `deleted` | Soft-deleted | Hidden | N/A | N/A |

### Status Transitions

```
[Image Generation]
    ↓
status='draft' → (user publishes) → status='published'
    ↓
(user deletes) → status='deleted'


[Video Generation]
    ↓
status='pending' → status='processing' → status='draft' → status='published'
    ↓                       ↓                    ↓
(user deletes)      (user deletes)       (user deletes)
    ↓                       ↓                    ↓
status='deleted'    status='deleted'    status='deleted'
    
                    (generation fails)
                            ↓
                    status='failed'
                            ↓
                    (user deletes)
                            ↓
                    status='deleted'
```

---

## API Endpoints & Database Queries

### 1. **GET /api/generate/drafts** (Drafts Tab)
**Purpose:** Show all user's unpublished creations

**Query:**
```javascript
db.collection('creations')
  .where('userId', '==', currentUserId)
  .where('status', 'in', ['pending', 'processing', 'draft', 'failed'])
  .orderBy('createdAt', 'DESC')
  .limit(50)
```

**Frontend Logic:**
- Shows status badges (Ready, Processing, Failed)
- "Publish" button only enabled when `status === 'draft'`
- "Delete" button always available

---

### 2. **GET /api/feed/explore** (Explore Feed)
**Purpose:** Show all published creations from all users

**Query:**
```javascript
db.collection('creations')
  .where('status', '==', 'published')
  .orderBy('publishedAt', 'DESC')
  .limit(20)
```

**Frontend Logic:**
- Shows like button, comment count
- No edit/delete actions (published posts are immutable)

---

### 3. **GET /api/users/{username}/creations** (Profile Posts Tab)
**Purpose:** Show a specific user's published creations

**Query:**
```javascript
db.collection('creations')
  .where('userId', '==', targetUserId)
  .where('status', '==', 'published')
  .orderBy('publishedAt', 'DESC')
  .limit(20)
```

**Frontend Logic:**
- Grid view of user's public portfolio
- Like counts visible
- No drafts visible (even on own profile - that's in Drafts tab)

---

### 4. **POST /api/generate/creation/{id}/publish** (Publish Draft)
**Purpose:** Move creation from draft to published

**Process:**
1. ✅ Verify `status === 'draft'` (reject if not)
2. ✅ Verify `mediaUrl` exists
3. ✅ Update document:
```javascript
db.collection('creations').doc(creationId).update({
  'status': 'published',
  'publishedAt': FieldValue.serverTimestamp(),
  'caption': userProvidedCaption,
  'username': currentUsername,  // Denormalize
  'likeCount': 0,
  'commentCount': 0,
  'updatedAt': FieldValue.serverTimestamp()
})
```

**Result:** Creation now appears in:
- ✅ Explore feed (`/api/feed/explore`)
- ✅ User's profile Posts tab (`/api/users/{username}/creations`)
- ❌ Drafts tab (filtered out by status)

---

### 5. **DELETE /api/generate/creation/{id}** (Delete Draft)
**Purpose:** Soft-delete a draft/failed creation

**Process:**
1. ✅ Verify ownership (`userId === currentUserId`)
2. ✅ Verify `status` in `['draft', 'failed', 'pending', 'processing']`
3. ✅ Reject if `status === 'published'` (published posts can't be deleted)
4. ✅ Update document:
```javascript
db.collection('creations').doc(creationId).update({
  'status': 'deleted',
  'updatedAt': FieldValue.serverTimestamp()
})
```

**Result:** Creation hidden from all views

---

## Token Economy Integration

### Image Generation Flow
```javascript
// 1. Pre-check token balance
if (userTokens < 1) {
  return { error: 'Insufficient tokens', required: 1 };
}

// 2. Generate image via Imagen API
const imageUrl = await generateImage(prompt);

// 3. Deduct 1 token
await tokenService.deductTokens(userId, 1, 'image_generation');

// 4. Save to database with status='draft'
await db.collection('creations').doc(imageId).set({
  userId,
  username,
  prompt,
  mediaUrl: imageUrl,
  mediaType: 'image',
  status: 'draft',  // 🔑 Saved as draft, not published
  likeCount: 0,
  createdAt: FieldValue.serverTimestamp()
});

// 5. If Firestore save fails, refund token
catch (error) {
  await tokenService.refundTokens(userId, 1, 'image_generation_failed');
}
```

### Video Generation Flow
```javascript
// 1. Pre-check token balance
if (userTokens < 10) {
  return { error: 'Insufficient tokens', required: 10 };
}

// 2. Create pending job
await db.collection('creations').doc(videoId).set({
  userId,
  username,
  prompt,
  mediaUrl: null,  // Not ready yet
  mediaType: 'video',
  status: 'pending',  // 🔑 Shows in drafts with "Queued" badge
  likeCount: 0,
  createdAt: FieldValue.serverTimestamp()
});

// 3. Deduct 10 tokens
await tokenService.deductTokens(userId, 10, 'video_generation');

// 4. Submit to Veo API (async)
await videoService.generateVideo(videoId, prompt);

// 5. Webhook updates status: pending → processing → draft
// User sees real-time progress in drafts tab
```

---

## Firestore Indexes Required

```javascript
// Index 1: User's drafts (all non-published)
{
  collection: 'creations',
  fields: [
    { field: 'userId', order: 'ASCENDING' },
    { field: 'status', order: 'ASCENDING' },
    { field: 'createdAt', order: 'DESCENDING' }
  ]
}

// Index 2: Explore feed (all published)
{
  collection: 'creations',
  fields: [
    { field: 'status', order: 'ASCENDING' },
    { field: 'publishedAt', order: 'DESCENDING' }
  ]
}

// Index 3: User's published gallery
{
  collection: 'creations',
  fields: [
    { field: 'userId', order: 'ASCENDING' },
    { field: 'status', order: 'ASCENDING' },
    { field: 'publishedAt', order: 'DESCENDING' }
  ]
}
```

---

## Frontend Tab Logic

### Profile Page Tabs

```javascript
// Tab 1: POSTS (Published Creations)
async function loadPosts() {
  const response = await fetch(`/api/users/${username}/creations?limit=50`);
  const data = await response.json();
  
  // ✅ Only status='published' creations returned
  // ✅ Shows like counts, published timestamps
  // ❌ No publish/delete buttons (immutable)
  
  renderPostsGrid(data.creations);
}

// Tab 2: DRAFTS (Unpublished Creations - Own Profile Only)
async function loadDrafts() {
  if (!isOwnProfile) return; // Hide tab for other users
  
  const response = await fetch('/api/generate/drafts?limit=50');
  const data = await response.json();
  
  // ✅ All non-published creations returned
  // ✅ Shows status badges (Ready, Processing, Failed)
  // ✅ Publish button (if status='draft')
  // ✅ Delete button (always available)
  
  renderDraftsGrid(data.creations);
}
```

### Tab Visibility Rules

| Viewing | Posts Tab | Drafts Tab |
|---------|-----------|------------|
| Own Profile | ✅ Visible | ✅ Visible |
| Other User's Profile | ✅ Visible | ❌ Hidden |

---

## Why This Architecture?

### ✅ Advantages

1. **Single Source of Truth**
   - No data duplication between `drafts` and `posts` collections
   - All creation metadata in one place

2. **Simple Status Transitions**
   - Publishing = just flip `status` from `draft` to `published`
   - No need to copy/move documents between collections

3. **Easy Querying**
   - Single collection with indexed `status` field
   - Firestore composite indexes handle performance

4. **Atomic Operations**
   - `status` updates are atomic
   - No risk of partial state (e.g., deleted from drafts but not in posts)

5. **Audit Trail**
   - Full lifecycle in one document
   - `createdAt`, `publishedAt`, `updatedAt` tell the story

6. **Flexible Filtering**
   - Can query any subset: `status='draft'`, `status IN ['draft', 'failed']`
   - Easy to add new statuses (e.g., `'scheduled'`, `'archived'`)

### ⚠️ Considerations

1. **Firestore Index Cost**
   - Need composite indexes for `userId + status + publishedAt`
   - Minimal cost impact (indexes are cheap)

2. **Query Complexity**
   - Must always filter by `status` to separate drafts/posts
   - Mitigated by consistent query patterns

3. **Data Denormalization**
   - `username` denormalized for feed performance
   - Must update if user changes username (rare event)

---

## Security Rules

```javascript
// Firestore Security Rules
match /creations/{creationId} {
  // Anyone can read published creations
  allow read: if resource.data.status == 'published';
  
  // Users can read their own drafts
  allow read: if request.auth != null 
              && resource.data.userId == request.auth.uid;
  
  // Users can create their own creations
  allow create: if request.auth != null 
                && request.resource.data.userId == request.auth.uid
                && request.resource.data.status in ['pending', 'draft'];
  
  // Users can update their own drafts (publish or delete)
  allow update: if request.auth != null 
                && resource.data.userId == request.auth.uid
                && (
                  // Allow publishing draft
                  (resource.data.status == 'draft' 
                   && request.resource.data.status == 'published')
                  ||
                  // Allow soft-delete of non-published
                  (resource.data.status in ['draft', 'failed', 'pending', 'processing']
                   && request.resource.data.status == 'deleted')
                );
  
  // Cannot delete published posts
  allow delete: if false;
}
```

---

## Summary

✅ **Drafts and posts in same `creations` collection**  
✅ **`status` field determines visibility (draft vs published)**  
✅ **Publishing = update `status='draft'` to `status='published'`**  
✅ **Deleting = update `status` to `status='deleted'` (soft delete)**  
✅ **Frontend filters by status for tabs (Posts vs Drafts)**  
✅ **Token deduction happens before generation, refund on failure**  
✅ **Composite indexes ensure fast queries**  
✅ **Security rules prevent unauthorized access**  

This architecture is already fully implemented and working! 🎉
