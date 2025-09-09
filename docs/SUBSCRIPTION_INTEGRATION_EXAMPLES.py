"""
Example of how to add subscription-based features to existing Phoenix routes.

This file demonstrates how to integrate subscription checking into the existing
chat and other features to provide a professional subscription experience.
"""

from services.subscription_middleware import premium_required, check_feature_limit
from services.stripe_service import StripeService
from flask import session, jsonify

# Example 1: Adding premium requirement to existing chat route
def enhanced_chat_with_subscription():
    """
    Example of how to modify the derplexity chat to check subscription limits.
    This would be integrated into the existing chat_routes.py
    """
    
    # Get current user
    firebase_uid = session.get('user_id')
    if not firebase_uid:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Check feature limits for free users
    # For example: free users get 5 conversations per day
    current_usage = get_user_daily_chat_count(firebase_uid)  # You'd implement this
    limit_check = check_feature_limit('daily_chats', current_usage, free_limit=5)
    
    if not limit_check['allowed']:
        return jsonify({
            'error': 'Daily chat limit reached',
            'limit': limit_check['limit'],
            'usage': limit_check['usage'],
            'is_premium': limit_check['is_premium'],
            'upgrade_url': '/subscription'
        }), 403
    
    # Proceed with chat processing...
    return process_chat_message()

# Example 2: Premium-only features
@premium_required
def advanced_analytics_route():
    """
    Example of a premium-only feature.
    This decorator automatically checks subscription and redirects/errors if needed.
    """
    firebase_uid = session.get('user_id')
    
    # Generate advanced analytics only for premium users
    analytics_data = {
        'conversation_insights': generate_conversation_insights(firebase_uid),
        'usage_patterns': analyze_usage_patterns(firebase_uid),
        'ai_model_performance': get_model_performance_metrics(firebase_uid),
        'export_options': get_export_capabilities()
    }
    
    return jsonify(analytics_data)

# Example 3: Tiered feature access
def get_available_ai_models():
    """
    Example of how to provide different AI models based on subscription.
    """
    firebase_uid = session.get('user_id')
    
    # Basic models available to all users
    available_models = [
        {'id': 'gpt-3.5-turbo', 'name': 'GPT-3.5 Turbo', 'tier': 'free'},
        {'id': 'claude-3-haiku', 'name': 'Claude 3 Haiku', 'tier': 'free'}
    ]
    
    # Check if user has premium subscription
    try:
        stripe_service = StripeService()
        if stripe_service.is_user_premium(firebase_uid):
            # Add premium models
            available_models.extend([
                {'id': 'gpt-4', 'name': 'GPT-4', 'tier': 'premium'},
                {'id': 'claude-3-opus', 'name': 'Claude 3 Opus', 'tier': 'premium'},
                {'id': 'grok-2', 'name': 'Grok 2', 'tier': 'premium'}
            ])
    except Exception as e:
        # If Stripe service fails, continue with free models only
        pass
    
    return jsonify({'models': available_models})

# Example 4: Dynamic feature limiting in templates
def get_template_context(firebase_uid):
    """
    Example of providing subscription context to templates.
    This is automatically done via the context processor in app.py
    """
    try:
        stripe_service = StripeService()
        subscription_data = stripe_service.get_user_subscription(firebase_uid)
        is_premium = stripe_service.is_user_premium(firebase_uid)
        
        # Calculate usage limits
        daily_chats = get_user_daily_chat_count(firebase_uid)
        chat_limit = check_feature_limit('daily_chats', daily_chats, free_limit=5)
        
        return {
            'subscription': {
                'is_premium': is_premium,
                'subscription': subscription_data,
                'stripe_configured': True
            },
            'usage': {
                'daily_chats': chat_limit,
                'available_models': len(get_available_ai_models().get_json()['models']),
                'export_enabled': is_premium,
                'analytics_enabled': is_premium
            }
        }
    except Exception:
        # Fallback if Stripe is not configured
        return {
            'subscription': {
                'is_premium': False,
                'subscription': None,
                'stripe_configured': False
            },
            'usage': {
                'daily_chats': {'allowed': True, 'remaining': 5},
                'available_models': 2,
                'export_enabled': False,
                'analytics_enabled': False
            }
        }

# Example 5: Graceful degradation for missing Stripe config
def safe_subscription_check(firebase_uid, feature_name):
    """
    Example of how to safely check subscriptions with fallback behavior.
    """
    try:
        stripe_service = StripeService()
        return stripe_service.is_user_premium(firebase_uid)
    except Exception:
        # If Stripe is not configured, allow access (development mode)
        return True

# Example helper functions (you would implement these based on your needs)
def get_user_daily_chat_count(firebase_uid):
    """Get the number of chats user has had today."""
    # This would query your database for today's chat count
    # For demo purposes, return a sample value
    return 3

def process_chat_message():
    """Process the actual chat message."""
    return jsonify({'message': 'Chat processed successfully'})

def generate_conversation_insights(firebase_uid):
    """Generate insights from user's conversations."""
    return {
        'total_conversations': 150,
        'avg_messages_per_conversation': 8.5,
        'most_used_topics': ['AI', 'Programming', 'Science'],
        'peak_usage_hours': ['10:00-11:00', '14:00-15:00']
    }

def analyze_usage_patterns(firebase_uid):
    """Analyze user's usage patterns."""
    return {
        'daily_usage': [5, 8, 12, 6, 10, 15, 9],  # Last 7 days
        'preferred_models': ['gpt-4', 'claude-3-opus'],
        'session_duration_avg': '25 minutes'
    }

def get_model_performance_metrics(firebase_uid):
    """Get AI model performance for user."""
    return {
        'response_time_avg': '2.3 seconds',
        'satisfaction_score': 4.7,
        'most_helpful_responses': 85
    }

def get_export_capabilities():
    """Get available export options for premium users."""
    return {
        'formats': ['JSON', 'CSV', 'PDF'],
        'conversation_history': True,
        'analytics_reports': True,
        'custom_filters': True
    }

"""
Integration Instructions:

1. Add subscription checks to existing chat routes:
   - Modify api/chat_routes.py to include daily limits
   - Add premium model access in LLM services
   - Implement usage tracking in Firestore

2. Create premium-only features:
   - Advanced analytics dashboard
   - Conversation export functionality
   - Custom AI personalities
   - Priority support access

3. Update templates to show subscription status:
   - Add subscription badges in navigation
   - Show usage limits on dashboard
   - Display upgrade prompts when appropriate

4. Implement graceful degradation:
   - Allow development without Stripe configuration
   - Provide meaningful error messages
   - Fall back to free tier on service errors

5. Add monitoring and logging:
   - Track subscription conversion rates
   - Monitor feature usage by tier
   - Log payment and subscription events

Example template usage:

{% if subscription.is_premium %}
    <div class="premium-features">
        <h4>Premium Features</h4>
        <ul>
            <li>✅ Unlimited conversations</li>
            <li>✅ Premium AI models</li>
            <li>✅ Advanced analytics</li>
        </ul>
    </div>
{% else %}
    <div class="upgrade-prompt">
        <p>You have {{ usage.daily_chats.remaining }} conversations remaining today.</p>
        <a href="/subscription" class="btn btn-primary">Upgrade to Premium</a>
    </div>
{% endif %}
"""