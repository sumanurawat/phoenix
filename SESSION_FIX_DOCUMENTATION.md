# Session Configuration Fix for Cloud Run

## Problem

Users were experiencing "session has expired" errors shortly after login, particularly when accessing the reel-maker page with multiple video clips. The issue manifested as:

1. User logs in successfully
2. User navigates to reel-maker page
3. Cloud Run auto-scales and creates a new instance
4. Subsequent API requests (e.g., video clip URLs) return 401 Unauthorized

## Root Cause

The application was using **filesystem-based sessions** (`SESSION_TYPE = "filesystem"`), which stores session data in the `./flask_session/` directory. In Cloud Run's multi-instance environment:

- Each instance has its own ephemeral filesystem
- Sessions created on Instance A are not accessible from Instance B
- When load balancer routes requests to different instances, sessions appear to be "expired"

## Solution

Switched to **signed cookie-based sessions** by setting `SESSION_TYPE = None`. This approach:

- Stores session data in encrypted, signed cookies sent to the client
- Works seamlessly across multiple Cloud Run instances
- Provides the same security guarantees with proper configuration

## Configuration Changes

### Session Settings (`config/settings.py`)

```python
# Session configuration
SESSION_TYPE = None  # Cookie-based (was: "filesystem")
SESSION_PERMANENT = True  # Enable 7-day session lifetime
SESSION_USE_SIGNER = True  # Sign cookies for security
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE", default=False)  # HTTPS only (set via env var)
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access (XSS protection)
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Session expires after 7 days
```

### Environment Variables

**Production (`cloudbuild.yaml` and `cloudbuild-dev.yaml`):**
```yaml
--update-env-vars
- SESSION_COOKIE_SECURE=true  # Only send cookies over HTTPS
```

**Local Development:**
```bash
# SESSION_COOKIE_SECURE defaults to false for HTTP testing
# No environment variable needed
```

### Application Changes (`app.py`)

```python
# Only initialize flask-session if using server-side sessions
if SESSION_TYPE is not None:
    app.config["SESSION_TYPE"] = SESSION_TYPE
    Session(app)
# else: Use Flask's built-in cookie-based sessions
```

## Security Considerations

### Cookie Signing
- All session cookies are cryptographically signed using `SECRET_KEY`
- Tampering with cookies is detected and rejected
- Equivalent security to server-side sessions

### Cookie Attributes
- **HttpOnly**: Prevents JavaScript access, mitigating XSS attacks
- **SameSite=Lax**: Provides CSRF protection while allowing legitimate cross-site navigation
- **Secure** (production): Ensures cookies only sent over HTTPS

### Session Lifetime
- 7-day expiration prevents indefinite sessions
- Automatic cleanup as cookies expire client-side
- Users remain logged in across browser restarts (until expiration)

## Migration Notes

### What Changed
1. **Session storage**: Filesystem → Signed cookies
2. **Session persistence**: Per-instance → Shared across all instances
3. **Session lifetime**: Indefinite → 7 days
4. **Directory cleanup**: `./flask_session/` no longer used or created

### What Stayed the Same
- Session data structure (same keys: `user_id`, `user_email`, etc.)
- Authentication flow (no changes to login/logout)
- CSRF protection (still using `csrf_token` in session)
- API authentication (still checking `id_token` in session)

### Compatibility
- ✅ **Backward compatible**: Existing logged-in users will need to re-login once (old filesystem sessions won't work)
- ✅ **Multi-instance safe**: Sessions work across all Cloud Run instances
- ✅ **Local development**: Works with `SESSION_COOKIE_SECURE=false` (HTTP)
- ✅ **Production**: Works with `SESSION_COOKIE_SECURE=true` (HTTPS)

## Testing

### Automated Tests
```bash
python test_session_config.py
```

Verifies:
- Session configuration imports correctly
- Flask app initializes with cookie-based sessions
- Session data persists across requests
- Cookie attributes (HttpOnly, SameSite) are set correctly
- Secure attribute is environment-dependent

### Manual Verification

**Production (after deployment):**
1. Login to Phoenix
2. Navigate to reel-maker page
3. Load multiple video clips (triggers multiple instances)
4. Verify no "session expired" errors

**Local Development:**
```bash
./start_local.sh
# Login and test features
```

## Troubleshooting

### Issue: "Session is unavailable because no secret key was set"
**Cause**: `SECRET_KEY` not configured or too short

**Solution**: Ensure `SECRET_KEY` environment variable is set to a strong, unique value (minimum 32 characters)

### Issue: Cookies not being set in production
**Cause**: `SESSION_COOKIE_SECURE=true` but site is HTTP

**Solution**: Verify site is accessed via HTTPS (Cloud Run enforces this)

### Issue: Sessions expire too quickly
**Cause**: Browser blocking cookies or session lifetime too short

**Solution**: 
- Check browser cookie settings
- Adjust `PERMANENT_SESSION_LIFETIME` in `config/settings.py`

### Issue: Users must re-login after deployment
**Cause**: `SECRET_KEY` changed between deployments

**Solution**: Ensure `SECRET_KEY` is persisted in Google Secret Manager and not regenerated

## Performance Impact

### Before (Filesystem Sessions)
- **Storage**: Local disk I/O per request
- **Scaling**: Session data lost when instance scales down
- **Memory**: Accumulated session files (500 file limit)

### After (Cookie Sessions)
- **Storage**: No server-side storage needed
- **Scaling**: Seamless - cookies travel with requests
- **Memory**: Zero server memory for session storage

**Trade-off**: Slightly larger HTTP headers (~1-2 KB per request) vs. no session management overhead

## References

- [Flask Sessions Documentation](https://flask.palletsprojects.com/en/stable/api/#sessions)
- [Flask-Session Documentation](https://flask-session.readthedocs.io/)
- [Cloud Run Best Practices - Stateless Containers](https://cloud.google.com/run/docs/tips/general#stateless)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
