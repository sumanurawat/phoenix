"""Routes for user authentication, including Google and Instagram OAuth."""
import os
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
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


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
            # Redirect to intended page or default
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            else:
                return redirect(url_for('auth.profile'))
        except Exception as e:
            error = str(e)
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
            # Redirect to intended page or default
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            else:
                return redirect(url_for('auth.profile'))
        except Exception as e:
            error = str(e)
    return render_template('login.html', title='Login', error=error, next=next_url)


@auth_bp.route('/login/google')
def google_login():
    """Start Google OAuth flow for sign-in/sign-up."""
    # Store the next URL in session for after OAuth
    next_url = request.args.get('next')
    if next_url:
        session['oauth_next_url'] = next_url
    
    prod_url_base = os.getenv('PRODUCTION_URL')
    if prod_url_base:
        # Ensure no trailing slash in prod_url_base and leading slash in callback path
        redirect_uri = prod_url_base.rstrip('/') + url_for('auth.google_callback', _external=False)
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
        
        prod_url_base = os.getenv('PRODUCTION_URL')
        if prod_url_base:
            callback_uri_for_token_exchange = prod_url_base.rstrip('/') + url_for('auth.google_callback', _external=False)
        else:
            callback_uri_for_token_exchange = url_for('auth.google_callback', _external=True)

        token_data = {
            'code': code,
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': callback_uri_for_token_exchange, # Use the potentially overridden URI
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

        # Ensure user record and free subscription exist
        try:
            StripeService().ensure_free_subscription(session['user_id'], session.get('user_email'))
            try:
                db = firestore.client()
                db.collection('users').document(session['user_id']).set({
                    'firebase_uid': session['user_id'],
                    'email': session.get('user_email'),
                    'name': session.get('user_name'),
                    'picture': session.get('user_picture')
                }, merge=True)
            except Exception:
                pass
        except Exception:
            pass
        # Handle redirect after OAuth
        next_url = session.pop('oauth_next_url', None)
        if next_url and is_safe_url(next_url):
            return redirect(next_url)
        else:
            # Redirect to username setup (will redirect to soho if username exists)
            return redirect(url_for('username_setup'))
    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
def logout():
    session.clear()
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
