# Session Expiration Fix - Deployment Instructions

## Summary of Changes

This PR fixes the "session has expired" error that occurs when Cloud Run auto-scales and creates multiple instances. The issue was caused by using filesystem-based sessions which don't work across multiple instances.

## What Changed

### Configuration Changes
- **Session Storage**: Filesystem (`SESSION_TYPE = "filesystem"`) → Cookie-based (`SESSION_TYPE = None`)
- **Session Lifetime**: Indefinite → 7 days (`PERMANENT_SESSION_LIFETIME = timedelta(days=7)`)
- **Cookie Security**: Added HttpOnly, SameSite=Lax, and environment-configurable Secure attribute

### Files Modified
1. `config/settings.py` - Session configuration
2. `app.py` - Session initialization logic
3. `cloudbuild.yaml` - Added `SESSION_COOKIE_SECURE=true` env var
4. `cloudbuild-dev.yaml` - Added `SESSION_COOKIE_SECURE=true` env var
5. `start_local.sh`, `start_production.sh`, `start_dev_mode.sh` - Removed flask_session directory creation
6. `RUNNING_THE_APP.md` - Updated documentation
7. `SESSION_FIX_DOCUMENTATION.md` - Comprehensive fix documentation
8. `test_session_config.py` - Added test coverage

## Deployment Steps

### 1. Review Changes
```bash
git diff main...copilot/fix-session-expired-error
```

### 2. Merge to Main Branch
This will trigger automatic deployment to production via GitHub webhook:
```bash
git checkout main
git merge copilot/fix-session-expired-error
git push origin main
```

### 3. Monitor Deployment
Watch Cloud Build logs:
```bash
gcloud builds list --limit=5
# Get the latest build ID, then:
gcloud builds log <BUILD_ID> --stream
```

### 4. Verify Production
After deployment completes (~5-10 minutes):

1. **Login to Phoenix**: https://phoenix-234619602247.us-central1.run.app/login
2. **Navigate to Reel Maker**: https://phoenix-234619602247.us-central1.run.app/reel-maker
3. **Load a project with video clips** - This will trigger multiple API requests
4. **Expected Result**: No "session expired" errors, all video clips load successfully

### 5. Check Session Cookies
In browser DevTools (F12):
1. Go to **Application** tab → **Cookies**
2. Find the session cookie
3. Verify attributes:
   - ✅ **HttpOnly**: Yes
   - ✅ **Secure**: Yes (production HTTPS)
   - ✅ **SameSite**: Lax
   - ✅ **Expires**: ~7 days from now

## Expected Behavior Changes

### For Users
- **✅ Sessions persist across Cloud Run instances** - No more "session expired" errors
- **✅ Sessions last 7 days** - Users stay logged in across browser restarts
- **⚠️ One-time re-login required** - Existing sessions from filesystem will be invalidated

### For Developers
- **✅ Local development works without changes** - HTTP cookies work (SESSION_COOKIE_SECURE=false by default)
- **✅ No more flask_session directory** - No cleanup needed
- **✅ Faster startup** - No session file I/O

## Rollback Plan

If issues arise, rollback is straightforward:

```bash
# 1. Revert the merge
git revert <merge-commit-sha>
git push origin main

# 2. Or rollback Cloud Run to previous revision
gcloud run services update-traffic phoenix \
  --to-revisions=<previous-revision>=100 \
  --region=us-central1
```

## Testing in Development

### Local Testing
```bash
# Clone and checkout the branch
git fetch origin
git checkout copilot/fix-session-expired-error

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python test_session_config.py

# Start app (will use HTTP cookies since SESSION_COOKIE_SECURE defaults to false)
./start_local.sh

# Test login and navigation
# Open http://localhost:8080
```

### Dev Environment Testing (Optional)
Deploy to dev environment first if you want extra confidence:

```bash
# Deploy to dev
gcloud builds submit --config cloudbuild-dev.yaml

# Test at dev URL
# Login and verify session persistence
```

## Monitoring Post-Deployment

### Success Indicators
- ✅ No 401 errors in Cloud Run logs when accessing `/api/reel/projects/<id>/clips/`
- ✅ Users can load reel-maker page with multiple video clips
- ✅ Sessions persist across page refreshes and tab reopens
- ✅ Cloud Run scales up/down without session loss

### Warning Signs
- ❌ Increased 401 errors in logs
- ❌ Users reporting frequent re-login prompts
- ❌ Session cookies not being set (check browser DevTools)

### Logs to Monitor
```bash
# Watch Cloud Run logs
gcloud run services logs read phoenix --region=us-central1 --limit=50 --format="table(timestamp,severity,textPayload)"

# Filter for session/auth errors
gcloud run services logs read phoenix --region=us-central1 --limit=100 | grep -E "(401|session|Authentication)"
```

## FAQ

### Q: Will this break existing user sessions?
**A:** Yes, users with active filesystem-based sessions will need to re-login once after deployment. This is a one-time impact.

### Q: Is cookie-based session storage secure?
**A:** Yes, when properly configured:
- Cookies are cryptographically signed with SECRET_KEY (tamper-proof)
- HttpOnly prevents JavaScript access (XSS protection)
- Secure attribute ensures HTTPS-only transmission (production)
- SameSite=Lax provides CSRF protection

### Q: What if users clear cookies?
**A:** They'll need to re-login, same as before. Session lifetime is now 7 days instead of indefinite.

### Q: Can we increase session lifetime?
**A:** Yes, adjust `PERMANENT_SESSION_LIFETIME` in `config/settings.py`. Current value (7 days) balances convenience and security.

### Q: Does this affect API authentication?
**A:** No, API routes still check for `id_token` in session. The storage mechanism changed, not the authentication logic.

## Additional Notes

- **SECRET_KEY**: Ensure this remains constant across deployments (stored in Google Secret Manager)
- **Cookie Size**: Session data is now in cookies (~1-2 KB per request). Shouldn't be an issue for Phoenix's session data.
- **Compliance**: Cookie-based sessions meet GDPR/privacy requirements when properly disclosed in privacy policy.

## Contact

For questions or issues during deployment, refer to:
- **Technical Documentation**: `SESSION_FIX_DOCUMENTATION.md`
- **Code Changes**: Review the PR diff
- **Tests**: Run `python test_session_config.py`
