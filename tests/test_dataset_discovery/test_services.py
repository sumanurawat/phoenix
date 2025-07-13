"""
Tests for dataset discovery service components.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from services.dataset_discovery.config import DatasetConfig
from services.dataset_discovery.evaluator import DatasetEvaluator
from services.dataset_discovery.models import DatasetInfo, SearchRequest, DatasetFile
from services.dataset_discovery.exceptions import (
    ConfigurationError, SearchValidationError, KaggleAuthenticationError
)


class TestDatasetConfig:
    """Test cases for DatasetConfig."""
    
    def test_config_with_env_vars(self):
        """Test config initialization with environment variables."""
        with patch.dict('os.environ', {
            'KAGGLE_USERNAME': 'testuser',
            'KAGGLE_KEY': 'testkey123'
        }):
            config = DatasetConfig()
            assert config.KAGGLE_USERNAME == 'testuser'
            assert config.KAGGLE_KEY == 'testkey123'
    
    def test_config_missing_credentials(self):
        """Test config initialization with missing credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(ConfigurationError) as exc_info:
                    DatasetConfig()
                assert "KAGGLE_USERNAME not found" in str(exc_info.value)
    
    def test_config_with_kaggle_json(self):
        """Test config initialization with kaggle.json file."""
        mock_credentials = {
            'username': 'jsonuser',
            'key': 'jsonkey123'
        }
        
        with patch.dict('os.environ', {}, clear=True):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = str(mock_credentials).replace("'", '"')
                    with patch('json.load', return_value=mock_credentials):
                        config = DatasetConfig()
                        assert config.KAGGLE_USERNAME == 'jsonuser'
                        assert config.KAGGLE_KEY == 'jsonkey123'
    
    def test_get_kaggle_credentials(self):
        """Test getting Kaggle credentials."""
        with patch.dict('os.environ', {
            'KAGGLE_USERNAME': 'testuser',
            'KAGGLE_KEY': 'testkey123'
        }):
            config = DatasetConfig()
            creds = config.get_kaggle_credentials()
            assert creds['username'] == 'testuser'
            assert creds['key'] == 'testkey123'
    
    def test_get_search_defaults(self):
        """Test getting search defaults."""
        with patch.dict('os.environ', {
            'KAGGLE_USERNAME': 'testuser',
            'KAGGLE_KEY': 'testkey123'
        }):
            config = DatasetConfig()
            defaults = config.get_search_defaults()
            assert defaults['limit'] == config.DEFAULT_SEARCH_LIMIT
            assert defaults['sort_by'] == config.DEFAULT_SORT_BY


