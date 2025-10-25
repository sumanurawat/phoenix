# Social Platform Implementation - Progress Report

**Date:** October 25, 2025  
**Status:** Core Services Complete - Moving to API Layer

---

## 🎯 Project Vision

Building a complete social and economic platform within Phoenix for AI-generated content (images now, videos later). Users can:
- Generate AI images (costs tokens)
- Share posts to a public feed
- Like and tip creators
- Purchase tokens via Stripe
- Build a following and earn from their art

---

## ✅ Completed: Core Service Layer

### 1. Token Wallet Service (`services/token_service.py`)

**Purpose:** Atomic token balance management with race condition prevention

**Key Features:**
- ✅ `get_balance(user_id)` - Fetch current token count
- ✅ `get_total_earned(user_id)` - Lifetime earnings from tips
- ✅ `deduct_tokens(user_id, amount)` - Spend tokens (atomic)
- ✅ `add_tokens(user_id, amount)` - Credit tokens (atomic)
- ✅ `transfer_tokens(sender, recipient, amount)` - Tipping system
- ✅ `check_sufficient_balance()` - Pre-flight check before spending

**Technical Implementation:**
- Uses Firestore transactions for atomicity
- `Increment()` operations prevent race conditions
- Custom `InsufficientTokensError` exception
- Comprehensive logging for debugging

**Database Impact:**
- Updates `users.tokenBalance` field
- Updates `users.totalTokensEarned` (for tips only)

---

### 2. Transaction Ledger Service (`services/transaction_service.py`)

**Purpose:** Immutable financial audit trail for the token economy

**Key Features:**
- ✅ `record_transaction(user_id, type, amount, details)` - Core logging
- ✅ `record_purchase()` - Log Stripe token purchases
- ✅ `record_generation_spend()` - Log image generation costs
- ✅ `record_tip()` - Log tip transfers (2 records: sent + received)
- ✅ `record_signup_bonus()` - Log welcome tokens
- ✅ `get_user_transactions()` - User transaction history
- ✅ `get_transaction_stats()` - Aggregated user analytics

**Transaction Types:**
- `purchase` - Bought tokens via Stripe
- `generation_spend` - Spent tokens on AI generation
- `tip_sent` - Sent tip to creator
- `tip_received` - Received tip from fan
- `signup_bonus` - Free welcome tokens
- `admin_credit` - Manual admin adjustment
- `refund` - Tokens refunded

**Database Schema:**
```javascript
{
  userId: "firebase_uid",
  type: "generation_spend",
  amount: -5,  // Negative for debits
  timestamp: SERVER_TIMESTAMP,
  details: {
    postId: "abc123",
    prompt: "a cat in space...",
    stripeSessionId: "cs_xxx",  // For purchases
    recipientId: "uid_xyz"  // For tips
  }
}
```

**Key Design Decisions:**
- ✅ Immutable records (never updated/deleted)
- ✅ Perfect audit trail for disputes
- ✅ Supports analytics and reporting
- ✅ Details field flexible for context-specific data

---

### 3. Post Management Service (`services/post_service.py`)

**Purpose:** Manage user-generated content in the social feed

**Key Features:**
- ✅ `create_post(user_id, media_url, caption, prompt)` - New post
- ✅ `get_post(post_id)` - Fetch single post
- ✅ `get_user_posts(user_id)` - User's gallery
- ✅ `get_feed()` - Public discovery feed
- ✅ `increment_like_count()` - Atomic like counter
- ✅ `decrement_like_count()` - Atomic unlike counter
- ✅ `delete_post()` - Remove post (owner only)
- ✅ `get_post_count()` - Total posts by user

**Database Schema:**
```javascript
{
  userId: "firebase_uid",
  type: "image",  // or "video"
  mediaUrl: "https://pub-xxx.r2.dev/generated/user/abc.png",
  caption: "Check out my AI art!",
  prompt: "a cyberpunk city at sunset",  // Private by default
  likeCount: 42,  // Denormalized for performance
  createdAt: SERVER_TIMESTAMP
}
```

**Key Design Decisions:**
- ✅ Prompt field stored but hidden from public API (privacy + future monetization)
- ✅ Denormalized `likeCount` for fast feed rendering
- ✅ Support for both image and video types (future-proof)
- ✅ Pagination support via `start_after` cursor
- ✅ Atomic like count updates prevent race conditions

---

### 4. Like Management Service (`services/like_service.py`)

**Purpose:** Many-to-many user-post relationships for social engagement

**Key Features:**
- ✅ `like_post(user_id, post_id)` - Add like (idempotent)
- ✅ `unlike_post(user_id, post_id)` - Remove like
- ✅ `toggle_like()` - Smart toggle (like/unlike)
- ✅ `check_if_liked()` - Query like status
- ✅ `get_user_liked_posts()` - All posts user liked
- ✅ `get_post_likers()` - All users who liked post
- ✅ `check_multiple_likes()` - Batch check for feed rendering
- ✅ `delete_post_likes()` - Cleanup on post deletion

