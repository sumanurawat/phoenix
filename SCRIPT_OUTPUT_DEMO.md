# 🎬 Start Script Output Demo

## What You'll See When Running `./start_local.sh`

---

### Beautiful Startup Banner

```
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║           🚀 PHOENIX AI PLATFORM + SOHO 🎨                ║
║                                                            ║
║              Starting Full Stack Application...            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

[1/8] Checking environment configuration...
✅ Environment file found

[2/8] Setting up Python environment...
✅ Virtual environment already active

[3/8] Cleaning ports (8080 for Backend, 5173 for Frontend)...
✅ Port 8080 is available
✅ Port 5173 is available
✅ Session directory ready

[4/8] Checking Redis (required for video generation)...
✅ Redis already running (Port: 6379)

[5/8] Starting Celery worker for async video generation...
✅ Celery worker started (PID: 45623)
   📝 Worker logs: celery_worker.log
   📝 Tail logs: tail -f celery_worker.log

[6/8] Preparing frontend applications...
  📦 Building Reel Maker (legacy)...
  ✅ Reel Maker built (served at /reel-maker)
  🎨 Preparing SOHO frontend...
  ✅ SOHO frontend ready (will run on port 5173)

[7/8] Starting Backend API Server...
✅ Flask will start on port 8080

[8/8] Starting SOHO Frontend Dev Server...
✅ Vite will start on port 5173

╔════════════════════════════════════════════════════════════╗
║                                                            ║
║                  🎉 STARTUP COMPLETE! 🎉                  ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

📍 OPEN THESE URLS IN YOUR BROWSER:

  🚀 SOHO FRONTEND (NEW UI)
     ➜ http://localhost:5173
     (React + Vite dev server with hot reload)

  🔧 BACKEND API
     ➜ http://localhost:8080
     (Flask backend serving all APIs)

  🎬 REEL MAKER (LEGACY)
     ➜ http://localhost:8080/reel-maker
     (Existing video generation interface)

📊 SERVICES RUNNING:
  • Backend API:      Port 8080
  • SOHO Frontend:    Port 5173
  • Redis:            Port 6379
  • Celery Worker:    Background (logs: celery_worker.log)

📝 LOGS:
  • Celery logs:  tail -f celery_worker.log
  • Backend logs: Below this message
  • Frontend logs: Check Vite terminal output

🛑 TO STOP: Press Ctrl+C

═══════════════════════════════════════════════════════════

[FRONTEND] Starting SOHO dev server...
[FRONTEND] Started with PID: 45624

[BACKEND] Starting Flask API...

 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:8080
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 123-456-789
```

---

## When You Press Ctrl+C

```
^C
🛑 Shutting down services...
✅ Cleanup complete
```

---

## Color-Coded Output

### ✅ Green = Success
- Environment checks passed
- Servers started successfully
- Ports available

### ⚠️ Yellow = Warning
- Optional services not available
- Non-critical issues
- Suggestions for improvement

### ❌ Red = Error
- Critical failures
- Missing requirements
- Startup blocked

### 🔵 Blue = Info
- Process information
- Log file locations
- Helpful commands

### 🟣 Purple = Highlight
- URLs to open
- Important sections
- User actions needed

---

## Step-by-Step Breakdown

### Step 1: Environment Check
```
[1/8] Checking environment configuration...
✅ Environment file found
```
**What it does:** Verifies `.env` file exists

### Step 2: Python Setup
```
[2/8] Setting up Python environment...
✅ Virtual environment already active
```
**What it does:** Activates venv or reports if already active

### Step 3: Port Cleanup
```
[3/8] Cleaning ports (8080 for Backend, 5173 for Frontend)...
✅ Port 8080 is available
✅ Port 5173 is available
✅ Session directory ready
```
**What it does:**
- Kills processes on ports 8080 and 5173
- Creates Flask session directory

### Step 4: Redis Check
```
[4/8] Checking Redis (required for video generation)...
✅ Redis already running (Port: 6379)
```
**What it does:**
- Checks if Redis is running
- Starts Redis if needed
- Warns if not available

### Step 5: Celery Worker
```
[5/8] Starting Celery worker for async video generation...
✅ Celery worker started (PID: 45623)
   📝 Worker logs: celery_worker.log
   📝 Tail logs: tail -f celery_worker.log
```
**What it does:**
- Kills old Celery processes
- Starts new worker in background
- Redirects logs to file

### Step 6: Frontend Preparation
```
[6/8] Preparing frontend applications...
  📦 Building Reel Maker (legacy)...
  ✅ Reel Maker built (served at /reel-maker)
  🎨 Preparing SOHO frontend...
  ✅ SOHO frontend ready (will run on port 5173)
```
**What it does:**
- Builds Reel Maker bundle
- Installs SOHO dependencies if needed
- Prepares both frontends

### Step 7: Backend Start
```
[7/8] Starting Backend API Server...
✅ Flask will start on port 8080
```
**What it does:** Confirms Flask will start

### Step 8: Frontend Start
```
[8/8] Starting SOHO Frontend Dev Server...
✅ Vite will start on port 5173
```
**What it does:** Confirms Vite will start

---

## The "Go Now" Section

```
╔════════════════════════════════════════════════════════════╗
║                  🎉 STARTUP COMPLETE! 🎉                  ║
╚════════════════════════════════════════════════════════════╝

📍 OPEN THESE URLS IN YOUR BROWSER:
```

**This is your action list!** Copy these URLs:

