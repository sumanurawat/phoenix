"""
Enhanced Chat API Routes with persistent conversation management.
Provides endpoints for conversation and message CRUD operations.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from functools import wraps

from services.enhanced_chat_service import EnhancedChatService
from api.auth_routes import login_required
from middleware.csrf_protection import csrf_protect

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
enhanced_chat_bp = Blueprint('enhanced_chat', __name__)

# Initialize service
chat_service = EnhancedChatService()

def handle_api_error(func):
    """Decorator to handle API errors consistently."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Client error in {func.__name__}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            logger.error(f"Server error in {func.__name__}: {str(e)}", exc_info=True)
            return jsonify({"success": False, "error": "Internal server error"}), 500
    return wrapper

def get_current_user():
    """Get current user info from session."""
    return {
        'uid': session.get('user_id'),
        'email': session.get('user_email'),
        'name': session.get('user_name')
    }

# Conversation Management Endpoints

@enhanced_chat_bp.route('/api/conversations', methods=['GET'])
@login_required
@handle_api_error
def get_conversations():
    """Get user's conversations, optionally filtered by origin."""
    user = get_current_user()
    origin = request.args.get('origin')  # derplexity
    limit = request.args.get('limit', 50, type=int)
    
    conversations = chat_service.get_user_conversations(
        user_id=user['uid'],
        origin=origin,
        limit=min(limit, 100)  # Cap at 100
    )
    
    # Convert Firestore timestamps to ISO format for JSON serialization
    for conversation in conversations:
        for field in ['created_at', 'updated_at', 'last_activity', 'deleted_at']:
            if conversation.get(field):
                conversation[field] = conversation[field].isoformat()
    
    return jsonify({
        "success": True,
        "conversations": conversations,
        "count": len(conversations)
    })

@enhanced_chat_bp.route('/api/conversations', methods=['POST'])
@csrf_protect
@login_required
@handle_api_error
def create_conversation():
    """Create a new conversation."""
    user = get_current_user()
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    origin = data.get('origin', 'derplexity')
    title = data.get('title')
    
    # Validate origin
    valid_origins = ['derplexity']
    if origin not in valid_origins:
        return jsonify({"success": False, "error": f"Invalid origin. Must be one of: {valid_origins}"}), 400
    
    conversation = chat_service.create_conversation(
        user_id=user['uid'],
        user_email=user['email'],
        origin=origin,
        title=title
    )
    
    # Convert timestamps for JSON serialization
    for field in ['created_at', 'updated_at', 'last_activity']:
        if conversation.get(field):
            conversation[field] = conversation[field].isoformat()
    
    return jsonify({
        "success": True,
        "conversation": conversation
    })

@enhanced_chat_bp.route('/api/conversations/<conversation_id>', methods=['GET'])
@login_required
@handle_api_error
def get_conversation(conversation_id):
    """Get a specific conversation."""
    user = get_current_user()
    
    conversation = chat_service.get_conversation(conversation_id, user['uid'])
    
    if not conversation:
        return jsonify({"success": False, "error": "Conversation not found"}), 404
    
    # Convert timestamps for JSON serialization
    for field in ['created_at', 'updated_at', 'last_activity', 'deleted_at']:
        if conversation.get(field):
            conversation[field] = conversation[field].isoformat()
    
    return jsonify({
        "success": True,
        "conversation": conversation
    })

@enhanced_chat_bp.route('/api/conversations/<conversation_id>', methods=['PUT'])
@csrf_protect
@login_required
@handle_api_error
def update_conversation(conversation_id):
    """Update a conversation."""
    user = get_current_user()
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    # Only allow updating certain fields
    allowed_fields = ['title', 'is_archived', 'is_pinned']
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not updates:
        return jsonify({"success": False, "error": "No valid fields to update"}), 400
    
    success = chat_service.update_conversation(conversation_id, user['uid'], updates)
    
    if not success:
        return jsonify({"success": False, "error": "Failed to update conversation"}), 404
    
    return jsonify({"success": True})

@enhanced_chat_bp.route('/api/conversations/<conversation_id>', methods=['DELETE'])
@csrf_protect
@login_required
@handle_api_error
def delete_conversation(conversation_id):
    """Delete a conversation and all its messages permanently."""
    user = get_current_user()
    # Default to hard delete, allow soft delete via query param
    hard_delete = request.args.get('hard', 'true').lower() == 'true'
    
    success = chat_service.delete_conversation(conversation_id, user['uid'], hard_delete)
    
    if not success:
        return jsonify({"success": False, "error": "Failed to delete conversation"}), 404
    
    return jsonify({"success": True, "deleted": "permanently" if hard_delete else "soft"})

# Message Management Endpoints

@enhanced_chat_bp.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
@login_required
@handle_api_error
def get_conversation_messages(conversation_id):
    """Get messages for a conversation."""
    user = get_current_user()
    limit = request.args.get('limit', type=int)
    
    messages = chat_service.get_conversation_messages(
        conversation_id=conversation_id,
        user_id=user['uid'],
        limit=limit
    )
    
    # Convert timestamps for JSON serialization
    for message in messages:
        for field in ['created_at', 'updated_at', 'deleted_at']:
            if message.get(field):
                message[field] = message[field].isoformat()
    
    return jsonify({
        "success": True,
        "messages": messages,
        "count": len(messages)
    })

