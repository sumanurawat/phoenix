"""
Dataset Discovery API Routes for Phoenix Flask Application.
Provides REST endpoints for dataset search and discovery operations.
"""
import logging
import time
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from functools import wraps

from services.dataset_discovery import DatasetDiscoveryService, create_dataset_service
from services.dataset_discovery.models import SearchRequest
from services.dataset_discovery.download_service import DatasetDownloadService
from services.dataset_discovery.exceptions import (
    DatasetDiscoveryError, SearchValidationError, KaggleAuthenticationError,
    KaggleAPIError, ConfigurationError
)

# Configure logging
logger = logging.getLogger(__name__)

from middleware.csrf_protection import csrf_protect

# Feature gating imports
from config.settings import FEATURE_GATING_V2_ENABLED
if FEATURE_GATING_V2_ENABLED:
    from services.feature_gating import feature_required
else:
    from services.subscription_middleware import feature_limited, premium_required

# Create blueprint
dataset_bp = Blueprint('datasets', __name__, url_prefix='/api/datasets')

# Initialize services (will be lazy-loaded)
_dataset_service = None
_download_service = None


def get_dataset_service() -> DatasetDiscoveryService:
    """Get or create the dataset service instance."""
    global _dataset_service
    if _dataset_service is None:
        try:
            _dataset_service = create_dataset_service()
            logger.info("🎯 Dataset discovery service initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Dataset discovery service initialization failed: {e}")
            # Still return None - will be handled by endpoints
            raise
    return _dataset_service


def get_download_service() -> DatasetDownloadService:
    """Get or create the download service instance."""
    global _download_service
    if _download_service is None:
        try:
            _download_service = DatasetDownloadService()
            logger.info("🔽 Dataset download service initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Dataset download service initialization failed: {e}")
            raise
    return _download_service


