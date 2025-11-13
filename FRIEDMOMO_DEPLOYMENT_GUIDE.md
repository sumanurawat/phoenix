# Friedmomo.com Deployment Guide

## 🎯 Goal
Deploy a fully functioning social media website (SOHO) at **www.friedmomo.com**

## 🏗️ Current Architecture

### Domain Strategy
- **friedmomo.com** → Your custom domain (purchased on Squarespace)
- **www.friedmomo.com** → Will redirect to friedmomo.com (standard practice)
- **friedmomo.web.app** → Temporary Firebase hosting URL (only for testing until DNS is configured)

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────┐
│                    USER VISITS                               │
│                 www.friedmomo.com                            │
│                      ↓                                       │
│              (DNS → Firebase Hosting)                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND (SOHO React App)                       │
│  Hosted on: Firebase Hosting (friedmomo site)               │
│  - Built with React + TypeScript + Vite                     │
│  - Tailwind CSS for styling                                 │
│  - SPA with client-side routing                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    API Calls to Backend
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              BACKEND (Phoenix Flask API)                     │
│  Hosted on: Google Cloud Run                                │
│  URL: phoenix-234619602247.us-central1.run.app              │
│  - Flask REST API                                           │
│  - Google OAuth authentication                              │
│  - Firestore database                                       │
│  - Image/Video generation jobs                              │
└─────────────────────────────────────────────────────────────┘
```

## 📊 What We've Done So Far

### ✅ Completed Steps

1. **Created SOHO React Frontend**
   - Built modern React app in `/frontend/soho/`
   - Configured production environment pointing to Cloud Run backend
   - Production build created: `/frontend/soho/dist/`

2. **Deployed to Firebase Hosting**
   - Created Firebase hosting site: `friedmomo`
   - Deployed to temporary URL: `https://friedmomo.web.app`
   - Configured SPA routing and cache headers

3. **Updated Backend CORS**
   - Added friedmomo.com and friedmomo.web.app to allowed origins
   - Backend accepts API calls from frontend

4. **Committed Changes to Git**
   - Branch: `claude-ui-overhaul`
   - All changes pushed to GitHub

## 🚧 Current Issues & Why

### Issue #1: Why friedmomo.web.app exists?
**Explanation:**
- Firebase Hosting gives every site a default `.web.app` URL
- This is a **temporary URL for testing** before your custom domain DNS is set up
- Once DNS is configured, **friedmomo.com will be the primary URL**
- The `.web.app` URL will continue to work but isn't meant for end users

### Issue #2: OAuth Login Loop
**Problem:** Google OAuth redirects are configured for the backend URL, not the frontend URL

**Current Flow (BROKEN):**
```
User on friedmomo.web.app
    ↓
Clicks "Login with Google"
    ↓
Backend generates OAuth URL: redirects to phoenix-234619602247.us-central1.run.app/login/google
    ↓
Google authenticates
    ↓
Redirects to: phoenix-234619602247.us-central1.run.app/login/google/callback
    ↓
Backend tries to redirect to: friedmomo.web.app
    ↓
Frontend doesn't have session (different domain) → LOOP
```

**Why This Happens:**
- OAuth redirects are cross-domain (frontend → backend → Google → backend → frontend)
- Sessions don't transfer between domains
- The `next` parameter gets lost in the redirect chain

### Issue #3: friedmomo.com Shows Squarespace
**Reason:** DNS records haven't been configured yet in Squarespace
- The domain is registered but not pointing to Firebase Hosting
- Squarespace shows default "under construction" page

## 🔧 What Needs to Be Fixed

### Priority 1: Fix OAuth Login Loop ⚠️

**Solution:** Update OAuth flow to use frontend domain in redirects

**Changes Needed:**
1. Update Google Cloud OAuth consent screen to allow `friedmomo.com` and `friedmomo.web.app`
2. Add authorized redirect URIs in Google Cloud Console
3. Update backend OAuth flow to redirect back to frontend properly

### Priority 2: Configure DNS in Squarespace

**Required Actions:**
1. Add custom domain in Firebase Console (get DNS records)
2. Configure DNS records in Squarespace
3. Wait for DNS propagation (1-48 hours)

### Priority 3: Update OAuth After DNS Propagation

Once friedmomo.com is live:
1. Test OAuth flow on production domain
2. Remove friedmomo.web.app from allowed origins (keep for testing if needed)

## 📝 Pending Tasks

### Immediate (Today)
- [ ] Fix OAuth redirect loop for friedmomo.web.app
- [ ] Add custom domain in Firebase Console
- [ ] Get DNS records from Firebase
- [ ] Configure DNS in Squarespace

### Short-term (1-2 days)
- [ ] Wait for DNS propagation
- [ ] Verify friedmomo.com loads correctly
- [ ] Test OAuth on friedmomo.com
- [ ] Update Google OAuth allowed domains

### Medium-term (1 week)
- [ ] Monitor performance and errors
- [ ] Set up monitoring/alerts
- [ ] Configure CDN optimization
- [ ] Add SSL certificate validation

## 🔐 Security Configuration

### CORS Settings (app.py:127)
```python
default_origins = 'https://friedmomo.com,https://www.friedmomo.com,https://friedmomo.web.app,http://localhost:5173'
```

### Environment Variables
- **Frontend (.env.production):**
  - `VITE_API_BASE_URL=https://phoenix-234619602247.us-central1.run.app`

- **Backend (Cloud Run):**
  - All secrets configured via Google Secret Manager
  - OAuth credentials, API keys, etc.

## 🎯 End Goal

**When Everything is Working:**

1. User visits **www.friedmomo.com**
2. Sees beautiful SOHO landing page
3. Clicks "Login with Google"
4. Authenticates with Google (smooth OAuth flow)
5. Returns to **www.friedmomo.com** logged in
6. Can create posts, explore feed, manage tokens
7. Full social media experience

## 📞 What You Need to Do Next

**For Comet Agent:**
1. Follow the Squarespace DNS configuration instructions (provided separately)
2. Report back when DNS records are added

**For Development:**
1. Let me fix the OAuth redirect loop issue now
2. Test on friedmomo.web.app
3. Once DNS propagates, test on friedmomo.com

---

**Last Updated:** 2025-11-12
**Status:** 🟡 In Progress - OAuth fix needed, DNS configuration pending
