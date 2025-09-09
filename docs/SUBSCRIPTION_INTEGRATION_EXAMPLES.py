"""
Phoenix AI - Subscription Integration Examples

This file demonstrates how to integrate subscription checks into your existing
Phoenix AI features. Copy these patterns to add subscription gating to any feature.
"""

from flask import Blueprint, request, jsonify, session, render_template
from services.subscription_middleware import (
    premium_required, 
    feature_limited, 
    check_feature_limit,
    model_allowed,
    get_available_models,
    feature_enabled
)
from api.auth_routes import login_required

# Example blueprint for demonstration
example_bp = Blueprint('examples', __name__)

# =============================================================================
# EXAMPLE 1: Premium-Only Feature
# =============================================================================

@example_bp.route('/premium-analytics')
@login_required
@premium_required  # Requires active premium subscription
def premium_analytics():
    """Example of a premium-only feature like advanced analytics."""
    
    # This code only runs for premium users
    analytics_data = {
        'advanced_metrics': True,
        'export_enabled': True,
        'custom_reports': True
    }
    
    return render_template('premium_analytics.html', data=analytics_data)


# =============================================================================
# EXAMPLE 2: Feature with Usage Limits
# =============================================================================

@example_bp.route('/api/chat', methods=['POST'])
@login_required
@feature_limited('chat_messages')  # Automatically tracks usage and enforces limits
def chat_api():
    """Chat API with automatic usage tracking and limiting."""
    
    data = request.json
    message = data.get('message')
    
    # Process the chat message
    response = process_chat_message(message)
    
    # Usage is automatically incremented by @feature_limited decorator
    return jsonify({
        'response': response,
        'status': 'success'
    })


# =============================================================================
# EXAMPLE 3: Manual Usage Checking
# =============================================================================

@example_bp.route('/api/dataset-analysis', methods=['POST'])
@login_required
def dataset_analysis():
    """Example with manual usage checking and custom limits."""
    
    # Check current usage before processing
    limit_result = check_feature_limit('datasets_analyzed')
    
    if not limit_result['allowed']:
        return jsonify({
            'error': 'Daily limit reached',
            'message': limit_result['message'],
            'limit': limit_result['limit'],
            'current': limit_result['current'],
            'upgrade_url': '/subscription'
        }), 429
    
    # Process the dataset analysis
    data = request.json
    dataset_url = data.get('dataset_url')
    
    analysis_result = analyze_dataset(dataset_url)
    
    # Manually increment usage after successful processing
    from services.subscription_middleware import increment_feature_usage
    increment_feature_usage('datasets_analyzed')
    
    return jsonify({
        'analysis': analysis_result,
        'usage_remaining': limit_result['remaining'] - 1
    })


# =============================================================================
# EXAMPLE 4: Model Access Control
# =============================================================================

@example_bp.route('/api/smart-chat', methods=['POST'])
@login_required
def smart_chat():
    """Chat endpoint with model access control based on subscription."""
    
    data = request.json
    message = data.get('message')
    preferred_model = data.get('model', 'gpt-3.5-turbo')
    
    # Check if user can access the requested model
    if not model_allowed(preferred_model):
        # Fall back to a basic model or return error
        if preferred_model in ['gpt-4', 'claude-3-opus']:
            return jsonify({
                'error': 'Premium subscription required',
                'message': f'Model {preferred_model} requires premium subscription',
                'available_models': get_available_models(),
                'upgrade_url': '/subscription'
            }), 403
        else:
            # Use default model for free users
            preferred_model = 'gpt-3.5-turbo'
    
    # Check usage limits for chat
    limit_result = check_feature_limit('chat_messages')
    if not limit_result['allowed']:
        return jsonify({
            'error': 'Daily chat limit reached',
            'message': limit_result['message'],
            'upgrade_url': '/subscription'
        }), 429
    
    # Process with allowed model
    response = generate_chat_response(message, preferred_model)
    
    # Increment usage
    from services.subscription_middleware import increment_feature_usage
    increment_feature_usage('chat_messages')
    
    return jsonify({
        'response': response,
        'model_used': preferred_model,
        'usage_remaining': limit_result['remaining'] - 1
    })


# =============================================================================
# EXAMPLE 5: Feature Toggle Based on Subscription
# =============================================================================

