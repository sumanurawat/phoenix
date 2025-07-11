#!/usr/bin/env python3
"""
Test script to verify Gemini API configuration and functionality.
This script will help debug the Derplexity chat issue.
"""
import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment_variables():
    """Check if required environment variables are set."""
    logger.info("=== Environment Variables Check ===")
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    
    if gemini_key:
        logger.info(f"✓ GEMINI_API_KEY is set: {gemini_key[:10]}...")
    else:
        logger.error("✗ GEMINI_API_KEY is not set")
    
    if google_key:
        logger.info(f"✓ GOOGLE_API_KEY is set: {google_key[:10]}...")
    else:
        logger.warning("⚠ GOOGLE_API_KEY is not set")
    
    return gemini_key

def test_gemini_configuration(api_key):
    """Test Gemini API configuration."""
    logger.info("=== Gemini API Configuration Test ===")
    
    try:
        genai.configure(api_key=api_key)
        logger.info("✓ Gemini API configured successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to configure Gemini API: {e}")
        return False

def list_available_models(api_key):
    """List all available Gemini models."""
    logger.info("=== Available Models ===")
    
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        
        available_models = []
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                logger.info(f"✓ {model.name}")
        
        logger.info(f"Total available models: {len(available_models)}")
        return available_models
    except Exception as e:
        logger.error(f"✗ Failed to list models: {e}")
        return []

def test_model_generation(api_key, model_name="gemini-1.5-flash"):
    """Test text generation with a specific model."""
    logger.info(f"=== Testing Model: {model_name} ===")
    
    try:
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello! Please respond with 'API test successful' if you can see this.")
        
        logger.info(f"✓ Model {model_name} response: {response.text}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to generate content with {model_name}: {e}")
        return False

def test_chat_functionality(api_key, model_name="gemini-1.5-flash"):
    """Test chat functionality."""
    logger.info(f"=== Testing Chat with {model_name} ===")
    
    try:
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(model_name)
        chat = model.start_chat(history=[])
        
        response = chat.send_message("Hello! Can you confirm this chat test is working?")
        logger.info(f"✓ Chat response: {response.text}")
        
        # Test follow-up message
        response2 = chat.send_message("What was my first message?")
        logger.info(f"✓ Follow-up response: {response2.text}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed chat test with {model_name}: {e}")
        return False

def test_llm_service_integration():
    """Test the LLM service integration."""
    logger.info("=== Testing LLM Service Integration ===")
    
    try:
        from services.llm_service import LLMService
        
        llm_service = LLMService()
        logger.info("✓ LLM Service initialized successfully")
        
        # Test text generation
        result = llm_service.generate_text("Hello! Please confirm this test is working.")
        if result.get("success"):
            logger.info(f"✓ LLM Service text generation: {result.get('text')}")
            logger.info(f"✓ Model used: {result.get('model_used')}")
        else:
            logger.error(f"✗ LLM Service text generation failed: {result}")
        
        # Test chat
        messages = [{"role": "user", "content": "Hello! Test chat functionality."}]
        chat_result = llm_service.chat(messages)
        if chat_result.get("success"):
            logger.info(f"✓ LLM Service chat: {chat_result.get('text')}")
            logger.info(f"✓ Model used: {chat_result.get('model_used')}")
        else:
            logger.error(f"✗ LLM Service chat failed: {chat_result}")
        
        # Get model info
        model_info = llm_service.get_model_info()
        logger.info(f"✓ Current model: {model_info.get('current_model')}")
        logger.info(f"✓ Primary model: {model_info.get('primary_model')}")
        logger.info(f"✓ Fallback models: {model_info.get('fallback_models')}")
        
        return True
    except Exception as e:
        logger.error(f"✗ LLM Service integration test failed: {e}")
        return False

def main():
    """Main test function."""
    logger.info("🚀 Starting Gemini API and LLM Service Test")
    logger.info("=" * 50)
    
    # Check environment variables
    api_key = check_environment_variables()
    if not api_key:
        logger.error("Cannot proceed without GEMINI_API_KEY")
        return
    
    print()
    
    # Test API configuration
    if not test_gemini_configuration(api_key):
        logger.error("Cannot proceed with failed API configuration")
        return
    
    print()
    
    # List available models
    models = list_available_models(api_key)
    print()
    
    # Test model generation
    if models:
        # Test with the first available model
        test_model = models[0] if models else "gemini-1.5-flash"
        test_model_generation(api_key, test_model)
        print()
        
        # Test chat functionality
        test_chat_functionality(api_key, test_model)
        print()
    
    # Test LLM service integration
    test_llm_service_integration()
    
    logger.info("=" * 50)
    logger.info("🏁 Test completed!")

if __name__ == "__main__":
    main()
