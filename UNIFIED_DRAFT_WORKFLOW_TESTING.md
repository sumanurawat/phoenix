# Unified Draft-First Workflow - Testing Guide

## Implementation Summary

The unified draft-first workflow has been fully implemented across both images and videos. All content generation now follows this flow:

1. **User clicks Generate** → Immediate redirect to drafts tab
2. **Backend creates pending draft** → Atomic token debit in Firestore transaction
3. **Worker processes asynchronously** → Updates status: pending → processing → draft (or failed)
4. **User sees real-time status** → Visual indicators with loading animations, media previews, error states

---

## Architecture Changes

### Backend Services Created/Modified

#### 1. **CreationService** (`services/creation_service.py`) - NEW
- **Purpose**: Single source of truth for creation lifecycle
- **Key Methods**:
  - `create_pending_creation()` - Atomic token debit + draft creation in Firestore transaction
  - `handle_generation_failure()` - Idempotent token refund with ledger tracking
  - `update_creation_status()` - State transitions (pending → processing → draft)

#### 2. **Async Image Worker** (`jobs/async_image_generation_worker.py`) - NEW
- **Task**: `generate_image_task(creation_id, user_id, prompt, ...)`
- **Flow**:
  1. Updates status to 'processing'
  2. Calls ImageGenerationService.generate_image()
  3. Uploads to R2 storage
  4. Updates status to 'draft' with media URL
  5. On error: Calls creation_service.handle_generation_failure() for refund

#### 3. **Async Video Worker** (`jobs/async_video_generation_worker.py`) - REFACTORED
- **Changes**:
  - Removed duplicate `_refund_tokens` transaction logic
  - Now uses `creation_service.handle_generation_failure()`
  - Added lazy `_get_creation_service()` initializer

#### 4. **Unified API Endpoint** (`api/generation_routes.py`) - NEW
- **Route**: `POST /api/generate/creation`
- **Payload**:
  ```json
  {
    "type": "image",  // or "video"
    "prompt": "A beautiful sunset...",
    "aspect_ratio": "1:1",  // images only
    "orientation": "landscape"  // videos only
  }
  ```
- **Response**: `202 Accepted` with `creation_id`
- **Error Handling**: Automatic refund if queue fails

### Frontend Updates

#### 1. **Create Page** (`templates/create.html`)
- **generateButton Handler**:
  - Now calls `/api/generate/creation` for both images and videos
  - Immediately redirects to `/soho/{username}?tab=drafts` on 202 response
  - Sets sessionStorage flags for navigation state
- **Removed**:
  - Inline image result display
  - Old separate video status polling

#### 2. **Profile Drafts Tab** (`templates/profile.html`)
- **Enhanced `renderDrafts()` Function**:
  - Media type icons (🖼️ for images, 🎬 for videos)
  - **Pending/Processing**: Loading skeleton with shimmer animation
  - **Draft (completed)**: Image preview (clickable) or video player with poster
  - **Failed**: Error message display with red background
  - Status-specific action buttons (Refresh, Publish, Delete)

#### 3. **Celery App** (`celery_app.py`)
- Added `jobs.async_image_generation_worker` to auto-discovery

---

## Testing Procedures

### Pre-Flight Checks

1. **Verify Virtual Environment**:
   ```bash
   source venv/bin/activate
   which python  # Should point to venv/bin/python
   ```

2. **Check Dependencies**:
   ```bash
   pip list | grep -E "celery|redis|google-cloud"
   ```

3. **Verify Environment Variables**:
   ```bash
   # In .env file
   GEMINI_API_KEY=...
   REDIS_HOST=localhost
   REDIS_PORT=6379
   GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials.json
   ```

4. **Start Redis**:
   ```bash
   # Install if needed
   brew install redis  # macOS
   
   # Start Redis server
   redis-server
   ```

5. **Start Celery Worker**:
   ```bash
   # In separate terminal
   source venv/bin/activate
   celery -A celery_app.celery_app worker --loglevel=info
   
   # Look for registered tasks in output:
   # [tasks]
   #   . jobs.async_image_generation_worker.generate_image_task
   #   . jobs.async_video_generation_worker.generate_video_task
   ```

6. **Start Flask App**:
   ```bash
   # In another terminal
   ./start_local.sh
   ```

---

### Test Case 1: Image Generation (Happy Path)

**Objective**: Verify end-to-end image generation with draft-first workflow

1. **Navigate to Create Page**:
   - Go to http://localhost:8080/create
   - Ensure you're logged in

2. **Generate Image**:
   - Select "Image" tab
   - Enter prompt: "A serene mountain lake at sunset"
   - Select aspect ratio: "1:1"
   - Click "Generate"

3. **Verify Immediate Redirect**:
   - Should redirect to `/soho/{your-username}?tab=drafts` within 1 second
   - Browser console should show: `"Redirecting to drafts tab..."`

