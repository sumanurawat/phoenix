"""
Phoenix AI Platform Application

This is the main application file that sets up the Flask application,
registers routes, and initializes services.
"""
import os
import logging
import secrets
from functools import wraps
from flask import Flask, render_template, session, request, redirect, url_for, flash, abort, jsonify, jsonify, send_from_directory
from flask_cors import CORS
from flask_session import Session
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
            logger.info("Firebase Admin SDK initialized with service account.")
        except FileNotFoundError:
            # Fallback to Application Default Credentials (for production)
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized with Application Default Credentials.")
    else:
        logger.info("Firebase Admin SDK already initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

# Import API routes (AFTER Firebase initialization)
from api.chat_routes import chat_bp
from api.enhanced_chat_routes import enhanced_chat_bp
from api.deeplink_routes import deeplink_bp
from api.auth_routes import auth_bp, login_required
from api.stats_routes import stats_bp
from api.video_routes import video_bp
from api.stripe_routes import stripe_bp, subscription_bp
from api.token_routes import token_bp
from api.socials_routes import socials_bp
from api.image_routes import image_bp
from api.generation_routes import generation_bp  # Unified creation endpoint
from api.user_routes import user_bp
from api.feed_routes import feed_bp

# Import services (AFTER Firebase initialization)
from services.chat_service import ChatService
from services.enhanced_chat_service import EnhancedChatService
from services.subscription_middleware import (
    init_subscription_context, 
    subscription_context_processor
)
from config.app_display_names import get_display_name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (only once, globally)
try:
    # Check if Firebase app is already initialized
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
    else:
        logger.info("Firebase Admin SDK already initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

# Service instances (lazy-loaded)
_chat_service = None
_enhanced_chat_service = None

def get_chat_service():
    """Get or create ChatService instance (lazy initialization)."""
    global _chat_service
    if _chat_service is None:
        logger.info("Initializing ChatService...")
        _chat_service = ChatService()
    return _chat_service

def get_enhanced_chat_service():
    """Get or create EnhancedChatService instance (lazy initialization)."""
    global _enhanced_chat_service
    if _enhanced_chat_service is None:
        logger.info("Initializing EnhancedChatService...")
        _enhanced_chat_service = EnhancedChatService()
    return _enhanced_chat_service

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
    app.config["SESSION_COOKIE_SECURE"] = True  # Require HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JS access
    app.config["SESSION_COOKIE_SAMESITE"] = "None"  # Allow cross-domain cookies
    # Set cookie domain based on environment - use .friedmomo.com for production
    if os.getenv('FLASK_ENV') == 'development':
        app.config["SESSION_COOKIE_DOMAIN"] = None  # localhost
    else:
        app.config["SESSION_COOKIE_DOMAIN"] = ".friedmomo.com"  # Works for friedmomo.com and all subdomains
    app.config["SESSION_COOKIE_NAME"] = "session"  # Cookie name
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
    app.register_blueprint(chat_bp)
    app.register_blueprint(enhanced_chat_bp)
    app.register_blueprint(deeplink_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(stripe_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(token_bp)
    app.register_blueprint(socials_bp)
    app.register_blueprint(image_bp)
    app.register_blueprint(generation_bp)  # Unified draft-first creation with Cloud Run Jobs
    app.register_blueprint(user_bp)  # Phase 4: User profiles & usernames
    app.register_blueprint(feed_bp)  # Phase 4: Social feed & likes
    
    # Setup subscription middleware
    @app.before_request
    def setup_subscription_context():
        """Initialize subscription context for each request."""
        init_subscription_context()

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

    # Add subscription context processor for templates
    app.context_processor(subscription_context_processor)

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
        """Render the main index page."""
        return render_template('index.html', title='Phoenix AI Platform')

    @app.route('/derplexity')
    @login_required
    def derplexity():
        """Render the Derplexity chat interface with persistent conversations."""
        return render_template('derplexity.html', 
                            title='Derplexity Chat')
    
    @app.route('/phase4-test')
    @login_required
    def phase4_test():
        """Phase 4 API testing page."""
        return render_template('phase4_test.html', title='Phase 4 API Test')

    @app.route('/socials')
    @login_required
    def socials_page():
        """Render the Social Media Timeline page."""
        return render_template('socials.html', title='Social Timeline - Phoenix AI')
    
    @app.route('/blogs')
    def blogs():
        """Render the Technical Blogs page."""
        return render_template('blogs.html', 
                           title='Technical Blogs - Sumanu Rawat')
    
    @app.route('/dashboard')
    @require_auth
    def dashboard_page():
        """Render the Dashboard page - requires authentication."""
        return render_template('dashboard.html', 
                           title='My Dashboards',
                           user_name=session.get('user_name'),
                           user_email=session.get('user_email'))
    
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

    # Token purchase success/cancel pages removed - handled by friedmomo.com frontend
    

    @app.route('/api/test-grok', methods=['GET'])
    def test_grok_api():
        """Test endpoint to diagnose Grok API issues."""
        try:
            from flask import jsonify
            from services.enhanced_llm_service import EnhancedLLMService, ModelProvider
            import os
            
            # Check environment
            grok_key = os.getenv('GROK_API_KEY')
            
            diagnostics = {
                "grok_api_key_present": bool(grok_key),
                "grok_api_key_length": len(grok_key) if grok_key else 0,
                "grok_api_key_prefix": grok_key[:10] + "..." if grok_key else None
            }
            
            # Try direct OpenAI client creation
            try:
                import openai
                diagnostics["openai_version"] = openai.__version__
                
                # Test direct client creation
                client = openai.OpenAI(
                    api_key=grok_key,
                    base_url="https://api.x.ai/v1"
                )
                diagnostics["direct_client_creation"] = "success"
                
                # Test API call
                response = client.chat.completions.create(
                    model="grok-2-1212",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                diagnostics["api_call_test"] = "success"
                diagnostics["response_content"] = response.choices[0].message.content
                
            except Exception as e:
                diagnostics["direct_client_error"] = str(e)
                diagnostics["error_type"] = type(e).__name__
            
            # Test via EnhancedLLMService
            try:
                service = EnhancedLLMService(provider=ModelProvider.GROK, model="grok-2-1212")
                diagnostics["enhanced_service_init"] = "success"
                diagnostics["grok_client_available"] = bool(service.grok_client)
                
                if service.grok_client:
                    result = service.generate_text("Hello, respond with 'Hi'")
                    diagnostics["enhanced_service_test"] = "success" if result.get("success") else "failed"
                    diagnostics["enhanced_service_response"] = result.get("text", result.get("error"))
            except Exception as e:
                diagnostics["enhanced_service_error"] = str(e)
            
            return jsonify({
                "success": True,
                "diagnostics": diagnostics
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }), 500

    @app.route('/videos/<path:relpath>')
    def serve_generated_video(relpath: str):
        """Serve locally generated video files saved under VIDEO_OUTPUT_DIR (default generated_videos).

        Security: ensures the resolved absolute path stays within the base directory to prevent traversal.
        """
        from flask import abort, send_file
        base_dir = os.getenv('VIDEO_OUTPUT_DIR', 'generated_videos')
        # Normalize paths
        base_abs = os.path.abspath(base_dir)
        target_abs = os.path.abspath(os.path.join(base_dir, relpath))
        if not target_abs.startswith(base_abs):
            abort(403)
        if not os.path.exists(target_abs):
            abort(404)
        # Basic content type assumption (could inspect)
        return send_file(target_abs, mimetype='video/mp4')
    
    @app.route('/video-generation')
    @login_required
    def video_generation():
        """Render the Video Generation page (requires login)."""
        return render_template('video_generation.html', title='Video Generation - Phoenix AI')
    
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