@example_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard with features enabled/disabled based on subscription."""
    
    # Check which features are enabled for the user
    export_enabled = feature_enabled('export_enabled')
    advanced_analytics = feature_enabled('advanced_analytics')
    custom_personalities = feature_enabled('custom_personalities')
    
    # Get current usage stats
    from services.stripe_service import StripeService
    stripe_service = StripeService()
    usage_stats = stripe_service.get_usage_stats(session.get('user_id'))
    
    context = {
        'title': 'Dashboard',
        'features': {
            'export_enabled': export_enabled,
            'advanced_analytics': advanced_analytics,
            'custom_personalities': custom_personalities
        },
        'usage': usage_stats
    }
    
    return render_template('dashboard.html', **context)


# =============================================================================
# EXAMPLE 6: Custom Decorator for Specific Features
# =============================================================================

def video_generation_required(f):
    """Custom decorator for video generation feature with special limits."""
    from functools import wraps
    from flask import jsonify, request
    from services.subscription_middleware import check_feature_limit, increment_feature_usage
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        
        # Check video generation limits (1 per day for free, 10 for premium)
        limit_result = check_feature_limit('videos_generated')
        
        if not limit_result['allowed']:
            if request.is_json:
                return jsonify({
                    'error': 'Video generation limit reached',
                    'message': limit_result['message'],
                    'upgrade_url': '/subscription'
                }), 429
            return redirect(url_for('subscription.manage'))
        
        # Call the original function
        result = f(*args, **kwargs)
        
        # Only increment if the function succeeded (didn't return an error)
        if isinstance(result, tuple):
            response, status_code = result
            if status_code < 400:  # Success status codes
                increment_feature_usage('videos_generated')
        else:
            # Assume success for non-tuple returns
            increment_feature_usage('videos_generated')
        
        return result
    
    return decorated_function

@example_bp.route('/api/generate-video', methods=['POST'])
@login_required
@video_generation_required  # Custom decorator with specific limits
def generate_video():
    """Video generation with custom usage tracking."""
    
    data = request.json
    prompt = data.get('prompt')
    
    # Generate video (this would be your actual video generation logic)
    video_result = create_video_from_prompt(prompt)
    
    return jsonify({
        'video_id': video_result['id'],
        'status': 'processing',
        'estimated_completion': '2 minutes'
    })


# =============================================================================
# EXAMPLE 7: Template Context Usage
# =============================================================================

@example_bp.route('/features')
@login_required  
def features_page():
    """Example page showing how to use subscription context in templates."""
    
    return render_template('features.html', title='Features')

# Template: features.html
"""
<!-- Example template using subscription context -->
<div class="container">
    <h1>Phoenix AI Features</h1>
    
    <!-- Subscription Status Display -->
    <div class="subscription-status mb-4">
        {% if subscription.is_premium %}
            <div class="alert alert-success">
                <i class="fas fa-crown"></i>
                <strong>Premium Member</strong> - You have access to all features!
            </div>
        {% else %}
            <div class="alert alert-info">
                <i class="fas fa-user"></i>
                <strong>Free Plan</strong> - 
                <a href="/subscription" class="btn btn-sm btn-primary">
                    Upgrade to Premium
                </a>
            </div>
        {% endif %}
    </div>
    
    <!-- Usage Statistics -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h3>{{ subscription.usage.chat_messages or 0 }}</h3>
                    <p class="text-muted">
                        Chat Messages Today
                        {% if not subscription.is_premium %}
                            <br><small>({{ subscription.limits.chat_messages }} max)</small>
                        {% endif %}
                    </p>
                </div>
            </div>
        </div>
        <!-- More usage stats... -->
    </div>
    
    <!-- Feature Cards -->
    <div class="row">
        <!-- Basic Chat -->
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <h5>AI Chat</h5>
                    <p>Conversational AI assistant</p>
                    {% if subscription.usage.chat_messages >= subscription.limits.chat_messages and not subscription.is_premium %}
                        <button class="btn btn-secondary" disabled>
                            Daily limit reached
                        </button>
                        <a href="/subscription" class="btn btn-primary btn-sm">
                            Upgrade
                        </a>
                    {% else %}
                        <a href="/derplexity" class="btn btn-success">
                            Start Chat
                        </a>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <!-- Premium Feature -->
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <h5>
                        Advanced Analytics
                        <i class="fas fa-crown text-warning"></i>
                    </h5>
                    <p>Detailed insights and reporting</p>
                    {% if subscription.is_premium %}
                        <a href="/premium-analytics" class="btn btn-success">
                            View Analytics
                        </a>
                    {% else %}
                        <button class="btn btn-outline-secondary" disabled>
                            Premium Required
                        </button>
                        <a href="/subscription" class="btn btn-primary btn-sm">
                            Upgrade
                        </a>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <!-- Model Selection -->
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <h5>AI Models</h5>
                    <div class="form-group">
                        <select class="form-select" id="modelSelect">
                            {% for model in subscription.available_models %}
                                <option value="{{ model }}">{{ model }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    {% if not subscription.is_premium %}
                        <small class="text-muted">
                            Premium models require upgrade
                        </small>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
"""


# =============================================================================
# UTILITY FUNCTIONS (implement these in your actual code)
# =============================================================================

def process_chat_message(message):
    """Process a chat message (implement your logic here)."""
    return f"AI response to: {message}"

def analyze_dataset(dataset_url):
    """Analyze a dataset (implement your logic here)."""
    return {"summary": "Dataset analysis complete"}

def generate_chat_response(message, model):
    """Generate chat response with specific model (implement your logic here)."""
    return f"Response from {model}: {message}"

def create_video_from_prompt(prompt):
    """Create video from prompt (implement your logic here)."""
    return {"id": "video_123", "status": "processing"}