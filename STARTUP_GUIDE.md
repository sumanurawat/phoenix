# 🚀 Phoenix + SOHO - Local Development Startup Guide

**One script. Two servers. Zero hassle.**

---

## Quick Start

```bash
./start_local.sh
```

That's it! The script handles everything automatically.

---

## What Happens When You Run It

### The Beautiful Startup Process

```
╔════════════════════════════════════════════════════════════╗
║           🚀 PHOENIX AI PLATFORM + SOHO 🎨                ║
║              Starting Full Stack Application...            ║
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
✅ Celery worker started (PID: 12345)
   📝 Worker logs: celery_worker.log
   📝 Tail logs: tail -f celery_worker.log

[6/8] Preparing frontend applications...
  ✅ Reel Maker built (served at /reel-maker)
  ✅ SOHO frontend ready (will run on port 5173)

[7/8] Starting Backend API Server...
✅ Flask will start on port 8080

[8/8] Starting SOHO Frontend Dev Server...
✅ Vite will start on port 5173

╔════════════════════════════════════════════════════════════╗
║                  🎉 STARTUP COMPLETE! 🎉                  ║
╚════════════════════════════════════════════════════════════╝
```

---

## 📍 URLs to Open

### 🚀 **SOHO Frontend (NEW UI)**
```
➜ http://localhost:5173
```
**What it is:** The brand new React + Vite frontend with hot reload
**What you see:** Modern dark-themed social media interface
**Technologies:** React 18, TypeScript, Tailwind CSS, Vite

### 🔧 **Backend API**
```
➜ http://localhost:8080
```
**What it is:** Flask backend serving all APIs
**What you see:** API responses, legacy templates
**Technologies:** Flask, Python, Firebase, Celery

### 🎬 **Reel Maker (Legacy)**
```
➜ http://localhost:8080/reel-maker
```
**What it is:** Existing video generation interface
**What you see:** Original reel maker UI
**Technologies:** React (bundled), served by Flask

---

## 📊 Services Running

| Service | Port | Purpose | Logs |
|---------|------|---------|------|
| **Backend API** | 8080 | Flask + APIs | Terminal output |
| **SOHO Frontend** | 5173 | Vite dev server | `soho_frontend.log` |
| **Redis** | 6379 | Task queue | `redis-server` |
| **Celery Worker** | Background | Video generation | `celery_worker.log` |

---

## 📝 Viewing Logs

### Backend Logs
Visible directly in the terminal where you ran `start_local.sh`

### Frontend Logs
```bash
tail -f soho_frontend.log
```

### Celery Worker Logs
```bash
tail -f celery_worker.log
```

### All Logs at Once (separate terminal)
```bash
# Terminal 1: Backend
./start_local.sh

# Terminal 2: Frontend logs
tail -f soho_frontend.log

# Terminal 3: Worker logs
tail -f celery_worker.log
```

---

## 🛑 Stopping Everything

**Just press `Ctrl+C` in the terminal running the script.**

The script automatically cleans up:
- ✅ Celery worker processes
- ✅ Frontend dev server
- ✅ Port 8080 (backend)
- ✅ Port 5173 (frontend)

---

## 🔧 Troubleshooting

### Port Already in Use

The script automatically kills processes on ports 8080 and 5173.

If you still see issues:
```bash
# Manually kill port 8080
lsof -ti tcp:8080 | xargs kill -9

# Manually kill port 5173
lsof -ti tcp:5173 | xargs kill -9
```

### Redis Not Running

Install Redis:
```bash
brew install redis
```

Start Redis:
```bash
redis-server --daemonize yes
```

Check Redis:
```bash
redis-cli ping
# Should return: PONG
```

### Frontend Not Building

Install dependencies manually:
```bash
cd frontend/soho
npm install
npm run dev
```

### Python Environment Issues

Create and activate venv:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🎯 Development Workflow

### 1. Start Everything
```bash
./start_local.sh
```

### 2. Open SOHO Frontend
```
http://localhost:5173
```

### 3. Make Changes
- **Frontend:** Edit files in `frontend/soho/src/` - Hot reload is automatic
- **Backend:** Edit files in `api/`, `services/` - Flask auto-reloads

### 4. Test
- Frontend changes: Instant in browser (Vite HMR)
- Backend changes: Save file, Flask reloads

