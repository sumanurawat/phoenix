# Phase 4 Testing Guide

**Quick guide to test the new Phase 4 APIs**

---

## 🚀 How to Access the Test Page

1. **Start the server:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ./start_local.sh
   ```

2. **Login to Phoenix:**
   - Go to http://localhost:8080
   - Login with your account

3. **Navigate to the test page:**
   - Go to http://localhost:8080/phase4-test
   - You'll see a beautiful testing interface!

---

## 🧪 What You Can Test

### 1. Username System

**Check Availability:**
- Enter any username (e.g., "PixelPioneer")
- Click "Check Availability"
- See if it's available or taken

**Claim Username:**
- Enter your desired username
- Click "Claim Username"
- Your username is now claimed atomically!

**Get Your Profile:**
- Click "Get My Profile"
- See your complete user data including:
  - Username
  - Email
  - Token balance
  - Total tokens earned

---

### 2. Explore Feed

**Load Feed:**
- Set the limit (1-50)
- Click "Load Feed"
- See all published creations from all users
- Each creation shows:
  - Username
  - Prompt
  - Caption
  - Like count
  - Duration & aspect ratio
  - Like/Unlike button

**Like/Unlike:**
- Click the "Like" button on any creation
- It turns red when liked
- Click again to unlike
- Like count updates in real-time

---

### 3. Transaction History

**Load Transactions:**
- Set the number of transactions (1-100)
- Click "Load Transactions"
- See your complete transaction history:
  - Current balance
  - Total earned
  - All transactions with descriptions:
    - Token Purchase → +110 tokens
    - Video Generation → -10 tokens
    - Failed Generation Refund → +10 tokens
    - Tip Received from @username → +5 tokens

---

### 4. User Gallery

**Load Gallery:**
- Enter any username (must exist)
- Click "Load Gallery"
- See:
  - User profile info
  - All their published creations
  - Number of creations
  - Whether there are more to load

---

## 📋 Testing Checklist

### Before You Start
- [ ] Server is running
- [ ] You're logged in
- [ ] You have at least 10 tokens (for testing video generation)

### Username Tests
- [ ] Check if "TestUser123" is available
- [ ] Claim your own unique username
- [ ] Try to claim the same username again (should fail with 409)
- [ ] Try invalid usernames (too short, special chars)
- [ ] Get your profile to verify username is set

### Feed Tests
- [ ] Load the explore feed (should be empty if no published creations)
- [ ] Generate a video (use existing video generation)
- [ ] Wait for it to complete (status: "draft")
- [ ] Publish it with a caption
- [ ] Reload the explore feed (should see your creation!)
- [ ] Like your own creation
- [ ] Unlike it

### Transaction Tests
- [ ] Load transaction history
- [ ] Verify you see your signup bonus (10 tokens)
- [ ] Verify you see any token purchases
- [ ] Generate a video and check the -10 spend appears
- [ ] If generation fails, verify you see +10 refund

### Gallery Tests
- [ ] Load your own gallery (using your username)
- [ ] Verify it shows all your published creations
- [ ] Try loading another user's gallery (if they exist)

---

## 🎯 Expected Results

### Successful Username Claim
```json
{
  "success": true,
  "user": {
    "username": "PixelPioneer",
    "firebase_uid": "..."
  },
  "message": "Successfully claimed username \"PixelPioneer\""
}
```

### Explore Feed (with creations)
```json
{
  "success": true,
  "count": 2,
  "hasMore": false
}
```

### Transaction History
```json
{
  "balance": 110,
  "totalEarned": 0,
  "transactionCount": 2
}
```

---

## 🐛 Troubleshooting

### "User not authenticated" error
**Fix:** Make sure you're logged in. Go to http://localhost:8080 and login first.

### Empty explore feed
**Fix:** No published creations yet. Generate and publish a video first:
1. Go to the video generation page
2. Generate a video
3. Wait for it to complete
4. Publish it
5. Reload the test page

### Username already taken
**Fix:** Try a different username. Check Firestore console to see claimed usernames.

### No transactions showing
**Fix:** You need to have done at least one transaction:
- Purchase tokens
- Generate a video
- Receive signup bonus (should be automatic)

---

## 🔍 API Endpoints Being Tested

| Feature | Endpoint | Method |
|---------|----------|--------|
| Check username | `/api/users/check-username?username=X` | GET |
| Claim username | `/api/users/set-username` | POST |
| Get profile | `/api/users/me` | GET |
| Explore feed | `/api/feed/explore?limit=10` | GET |
| Like creation | `/api/creations/{id}/like` | POST |
| Unlike creation | `/api/creations/{id}/like` | DELETE |
| Transaction history | `/api/tokens/transactions?limit=10` | GET |
| User gallery | `/api/users/{username}/creations` | GET |

---

## 💡 Tips

1. **Open Browser DevTools** (F12) to see network requests and responses
2. **Test with multiple users** to see the social features in action
3. **Try edge cases:**
   - Very long usernames (>20 chars - should fail)
   - Special characters in usernames
   - Liking the same creation twice
   - Loading feed with limit=1

---

## ✅ Success Criteria

Phase 4 is working correctly when:

- ✅ You can claim a unique username
- ✅ Explore feed shows published creations
- ✅ Like/unlike updates the count immediately
- ✅ Transaction history shows all your transactions
- ✅ User galleries work for any username
- ✅ No errors in the browser console
- ✅ All JSON responses are well-formatted

---

**Happy Testing! 🚀**

If you find any bugs, they're likely in the frontend (which we haven't built yet).
The backend APIs are solid!
