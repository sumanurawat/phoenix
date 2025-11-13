# SOHO Architecture & Production Deployment

## Overview
SOHO is a React-based frontend that communicates with the Phoenix Flask backend via API calls. This document explains the architecture, authentication flow, and production deployment strategy.

---

## Development Architecture

### Current Setup (localhost)
```
┌─────────────────────┐         ┌──────────────────────┐
│   React Frontend    │         │   Flask Backend      │
│   localhost:5173    │ ◄────► │   localhost:8080     │
│   (Vite Dev Server) │  API    │   (Session + API)    │
└─────────────────────┘         └──────────────────────┘
```

**Key Points:**
- React app runs on port 5173 (Vite dev server)
- Flask backend runs on port 8080
- CORS enabled with `withCredentials: true`
- Session cookies work across localhost ports

---

## Production Architecture (Recommended)

### Option 1: Separate Domains with CDN
```
┌─────────────────────────────────────┐
│         soho.com (Frontend)         │
│    Static files on Cloud Storage    │
│         + CDN (optional)            │
└────────────┬────────────────────────┘
             │ API calls
             ▼
┌─────────────────────────────────────┐
│     api.soho.com (Backend)          │
│    Flask on Cloud Run               │
│    Session-based authentication     │
└─────────────────────────────────────┘
```

**Pros:**
- Clean separation of concerns
- Frontend can be served from CDN (fast global delivery)
- Backend can scale independently
- Professional architecture

**Cons:**
- Requires 2 domains
- CORS configuration needed
- Cookie domain must be set to `.soho.com`
- More complex setup

**Cost:** ~$52/month ($50 Cloud Run + ~$2 DNS/Storage)

---

### Option 2: Same Domain with Path Routing (CURRENT IMPLEMENTATION)
```
┌────────────────────────────────────────────┐
│          soho.com (All traffic)            │
│        Flask on Cloud Run                  │
│                                            │
│  /          → React app (index.html)       │
│  /login     → React app (index.html)       │
│  /signup    → React app (index.html)       │
│  /explore   → React app (index.html)       │
│  /api/*     → Flask API routes             │
│  /static/*  → React static assets          │
└────────────────────────────────────────────┘
```

**How it works:**
1. React app built to `static/soho/` directory
2. Flask serves `index.html` for all non-API routes
3. React Router handles client-side routing
4. API calls go to same domain (no CORS needed)
5. Session cookies work seamlessly

**Pros:**
- Single domain (simpler)
- No CORS issues
- Session cookies "just work"
- Cheaper (single Cloud Run instance)
- Easier deployment

**Cons:**
- Flask serves both app and API
- Can't use CDN for frontend (unless configured carefully)
- All traffic goes through Flask

**Cost:** ~$50/month (single Cloud Run instance)

---

## Authentication Flow

### Login/Signup Flow (React → Flask → React)

```
1. User visits http://localhost:5173/
   └─> React landing page renders

2. User clicks "Sign In"
   └─> Navigate to /login (React route)
   └─> LoginPage component renders

3. User enters email/password
   └─> React fetches CSRF token from /api/csrf-token
   └─> React POSTs to Flask /login with credentials
   └─> Flask creates session cookie
   └─> Flask returns success

4. React does full page reload (window.location.href)
   └─> Session cookie now set in browser
   └─> useAuth hook fetches /api/users/me
   └─> User data loads successfully
   └─> User sees authenticated UI
```

**Key Technical Details:**
- Session cookie: `session=<encrypted_data>; HttpOnly; SameSite=Lax`
- CSRF protection: Token fetched before form submit
- Full page reload: Required to establish session properly
- `withCredentials: true`: Required for cross-origin cookies (dev only)

---

## API Communication

### Frontend Configuration
```typescript
// api.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // CRITICAL: Sends cookies with requests
});
```

### Backend CORS Configuration (Development Only)
```python
# app.py
CORS(app, 
     origins=['http://localhost:5173', 'http://localhost:5174'],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'])
```

**Production:** CORS not needed if using same domain (Option 2)

---

## File Structure

```
phoenix/
├── frontend/soho/              # React application
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx    # Public homepage
│   │   │   ├── LoginPage.tsx      # ✅ React login form
│   │   │   ├── SignupPage.tsx     # ✅ React signup form
│   │   │   ├── ExplorePage.tsx    # Browse creations
│   │   │   ├── CreatePage.tsx     # Generate images/videos
│   │   │   ├── ProfilePage.tsx    # User profiles
│   │   │   └── ...
│   │   ├── components/
│   │   │   └── layout/
│   │   │       └── Header.tsx     # Main navigation + logout
│   │   ├── hooks/
│   │   │   └── useAuth.ts         # Auth state management
│   │   ├── api.ts                 # Axios configuration
│   │   └── App.tsx                # Route definitions
│   └── package.json
│
├── api/                        # Flask API routes
│   ├── auth_routes.py         # /login, /signup, /logout
│   ├── user_routes.py         # /api/users/me, etc.
│   ├── token_routes.py        # Token balance, purchases
│   └── ...
│
├── templates/                  # Flask HTML templates (legacy)
│   ├── login.html             # ⚠️ Old Flask login (not used in React)
│   └── signup.html            # ⚠️ Old Flask signup (not used in React)
│
└── app.py                      # Flask application entry point
```

---

## Deployment Steps