@enhanced_chat_bp.route('/api/conversations/<conversation_id>/messages', methods=['POST'])
@csrf_protect
@login_required
@handle_api_error
def send_message(conversation_id):
    """Send a message and get AI response."""
    user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('message'):
        return jsonify({"success": False, "error": "Message content is required"}), 400
    
    message = data['message'].strip()
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty"}), 400
    
    # Get model configuration from request
    model_provider = data.get('model_provider')
    model_name = data.get('model_name')
    enable_thinking = data.get('enable_thinking', False)
    thinking_budget = data.get('thinking_budget', 2048)
    
    result = chat_service.process_user_message(
        conversation_id=conversation_id,
        user_id=user['uid'],
        message=message,
        model_provider=model_provider,
        model_name=model_name,
        enable_thinking=enable_thinking,
        thinking_budget=thinking_budget
    )
    
    if result.get('success'):
        # Convert timestamps for JSON serialization
        for msg_key in ['user_message', 'assistant_message']:
            if result.get(msg_key):
                for field in ['created_at', 'updated_at']:
                    if result[msg_key].get(field):
                        result[msg_key][field] = result[msg_key][field].isoformat()
    
    return jsonify(result)

@enhanced_chat_bp.route('/api/messages/<message_id>', methods=['DELETE'])
@csrf_protect
@login_required
@handle_api_error
def delete_message(message_id):
    """Delete a message permanently."""
    user = get_current_user()
    # Default to hard delete, allow soft delete via query param
    hard_delete = request.args.get('hard', 'true').lower() == 'true'
    
    success = chat_service.delete_message(message_id, user['uid'], hard_delete)
    
    if not success:
        return jsonify({"success": False, "error": "Failed to delete message"}), 404
    
    return jsonify({"success": True, "deleted": "permanently" if hard_delete else "soft"})

# Chat Session Management

@enhanced_chat_bp.route('/api/chat/start-conversation', methods=['POST'])
@csrf_protect
@login_required
@handle_api_error
def start_conversation_with_message():
    """Start a new conversation with the first message."""
    user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('message'):
        return jsonify({"success": False, "error": "Message is required"}), 400
    
    message = data['message'].strip()
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty"}), 400
    
    origin = data.get('origin', 'derplexity')
    model_provider = data.get('model_provider')
    model_name = data.get('model_name')
    enable_thinking = data.get('enable_thinking', False)
    thinking_budget = data.get('thinking_budget', 2048)
    
    result = chat_service.create_conversation_with_first_message(
        user_id=user['uid'],
        user_email=user['email'],
        first_message=message,
        origin=origin,
        model_provider=model_provider,
        model_name=model_name,
        enable_thinking=enable_thinking,
        thinking_budget=thinking_budget
    )
    
    if result.get('success'):
        # Convert timestamps for JSON serialization
        for key in ['conversation', 'user_message', 'assistant_message']:
            if result.get(key):
                for field in ['created_at', 'updated_at']:
                    if result[key].get(field):
                        result[key][field] = result[key][field].isoformat()
    
    return jsonify(result)

@enhanced_chat_bp.route('/api/chat/new-session', methods=['POST'])
@csrf_protect
@login_required
@handle_api_error
def start_new_session():
    """Start a new chat session (creates a conversation). DEPRECATED."""
    user = get_current_user()
    data = request.get_json() or {}
    
    origin = data.get('origin', 'derplexity')
    
    session_data = chat_service.start_new_chat_session(
        user_id=user['uid'],
        user_email=user['email'],
        origin=origin
    )
    
    # Convert timestamps for JSON serialization
    if session_data.get('created_at'):
        session_data['created_at'] = session_data['created_at'].isoformat()
    
    return jsonify({
        "success": True,
        "session": session_data
    })

@enhanced_chat_bp.route('/api/chat/load-session/<conversation_id>', methods=['POST'])
@csrf_protect
@login_required
@handle_api_error
def load_session(conversation_id):
    """Load an existing chat session."""
    user = get_current_user()
    
    # Get conversation
    conversation = chat_service.get_conversation(conversation_id, user['uid'])
    if not conversation:
        return jsonify({"success": False, "error": "Conversation not found"}), 404
    
    # Get messages
    messages = chat_service.get_conversation_messages(conversation_id, user['uid'])
    
    # Convert timestamps for JSON serialization
    for field in ['created_at', 'updated_at', 'last_activity']:
        if conversation.get(field):
            conversation[field] = conversation[field].isoformat()
    
    for message in messages:
        for field in ['created_at', 'updated_at']:
            if message.get(field):
                message[field] = message[field].isoformat()
    
    session_data = {
        "conversation_id": conversation["conversation_id"],
        "title": conversation["title"],
        "created_at": conversation["created_at"],
        "updated_at": conversation["updated_at"],
        "messages": messages,
        "model_info": chat_service.llm_service.get_model_info()
    }
    
    return jsonify({
        "success": True,
        "session": session_data
    })

# Utility Endpoints

@enhanced_chat_bp.route('/api/chat/models', methods=['GET'])
@handle_api_error
def get_models():
    """Get available models information (public endpoint)."""
    model_info = chat_service.llm_service.get_model_info()
    return jsonify({
        "success": True,
        "models": model_info
    })

@enhanced_chat_bp.route('/api/conversations/<conversation_id>/title', methods=['PUT'])
@csrf_protect
@login_required
@handle_api_error
def update_conversation_title(conversation_id):
    """Update conversation title."""
    user = get_current_user()
    data = request.get_json()
    
    if not data or not data.get('title'):
        return jsonify({"success": False, "error": "Title is required"}), 400
    
    title = data['title'].strip()
    if not title:
        return jsonify({"success": False, "error": "Title cannot be empty"}), 400
    
    success = chat_service.update_conversation(conversation_id, user['uid'], {'title': title})
    
    if not success:
        return jsonify({"success": False, "error": "Failed to update title"}), 404
    
    return jsonify({"success": True})