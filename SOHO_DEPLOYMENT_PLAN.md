# SOHO Frontend Deployment Plan

**Date:** November 11, 2025  
**Status:** Planning Phase  
**Goal:** Deploy React frontend with separate domain (soho.com) pointing to new UI

---

## Current Architecture

### Development Setup
```
Frontend (React + Vite):  http://localhost:5173
Backend (Flask):          http://localhost:8080
```

- React app serves from Vite dev server (port 5173)
- Backend API on Flask dev server (port 8080)
- CORS configured for cross-origin requests
- Session cookies shared via `withCredentials: true`

### Old SOHO (Flask Templates)
- Routes: `/soho`, `/soho/explore`, `/soho/<username>`
- Templates in `templates/` directory
- **Status:** Will be replaced by React frontend

---

## Production Deployment Strategy

### Option 1: Separate Domain (Recommended) ✅

**Domain Structure:**
```
soho.com               → React Frontend (SOHO)
api.soho.com           → Flask Backend
(or backend.soho.com)
```

**Architecture:**
```
┌─────────────────────────────────────────┐
│         User Browser                     │
└────────────┬────────────────────────────┘
             │
             ├─→ soho.com (React App)
             │   • Static files (HTML, JS, CSS)
             │   • Client-side routing (React Router)
             │   • Hosted on: Cloud Storage + CDN
             │
             └─→ api.soho.com (Flask API)
                 • REST endpoints (/api/*)
                 • Authentication (/login, /logout)
                 • Hosted on: Cloud Run
```

**Pros:**
- Clean separation of concerns
- Independent scaling (frontend CDN vs backend containers)
- Professional setup (industry standard)
- Easy to add more frontends later
- CDN for fast global delivery

**Implementation Steps:**

1. **Build React App for Production**
   ```bash
   cd frontend/soho
   npm run build
   # Output: dist/ directory with static files
   ```

2. **Deploy Frontend to Cloud Storage + CDN**
   ```bash
   # Upload to Google Cloud Storage bucket
   gsutil -m cp -r dist/* gs://soho-frontend-bucket/
   
   # Configure bucket for static hosting
   gsutil web set -m index.html -e index.html gs://soho-frontend-bucket
   
   # Set up Cloud CDN (or use Firebase Hosting)
   # Point soho.com → Cloud Storage bucket
   ```

3. **Update Backend for CORS**
   ```python
   # In app.py
   CORS(app, origins=[
       'https://soho.com',
       'https://www.soho.com',
       'http://localhost:5173'  # Keep for dev
   ], supports_credentials=True)
   ```

4. **Deploy Backend to Cloud Run**
   ```bash
   # Backend stays on Cloud Run as is
   gcloud run deploy phoenix-backend \
     --image gcr.io/phoenix-ai/phoenix:latest \
     --platform managed \
     --region us-central1
   
   # Map custom domain: api.soho.com → Cloud Run service
   ```

5. **Update React Environment Variables**
   ```env
   # .env.production
   VITE_API_BASE_URL=https://api.soho.com
   ```

6. **DNS Configuration**
   ```
   soho.com          A/CNAME → Cloud Storage/CDN
   www.soho.com      A/CNAME → Cloud Storage/CDN
   api.soho.com      A/CNAME → Cloud Run backend
   ```

---

### Option 2: Same Domain, Different Paths

**URL Structure:**
```
phoenix.ai/             → Main Phoenix platform (Flask)
phoenix.ai/soho         → React Frontend (SOHO)
phoenix.ai/api/*        → Backend API
```

**Architecture:**
```
┌────────────────────────────────────────┐
│         Cloud Run Container             │
├────────────────────────────────────────┤
│  Flask App (Reverse Proxy)             │
│  ├─ /          → Main Platform         │
│  ├─ /soho/*    → React Static Files    │
│  └─ /api/*     → API Endpoints         │
└────────────────────────────────────────┘
```

**Implementation Steps:**

1. **Build React App**
   ```bash
   cd frontend/soho
   npm run build
   # Output: dist/
   ```

2. **Configure Flask to Serve React**
   ```python
   # In app.py
   from flask import send_from_directory
   
   # Serve React static files
   @app.route('/soho')
   @app.route('/soho/<path:path>')
   def serve_soho(path=''):
       """Serve React frontend for SOHO."""
       if path and os.path.exists(os.path.join('frontend/soho/dist', path)):
           return send_from_directory('frontend/soho/dist', path)
       return send_from_directory('frontend/soho/dist', 'index.html')
   ```

3. **Update React Router Base**
   ```tsx
   // In App.tsx
   <BrowserRouter basename="/soho">
     <Routes>
       <Route path="/" element={<LandingPage />} />
       {/* ... */}
     </Routes>
   </BrowserRouter>
   ```

4. **Update API Endpoints**
   ```typescript
   // No change needed - relative URLs work fine
   const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
   ```

