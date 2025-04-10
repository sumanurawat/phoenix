"""
API endpoints for chat functionality.
"""
from flask import Blueprint, jsonify, request, session

from services.chat_service import ChatService

# Initialize services
chat_service = ChatService()

# Create Blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

@chat_bp.route('/message', methods=['POST'])
def chat_message():
    """Process a new chat message and return a response."""
    if "chat" not in session:
        session["chat"] = chat_service.start_new_chat()
    
    # Get message from request
    data = request.json
    message = data.get('message', '')
    
    if not message.strip():
        return jsonify({"error": "Message cannot be empty"}), 400
    
    # Process the message and get a response
    updated_chat = chat_service.process_user_message(session["chat"], message)
    session["chat"] = updated_chat
    
    # Return the updated chat
    return jsonify({"chat": updated_chat})

@chat_bp.route('/clear', methods=['POST'])
def clear_chat():
    """Clear the current chat history."""
    if "chat" in session:
        session["chat"] = chat_service.clear_chat_history(session["chat"])
    else:
        session["chat"] = chat_service.start_new_chat()
    
    return jsonify({"chat": session["chat"]})

@chat_bp.route('/models', methods=['GET'])
def get_models():
    """Get information about available models."""
    if "chat" not in session:
        session["chat"] = chat_service.start_new_chat()
    
    return jsonify({"model_info": session["chat"]["model_info"]})