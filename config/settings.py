"""
Application settings and configuration.
Centralizes all configuration variables for easier management.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

# LLM Models
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-pro-exp-03-25")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-2.0-flash")
FINAL_FALLBACK_MODEL = "gemini-1.5-flash"

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