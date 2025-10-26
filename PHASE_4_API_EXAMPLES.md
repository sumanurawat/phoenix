# Phase 4: API Response Examples

**Real-world examples of what the APIs will return**

---

## Username System

### ✅ Check Username Availability

**Request:**
```bash
GET /api/users/check-username?username=PixelPioneer
```

**Response (Available):**
```json
{
  "available": true,
  "message": "Username \"PixelPioneer\" is available"
}
```

**Response (Taken):**
```json
{
  "available": false,
  "message": "Username \"PixelPioneer\" is already taken"
}
```

**Response (Invalid Format):**
```json
{
  "available": false,
  "message": "Username must be at least 3 characters"
}
```

---

### ✅ Claim Username

**Request:**
```bash
POST /api/users/set-username
Content-Type: application/json

{
  "username": "PixelPioneer"
}
```

**Response (Success):**
```json
{
  "success": true,
  "user": {
    "username": "PixelPioneer",
    "firebase_uid": "XyZ123AbC456"
  },
  "message": "Successfully claimed username \"PixelPioneer\""
}
```

**Response (Already Taken - 409):**
```json
{
  "error": "Username 'PixelPioneer' is already taken"
}
```

**Response (Invalid - 400):**
```json
{
  "error": "Username cannot contain consecutive dots or underscores"
}
```

---

### ✅ Get Current User Profile

**Request:**
```bash
GET /api/users/me
Authorization: Bearer <firebase-token>
```

**Response:**
```json
{
  "user": {
    "firebase_uid": "XyZ123AbC456",
    "username": "PixelPioneer",
    "email": "pioneer@example.com",
    "displayName": "Pixel",
    "bio": "AI video artist exploring the boundaries of creativity",
    "profileImageUrl": "https://pub-xxx.r2.dev/profiles/XyZ123.jpg",
    "tokenBalance": 110,
    "totalTokensEarned": 50,
    "createdAt": "2025-10-20T10:30:00Z",
    "updatedAt": "2025-10-26T14:15:00Z"
  }
}
```

---

### ✅ Get Public User Profile

**Request:**
```bash
GET /api/users/PixelPioneer
```

**Response:**
```json
{
  "user": {
    "username": "PixelPioneer",
    "displayName": "Pixel",
    "bio": "AI video artist exploring the boundaries of creativity",
    "profileImageUrl": "https://pub-xxx.r2.dev/profiles/XyZ123.jpg",
    "totalTokensEarned": 50
  }
}
```

**Note:** `tokenBalance` is intentionally hidden for privacy.

**Response (Not Found - 404):**
```json
{
  "error": "User not found"
}
```

---

## Explore Feed

### ✅ Get Explore Feed (Initial Load)

**Request:**
```bash
GET /api/feed/explore?limit=3
```

**Response:**
```json
{
  "success": true,
  "creations": [
    {
      "creationId": "abc123-def456-ghi789",
      "userId": "XyZ123AbC456",
      "username": "PixelPioneer",
      "prompt": "A serene sunset over mountains with vibrant colors",
      "caption": "My latest creation! What do you think?",
      "mediaUrl": "https://pub-xxx.r2.dev/generated/XyZ123/abc123.mp4",
      "aspectRatio": "9:16",
      "duration": 8,
      "likeCount": 42,
      "publishedAt": "2025-10-26T12:00:00Z",
      "isLiked": false
    },
    {
      "creationId": "def456-ghi789-jkl012",
      "userId": "AbC789DeF012",
      "username": "ArtMaster",
      "prompt": "Cyberpunk city at night with neon lights",
      "caption": "Neon dreams 🌃",
      "mediaUrl": "https://pub-xxx.r2.dev/generated/AbC789/def456.mp4",
      "aspectRatio": "16:9",
      "duration": 6,
      "likeCount": 128,
      "publishedAt": "2025-10-26T11:30:00Z",
      "isLiked": true
    },
    {
      "creationId": "ghi789-jkl012-mno345",
      "userId": "DeF012GhI345",
      "username": "CreativeAI",
      "prompt": "Abstract geometric patterns morphing smoothly",
      "caption": "",
      "mediaUrl": "https://pub-xxx.r2.dev/generated/DeF012/ghi789.mp4",
      "aspectRatio": "9:16",
      "duration": 8,
      "likeCount": 73,
      "publishedAt": "2025-10-26T10:45:00Z",
      "isLiked": false
    }
  ],
  "nextCursor": "ghi789-jkl012-mno345",
  "hasMore": true
}
```