def handle_api_error(func):
    """Decorator to handle API errors consistently."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SearchValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            return jsonify({
                "success": False,
                "error": e.to_dict()
            }), 400
        except KaggleAuthenticationError as e:
            logger.error(f"Authentication error in {func.__name__}: {str(e)}")
            return jsonify({
                "success": False,
                "error": e.to_dict()
            }), 401
        except ConfigurationError as e:
            logger.error(f"Configuration error in {func.__name__}: {str(e)}")
            return jsonify({
                "success": False,
                "error": e.to_dict()
            }), 500
        except DatasetDiscoveryError as e:
            logger.error(f"Service error in {func.__name__}: {str(e)}")
            return jsonify({
                "success": False,
                "error": e.to_dict()
            }), 500
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": "Please try again or contact support"
                }
            }), 500
    return wrapper


def apply_dataset_search_gating(f):
    """Apply gating for dataset search."""
    if FEATURE_GATING_V2_ENABLED:
        return feature_required('dataset_search')(f)
    else:
        return feature_limited('datasets_analyzed')(f)

def apply_dataset_download_gating(f):
    """Apply gating for dataset download."""
    if FEATURE_GATING_V2_ENABLED:
        return feature_required('dataset_download')(f)
    else:
        return premium_required(f)

def apply_dataset_analysis_gating(f):
    """Apply gating for dataset analysis."""
    if FEATURE_GATING_V2_ENABLED:
        return feature_required('dataset_analysis')(f)
    else:
        return premium_required(f)


@dataset_bp.route('/search', methods=['POST'])
@csrf_protect
@apply_dataset_search_gating
@handle_api_error
def search_datasets():
    """
    Search for datasets on Kaggle.
    
    Expected JSON payload:
    {
        "query": "climate change",
        "limit": 10,
        "sort_by": "hottest",
        "min_quality_score": 0.0
    }
    
    Returns:
        JSON response with search results and metadata
    """
    # Log request
    request_start = time.time()
    logger.info(f"📨 Dataset search request from {request.remote_addr}")
    
    # Validate request
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Content-Type must be application/json"
            }
        }), 400
    
    data = request.get_json()
    if not data:
        return jsonify({
            "success": False,
            "error": {
                "code": "EMPTY_REQUEST",
                "message": "Request body cannot be empty"
            }
        }), 400
    
    # Extract parameters
    query = data.get('query', '').strip()
    if not query:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_QUERY",
                "message": "Query parameter is required"
            }
        }), 400
    
    # Create search request with validation
    try:
        search_request = SearchRequest(
            query=query,
            limit=data.get('limit', 20),
            sort_by=data.get('sort_by', 'votes'),
            min_quality_score=data.get('min_quality_score', 0.0)
        )
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_PARAMETERS",
                "message": str(e)
            }
        }), 400
    
    # Log search parameters
    logger.info(
        f"🔍 Searching datasets: query='{search_request.query}', "
        f"limit={search_request.limit}, sort_by={search_request.sort_by}, "
        f"min_quality={search_request.min_quality_score}"
    )
    
    # Perform search
    service = get_dataset_service()
    search_response = service.search_datasets(search_request)
    
    # Log performance
    total_time = int((time.time() - request_start) * 1000)
    logger.info(
        f"✅ Search completed: {search_response.returned_count} results in {total_time}ms "
        f"(query: '{search_request.query}')"
    )
    
    # Return response
    response_data = {
        "success": True,
        **search_response.to_dict()
    }
    
    return jsonify(response_data), 200


@dataset_bp.route('/health', methods=['GET'])
@handle_api_error
def health_check():
    """
    Check if dataset service is operational.
    
    Returns:
        JSON response with service health status
    """
    logger.debug("🏥 Health check requested")
    
    try:
        service = get_dataset_service()
        health_status = service.get_health_status()
        
        # Determine HTTP status code based on health
        if health_status.status == 'healthy':
            status_code = 200
        elif health_status.status == 'degraded':
            status_code = 200  # Still operational
        else:
            status_code = 503  # Service unavailable
        
        logger.info(f"🏥 Health check result: {health_status.status}")
        
        return jsonify({
            "success": True,
            **health_status.to_dict()
        }), status_code
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": {
                "code": "HEALTH_CHECK_FAILED",
                "message": str(e)
            }
        }), 503


@dataset_bp.route('/config', methods=['GET'])
@handle_api_error
def get_config_info():
    """
    Get configuration information (non-sensitive data only).
    
    Returns:
        JSON response with configuration details
    """
    logger.debug("⚙️ Configuration info requested")
    
    try:
        service = get_dataset_service()
        config = service.config
        
        config_info = {
            "version": "1.0.0",
            "defaults": config.get_search_defaults(),
            "kaggle_configured": bool(config.KAGGLE_USERNAME and config.KAGGLE_KEY),
            "features": {
                "search": True,
                "scoring": True,
                "file_analysis": True
            }
        }
        
        return jsonify({
            "success": True,
            **config_info
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Config info request failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "CONFIG_ERROR",
                "message": "Failed to retrieve configuration"
            }
        }), 500


@dataset_bp.route('/download/check', methods=['POST'])
@csrf_protect
@handle_api_error
def check_download_feasibility():
    """
    Check if a dataset can be downloaded in the current environment.
    
    Expected JSON payload:
    {
        "dataset_ref": "owner/dataset-name",
        "size_mb": 25.5
    }
    
    Returns:
        JSON response with feasibility information
    """
    logger.info(f"🔍 Download feasibility check from {request.remote_addr}")
    
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Content-Type must be application/json"
            }
        }), 400
    
    data = request.get_json()
    dataset_ref = data.get('dataset_ref', '').strip()
    size_mb = data.get('size_mb', 0)
    
    if not dataset_ref:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATASET_REF",
                "message": "dataset_ref parameter is required"
            }
        }), 400
    
    try:
        download_service = get_download_service()
        feasibility = download_service.check_download_feasibility(dataset_ref, size_mb)
        
        return jsonify({
            "success": True,
            **feasibility
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Download feasibility check failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "CHECK_FAILED",
                "message": "Failed to check download feasibility",
                "details": str(e)
            }
        }), 500


@dataset_bp.route('/download', methods=['POST'])
@csrf_protect
@apply_dataset_download_gating
@handle_api_error
def download_dataset():
    """
    Download a dataset temporarily for analysis.
    
    Expected JSON payload:
    {
        "dataset_ref": "owner/dataset-name",
        "size_mb": 25.5,
        "force": false
    }
    
    Returns:
        JSON response with download results
    """
    logger.info(f"🔽 Dataset download request from {request.remote_addr}")
    
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Content-Type must be application/json"
            }
        }), 400
    
    data = request.get_json()
    dataset_ref = data.get('dataset_ref', '').strip()
    size_mb = data.get('size_mb', 0)
    force = data.get('force', False)
    
    if not dataset_ref:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATASET_REF",
                "message": "dataset_ref parameter is required"
            }
        }), 400
    
    try:
        download_service = get_download_service()
        result = download_service.download_dataset(dataset_ref, size_mb, force)
        
        return jsonify({
            "success": True,
            **result
        }), 200
        
    except DatasetDiscoveryError as e:
        logger.warning(f"⚠️ Download rejected: {e}")
        return jsonify({
            "success": False,
            "error": e.to_dict()
        }), 400
        
    except Exception as e:
        logger.error(f"❌ Dataset download failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "DOWNLOAD_FAILED",
                "message": "Failed to download dataset",
                "details": str(e)
            }
        }), 500


@dataset_bp.route('/download/status', methods=['GET'])
@handle_api_error
def get_download_status():
    """
    Get current download directory status.
    
    Returns:
        JSON response with download status
    """
    logger.debug("📊 Download status requested")
    
    try:
        download_service = get_download_service()
        status = download_service.get_download_status()
        
        return jsonify({
            "success": True,
            **status
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Download status failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "STATUS_FAILED",
                "message": "Failed to get download status"
            }
        }), 500


@dataset_bp.route('/download/cleanup', methods=['POST'])
@csrf_protect
@handle_api_error
def cleanup_downloads():
    """
    Clean up old downloaded datasets.
    
    Expected JSON payload (optional):
    {
        "max_age_hours": 2,
        "clear_all": false
    }
    
    Returns:
        JSON response with cleanup results
    """
    logger.info(f"🗑️ Download cleanup requested from {request.remote_addr}")
    
    max_age_hours = 1  # Default
    clear_all = False
    
    if request.is_json:
        data = request.get_json() or {}
        max_age_hours = data.get('max_age_hours', 1)
        clear_all = data.get('clear_all', False)
    
    try:
        download_service = get_download_service()
        
        if clear_all:
            result = download_service.cleanup_all_downloads()
        else:
            result = download_service.cleanup_old_downloads(max_age_hours)
        
        return jsonify({
            "success": True,
            **result
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Download cleanup failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "CLEANUP_FAILED",
                "message": "Failed to cleanup downloads"
            }
        }), 500


@dataset_bp.route('/analyze')
def dataset_analyze():
    """
    Dataset analysis page - shows analysis interface for downloaded dataset
    """
    dataset_ref = request.args.get('ref')
    file_count = request.args.get('files', 0, type=int)
    size_mb = request.args.get('size', 0, type=float)
    
    if not dataset_ref:
        logger.warning("Dataset analysis page accessed without dataset reference")
        return redirect(url_for('dataset_discovery.dataset_discovery'))
    
    logger.info(f"📊 Dataset analysis page requested for {dataset_ref}")
    
    return render_template('dataset_analysis_chat.html', 
                         dataset_ref=dataset_ref,
                         file_count=file_count,
                         size_mb=size_mb)


@dataset_bp.route('/analyze/step', methods=['POST'])
@csrf_protect
@apply_dataset_analysis_gating
def analyze_step():
    """
    Run individual analysis step on downloaded dataset with configurable models
    """
    try:
        data = request.get_json()
        dataset_ref = data.get('dataset_ref')
        step = data.get('step')
        description = data.get('description', '')
        model_config = data.get('model_config', {})
        
        if not dataset_ref or not step:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETERS",
                    "message": "dataset_ref and step are required"
                }
            }), 400
        
        # Extract model configuration
        provider = model_config.get('provider', 'gemini')
        model = model_config.get('model', 'gemini-2.5-flash')
        iterative_mode = model_config.get('iterative_mode', False)
        max_iterations = model_config.get('max_iterations', 5)
        # Thinking mode parameters removed for simplicity
        
        logger.info(f"📊 Running analysis step {step} for {dataset_ref}: {description}")
        logger.info(f"🤖 Using {provider}:{model}, iterative: {iterative_mode}, max_iter: {max_iterations}")
        
        if iterative_mode:
            # Use iterative coding agent
            from services.enhanced_llm_service import EnhancedLLMService, ModelProvider
            from services.dataset_discovery.iterative_coding_agent import IterativeCodingAgent
            from services.dataset_discovery.temp_analysis_service import TempAnalysisService
            
            # Initialize enhanced LLM service
            if provider == 'gemini':
                provider_enum = ModelProvider.GEMINI
            elif provider == 'claude':
                provider_enum = ModelProvider.CLAUDE
            elif provider == 'grok':
                provider_enum = ModelProvider.GROK
            else:
                provider_enum = ModelProvider.GEMINI  # Default fallback
            llm_service = EnhancedLLMService(provider=provider_enum, model=model)
            
            # Initialize iterative agent with conversation tracking enabled
            agent = IterativeCodingAgent(
                llm_service, 
                max_iterations=max_iterations,
                enable_conversation_tracking=True,
                save_conversations=False  # Keep in-memory for now to save costs
            )
            
            # Get dataset files
            temp_service = TempAnalysisService()
            dataset_files = temp_service._find_dataset_files(dataset_ref)
            
            if not dataset_files:
                raise ValueError(f"No dataset files found for {dataset_ref}")
            
            # Create task prompt for the step
            step_prompts = {
                1: "Comprehensive Data Analysis: Load dataset, explore structure, perform statistical analysis, and analyze individual columns with data quality checks",
                2: "Advanced Statistical Analysis: Perform correlation analysis, outlier detection, distribution analysis, and feature relationships", 
                3: "Machine Learning Analysis: Build predictive models, feature importance analysis, and performance evaluation",
                4: "Generate insights and recommendations based on the complete dataset analysis"
            }
            
            task_prompt = step_prompts.get(step, description)
            
            # Run iterative agent (thinking mode removed)
            result = agent.generate_and_refine_code(task_prompt, dataset_files)
            
            # Format result for API response
            api_result = {
                "output": result.final_output,
                "insights": result.insights,
                "recommendations": result.recommendations,
                "code_generated": result.success,
                "files_analyzed": len(dataset_files),
                "iterations_used": result.total_iterations,
                "cost_estimate": result.total_cost_estimate,
                "model_used": f"{provider}:{model}",
                "iterative_mode": True,
                "fallback_info": getattr(result, 'fallback_info', None),  # Include fallback details if used
                "conversation_id": getattr(result, 'conversation_id', None),  # Include conversation ID
                "iterations": [
                    {
                        "iteration": iter.iteration,
                        "success": iter.success,
                        "prompt_tokens": iter.prompt_tokens,
                        "completion_tokens": iter.completion_tokens,
                        "generation_time": iter.generation_time,
                        "execution_time": iter.execution_time,
                        "model_used": iter.model_used,
                        "phase_description": iter.phase_description,
                        "execution_result": iter.execution_result[:500] if iter.execution_result else "",  # Truncate for size
                        "error_message": iter.error_message,
                        "code": iter.code[:200] if iter.code else ""  # Truncate code for size
                    }
                    for iter in result.iterations
                ]  # Convert iterations to JSON-serializable format
            }
            
        else:
            # Use original single-shot analysis
            from services.dataset_discovery.temp_analysis_service import TempAnalysisService
            from services.enhanced_llm_service import EnhancedLLMService, ModelProvider
            
            # Create enhanced LLM service for single shot
            if provider == 'gemini':
                provider_enum = ModelProvider.GEMINI
            elif provider == 'claude':
                provider_enum = ModelProvider.CLAUDE
            elif provider == 'grok':
                provider_enum = ModelProvider.GROK
            else:
                provider_enum = ModelProvider.GEMINI  # Default fallback
            llm_service = EnhancedLLMService(provider=provider_enum, model=model)
            
            # Temporarily override the LLM service in temp analysis
            analysis_service = TempAnalysisService()
            analysis_service.llm_service = llm_service
            
            api_result = analysis_service.run_analysis_step(dataset_ref, step, description)
            api_result["model_used"] = f"{provider}:{model}"
            api_result["iterative_mode"] = False
        
        return jsonify({
            "success": True,
            "result": api_result
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Analysis step failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "ANALYSIS_STEP_FAILED",
                "message": str(e)
            }
        }), 500


@dataset_bp.route('/conversation/<conversation_id>', methods=['GET'])
@handle_api_error
def get_conversation_messages(conversation_id):
    """
    Get conversation messages for a dataset analysis session.
    
    Args:
        conversation_id: The conversation ID from the analysis result
        
    Returns:
        JSON response with conversation messages
    """
    try:
        logger.info(f"💬 Fetching conversation messages for {conversation_id}")
        
        # Import conversation tracker to access messages
        from services.dataset_discovery.conversation_tracker import ConversationTracker
        
        # Get tracker from global store
        tracker = ConversationTracker.get_conversation_by_id(conversation_id)
        
        if not tracker:
            return jsonify({
                "success": False,
                "error": {
                    "code": "CONVERSATION_NOT_FOUND",
                    "message": f"Conversation {conversation_id} not found"
                }
            }), 404
        
        # Get messages and format them properly for frontend
        messages = tracker.get_messages()
        
        # Format messages to ensure consistent structure for debug display
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "role": msg.get("role", "unknown"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", 0),
                "message_id": msg.get("message_id", ""),
                "conversation_id": msg.get("conversation_id", conversation_id),
                "message_type": msg.get("metadata", {}).get("message_type", "unknown"),
                
                # Extract metadata fields for easier access
                "model": msg.get("metadata", {}).get("model", ""),
                "model_used": msg.get("metadata", {}).get("model_used", ""),
                "tokens": msg.get("metadata", {}).get("tokens", {}),
                "generation_time": msg.get("metadata", {}).get("generation_time", 0),
                "duration": msg.get("metadata", {}).get("duration", 0),
                "execution_time": msg.get("metadata", {}).get("execution_time", 0),
                "code": msg.get("metadata", {}).get("code", ""),
                "execution_result": msg.get("metadata", {}).get("execution_result", ""),
                "error_message": msg.get("metadata", {}).get("error_message", ""),
                "success": msg.get("metadata", {}).get("success", False),
                "step": msg.get("metadata", {}).get("step", 0),
                "iteration": msg.get("metadata", {}).get("iteration", 0),
                
                # Keep original metadata for any additional fields
                "metadata": msg.get("metadata", {})
            }
            formatted_messages.append(formatted_msg)
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "messages": formatted_messages,
            "message_count": len(formatted_messages)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch conversation messages: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "CONVERSATION_FETCH_FAILED", 
                "message": "Failed to fetch conversation messages",
                "details": str(e)
            }
        }), 500


@dataset_bp.route('/generate-code', methods=['POST'])
@csrf_protect
def generate_analysis_code():
    """
    Generate complete analysis code using Gemini API
    """
    try:
        data = request.get_json()
        dataset_ref = data.get('dataset_ref')
        analysis_results = data.get('analysis_results', {})
        
        if not dataset_ref:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETERS",
                    "message": "dataset_ref is required"
                }
            }), 400
        
        logger.info(f"🤖 Generating analysis code for {dataset_ref}")
        
        # Import here to avoid circular imports
        from services.dataset_discovery.temp_analysis_service import TempAnalysisService
        
        analysis_service = TempAnalysisService()
        code = analysis_service.generate_analysis_code(dataset_ref, analysis_results)
        
        return jsonify({
            "success": True,
            "code": code
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Code generation failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "CODE_GENERATION_FAILED",
                "message": str(e)
            }
        }), 500


# Error handlers for the blueprint
@dataset_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors within the dataset blueprint."""
    return jsonify({
        "success": False,
        "error": {
            "code": "ENDPOINT_NOT_FOUND",
            "message": "The requested endpoint does not exist",
            "details": "Please check the API documentation for valid endpoints"
        }
    }), 404


