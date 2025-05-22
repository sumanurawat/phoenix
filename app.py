"""
Phoenix AI Platform Application

This is the main application file that sets up the Flask application,
registers routes, and initializes services.
"""
import os
import logging
from flask import Flask, render_template, session, request
from flask_session import Session

# Import configurations
from config.settings import (
    SECRET_KEY, FLASK_ENV, FLASK_DEBUG,
    SESSION_TYPE, SESSION_PERMANENT, SESSION_USE_SIGNER,
    SESSION_FILE_DIR, SESSION_FILE_THRESHOLD
)

# Import Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials

# Import API routes
from api.chat_routes import chat_bp
from api.search_routes import search_bp
from api.robin_routes import robin_bp
from api.deeplink_routes import deeplink_bp
from api.auth_routes import auth_bp

# Import services
from services.chat_service import ChatService
from services.search_service import SearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
chat_service = ChatService()
search_service = SearchService()

def create_app():
    """Create and configure the Flask application."""
    # Initialize Flask app
    app = Flask(__name__)
    
    # Configure application
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["ENV"] = FLASK_ENV
    app.config["DEBUG"] = FLASK_DEBUG
    
    # Configure session
    app.config["SESSION_TYPE"] = SESSION_TYPE
    app.config["SESSION_PERMANENT"] = SESSION_PERMANENT
    app.config["SESSION_USE_SIGNER"] = SESSION_USE_SIGNER
    app.config["SESSION_FILE_DIR"] = SESSION_FILE_DIR
    app.config["SESSION_FILE_THRESHOLD"] = SESSION_FILE_THRESHOLD
    Session(app)

    # Initialize Firebase Admin SDK (if not already initialized)
    # This should be done before any services that use Firebase are initialized
    # or blueprints that rely on Firebase services are registered.
    if not firebase_admin._apps:
        try:
            # Try to load credentials from a JSON file path (e.g., for local development)
            creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
            if os.path.exists(creds_path):
                cred = credentials.Certificate(creds_path)
                app.logger.info(f"Initializing Firebase Admin SDK with credentials from: {creds_path}")
            # Try to load credentials from an environment variable (e.g., for CI/CD or some PaaS)
            elif os.getenv("FIREBASE_CREDENTIALS"):
                import json
                cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
                cred = credentials.Certificate(cred_dict)
                app.logger.info("Initializing Firebase Admin SDK with credentials from FIREBASE_CREDENTIALS env var.")
            else:
                # Fallback for environments like Google Cloud Run/Functions where Application Default Credentials (ADC) might be available.
                # If running locally without a service account JSON or GOOGLE_APPLICATION_CREDENTIALS env var,
                # this might not provide specific project access unless ADC are configured locally.
                cred = credentials.ApplicationDefault()
                app.logger.info("Initializing Firebase Admin SDK with Application Default Credentials.")
            
            firebase_admin.initialize_app(cred)
            app.logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            app.logger.error(f"Firebase Admin SDK initialization error: {e}")
            # Depending on the application's needs, you might want to raise the exception
            # or exit if Firebase is critical for all operations. For now, just log the error.

    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(robin_bp)
    app.register_blueprint(deeplink_bp)
    app.register_blueprint(auth_bp)
    
    # Define routes
    @app.route('/')
    def index():
        """Render the main index page."""
        return render_template('index.html', title='Phoenix AI Platform')

    @app.route('/derplexity')
    def derplexity():
        """Render the Derplexity chat interface."""
        # Initialize a new chat session if one doesn't exist
        if "chat" not in session:
            session["chat"] = chat_service.start_new_chat()
        
        return render_template('derplexity.html', 
                            title='Derplexity Chat', 
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
    
    @app.route('/blogs')
    def blogs():
        """Render the Technical Blogs page."""
        return render_template('blogs.html', 
                           title='Technical Blogs - Sumanu Rawat')
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    os.makedirs(SESSION_FILE_DIR, exist_ok=True)
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=8080)