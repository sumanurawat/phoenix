# Video Generation Local Development Setup - COMPLETE ✅

## Status: FULLY OPERATIONAL

### Services Running

1. ✅ **Redis** - Background service (auto-starts on login)
   - Status: Running on localhost:6379
   - Verified with: `redis-cli ping` → PONG

2. ✅ **Celery Worker** - Processing video jobs
   - Terminal ID: `ffae6289-7df9-474b-a8db-2b85e618d635`
   - Connected to Redis successfully
   - Ready to process: `jobs.async_video_generation_worker.generate_video_task`

3. ✅ **Flask App** - Running on port 8080
   - http://localhost:8080

### Quick Commands

#### Check Redis Status
```bash
redis-cli ping
# Should return: PONG
```

#### Stop Redis (if needed)
```bash
brew services stop redis
```

#### Restart Redis
```bash
brew services restart redis
```

#### Start Celery Worker (if not running)
```bash
export GOOGLE_CLOUD_PROJECT=phoenix-project-386
cd /Users/sumanurawat/Documents/GitHub/phoenix
source venv/bin/activate
celery -A celery_app worker --loglevel=info --concurrency=2 --pool=solo
```

#### Check Celery Worker Status
```bash
celery -A celery_app inspect active
```

### Test Video Generation

Now you can test video generation from your app:

1. Navigate to http://localhost:8080/create
2. Switch to "Video" tab
3. Enter a prompt (e.g., "red dragon breathing fire")
4. Click "Generate Video"

**Expected flow:**
- ✅ HTTP 202 Accepted (job queued)
- ✅ Tokens debited (10 tokens)
- ✅ Creation document created with status `pending`
- ✅ Celery worker picks up job
- ✅ Status updates: `pending` → `processing` → `draft`
- ✅ Video appears in Drafts tab when complete

**If Redis/Celery not running:**
- ✅ HTTP 503 Service Unavailable
- ✅ Tokens automatically refunded
- ✅ Creation marked as `failed` with clear error message
- ✅ User can retry after starting services

### Monitoring

#### Watch Celery Worker Logs
The worker is running in terminal `ffae6289-7df9-474b-a8db-2b85e618d635`

You'll see logs like:
```
[INFO] 🎬 Task starting: generate_video_task [ID: ...]
[INFO] 📝 Updated creation ... status: processing
[INFO] ✅ Task complete: generate_video_task [ID: ...]
```

#### Check Redis Activity
```bash
redis-cli monitor
```

#### Check Firestore for Jobs
Navigate to Firebase Console → Firestore:
- Collection: `creations`
- Filter: `status == 'processing'` or `status == 'draft'`

### Troubleshooting

#### Video Generation Still Fails?
1. Restart Flask app to pick up new error handling
2. Check Celery worker is connected: `celery -A celery_app inspect ping`
3. Verify Redis: `redis-cli ping`

#### Port 6379 Already in Use?
```bash
lsof -ti tcp:6379
# Kill the process if needed
```

#### Worker Keeps Crashing?
Check environment variables:
```bash
echo $GOOGLE_CLOUD_PROJECT
# Should print: phoenix-project-386
```

### Production vs Local Development

| Feature | Local (Now) | Production |
|---------|------------|------------|
| Redis | localhost:6379 (Homebrew) | Cloud Memorystore |
| Worker | Terminal process | Cloud Run Service |
| Queue | Single worker | Auto-scaling workers |
| Videos | Temp files → R2 | Direct to R2 |
| Cost | Free | ~$0.32/video + infrastructure |

### Next Steps (Optional)

1. Test video generation with the new graceful error handling
2. Monitor Celery worker logs during generation
3. Verify drafts refresh immediately after generation (your earlier fix)
4. Test the highlight/scroll effect for new drafts

### Files Changed in This Session

1. `api/video_generation_routes.py` - Added Redis connection error handling
2. `VIDEO_GENERATION_QUEUE_FIX.md` - Comprehensive troubleshooting guide
3. `templates/profile.html` - Draft auto-refresh logic
4. `templates/create.html` - Draft creation flags for refresh

---

**Status**: ✅ **READY FOR TESTING** - All services operational, video generation fully enabled!