class TestDatasetEvaluator:
    """Test cases for DatasetEvaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create DatasetEvaluator instance."""
        return DatasetEvaluator()
    
    @pytest.fixture
    def sample_dataset(self):
        """Create sample dataset for testing."""
        return DatasetInfo(
            ref="test/sample-dataset",
            title="Sample Climate Data",
            subtitle="Temperature and precipitation data",
            description="Comprehensive climate data from weather stations worldwide",
            owner="climateresearch",
            vote_count=150,
            download_count=5000,
            view_count=15000,
            total_bytes=50 * 1024 * 1024,  # 50MB
            file_count=5,
            version_count=3,
            created_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_date=datetime.now(timezone.utc),
            license_name="CC BY 4.0",
            tags=["climate", "weather", "temperature", "data"],
            files=[
                DatasetFile("temperatures.csv", 20*1024*1024),
                DatasetFile("precipitation.csv", 15*1024*1024),
                DatasetFile("metadata.json", 1024),
                DatasetFile("readme.txt", 2048),
                DatasetFile("stations.csv", 10*1024*1024)
            ]
        )
    
    def test_calculate_quality_score(self, evaluator, sample_dataset):
        """Test quality score calculation."""
        score = evaluator.calculate_quality_score(sample_dataset)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be a decent quality dataset
    
    def test_calculate_relevance_score_exact_match(self, evaluator, sample_dataset):
        """Test relevance score with exact title match."""
        score = evaluator.calculate_relevance_score(sample_dataset, "climate")
        
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # Should have high relevance
    
    def test_calculate_relevance_score_partial_match(self, evaluator, sample_dataset):
        """Test relevance score with partial match."""
        score = evaluator.calculate_relevance_score(sample_dataset, "weather station")
        
        assert 0.0 <= score <= 1.0
        assert score > 0.3  # Should have some relevance
    
    def test_calculate_relevance_score_no_match(self, evaluator, sample_dataset):
        """Test relevance score with no match."""
        score = evaluator.calculate_relevance_score(sample_dataset, "cryptocurrency blockchain")
        
        assert 0.0 <= score <= 1.0
        assert score < 0.3  # Should have low relevance
    
    def test_combine_scores(self, evaluator):
        """Test score combination."""
        quality = 0.8
        relevance = 0.6
        
        # Default weights (0.4, 0.6)
        combined = evaluator.combine_scores(quality, relevance)
        expected = quality * 0.4 + relevance * 0.6
        assert abs(combined - expected) < 0.001
        
        # Custom weights
        combined_custom = evaluator.combine_scores(quality, relevance, weights=(0.7, 0.3))
        expected_custom = quality * 0.7 + relevance * 0.3
        assert abs(combined_custom - expected_custom) < 0.001
    
    def test_popularity_score_calculation(self, evaluator, sample_dataset):
        """Test popularity component of quality score."""
        # This tests the internal _calculate_popularity_score method
        score = evaluator._calculate_popularity_score(sample_dataset)
        
        assert 0.0 <= score <= 1.0
        
        # Test with zero votes and downloads
        zero_dataset = DatasetInfo(
            ref="test/zero",
            title="Test",
            subtitle="",
            description="",
            owner="test",
            vote_count=0,
            download_count=0,
            view_count=0,
            total_bytes=0,
            file_count=0,
            version_count=1,
            created_date=None,
            updated_date=None,
            license_name=""
        )
        
        zero_score = evaluator._calculate_popularity_score(zero_dataset)
        assert zero_score == 0.0
    
    def test_recency_score_calculation(self, evaluator, sample_dataset):
        """Test recency component of quality score."""
        score = evaluator._calculate_recency_score(sample_dataset)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Recent dataset should score high
        
        # Test with no update date
        no_date_dataset = DatasetInfo(
            ref="test/nodate",
            title="Test",
            subtitle="",
            description="",
            owner="test",
            vote_count=0,
            download_count=0,
            view_count=0,
            total_bytes=0,
            file_count=0,
            version_count=1,
            created_date=None,
            updated_date=None,
            license_name=""
        )
        
        no_date_score = evaluator._calculate_recency_score(no_date_dataset)
        assert no_date_score == 0.3  # Default score
    
    def test_completeness_score_calculation(self, evaluator, sample_dataset):
        """Test completeness component of quality score."""
        score = evaluator._calculate_completeness_score(sample_dataset)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Complete dataset should score high
        
        # Test with minimal dataset
        minimal_dataset = DatasetInfo(
            ref="test/minimal",
            title="Test",
            subtitle="",
            description="",
            owner="test",
            vote_count=0,
            download_count=0,
            view_count=0,
            total_bytes=0,
            file_count=0,
            version_count=1,
            created_date=None,
            updated_date=None,
            license_name=""
        )
        
        minimal_score = evaluator._calculate_completeness_score(minimal_dataset)
        assert minimal_score == 0.0
    
    def test_size_appropriateness_score(self, evaluator, sample_dataset):
        """Test size appropriateness component of quality score."""
        score = evaluator._calculate_size_appropriateness_score(sample_dataset)
        
        assert 0.0 <= score <= 1.0
        assert score == 1.0  # 50MB is in optimal range
        
        # Test with very small dataset
        small_dataset = DatasetInfo(
            ref="test/small",
            title="Test",
            subtitle="",
            description="",
            owner="test",
            vote_count=0,
            download_count=0,
            view_count=0,
            total_bytes=1024,  # 1KB
            file_count=1,
            version_count=1,
            created_date=None,
            updated_date=None,
            license_name=""
        )
        
        small_score = evaluator._calculate_size_appropriateness_score(small_dataset)
        assert small_score < 1.0
    
    def test_text_tokenization(self, evaluator):
        """Test text tokenization utility."""
        tokens = evaluator._tokenize_text("Hello, World! This is a test.")
        expected = ["hello", "world", "this", "is", "test"]
        assert tokens == expected
        
        # Test with empty string
        empty_tokens = evaluator._tokenize_text("")
        assert empty_tokens == []
        
        # Test with punctuation
        punct_tokens = evaluator._tokenize_text("data-science & machine_learning")
        assert "data" in punct_tokens
        assert "science" in punct_tokens
        assert "machine" in punct_tokens
        assert "learning" in punct_tokens


