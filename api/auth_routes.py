"""Routes for user authentication, including Google and Instagram OAuth."""
import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import requests

from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'id_token' not in session:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return wrapper


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            data = auth_service.signup_email_password(email, password)
            session['id_token'] = data.get('idToken')
            session['user_email'] = data.get('email')
            session['user_id'] = data.get('localId')

            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            else:
                return redirect(url_for('deeplink.manage_short_links_page'))
        except Exception as e:
            error = str(e)
    return render_template('signup.html', title='Sign Up', error=error)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            data = auth_service.login_email_password(email, password)
            session['id_token'] = data.get('idToken')
            session['user_email'] = data.get('email')
            session['user_id'] = data.get('localId')

            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            else:
                return redirect(url_for('deeplink.manage_short_links_page'))
        except Exception as e:
            error = str(e)
    return render_template('login.html', title='Login', error=error)


@auth_bp.route('/login/google')
def google_login():
    """Start Google OAuth flow for sign-in/sign-up."""
    prod_url_base = os.getenv('PRODUCTION_URL')
    if prod_url_base:
        # Ensure no trailing slash in prod_url_base and leading slash in callback path
        redirect_uri = prod_url_base.rstrip('/') + url_for('auth.google_callback', _external=False)
    else:
        redirect_uri = url_for('auth.google_callback', _external=True)
    
    auth_url, state = auth_service.get_google_auth_url(redirect_uri)
    session['oauth_state'] = state

    next_url = request.args.get('next')
    if next_url and next_url.startswith('/'):
        session['post_login_redirect'] = next_url
    else:
        # Clear any previous value if next_url is not valid or not present
        session.pop('post_login_redirect', None)

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

        post_login_redirect_url = session.pop('post_login_redirect', None)
        if post_login_redirect_url and post_login_redirect_url.startswith('/'):
            return redirect(post_login_redirect_url)
        else:
            return redirect(url_for('deeplink.manage_short_links_page'))
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
