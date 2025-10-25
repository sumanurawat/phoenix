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

# Google Cloud Storage Configuration
# For video generation and Reel Maker features
VIDEO_STORAGE_BUCKET = os.getenv("VIDEO_STORAGE_BUCKET")
REEL_MAKER_GCS_BUCKET = os.getenv("REEL_MAKER_GCS_BUCKET")
VIDEO_GENERATION_BUCKET = os.getenv("VIDEO_GENERATION_BUCKET")

# Cloudflare R2 Configuration (for image storage - $0 egress for future video platform)
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "ai-image-posts-prod")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

# Image Generation Configuration
IMAGE_STORAGE_BUCKET = os.getenv("IMAGE_STORAGE_BUCKET", "phoenix-images")  # Legacy GCS, now using R2
DEFAULT_IMAGE_ASPECT_RATIO = "9:16"  # Portrait mode (vertical)
IMAGE_SAFETY_FILTER = "block_few"  # Lowest safety level
IMAGE_PERSON_GENERATION = "allow_all"  # No restrictions on person generation

# Instagram OAuth Configuration
INSTAGRAM_CLIENT_ID = os.getenv("INSTAGRAM_CLIENT_ID")
INSTAGRAM_CLIENT_SECRET = os.getenv("INSTAGRAM_CLIENT_SECRET")
INSTAGRAM_REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI")  # e.g., https://phoenix.app/api/socials/instagram/callback

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Token Package Price IDs (configured in Stripe Dashboard)
STRIPE_TOKEN_STARTER_PRICE_ID = os.getenv("STRIPE_TOKEN_STARTER_PRICE_ID")   # 50 tokens - $4.99
STRIPE_TOKEN_POPULAR_PRICE_ID = os.getenv("STRIPE_TOKEN_POPULAR_PRICE_ID")   # 110 tokens - $9.99 (10% bonus)
STRIPE_TOKEN_PRO_PRICE_ID = os.getenv("STRIPE_TOKEN_PRO_PRICE_ID")           # 250 tokens - $19.99 (25% bonus)
STRIPE_TOKEN_CREATOR_PRICE_ID = os.getenv("STRIPE_TOKEN_CREATOR_PRICE_ID")   # 700 tokens - $49.99 (40% bonus)

# Application Base URL (for Stripe redirects)
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080")

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