class TestSearchRequest:
    """Test cases for SearchRequest model."""
    
    def test_valid_search_request(self):
        """Test creating valid search request."""
        request = SearchRequest(
            query="climate change",
            limit=10,
            sort_by="votes",
            min_quality_score=0.5
        )
        
        assert request.query == "climate change"
        assert request.limit == 10
        assert request.sort_by == "votes"
        assert request.min_quality_score == 0.5
    
    def test_search_request_defaults(self):
        """Test search request with default values."""
        request = SearchRequest(query="test")
        
        assert request.query == "test"
        assert request.limit == 20
        assert request.sort_by == "hottest"
        assert request.min_quality_score == 0.0
    
    def test_search_request_validation_short_query(self):
        """Test validation with too short query."""
        with pytest.raises(SearchValidationError) as exc_info:
            SearchRequest(query="a")
        assert "at least 2 characters" in str(exc_info.value)
    
    def test_search_request_validation_empty_query(self):
        """Test validation with empty query."""
        with pytest.raises(SearchValidationError):
            SearchRequest(query="")
    
    def test_search_request_validation_high_limit(self):
        """Test validation with limit too high."""
        with pytest.raises(SearchValidationError) as exc_info:
            SearchRequest(query="test", limit=150)
        assert "between 1 and 100" in str(exc_info.value)
    
    def test_search_request_validation_invalid_sort(self):
        """Test validation with invalid sort_by."""
        with pytest.raises(SearchValidationError) as exc_info:
            SearchRequest(query="test", sort_by="invalid")
        assert "hottest, votes, updated, active" in str(exc_info.value)
    
    def test_search_request_validation_invalid_quality_score(self):
        """Test validation with invalid quality score."""
        with pytest.raises(SearchValidationError) as exc_info:
            SearchRequest(query="test", min_quality_score=1.5)
        assert "between 0.0 and 1.0" in str(exc_info.value)
    
    def test_sanitized_query(self):
        """Test query sanitization."""
        request = SearchRequest(query="climate change!!! @#$%")
        sanitized = request.sanitized_query
        
        assert "!" not in sanitized
        assert "@" not in sanitized
        assert "climate change" in sanitized


class TestDatasetInfo:
    """Test cases for DatasetInfo model."""
    
    def test_dataset_info_properties(self):
        """Test computed properties."""
        files = [
            DatasetFile("data.csv", 1024*1024),
            DatasetFile("readme.txt", 2048),
            DatasetFile("metadata.json", 512)
        ]
        
        dataset = DatasetInfo(
            ref="user/dataset",
            title="Test Dataset",
            subtitle="A test",
            description="Description",
            owner="user",
            vote_count=100,
            download_count=1000,
            view_count=5000,
            total_bytes=1024*1024 + 2048 + 512,
            file_count=3,
            version_count=1,
            created_date=None,
            updated_date=None,
            license_name="MIT",
            files=files
        )
        
        assert dataset.url == "https://www.kaggle.com/datasets/user/dataset"
        assert dataset.size_mb == round((1024*1024 + 2048 + 512) / (1024*1024), 2)
        assert dataset.file_types == [".csv", ".json", ".txt"]
    
    def test_from_kaggle_dataset(self):
        """Test creating DatasetInfo from Kaggle API response."""
        kaggle_data = {
            'ref': 'user/test-dataset',
            'title': 'Test Dataset',
            'subtitle': 'A test dataset',
            'description': 'This is a test dataset',
            'ownerName': 'testuser',
            'voteCount': 50,
            'downloadCount': 500,
            'viewCount': 2000,
            'totalBytes': 1024*1024,
            'versionCount': 2,
            'creationDate': '2023-01-01T00:00:00Z',
            'lastUpdated': '2023-06-01T00:00:00Z',
            'licenseName': 'MIT',
            'tags': ['test', 'data']
        }
        
        dataset = DatasetInfo.from_kaggle_dataset(kaggle_data)
        
        assert dataset.ref == 'user/test-dataset'
        assert dataset.title == 'Test Dataset'
        assert dataset.owner == 'testuser'
        assert dataset.vote_count == 50
        assert dataset.download_count == 500
        assert dataset.tags == ['test', 'data']
    
    def test_to_dict(self):
        """Test converting DatasetInfo to dictionary."""
        dataset = DatasetInfo(
            ref="user/dataset",
            title="Test",
            subtitle="",
            description="",
            owner="user",
            vote_count=0,
            download_count=0,
            view_count=0,
            total_bytes=0,
            file_count=0,
            version_count=1,
            created_date=None,
            updated_date=None,
            license_name="",
            quality_score=0.5,
            relevance_score=0.7,
            combined_score=0.6
        )
        
        data_dict = dataset.to_dict()
        
        assert data_dict['ref'] == "user/dataset"
        assert data_dict['quality_score'] == 0.5
        assert data_dict['relevance_score'] == 0.7
        assert data_dict['combined_score'] == 0.6
        assert data_dict['url'] == "https://www.kaggle.com/datasets/user/dataset"