**Pros:**
- No need for separate domain (saves cost)
- Simpler deployment (single container)
- Session cookies work automatically (same domain)

**Cons:**
- Backend handles static file serving (less efficient than CDN)
- Harder to scale frontend independently
- Less clean separation

---

## Recommended Approach: Separate Domain (Option 1)

### Phase 1: Immediate Setup (Current Domain)
```
phoenix-ai.com/soho → React frontend (temporary)
```
- Use Option 2 initially to test
- No new domain purchase needed
- Quick deployment to validate

### Phase 2: Custom Domain (After Purchase)
```
soho.com → React frontend
api.soho.com → Backend
```
- Purchase soho.com domain
- Migrate to Option 1 architecture
- Professional setup for launch

---

## Updated Main Phoenix Index Page

### Add SOHO Link
```html
<!-- In templates/index.html -->
<div class="apps-section">
  <h2>Phoenix Applications</h2>
  
  <a href="/soho" class="app-card">
    <h3>SOHO - Social Media Platform</h3>
    <p>AI-powered creative community</p>
  </a>
  
  <!-- Other apps... -->
</div>
```

### Or Redirect Completely
```python
# In app.py
@app.route('/')
def index():
    """Main landing page."""
    # Check if user wants SOHO (could be query param or subdomain)
    if request.args.get('app') == 'soho':
        return redirect('/soho')
    
    # Default Phoenix platform
    return render_template('index.html', title='Phoenix AI Platform')
```

---

## Logout Redirect Configuration

### Development
```python
# Detects localhost:5173 and redirects there
if 'localhost:5173' in referer:
    return redirect('http://localhost:5173/')
```

### Production (Same Domain)
```python
# Redirects to /soho
return redirect('/soho')
```

### Production (Separate Domain)
```python
# Redirects to soho.com
return redirect('https://soho.com/')
```

---

## Build & Deploy Commands

### Frontend Build
```bash
cd frontend/soho
npm run build
# Output: dist/ directory
```

### Backend Deploy (Cloud Run)
```bash
# Already configured in cloudbuild.yaml
gcloud builds submit --config cloudbuild.yaml
```

### Frontend Deploy (Separate Domain)
```bash
# Option A: Google Cloud Storage
gsutil -m cp -r frontend/soho/dist/* gs://soho-frontend/

# Option B: Firebase Hosting
firebase deploy --only hosting:soho

# Option C: Netlify/Vercel (easiest)
cd frontend/soho
netlify deploy --prod
```

---

## Environment Variables

### Development (.env.local)
```env
VITE_API_BASE_URL=http://localhost:8080
```

### Production (.env.production)
```env
# Option 1: Separate domain
VITE_API_BASE_URL=https://api.soho.com

# Option 2: Same domain
VITE_API_BASE_URL=https://phoenix-ai.com
```

---

## Session & Cookie Configuration

### Development
```python
# app.py
app.config['SESSION_COOKIE_DOMAIN'] = 'localhost'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

### Production (Same Domain)
```python
app.config['SESSION_COOKIE_DOMAIN'] = '.phoenix-ai.com'  # Note the dot
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
```

### Production (Separate Domain)
```python
app.config['SESSION_COOKIE_DOMAIN'] = '.soho.com'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Cross-site
app.config['SESSION_COOKIE_SECURE'] = True  # Required for SameSite=None
```

---

## Migration Checklist

### Before Deployment
- [ ] Build React app for production
- [ ] Test build locally (`npm run preview`)
- [ ] Update API base URL for production
- [ ] Configure CORS for production domain
- [ ] Test logout flow
- [ ] Test all protected routes

### Deployment
- [ ] Deploy backend first (no breaking changes)
- [ ] Deploy frontend
- [ ] Update DNS records
- [ ] Test on production URL
- [ ] Monitor logs for errors

### After Deployment
- [ ] Update main Phoenix index page with SOHO link
- [ ] Redirect old `/soho` Flask routes to new frontend
- [ ] Remove old Flask templates (optional)
- [ ] Set up CDN for frontend (performance)
- [ ] Configure SSL certificates

---

## Cost Considerations

### Option 1: Separate Domain
- **Domain**: ~$12/year (soho.com)
- **Cloud Storage**: ~$0.026/GB/month
- **Cloud CDN**: ~$0.08/GB (data transfer)
- **Cloud Run Backend**: ~$50/month (existing)
- **Total**: ~$52/month + domain

### Option 2: Same Domain
- **Cloud Run Only**: ~$50/month (existing)
- **No additional cost** for serving static files
- **Total**: ~$50/month

---

## Recommendation

**Start with Option 2** (same domain) for immediate launch:
1. Build and test with `/soho` path
2. Deploy to existing Cloud Run
3. Validate everything works

**Migrate to Option 1** when ready:
1. Purchase soho.com domain
2. Set up Cloud Storage + CDN
3. Update DNS and environment variables
4. Professional, scalable setup

This gives you flexibility to launch quickly and migrate to a better architecture when you have the domain!