### Development
```bash
# Terminal 1: Start Flask backend
source venv/bin/activate
python app.py
# Running on http://localhost:8080

# Terminal 2: Start React frontend
cd frontend/soho
npm run dev
# Running on http://localhost:5173
```

### Production (Option 2: Same Domain)

#### Step 1: Build React App
```bash
cd frontend/soho
npm run build
# Output: dist/ directory with optimized files
```

#### Step 2: Copy Build to Flask Static Directory
```bash
mkdir -p static/soho
cp -r dist/* static/soho/
```

#### Step 3: Configure Flask to Serve React App
```python
# app.py
@app.route('/')
@app.route('/login')
@app.route('/signup')
@app.route('/explore')
@app.route('/create')
@app.route('/profile/<username>')
def serve_soho(*args, **kwargs):
    """Serve React app for all non-API routes"""
    return send_from_directory('static/soho', 'index.html')
```

#### Step 4: Deploy to Cloud Run
```bash
gcloud builds submit --config cloudbuild.yaml
# Deploys to: https://phoenix-ai-dev-123456.run.app
```

#### Step 5: Configure Domain
```bash
# Map custom domain
gcloud run domain-mappings create --service phoenix-ai --domain soho.com
```

**Result:** 
- Frontend: `https://soho.com/`
- API: `https://soho.com/api/*`
- Single domain, no CORS issues, session cookies work perfectly

---

## Environment Variables

### Development (.env)
```bash
# React (frontend/soho/.env)
VITE_API_BASE_URL=http://localhost:8080

# Flask (phoenix/.env)
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key
FIREBASE_API_KEY=...
GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials.json
```

### Production (Cloud Run)
```bash
# Environment secrets set in Cloud Run console
SECRET_KEY=<random-secret>
FIREBASE_API_KEY=<from-firebase-console>
GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json
```

**React production build:**
- `VITE_API_BASE_URL` not needed (same domain)
- All API calls use relative paths: `/api/*`

---

## Session Management

### How Sessions Work
```
1. User logs in → Flask creates session
   └─> session['user_id'] = 'abc123'
   └─> session['user_email'] = 'user@example.com'

2. Flask encrypts session data
   └─> Uses SECRET_KEY to sign cookie
   └─> Cookie: session=<encrypted_payload>

3. Browser stores cookie
   └─> HttpOnly: JavaScript can't access
   └─> SameSite=Lax: CSRF protection
   └─> Secure: HTTPS only (production)

4. Subsequent requests include cookie
   └─> Flask decrypts and validates
   └─> User data available in session dict
```

### Session Storage (Production)
```python
# Current: Filesystem sessions (single instance only)
app.config['SESSION_FILE_DIR'] = './flask_session/'

# For multi-instance: Use Redis
# app.config['SESSION_TYPE'] = 'redis'
# app.config['SESSION_REDIS'] = redis.from_url('redis://...')
```

**Note:** With `max-instances=1` in Cloud Run, filesystem sessions work fine. For scaling, switch to Redis.

---

## Security Considerations

### CSRF Protection
- Token fetched before form submission
- Validated on server side
- Prevents cross-site request forgery

### Session Security
- HttpOnly cookies (not accessible via JavaScript)
- Secure flag in production (HTTPS only)
- SameSite=Lax (prevents CSRF)
- SECRET_KEY must be strong and secret

### CORS (Development Only)
```python
# Restrict origins in production
CORS(app, 
     origins=['https://soho.com'],  # Only your domain
     supports_credentials=True)
```

---

## Troubleshooting

### Issue: 401 Unauthorized after login
**Cause:** Session cookie not being sent with requests
**Fix:** Ensure `withCredentials: true` in axios config

### Issue: CORS errors in development
**Cause:** Backend not allowing localhost:5173
**Fix:** Add origin to CORS config in `app.py`

### Issue: Session expires immediately
**Cause:** SECRET_KEY changed or cookies not persisting
**Fix:** Check SECRET_KEY is consistent, cookies are HttpOnly

### Issue: Redirect loops between ports
**Cause:** Mixed Flask templates and React routes
**Fix:** Use React pages for all auth flows (LoginPage, SignupPage)

---

## Future Enhancements

### Phase 1 (Current): React Auth ✅
- ✅ React-based login/signup pages
- ✅ No port jumping
- ✅ Session-based authentication
- ✅ Proper error handling

### Phase 2: Production Deployment
- [ ] Build React app to static/soho/
- [ ] Configure Flask catchall routes
- [ ] Deploy to Cloud Run with custom domain
- [ ] Test full authentication flow

### Phase 3: Optimization
- [ ] Add Redis for session storage
- [ ] Enable Cloud Run autoscaling (remove max-instances=1)
- [ ] Add CDN for static assets
- [ ] Implement refresh tokens

### Phase 4: Advanced Features
- [ ] OAuth (Google login in React)
- [ ] Password reset flow
- [ ] Email verification
- [ ] Two-factor authentication

---

## Summary

**Current State:**
- ✅ React-based login/signup (no port jumping)
- ✅ Session authentication working
- ✅ Clean separation of concerns
- ✅ Production-ready architecture designed

**Production Strategy:**
- **Recommended:** Option 2 (Same domain with path routing)
- **Cost:** $50/month (Cloud Run only)
- **Complexity:** Low (single deployment)
- **Performance:** Good (consider CDN later)

**Next Steps:**
1. Test full login/signup flow in development
2. Build React app and integrate with Flask
3. Deploy to Cloud Run with custom domain
4. Monitor and optimize as needed
