# Momo Frontend Deployment Guide

## What Happens When You Push to GitHub

### Current Setup ✅
```
GitHub (main branch)
    ↓ webhook
Cloud Build
    ↓ builds & deploys
Cloud Run (Single Service)
    - URL: phoenix-234619602247.us-central1.run.app
```

### After This Update ✅
```
GitHub (main branch)
    ↓ webhook  
Cloud Build (SAME BUILD PIPELINE)
    ├─ Step 1: Build React Frontend (npm run build)
    ├─ Step 2: Copy dist/ to static/momo/
    ├─ Step 3: Build Flask Docker image (includes frontend)
    └─ Step 4: Deploy to Cloud Run
             ↓
Cloud Run (SAME SERVICE - No new server!)
    ├─ /api/*         → Flask API endpoints
    ├─ /momo/*        → React SPA (your new frontend)
    └─ /soho/*        → Old Flask templates (still works)
```

## Architecture: One Server, Two Frontends

### URL Structure
```
https://phoenix-234619602247.us-central1.run.app/
    ├─ /                    → Phoenix homepage
    ├─ /momo                → NEW React frontend (SPA)
    ├─ /momo/explore        → React handles routing
    ├─ /momo/profile/user   → React handles routing
    ├─ /api/feed/explore    → Flask API (used by React)
    ├─ /api/users/me        → Flask API (used by React)
    └─ /soho/explore        → Old Flask templates (backward compatible)
```

### How It Works

**Development (Local):**
```bash
# Terminal 1: Flask backend
python app.py  # http://localhost:8080

# Terminal 2: React frontend (with hot reload)
cd frontend/soho && npm run dev  # http://localhost:5173
```
- React dev server proxies API calls to Flask
- Hot reload works instantly
- CORS allows cross-origin requests

**Production (After Push):**
```bash
# Cloud Build automatically:
1. npm ci                        # Install Node dependencies (~20s)
2. npm run build                 # Build React to dist/ (~30s)
3. cp dist/* static/momo/        # Copy to Flask static folder (~1s)
4. docker build                  # Build Flask container (includes frontend) (~60s)
5. gcloud run deploy             # Deploy to Cloud Run (~30s)

# Total time: ~2-3 minutes (SAME as before)
```

## Security & Performance

### ✅ Security Benefits (Same Server)
- **No CORS issues**: Frontend and API on same domain
- **Session cookies work automatically**: No cross-origin cookie problems
- **Simple authentication**: Sessions persist naturally
- **One SSL certificate**: Cloud Run handles HTTPS
- **No exposed secrets**: All in Cloud Secret Manager

### ⚡ Performance
- **Frontend load**: Instant (static files)
- **API calls**: 100-200ms (local to server)
- **Cold start**: 1-2 seconds (unchanged)
- **Build time**: 2-3 minutes (unchanged)

### 💰 Cost
- **No additional cost**: Still one Cloud Run service
- **Free tier eligible**: Up to 2 million requests/month free
- **Storage**: Frontend files add ~500KB to Docker image (negligible)

## Development vs Production Workflow

### Development (Local Testing)
```bash
# Start both servers locally
./start_local.sh

# Or manually:
python app.py                    # Backend: http://localhost:8080
cd frontend/soho && npm run dev  # Frontend: http://localhost:5173

# Make changes:
- Edit React components → Hot reload in browser
- Edit Flask routes → Restart Flask server
- No build step needed
```

### Staging/Testing (Before Production)
```bash
# Build frontend locally to test production build
cd frontend/soho
npm run build

# Copy to Flask static folder
mkdir -p ../../static/momo
cp -r dist/* ../../static/momo/

# Test locally with production build
python app.py  # Visit http://localhost:8080/momo
```

### Production (Push to GitHub)
```bash
git add .
git commit -m "feat: add Momo React frontend"
git push origin main

# GitHub webhook triggers Cloud Build (automatically):
# 1. Builds frontend
# 2. Builds backend Docker image (includes frontend)
# 3. Deploys to Cloud Run
# 4. Done! ✅

# Visit: https://phoenix-234619602247.us-central1.run.app/momo
```

## What About Separate Servers? (Future Option)

If you later want **separate servers** (e.g., `friedmomo.com` for frontend):

### Benefits
- ✅ Scale frontend/backend independently
- ✅ Use CDN for frontend (faster globally)
- ✅ Deploy frontend without rebuilding Flask

### Costs
- ⚠️ Need to configure:
  - CORS headers (already done in `app.py`)
  - Cookie domain: `SESSION_COOKIE_DOMAIN = '.friedmomo.com'`
  - Two Cloud Build configs
  - Two domains/certificates
