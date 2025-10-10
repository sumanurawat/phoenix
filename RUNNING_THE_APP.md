# Running Phoenix AI Platform

## 🚀 Quick Start (Production Mode)

### Single Command - Builds Everything
```bash
./start_local.sh
```

This script automatically:
1. ✅ Activates virtual environment (or creates if missing)
2. ✅ Cleans up port 8080 if in use
3. ✅ Installs frontend dependencies (first run only)
4. ✅ **Builds React frontend** (Vite → static assets)
5. ✅ Starts Flask backend on port 8080

**Result**: Complete working application at http://localhost:8080

### What Gets Built
- **Frontend**: React app compiled to `static/reel_maker/assets/`
- **Backend**: Flask serves both static files and API endpoints

## ⚡ Development Mode (Hot Reload)

### For Active Frontend Development
```bash
./start_dev_mode.sh
```

This script runs:
1. ✅ Vite dev server on port 5173 (hot-reload for React)
2. ✅ Flask backend on port 8080 (auto-restart on Python changes)
3. ✅ Both servers run concurrently

**Use this when**:
- Making frequent changes to React components
- Want instant visual feedback without rebuilding
- Developing new UI features

**Note**: In dev mode, Vite proxies API calls to Flask automatically.

## 📊 Comparison

| Feature | `start_local.sh` | `start_dev_mode.sh` |
|---------|------------------|---------------------|
| **Frontend** | Built once (static) | Dev server (hot-reload) |
| **Backend** | Flask on :8080 | Flask on :8080 |
| **React Changes** | Requires rebuild | Instant updates |
| **Python Changes** | Auto-restart | Auto-restart |
| **Use Case** | Testing, production-like | Active development |
| **Speed** | Fast startup | Slower initial build |
| **Ports** | :8080 only | :5173 + :8080 |

## 🎯 Recommended Workflow

### For Most Testing/Usage
```bash
./start_local.sh
# Visit http://localhost:8080/reel-maker
```

### For Frontend Development
```bash
./start_dev_mode.sh
# Visit http://localhost:5173 (Vite dev server)
# Changes auto-reload on save
```

### For Backend Development
```bash
./start_local.sh
# Flask auto-restarts on Python file changes
# Frontend is pre-built and static
```

## 🔧 Manual Commands (Advanced)

### Build Frontend Only
```bash
cd frontend/reel-maker
npm install          # If first time
npm run build        # Outputs to ../../static/reel_maker/
cd ../..
```

### Run Backend Only (Frontend Pre-built)
```bash
source venv/bin/activate
python app.py
```

### Clean Install
```bash
# Remove all builds and dependencies
rm -rf frontend/reel-maker/node_modules
rm -rf static/reel_maker
rm -rf venv

# Start fresh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./start_local.sh
```

## 🐛 Troubleshooting

### "Port 8080 already in use"
**Script handles this automatically!** It kills the process before starting.

Manual fix:
```bash
lsof -ti tcp:8080 | xargs kill -9
```

### "Frontend not loading / old version showing"
```bash
cd frontend/reel-maker
npm run build
cd ../..
./start_local.sh
```

### "npm command not found"
Install Node.js (includes npm):
```bash
# macOS
brew install node

# Or download from nodejs.org
```

### "Virtual environment not found"
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📝 Environment Setup

### First Time Setup
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Install frontend dependencies and build
cd frontend/reel-maker
npm install
npm run build
cd ../..

# 5. Start the application
./start_local.sh
```

### Subsequent Runs
```bash
# Just run this - handles everything!
./start_local.sh
```

## 🎬 Reel Maker Specific

The Reel Maker feature requires:
1. ✅ Frontend built (automatic with `start_local.sh`)
2. ✅ Backend running
3. ✅ GCS bucket configured (`VIDEO_STORAGE_BUCKET` in `.env`)
4. ✅ Firebase authentication

Access at: http://localhost:8080/reel-maker

## 💡 Pro Tips

### 1. Fast Iteration (Frontend)
```bash
# Terminal 1: Keep dev server running
./start_dev_mode.sh

# Edit React files in frontend/reel-maker/src/
# Changes appear instantly at http://localhost:5173
```

### 2. Fast Iteration (Backend)
```bash
# Terminal 1: Keep Flask running
./start_local.sh

# Edit Python files in api/, services/, etc.
# Flask auto-restarts on save
# Frontend stays static (fast)
```

### 3. Full Production Build
```bash
# Build frontend
cd frontend/reel-maker && npm run build && cd ../..

# Start Flask (serves built assets)
./start_local.sh
```

### 4. Check What's Running
```bash
# See processes on port 8080
lsof -i :8080

# See processes on port 5173 (Vite dev server)
lsof -i :5173
```

## 🌐 URLs

### Production Mode (start_local.sh)
- Main app: http://localhost:8080
- Reel Maker: http://localhost:8080/reel-maker
- API: http://localhost:8080/api/*

### Dev Mode (start_dev_mode.sh)
- Frontend (Vite): http://localhost:5173
- Backend (Flask): http://localhost:8080
- API: http://localhost:8080/api/* (proxied from Vite)

## 🔒 Security Notes

- `.env` file is gitignored (contains secrets)
- `firebase-credentials.json` is gitignored
- Always use `.env.example` as template
- Never commit real API keys

## 📚 Related Documentation

- **Setup**: `REEL_MAKER_SETUP.md`
- **Quick Reference**: `REEL_MAKER_QUICK_REFERENCE.md`
- **Status**: `REEL_MAKER_STATUS.md`

---

**Quick Start**: Just run `./start_local.sh` - it does everything! 🚀
