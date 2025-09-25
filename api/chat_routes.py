"""
API endpoints for chat functionality.
"""
from flask import Blueprint, jsonify, request, session
from api.auth_routes import login_required

from services.chat_service import ChatService
from services.document_service import DocumentService, SUPPORTED_FILE_TYPES
from middleware.csrf_protection import csrf_protect

# Feature gating imports
from config.settings import FEATURE_GATING_V2_ENABLED
if FEATURE_GATING_V2_ENABLED:
    from services.feature_gating import feature_required
else:
    from services.subscription_middleware import feature_limited

# Initialize services
chat_service = ChatService()
document_service = DocumentService()

# Create Blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

def apply_chat_feature_gating(f):
    """Apply appropriate feature gating decorator based on configuration."""
    if FEATURE_GATING_V2_ENABLED:
        return feature_required('chat_basic')(f)
    else:
        return feature_limited('chat_messages')(f)

@chat_bp.route('/message', methods=['POST'])
@csrf_protect  
@login_required
@apply_chat_feature_gating
def chat_message():
    """Process a new chat message and return a response."""
    if "chat" not in session:
        session["chat"] = chat_service.start_new_chat()
    
    # Get message from request
    data = request.json
    message = data.get('message', '')
    
    if not message.strip():
        return jsonify({"error": "Message cannot be empty"}), 400
    
    # Process the message and get a response (counts handled in service)
    updated_chat = chat_service.process_user_message(session["chat"], message)
    session["chat"] = updated_chat
    
    # Return the updated chat
    return jsonify({"chat": updated_chat})

def apply_document_upload_gating(f):
    """Apply appropriate feature gating decorator for document upload."""
    if FEATURE_GATING_V2_ENABLED:
        return feature_required('chat_document_upload')(f)
    else:
        return feature_limited('documents_uploaded')(f)

@chat_bp.route('/upload-document', methods=['POST'])
@csrf_protect
@login_required
@apply_document_upload_gating
def upload_document():
    """Upload a document to be used as context in the chat."""
    if "chat" not in session:
        session["chat"] = chat_service.start_new_chat()
    
    # Check if a file was uploaded
    if 'document' not in request.files:
        return jsonify({"error": "No document found"}), 400
    
    file = request.files['document']
    
    # Check if the file has a name
    if file.filename == '':
        return jsonify({"error": "No document selected"}), 400
    
    # Check if the file type is supported
    if not document_service.is_supported_filetype(file.mimetype):
        return jsonify({
            "error": "Unsupported file type",
            "supported_types": list(SUPPORTED_FILE_TYPES.keys())
        }), 400
    
    try:
        # Process the document
        document_info = document_service.process_document(file)
        
        # Add the document to the chat session
        updated_chat = chat_service.add_document(session["chat"], document_info)
        session["chat"] = updated_chat
        
        # Return success
        return jsonify({
            "success": True,
            "chat": updated_chat,
            "document": {
                "id": document_info["id"],
                "filename": document_info["original_filename"],
                "text_preview": document_info["text_preview"]
            }
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/clear', methods=['POST'])
@csrf_protect
@login_required
def clear_chat():
    """Clear the current chat history."""
    if "chat" in session:
        session["chat"] = chat_service.clear_chat_history(session["chat"])
    else:
        session["chat"] = chat_service.start_new_chat()
    
    return jsonify({"chat": session["chat"]})

def apply_models_gating(f):
    """Apply appropriate feature gating decorator for model access."""
    if FEATURE_GATING_V2_ENABLED:
        return feature_required('chat_basic', check_limits=False)(f)  # No usage increment for model list
    else:
        return f  # No gating in legacy system for model list

@chat_bp.route('/models', methods=['GET'])
@login_required
@apply_models_gating
def get_models():
    """Get information about available models."""
    if "chat" not in session:
        session["chat"] = chat_service.start_new_chat()
    
    return jsonify({"model_info": session["chat"]["model_info"]})