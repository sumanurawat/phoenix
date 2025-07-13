"""
Phoenix AI Platform Application

This is the main application file that sets up the Flask application,
registers routes, and initializes services.
"""
import os
import logging
from functools import wraps
from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_session import Session

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
from api.search_routes import search_bp
from api.robin_routes import robin_bp
from api.deeplink_routes import deeplink_bp
from api.auth_routes import auth_bp, login_required
from api.stats_routes import stats_bp
from api.dataset_routes import dataset_bp

# Import services (AFTER Firebase initialization)
from services.chat_service import ChatService
from services.enhanced_chat_service import EnhancedChatService
from services.search_service import SearchService

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

# Initialize services
chat_service = ChatService()
enhanced_chat_service = EnhancedChatService()
search_service = SearchService()

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
    
    # Configure application - Set ENV first
    app.config["ENV"] = FLASK_ENV
    app.config["DEBUG"] = FLASK_DEBUG
    app.config["SECRET_KEY"] = SECRET_KEY
    
    # Security check after ENV is set
    if app.config["ENV"] != "development" and app.config["SECRET_KEY"] == "default-secret-key":
        raise RuntimeError("SECURITY CRITICAL: Default SECRET_KEY is not allowed in production/staging. Please set a strong, unique SECRET_KEY in the environment configuration.")
    
    # Configure session
    app.config["SESSION_TYPE"] = SESSION_TYPE
    app.config["SESSION_PERMANENT"] = SESSION_PERMANENT
    app.config["SESSION_USE_SIGNER"] = SESSION_USE_SIGNER
    app.config["SESSION_FILE_DIR"] = SESSION_FILE_DIR
    app.config["SESSION_FILE_THRESHOLD"] = SESSION_FILE_THRESHOLD
    Session(app)
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(enhanced_chat_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(robin_bp)
    app.register_blueprint(deeplink_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(dataset_bp)
    
    # Define routes
    @app.route('/')
    def index():
        """Render the main index page."""
        return render_template('index.html', title='Phoenix AI Platform')

    @app.route('/derplexity')
    @login_required
    def derplexity():
        """Render the enhanced Derplexity chat interface with persistent conversations."""
        return render_template('derplexity_v2.html', 
                            title='Derplexity Chat')
    
    @app.route('/derplexity-enhanced')
    @login_required
    def derplexity_enhanced():
        """Render the enhanced Derplexity chat interface (alternative)."""
        return render_template('enhanced_derplexity.html', 
                            title='Derplexity Chat (Enhanced)')
    
    @app.route('/derplexity-legacy')
    def derplexity_legacy():
        """Render the legacy Derplexity chat interface (session-based)."""
        # Initialize a new chat session if one doesn't exist
        if "chat" not in session:
            session["chat"] = chat_service.start_new_chat()
        
        return render_template('derplexity.html', 
                            title='Derplexity Chat (Legacy)', 
                            chat=session["chat"])
    
    @app.route('/doogle')
    def doogle():
        """Render the Doogle search interface."""
        query = request.args.get('q', '')
        category = request.args.get('category', 'web')
        page = int(request.args.get('page', 1))
        
        # Validate category - only allow web or news
        if category not in ['web', 'news']:
            category = 'web'
        
        # If there's a query, perform search and pass results to template
        results = {}
        if query:
            results = search_service.search(query, category, page)
            
        return render_template('doogle.html', 
                           title='Doogle Search', 
                           query=query,
                           category=category,
                           results=results)
    
    @app.route('/datasets')
    def dataset_discovery():
        """Render the Dataset Discovery page."""
        return render_template('dataset_discovery.html', title='Dataset Discovery - Phoenix AI')
    
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
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    os.makedirs(SESSION_FILE_DIR, exist_ok=True)
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=8080)