@dataset_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors within the dataset blueprint."""
    return jsonify({
        "success": False,
        "error": {
            "code": "METHOD_NOT_ALLOWED",
            "message": "The HTTP method is not allowed for this endpoint",
            "details": f"Allowed methods: {', '.join(error.valid_methods) if hasattr(error, 'valid_methods') else 'Unknown'}"
        }
    }), 405


@dataset_bp.errorhandler(413)
def payload_too_large(error):
    """Handle 413 errors within the dataset blueprint."""
    return jsonify({
        "success": False,
        "error": {
            "code": "PAYLOAD_TOO_LARGE",
            "message": "Request payload is too large",
            "details": "Please reduce the size of your request"
        }
    }), 413


@dataset_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle 429 errors within the dataset blueprint."""
    return jsonify({
        "success": False,
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests",
            "details": "Please wait before making more requests"
        }
    }), 429


# Add request logging middleware
@dataset_bp.before_request
def log_request():
    """Log incoming requests for monitoring."""
    logger.debug(
        f"📥 {request.method} {request.path} from {request.remote_addr} "
        f"(User-Agent: {request.headers.get('User-Agent', 'Unknown')})"
    )


@dataset_bp.after_request
def log_response(response):
    """Log outgoing responses for monitoring."""
    logger.debug(
        f"📤 {request.method} {request.path} -> {response.status_code} "
        f"({response.content_length or 0} bytes)"
    )
    return response