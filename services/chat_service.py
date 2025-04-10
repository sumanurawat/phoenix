"""
Chat Service module for managing chat sessions and interactions.
This service uses the LLM Service for generating responses.
"""
import time
import logging
from typing import Dict, Any

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
            # Pass the entire message history to the LLM service
            response = self.llm_service.chat(chat["messages"])
            
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
            "model_info": self.llm_service.get_model_info()
        }