- ⚠️ More expensive: ~$5-10/month for second service + domain

### When to switch?
- When you have >1000 daily active users
- When frontend deploys 10+ times per day
- When you need global CDN performance

## Files Modified

### 1. `cloudbuild.yaml` (Updated)
**What changed:**
- Added frontend build steps **before** Docker build
- Copies `frontend/soho/dist/` → `static/momo/`
- No new build config needed!

**Build process:**
```yaml
Step 1: npm ci              # Install dependencies
Step 2: npm run build       # Build React
Step 3: cp dist/ static/    # Copy to Flask
Step 4: docker build        # Build Flask (includes frontend)
Step 5: gcloud run deploy   # Deploy to Cloud Run
```

### 2. `app.py` (Updated)
**What changed:**
- Added `/momo` route that serves React SPA
- Handles client-side routing (React Router)
- Falls back to `index.html` for all React routes

**Routes:**
```python
@app.route('/momo')
@app.route('/momo/<path:path>')
def serve_momo_frontend(path=''):
    # Serve React app or static files
    if path and os.path.exists(os.path.join('static/momo', path)):
        return send_from_directory('static/momo', path)
    return send_from_directory('static/momo', 'index.html')
```

### 3. `frontend/soho/.env` (Already updated)
**Current config:**
```bash
VITE_API_BASE_URL=http://localhost:8080  # Local dev
# Production uses relative URLs (same domain)
```

## Testing Checklist

### Before Pushing
- [ ] Frontend builds successfully: `cd frontend/soho && npm run build`
- [ ] No TypeScript errors: `npm run build` (shows errors)
- [ ] Local backend runs: `python app.py`
- [ ] API endpoints work: Test `/api/users/me`, `/api/feed/explore`

### After Pushing
- [ ] Cloud Build succeeds (check GitHub Actions or Cloud Console)
- [ ] Visit: `https://phoenix-234619602247.us-central1.run.app/momo`
- [ ] React app loads
- [ ] Login works
- [ ] API calls work (check Network tab)
- [ ] Navigation works (React Router)

## Rollback Plan

If something breaks:

### Option 1: Quick Rollback
```bash
git revert HEAD
git push origin main
# Cloud Build redeploys previous version
```

### Option 2: Disable Frontend Route
```python
# In app.py, comment out:
# @app.route('/momo')
# @app.route('/momo/<path:path>')
# def serve_momo_frontend(path=''):
#     ...

# Old routes still work: /soho/explore
```

### Option 3: Rebuild Without Frontend
```bash
# Manually remove frontend build steps from cloudbuild.yaml
# Push to trigger rebuild
```

## FAQ

### Q: Will this affect my existing Flask routes?
**A:** No! Your old routes (`/soho/*`, `/api/*`, `/`) still work exactly the same.

### Q: Do I need to change my domain?
**A:** No! Everything runs on the same Cloud Run URL. You can add `friedmomo.com` later.

### Q: What if the build fails?
**A:** Cloud Build shows detailed logs. Most common issues:
- TypeScript errors → Fix in code
- Missing npm dependencies → Update `package.json`
- Build timeout → Increase Cloud Build timeout (default: 10 minutes)

### Q: Can I test the build locally first?
**A:** Yes! Run:
```bash
cd frontend/soho
npm run build
# Check dist/ folder for errors
```

### Q: How do I see build logs?
**A:** 
- GitHub: Actions tab → Latest workflow run
- GCP Console: Cloud Build → History → Latest build

### Q: What's the cost?
**A:** Same as before! Frontend adds:
- ~20-30s to build time
- ~500KB to Docker image
- $0 in Cloud Run costs (same service)

## Next Steps

### Immediate (After This Push)
1. ✅ Push changes to GitHub
2. ✅ Wait for Cloud Build (~2-3 minutes)
3. ✅ Test at `/momo` route
4. ✅ Verify API calls work
5. ✅ Check authentication

### Soon (If Needed)
- [ ] Add frontend environment variables to Cloud Build
- [ ] Set up custom domain (`friedmomo.com`)
- [ ] Add CDN/caching headers for static files
- [ ] Set up monitoring/analytics

### Later (Scale Phase)
- [ ] Separate frontend/backend servers (if needed)
- [ ] Add CI/CD for frontend-only deploys
- [ ] Set up staging environment
- [ ] Add end-to-end tests

---

**Summary:** You're adding the frontend to your existing build pipeline. **No new server**, **no new costs**, **same deployment process**. Just faster, modern React UI served alongside your Flask backend! 🚀