---

### ✅ Get Explore Feed (Load More)

**Request:**
```bash
GET /api/feed/explore?limit=3&cursor=ghi789-jkl012-mno345
```

**Response:**
```json
{
  "success": true,
  "creations": [
    {
      "creationId": "jkl012-mno345-pqr678",
      "userId": "GhI345JkL678",
      "username": "VideoWizard",
      "prompt": "Floating islands in the sky with waterfalls",
      "caption": "Sky islands! 🏝️",
      "mediaUrl": "https://pub-xxx.r2.dev/generated/GhI345/jkl012.mp4",
      "aspectRatio": "9:16",
      "duration": 8,
      "likeCount": 95,
      "publishedAt": "2025-10-26T09:20:00Z",
      "isLiked": false
    }
  ],
  "nextCursor": "jkl012-mno345-pqr678",
  "hasMore": false
}
```

**Note:** `hasMore: false` indicates this is the last page.

---

### ✅ Get User Gallery

**Request:**
```bash
GET /api/users/PixelPioneer/creations?limit=2
```

**Response:**
```json
{
  "success": true,
  "user": {
    "username": "PixelPioneer",
    "displayName": "Pixel",
    "bio": "AI video artist exploring the boundaries of creativity",
    "profileImageUrl": "https://pub-xxx.r2.dev/profiles/XyZ123.jpg",
    "totalTokensEarned": 50
  },
  "creations": [
    {
      "creationId": "abc123-def456-ghi789",
      "prompt": "A serene sunset over mountains with vibrant colors",
      "caption": "My latest creation! What do you think?",
      "mediaUrl": "https://pub-xxx.r2.dev/generated/XyZ123/abc123.mp4",
      "aspectRatio": "9:16",
      "duration": 8,
      "likeCount": 42,
      "publishedAt": "2025-10-26T12:00:00Z",
      "isLiked": false
    },
    {
      "creationId": "stu901-vwx234-yza567",
      "prompt": "Ocean waves crashing on a rocky shore",
      "caption": "Nature's power 🌊",
      "mediaUrl": "https://pub-xxx.r2.dev/generated/XyZ123/stu901.mp4",
      "aspectRatio": "16:9",
      "duration": 6,
      "likeCount": 31,
      "publishedAt": "2025-10-25T16:45:00Z",
      "isLiked": true
    }
  ],
  "nextCursor": "stu901-vwx234-yza567",
  "hasMore": true
}
```

---

## Like System

### ✅ Like a Creation

**Request:**
```bash
POST /api/creations/abc123-def456-ghi789/like
Authorization: Bearer <firebase-token>
```

**Response (First Like):**
```json
{
  "success": true,
  "liked": true,
  "likeCount": 43,
  "wasAdded": true
}
```

**Response (Already Liked - Idempotent):**
```json
{
  "success": true,
  "liked": true,
  "likeCount": 43,
  "wasAdded": false
}
```

**Note:** Calling like multiple times is safe (idempotent).

---

### ✅ Unlike a Creation

**Request:**
```bash
DELETE /api/creations/abc123-def456-ghi789/like
Authorization: Bearer <firebase-token>
```

**Response:**
```json
{
  "success": true,
  "liked": false,
  "likeCount": 42,
  "wasRemoved": true
}
```

---

### ✅ Get Like Information

**Request:**
```bash
GET /api/creations/abc123-def456-ghi789/likes
```

**Response (Authenticated User):**
```json
{
  "success": true,
  "likeCount": 42,
  "isLiked": true
}
```

**Response (Unauthenticated):**
```json
{
  "success": true,
  "likeCount": 42,
  "isLiked": false
}
```

---

## Transaction History

### ✅ Get Transaction History

**Request:**
```bash
GET /api/tokens/transactions?limit=10
Authorization: Bearer <firebase-token>
```

