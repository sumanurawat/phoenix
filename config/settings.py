"""
Application settings and configuration.
Centralizes all configuration variables for easier management.
"""
import os
from dotenv import load_dotenv
from config.gemini_models import GEMINI_MODELS

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")  # xAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

# LLM Models - Using constants from gemini_models.py
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", GEMINI_MODELS.PRIMARY)  # gemini-1.5-flash
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", GEMINI_MODELS.FALLBACK)  # gemini-1.5-flash-002
FINAL_FALLBACK_MODEL = GEMINI_MODELS.FINAL_FALLBACK  # gemini-1.5-flash

# Alternative model configurations (can be set via environment variables)
HIGH_PERFORMANCE_MODEL = os.getenv("HIGH_PERFORMANCE_MODEL", GEMINI_MODELS.HIGH_PERFORMANCE)  # gemini-2.5-pro
ULTRA_FAST_MODEL = os.getenv("ULTRA_FAST_MODEL", GEMINI_MODELS.ULTRA_FAST)  # gemini-1.5-flash-8b

# Flask configuration
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
FLASK_ENV = os.getenv("FLASK_ENV", "development")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

# LLM Service configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Session configuration
SESSION_TYPE = "filesystem"
SESSION_PERMANENT = False
SESSION_USE_SIGNER = True
SESSION_FILE_DIR = "./flask_session"
SESSION_FILE_THRESHOLD = 500

# Feature Gating Configuration
FEATURE_GATING_V2_ENABLED = os.getenv("FEATURE_GATING_V2_ENABLED", "false").lower() == "true"