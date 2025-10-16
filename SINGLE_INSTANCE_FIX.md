# Single Instance Fix for Session Expiration

## Problem
Users were getting "Your session has expired" errors within seconds of logging in, especially when navigating to Reel Maker.

**Root Cause**: Cloud Run autoscaling created new instances that didn't have access to session files stored in `./flask_session/` on the original instance.

## Solution
Set `max-instances=1` to prevent autoscaling:
- All requests go to the **same instance**
- All sessions stored in **same `./flask_session/` directory**
- No new instances = no session loss
- **$0 monthly cost** (stays in FREE TIER)

## Changes Made

### 1. Cloud Build Configs
**Production (`cloudbuild.yaml`)**:
```yaml
- '--max-instances'
- '1'
```

**Dev (`cloudbuild-dev.yaml`)**:
```yaml
- '--max-instances'
- '1'
```

### 2. Localhost Video Signing Fix (Bonus)
Updated `services/reel_storage_service.py` to try multiple credential paths:
1. `firebase-credentials.json` (most common for local dev)
2. `GOOGLE_APPLICATION_CREDENTIALS` env var
3. `~/.config/gcloud/application_default_credentials.json`

### 3. Documentation Updates
Updated `.github/copilot-instructions.md` to document single-instance solution.

## Trade-offs

### ✅ What You Get:
- No "session expired" errors
- $0/month infrastructure cost
- Stay in Cloud Run FREE TIER
- Simple architecture

### ⚠️ What You Give Up:
- High traffic handling (limited to ~100 concurrent requests)
- Redundancy (single point of failure)
- Geographic distribution

**Perfect for prototyping and MVP development!**

## Cost Impact
- **Before**: $0 (but session issues)
- **Now**: $0 (no session issues)
- **Alternative (Redis)**: ~$71/month

## Deployment
Already committed and deployed. Changes are live in both production and dev environments.

## Future Scaling
When ready to scale beyond single instance:
1. Consider Redis session storage (~$71/month)
2. Update `max-instances` to higher number
3. Set up VPC connector for Redis access

For now, single instance is perfect for FREE TIER prototyping!

