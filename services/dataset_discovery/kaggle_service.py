"""
Kaggle service for searching and retrieving datasets from Kaggle API.
Handles authentication, API calls, and data transformation.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import kaggle
    # Don't import KaggleApi here to avoid automatic authentication
    KAGGLE_AVAILABLE = True
    KaggleApi = None  # Will be imported later when needed
except ImportError:
    KAGGLE_AVAILABLE = False
    KaggleApi = None

from .config import DatasetConfig
from .exceptions import (
    KaggleAuthenticationError, KaggleAPIError, DatasetNotFoundError,
    RateLimitError, TimeoutError, ConfigurationError
)
from .models import DatasetFile

logger = logging.getLogger(__name__)


class KaggleSearchService:
    """Service for searching and retrieving datasets from Kaggle."""
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """
        Initialize the Kaggle search service.
        
        Args:
            config: Optional configuration object. If None, will create from environment.
        """
        if not KAGGLE_AVAILABLE:
            raise ConfigurationError(
                "Kaggle API package not available",
                details="Please install kaggle package: pip install kaggle"
            )
        
        self.config = config or DatasetConfig()
        self.api: Optional[KaggleApi] = None
        self._authenticated = False
        self._auth_time: Optional[datetime] = None
        
        logger.info("🔧 Kaggle search service initialized")
    
    def authenticate(self) -> None:
        """
        Authenticate with Kaggle API using configured credentials.
        Uses lazy authentication - only authenticates when needed.
        
        Raises:
            KaggleAuthenticationError: If authentication fails
        """
        try:
            if self._authenticated and self.api:
                logger.debug("📡 Already authenticated with Kaggle API")
                return
            
            logger.info("🔑 Authenticating with Kaggle API...")
            
            # Lazy import KaggleApi to avoid automatic authentication on import
            from kaggle.api.kaggle_api_extended import KaggleApi
            
            # Initialize API instance
            self.api = KaggleApi()
            
            # Set credentials
            credentials = self.config.get_kaggle_credentials()
            self.api.username = credentials['username']
            self.api.key = credentials['key']
            
            # Authenticate
            self.api.authenticate()
            
            self._authenticated = True
            self._auth_time = datetime.now()
            
            logger.info(f"✅ Successfully authenticated with Kaggle API as {credentials['username']}")
            
        except Exception as e:
            error_msg = f"Failed to authenticate with Kaggle API: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            if "401" in str(e) or "Unauthorized" in str(e):
                raise KaggleAuthenticationError(
                    "Invalid Kaggle credentials",
                    details="Please check your KAGGLE_USERNAME and KAGGLE_KEY"
                )
            else:
                raise KaggleAuthenticationError(error_msg, details=str(e))
    
    def search_datasets(self, query: str, limit: int = None, sort_by: str = None) -> List[Dict[str, Any]]:
        """
        Search for datasets on Kaggle.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            sort_by: Sort order ('hottest', 'votes', 'updated', 'active')
            
        Returns:
            List of dataset dictionaries from Kaggle API
            
        Raises:
            KaggleAPIError: If API request fails
            KaggleAuthenticationError: If authentication fails
        """
        # Set defaults
        defaults = self.config.get_search_defaults()
        limit = limit or defaults['limit']
        sort_by = sort_by or defaults['sort_by']
        
        # Ensure authenticated
        self._ensure_authenticated()
        
        # Sanitize query
        sanitized_query = self._sanitize_query(query)
        
        logger.info(f"🔍 Searching Kaggle datasets: '{sanitized_query}' (limit: {limit}, sort: {sort_by})")
        
        start_time = time.time()
        
        try:
            # Call Kaggle API with retry logic
            datasets = self._call_with_retry(
                lambda: list(self.api.dataset_list(
                    search=sanitized_query,
                    sort_by=sort_by,
                    max_size=limit
                ))
            )
            
            search_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"✅ Found {len(datasets)} datasets in {search_time}ms")
            
            # Convert to dictionaries if needed
            result = []
            for dataset in datasets:
                if hasattr(dataset, '__dict__'):
                    # Convert object to dict
                    dataset_dict = {}
                    for attr in dir(dataset):
                        if not attr.startswith('_') and not callable(getattr(dataset, attr)):
                            try:
                                value = getattr(dataset, attr)
                                dataset_dict[attr] = value
                            except:
                                continue
                    result.append(dataset_dict)
                else:
                    result.append(dataset)
            
            return result
            
        except Exception as e:
            self._handle_api_error(e, f"searching datasets with query '{sanitized_query}'")
    
    def get_dataset_files(self, dataset_ref: str) -> List[DatasetFile]:
        """
        Get file list for a specific dataset.
        
        Args:
            dataset_ref: Dataset reference (username/dataset-name)
            
        Returns:
            List of DatasetFile objects
            
        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            KaggleAPIError: If API request fails
        """
        self._ensure_authenticated()
        
        logger.debug(f"📁 Fetching file list for dataset: {dataset_ref}")
        
        try:
            # Split dataset ref
            if '/' not in dataset_ref:
                raise ValueError("Dataset ref must be in format 'username/dataset-name'")
            
            owner_slug, dataset_slug = dataset_ref.split('/', 1)
            
            # Call Kaggle API
            files = self._call_with_retry(
                lambda: list(self.api.dataset_list_files(owner_slug, dataset_slug))
            )
            
            # Convert to DatasetFile objects
            dataset_files = []
            for file_info in files:
                try:
                    if hasattr(file_info, 'name') and hasattr(file_info, 'size'):
                        dataset_files.append(DatasetFile(
                            name=file_info.name,
                            size_bytes=file_info.size
                        ))
                    elif isinstance(file_info, dict):
                        dataset_files.append(DatasetFile(
                            name=file_info.get('name', ''),
                            size_bytes=file_info.get('size', 0)
                        ))
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing file info: {e}")
                    continue
            
            logger.debug(f"📁 Found {len(dataset_files)} files for {dataset_ref}")
            return dataset_files
            
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise DatasetNotFoundError(dataset_ref, details=str(e))
            else:
                self._handle_api_error(e, f"fetching files for dataset '{dataset_ref}'")
    
    def _ensure_authenticated(self) -> None:
        """Ensure we are authenticated with Kaggle API."""
        if not self._authenticated:
            self.authenticate()
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize query string for safe API usage."""
        import re
        
        # Remove special characters except spaces, hyphens, and underscores
        sanitized = re.sub(r'[^a-zA-Z0-9\s\-_]', '', query.strip())
        
        # Replace multiple spaces with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200].strip()
        
        return sanitized
    
    def _call_with_retry(self, api_call, max_retries: int = None) -> Any:
        """
        Call Kaggle API with exponential backoff retry logic.
        
        Args:
            api_call: Function to call
            max_retries: Maximum number of retries
            
        Returns:
            API call result
            
        Raises:
            Various API errors based on failure type
        """
        max_retries = max_retries or self.config.MAX_RETRIES
        base_delay = 1.0
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return api_call()
                
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    break
                
                # Determine if we should retry
                if self._should_retry_error(e):
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"🔄 API call failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    # Don't retry for certain errors
                    break
        
        # If we get here, all retries failed
        raise last_exception
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        error_str = str(error).lower()
        
        # Don't retry authentication or permission errors
        if any(phrase in error_str for phrase in ['401', '403', 'unauthorized', 'forbidden']):
            return False
        
        # Don't retry not found errors
        if any(phrase in error_str for phrase in ['404', 'not found']):
            return False
        
        # Retry server errors, timeouts, and rate limits
        if any(phrase in error_str for phrase in ['500', '502', '503', '504', 'timeout', 'rate limit']):
            return True
        
        # Retry connection errors
        if any(phrase in error_str for phrase in ['connection', 'network', 'dns']):
            return True
        
        return False
    
    def _handle_api_error(self, error: Exception, context: str) -> None:
        """
        Convert Kaggle API errors to custom exceptions with helpful messages.
        
        Args:
            error: Original exception
            context: Description of what was being attempted
            
        Raises:
            Appropriate custom exception
        """
        error_str = str(error).lower()
        
        logger.error(f"❌ Kaggle API error while {context}: {error}")
        
        # Rate limit errors
        if 'rate limit' in error_str or '429' in error_str:
            raise RateLimitError(
                f"Rate limit exceeded while {context}",
                details="Please wait before making more requests to Kaggle API"
            )
        
        # Timeout errors
        if 'timeout' in error_str:
            raise TimeoutError(
                f"Request timed out while {context}",
                details="The Kaggle API request took too long to complete"
            )
        
        # Authentication errors
        if any(phrase in error_str for phrase in ['401', '403', 'unauthorized', 'forbidden']):
            raise KaggleAuthenticationError(
                f"Authentication failed while {context}",
                details="Please check your Kaggle credentials"
            )
        
        # Not found errors
        if '404' in error_str or 'not found' in error_str:
            raise DatasetNotFoundError(
                context.split("'")[-2] if "'" in context else "unknown",
                details=str(error)
            )
        
        # Generic API errors
        raise KaggleAPIError(
            f"Kaggle API error while {context}",
            details=str(error)
        )