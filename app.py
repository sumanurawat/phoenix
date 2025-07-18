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
    
    @app.route('/api/dataset-image/<path:filename>')
    def serve_dataset_image(filename):
        """Serve generated dataset analysis images."""
        import os
        from flask import send_file, abort
        
        app.logger.info(f"📊 Requesting image: {filename}")
        
        # Look for the image in common analysis directories
        import glob
        
        # First try exact paths we know
        possible_paths = [
            f"/private/var/folders/9g/xc39_69164346pmz81fs3g9m0000gn/T/phoenix_datasets/raw/arshid_iris-flower-dataset/{filename}",
            f"/var/folders/9g/xc39_69164346pmz81fs3g9m0000gn/T/phoenix_coding_agent/{filename}",
            f"/tmp/phoenix_coding_agent/{filename}",
            f"./{filename}",  # Current directory
        ]
        
        # Also search for the file in common temp directories
        search_patterns = [
            f"/private/var/folders/**/T/phoenix_datasets/**/{filename}",
            f"/var/folders/**/phoenix_coding_agent/{filename}",
            f"/tmp/**/{filename}",
            f"/var/tmp/**/{filename}",
        ]
        
        for pattern in search_patterns:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                possible_paths.extend(matches[:5])  # Add first 5 matches
        
        for path in possible_paths:
            if os.path.exists(path):
                app.logger.info(f"✅ Found image at: {path}")
                return send_file(path, mimetype='image/png')
        
        # Log all paths searched
        app.logger.warning(f"❌ Image not found. Searched paths: {possible_paths}")
        
        # If not found, return a placeholder or 404
        abort(404)
        
    @app.route('/api/list-dataset-images')
    def list_dataset_images():
        """Debug endpoint to list available dataset images."""
        import os
        import glob
        from flask import jsonify
        
        found_images = []
        
        # Search patterns for common image locations
        search_patterns = [
            "/private/var/folders/**/T/phoenix_datasets/**/*.png",
            "/var/folders/**/phoenix_coding_agent/*.png", 
            "/tmp/**/*.png",
            "/var/tmp/**/*.png",
            "./*.png",
        ]
        
        for pattern in search_patterns:
            matches = glob.glob(pattern, recursive=True)
            for match in matches:
                if os.path.exists(match):
                    found_images.append({
                        "filename": os.path.basename(match),
                        "full_path": match,
                        "size_kb": round(os.path.getsize(match) / 1024, 2)
                    })
        
        return jsonify({
            "success": True,
            "images_found": len(found_images),
            "images": found_images[:20]  # Limit to first 20
        })
        
    @app.route('/api/chat/dataset', methods=['POST'])
    def chat_dataset():
        """Chat endpoint for dataset analysis continuation."""
        try:
            from flask import jsonify
            from services.enhanced_llm_service import EnhancedLLMService, ModelProvider
            import time
            
            data = request.get_json()
            message = data.get('message', '')
            dataset_ref = data.get('dataset_ref', '')
            model_config = data.get('model_config', {})
            
            if not message:
                return jsonify({"success": False, "error": "Message is required"}), 400
            
            # Extract model configuration
            provider = model_config.get('provider', 'grok')
            model = model_config.get('model', 'grok-2-1212')
            enable_thinking = model_config.get('enable_thinking', False)
            thinking_budget = model_config.get('thinking_budget', 2048)
            
            # Create enhanced LLM service with specified model
            if provider == 'gemini':
                provider_enum = ModelProvider.GEMINI
            elif provider == 'claude':
                provider_enum = ModelProvider.CLAUDE
            elif provider == 'grok':
                provider_enum = ModelProvider.GROK
            else:
                provider_enum = ModelProvider.GROK  # Default fallback
            
            llm_service = EnhancedLLMService(provider=provider_enum, model=model)
            
            # Create context-aware prompt for dataset analysis chat
            prompt = f"""You are a dataset analysis assistant. The user has analyzed dataset "{dataset_ref}" and is asking: "{message}"

Please provide a helpful response about the dataset analysis. You can:
- Answer questions about the analysis results
- Suggest additional analysis steps
- Explain insights from the data
- Recommend visualizations
- Provide statistical interpretations

Keep your response concise and actionable."""
            
            start_time = time.time()
            response = llm_service.generate_text(
                prompt,
                enable_fallback=True,
                enable_thinking=enable_thinking,
                thinking_budget=thinking_budget
            )
            response_time = time.time() - start_time
            
            if response.get("success"):
                return jsonify({
                    "success": True,
                    "response": response["text"],
                    "tokens_used": {
                        "input": response.get("usage", {}).get("input_tokens", 0),
                        "output": response.get("usage", {}).get("output_tokens", 0)
                    },
                    "cost": 0,  # Will be calculated on frontend
                    "response_time": response_time,
                    "model_used": f"{provider}:{model}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": response.get("error", "Failed to generate response")
                }), 500
                
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

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
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    os.makedirs(SESSION_FILE_DIR, exist_ok=True)
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=8080)