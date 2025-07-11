# Debugging Guide: Frontend JSON Parsing Errors

## Problem Diagnosed

The error `Unexpected token '<', "<!DOCTYPE "... is not valid JSON` occurs when:

1. **Frontend expects JSON** from an API endpoint
2. **Backend returns HTML** (usually a login/error page) instead
3. **JavaScript tries to parse HTML as JSON** and fails

## Root Cause Analysis

### The Issue
- Frontend JavaScript: `fetch('/api/chat/message')` expects JSON response
- Backend authentication: Redirects unauthenticated users to HTML login page
- Result: Frontend receives HTML instead of JSON

### Why This Happened
1. **Authentication Check**: `@login_required` decorator redirects to login page
2. **AJAX vs Page Navigation**: Decorator doesn't distinguish between browser navigation and AJAX calls
3. **Content Type Mismatch**: Frontend sends `Content-Type: application/json` but receives `text/html`

## The Fix Applied

### 1. Updated `login_required` Decorator
```python
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'id_token' not in session:
            # Check if this is an AJAX request (expects JSON response)
            if request.headers.get('Content-Type') == 'application/json' or \
               request.headers.get('Accept', '').find('application/json') > -1 or \
               request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            else:
                return redirect(url_for('auth.login', next=request.url))
        return func(*args, **kwargs)
    return wrapper
```

**Key Changes:**
- Detects AJAX/API requests
- Returns JSON error instead of HTML redirect
- Provides redirect URL in JSON response

### 2. Enhanced Frontend Error Handling
```javascript
// Handle authentication errors
if (response.status === 401) {
    const errorData = await response.json();
    if (errorData.redirect) {
        alert('Please log in to continue chatting.');
        window.location.href = errorData.redirect;
        return;
    }
}

// Handle HTML responses (fallback)
if (!response.ok) {
    const errorText = await response.text();
    if (errorText.includes('<!DOCTYPE') || errorText.includes('<html')) {
        alert('Authentication required. Please log in to continue.');
        window.location.href = '/login';
        return;
    }
    throw new Error(`Server error: ${response.status}`);
}
```

**Key Changes:**
- Checks for 401 status code
- Detects HTML responses
- Graceful error messages
- Automatic redirect to login

### 3. Added Enhanced Logging
```python
logger.info(f"🤖 Generating text with model: {self.current_model}")
logger.info(f"📝 Prompt length: {len(prompt)} characters")
logger.info(f"🚀 Making API call to {self.current_model} (attempt {attempt + 1})")
logger.info(f"✅ Successfully generated text with {self.current_model}")
```

**Benefits:**
- Track LLM service calls
- Monitor model usage
- Debug API issues

## GCP Configuration Verified

### API Keys and Secrets
```bash
# Check GCP project
gcloud config get-value project
# phoenix-project-386

# List secrets
gcloud secrets list
# phoenix-gemini-api-key ✓
# phoenix-google-api-key ✓

# Verify API key
gcloud secrets versions access latest --secret="phoenix-gemini-api-key"
# AIzaSyAN-DyLvCpI2YXsD5APYupXWUsjWc-WSjU ✓

# Check enabled APIs
gcloud services list --enabled | grep -E "(generat|ai)"
# generativelanguage.googleapis.com ✓
# aiplatform.googleapis.com ✓
```

### Cloud Build Configuration
```yaml
# cloudbuild.yaml
- '--update-secrets'
- 'GEMINI_API_KEY=phoenix-gemini-api-key:latest,SECRET_KEY=phoenix-secret-key:latest,GOOGLE_API_KEY=phoenix-google-api-key:latest,GOOGLE_SEARCH_ENGINE_ID=phoenix-search-engine-id:latest,NEWSDATA_API_KEY=phoenix-newsdata-api-key:latest'
```

## Debugging Tools Created

### 1. `test_gemini_api.py`
- Tests Gemini API configuration
- Lists available models
- Verifies LLM service integration
- Tests chat functionality

### 2. `test_chat_api.py`
- Tests API endpoints
- Simulates frontend errors
- Checks authentication flow
- Identifies HTML vs JSON responses

### 3. `test_auth_fix.py`
- Verifies authentication fix
- Tests JSON error responses
- Confirms proper error handling

## How to Debug Similar Issues

### 1. Check Browser Developer Tools
```javascript
// In browser console, check Network tab:
// - Request headers: Content-Type: application/json
// - Response headers: text/html vs application/json
// - Response body: HTML vs JSON
```

### 2. Test API Directly
```bash
# Test with curl
curl -X POST https://your-app.com/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}' \
  -v

# Look for:
# - Status code (401, 200, etc.)
# - Content-Type header
# - Response body format
```

### 3. Check Server Logs
```bash
# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=phoenix" --limit=10

# Look for:
# - Authentication errors
# - LLM service calls
# - API responses
```

### 4. Test Authentication State
```javascript
// In browser console:
console.log(document.cookie); // Check session cookies
console.log(sessionStorage);  // Check stored tokens
console.log(localStorage);    // Check Firebase auth
```

## Prevention Tips

### 1. Consistent Error Handling
- Always check if request expects JSON
- Return appropriate content type
- Provide meaningful error messages

### 2. Frontend Robustness
- Handle different response types
- Check status codes before parsing
- Provide user-friendly error messages

### 3. Logging and Monitoring
- Log authentication attempts
- Monitor API response types
- Track LLM service usage

### 4. Testing
- Test both authenticated and unauthenticated scenarios
- Verify AJAX vs browser navigation behavior
- Test error conditions

## Summary

The issue was a classic **content type mismatch**:
- Frontend: Expected JSON from `/api/chat/message`
- Backend: Returned HTML login page for unauthenticated users
- Solution: Detect API requests and return JSON errors instead of HTML redirects

This type of error is common in single-page applications with authentication and can be prevented with proper API design and error handling.
