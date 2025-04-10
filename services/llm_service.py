"""
LLM Service module for handling interactions with large language models.
This service provides functionality to interact with Google's Gemini API.
"""
import time
import logging
from typing import List, Dict, Any

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from config.settings import (
    GOOGLE_API_KEY, DEFAULT_MODEL, FALLBACK_MODEL, 
    FINAL_FALLBACK_MODEL, MAX_RETRIES, RETRY_DELAY
)
from services.utils import format_chat_history, handle_api_error

# Configure logging
logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with LLM models via Google's Gemini API."""
    
    def __init__(self):
        """Initialize the LLM service with API credentials."""
        if not GOOGLE_API_KEY:
            logger.error("Gemini API key not found in environment variables")
            raise ValueError("Gemini API key not found. Please set the GOOGLE_API_KEY environment variable.")
        
        genai.configure(api_key=GOOGLE_API_KEY)
        self.models = {
            "primary": DEFAULT_MODEL,
            "fallback": FALLBACK_MODEL,
            "final_fallback": FINAL_FALLBACK_MODEL
        }
        self.current_model = self.models["primary"]
        
        # Log available models
        logger.info(f"Initialized LLM service with primary model: {self.current_model}")
    
    def list_available_models(self) -> List[str]:
        """
        List all available models.
        
        Returns:
            List of available model names
        """
        try:
            models = genai.list_models()
            return [model.name for model in models if 'generateContent' in model.supported_generation_methods]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def switch_to_fallback_model(self) -> str:
        """
        Switch to fallback model when quota is exceeded.
        
        Returns:
            Name of the model switched to
        """
        if self.current_model == self.models["primary"]:
            self.current_model = self.models["fallback"]
            logger.warning(f"Switched to fallback model: {self.current_model}")
        elif self.current_model == self.models["fallback"]:
            self.current_model = self.models["final_fallback"]
            logger.warning(f"Switched to final fallback model: {self.current_model}")
        else:
            logger.error("No more fallback models available")
            
        return self.current_model
    
    def _create_generation_config(self) -> Dict[str, Any]:
        """
        Create a configuration for text generation.
        
        Returns:
            Generation configuration dictionary
        """
        return {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 4096,  # Increased from 1024 to 4096 to allow longer responses
        }
    
    def _create_safety_settings(self) -> List[Dict[str, Any]]:
        """
        Create safety settings for content generation.
        
        Returns:
            List of safety setting dictionaries
        """
        # Default safety settings (using medium thresholds)
        return []  # Using default settings for now
    
    def generate_text(self, prompt: str) -> Dict[str, Any]:
        """
        Generate text using the Gemini model.
        
        Args:
            prompt: Text prompt for generation
            
        Returns:
            Dictionary containing the generated text and metadata
        """
        for attempt in range(MAX_RETRIES):
            try:
                model = genai.GenerativeModel(
                    model_name=self.current_model,
                    generation_config=self._create_generation_config(),
                    safety_settings=self._create_safety_settings()
                )
                
                response = model.generate_content(prompt)
                
                return {
                    "success": True,
                    "text": response.text,
                    "model_used": self.current_model,
                    "timestamp": time.time()
                }
                
            except ResourceExhausted as e:
                logger.warning(f"Resource exhausted on attempt {attempt+1}: {str(e)}")
                self.switch_to_fallback_model()
                if attempt == MAX_RETRIES - 1:
                    return handle_api_error(e)
                    
            except Exception as e:
                logger.error(f"Error generating text on attempt {attempt+1}: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    return handle_api_error(e)
                time.sleep(RETRY_DELAY)
    
    def chat(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Conduct a chat conversation using the Gemini model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            Dictionary containing the response and metadata
        """
        formatted_messages = format_chat_history(messages)
        
        for attempt in range(MAX_RETRIES):
            try:
                model = genai.GenerativeModel(
                    model_name=self.current_model,
                    generation_config=self._create_generation_config(),
                    safety_settings=self._create_safety_settings()
                )
                
                chat = model.start_chat(history=formatted_messages[:-1] if len(formatted_messages) > 1 else [])
                response = chat.send_message(formatted_messages[-1]["parts"][0]["text"])
                
                return {
                    "success": True,
                    "text": response.text,
                    "model_used": self.current_model,
                    "timestamp": time.time()
                }
                
            except ResourceExhausted as e:
                logger.warning(f"Resource exhausted on attempt {attempt+1}: {str(e)}")
                self.switch_to_fallback_model()
                if attempt == MAX_RETRIES - 1:
                    return handle_api_error(e)
                    
            except Exception as e:
                logger.error(f"Error in chat on attempt {attempt+1}: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    return handle_api_error(e)
                time.sleep(RETRY_DELAY)
                
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the currently used model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "current_model": self.current_model,
            "primary_model": self.models["primary"],
            "fallback_models": [self.models["fallback"], self.models["final_fallback"]]
        }