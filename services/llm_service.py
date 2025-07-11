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
    GEMINI_API_KEY, DEFAULT_MODEL, FALLBACK_MODEL, 
    FINAL_FALLBACK_MODEL, MAX_RETRIES, RETRY_DELAY
)
from config.gemini_models import get_model_info, GEMINI_MODELS
from services.utils import format_chat_history, handle_api_error

# Configure logging
logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with LLM models via Google's Gemini API."""
    
    def __init__(self):
        """Initialize the LLM service with API credentials."""
        if not GEMINI_API_KEY:
            logger.error("Gemini API key not found in environment variables")
            raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.models = {
            "primary": DEFAULT_MODEL,
            "fallback": FALLBACK_MODEL,
            "final_fallback": FINAL_FALLBACK_MODEL
        }
        self.current_model = self.models["primary"]
        
        # Log detailed model information
        primary_info = get_model_info(self.current_model)
        logger.info(f"🚀 LLM Service initialized successfully!")
        logger.info(f"📊 Primary model: {self.current_model}")
        logger.info(f"📝 Model info: {primary_info.get('name', 'Unknown')} - {primary_info.get('description', 'No description')}")
        logger.info(f"⚡ Performance: {primary_info.get('performance', 'Unknown')} | Speed: {primary_info.get('speed', 'Unknown')} | Cost: {primary_info.get('cost', 'Unknown')}")
        logger.info(f"🔧 Fallback models: {self.models['fallback']} → {self.models['final_fallback']}")
        
        # Log API key info (first 10 chars for security)
        logger.info(f"🔑 Using API key: {GEMINI_API_KEY[:10]}...")
        
        # Try to verify API connectivity
        try:
            available_models = self.list_available_models()
            if self.current_model.replace("models/", "") in [m.replace("models/", "") for m in available_models]:
                logger.info(f"✅ Primary model {self.current_model} is available via API")
            else:
                logger.warning(f"⚠️ Primary model {self.current_model} not found in available models")
                logger.info(f"📋 Available models: {len(available_models)} total")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify model availability: {e}")
    
    def list_available_models(self) -> List[str]:
        """
        List all available models.
        
        Returns:
            List of available model names
        """
        try:
            models = genai.list_models()
            available = [model.name for model in models if 'generateContent' in model.supported_generation_methods]
            logger.info(f"📋 Found {len(available)} available models")
            return available
        except Exception as e:
            logger.error(f"❌ Error listing models: {e}")
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
        logger.info(f"🤖 Generating text with model: {self.current_model}")
        logger.info(f"📝 Prompt length: {len(prompt)} characters")
        
        for attempt in range(MAX_RETRIES):
            try:
                model = genai.GenerativeModel(
                    model_name=self.current_model,
                    generation_config=self._create_generation_config(),
                    safety_settings=self._create_safety_settings()
                )
                
                logger.info(f"🚀 Making API call to {self.current_model} (attempt {attempt + 1})")
                start_time = time.time()
                response = model.generate_content(prompt)
                end_time = time.time()
                
                response_time = end_time - start_time
                logger.info(f"✅ Successfully generated text with {self.current_model}")
                logger.info(f"⏱️ Response time: {response_time:.2f} seconds")
                logger.info(f"📄 Response length: {len(response.text)} characters")
                
                # Log model info for verification
                model_info = get_model_info(self.current_model)
                logger.info(f"🏷️ Model used: {model_info.get('name', self.current_model)} ({model_info.get('generation', 'Unknown')} gen)")
                
                return {
                    "success": True,
                    "text": response.text,
                    "model_used": self.current_model,
                    "model_info": model_info,
                    "response_time": response_time,
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
        logger.info(f"💬 Starting chat with model: {self.current_model}")
        logger.info(f"📨 Message count: {len(messages)}")
        
        for attempt in range(MAX_RETRIES):
            try:
                model = genai.GenerativeModel(
                    model_name=self.current_model,
                    generation_config=self._create_generation_config(),
                    safety_settings=self._create_safety_settings()
                )
                
                chat = model.start_chat(history=formatted_messages[:-1] if len(formatted_messages) > 1 else [])
                logger.info(f"🚀 Sending chat message to {self.current_model} (attempt {attempt + 1})")
                start_time = time.time()
                response = chat.send_message(formatted_messages[-1]["parts"][0]["text"])
                end_time = time.time()
                
                response_time = end_time - start_time
                logger.info(f"✅ Successfully received chat response from {self.current_model}")
                logger.info(f"⏱️ Response time: {response_time:.2f} seconds")
                logger.info(f"📄 Response length: {len(response.text)} characters")
                
                # Log model info for verification
                model_info = get_model_info(self.current_model)
                logger.info(f"🏷️ Model used: {model_info.get('name', self.current_model)} ({model_info.get('generation', 'Unknown')} gen)")
                
                return {
                    "success": True,
                    "text": response.text,
                    "model_used": self.current_model,
                    "model_info": model_info,
                    "response_time": response_time,
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
            Dictionary with detailed model information
        """
        current_model_info = get_model_info(self.current_model)
        primary_model_info = get_model_info(self.models["primary"])
        
        return {
            "current_model": self.current_model,
            "current_model_info": current_model_info,
            "primary_model": self.models["primary"],
            "primary_model_info": primary_model_info,
            "fallback_models": [self.models["fallback"], self.models["final_fallback"]],
            "available_models": {
                "production_recommended": [GEMINI_MODELS.PRIMARY, GEMINI_MODELS.FALLBACK],
                "high_performance": [GEMINI_MODELS.HIGH_PERFORMANCE],
                "ultra_fast": [GEMINI_MODELS.ULTRA_FAST]
            }
        }