**Response:**
```json
{
  "success": true,
  "transactions": [
    {
      "type": "tip_received",
      "amount": 5,
      "timestamp": "2025-10-26T14:30:00Z",
      "description": "Tip Received from @ArtLover",
      "details": {
        "senderUsername": "ArtLover",
        "message": "Amazing work!"
      }
    },
    {
      "type": "generation_spend",
      "amount": -10,
      "timestamp": "2025-10-26T12:00:00Z",
      "description": "Video Generation",
      "details": {
        "creationId": "abc123-def456-ghi789",
        "prompt": "A serene sunset over mountains..."
      }
    },
    {
      "type": "purchase",
      "amount": 110,
      "timestamp": "2025-10-26T10:00:00Z",
      "description": "Token Purchase",
      "details": {
        "stripeSessionId": "cs_test_abc123",
        "packageId": "popular"
      }
    },
    {
      "type": "generation_spend",
      "amount": -10,
      "timestamp": "2025-10-25T18:00:00Z",
      "description": "Video Generation",
      "details": {
        "creationId": "xyz789-abc123-def456",
        "prompt": "Cyberpunk city..."
      }
    },
    {
      "type": "generation_refund",
      "amount": 10,
      "timestamp": "2025-10-25T18:02:00Z",
      "description": "Failed Generation Refund",
      "details": {
        "creationId": "xyz789-abc123-def456",
        "error": "Content policy violation"
      }
    },
    {
      "type": "tip_sent",
      "amount": -5,
      "timestamp": "2025-10-25T16:30:00Z",
      "description": "Tip Sent to @VideoWizard",
      "details": {
        "recipientUsername": "VideoWizard",
        "creationId": "jkl012-mno345-pqr678"
      }
    },
    {
      "type": "signup_bonus",
      "amount": 10,
      "timestamp": "2025-10-20T10:30:00Z",
      "description": "Welcome Bonus",
      "details": {
        "reason": "new_user_signup"
      }
    }
  ],
  "balance": 110,
  "totalEarned": 50,
  "limit": 10
}
```

**Key Features:**
- ✅ Failed generation shows both spend (-10) and refund (+10)
- ✅ Tips show sender/recipient usernames
- ✅ Clear descriptions for every transaction type
- ✅ Current balance and lifetime earnings included

---

### ✅ Filter Transactions by Type

**Request:**
```bash
GET /api/tokens/transactions?type=tip_received&limit=5
Authorization: Bearer <firebase-token>
```

**Response:**
```json
{
  "success": true,
  "transactions": [
    {
      "type": "tip_received",
      "amount": 5,
      "timestamp": "2025-10-26T14:30:00Z",
      "description": "Tip Received from @ArtLover",
      "details": {
        "senderUsername": "ArtLover",
        "message": "Amazing work!"
      }
    },
    {
      "type": "tip_received",
      "amount": 10,
      "timestamp": "2025-10-24T11:00:00Z",
      "description": "Tip Received from @CreativeAI",
      "details": {
        "senderUsername": "CreativeAI",
        "message": "Love this!"
      }
    }
  ],
  "balance": 110,
  "totalEarned": 50,
  "limit": 5
}
```

---

## Publishing Creations

### ✅ Publish Draft to Feed

**Request:**
```bash
POST /api/generate/video/abc123-def456-ghi789/publish
Authorization: Bearer <firebase-token>
Content-Type: application/json

{
  "caption": "My latest AI creation! What do you think? 🎨"
}
```

**Response (Success):**
```json
{
  "success": true,
  "creationId": "abc123-def456-ghi789",
  "message": "Creation published to feed"
}
```

**What Happens in Firestore:**
```javascript
// Before (draft)
{
  userId: "XyZ123AbC456",
  prompt: "A serene sunset over mountains...",
  mediaUrl: "https://pub-xxx.r2.dev/...",
  status: "draft",
  createdAt: SERVER_TIMESTAMP
}

// After (published)
{
  userId: "XyZ123AbC456",
  prompt: "A serene sunset over mountains...",
  mediaUrl: "https://pub-xxx.r2.dev/...",
  status: "published",
  publishedAt: SERVER_TIMESTAMP,
  caption: "My latest AI creation! What do you think? 🎨",
  username: "PixelPioneer",  // Denormalized!
  likeCount: 0,
  createdAt: SERVER_TIMESTAMP,
  updatedAt: SERVER_TIMESTAMP
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "error": "Authentication required",
  "redirect": "/login"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "User not found"
}
```

### 409 Conflict (Username Taken)
```json
{
  "error": "Username 'PixelPioneer' is already taken"
}
```

### 400 Bad Request
```json
{
  "error": "Username must be at least 3 characters"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Failed to load feed"
}
```

---

## Summary

All APIs return:
- ✅ **Consistent structure** (success/error fields)
- ✅ **User-friendly messages**
- ✅ **Complete data** (no missing fields)
- ✅ **Denormalized usernames** (fast feed rendering)
- ✅ **Proper HTTP status codes**

The APIs are production-ready and follow REST best practices!
