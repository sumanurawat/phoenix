"""
Chat Service module for managing chat sessions and interactions.
This service uses the LLM Service for generating responses.
"""
import time
import logging
from typing import Dict, Any, List

from services.llm_service import LLMService
from services.utils import format_timestamp

# Configure logging
logger = logging.getLogger(__name__)

class ChatService:
    """Service for managing chat interactions."""
    
    def __init__(self):
        """Initialize the chat service."""
        self.llm_service = LLMService()
    
    def start_new_chat(self) -> Dict[str, Any]:
        """
        Start a new chat session.
        
        Returns:
            Dictionary with new chat session info
        """
        return {
            "id": f"chat_{int(time.time())}",
            "created_at": format_timestamp(),
            "messages": [],
            "documents": [],  # New field to store uploaded documents
            "model_info": self.llm_service.get_model_info()
        }
    
    def add_user_message(self, chat: Dict[str, Any], message: str) -> Dict[str, Any]:
        """
        Add a user message to the chat history.
        
        Args:
            chat: Chat session dictionary
            message: User message text
            
        Returns:
            Updated chat session
        """
        # Create a copy of the chat to avoid modifying the original
        updated_chat = chat.copy()
        updated_chat["messages"] = chat["messages"].copy()
        
        # Add the message
        updated_chat["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": format_timestamp()
        })
        
        return updated_chat
    
    def add_document(self, chat: Dict[str, Any], document_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a document to the chat session.
        
        Args:
            chat: Chat session dictionary
            document_info: Document information dictionary
            
        Returns:
            Updated chat session
        """
        # Create a copy of the chat to avoid modifying the original
        updated_chat = chat.copy()
        
        # Initialize documents list if it doesn't exist
        if "documents" not in updated_chat:
            updated_chat["documents"] = []
        else:
            updated_chat["documents"] = chat["documents"].copy()
        
        # Add the document
        updated_chat["documents"].append(document_info)
        
        # Add a system message about the document
        if updated_chat["messages"]:
            updated_chat["messages"] = chat["messages"].copy()
        else:
            updated_chat["messages"] = []
            
        updated_chat["messages"].append({
            "role": "system",
            "content": f"Document uploaded: {document_info['original_filename']}",
            "timestamp": format_timestamp(),
            "document_id": document_info["id"],
            "is_document": True
        })
        
        return updated_chat
    
    def _prepare_context_with_documents(self, chat: Dict[str, Any]) -> str:
        """
        Prepare context string with document content for the LLM.
        
        Args:
            chat: Chat session dictionary
            
        Returns:
            Context string with document information
        """
        if not chat.get("documents"):
            return ""
        
        context = "I have the following documents as context:\n\n"
        
        for doc in chat["documents"]:
            context += f"Document: {doc['original_filename']}\n"
            context += f"Content: {doc['extracted_text']}\n\n"
        
        context += "Please use this information to answer my questions when relevant.\n\n"
        
        return context
    
    def generate_response(self, chat: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a response to the latest message in the chat.
        
        Args:
            chat: Chat session dictionary
            
        Returns:
            Updated chat session with response
        """
        if not chat["messages"]:
            logger.warning("Attempted to generate a response with no messages in the chat")
            return chat
        
        # Create a copy of the chat to avoid modifying the original
        updated_chat = chat.copy()
        updated_chat["messages"] = chat["messages"].copy()
        
        try:
            # Prepare context-enhanced messages for the LLM
            messages_for_llm = self._prepare_messages_with_context(chat)
            
            # Pass the enhanced message history to the LLM service
            response = self.llm_service.chat(messages_for_llm)
            
            # Add the assistant's response to the chat
            if response["success"]:
                updated_chat["messages"].append({
                    "role": "assistant",
                    "content": response["text"],
                    "timestamp": format_timestamp(),
                    "model_used": response["model_used"]
                })
            else:
                # Add error message if generation failed
                updated_chat["messages"].append({
                    "role": "assistant",
                    "content": "I'm sorry, I encountered an issue. Please try again.",
                    "timestamp": format_timestamp(),
                    "error": True
                })
            
            # Update model info
            updated_chat["model_info"] = self.llm_service.get_model_info()
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            # Add error message
            updated_chat["messages"].append({
                "role": "assistant",
                "content": "I'm sorry, I encountered an unexpected error. Please try again.",
                "timestamp": format_timestamp(),
                "error": True
            })
        
        return updated_chat
    
    def _prepare_messages_with_context(self, chat: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Prepare messages with document context for the LLM.
        
        Args:
            chat: Chat session dictionary
            
        Returns:
            List of messages with document context
        """
        # Make a copy of the messages
        messages = [msg.copy() for msg in chat["messages"] if msg["role"] != "system"]
        
        # If we have documents, add a system message with context
        document_context = self._prepare_context_with_documents(chat)
        if document_context:
            # Insert the context as a system message at the beginning
            messages.insert(0, {
                "role": "system",
                "content": document_context,
                "timestamp": format_timestamp()
            })
        
        return messages
    
    def process_user_message(self, chat: Dict[str, Any], message: str) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            chat: Chat session dictionary
            message: User message text
            
        Returns:
            Updated chat session with response
        """
        # Add user message
        updated_chat = self.add_user_message(chat, message)
        
        # Generate response
        return self.generate_response(updated_chat)
    
    def clear_chat_history(self, chat: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clear the chat history while preserving the chat ID.
        
        Args:
            chat: Chat session dictionary
            
        Returns:
            Fresh chat session with same ID
        """
        return {
            "id": chat["id"],
            "created_at": chat["created_at"],
            "cleared_at": format_timestamp(),
            "messages": [],
            "documents": [],  # Clear documents as well
            "model_info": self.llm_service.get_model_info()
        }