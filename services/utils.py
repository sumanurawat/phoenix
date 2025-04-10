"""
Utility functions for services across the application.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_timestamp(timestamp: Optional[float] = None) -> str:
    """
    Format a timestamp into a readable string.
    
    Args:
        timestamp: Unix timestamp, defaults to current time if None
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now().timestamp()
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to maximum length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def format_chat_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format chat history into the structure expected by Gemini API.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        
    Returns:
        Formatted messages list
    """
    formatted_messages = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        formatted_messages.append({"role": role, "parts": [{"text": msg["content"]}]})
    return formatted_messages

def handle_api_error(error: Exception) -> Dict[str, Any]:
    """
    Handle API errors gracefully and return a user-friendly response.
    
    Args:
        error: The exception that was raised
        
    Returns:
        Dict containing error information
    """
    logger.error(f"API Error: {str(error)}", exc_info=True)
    return {
        "success": False,
        "error": str(error),
        "message": "Sorry, I encountered an issue. Please try again later.",
        "timestamp": format_timestamp()
    }