"""Routes for user authentication, including Google and Instagram OAuth."""
import os
import logging
from functools import wraps
from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import requests

from services.auth_service import AuthService
from services.stripe_service import StripeService
from firebase_admin import firestore
from middleware.csrf_protection import csrf_protect

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()
logger = logging.getLogger(__name__)


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
            
            # Ensure user record and free subscription exist
            try:
                StripeService().ensure_free_subscription(session['user_id'], session.get('user_email'))
                # also ensure a minimal users collection record
                try:
                    db = firestore.client()
                    db.collection('users').document(session['user_id']).set({
                        'firebase_uid': session['user_id'],
                        'email': session.get('user_email')
                    }, merge=True)
                except Exception:
                    pass
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
            
            # Ensure user record and free subscription exist
            try:
                StripeService().ensure_free_subscription(session['user_id'], session.get('user_email'))
                try:
                    db = firestore.client()
                    db.collection('users').document(session['user_id']).set({
                        'firebase_uid': session['user_id'],
                        'email': session.get('user_email')
                    }, merge=True)
                except Exception:
                    pass
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
    """Start Google OAuth flow for sign-in/sign-up."""
    # Store the next URL in session for after OAuth
    next_url = request.args.get('next')
    if next_url:
        session['oauth_next_url'] = next_url
    
    # Use FRONTEND_URL (friedmomo.com) for OAuth callback so users stay on friedmomo.com
    frontend_url = os.getenv('FRONTEND_URL')
    if frontend_url:
        redirect_uri = frontend_url.rstrip('/') + url_for('auth.google_callback', _external=False)
    else:
        redirect_uri = url_for('auth.google_callback', _external=True)
    
    auth_url, state = auth_service.get_google_auth_url(redirect_uri)
    session['oauth_state'] = state
    return redirect(auth_url)


@auth_bp.route('/login/google/callback')
def google_callback():
    """Handle callback from Google OAuth."""
    # Verify state to prevent CSRF
    state = session.pop('oauth_state', None)
    if not state or state != request.args.get('state'):
        flash('Authentication failed: Invalid state parameter.', 'danger')
        return redirect(url_for('auth.login'))

    # Get authorization code from Google
    code = request.args.get('code')
    if not code:
        flash('Authentication failed: No authorization code received.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        # Exchange code for tokens
        token_url = 'https://oauth2.googleapis.com/token'
        
        # Use FRONTEND_URL (friedmomo.com) for OAuth callback
        frontend_url = os.getenv('FRONTEND_URL')
        if frontend_url:
            callback_uri_for_token_exchange = frontend_url.rstrip('/') + url_for('auth.google_callback', _external=False)
        else:
            callback_uri_for_token_exchange = url_for('auth.google_callback', _external=True)

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

        # Get user info
        userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        userinfo_response = requests.get(
            userinfo_url,
            headers={'Authorization': f"Bearer {tokens['access_token']}"}
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

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

        # Set session variables
        session['id_token'] = firebase_user['idToken']
        session['user_id'] = firebase_user['localId']
        session['user_email'] = firebase_user.get('email', userinfo.get('email'))
        session['user_name'] = userinfo.get('name')
        session['user_picture'] = userinfo.get('picture')
        session.permanent = True  # Make session permanent
        session.modified = True   # Force session to save

        # Ensure user record and free subscription exist
        db = firestore.client()
        user_has_username = False

        try:
            StripeService().ensure_free_subscription(session['user_id'], session.get('user_email'))
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
        except Exception as e:
            logger.error(f"Error ensuring free subscription: {e}")

        # Handle redirect after OAuth
        next_url = session.pop('oauth_next_url', None)

        # Check if redirecting to frontend (cross-domain)
        if next_url and is_safe_url(next_url):
            parsed_next = urlparse(next_url)
            frontend_domains = ['friedmomo.com', 'www.friedmomo.com', 'friedmomo.web.app', 'localhost:5173']

            if parsed_next.netloc in frontend_domains:
                # Cross-domain redirect: pass Firebase ID token in URL
                # Frontend will use this token to establish its session
                separator = '&' if '?' in next_url else '?'
                redirect_url = f"{next_url}{separator}token={firebase_user['idToken']}&user_id={session['user_id']}"
                return redirect(redirect_url)
            else:
                # Same-domain redirect: use session as normal
                return redirect(next_url)

        # Default Flask redirect logic based on username status
        if user_has_username:
            # User has username, go straight to their profile
            return redirect(url_for('soho'))
        else:
            # No username, redirect to username setup
            return redirect(url_for('username_setup'))
    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))


@auth_bp.route('/api/auth/exchange-token', methods=['POST'])
def exchange_token():
    """
    Exchange Firebase ID token for backend session cookie.
    Used for cross-domain OAuth flows (friedmomo.web.app → backend).
    """
    try:
        data = request.get_json()
        token = data.get('token')
        user_id = data.get('user_id')

        if not token or not user_id:
            return jsonify({'success': False, 'error': 'Missing token or user_id'}), 400

        # Verify the Firebase ID token
        try:
            from firebase_admin import auth as firebase_auth
            decoded_token = firebase_auth.verify_id_token(token)

            if decoded_token['uid'] != user_id:
                return jsonify({'success': False, 'error': 'Token user ID mismatch'}), 401

            # Get user info from Firestore
            db = firestore.client()
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
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
            logger.error(f"Token verification failed: {e}")
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to landing page."""
    session.clear()
    
    # Check if redirect parameter specifies where to go
    redirect_param = request.args.get('redirect', '')
    redirect_url = request.args.get('redirect_url', '')  # Full URL for redirect
    
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
