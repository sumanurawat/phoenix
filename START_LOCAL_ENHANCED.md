# Start Local Script - Now with Automatic Redis & Celery

## What Changed

`start_local.sh` now automatically manages all required services:

### Before (Manual Setup)
```bash
# Terminal 1: Start Redis
brew services start redis

# Terminal 2: Start Celery worker  
export GOOGLE_CLOUD_PROJECT=phoenix-project-386
celery -A celery_app worker --loglevel=info --concurrency=2 --pool=solo

# Terminal 3: Start Flask
./start_local.sh
```

### After (Single Command)
```bash
./start_local.sh
```

## What It Does Now

1. ✅ **Checks virtual environment** (activates if needed)
2. ✅ **Cleans port 8080** (kills any existing processes)
3. ✅ **Starts Redis** (if not running)
4. ✅ **Starts Celery worker** (in background)
5. ✅ **Builds React frontend** (Reel Maker)
6. ✅ **Starts Flask server** (port 8080)
7. ✅ **Cleans up on exit** (Ctrl+C stops Celery gracefully)

## Usage

### Start Everything
```bash
./start_local.sh
```

### Stop Everything
```
Press Ctrl+C in the terminal
```

This will:
- Stop Flask server
- Stop Celery worker
- Leave Redis running (system service)

### Monitor Celery Worker
```bash
# Watch worker logs in real-time
tail -f celery_worker.log

# Or check last 50 lines
tail -50 celery_worker.log
```

## What Gets Started

| Service | Status | Purpose |
|---------|--------|---------|
| Redis | Port 6379 | Message broker for Celery |
| Celery Worker | Background | Processes video generation jobs |
| Flask | Port 8080 | Main web application |

## If Redis Not Installed

The script will gracefully handle missing Redis:

```
❌ Redis not installed. Video generation will use graceful fallback.
   To enable video generation, install Redis: brew install redis
   (Image generation and other features will work normally)
```

- Image generation (1 token) works fine
- Video generation returns 503 with auto-refund
- All other features work normally

## Logs

### Flask Logs
Displayed in terminal (standard output)

### Celery Worker Logs
Saved to `celery_worker.log` (automatically created)

```bash
# Watch in real-time
tail -f celery_worker.log

# Search for errors
grep ERROR celery_worker.log

# See task completions
grep "Task complete" celery_worker.log
```

## Troubleshooting

### Redis Already Running (Different Port)
```bash
# Check Redis status
redis-cli ping

# If on different port
redis-cli -p <port> ping
```

### Celery Worker Not Starting
Check logs:
```bash
cat celery_worker.log
```

Common issues:
- Missing `GOOGLE_CLOUD_PROJECT` env var → Script sets it automatically
- Redis not running → Script starts it automatically
- Port 6379 in use → Kill existing Redis: `pkill redis-server`

### Port 8080 Still Occupied
The script kills processes automatically, but if it fails:
```bash
lsof -ti tcp:8080 | xargs kill -9
```

## Advanced Usage

### Start With Custom Celery Concurrency
Edit line in `start_local.sh`:
```bash
celery -A celery_app worker --loglevel=info --concurrency=4 --pool=solo
```

### Enable Celery Beat (Scheduled Tasks)
```bash
celery -A celery_app worker --loglevel=info --beat
```

### Debug Mode
Add to `start_local.sh` before `python app.py`:
```bash
export FLASK_DEBUG=1
```

## Comparison with Production

| Feature | Local (`start_local.sh`) | Production |
|---------|-------------------------|------------|
| Redis | localhost:6379 (daemon) | Cloud Memorystore |
| Celery | Single worker process | Cloud Run Service |
| Flask | Development server | Gunicorn + Cloud Run |
| Logs | Terminal + files | Cloud Logging |
| Scaling | Manual | Auto-scaling |

## Files Modified

1. **`start_local.sh`**
   - Added Redis detection and startup
   - Added Celery worker background process
   - Added cleanup handler for Ctrl+C
   - Added log file redirection

2. **`.gitignore`**
   - Added `celery_worker.log` to ignore list

## Benefits

✅ **Single command startup** - No need for multiple terminals
✅ **Automatic service management** - Redis and Celery start automatically
✅ **Graceful degradation** - Works even if Redis not installed
✅ **Clean shutdown** - Ctrl+C stops everything properly
✅ **Better DX** - Logs organized and easy to access

## Next Steps

1. Stop any running Flask/Celery processes
2. Run `./start_local.sh`
3. Navigate to http://localhost:8080
4. Test video generation (if Redis installed)
5. Check `celery_worker.log` for worker activity

---

**Status**: ✅ **ENHANCED** - Single script now manages all services!
