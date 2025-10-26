# Phase 4: Deployment Steps

**Quick reference for deploying Phase 4 social features**

---

## Prerequisites ✅

Before deploying, ensure:
- [ ] Phase 3 is deployed and working (video generation)
- [ ] Firestore indexes are created
- [ ] Backend tests pass

---

## Step 1: Deploy Firestore Rules

```bash
cd /Users/sumanurawat/Documents/GitHub/phoenix
firebase deploy --only firestore:rules
```

**Expected Output:**
```
✔ Deploy complete!
```

**What This Does:**
- Adds `usernames` collection rules (public read, backend write)
- Updates `creations` rules (public read for published)
- Updates `likes` rules (works with creationId)
- Updates `users` rules (protects username field)

---

## Step 2: Deploy Backend to Cloud Run

```bash
gcloud builds submit --config cloudbuild.yaml .
```

**Expected Output:**
```
✔ Build finished successfully
✔ Deploying to Cloud Run...
✔ Service [phoenix-api-prod] revision [phoenix-api-prod-00123-abc] has been deployed
```

**What This Deploys:**
- New services: `user_service.py`
- New API routes: `user_routes.py`, `feed_routes.py`
- Updated routes: `video_generation_routes.py`, `token_routes.py`
- Updated service: `like_service.py`

---

## Step 3: Verify Backend APIs

### Test Username System

```bash
# Replace $TOKEN with your Firebase auth token
# Get token from browser: firebase.auth().currentUser.getIdToken()

# Test availability check
curl "https://phoenix-<PROJECT_ID>.run.app/api/users/check-username?username=TestUser"

# Expected: {"available": true, "message": "..."}
```

### Test Explore Feed

```bash
curl "https://phoenix-<PROJECT_ID>.run.app/api/feed/explore?limit=5"

# Expected: {"success": true, "creations": [], "nextCursor": null, "hasMore": false}
# (Empty array if no published creations yet)
```

### Test Transaction History

```bash
curl "https://phoenix-<PROJECT_ID>.run.app/api/tokens/transactions?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Expected: {"success": true, "transactions": [...], "balance": 0, "totalEarned": 0}
```

---

## Step 4: Create First Username (Manual Test)

1. **Login to your app** (get auth token)

2. **Claim username:**
```bash
curl -X POST "https://phoenix-<PROJECT_ID>.run.app/api/users/set-username" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "Pioneer"}'
```

3. **Verify in Firestore:**
   - Go to Firestore console
   - Check `usernames` collection has document `pioneer`
   - Check your user document has `username: "Pioneer"`

---

## Step 5: Publish a Creation (Test Feed)

1. **Generate a video** (use existing endpoint)

2. **Wait for it to complete** (status: "draft")

3. **Publish it:**
```bash
curl -X POST "https://phoenix-<PROJECT_ID>.run.app/api/generate/video/<CREATION_ID>/publish" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"caption": "My first video!"}'
```

4. **Verify in Firestore:**
   - Creation document should have:
     - `status: "published"`
     - `username: "Pioneer"`
     - `caption: "My first video!"`
     - `likeCount: 0`

---

## Step 6: Test Like System

```bash
# Like the creation
curl -X POST "https://phoenix-<PROJECT_ID>.run.app/api/creations/<CREATION_ID>/like" \
  -H "Authorization: Bearer $TOKEN"

# Expected: {"success": true, "liked": true, "likeCount": 1, "wasAdded": true}

# Unlike the creation
curl -X DELETE "https://phoenix-<PROJECT_ID>.run.app/api/creations/<CREATION_ID>/like" \
  -H "Authorization: Bearer $TOKEN"

# Expected: {"success": true, "liked": false, "likeCount": 0, "wasRemoved": true}
```

---

## Step 7: Test Explore Feed

```bash
curl "https://phoenix-<PROJECT_ID>.run.app/api/feed/explore?limit=10"

# Expected: {"success": true, "creations": [{"creationId": "...", "username": "Pioneer", ...}], ...}
```

---

## Step 8: Test User Gallery

```bash
curl "https://phoenix-<PROJECT_ID>.run.app/api/users/Pioneer/creations?limit=10"

# Expected: {
#   "success": true,
#   "user": {"username": "Pioneer", ...},
#   "creations": [...]
# }
```

---

## Step 9: Monitor Logs

```bash
# Watch API logs for errors
gcloud run services logs read phoenix-api-prod --region=us-central1 --follow --limit=50
```

**Look for:**
- `🚀 Published creation ... for user ... (@Pioneer)` - Publish success
- `User ... liked creation ...` - Like success
- `User ... claimed username 'Pioneer'` - Username claim success

---

## Common Issues & Fixes

### Issue: "Username already taken" (409)
**Cause:** Username was claimed in a previous test
**Fix:** Try a different username or delete from `usernames` collection

### Issue: Explore feed empty
**Cause:** No published creations yet
**Fix:** Publish at least one creation (Step 5)

### Issue: "User not authenticated" (401)
**Cause:** Invalid or expired Firebase token
**Fix:** Get fresh token from browser: `await firebase.auth().currentUser.getIdToken()`

### Issue: Firestore permission denied
**Cause:** Firestore rules not deployed or incorrect
**Fix:** Re-run `firebase deploy --only firestore:rules`

---

## Rollback Procedure

If Phase 4 deployment fails:

1. **Revert Firestore rules:**
```bash
git checkout HEAD~1 firestore.rules
firebase deploy --only firestore:rules
```

2. **Revert backend code:**
```bash
git revert HEAD
git push origin main
gcloud builds submit --config cloudbuild.yaml .
```

---

## Success Criteria

Phase 4 deployment is successful when:

- [ ] Firestore rules deployed
- [ ] Backend deployed to Cloud Run
- [ ] Username claim works (atomic)
- [ ] Explore feed returns published creations
- [ ] Like/unlike works (count updates)
- [ ] User gallery works
- [ ] Transaction history shows all types
- [ ] No errors in logs

---

## Next: Frontend Development

With the backend deployed, you can now build:

1. **Username onboarding page** (`/welcome/create-username`)
2. **Explore feed** (`/explore`)
3. **User profile page** (`/profile/<username>`)
4. **Transaction history page** (`/profile/transactions`)

See `PHASE_4_BACKEND_COMPLETE.md` for detailed frontend integration guide.

---

**Estimated deployment time:** 10 minutes

**Questions?** Check logs or review API docs in `PHASE_4_BACKEND_COMPLETE.md`.
