"""
Tests for dataset discovery API routes.
"""
import pytest
import json
from unittest.mock import Mock, patch
from flask import Flask

from api.dataset_routes import dataset_bp
from services.dataset_discovery.models import SearchResponse, DatasetInfo, ServiceHealth
from services.dataset_discovery.exceptions import (
    SearchValidationError, KaggleAuthenticationError, DatasetDiscoveryError
)


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(dataset_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestDatasetRoutes:
    """Test cases for dataset API routes."""
    
    def test_search_datasets_success(self, client):
        """Test successful dataset search."""
        # Mock the service
        mock_dataset = DatasetInfo(
            ref="test/dataset",
            title="Test Dataset",
            subtitle="A test dataset",
            description="Test description",
            owner="testuser",
            vote_count=100,
            download_count=1000,
            view_count=5000,
            total_bytes=1024*1024,  # 1MB
            file_count=3,
            version_count=1,
            created_date=None,
            updated_date=None,
            license_name="MIT",
            tags=["test", "data"],
            quality_score=0.8,
            relevance_score=0.9,
            combined_score=0.85
        )
        
        mock_response = SearchResponse(
            query="test",
            total_found=1,
            returned_count=1,
            datasets=[mock_dataset],
            search_time_ms=100,
            cached=False
        )
        
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.search_datasets.return_value = mock_response
            
            response = client.post('/api/datasets/search', 
                                 json={"query": "test", "limit": 10})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['query'] == "test"
            assert data['returned_count'] == 1
            assert len(data['datasets']) == 1
            assert data['datasets'][0]['ref'] == "test/dataset"
    
    def test_search_datasets_missing_query(self, client):
        """Test search with missing query parameter."""
        response = client.post('/api/datasets/search', json={})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == "MISSING_QUERY"
    
    def test_search_datasets_empty_request(self, client):
        """Test search with empty request body."""
        response = client.post('/api/datasets/search', json=None)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == "EMPTY_REQUEST"
    
    def test_search_datasets_invalid_json(self, client):
        """Test search with invalid JSON."""
        response = client.post('/api/datasets/search', 
                             data="invalid json",
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == "INVALID_REQUEST"
    
    def test_search_datasets_validation_error(self, client):
        """Test search with validation error."""
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.search_datasets.side_effect = SearchValidationError(
                "Query too short"
            )
            
            response = client.post('/api/datasets/search', 
                                 json={"query": "a"})
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['error']['code'] == "SEARCH_VALIDATION_ERROR"
    
    def test_search_datasets_auth_error(self, client):
        """Test search with authentication error."""
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.search_datasets.side_effect = KaggleAuthenticationError(
                "Invalid credentials"
            )
            
            response = client.post('/api/datasets/search', 
                                 json={"query": "test"})
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['error']['code'] == "KAGGLE_AUTH_ERROR"
    
    def test_search_datasets_service_error(self, client):
        """Test search with service error."""
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.search_datasets.side_effect = DatasetDiscoveryError(
                "Service error"
            )
            
            response = client.post('/api/datasets/search', 
                                 json={"query": "test"})
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['error']['code'] == "UNKNOWN_ERROR"
    
    def test_search_datasets_unexpected_error(self, client):
        """Test search with unexpected error."""
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.search_datasets.side_effect = Exception(
                "Unexpected error"
            )
            
            response = client.post('/api/datasets/search', 
                                 json={"query": "test"})
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['error']['code'] == "INTERNAL_ERROR"
    
    def test_health_check_healthy(self, client):
        """Test health check with healthy service."""
        mock_health = ServiceHealth(
            status="healthy",
            timestamp=None,
            kaggle_authenticated=True,
            checks={"kaggle_auth": {"status": "ok"}}
        )
        
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.get_health_status.return_value = mock_health
            
            response = client.get('/api/datasets/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['status'] == "healthy"
            assert data['kaggle_authenticated'] is True
    
    def test_health_check_degraded(self, client):
        """Test health check with degraded service."""
        mock_health = ServiceHealth(
            status="degraded",
            timestamp=None,
            kaggle_authenticated=False,
            checks={"kaggle_auth": {"status": "error"}}
        )
        
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.get_health_status.return_value = mock_health
            
            response = client.get('/api/datasets/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['status'] == "degraded"
    
    def test_health_check_unhealthy(self, client):
        """Test health check with unhealthy service."""
        mock_health = ServiceHealth(
            status="unhealthy",
            timestamp=None,
            kaggle_authenticated=False,
            checks={}
        )
        
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.get_health_status.return_value = mock_health
            
            response = client.get('/api/datasets/health')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['status'] == "unhealthy"
    
    def test_health_check_error(self, client):
        """Test health check with service error."""
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.get_health_status.side_effect = Exception(
                "Health check failed"
            )
            
            response = client.get('/api/datasets/health')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['status'] == "unhealthy"
    
    def test_get_config_info_success(self, client):
        """Test config info endpoint success."""
        mock_config = Mock()
        mock_config.get_search_defaults.return_value = {
            "limit": 20,
            "sort_by": "hottest"
        }
        mock_config.KAGGLE_USERNAME = "testuser"
        mock_config.KAGGLE_KEY = "testkey"
        
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.config = mock_config
            
            response = client.get('/api/datasets/config')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['kaggle_configured'] is True
            assert 'defaults' in data
    
    def test_search_datasets_with_all_params(self, client):
        """Test search with all parameters specified."""
        mock_dataset = DatasetInfo(
            ref="test/dataset",
            title="Test Dataset",
            subtitle="A test dataset",
            description="Test description",
            owner="testuser",
            vote_count=100,
            download_count=1000,
            view_count=5000,
            total_bytes=1024*1024,
            file_count=3,
            version_count=1,
            created_date=None,
            updated_date=None,
            license_name="MIT",
            tags=["test"],
            quality_score=0.8,
            relevance_score=0.9,
            combined_score=0.85
        )
        
        mock_response = SearchResponse(
            query="climate change",
            total_found=1,
            returned_count=1,
            datasets=[mock_dataset],
            search_time_ms=150,
            cached=False
        )
        
        with patch('api.dataset_routes.get_dataset_service') as mock_service:
            mock_service.return_value.search_datasets.return_value = mock_response
            
            response = client.post('/api/datasets/search', json={
                "query": "climate change",
                "limit": 5,
                "sort_by": "votes",
                "min_quality_score": 0.5
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['query'] == "climate change"