"""
Configuration for dataset discovery services.
Integrates with Phoenix's existing configuration system.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class ConfigurationError(Exception):
    """Raised when service configuration is invalid."""
    pass


class DatasetConfig:
    """Configuration for dataset discovery services."""
    
    # Service defaults
    DEFAULT_SEARCH_LIMIT = 20
    DEFAULT_SORT_BY = 'votes'  # Options: hottest, votes, updated, active
    CACHE_TIMEOUT = 3600  # 1 hour cache for search results
    REQUEST_TIMEOUT = 30  # API timeout in seconds
    MAX_RETRIES = 3
    
    # Dataset download limits (in MB) based on environment
    MAX_DOWNLOAD_SIZE_MB = {
        'development': 50,    # Cloud Run dev: 256MB memory
        'production': 100,    # Cloud Run prod: 512MB memory  
        'local': 500         # Local development: abundant memory
    }
    DOWNLOAD_WARNING_SIZE_MB = 25  # Show warning above this size
    
    # Kaggle API configuration
    KAGGLE_USERNAME: Optional[str] = None
    KAGGLE_KEY: Optional[str] = None
    
    def __init__(self):
        """Initialize configuration and validate credentials."""
        self._load_credentials()
        self._validate_credentials()
        logger.info("🔧 Dataset discovery configuration initialized successfully")
    
    def _load_credentials(self) -> None:
        """Load Kaggle credentials from environment variables or kaggle.json."""
        # Try environment variables first
        self.KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME')
        self.KAGGLE_KEY = os.getenv('KAGGLE_KEY')
        
        # If environment variables not found, try kaggle.json
        if not self.KAGGLE_USERNAME or not self.KAGGLE_KEY:
            kaggle_json_path = Path.home() / '.kaggle' / 'kaggle.json'
            
            if kaggle_json_path.exists():
                try:
                    with open(kaggle_json_path, 'r') as f:
                        credentials = json.load(f)
                        self.KAGGLE_USERNAME = self.KAGGLE_USERNAME or credentials.get('username')
                        self.KAGGLE_KEY = self.KAGGLE_KEY or credentials.get('key')
                        logger.info(f"📁 Loaded Kaggle credentials from {kaggle_json_path}")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"⚠️ Failed to load kaggle.json: {e}")
    
    def _validate_credentials(self) -> None:
        """Validate that required credentials are present."""
        if not self.KAGGLE_USERNAME:
            raise ConfigurationError(
                "KAGGLE_USERNAME not found. Please set the KAGGLE_USERNAME environment variable "
                "or ensure ~/.kaggle/kaggle.json contains valid credentials."
            )
        
        if not self.KAGGLE_KEY:
            raise ConfigurationError(
                "KAGGLE_KEY not found. Please set the KAGGLE_KEY environment variable "
                "or ensure ~/.kaggle/kaggle.json contains valid credentials."
            )
        
        # Log success (mask sensitive info)
        username_masked = f"{self.KAGGLE_USERNAME[:3]}***{self.KAGGLE_USERNAME[-2:]}" if len(self.KAGGLE_USERNAME) > 5 else "***"
        key_masked = f"{self.KAGGLE_KEY[:8]}..." if self.KAGGLE_KEY else "None"
        logger.info(f"🔑 Kaggle credentials validated - Username: {username_masked}, Key: {key_masked}")
    
    def get_kaggle_credentials(self) -> Dict[str, str]:
        """Get Kaggle credentials as a dictionary."""
        return {
            'username': self.KAGGLE_USERNAME,
            'key': self.KAGGLE_KEY
        }
    
    def get_search_defaults(self) -> Dict[str, Any]:
        """Get default search parameters."""
        return {
            'limit': self.DEFAULT_SEARCH_LIMIT,
            'sort_by': self.DEFAULT_SORT_BY,
            'timeout': self.REQUEST_TIMEOUT,
            'max_retries': self.MAX_RETRIES
        }
    
    def get_environment(self) -> str:
        """Detect current environment for size limits."""
        flask_env = os.getenv('FLASK_ENV', '').lower()
        production_url = os.getenv('PRODUCTION_URL', '')
        
        if flask_env == 'production' or 'phoenix-234619602247.us-central1.run.app' in production_url:
            return 'production'
        elif flask_env == 'development' or 'phoenix-dev' in production_url:
            return 'development'
        else:
            return 'local'
    
    def get_max_download_size_mb(self) -> int:
        """Get maximum allowed dataset download size for current environment."""
        env = self.get_environment()
        return self.MAX_DOWNLOAD_SIZE_MB.get(env, self.MAX_DOWNLOAD_SIZE_MB['local'])
    
    def get_download_warning_size_mb(self) -> int:
        """Get size threshold for showing download warnings."""
        return self.DOWNLOAD_WARNING_SIZE_MB
    
    def is_download_allowed(self, size_mb: float) -> tuple[bool, str]:
        """Check if dataset download is allowed based on size."""
        max_size = self.get_max_download_size_mb()
        env = self.get_environment()
        
        if size_mb <= max_size:
            return True, "Download allowed"
        else:
            return False, (
                f"Dataset too large ({size_mb:.1f} MB) for {env} environment. "
                f"Maximum allowed: {max_size} MB. This feature is under development - "
                f"we're working on supporting larger datasets soon!"
            )
    
    @classmethod
    def create_from_env(cls) -> 'DatasetConfig':
        """Factory method to create config from environment."""
        return cls()


# Global config instance
_config_instance: Optional[DatasetConfig] = None


def get_config() -> DatasetConfig:
    """Get or create the global dataset configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = DatasetConfig()
    return _config_instance