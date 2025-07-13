"""
Dataset Discovery Service for Phoenix Flask Application.

This module provides dataset search and evaluation capabilities using Kaggle's API.
It includes scoring algorithms for dataset quality and relevance evaluation.
"""
import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .config import get_config, DatasetConfig
from .kaggle_service import KaggleSearchService
from .evaluator import DatasetEvaluator
from .smart_search_agent import SmartSearchAgent
from .models import DatasetInfo, SearchRequest, SearchResponse, ServiceHealth, DatasetFile
from .exceptions import DatasetDiscoveryError, SearchValidationError

logger = logging.getLogger(__name__)


class DatasetDiscoveryService:
    """
    Main service class that orchestrates dataset discovery operations.
    Combines Kaggle API integration with evaluation algorithms.
    """
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """
        Initialize the dataset discovery service.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or get_config()
        self.kaggle_service = KaggleSearchService(self.config)
        self.evaluator = DatasetEvaluator()
        
        # Initialize smart search agent with LLM service
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            self.smart_search_agent = SmartSearchAgent(self.kaggle_service, llm_service)
            self.use_smart_search = True
            logger.info("🤖 Smart search agent initialized")
        except Exception as e:
            logger.warning(f"⚠️ Smart search agent failed to initialize: {e}, using fallback search")
            self.smart_search_agent = None
            self.use_smart_search = False
        
        logger.info("🚀 Dataset Discovery Service initialized successfully")
    
    def search_datasets(self, search_request: SearchRequest) -> SearchResponse:
        """
        Search for datasets and return scored, ranked results.
        
        Args:
            search_request: Search parameters
            
        Returns:
            SearchResponse with ranked datasets
            
        Raises:
            SearchValidationError: If search parameters are invalid
            DatasetDiscoveryError: If search fails
        """
        start_time = time.time()
        
        logger.info(f"🔍 Starting dataset search: '{search_request.query}' (limit: {search_request.limit})")
        
        try:
            # Use smart search agent if available, otherwise fallback to direct search
            if self.use_smart_search and self.smart_search_agent:
                logger.info("🤖 Using smart search agent")
                search_result = self.smart_search_agent.smart_search(
                    user_query=search_request.sanitized_query,
                    limit=search_request.limit * 2  # Get more results for better filtering
                )
                raw_datasets = search_result.datasets
                search_metadata = {
                    'search_terms_used': search_result.search_terms_used,
                    'ai_generated_terms': search_result.ai_generated_terms
                }
            else:
                logger.info("🔍 Using direct Kaggle search")
                raw_datasets = self.kaggle_service.search_datasets(
                    query=search_request.sanitized_query,
                    limit=search_request.limit,
                    sort_by=search_request.sort_by
                )
                search_metadata = {
                    'search_terms_used': [search_request.sanitized_query],
                    'ai_generated_terms': False
                }
            
            logger.info(f"📊 Processing {len(raw_datasets)} raw datasets from search")
            
            # Process and score each dataset
            scored_datasets = []
            
            for raw_dataset in raw_datasets:
                try:
                    # Skip file fetching for search results to avoid API limits and 403 errors
                    # File info (count, size) should come from the main dataset API response
                    files = []
                    
                    # Create DatasetInfo object
                    dataset_info = DatasetInfo.from_kaggle_dataset(raw_dataset, files)
                    
                    # Calculate scores
                    quality_score = self.evaluator.calculate_quality_score(dataset_info)
                    relevance_score = self.evaluator.calculate_relevance_score(dataset_info, search_request.query)
                    combined_score = self.evaluator.combine_scores(quality_score, relevance_score)
                    
                    # Update dataset with scores
                    dataset_info.quality_score = quality_score
                    dataset_info.relevance_score = relevance_score
                    dataset_info.combined_score = combined_score
                    
                    # Apply quality filter
                    if quality_score >= search_request.min_quality_score:
                        scored_datasets.append(dataset_info)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error processing dataset {raw_dataset.get('ref', 'unknown')}: {e}")
                    continue
            
            # Sort by combined score (descending)
            scored_datasets.sort(key=lambda d: d.combined_score, reverse=True)
            
            # Calculate timing
            search_time_ms = int((time.time() - start_time) * 1000)
            
            # Create response
            response = SearchResponse(
                query=search_request.query,
                total_found=len(raw_datasets),
                returned_count=len(scored_datasets),
                datasets=scored_datasets,
                search_time_ms=search_time_ms,
                cached=False
            )
            
            # Add smart search metadata if available
            if search_metadata:
                response.search_metadata = search_metadata
            
            logger.info(
                f"✅ Search completed: {response.returned_count} datasets returned "
                f"(filtered from {response.total_found}) in {search_time_ms}ms"
            )
            
            return response
            
        except SearchValidationError:
            raise  # Re-raise validation errors as-is
        except Exception as e:
            logger.error(f"❌ Dataset search failed: {e}", exc_info=True)
            raise DatasetDiscoveryError(f"Search failed: {str(e)}")
    
    def get_health_status(self) -> ServiceHealth:
        """
        Get service health status including Kaggle authentication check.
        
        Returns:
            ServiceHealth object with current status
        """
        timestamp = datetime.now()
        checks = {}
        
        try:
            # Test Kaggle authentication
            self.kaggle_service.authenticate()
            kaggle_authenticated = True
            checks['kaggle_auth'] = {
                'status': 'ok',
                'message': 'Successfully authenticated with Kaggle API'
            }
        except Exception as e:
            kaggle_authenticated = False
            checks['kaggle_auth'] = {
                'status': 'error',
                'message': f'Kaggle authentication failed: {str(e)}'
            }
        
        # Test configuration
        try:
            config_test = self.config.get_kaggle_credentials()
            checks['configuration'] = {
                'status': 'ok',
                'message': 'Configuration loaded successfully'
            }
        except Exception as e:
            checks['configuration'] = {
                'status': 'error',
                'message': f'Configuration error: {str(e)}'
            }
        
        # Determine overall status
        if kaggle_authenticated and checks.get('configuration', {}).get('status') == 'ok':
            status = 'healthy'
        elif kaggle_authenticated or checks.get('configuration', {}).get('status') == 'ok':
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return ServiceHealth(
            status=status,
            timestamp=timestamp,
            kaggle_authenticated=kaggle_authenticated,
            checks=checks
        )


# Factory function for easy service creation
def create_dataset_service(config: Optional[DatasetConfig] = None) -> DatasetDiscoveryService:
    """
    Factory function to create a configured dataset discovery service.
    
    Args:
        config: Optional configuration object
        
    Returns:
        Configured DatasetDiscoveryService instance
    """
    return DatasetDiscoveryService(config)