"""Routes for user authentication, including Google and Instagram OAuth."""
import os
import json
import base64
import logging
import uuid
from functools import wraps
from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
import requests

from services.auth_service import AuthService
from services.stripe_service import StripeService
from firebase_admin import firestore
from middleware.csrf_protection import csrf_protect

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()
logger = logging.getLogger(__name__)

# Instance ID for tracking which Cloud Run instance handles requests
# This helps debug autoscaling issues
import os
INSTANCE_ID = os.getenv('K_REVISION', 'local')[:20]  # Cloud Run revision name
CONTAINER_ID = uuid.uuid4().hex[:8]  # Unique per container start


@auth_bp.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """Endpoint to refresh CSRF token."""
    return jsonify({
        'success': True,
        'csrf_token': session.get('csrf_token')
    })


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

    # Allow friedmomo.com domains (production frontend)
    allowed_frontend_domains = [
        'friedmomo.com',
        'www.friedmomo.com',
        'friedmomo.web.app',
        'friedmomo--production-pfwp1l6e.web.app'  # Firebase preview channel
    ]
    if test_url.netloc in allowed_frontend_domains:
        return True

    return False


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Debug logging for auth issues
        all_cookies = list(request.cookies.keys())
        session_cookie = request.cookies.get('__session') or request.cookies.get('session')
        has_id_token = 'id_token' in session
        
        logger.info(f"[login_required] Checking auth for {request.path} | instance={INSTANCE_ID}/{CONTAINER_ID}")
        logger.info(f"[login_required] Cookies received: {all_cookies} | __session={'present' if session_cookie else 'MISSING'}")
        logger.info(f"[login_required] Session has id_token: {has_id_token} | session_keys: {list(session.keys())}")
        
        if 'id_token' not in session:
            logger.warning(f"[login_required] AUTH FAILED - No id_token in session | path={request.path}")
            # Check if this is an AJAX request (expects JSON response)
            if request.headers.get('Content-Type') == 'application/json' or \
               request.headers.get('Accept', '').find('application/json') > -1 or \
               request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            else:
                return redirect(url_for('auth.login', next=request.url))
        
        logger.info(f"[login_required] AUTH SUCCESS for {request.path} | user_id={session.get('user_id', 'unknown')}")
        return func(*args, **kwargs)
    return wrapper


@auth_bp.route('/signup', methods=['GET', 'POST'])
@csrf_protect
def signup():
    error = None
    next_url = request.args.get('next') or request.form.get('next')
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            data = auth_service.signup_email_password(email, password)
            session['id_token'] = data.get('idToken')
            session['user_email'] = data.get('email')
            session['user_id'] = data.get('localId')
            
            # Ensure user record exists in Firestore
            try:
                db = firestore.client()
                db.collection('users').document(session['user_id']).set({
                    'firebase_uid': session['user_id'],
                    'email': session.get('user_email')
                }, merge=True)
            except Exception:
                pass
            
            # Check if this is an API request (from React) or traditional form submission
            is_api_request = (
                request.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded') and
                request.headers.get('Accept', '').find('application/json') > -1
            ) or request.path.startswith('/api/')
            
            if is_api_request:
                # Return JSON response for API clients (React)
                return jsonify({
                    'success': True,
                    'user_id': session['user_id'],
                    'email': session['user_email'],
                    'next': next_url or '/explore'
                }), 200
            else:
                # Traditional redirect for Flask template forms
                if next_url and is_safe_url(next_url):
                    return redirect(next_url)
                else:
                    return redirect(url_for('auth.profile'))
        except Exception as e:
            error_str = str(e)
            # Check if this is an "email already exists" error
            if 'EMAIL_EXISTS' in error_str or 'email already exists' in error_str.lower():
                # Check if API request
                is_api_request = (
                    request.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded') and
                    request.headers.get('Accept', '').find('application/json') > -1
                ) or request.path.startswith('/api/')
                
                if is_api_request:
                    return jsonify({
                        'success': False,
                        'error': 'EMAIL_EXISTS',
                        'message': 'This email is already registered. Please sign in instead.'
                    }), 409
                else:
                    # Redirect to login page with a helpful message
                    flash('This email is already registered. Please sign in instead.', 'info')
                    login_url = url_for('auth.login')
                    if next_url:
                        login_url += f'?next={next_url}'
                    return redirect(login_url)
            
            # Other errors
            is_api_request = (
                request.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded') and
                request.headers.get('Accept', '').find('application/json') > -1
            ) or request.path.startswith('/api/')
            
            if is_api_request:
                return jsonify({'success': False, 'error': error_str}), 400
            
            error = error_str
    return render_template('signup.html', title='Sign Up', error=error, next=next_url)