4. **Check Pending State** (0-5 seconds):
   - Drafts tab should show new card with:
     - 🖼️ icon (image type indicator)
     - Status badge: "Pending" (blue background)
     - Loading skeleton with shimmer animation
     - "Refresh" button
   - Prompt text should be visible

5. **Monitor Processing State** (5-10 seconds):
   - Manual refresh or auto-update should show:
     - Status badge: "Processing" (orange background)
     - Shimmer animation still active

6. **Verify Completed Draft** (10-20 seconds):
   - After ~10-15 seconds, refresh the page
   - Draft card should now show:
     - Status badge: "Draft" (green background)
     - Image preview (clickable thumbnail, max-height 300px)
     - "Publish" and "Delete" buttons
   - Click image → Opens in new tab

7. **Check Firestore**:
   ```bash
   # Check creation document
   # Should have:
   # - status: "draft"
   # - media_url: "https://pub-xxx.r2.dev/..."
   # - media_type: "image"
   ```

8. **Verify Token Deduction**:
   - Check your token balance (should be -1 token)
   - Check `token_transactions` collection for debit record

---

### Test Case 2: Video Generation (Happy Path)

**Objective**: Verify video generation workflow with longer processing time

1. **Navigate to Create Page**:
   - Go to http://localhost:8080/create
   - Select "Video" tab

2. **Generate Video**:
   - Enter prompt: "A cat playing with a ball of yarn"
   - Select orientation: "Landscape"
   - Click "Generate"

3. **Verify Redirect**:
   - Should redirect to drafts immediately

4. **Check Pending State**:
   - 🎬 icon (video type indicator)
   - "Pending" badge
   - Loading skeleton

5. **Monitor Long Processing** (60-120 seconds):
   - Video generation takes longer than images
   - Refresh periodically to see "Processing" state
   - Shimmer animation should persist

6. **Verify Completed Video Draft**:
   - After ~1-2 minutes, draft should show:
     - Video player with poster thumbnail
     - Duration badge (e.g., "8s")
     - "Publish" and "Delete" buttons
   - Click play → Video should play

7. **Check Token Deduction**:
   - Should be -10 tokens for video

---

### Test Case 3: Failure Handling & Token Refund

**Objective**: Verify automatic refunds when generation fails

1. **Trigger Policy Violation** (Image):
   - Prompt: "Violent or inappropriate content" (intentionally violate policy)
   - Generate

2. **Monitor Failure**:
   - Worker should catch `PolicyViolationError`
   - Should call `creation_service.handle_generation_failure()`

3. **Verify Failed State in UI**:
   - Refresh drafts tab
   - Failed card should show:
     - Status badge: "Failed" (red background)
     - Error message: "Generation failed: [reason]"
     - Red background on entire card
     - "Delete" button only (no Publish)

4. **Check Token Refund**:
   ```bash
   # Check token_transactions collection
   # Should have:
   # 1. Debit entry (type: "debit", amount: -1)
   # 2. Refund entry (type: "refund", amount: +1, linked_transaction: <debit_id>)
   # Net change: 0 tokens
   ```

5. **Verify Idempotency**:
   - If worker retries (Celery auto-retry), refund should only happen once
   - Check `refunded` field in creation document (should be `true`)

---

### Test Case 4: Queue Failure Handling

**Objective**: Verify refund if task can't be enqueued

1. **Stop Celery Worker**:
   ```bash
   # Kill Celery worker process
   pkill -f "celery.*worker"
   ```

2. **Attempt Generation**:
   - Try generating image or video
   - API should return 500 error

3. **Verify Immediate Refund**:
   - Check token balance (should be unchanged)
   - Check `token_transactions` for refund entry
   - Error message should appear in UI

4. **Restart Worker**:
   ```bash
   celery -A celery_app.celery_app worker --loglevel=info
   ```

---

### Test Case 5: Publish Flow

**Objective**: Verify publishing draft to posts

1. **From Draft to Post**:
   - Open drafts tab
   - Find a completed draft (status: "draft")
   - Click "Publish" button

2. **Add Caption**:
   - Modal should appear
   - Enter caption: "My first AI creation!"
   - Click "Publish"

3. **Verify Post Appears**:
   - Switch to "POSTS" tab
   - Draft should now appear as published post
   - Should be visible in Explore feed

4. **Check Firestore**:
   - Creation document should have:
     - `status: "published"`
     - `caption: "My first AI creation!"`
     - `published_at: <timestamp>`

---

## Monitoring & Debugging

### Celery Worker Logs

```bash
# Watch worker terminal for:
[2024-01-15 10:30:00,123: INFO/MainProcess] Received task: jobs.async_image_generation_worker.generate_image_task[abc123]
[2024-01-15 10:30:05,456: INFO/ForkPoolWorker-1] Image generated successfully: https://pub-xxx.r2.dev/...
[2024-01-15 10:30:06,789: INFO/ForkPoolWorker-1] Task completed: abc123
```

