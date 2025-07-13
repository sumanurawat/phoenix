"""
Enhanced Chat Service module with persistent database storage.
Supports multiple applications with conversation management.
"""
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from firebase_admin import firestore

from services.llm_service import LLMService
from services.enhanced_llm_service import EnhancedLLMService, ModelProvider
from services.utils import format_timestamp

# Configure logging
logger = logging.getLogger(__name__)

class EnhancedChatService:
    """Enhanced service for managing persistent chat conversations."""
    
    def __init__(self, db=None):
        """Initialize the enhanced chat service."""
        # Use EnhancedLLMService for multi-provider support
        self.llm_service = EnhancedLLMService()
        self.db = db or firestore.client()
    
    # Conversation Management
    
    def create_conversation(self, user_id: str, user_email: str, origin: str = "derplexity", 
                          title: str = None) -> Dict[str, Any]:
        """
        Create a new conversation.
        
        Args:
            user_id: User ID creating the conversation
            user_email: User email
            origin: Application origin (derplexity, robin, doogle)
            title: Optional conversation title
            
        Returns:
            Created conversation data
        """
        try:
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
            
            conversation_data = {
                "conversation_id": conversation_id,
                "title": title or "New Conversation",
                "origin": origin,
                "user_id": user_id,
                "user_email": user_email,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "message_count": 0,
                "model_settings": {
                    "current_model": self.llm_service.get_model_info().get("current_model", "gemini-1.5-flash-8b"),
                    "temperature": 0.7,
                    "max_tokens": 8192
                },
                "is_archived": False,
                "is_pinned": False,
                "is_deleted": False,
                "deleted_at": None,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "last_activity": firestore.SERVER_TIMESTAMP
            }
            
            # Save to Firestore
            self.db.collection('conversations').document(conversation_id).set(conversation_data)
            
            # Convert SERVER_TIMESTAMP to datetime for return
            conversation_data['created_at'] = datetime.now()
            conversation_data['updated_at'] = datetime.now()
            conversation_data['last_activity'] = datetime.now()
            
            logger.info(f"Created conversation {conversation_id} for user {user_id}")
            return conversation_data
            
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}", exc_info=True)
            raise
    
    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation by ID (user can only access their own).
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID requesting the conversation
            
        Returns:
            Conversation data or None if not found
        """
        try:
            doc_ref = self.db.collection('conversations').document(conversation_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            conversation_data = doc.to_dict()
            
            # Security check: user can only access their own conversations
            if conversation_data.get('user_id') != user_id:
                logger.warning(f"User {user_id} attempted to access conversation {conversation_id} owned by {conversation_data.get('user_id')}")
                return None
            
            return conversation_data
            
        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {str(e)}", exc_info=True)
            return None
    
    def get_user_conversations(self, user_id: str, origin: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversations for a user, optionally filtered by origin.
        
        Args:
            user_id: User ID
            origin: Optional origin filter (derplexity, robin, doogle)
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversations ordered by last activity
        """
        try:
            # Simplified query that works without indexes
            query = self.db.collection('conversations') \
                .where('user_id', '==', user_id)
            
            conversations = []
            for doc in query.stream():
                conversation_data = doc.to_dict()
                
                # Filter in code until indexes are created
                if conversation_data.get('is_deleted', False):
                    continue
                    
                if origin and conversation_data.get('origin') != origin:
                    continue
                    
                conversations.append(conversation_data)
            
            # Sort by updated_at in code
            conversations.sort(key=lambda x: x.get('updated_at', datetime.min), reverse=True)
            
            # Apply limit
            return conversations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting conversations for user {user_id}: {str(e)}", exc_info=True)
            return []
    
    def update_conversation(self, conversation_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update conversation metadata.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First verify user owns this conversation
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return False
            
            # Add updated timestamp
            updates['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Update the document
            self.db.collection('conversations').document(conversation_id).update(updates)
            
            logger.info(f"Updated conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating conversation {conversation_id}: {str(e)}", exc_info=True)
            return False
    
    def delete_conversation(self, conversation_id: str, user_id: str, hard_delete: bool = True) -> bool:
        """
        Delete a conversation and all its messages (hard delete by default).
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            hard_delete: If True, permanently delete; if False, soft delete (mark as deleted)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First verify user owns this conversation
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return False
            
            if hard_delete:
                # Hard delete: remove all messages first, then conversation
                logger.info(f"Hard deleting conversation {conversation_id} and all its messages")
                
                # Delete all messages in this conversation
                messages_query = self.db.collection('messages') \
                    .where('conversation_id', '==', conversation_id)
                
                deleted_messages = 0
                for message_doc in messages_query.stream():
                    message_doc.reference.delete()
                    deleted_messages += 1
                
                logger.info(f"Deleted {deleted_messages} messages from conversation {conversation_id}")
                
                # Delete the conversation document
                self.db.collection('conversations').document(conversation_id).delete()
                
            else:
                # Soft delete: mark as deleted (keep for recovery)
                self.db.collection('conversations').document(conversation_id).update({
                    'is_deleted': True,
                    'deleted_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"{'Hard' if hard_delete else 'Soft'} deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {str(e)}", exc_info=True)
            return False
    
    # Message Management
    
    def create_message(self, conversation_id: str, user_id: str, role: str, content: str, 
                      content_type: str = "text", model_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new message in a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            role: Message role (user, assistant, system)
            content: Message content
            content_type: Content type (text, image, document)
            model_info: Model information for assistant messages
            
        Returns:
            Created message data
        """
        try:
            # Verify conversation exists and user has access
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found or access denied")
            
            message_id = f"msg_{uuid.uuid4().hex[:12]}"
            
            # Get current message count for sequence number
            current_count = conversation.get('message_count', 0)
            sequence_number = current_count + 1
            
            message_data = {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "content_type": content_type,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "sequence_number": sequence_number,
                "user_id": user_id,
                "user_email": conversation.get('user_email'),
                "is_edited": False,
                "is_deleted": False,
                "deleted_at": None,
                "attachments": [],
                "citations": [],
                "feedback": {
                    "rating": None,
                    "helpful": None
                }
            }
            
            # Add model information for assistant messages
            if role == "assistant" and model_info:
                message_data.update({
                    "model_used": model_info.get("model_used"),
                    "model_settings": {
                        "temperature": model_info.get("temperature", 0.7),
                        "max_tokens": model_info.get("max_tokens", 8192)
                    },
                    "input_tokens": model_info.get("input_tokens", 0),
                    "output_tokens": model_info.get("output_tokens", 0),
                    "generation_time": model_info.get("generation_time", 0)
                })
            
            # Save message to Firestore
            self.db.collection('messages').document(message_id).set(message_data)
            
            # Update conversation metadata
            updates = {
                'message_count': sequence_number,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'last_activity': firestore.SERVER_TIMESTAMP
            }
            
            # Update token counts if this is an assistant message
            if role == "assistant" and model_info:
                updates['total_input_tokens'] = conversation.get('total_input_tokens', 0) + model_info.get('input_tokens', 0)
                updates['total_output_tokens'] = conversation.get('total_output_tokens', 0) + model_info.get('output_tokens', 0)
            
            self.db.collection('conversations').document(conversation_id).update(updates)
            
            # Convert SERVER_TIMESTAMP to datetime for return
            message_data['created_at'] = datetime.now()
            message_data['updated_at'] = datetime.now()
            
            logger.info(f"Created message {message_id} in conversation {conversation_id}")
            return message_data
            
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}", exc_info=True)
            raise
    
    def get_conversation_messages(self, conversation_id: str, user_id: str, 
                                limit: int = None) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            limit: Optional limit on number of messages
            
        Returns:
            List of messages ordered by sequence number
        """
        try:
            # Verify user has access to conversation
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return []
            
            # Simplified query that works without indexes
            query = self.db.collection('messages') \
                .where('conversation_id', '==', conversation_id)
            
            messages = []
            for doc in query.stream():
                message_data = doc.to_dict()
                
                # Filter in code until indexes are created
                if message_data.get('is_deleted', False):
                    continue
                    
                messages.append(message_data)
            
            # Sort by sequence_number in code
            messages.sort(key=lambda x: x.get('sequence_number', 0))
            
            # Apply limit if specified
            if limit:
                messages = messages[:limit]
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for conversation {conversation_id}: {str(e)}", exc_info=True)
            return []
    
    def delete_message(self, message_id: str, user_id: str, hard_delete: bool = True) -> bool:
        """
        Delete a message (hard delete by default).
        
        Args:
            message_id: Message ID
            user_id: User ID (for security check)
            hard_delete: If True, permanently delete; if False, soft delete (mark as deleted)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get message and verify user has access
            message_doc = self.db.collection('messages').document(message_id).get()
            if not message_doc.exists:
                return False
            
            message_data = message_doc.to_dict()
            conversation_id = message_data.get('conversation_id')
            
            # Verify user owns the conversation
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                return False
            
            if hard_delete:
                # Hard delete: permanently remove message
                self.db.collection('messages').document(message_id).delete()
                logger.info(f"Hard deleted message {message_id} from conversation {conversation_id}")
                
                # Update conversation message count
                current_messages = self.get_conversation_messages(conversation_id, user_id)
                self.db.collection('conversations').document(conversation_id).update({
                    'message_count': len(current_messages),
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
            else:
                # Soft delete: mark as deleted
                self.db.collection('messages').document(message_id).update({
                    'is_deleted': True,
                    'deleted_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                logger.info(f"Soft deleted message {message_id} from conversation {conversation_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {str(e)}", exc_info=True)
            return False
    
    # Enhanced Chat Operations
    
    def process_user_message(self, conversation_id: str, user_id: str, message: str, 
                           model_provider: str = None, model_name: str = None,
                           enable_thinking: bool = False, thinking_budget: int = 2048) -> Dict[str, Any]:
        """
        Process a user message and generate AI response.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            message: User message text
            model_provider: Optional model provider override
            model_name: Optional model name override
            enable_thinking: Enable Claude thinking mode
            thinking_budget: Token budget for thinking (1024-3072)
            
        Returns:
            Dictionary containing user message and AI response
        """
        try:
            # Create user message
            user_message = self.create_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="user",
                content=message
            )
            
            # Get conversation history for context
            messages = self.get_conversation_messages(conversation_id, user_id)
            
            # Prepare messages for LLM - only include user and assistant messages
            llm_messages = []
            for msg in messages:
                if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                    llm_messages.append({
                        "role": msg["role"], 
                        "content": msg["content"]
                    })
            
            # Debug logging
            logger.info(f"Processing message for conversation {conversation_id}")
            logger.info(f"Found {len(messages)} total messages, {len(llm_messages)} for LLM")
            
            # Ensure we have at least the user's message for LLM
            if not llm_messages:
                logger.warning(f"No messages found for conversation {conversation_id}, using current message only")
                llm_messages = [{"role": "user", "content": message}]
            
            # Switch model if requested
            if model_provider and model_name:
                original_provider = self.llm_service.provider
                original_model = self.llm_service.model
                try:
                    provider_enum = ModelProvider(model_provider)
                    self.llm_service.switch_model(provider_enum, model_name)
                    logger.info(f"Switched to {model_provider}:{model_name} for this message")
                except Exception as e:
                    logger.warning(f"Failed to switch model: {e}, using default")
            
            # Generate AI response
            response = self.llm_service.generate_text(
                self._format_messages_for_llm(llm_messages),
                enable_fallback=True,
                enable_thinking=enable_thinking,
                thinking_budget=thinking_budget
            )
            
            # Restore original model if we switched
            if model_provider and model_name:
                try:
                    self.llm_service.switch_model(original_provider, original_model)
                except:
                    pass
            
            if response.get("success"):
                # Create assistant message
                model_info = {
                    "model_used": response.get("model", response.get("model_used")),
                    "input_tokens": response.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": response.get("usage", {}).get("output_tokens", 0),
                    "generation_time": response.get("response_time", 0),
                    "fallback_used": response.get("fallback_used", False),
                    "provider": response.get("provider", "unknown")
                }
                
                # Add thinking content to message if available
                message_content = response["text"]
                if response.get("thinking"):
                    # Store thinking content in model_info for database storage
                    model_info["thinking"] = response["thinking"]
                
                assistant_message = self.create_message(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role="assistant",
                    content=message_content,
                    model_info=model_info
                )
                
                # Add thinking content to response for API
                if response.get("thinking"):
                    assistant_message["thinking"] = response["thinking"]
                
                # Update conversation title if this is the first exchange
                conversation = self.get_conversation(conversation_id, user_id)
                if conversation and conversation.get('message_count', 0) == 2 and conversation.get('title') == "New Conversation":
                    # Generate a title from the first user message
                    title = self._generate_conversation_title(message)
                    self.update_conversation(conversation_id, user_id, {'title': title})
                
                return {
                    "success": True,
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "model_info": self.llm_service.get_model_info()
                }
            else:
                # Create error message
                error_message = self.create_message(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role="assistant",
                    content="I'm sorry, I encountered an issue. Please try again."
                )
                
                return {
                    "success": False,
                    "user_message": user_message,
                    "assistant_message": error_message,
                    "error": response.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"Error processing user message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_conversation_title(self, first_message: str, max_length: int = 50) -> str:
        """
        Generate a conversation title using AI based on the first user message.
        
        Args:
            first_message: First user message
            max_length: Maximum title length
            
        Returns:
            Generated title
        """
        try:
            # Use LLM to generate a concise title
            title_prompt = [
                {
                    "role": "user", 
                    "content": f"Generate a short, concise title (max {max_length} characters) for a conversation that starts with this message: '{first_message}'. Only respond with the title, nothing else."
                }
            ]
            
            response = self.llm_service.chat(title_prompt)
            
            if response["success"] and response["text"]:
                title = response["text"].strip()
                # Remove quotes if present
                title = title.strip('"\'')
                
                # Ensure it's not too long
                if len(title) > max_length:
                    title = title[:max_length].rsplit(' ', 1)[0] + "..."
                
                return title
                
        except Exception as e:
            logger.warning(f"Failed to generate AI title: {e}")
        
        # Fallback to simple title generation
        title = first_message.strip()
        title = title.replace("?", "").replace("!", "")
        
        if len(title) > max_length:
            title = title[:max_length].rsplit(' ', 1)[0] + "..."
        
        return title or "New Conversation"
    
    def create_conversation_with_first_message(self, user_id: str, user_email: str, 
                                             first_message: str, origin: str = "derplexity",
                                             model_provider: str = None, model_name: str = None,
                                             enable_thinking: bool = False, thinking_budget: int = 2048) -> Dict[str, Any]:
        """
        Create a new conversation with the first user message and AI response.
        This is the main method to start a conversation.
        
        Args:
            user_id: User ID
            user_email: User email
            first_message: First user message
            origin: Application origin
            model_provider: Optional model provider override
            model_name: Optional model name override
            enable_thinking: Enable Claude thinking mode
            thinking_budget: Token budget for thinking (1024-3072)
            
        Returns:
            Complete conversation data with messages
        """
        try:
            # Generate AI title for the conversation
            ai_title = self._generate_conversation_title(first_message)
            
            # Create the conversation
            conversation = self.create_conversation(
                user_id=user_id,
                user_email=user_email,
                origin=origin,
                title=ai_title
            )
            
            # Add the first user message
            user_message = self.create_message(
                conversation_id=conversation['conversation_id'],
                user_id=user_id,
                role="user",
                content=first_message
            )
            
            # Switch model if requested
            if model_provider and model_name:
                original_provider = self.llm_service.provider
                original_model = self.llm_service.model
                try:
                    provider_enum = ModelProvider(model_provider)
                    self.llm_service.switch_model(provider_enum, model_name)
                    logger.info(f"Switched to {model_provider}:{model_name} for first message")
                except Exception as e:
                    logger.warning(f"Failed to switch model: {e}, using default")
            
            # Generate AI response
            llm_messages = [{"role": "user", "content": first_message}]
            response = self.llm_service.generate_text(
                self._format_messages_for_llm(llm_messages),
                enable_fallback=True,
                enable_thinking=enable_thinking,
                thinking_budget=thinking_budget
            )
            
            # Restore original model if we switched
            if model_provider and model_name:
                try:
                    self.llm_service.switch_model(original_provider, original_model)
                except:
                    pass
            
            if response.get("success"):
                # Create assistant message
                model_info = {
                    "model_used": response.get("model", response.get("model_used")),
                    "input_tokens": response.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": response.get("usage", {}).get("output_tokens", 0),
                    "generation_time": response.get("response_time", 0),
                    "fallback_used": response.get("fallback_used", False),
                    "provider": response.get("provider", "unknown")
                }
                
                # Add thinking content to message if available
                message_content = response["text"]
                if response.get("thinking"):
                    # Store thinking content in model_info for database storage
                    model_info["thinking"] = response["thinking"]
                
                assistant_message = self.create_message(
                    conversation_id=conversation['conversation_id'],
                    user_id=user_id,
                    role="assistant",
                    content=message_content,
                    model_info=model_info
                )
                
                # Add thinking content to response for API
                if response.get("thinking"):
                    assistant_message["thinking"] = response["thinking"]
                
                return {
                    "success": True,
                    "conversation": conversation,
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "model_info": self.llm_service.get_model_info()
                }
            else:
                # Create error message
                error_message = self.create_message(
                    conversation_id=conversation['conversation_id'],
                    user_id=user_id,
                    role="assistant",
                    content="I'm sorry, I encountered an issue. Please try again."
                )
                
                return {
                    "success": False,
                    "conversation": conversation,
                    "user_message": user_message,
                    "assistant_message": error_message,
                    "error": response.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"Error creating conversation with first message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def start_new_chat_session(self, user_id: str, user_email: str, origin: str = "derplexity") -> Dict[str, Any]:
        """
        Start a new chat session (creates conversation and returns session data).
        DEPRECATED: Use create_conversation_with_first_message instead.
        
        Args:
            user_id: User ID
            user_email: User email
            origin: Application origin
            
        Returns:
            Session data with conversation ID and metadata
        """
        try:
            conversation = self.create_conversation(user_id, user_email, origin)
            
            return {
                "conversation_id": conversation["conversation_id"],
                "title": conversation["title"],
                "created_at": conversation["created_at"],
                "messages": [],
                "model_info": self.llm_service.get_model_info()
            }
            
        except Exception as e:
            logger.error(f"Error starting new chat session: {str(e)}", exc_info=True)
            raise
    
    def _format_messages_for_llm(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into a prompt string for the LLM."""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")  # Prompt for the next response
        return "\n\n".join(prompt_parts)