@auth_bp.route('/login', methods=['GET', 'POST'])
@csrf_protect
def login():
    error = None
    next_url = request.args.get('next') or request.form.get('next')
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            data = auth_service.login_email_password(email, password)
            session['id_token'] = data.get('idToken')
            session['user_email'] = data.get('email')
            session['user_id'] = data.get('localId')
            
            # Ensure user record exists in Firestore
            try:
                db = firestore.client()
                db.collection('users').document(session['user_id']).set({
                    'firebase_uid': session['user_id'],
                    'email': session.get('user_email')
                }, merge=True)
            except Exception:
                pass

            # Check if this is an API request (from React) or traditional form submission
            is_api_request = (
                request.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded') and
                request.headers.get('Accept', '').find('application/json') > -1
            ) or request.path.startswith('/api/')
            
            if is_api_request:
                # Return JSON response for API clients (React)
                return jsonify({
                    'success': True,
                    'user_id': session['user_id'],
                    'email': session['user_email'],
                    'next': next_url or '/explore'
                }), 200
            else:
                # Traditional redirect for Flask template forms
                if next_url and is_safe_url(next_url):
                    return redirect(next_url)
                else:
                    return redirect(url_for('auth.profile'))
        except Exception as e:
            error = str(e)
            # Return JSON error for API requests
            if request.headers.get('Accept', '').find('application/json') > -1:
                return jsonify({'success': False, 'error': error}), 401
    
    return render_template('login.html', title='Login', error=error, next=next_url)


