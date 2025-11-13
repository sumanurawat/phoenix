# SOHO React Authentication Testing Guide

## Changes Summary
Fixed the authentication flow between React frontend (localhost:5173) and Flask backend (localhost:8080) to eliminate port jumping and provide seamless single-page app experience.

### What Was Fixed
1. **React Login/Signup Pages**: Added `Accept: application/json` header to requests
2. **Flask Login Route**: Returns JSON for API requests, HTML redirect for traditional forms
3. **Flask Signup Route**: Returns JSON for API requests with proper error handling
4. **Port Jumping Eliminated**: React now handles all redirects client-side after receiving JSON response

## Testing Steps

### Prerequisites
1. **Start Flask Backend**:
   ```bash
   cd /Users/sumanurawat/Documents/GitHub/phoenix
   source venv/bin/activate
   ./start_local.sh
   ```
   - Wait for "Running on http://localhost:8080"

2. **Start React Frontend** (in new terminal):
   ```bash
   cd /Users/sumanurawat/Documents/GitHub/phoenix/frontend/soho
   npm run dev
   ```
   - Should start on http://localhost:5173

### Test 1: Login Flow (Primary Test)
1. Open browser to http://localhost:5173
2. Click "Sign In" button
3. Should navigate to http://localhost:5173/login (NOT 8080!)
4. Enter valid credentials:
   - Email: [your test email]
   - Password: [your test password]
5. Click "Sign In"
6. **Expected Behavior**:
   - ✅ Network tab shows POST to http://localhost:8080/login returns JSON:
     ```json
     {
       "success": true,
       "user_id": "...",
       "email": "...",
       "next": "/"
     }
     ```
   - ✅ Browser redirects to http://localhost:5173/ (NOT 8080!)
   - ✅ You see logged-in state (user profile, token balance)
   - ✅ No port jumping - stays on 5173 throughout

### Test 2: Signup Flow with New Email
1. Navigate to http://localhost:5173/signup
2. Enter new email and password (min 6 chars)
3. Confirm password matches
4. Click "Sign Up"
5. **Expected Behavior**:
   - ✅ Network tab shows POST to http://localhost:8080/signup returns JSON:
     ```json
     {
       "success": true,
       "user_id": "...",
       "email": "...",
       "next": "/"
     }
     ```
   - ✅ Browser redirects to http://localhost:5173/
   - ✅ Account created with free tier subscription
   - ✅ Logged in automatically

### Test 3: Signup with Existing Email (Error Handling)
1. Navigate to http://localhost:5173/signup
2. Enter email that's already registered
3. Enter password and confirm
4. Click "Sign Up"
5. **Expected Behavior**:
   - ✅ Network tab shows POST returns JSON with 409 status:
     ```json
     {
       "success": false,
       "error": "EMAIL_EXISTS",
       "message": "This email is already registered..."
     }
     ```
   - ✅ Info message appears: "This email is already registered. Please sign in instead."
   - ✅ After 2 seconds, auto-redirects to http://localhost:5173/login
   - ✅ No port jumping

### Test 4: Google OAuth
1. Navigate to http://localhost:5173/login
2. Click "Continue with Google" button
3. **Expected Behavior**:
   - ✅ Redirects to Google OAuth consent screen
   - ✅ After consent, returns to application
   - ✅ Logged in state established
   - ⚠️ Note: Google OAuth callback URL must be configured in Firebase Console

### Test 5: Login with Invalid Credentials
1. Navigate to http://localhost:5173/login
2. Enter invalid email/password
3. Click "Sign In"
4. **Expected Behavior**:
   - ✅ Error message displays: "Invalid email or password"
   - ✅ Stays on http://localhost:5173/login
   - ✅ No redirect, no port jumping

