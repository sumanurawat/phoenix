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

# Import API routes
from api.chat_routes import chat_bp
from api.search_routes import search_bp

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
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(search_bp)
    
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
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    os.makedirs(SESSION_FILE_DIR, exist_ok=True)
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=8080)