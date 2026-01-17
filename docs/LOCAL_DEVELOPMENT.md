# Local Development Setup Guide

This guide explains how to set up the Phoenix/Friedmomo project for local development.

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn
- Google Cloud SDK (`gcloud`) installed and authenticated
- Access to the GCP project `phoenix-project-386`

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/sumanurawat/phoenix.git
cd phoenix

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up environment variables (see below)
cp .env.example .env
# Edit .env with your values

# 4. Set up Firebase credentials (see below)
# Place firebase-credentials.json in project root

# 5. Set up frontend
cd frontend/soho
npm install
cp .env.example .env
# Edit .env if needed

# 6. Run the backend
cd ../..
python run.py

# 7. Run the frontend (separate terminal)
cd frontend/soho
npm run dev
```

---

## Required Files (Get from Project Admin)

### 1. Firebase Service Account Credentials
**File:** `firebase-credentials.json`
**Location:** Project root (`/phoenix/firebase-credentials.json`)

This file is required for:
- Firebase Authentication
- Firestore database access
- Firebase Admin SDK operations

**How to get it:**
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select the project
3. Project Settings → Service Accounts
4. Generate new private key
5. Save as `firebase-credentials.json` in project root

### 2. Backend Environment Variables
**File:** `.env`
**Location:** Project root (`/phoenix/.env`)

Copy from `.env.example` and fill in values.

---

## Environment Variables Reference

### Required for Basic Functionality

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to firebase-credentials.json | Set to `./firebase-credentials.json` |
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | `phoenix-project-386` |
| `SECRET_KEY` | Flask session secret | Generate random string |
| `FIREBASE_API_KEY` | Firebase Web API key | Firebase Console → Project Settings |
| `GOOGLE_CLIENT_ID` | OAuth Client ID | GCP Console → APIs & Services → Credentials |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret | GCP Console → APIs & Services → Credentials |

### Required for AI Features

| Variable | Description | Where to Get |
|----------|-------------|--------------|




### Required for Payments (Stripe)

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `STRIPE_SECRET_KEY` | Stripe API secret | [Stripe Dashboard](https://dashboard.stripe.com/apikeys) |
| `STRIPE_PUBLISHABLE_KEY` | Stripe public key | Stripe Dashboard |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret | Stripe Dashboard → Webhooks |
| `STRIPE_PRO_PRICE_ID` | Pro plan price ID | Stripe Dashboard → Products |

### Optional Services

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `SENDGRID_API_KEY` | Email service | [SendGrid](https://sendgrid.com/) |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 storage | Cloudflare Dashboard |
| `R2_SECRET_ACCESS_KEY` | R2 secret key | Cloudflare Dashboard |
| `R2_BUCKET_NAME` | R2 bucket name | `ai-image-posts-prod` |
| `R2_ENDPOINT_URL` | R2 endpoint | Cloudflare Dashboard |

---

## Sample .env File

```bash
# === Core Configuration ===
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-random-secret-key-here-make-it-long

# === Google Cloud / Firebase ===
GOOGLE_APPLICATION_CREDENTIALS=./firebase-credentials.json
GOOGLE_CLOUD_PROJECT=phoenix-project-386
GOOGLE_CLOUD_LOCATION=us-central1
FIREBASE_API_KEY=your-firebase-api-key

# === OAuth (Google Sign-In) ===
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-oauth-client-secret

# === AI APIs ===
GEMINI_API_KEY=your-gemini-api-key
DEFAULT_MODEL=gemini-2.0-flash
FALLBACK_MODEL=gemini-2.0-flash

# === Stripe (use test keys for development) ===
STRIPE_SECRET_KEY=sk_test_your-test-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-test-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# === URLs ===
APP_BASE_URL=http://localhost:8080
BASE_URL=http://localhost:8080
```

---

## Frontend Environment Variables

**File:** `frontend/soho/.env`

```bash
VITE_API_BASE_URL=http://localhost:8080
VITE_APP_NAME=MOMO
VITE_ENV=development
```

---

## What NOT to Share (Secrets)

Never commit or share these files:
- `.env` (any .env file except .env.example)
- `firebase-credentials.json`
- Any `*-credentials.json` files
- Stripe webhook secrets
- API keys

These are already in `.gitignore`.

---

## Files to Share with New Developers

### Share These (Non-Secret)
1. **This guide** (`docs/LOCAL_DEVELOPMENT.md`)
2. **Example files** (`.env.example`, `frontend/soho/.env.example`)
3. **Agent instructions** (`AGENTS.md`)

### Share Securely (Secret - via secure channel, NOT GitHub)
1. `firebase-credentials.json` - Firebase service account
2. `.env` values - Or have them create their own API keys

### For Production Access
- Add their Google account to GCP project `phoenix-project-386`
- Add to Firebase project (if needed)
- Add to Stripe team (if needed)

---

## Running the Application

### Backend (Flask)
```bash
source venv/bin/activate
python run.py
# Runs on http://localhost:8080
```

### Frontend (React/Vite)
```bash
cd frontend/soho
npm run dev
# Runs on http://localhost:5173
```

### Both Together
Use two terminal windows, or:
```bash
# Terminal 1
python run.py

# Terminal 2
cd frontend/soho && npm run dev
```

---

## Testing Stripe Webhooks Locally

Use Stripe CLI to forward webhooks:
```bash
# Install Stripe CLI first
stripe listen --forward-to localhost:8080/api/stripe/webhook

# This will give you a webhook signing secret (whsec_...)
# Add it to your .env as STRIPE_WEBHOOK_SECRET
```

---

## Troubleshooting

### "Firebase credentials not found"
- Ensure `firebase-credentials.json` exists in project root
- Check `GOOGLE_APPLICATION_CREDENTIALS` points to it

### "Session issues / Not logged in"
- Clear browser cookies for localhost
- Check `SECRET_KEY` is set in `.env`

### "Stripe webhook errors"
- Run `stripe listen` to forward webhooks locally
- Update `STRIPE_WEBHOOK_SECRET` with the CLI secret

### "CORS errors"
- Backend runs on `:8080`, frontend on `:5173`
- CORS is configured to allow localhost origins

---

## Getting Help

- Check `AGENTS.md` for codebase guidelines
- Check `services/account_deletion_service.py` for data model reference
- Ask the project admin for credentials access