1. `http://localhost:5173` - SOHO (new UI)
2. `http://localhost:8080` - Backend API
3. `http://localhost:8080/reel-maker` - Legacy UI

---

## Services Status

```
📊 SERVICES RUNNING:
  • Backend API:      Port 8080
  • SOHO Frontend:    Port 5173
  • Redis:            Port 6379
  • Celery Worker:    Background (logs: celery_worker.log)
```

**Quick reference:**
- Know what's running
- Know which ports
- Know where logs are

---

## Log Locations

```
📝 LOGS:
  • Celery logs:  tail -f celery_worker.log
  • Backend logs: Below this message
  • Frontend logs: Check Vite terminal output
```

**Copy-paste ready commands:**
```bash
tail -f celery_worker.log  # Watch Celery
tail -f soho_frontend.log  # Watch Vite
```

---

## Error Examples

### Port in Use (Auto-Fixed)
```
[3/8] Cleaning ports (8080 for Backend, 5173 for Frontend)...
  Port 8080 is in use. Killing processes...
✅ Port 8080 cleared
✅ Port 5173 is available
```

### Redis Not Installed
```
[4/8] Checking Redis (required for video generation)...
  ⚠️  Redis is not running. Starting Redis...
⚠️  Redis not installed. Video generation will use graceful fallback.
   To enable video generation, install Redis: brew install redis
   (Image generation and other features will work normally)
```

### Missing venv
```
[2/8] Setting up Python environment...
  Virtual environment not detected. Activating venv...
❌ ERROR: venv directory not found. Please create a virtual environment first:
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
```

---

## Real-World Example

### First Run (Clean Machine)

```bash
$ ./start_local.sh

╔════════════════════════════════════════════════════════════╗
║           🚀 PHOENIX AI PLATFORM + SOHO 🎨                ║
╚════════════════════════════════════════════════════════════╝

[1/8] Checking environment configuration...
✅ Environment file found

[2/8] Setting up Python environment...
  Virtual environment not detected. Activating venv...
✅ Virtual environment activated: /Users/you/phoenix/venv/bin/python

[3/8] Cleaning ports...
✅ Port 8080 is available
✅ Port 5173 is available
✅ Session directory ready

[4/8] Checking Redis...
  ⚠️  Redis is not running. Starting Redis...
✅ Redis started successfully (Port: 6379)

[5/8] Starting Celery worker...
✅ Celery worker started (PID: 1234)

[6/8] Preparing frontend applications...
     Installing dependencies... (first run)
  ✅ Reel Maker built
     Installing dependencies... (first run)
  ✅ SOHO frontend ready

[7/8] Starting Backend API Server...
✅ Flask will start on port 8080

[8/8] Starting SOHO Frontend Dev Server...
✅ Vite will start on port 5173

╔════════════════════════════════════════════════════════════╗
║                  🎉 STARTUP COMPLETE! 🎉                  ║
╚════════════════════════════════════════════════════════════╝

📍 OPEN THESE URLS IN YOUR BROWSER:
     ➜ http://localhost:5173  (SOHO)
     ➜ http://localhost:8080  (Backend)

[FRONTEND] Starting SOHO dev server...
[FRONTEND] Started with PID: 1235

[BACKEND] Starting Flask API...
 * Running on http://127.0.0.1:8080
```

**Total time:** ~30 seconds first run, ~5 seconds subsequent runs

---

## Why This Script is Awesome

### 1. **Single Command**
- No more "start backend, then frontend, then redis, then celery"
- Just `./start_local.sh`

### 2. **Beautiful Output**
- Color-coded messages
- Progress indicators
- Clear instructions

### 3. **Smart Cleanup**
- Kills old processes automatically
- Frees up ports
- No manual cleanup needed

### 4. **Helpful Information**
- Shows all URLs to open
- Lists all services and ports
- Tells you where logs are

### 5. **Error Handling**
- Detects missing dependencies
- Suggests fixes
- Continues when possible

### 6. **One Stop to Stop**
- Press Ctrl+C once
- Everything stops cleanly
- No orphaned processes

---

## Developer Experience

### Before This Script 😫

```bash
# Terminal 1
source venv/bin/activate
python app.py

# Terminal 2
cd frontend/soho
npm run dev

# Terminal 3
redis-server

# Terminal 4
celery -A celery_app worker ...

# Remember all the ports
# Remember all the URLs
# Kill everything manually
```

### After This Script 😎

```bash
# Terminal 1
./start_local.sh

# Done! Everything is running.
# URLs printed clearly.
# Ctrl+C to stop everything.
```

---

## Pro User Features

### Quick Check Health
Look for:
- ✅ All green checkmarks
- No red errors
- All 8 steps complete
- URLs printed

### Monitor Logs
```bash
# Separate terminal
tail -f celery_worker.log
tail -f soho_frontend.log
```

### Force Clean Start
```bash
# Kill everything first
pkill -f celery
pkill -f flask
pkill -f vite

# Start fresh
./start_local.sh
```

---

## The PM Will Love This Because...

1. ✅ **One command to rule them all**
2. ✅ **Crystal clear what's happening**
3. ✅ **Shows exactly which URLs to open**
4. ✅ **Lists all services and ports**
5. ✅ **Beautiful, professional output**
6. ✅ **Handles errors gracefully**
7. ✅ **Easy to debug** (clear log locations)
8. ✅ **Clean shutdown** (Ctrl+C)

---

**This is how professional development should feel.** 🚀