**Database Schema:**
```javascript
// Document ID: "{userId}_{postId}" (deterministic)
{
  userId: "firebase_uid",
  postId: "post_abc123",
  createdAt: SERVER_TIMESTAMP
}
```

**Key Design Decisions:**
- ✅ Top-level collection (not subcollection) for flexible querying
- ✅ Deterministic document IDs prevent duplicates
- ✅ Existence of document = liked (simple boolean logic)
- ✅ Can query both "posts user liked" and "users who liked post"
- ✅ Batch operations for efficient feed rendering

---

## 🏗️ Database Architecture Summary

### Collections Created

| Collection | Purpose | Key Fields | Special Notes |
|------------|---------|------------|---------------|
| `users` (extend) | User profiles + wallets | `tokenBalance`, `totalTokensEarned` | Single source of truth |
| `posts` | Social feed content | `userId`, `mediaUrl`, `caption`, `prompt`, `likeCount` | Prompt private |
| `transactions` | Financial ledger | `userId`, `type`, `amount`, `details` | Immutable |
| `likes` | User-post relationships | `userId`, `postId` | Deterministic IDs |

### Data Flow Examples

**Image Generation Flow:**
1. User requests generation → Check `tokenBalance` ≥ 5
2. Deduct 5 tokens → Update `users.tokenBalance` (atomic)
3. Generate image → Save to R2
4. Create post → Add to `posts` collection
5. Record transaction → Add to `transactions` (generation_spend)

**Tipping Flow:**
1. User tips 10 tokens → Transfer from sender to recipient (atomic)
2. Update balances → `sender.tokenBalance -= 10`, `recipient.tokenBalance += 10`, `recipient.totalTokensEarned += 10`
3. Record transactions → Two records (tip_sent, tip_received)

**Feed Rendering Flow:**
1. Fetch posts → `get_feed(limit=50)`
2. Check likes → `check_multiple_likes(user_id, [post_ids])`
3. Display → Show like button state + like count

---

## 🔧 Technical Highlights

### Atomic Operations
All balance modifications use Firestore transactions with `Increment()`:
```python
transaction.update(user_ref, {
    'tokenBalance': admin_firestore.Increment(-5)
})
```

This prevents race conditions when multiple requests happen simultaneously.

###Immutable Ledger Pattern
```python
# Transactions are NEVER updated or deleted
doc_ref = db.collection('transactions').document()  # Auto ID
doc_ref.set(transaction_data)  # One-time write
```

### Denormalization for Performance
```python
# Fast: Read from post document
likeCount = post.get('likeCount')  # Single read

# Slow: Count likes collection
likeCount = len(db.collection('likes').where('postId', '==', id).stream())  # N reads
```

We use denormalized counters for speed, backed by atomic `Increment()`.

---

## 📊 Integration with Existing Phoenix Features

### Firebase Authentication
- ✅ Reuses existing user base
- ✅ `uid` is universal key across all collections
- ✅ No separate login/signup needed

### Stripe Integration
- ✅ Extends existing subscription system
- ⏳ TODO: Create token packages (100 tokens = $5, etc.)
- ⏳ TODO: Webhook handler to credit tokens

### R2 Storage
- ✅ Generated images already saved to R2 (recent migration)
- ✅ Public URLs ready for social feed
- ✅ $0 egress = unlimited viral potential

---

## 🚀 Next Steps (API Layer)

### Immediate Tasks
1. **Create API Routes:**
   - `api/post_routes.py` - Post CRUD + feed
   - `api/like_routes.py` - Like toggle + status
   - `api/token_routes.py` - Balance + transactions + tipping

2. **Update Image Generation:**
   - Add token cost check before generation
   - Deduct tokens on success
   - Create post automatically after generation
   - Return updated balance in response

3. **User Profile Enhancement:**
   - Add token fields to user creation (10 token signup bonus)
   - Update auth service to initialize new fields

### Frontend (After API)
- Social feed page with infinite scroll
- User gallery/profile with token balance
- Tip modal for sending tokens
- Token purchase flow (Stripe checkout)

---

## 🎯 Success Metrics

**When this is complete, users will be able to:**
- ✅ Sign up and receive 10 free tokens
- ✅ Generate AI images for 5 tokens each
- ✅ Post generations to a public feed
- ✅ Like and tip other creators
- ✅ Purchase more tokens when they run out
- ✅ Earn tokens from tips on their art
- ✅ View transaction history

**Platform Benefits:**
- Perfect audit trail for disputes
- Analytics on token flow and user engagement
- Scalable social features (ready for video)
- Monetization built-in from day one

---

## 📝 Code Quality Notes

All services include:
- ✅ Comprehensive docstrings
- ✅ Type hints for parameters
- ✅ Detailed logging (INFO/DEBUG/ERROR)
- ✅ Exception handling with specific error types
- ✅ Input validation
- ✅ Atomic operations where needed

**Ready for production deployment after API layer complete.**

---

**Status:** 4/5 core services complete. Moving to API routes next! 🚀