### Flask App Logs

```bash
# In Flask terminal:
INFO:api.generation_routes:Creating pending creation for user_id=...
INFO:services.creation_service:Created pending creation: creation_id=...
INFO:api.generation_routes:Enqueued image generation task: task_id=...
```

### Firestore Console

1. Go to Firebase Console → Firestore Database
2. Check collections:
   - `creations/{creation_id}` - Creation documents
   - `token_transactions` - Token ledger
   - `users/{user_id}` - User token balance

### Common Issues

#### Worker Not Picking Up Tasks
- **Symptom**: Drafts stuck in "pending" forever
- **Check**: Is Celery worker running?
- **Fix**: `celery -A celery_app.celery_app worker --loglevel=info`

#### Token Not Refunded
- **Symptom**: Failed draft but tokens still deducted
- **Check**: Worker logs for exception during refund
- **Fix**: Manually run `creation_service.handle_generation_failure(creation_id)`

#### Shimmer Animation Not Working
- **Symptom**: Loading skeleton shows but no animation
- **Check**: Browser DevTools → Elements → Check for `shimmer` class
- **Fix**: Hard refresh browser cache (Cmd+Shift+R)

#### Images/Videos Not Loading
- **Symptom**: Broken image icon or video won't play
- **Check**: Network tab → Are R2 URLs 403 Forbidden?
- **Fix**: Verify R2 bucket has public read access

---

## Performance Validation

### Expected Timings

| Action | Expected Duration |
|--------|------------------|
| API call to `/api/generate/creation` | < 500ms |
| Redirect to drafts | < 1 second |
| Image generation (Imagen) | 10-20 seconds |
| Video generation (Veo) | 60-120 seconds |
| Token refund on failure | < 2 seconds |

### Load Testing (Optional)

```bash
# Install Apache Bench
brew install ab

# Test concurrent image generations
ab -n 10 -c 2 -p image_payload.json -T application/json \
   -H "Cookie: session=..." \
   http://localhost:8080/api/generate/creation

# Monitor:
# - Celery worker queue depth
# - Redis memory usage
# - Token transaction conflicts (should be zero due to Firestore transactions)
```

---

## Rollback Plan

If issues occur, rollback steps:

1. **Disable New Endpoint**:
   ```python
   # In app.py, comment out:
   # app.register_blueprint(generation_bp)
   ```

2. **Revert Frontend**:
   - Restore old `templates/create.html` from git history
   - Remove draft enhancements from `templates/profile.html`

3. **Stop Workers**:
   ```bash
   pkill -f "celery.*worker"
   ```

4. **Git Revert**:
   ```bash
   git log --oneline  # Find commit before changes
   git revert <commit-hash>
   ```

---

## Success Criteria

✅ **Backend**:
- [ ] CreationService creates pending drafts with atomic token debit
- [ ] Image worker processes tasks and updates status correctly
- [ ] Video worker uses shared CreationService
- [ ] Token refunds work on failure with idempotency
- [ ] Unified endpoint returns 202 for both image/video

✅ **Frontend**:
- [ ] Generate button redirects to drafts immediately
- [ ] Pending drafts show loading skeleton with shimmer
- [ ] Processing drafts show orange status badge
- [ ] Completed drafts show media previews (img/video)
- [ ] Failed drafts show error message with red background
- [ ] Publish button works from drafts tab

✅ **Integration**:
- [ ] End-to-end flow works for images (generate → draft → publish)
- [ ] End-to-end flow works for videos
- [ ] Token economy is accurate (debit on start, refund on fail)
- [ ] No race conditions or duplicate refunds
- [ ] Celery worker registers both tasks on startup

---

## Next Steps After Testing

1. **Deploy to Dev Environment**:
   ```bash
   gcloud builds submit --config cloudbuild-dev.yaml
   ```

2. **Update Documentation**:
   - API docs with new `/api/generate/creation` endpoint
   - User guide for unified workflow

3. **Monitor Production**:
   - Set up alerts for failed tasks
   - Track token refund metrics
   - Monitor R2 storage costs

4. **Future Enhancements**:
   - Auto-refresh drafts tab (WebSocket or polling)
   - Bulk actions (publish/delete multiple drafts)
   - Draft expiration (auto-delete after 30 days)
   - Progress percentage for video generation

---

## Contact & Support

If you encounter issues during testing:
- Check worker logs first (`celery -A celery_app.celery_app worker --loglevel=debug`)
- Verify Firestore transactions in Firebase Console
- Review this document's "Common Issues" section
- Test with simple prompts before complex ones

**Implementation Complete**: All 6 tasks finished, ready for validation! 🚀