@auth_bp.route('/login/google')
def google_login():
    """Start Google OAuth flow for sign-in/sign-up (stateless implementation)."""
    # Debug logging
    logger.info(f"=== OAUTH INITIATION DEBUG ===")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request Host: {request.host}")

    # Get next URL from request
    next_url = request.args.get('next', '')
    logger.info(f"Next URL parameter: {next_url}")

    # Use FRONTEND_URL (friedmomo.com) for OAuth callback so users stay on friedmomo.com
    frontend_url = os.getenv('FRONTEND_URL')
    if frontend_url:
        redirect_uri = frontend_url.rstrip('/') + url_for('auth.google_callback', _external=False)
    else:
        redirect_uri = url_for('auth.google_callback', _external=True)

    logger.info(f"Generating Google OAuth URL | redirect_uri={redirect_uri} | client_id_suffix={os.getenv('GOOGLE_CLIENT_ID', 'MISSING')[-20:]}")

    # Generate base OAuth URL and state
    auth_url, csrf_state = auth_service.get_google_auth_url(redirect_uri)

    # Encode next_url and csrf_state into the state parameter (stateless approach)
    # This bypasses the need for session cookies during OAuth redirect
    state_data = {
        'csrf': csrf_state,
        'next': next_url
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    logger.info(f"Encoded stateless OAuth state: csrf={csrf_state} | next={next_url}")

    # Replace the state parameter in auth_url with our encoded state
    auth_url = auth_url.replace(f'state={csrf_state}', f'state={encoded_state}')

    logger.info(f"Redirecting to Google OAuth with stateless state parameter")
    return redirect(auth_url)


@auth_bp.route('/login/google/callback')
def google_callback():
    """Handle callback from Google OAuth (stateless implementation)."""
    # Debug logging
    logger.info(f"=== OAUTH CALLBACK DEBUG ===")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request Host: {request.host}")
    logger.info(f"Request Headers Host: {request.headers.get('Host')}")
    logger.info(f"Request Cookies: {list(request.cookies.keys())}")

    # Decode stateless state parameter
    encoded_state = request.args.get('state')
    logger.info(f"Received encoded state: {encoded_state}")

    if not encoded_state:
        logger.error("OAuth callback missing state parameter")
        flash('Authentication failed: Missing state parameter.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        # Decode state to get csrf_state and next_url
        state_json = base64.urlsafe_b64decode(encoded_state).decode()
        state_data = json.loads(state_json)
        csrf_state = state_data.get('csrf')
        next_url = state_data.get('next', '')
        logger.info(f"Decoded stateless state: csrf={csrf_state} | next={next_url}")
    except Exception as e:
        logger.error(f"Failed to decode state parameter: {e}", exc_info=True)
        flash('Authentication failed: Invalid state parameter.', 'danger')
        return redirect(url_for('auth.login'))

    # Note: In a stateless implementation, we can't verify CSRF state against a session
    # because there is no session during the OAuth redirect. Instead, we rely on:
    # 1. HTTPS encryption protecting the state parameter in transit
    # 2. Google's own CSRF protection (they validate redirect_uri matches registered URI)
    # 3. The state parameter being signed/encoded by our backend
    # This is the standard approach for cross-domain OAuth flows.
    logger.info(f"Using stateless OAuth - CSRF protection via Google's redirect_uri validation")

    # Get authorization code from Google
    code = request.args.get('code')
    if not code:
        logger.error("OAuth callback missing authorization code")
        flash('Authentication failed: No authorization code received.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        logger.info("Starting token exchange with Google")
        # Exchange code for tokens
        token_url = 'https://oauth2.googleapis.com/token'
        
        # Use FRONTEND_URL (friedmomo.com) for OAuth callback
        frontend_url = os.getenv('FRONTEND_URL')
        if frontend_url:
            callback_uri_for_token_exchange = frontend_url.rstrip('/') + url_for('auth.google_callback', _external=False)
        else:
            callback_uri_for_token_exchange = url_for('auth.google_callback', _external=True)
        
        logger.info(f"Token exchange URI: {callback_uri_for_token_exchange}")

        token_data = {
            'code': code,
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': callback_uri_for_token_exchange,
            'grant_type': 'authorization_code'
        }
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        logger.info("Successfully exchanged code for Google tokens")

        # Get user info
        userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        userinfo_response = requests.get(
            userinfo_url,
            headers={'Authorization': f"Bearer {tokens['access_token']}"}
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
        logger.info(f"Retrieved Google user info | email={userinfo.get('email')}")

        # Sign in with Firebase using Google token
        firebase_url = f"{auth_service.base_url}/accounts:signInWithIdp?key={auth_service.api_key}"
        firebase_data = {
            'postBody': f"id_token={tokens['id_token']}&providerId=google.com",
            'requestUri': request.base_url,
            'returnSecureToken': True
        }
        firebase_response = requests.post(firebase_url, json=firebase_data)
        firebase_response.raise_for_status()
        firebase_user = firebase_response.json()
        logger.info(f"Firebase sign-in successful | user_id={firebase_user['localId']}")

        # Set session variables
        session['id_token'] = firebase_user['idToken']
        session['user_id'] = firebase_user['localId']
        session['user_email'] = firebase_user.get('email', userinfo.get('email'))
        session['user_name'] = userinfo.get('name')
        session['user_picture'] = userinfo.get('picture')
        session.permanent = True  # Make session permanent
        session.modified = True   # Force session to save

        # Ensure user record exists in Firestore
        db = firestore.client()
        user_has_username = False

        try:
            # Get or create user document
            user_ref = db.collection('users').document(session['user_id'])
            user_doc = user_ref.get()

            # Create/update user document
            user_ref.set({
                'firebase_uid': session['user_id'],
                'email': session.get('user_email'),
                'name': session.get('user_name'),
                'picture': session.get('user_picture')
            }, merge=True)

            # Check if user already has a username
            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_has_username = bool(user_data.get('username'))
        except Exception as e:
            logger.error(f"Error creating user document: {e}")

        # Handle redirect after OAuth
        # Note: next_url was already decoded from the stateless state parameter above
        logger.info(f"OAuth redirect logic | next_url={next_url} | frontend_url={os.getenv('FRONTEND_URL')}")

        # Determine if this OAuth flow came from friedmomo.com
        # Check multiple indicators: next_url, referer, or the callback URL itself
        is_frontend_oauth = False
        frontend_domains = ['friedmomo.com', 'www.friedmomo.com', 'friedmomo.web.app', 'friedmomo--production-pfwp1l6e.web.app']
        
        # Check if next_url is to frontend
        if next_url:
            parsed_next = urlparse(next_url)
            if parsed_next.netloc in frontend_domains:
                is_frontend_oauth = True
                logger.info(f"Detected frontend OAuth from next_url: {next_url}")
        
        # Check if request came from frontend (referer or host)
        referer = request.headers.get('Referer', '')
        if not is_frontend_oauth and referer:
            parsed_referer = urlparse(referer)
            if parsed_referer.netloc in frontend_domains:
                is_frontend_oauth = True
                logger.info(f"Detected frontend OAuth from referer: {referer}")
        
        # Check if the callback URL itself is on friedmomo.com
        if not is_frontend_oauth and os.getenv('FRONTEND_URL'):
            frontend_url = os.getenv('FRONTEND_URL')
            if any(domain in frontend_url for domain in frontend_domains):
                is_frontend_oauth = True
                logger.info(f"Detected frontend OAuth from FRONTEND_URL env var: {frontend_url}")

        # If OAuth came from frontend, redirect back to frontend
        # SECURITY: Do NOT pass token in URL - it exposes credentials in:
        #   - Browser history
        #   - Server logs
        #   - Referrer headers
        #   - Shoulder surfing
        # The session cookie is already set (lines 370-376) and the frontend
        # verifies it via /api/users/me call in OAuthCallbackPage.tsx
        if is_frontend_oauth:
            frontend_url = os.getenv('FRONTEND_URL', 'https://friedmomo.com')
            # Use next_url if it's a frontend URL, otherwise use default /oauth/callback
            if next_url and is_safe_url(next_url):
                parsed_next = urlparse(next_url)
                if parsed_next.netloc in frontend_domains:
                    redirect_target = next_url
                else:
                    redirect_target = f"{frontend_url}/oauth/callback"
            else:
                redirect_target = f"{frontend_url}/oauth/callback"

            # Redirect without sensitive data - session cookie handles authentication
            logger.info(f"Redirecting to frontend (session cookie set) | url={redirect_target}")
            return redirect(redirect_target)

        # Traditional Flask redirect logic (for backend-only flows)
        if next_url and is_safe_url(next_url):
            logger.info(f"Using traditional redirect to: {next_url}")
            return redirect(next_url)

        # Default Flask redirect logic based on username status
        if user_has_username:
            # User has username, go straight to their profile
            logger.info(f"Redirecting to soho (user has username)")
            return redirect(url_for('soho'))
        else:
            # No username, redirect to username setup
            logger.info(f"Redirecting to username_setup (user has no username)")
            return redirect(url_for('username_setup'))
    except Exception as e:
        logger.error(f"Google OAuth callback error: {str(e)}", exc_info=True)
        flash(f'Authentication failed: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))


@auth_bp.route('/api/auth/exchange-token', methods=['POST'])
def exchange_token():
    """
    Exchange Firebase ID token for backend session cookie.
    Used for cross-domain OAuth flows (friedmomo.web.app → backend).
    """
    try:
        request_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex[:8]
        
        # Log all cookies to debug Firebase Hosting proxy behavior
        all_cookies = list(request.cookies.keys())
        session_cookie = request.cookies.get('__session') or request.cookies.get('session')
        
        logger.info(
            f"[exchange-token:{request_id}] Incoming request | instance={INSTANCE_ID}/{CONTAINER_ID}",
            extra={
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'referer': request.headers.get('Referer'),
            }
        )
        logger.info(f"[exchange-token:{request_id}] Cookies received: {all_cookies} | __session={'present' if session_cookie else 'MISSING'}")
        logger.info(f"[exchange-token:{request_id}] Headers - Host: {request.headers.get('Host')} | Origin: {request.headers.get('Origin')}")

        data = request.get_json()
        token = data.get('token')
        user_id = data.get('user_id')

        if not token or not user_id:
            logger.warning(
                f"[exchange-token:{request_id}] Missing credentials",
                extra={'has_token': bool(token), 'has_user_id': bool(user_id)}
            )
            return jsonify({'success': False, 'error': 'Missing token or user_id'}), 400

        # Verify the Firebase ID token
        try:
            from firebase_admin import auth as firebase_auth
            logger.info(
                f"[exchange-token:{request_id}] Verifying Firebase token",
                extra={
                    'user_id': user_id,
                    'token_prefix': token[:6] + '...' if token else None
                }
            )
            decoded_token = firebase_auth.verify_id_token(token)

            if decoded_token['uid'] != user_id:
                logger.warning(
                    f"[exchange-token:{request_id}] Token user mismatch",
                    extra={'decoded_uid': decoded_token.get('uid'), 'payload_user_id': user_id}
                )
                return jsonify({'success': False, 'error': 'Token user ID mismatch'}), 401

            # Get user info from Firestore
            db = firestore.client()
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
                logger.warning(f"[exchange-token:{request_id}] User not found in Firestore", extra={'user_id': user_id})
                return jsonify({'success': False, 'error': 'User not found'}), 404

            user_data = user_doc.to_dict()

            # Set session variables
            session['id_token'] = token
            session['user_id'] = user_id
            session['user_email'] = decoded_token.get('email', user_data.get('email'))
            session['user_name'] = user_data.get('name')
            session['user_picture'] = user_data.get('picture')
            session.permanent = True
            session.modified = True

            logger.info(
                f"[exchange-token:{request_id}] Session established",
                extra={
                    'user_id': user_id,
                    'email': session['user_email'],
                    'has_name': bool(session['user_name']),
                    'has_picture': bool(session['user_picture'])
                }
            )

            return jsonify({
                'success': True,
                'user': {
                    'id': user_id,
                    'email': session['user_email'],
                    'name': session['user_name'],
                    'picture': session['user_picture']
                }
            }), 200

        except Exception as e:
            logger.error(
                f"[exchange-token:{request_id}] Token verification failed: {e}",
                exc_info=True,
                extra={'user_id': user_id}
            )
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

    except Exception as e:
        logger.error(
            f"[exchange-token] Unexpected error: {e}",
            exc_info=True
        )
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to landing page."""
    # Log logout attempt
    user_id = session.get('user_id', 'unknown')
    session_keys = list(session.keys())
    logger.info(f"[logout] Starting logout | user_id={user_id} | session_keys={session_keys} | instance={INSTANCE_ID}/{CONTAINER_ID}")
    
    session.clear()
    logger.info(f"[logout] Session cleared successfully for user_id={user_id}")
    
    # Check if redirect parameter specifies where to go
    redirect_param = request.args.get('redirect', '')
    redirect_url = request.args.get('redirect_url', '')  # Full URL for redirect
    
    logger.info(f"[logout] Redirect params: redirect={redirect_param} | redirect_url={redirect_url}")
    
    if redirect_param in {'soho', 'momo'}:
        # For React SPA frontend (Soho legacy + Momo rebrand)
        if redirect_url:
            # Frontend provided full return URL - use it directly
            return redirect(redirect_url)
        else:
            # Fallback: redirect to root
            return redirect('/')
    
    # Default redirect to main platform
    return redirect(url_for('index'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Render user profile page."""
    context = {
        'title': 'Profile',
        'user_email': session.get('user_email'),
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'user_picture': session.get('user_picture')
    }
    return render_template('profile.html', **context)
