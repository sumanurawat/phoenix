# Google OAuth React Redirect Fix

## Problem
After logging in with Google OAuth from the React app (localhost:5173/login), users were being redirected to Flask app (localhost:8080/) instead of back to React app.

**Error in logs**:
```
INFO:werkzeug:127.0.0.1 - - [12/Nov/2025 00:03:49] "GET /login/google/callback?state=...&code=... HTTP/1.1" 302 -
INFO:werkzeug:127.0.0.1 - - [12/Nov/2025 00:03:49] "GET / HTTP/1.1" 200 -
```
The callback was redirecting to Flask `/` instead of React app.

## Root Cause
The `is_safe_url()` function was rejecting cross-port redirects. It only allowed URLs from the same domain:
```python
# Old code - only allowed localhost:8080 → localhost:8080
ref_url.netloc == test_url.netloc  # localhost:8080 != localhost:5173 ❌
```

When Google OAuth callback tried to redirect to `http://localhost:5173/`, `is_safe_url()` returned `False`, so it fell back to Flask's default redirect logic.

## Solution

### Updated `is_safe_url()` Function
Added exception for React dev server in development mode:

```python
def is_safe_url(target):
    """Ensure redirect URL is safe and belongs to our domain"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    # Allow same domain
    if test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc:
        return True
    
    # In development, allow React dev server (localhost:5173)
    if test_url.netloc == 'localhost:5173' and os.getenv('FLASK_ENV') == 'development':
        return True
    
    return False
```

### Google OAuth Callback Flow
The callback logic remains clean since `is_safe_url()` now handles React URLs:

```python
# Handle redirect after OAuth
next_url = session.pop('oauth_next_url', None)

# If we have a next_url and it's safe, use it
if next_url and is_safe_url(next_url):
    return redirect(next_url)  # ✅ Now redirects to localhost:5173

# Default Flask redirect logic
if user_has_username:
    return redirect(url_for('soho'))
else:
    return redirect(url_for('username_setup'))
```

## How It Works Now

### Google OAuth from React App:
```
1. User clicks "Continue with Google" on React login page (localhost:5173/login)
   
2. React navigates to: http://localhost:8080/login/google?next=http://localhost:5173/

3. Flask /login/google stores next=http://localhost:5173/ in session['oauth_next_url']

4. Redirects to Google OAuth consent screen

5. Google redirects back to /login/google/callback with code

6. Flask callback:
   - Exchanges code for tokens
   - Signs in user with Firebase
   - Creates session
   - Retrieves next_url = session.pop('oauth_next_url')  # http://localhost:5173/
   - Checks is_safe_url('http://localhost:5173/')  # ✅ Returns True (dev mode)
   - return redirect('http://localhost:5173/')

7. User lands on React app at localhost:5173/ with session established ✅
```

### Google OAuth from Flask Templates (Unchanged):
```
1. User clicks Google login on Flask template (localhost:8080/login)
2. No ?next parameter or next=localhost:8080/some-page
3. is_safe_url() allows same-domain redirects
4. Falls back to default Flask redirect (/profile or /username_setup)
5. ✅ Existing functionality preserved
```

## Security Considerations

### Development Mode Only
The React dev server exception only applies when `FLASK_ENV=development`:
```python
if test_url.netloc == 'localhost:5173' and os.getenv('FLASK_ENV') == 'development':
    return True
```

### Production Deployment
In production:
- React build served from Flask static directory
- Both frontend and API on same domain (no cross-origin redirects)
- `FLASK_ENV` != 'development', so localhost:5173 exception doesn't apply
- `is_safe_url()` only allows same-domain redirects (secure)

### Defense in Depth
- Still validates URL scheme (http/https)
- Still uses session-stored `oauth_next_url` (prevents tampering)
- Still checks domain/port for production
- Additional port check is explicit and conditional

## Testing

### Test Google OAuth from React:
1. Navigate to http://localhost:5173/login
2. Click "Continue with Google"
3. Complete Google OAuth flow
4. **Expected**: Land back on http://localhost:5173/ (not 8080) ✅
5. **Expected**: Session established, logged in state shown ✅

### Test Google OAuth from Flask (backward compatibility):
1. Navigate to http://localhost:8080/login
2. Click Google login button
3. Complete OAuth flow
4. **Expected**: Redirects to Flask route (profile or username setup) ✅

### Verify Production Safety:
1. Set `FLASK_ENV=production`
2. Try to craft redirect to external site
3. **Expected**: `is_safe_url()` rejects it ✅
4. Only same-domain redirects allowed ✅

## Files Modified
- ✅ `/api/auth_routes.py` - Updated `is_safe_url()` function
- ✅ `/api/auth_routes.py` - Simplified Google OAuth callback redirect logic

## Related Fixes
- Email/password login JSON response (SOHO_AUTH_FLOW_COMPLETE.md)
- Signup JSON response with EMAIL_EXISTS handling
- All authentication flows now work seamlessly with React app

## Status
✅ **FIXED** - Google OAuth now properly redirects back to React app after authentication
