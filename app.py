"""
Friedmomo Backend Application

Flask backend for friedmomo.com - AI-powered image and video generation platform.
Handles authentication, token management, content creation, and user profiles.
"""
import os
import logging
import secrets
from functools import wraps
from flask import Flask, render_template, session, request, redirect, url_for, flash, abort, jsonify, send_from_directory
from flask_cors import CORS
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configurations
from config.settings import (
    SECRET_KEY, FLASK_ENV, FLASK_DEBUG,
    SESSION_TYPE, SESSION_PERMANENT, SESSION_USE_SIGNER,
    SESSION_FILE_DIR, SESSION_FILE_THRESHOLD
)

# Initialize Firebase Admin SDK FIRST (before importing services)
import firebase_admin
from firebase_admin import credentials

try:
    # Check if Firebase app is already initialized
    if not firebase_admin._apps:
        # Try service account file first (for development)
        try:
            cred = credentials.Certificate('firebase-credentials.json')
            firebase_admin.initialize_app(cred)
            logger.debug("Firebase Admin SDK initialized with service account.")
        except FileNotFoundError:
            # Fallback to Application Default Credentials (for production)
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            logger.debug("Firebase Admin SDK initialized with Application Default Credentials.")
    else:
        logger.debug("Firebase Admin SDK already initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

# Import API routes (AFTER Firebase initialization)
from api.auth_routes import auth_bp, login_required
from api.stats_routes import stats_bp
from api.stripe_routes import stripe_bp, subscription_bp
from api.token_routes import token_bp
from api.socials_routes import socials_bp
from api.image_routes import image_bp
from api.generation_routes import generation_bp  # Unified creation endpoint (images + videos for Friedmomo)
from api.user_routes import user_bp
from api.feed_routes import feed_bp
from api.follow_routes import follow_bp

# Import services (AFTER Firebase initialization)
from config.app_display_names import get_display_name

logger = logging.getLogger(__name__)


def require_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def create_app():
    """Create and configure the Flask application."""
    # Initialize Flask app
    app = Flask(__name__)

    # Ensure Flask generates correct external URLs behind a proxy (Cloud Run)
    # This makes url_for(..., _external=True) use the forwarded scheme/host
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    # Prefer HTTPS for external URLs
    app.config['PREFERRED_URL_SCHEME'] = 'https'

    # Enable CORS for Momo frontend (production + local dev)
    default_origins = 'https://friedmomo.com,https://www.friedmomo.com,https://friedmomo.web.app,http://localhost:5173'
    allowed_origins_env = os.getenv('MOMO_ALLOWED_ORIGINS') or os.getenv('SOHO_ALLOWED_ORIGINS')
    allowed_origins = (allowed_origins_env or default_origins).split(',')
    allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
        expose_headers=['X-CSRF-Token'],
        allow_headers=['Content-Type', 'X-CSRF-Token', 'X-Requested-With', 'Authorization']
    )

    # --- Rate Limiting ---
    # Protects against brute force, DoS, and enumeration attacks
    # Uses in-memory storage (resets on container restart - acceptable for Cloud Run)
    def get_rate_limit_key():
        """Get rate limit key - prefer user_id if authenticated, else IP."""
        if 'user_id' in session:
            return f"user:{session['user_id']}"
        return get_remote_address()

    limiter = Limiter(
        app=app,
        key_func=get_rate_limit_key,
        default_limits=["200 per day", "50 per hour"],  # Default for all routes
        storage_uri="memory://",  # In-memory (resets on restart)
    )
    # Store limiter on app for use in blueprints
    app.limiter = limiter

    # Configure application - Set ENV first
    app.config["ENV"] = FLASK_ENV
    app.config["DEBUG"] = FLASK_DEBUG
    app.config["SECRET_KEY"] = SECRET_KEY
    
    # Security check after ENV is set
    if app.config["ENV"] != "development" and app.config["SECRET_KEY"] == "default-secret-key":
        raise RuntimeError("SECURITY CRITICAL: Default SECRET_KEY is not allowed in production/staging. Please set a strong, unique SECRET_KEY in the environment configuration.")
    
    # Configure session - Use Cache Service for Cloud Run compatibility
    # NOTE: Filesystem sessions don't work on Cloud Run (ephemeral containers)
    # We use Firestore-backed sessions via our cache service instead
    from services.cache_service.flask_adapter import CacheSessionInterface

    app.session_interface = CacheSessionInterface(
        key_prefix='friedmomo:session:',
        permanent_lifetime=2592000  # 30 days
    )

    # Configure session cookies for cross-domain support (friedmomo.com → backend)
    # In development, disable Secure flag so cookies work over HTTP
    is_development = app.config.get('ENV') == 'development' or app.config.get('DEBUG')
    app.config["SESSION_COOKIE_SECURE"] = not is_development  # Require HTTPS only in production
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JS access
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Lax for same-site (Firebase proxy makes all requests same-site)
    # Don't set cookie domain - let it default to the request domain
    # This way cookies work whether accessed via friedmomo.com (Firebase proxy) or run.app (direct)
    app.config["SESSION_COOKIE_DOMAIN"] = None
    # IMPORTANT: Firebase Hosting only forwards cookies named '__session'
    # All other cookies are stripped when proxying to Cloud Run/Cloud Functions
    # See: https://firebase.google.com/docs/hosting/manage-cache#using_cookies
    app.config["SESSION_COOKIE_NAME"] = "__session"  # Must be __session for Firebase Hosting proxy
    app.config["PERMANENT_SESSION_LIFETIME"] = 2592000  # 30 days in seconds

    # --- Centralized CSRF Protection ---
    from middleware.csrf_protection import csrf
    csrf.init_app(app)
    
    # Configure CSRF based on environment
    app.config['DISABLE_CSRF'] = os.getenv('DISABLE_CSRF', '0') == '1'
    
    # Expose CSRF token via header for frontend
    @app.after_request
    def add_csrf_header(resp):
        token = session.get('csrf_token')
        if token:
            resp.headers['X-CSRF-Token'] = token
        return resp
    
    # Make session accessible in templates
    @app.context_processor
    def inject_session():
        return {'session': session}
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(stripe_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(token_bp)
    app.register_blueprint(socials_bp)
    app.register_blueprint(image_bp)
    app.register_blueprint(generation_bp)  # Unified draft-first creation with Cloud Run Jobs (Friedmomo)
    app.register_blueprint(user_bp)  # Phase 4: User profiles & usernames
    app.register_blueprint(feed_bp)  # Phase 4: Social feed & likes
    app.register_blueprint(follow_bp)  # Phase 5: Follow feature

    # --- Apply Rate Limits to Sensitive Endpoints ---
    # These limits protect against brute force, enumeration, and DoS attacks
    limiter.limit("30 per minute")(app.view_functions['token.get_balance'])
    limiter.limit("5 per hour")(app.view_functions['token.transfer_tokens'])
    limiter.limit("10 per minute")(app.view_functions['auth.login'])
    limiter.limit("10 per minute")(app.view_functions['auth.signup'])
    limiter.limit("20 per minute")(app.view_functions['auth.google_login'])

    # Username enforcement middleware (Phase 4)
    @app.before_request
    def enforce_username_setup():
        """Redirect logged-in users without usernames to username setup page."""
        # Skip for non-authenticated users
        if 'user_id' not in session:
            return None

        # List of routes that don't require username (allow these)
        exempt_routes = [
            'auth.logout',
            'username_setup',
            'static',
            'auth.login',
            'auth.signup',
            'auth.google_login',
            'auth.google_callback',
        ]

        # Also exempt all API routes (they handle their own auth)
        if request.path.startswith('/api/'):
            return None

        # Check if current endpoint is exempt
        if request.endpoint in exempt_routes:
            return None

        # Check if user has a username
        try:
            from firebase_admin import firestore
            db = firestore.client()
            user_ref = db.collection('users').document(session['user_id'])
            user_doc = user_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                if not user_data.get('username'):
                    # User doesn't have username - redirect to setup
                    if request.endpoint != 'username_setup':
                        return redirect(url_for('username_setup'))
        except Exception as e:
            logger.error(f"Error checking username in middleware: {e}")

        return None

    # Inject app display names into templates for header
    @app.context_processor
    def inject_app_display_name():
        try:
            name = get_display_name(
                path=request.path,
                blueprint=getattr(request, 'blueprint', None),
                endpoint=getattr(request, 'endpoint', None)
            )
        except Exception:
            name = None
        return {'app_display_name': name}
    
    # Define routes
    @app.route('/')
    def index():
        """Redirect to the main Friedmomo application."""
        # In development, redirect to local frontend; in production, redirect to friedmomo.com
        if app.config.get('ENV') == 'development' or app.config.get('DEBUG'):
            return redirect('http://localhost:5173')
        return redirect('https://friedmomo.com')


    
    @app.route('/buy-tokens')
    @require_auth
    def buy_tokens_page():
        """Render the Buy Tokens page - requires authentication."""
        return render_template('buy_tokens.html',
                           title='Buy Tokens')

    @app.route('/transaction-history')
    @require_auth
    def transaction_history_page():
        """Render the Transaction History page - requires authentication."""
        return render_template('transaction_history.html',
                           title='Transaction History')

    @app.route('/image-generator')
    @login_required
    def image_generator():
        """Render the Image Generator page (requires login)."""
        return render_template('image_generator.html', title='Image Generator - Phoenix AI')

    @app.route('/username-setup')
    @login_required
    def username_setup():
        """Render the Username Setup page (Phase 4 - requires login)."""
        return render_template('username_setup.html', title='Create Your Username')

    @app.route('/create')
    @login_required
    def create_page():
        """Render the Create page for image generation (Phase 4 - requires login)."""
        return render_template('create.html', title='Create - Phoenix AI')

    @app.route('/explore')
    def explore_page():
        """Render the Explore feed page (Phase 4 - public)."""
        return render_template('explore.html', title='Explore - Phoenix AI')

    @app.route('/users/<username>')
    def public_profile(username):
        """Render public profile page for a user (Phase 4 - public)."""
        return render_template('profile.html', username=username)

    @app.route('/soho')
    @login_required
    def soho():
        """Redirect to the signed-in user's Momo profile page (Phase 4 - requires login)."""
        from firebase_admin import firestore
        try:
            db = firestore.client()
            user_ref = db.collection('users').document(session['user_id'])
            user_doc = user_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                username = user_data.get('username')
                if username:
                    return redirect(url_for('soho_public_profile', username=username))
        except Exception as e:
            logger.error(f"Error redirecting to user profile: {e}")

        # Fallback to username setup if something goes wrong
        return redirect(url_for('username_setup'))

    @app.route('/soho/explore')
    def soho_explore_page():
        """Render the public Explore feed for the Momo social platform (Phase 4 - public)."""
        return render_template('soho_explore.html', title='Explore - Momo')

    @app.route('/soho/<username>')
    def soho_public_profile(username):
        """Render a public Momo profile page for a specific user (Phase 4 - public)."""
        # Use profile.html which has drafts support
        return render_template('profile.html', username=username, title=f'@{username} - Momo')

    # ========================================
    # React Frontend Routes (Momo SPA)
    # ========================================
    
    @app.route('/momo')
    @app.route('/momo/<path:path>')
    def serve_momo_frontend(path=''):
        """
        Serve the React frontend (Momo) as a Single Page Application.
        All routes are handled by React Router on the client side.
        """
        # If requesting a specific file (like .js, .css, .svg), serve it directly
        if path and os.path.exists(os.path.join('static/momo', path)):
            return send_from_directory('static/momo', path)
        
        # Otherwise, serve index.html and let React Router handle the routing
        return send_from_directory('static/momo', 'index.html')

    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    os.makedirs(SESSION_FILE_DIR, exist_ok=True)
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=8080)