### 5. Check Logs
- Backend: Terminal output
- Frontend: `tail -f soho_frontend.log`
- Worker: `tail -f celery_worker.log`

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR BROWSER                         │
│                                                         │
│  http://localhost:5173 (SOHO Frontend - React/Vite)    │
│           ↓                                             │
│           ↓ API Calls                                   │
│           ↓                                             │
│  http://localhost:8080 (Backend - Flask)                │
│           ↓                                             │
│           ↓ Queue Tasks                                 │
│           ↓                                             │
│  Redis (Port 6379) → Celery Worker → AI Generation     │
└─────────────────────────────────────────────────────────┘
```

**Flow:**
1. User interacts with SOHO frontend (React)
2. Frontend calls backend API (Flask)
3. Backend queues async tasks (Redis + Celery)
4. Celery worker processes AI generation
5. Results stored in Firestore
6. Frontend polls/updates UI

---

## 📦 What Gets Built

### Reel Maker (Legacy)
- **Source:** `frontend/reel-maker/`
- **Build:** `frontend/reel-maker/dist/`
- **Served:** Flask copies to `static/reel_maker/`
- **Access:** `http://localhost:8080/reel-maker`

### SOHO (New)
- **Source:** `frontend/soho/src/`
- **Dev Server:** Vite on port 5173
- **Build:** `frontend/soho/dist/` (for production)
- **Access:** `http://localhost:5173` (dev)

---

## 🚀 Production Deployment

### Build for Production

```bash
# Build SOHO frontend
cd frontend/soho
npm run build

# Build Reel Maker
cd ../reel-maker
npm run build
```

### Configure Flask to Serve SOHO

Option 1: Serve from Flask (like Reel Maker)
Option 2: Deploy frontend separately (Vercel, Netlify)
Option 3: Use Cloud Run with both containers

---

## 🎨 SOHO Frontend Features

When you open `http://localhost:5173`:

- ✅ Modern dark-themed UI
- ✅ Instant hot reload
- ✅ TypeScript support
- ✅ Tailwind CSS styling
- ✅ React Router navigation
- ✅ API integration ready
- ✅ Token balance widget
- ✅ User authentication flow
- ✅ Explore feed
- ✅ Profile pages
- ✅ Creation modal

---

## 🔐 Environment Variables

### Backend (.env in root)
```bash
# Firebase
GOOGLE_APPLICATION_CREDENTIALS=...

# API Keys
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...

# Stripe
STRIPE_API_KEY=...
STRIPE_WEBHOOK_SECRET=...

# Redis
REDIS_URL=redis://localhost:6379
```

### Frontend (frontend/soho/.env)
```bash
VITE_API_BASE_URL=http://localhost:8080
VITE_APP_NAME=SOHO
VITE_ENV=development
```

---

## 📚 Next Steps

1. **Start the app:** `./start_local.sh`
2. **Open SOHO:** `http://localhost:5173`
3. **Build components:** Follow `docs/SOHO_UI_IMPLEMENTATION_PLAN.md`
4. **Test features:** Create, explore, profile pages
5. **Deploy:** Build and deploy to production

---

## 💡 Pro Tips

### Hot Reload
- Frontend changes: Instant (Vite HMR)
- Backend changes: Auto-reload (Flask debug mode)
- Don't restart script unless needed

### Multiple Terminals
```bash
# Terminal 1: Main app
./start_local.sh

# Terminal 2: Frontend logs
tail -f soho_frontend.log

# Terminal 3: Git operations
git status
git commit -m "..."
```

### Quick Restart
```bash
# Stop with Ctrl+C
# Start again
./start_local.sh
```

### Clean Start
```bash
# Kill everything manually
pkill -f celery
pkill -f flask
pkill -f vite
redis-cli shutdown

# Start fresh
./start_local.sh
```

---

## 🎉 Success Indicators

You know everything is working when:

- ✅ No red error messages in startup
- ✅ All checkmarks are green
- ✅ `http://localhost:5173` loads (SOHO)
- ✅ `http://localhost:8080` returns API responses
- ✅ No `EADDRINUSE` port errors
- ✅ Redis pings successfully
- ✅ Celery worker shows "ready"

---

## 🐛 Common Issues

### Issue: `Port 8080 already in use`
**Solution:** Script auto-kills it. If not, manually: `lsof -ti tcp:8080 | xargs kill -9`

### Issue: `npm not found`
**Solution:** Install Node.js from https://nodejs.org

### Issue: `Redis connection refused`
**Solution:** `brew install redis && redis-server --daemonize yes`

### Issue: `Module not found` in frontend
**Solution:** `cd frontend/soho && npm install`

### Issue: `Python module not found`
**Solution:** `source venv/bin/activate && pip install -r requirements.txt`

---

## 📞 Support

- **Documentation:** `docs/` folder
- **Design System:** `docs/SOHO_UI_DESIGN_PHILOSOPHY.md`
- **Implementation Plan:** `docs/SOHO_UI_IMPLEMENTATION_PLAN.md`
- **API Docs:** Check `api/` folder
- **GitHub Issues:** Create an issue for bugs

---

**Built with ❤️ by the Phoenix team**

*Making AI social, one pixel at a time.* 🎨