### Test 6: Navigation Flow with ?next Parameter
1. Try to access protected page (e.g., http://localhost:5173/reel-maker)
2. Should redirect to http://localhost:5173/login?next=%2Freel-maker
3. Enter valid credentials and login
4. **Expected Behavior**:
   - ✅ After login, redirects to http://localhost:5173/reel-maker (intended destination)
   - ✅ No port jumping throughout

### Test 7: Logout and Re-login
1. While logged in, click logout (if available in UI)
2. Should redirect to http://localhost:5173/
3. Click "Sign In" again
4. Login with valid credentials
5. **Expected Behavior**:
   - ✅ Clean logout (session cleared)
   - ✅ Successful re-login
   - ✅ All redirects stay on port 5173

## Debug Checklist

### If Login Redirects to Port 8080:
1. Check browser Network tab - is the response HTML or JSON?
   - If HTML: Flask isn't detecting API request (check Accept header)
   - If JSON: React isn't handling response correctly
2. Verify `Accept: application/json` header in LoginPage.tsx request
3. Check Flask logs for "is_api_request" detection logic

### If You Get 401 Errors:
1. Check CSRF token is being fetched and sent
2. Verify CORS configuration in Flask allows credentials
3. Check browser console for CORS errors
4. Ensure `withCredentials: true` in axios config

### If Session Not Persisting:
1. Check browser cookies - should see Flask session cookie
2. Verify `SameSite=Lax` cookie attribute
3. Check that `withCredentials: true` is set in axios
4. In dev tools, check Application > Cookies > localhost:8080

### If Google OAuth Fails:
1. Verify `/login/google` route exists in Flask (not `/auth/google`)
2. Check Firebase Console - Authorized domains and redirect URIs
3. Verify callback URL is configured: `http://localhost:8080/login/google/callback`

## Expected Network Traffic

### Successful Login Sequence:
```
1. GET http://localhost:8080/api/csrf-token
   Response: {"csrf_token": "..."}

2. POST http://localhost:8080/login
   Request Headers:
     Content-Type: application/x-www-form-urlencoded
     Accept: application/json
   Request Body:
     email=user@example.com&password=...&csrf_token=...
   Response (200):
     {"success": true, "user_id": "...", "email": "...", "next": "/"}

3. Client-side redirect: window.location.href = "/"
   (No additional network request - just browser navigation)
```

### Successful Signup Sequence:
```
1. GET http://localhost:8080/api/csrf-token
   Response: {"csrf_token": "..."}

2. POST http://localhost:8080/signup
   Request Headers:
     Content-Type: application/x-www-form-urlencoded
     Accept: application/json
   Response (200):
     {"success": true, "user_id": "...", "email": "...", "next": "/"}

3. Client-side redirect to "/"
```

### Email Already Exists Sequence:
```
1. GET http://localhost:8080/api/csrf-token
2. POST http://localhost:8080/signup
   Response (409):
     {"success": false, "error": "EMAIL_EXISTS", "message": "..."}
3. UI shows error message
4. After 2s, navigate to /login (React Router, no network request)
```

## Architecture Notes

### Development (Current Setup)
- React: localhost:5173 (Vite dev server)
- Flask: localhost:8080 (Python Flask)
- CORS: Enabled with `supports_credentials=True`
- Session: HttpOnly cookies from port 8080
- Communication: Cross-origin XHR with credentials

### Production (Planned)
- React: Served as static build from Flask (`/static/soho/`)
- Flask: Single domain serving both frontend and API
- CORS: Not needed (same origin)
- Session: HttpOnly cookies, same domain
- Communication: Same-origin requests, no CORS complexity

### Key Files Modified
- `frontend/soho/src/pages/LoginPage.tsx` - Added Accept header, JSON response handling
- `frontend/soho/src/pages/SignupPage.tsx` - Added Accept header, JSON response handling
- `api/auth_routes.py` - Dual-mode responses (JSON for API, redirect for templates)

### Backward Compatibility
The Flask routes still support traditional form submissions:
- If `Accept` header doesn't include `application/json`, returns HTML redirect
- This preserves existing Phoenix features that use Flask templates
- Only React SPA routes benefit from JSON responses

## Success Criteria
- ✅ All authentication actions stay on localhost:5173
- ✅ No visible port changes in browser address bar
- ✅ Session persists across page refreshes
- ✅ Login, signup, logout all work seamlessly
- ✅ Error messages display correctly in React UI
- ✅ Google OAuth works (if credentials configured)
- ✅ Network tab shows JSON responses, not HTML

## Next Steps After Testing
1. Test in production-like environment (React build served by Flask)
2. Update deployment scripts if needed
3. Document production build process
4. Consider migrating other Phoenix features to React (gradual migration)
