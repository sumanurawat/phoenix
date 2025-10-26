"""
Phoenix AI Platform Application

This is the main application file that sets up the Flask application,
registers routes, and initializes services.
"""
import os
import logging
import secrets
from functools import wraps
from flask import Flask, render_template, session, request, redirect, url_for, flash, abort, jsonify, jsonify
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
from api.search_routes import search_bp
from api.robin_routes import robin_bp
from api.deeplink_routes import deeplink_bp
from api.auth_routes import auth_bp, login_required
from api.stats_routes import stats_bp
from api.dataset_routes import dataset_bp
from api.video_routes import video_bp
from api.stripe_routes import stripe_bp, subscription_bp
from api.token_routes import token_bp
from api.reel_routes import reel_bp
from api.job_routes import job_bp
from api.socials_routes import socials_bp
from api.image_routes import image_bp
from api.video_generation_routes import video_generation_bp
from api.user_routes import user_bp
from api.feed_routes import feed_bp

# Import services (AFTER Firebase initialization)
from services.chat_service import ChatService
from services.enhanced_chat_service import EnhancedChatService
from services.search_service import SearchService
from services.website_stats_service import WebsiteStatsService
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

# Initialize services
chat_service = ChatService()
enhanced_chat_service = EnhancedChatService()
search_service = SearchService()
website_stats_service = WebsiteStatsService()

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

    # Configure application - Set ENV first
    app.config["ENV"] = FLASK_ENV
    app.config["DEBUG"] = FLASK_DEBUG
    app.config["SECRET_KEY"] = SECRET_KEY

    # Initialize Celery with Flask app context (Phase 3)
    from celery_app import celery_app
    celery_app.conf.update(flask_app=app)

    class ContextTask(celery_app.Task):
        """Make Celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    
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
    app.register_blueprint(search_bp)
    app.register_blueprint(robin_bp)
    app.register_blueprint(deeplink_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(dataset_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(stripe_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(token_bp)
    app.register_blueprint(reel_bp)
    app.register_blueprint(job_bp)
    app.register_blueprint(socials_bp)
    app.register_blueprint(image_bp)
    app.register_blueprint(video_generation_bp)  # Phase 3: Async video generation
    app.register_blueprint(user_bp)  # Phase 4: User profiles & usernames
    app.register_blueprint(feed_bp)  # Phase 4: Social feed & likes
    
    # Setup subscription middleware
    @app.before_request
    def setup_subscription_context():
        """Initialize subscription context for each request."""
        init_subscription_context()
    
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
    
    @app.route('/doogle')
    @login_required
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
            
            # Increment Doogle search stats for non-empty queries
            try:
                website_stats_service.increment_doogle_searches()
            except Exception as e:
                logger.warning(f"Failed to update Doogle search stats: {e}")
            
        return render_template('doogle.html', 
                           title='Doogle Search', 
                           query=query,
                           category=category,
                           results=results)
    
    @app.route('/phase4-test')
    @login_required
    def phase4_test():
        """Phase 4 API testing page."""
        return render_template('phase4_test.html', title='Phase 4 API Test')

    @app.route('/datasets')
    @login_required
    def dataset_discovery():
        """Render the Dataset Discovery page."""
        return render_template('dataset_discovery.html', title='Dataset Discovery - Phoenix AI')
    
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

    @app.route('/token-purchase-success')
    @require_auth
    def token_purchase_success():
        """Render the token purchase success page."""
        return render_template('token_purchase_success.html',
                           title='Payment Successful')

    @app.route('/token-purchase-cancel')
    def token_purchase_cancel():
        """Render the token purchase cancel page."""
        return render_template('token_purchase_cancel.html',
                           title='Payment Canceled')
    
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
    
    @app.route('/reel-maker')
    @login_required
    def reel_maker():
        """Render the Reel Maker page (requires login)."""
        return render_template('reel_maker.html', title='Reel Maker - Phoenix AI')
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    os.makedirs(SESSION_FILE_DIR, exist_ok=True)
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=8080)
