# Dashboard Backend Implementation Plan

## Overview
This document provides a comprehensive implementation plan for the AI-powered dashboard backend system. The backend will support automatic dataset discovery, AI-driven analysis, and dynamic dashboard generation.

## 🎯 Project Goals

### Core Functionality
1. **AI-Powered Dashboard Creation** - Users describe what they want, AI finds datasets and creates visualizations
2. **Dataset Discovery** - Search across multiple trusted sources (Kaggle, Google Dataset Search, etc.)
3. **Automated Analysis** - AI analyzes datasets and generates insights
4. **Dynamic Visualization** - Automatically creates charts and graphs based on data patterns
5. **Shareable Dashboards** - Public/private dashboards with unique URLs

### Technical Objectives
- **Scalable Architecture** - Handle multiple concurrent dashboard creation jobs
- **Real-time Progress** - Live updates during dashboard creation process
- **Data Security** - Secure handling of datasets and user data
- **Performance** - Fast dashboard loading and responsive UI

## 🏗️ System Architecture

### High-Level Architecture
```
Frontend (React/Vue) → API Gateway → Flask Backend → Job Queue → AI Services
                                                   ↓
                                              Database (PostgreSQL)
                                                   ↓
                                              Storage (GCS)
```

### Components Overview
1. **Flask API Server** - Main application server
2. **Job Queue System** - Background processing (Celery + Redis)
3. **AI Service Layer** - Dataset discovery and analysis
4. **Database Layer** - Data persistence
5. **Storage Layer** - Dataset and file management
6. **Cache Layer** - Performance optimization

## 📊 Database Design

### Core Tables

#### 1. users (existing)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. dashboards
```sql
CREATE TABLE dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    query TEXT NOT NULL, -- Original user query
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    is_public BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,
    refresh_interval INTEGER DEFAULT 0, -- minutes
    tags TEXT[], -- PostgreSQL array
    thumbnail_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    INDEX idx_dashboards_user_id (user_id),
    INDEX idx_dashboards_status (status),
    INDEX idx_dashboards_public (is_public)
);
```

#### 3. dashboard_datasets
```sql
CREATE TABLE dashboard_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID REFERENCES dashboards(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL, -- kaggle, google-dataset, etc.
    original_url TEXT,
    gcs_path TEXT NOT NULL, -- gs://bucket/path/to/file
    file_format VARCHAR(20), -- csv, json, parquet
    file_size BIGINT, -- bytes
    schema_json JSONB, -- column definitions
    metadata JSONB, -- additional metadata
    download_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_dashboard_datasets_dashboard_id (dashboard_id),
    INDEX idx_dashboard_datasets_status (download_status)
);
```

#### 4. dashboard_widgets
```sql
CREATE TABLE dashboard_widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID REFERENCES dashboards(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES dashboard_datasets(id),
    title VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- line, bar, pie, scatter, heatmap, table, metric
    config JSONB NOT NULL, -- widget configuration
    position JSONB, -- {x, y, width, height}
    chart_config JSONB, -- Chart.js configuration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_dashboard_widgets_dashboard_id (dashboard_id)
);
```

#### 5. dashboard_jobs
```sql
CREATE TABLE dashboard_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID REFERENCES dashboards(id) ON DELETE CASCADE,
    celery_task_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0, -- 0-100
    current_step VARCHAR(100),
    steps JSONB, -- array of step objects
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_dashboard_jobs_dashboard_id (dashboard_id),
    INDEX idx_dashboard_jobs_celery_task_id (celery_task_id),
    INDEX idx_dashboard_jobs_status (status)
);
```

#### 6. dashboard_views
```sql
CREATE TABLE dashboard_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID REFERENCES dashboards(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    user_agent TEXT,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_dashboard_views_dashboard_id (dashboard_id),
    INDEX idx_dashboard_views_viewed_at (viewed_at)
);
```

#### 7. dataset_cache
```sql
CREATE TABLE dataset_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash VARCHAR(64) UNIQUE NOT NULL, -- hash of search query
    query TEXT NOT NULL,
    sources VARCHAR(255)[], -- array of sources searched
    results JSONB NOT NULL, -- cached search results
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_dataset_cache_query_hash (query_hash),
    INDEX idx_dataset_cache_expires_at (expires_at)
);
```

## 🔧 Backend Implementation

### 1. Project Structure
```
backend/
├── app.py                      # Flask application entry point
├── config/
│   ├── __init__.py
│   ├── settings.py            # Configuration management
│   └── database.py            # Database connection
├── api/
│   ├── __init__.py
│   ├── dashboard_routes.py    # Dashboard API routes
│   ├── widget_routes.py       # Widget management
│   └── dataset_routes.py      # Dataset search API
├── services/
│   ├── __init__.py
│   ├── ai_service.py          # AI integration layer
│   ├── dataset_service.py     # Dataset discovery
│   ├── analysis_service.py    # Data analysis
│   └── visualization_service.py # Chart generation
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py          # Celery configuration
│   ├── dashboard_tasks.py     # Background jobs
│   └── dataset_tasks.py       # Dataset processing
├── models/
│   ├── __init__.py
│   ├── dashboard.py           # Database models
│   ├── dataset.py
│   └── widget.py
├── utils/
│   ├── __init__.py
│   ├── auth.py                # Authentication helpers
│   ├── storage.py             # GCS utilities
│   └── cache.py               # Redis cache utilities
└── requirements.txt
```

### 2. Core Dependencies
```txt
# Web Framework
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Migrate==4.0.5
Flask-Session==0.5.0

# Database
psycopg2-binary==2.9.7
SQLAlchemy==2.0.21

# Job Queue
celery==5.3.1
redis==4.6.0

# AI/ML Services
google-cloud-aiplatform==1.35.0
openai==0.28.1
requests==2.31.0

# Data Processing
pandas==2.1.1
numpy==1.24.3
pyarrow==13.0.0

# Cloud Storage
google-cloud-storage==2.10.0

# Utilities
python-dotenv==1.0.0
marshmallow==3.20.1
python-dateutil==2.8.2
```

### 3. Configuration Management
```python
# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Google Cloud
    GCS_BUCKET = os.getenv('GCS_BUCKET', 'phoenix-dashboards')
    GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    # AI Services
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # External APIs
    KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME')
    KAGGLE_KEY = os.getenv('KAGGLE_KEY')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Rate Limiting
    DASHBOARD_CREATION_LIMIT = 5  # per hour per user
    DATASET_SEARCH_LIMIT = 50     # per hour per user
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
```

## 🤖 AI Service Implementation

### 1. AI Service Layer
```python
# services/ai_service.py
from abc import ABC, abstractmethod
import google.generativeai as genai
import openai
import requests

class AIProvider(ABC):
    @abstractmethod
    async def analyze_query(self, query: str) -> dict:
        pass
    
    @abstractmethod
    async def search_datasets(self, query: str, sources: list) -> list:
        pass
    
    @abstractmethod
    async def analyze_dataset(self, dataset_path: str, schema: dict) -> dict:
        pass
    
    @abstractmethod
    async def generate_visualizations(self, analysis: dict) -> list:
        pass

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    async def analyze_query(self, query: str) -> dict:
        prompt = f"""
        Analyze this dashboard request and extract key information:
        
        Query: "{query}"
        
        Return a JSON response with:
        - intent: What the user wants to analyze
        - data_types: Types of data needed
        - suggested_sources: Recommended data sources
        - visualization_types: Appropriate chart types
        - keywords: Search keywords for datasets
        """
        
        response = self.model.generate_content(prompt)
        return self._parse_json_response(response.text)
    
    async def search_datasets(self, query: str, sources: list) -> list:
        # Implementation for dataset search using Gemini
        pass
    
    async def analyze_dataset(self, dataset_path: str, schema: dict) -> dict:
        # Implementation for dataset analysis
        pass
    
    async def generate_visualizations(self, analysis: dict) -> list:
        # Implementation for visualization generation
        pass

class PerplexityProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai"
    
    async def search_datasets(self, query: str, sources: list) -> list:
        """Use Perplexity for dataset discovery"""
        search_query = f"""
        Find datasets related to: {query}
        
        Search in these sources: {', '.join(sources)}
        
        For each dataset, provide:
        - Title and description
        - Source and URL
        - File format and size
        - Last updated date
        - Relevance score
        """
        
        response = await self._make_request(search_query)
        return self._parse_dataset_results(response)
```

### 2. Dataset Discovery Service
```python
# services/dataset_service.py
import asyncio
import aiohttp
from typing import List, Dict
import hashlib
import json

class DatasetDiscoveryService:
    def __init__(self, ai_provider, cache_service):
        self.ai_provider = ai_provider
        self.cache = cache_service
        self.sources = {
            'kaggle': KaggleSource(),
            'google-dataset': GoogleDatasetSource(),
            'world-bank': WorldBankSource(),
            'who': WHOSource(),
            'fred': FREDSource()
        }
    
    async def search_datasets(self, query: str, sources: List[str], limit: int = 10) -> Dict:
        # Check cache first
        cache_key = self._generate_cache_key(query, sources)
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Analyze query with AI
        query_analysis = await self.ai_provider.analyze_query(query)
        
        # Search across sources
        search_tasks = []
        for source_name in sources:
            if source_name in self.sources:
                source = self.sources[source_name]
                task = self._search_source(source, query_analysis, limit)
                search_tasks.append(task)
        
        # Execute searches concurrently
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Combine and rank results
        all_datasets = []
        for result in search_results:
            if isinstance(result, list):
                all_datasets.extend(result)
        
        # Rank datasets using AI
        ranked_datasets = await self._rank_datasets(all_datasets, query_analysis)
        
        # Cache results
        final_result = {
            'datasets': ranked_datasets[:limit],
            'total_found': len(all_datasets),
            'search_time_ms': 0,  # Calculate actual time
            'query_analysis': query_analysis
        }
        
        await self.cache.set(cache_key, final_result, expires_in=3600)  # 1 hour
        return final_result
    
    def _generate_cache_key(self, query: str, sources: List[str]) -> str:
        key_data = f"{query}:{sorted(sources)}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    async def _search_source(self, source, query_analysis: dict, limit: int) -> List[Dict]:
        try:
            return await source.search(query_analysis, limit)
        except Exception as e:
            print(f"Error searching {source.__class__.__name__}: {e}")
            return []
    
    async def _rank_datasets(self, datasets: List[Dict], query_analysis: dict) -> List[Dict]:
        # Use AI to rank datasets by relevance
        ranking_prompt = f"""
        Rank these datasets by relevance to the query: {query_analysis['intent']}
        
        Datasets: {json.dumps(datasets, indent=2)}
        
        Return ranked list with relevance scores (0-1).
        """
        
        ranked_results = await self.ai_provider.rank_datasets(datasets, query_analysis)
        return ranked_results

class KaggleSource:
    def __init__(self):
        self.api_client = kaggle.KaggleApi()
        self.api_client.authenticate()
    
    async def search(self, query_analysis: dict, limit: int) -> List[Dict]:
        # Implementation for Kaggle dataset search
        pass

class GoogleDatasetSource:
    async def search(self, query_analysis: dict, limit: int) -> List[Dict]:
        # Implementation for Google Dataset Search
        pass
```

### 3. Background Job Processing
```python
# tasks/dashboard_tasks.py
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import logging

celery_app = Celery('dashboard_tasks')

@celery_app.task(bind=True)
def create_dashboard_workflow(self, dashboard_id: str, user_query: str, preferences: dict):
    """Main workflow for creating an AI-powered dashboard"""
    
    job_service = DashboardJobService()
    
    try:
        # Update job status
        job_service.update_job_status(dashboard_id, 'processing', 0, 'search_datasets')
        
        # Step 1: Search and select datasets
        datasets = search_and_select_datasets.delay(dashboard_id, user_query, preferences)
        datasets_result = datasets.get()
        
        if not datasets_result['success']:
            raise Exception(f"Dataset search failed: {datasets_result['error']}")
        
        job_service.update_job_status(dashboard_id, 'processing', 25, 'download_datasets')
        
        # Step 2: Download datasets to GCS
        download_result = download_datasets.delay(dashboard_id, datasets_result['datasets'])
        download_result.get()
        
        job_service.update_job_status(dashboard_id, 'processing', 50, 'analyze_datasets')
        
        # Step 3: Analyze datasets
        analysis_result = analyze_datasets.delay(dashboard_id)
        analysis = analysis_result.get()
        
        job_service.update_job_status(dashboard_id, 'processing', 75, 'generate_visualizations')
        
        # Step 4: Generate visualizations
        viz_result = generate_visualizations.delay(dashboard_id, analysis)
        viz_result.get()
        
        job_service.update_job_status(dashboard_id, 'processing', 90, 'finalize_dashboard')
        
        # Step 5: Finalize dashboard
        finalize_result = finalize_dashboard.delay(dashboard_id)
        finalize_result.get()
        
        # Complete
        job_service.update_job_status(dashboard_id, 'completed', 100, 'completed')
        
        return {'success': True, 'dashboard_id': dashboard_id}
        
    except Exception as e:
        logging.error(f"Dashboard creation failed for {dashboard_id}: {str(e)}")
        job_service.update_job_status(dashboard_id, 'failed', 0, 'failed', str(e))
        return {'success': False, 'error': str(e)}

@celery_app.task
def search_and_select_datasets(dashboard_id: str, query: str, preferences: dict):
    """Search for datasets and let AI select the best ones"""
    
    dataset_service = DatasetDiscoveryService()
    ai_service = AIService()
    
    try:
        # Search for datasets
        search_results = dataset_service.search_datasets(
            query=query,
            sources=preferences.get('sources', ['kaggle', 'google-dataset']),
            limit=20
        )
        
        # Let AI select the best datasets
        selected_datasets = ai_service.select_optimal_datasets(
            search_results['datasets'],
            query,
            max_datasets=5
        )
        
        return {
            'success': True,
            'datasets': selected_datasets,
            'total_found': search_results['total_found']
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@celery_app.task
def download_datasets(dashboard_id: str, datasets: List[Dict]):
    """Download selected datasets to Google Cloud Storage"""
    
    storage_service = StorageService()
    
    for dataset in datasets:
        try:
            # Download dataset
            local_path = storage_service.download_dataset(dataset['url'])
            
            # Upload to GCS
            gcs_path = storage_service.upload_to_gcs(
                local_path,
                f"dashboards/{dashboard_id}/datasets/{dataset['id']}"
            )
            
            # Save dataset info to database
            dataset_model = DashboardDataset(
                dashboard_id=dashboard_id,
                name=dataset['title'],
                source=dataset['source'],
                original_url=dataset['url'],
                gcs_path=gcs_path,
                file_format=dataset['format'],
                file_size=dataset['size']
            )
            db.session.add(dataset_model)
            
        except Exception as e:
            logging.error(f"Failed to download dataset {dataset['id']}: {e}")
    
    db.session.commit()
    return {'success': True}

@celery_app.task
def analyze_datasets(dashboard_id: str):
    """Analyze downloaded datasets using AI"""
    
    analysis_service = DataAnalysisService()
    datasets = DashboardDataset.query.filter_by(dashboard_id=dashboard_id).all()
    
    analysis_results = []
    
    for dataset in datasets:
        try:
            # Load dataset from GCS
            df = analysis_service.load_dataset_from_gcs(dataset.gcs_path)
            
            # Analyze with AI
            analysis = analysis_service.analyze_dataset_with_ai(df, dataset.name)
            
            # Update dataset schema
            dataset.schema_json = analysis['schema']
            dataset.metadata = analysis['metadata']
            
            analysis_results.append({
                'dataset_id': dataset.id,
                'analysis': analysis
            })
            
        except Exception as e:
            logging.error(f"Failed to analyze dataset {dataset.id}: {e}")
    
    db.session.commit()
    return {'success': True, 'analyses': analysis_results}

@celery_app.task
def generate_visualizations(dashboard_id: str, analyses: List[Dict]):
    """Generate visualizations based on dataset analysis"""
    
    viz_service = VisualizationService()
    ai_service = AIService()
    
    # Get dashboard info
    dashboard = Dashboard.query.get(dashboard_id)
    
    # Let AI decide on visualizations
    viz_plan = ai_service.create_visualization_plan(
        dashboard.query,
        analyses
    )
    
    # Generate widgets
    for viz_config in viz_plan['visualizations']:
        try:
            widget = DashboardWidget(
                dashboard_id=dashboard_id,
                dataset_id=viz_config['dataset_id'],
                title=viz_config['title'],
                type=viz_config['type'],
                config=viz_config['config'],
                position=viz_config['position'],
                chart_config=viz_config['chart_config']
            )
            db.session.add(widget)
            
        except Exception as e:
            logging.error(f"Failed to create widget: {e}")
    
    db.session.commit()
    return {'success': True}

@celery_app.task
def finalize_dashboard(dashboard_id: str):
    """Final steps to complete dashboard creation"""
    
    dashboard = Dashboard.query.get(dashboard_id)
    
    # Generate thumbnail
    thumbnail_service = ThumbnailService()
    thumbnail_url = thumbnail_service.generate_dashboard_thumbnail(dashboard_id)
    
    # Update dashboard
    dashboard.status = 'completed'
    dashboard.completed_at = datetime.utcnow()
    dashboard.thumbnail_url = thumbnail_url
    
    db.session.commit()
    
    # Send notification (optional)
    # notification_service.send_dashboard_ready_notification(dashboard.user_id, dashboard_id)
    
    return {'success': True}
```

## 🚀 Deployment Plan

### 1. Infrastructure Requirements

#### Google Cloud Platform Services
```yaml
# GCP Services Needed
compute:
  - Cloud Run (API server)
  - Cloud Functions (lightweight tasks)
  
storage:
  - Cloud Storage (datasets, thumbnails)
  - Cloud SQL (PostgreSQL database)
  - Cloud Memorystore (Redis cache)
  
ai_services:
  - Vertex AI (Gemini API)
  - BigQuery (data analysis)
  
monitoring:
  - Cloud Logging
  - Cloud Monitoring
  - Error Reporting
```

#### Docker Configuration
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=app.py

# Expose port
EXPOSE 8080

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "app:app"]
```

### 2. CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy Dashboard Backend

on:
  push:
    branches: [main]
    paths: ['backend/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          cd backend
          pytest tests/ --cov=. --cov-report=xml
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v1
        with:
          service: dashboard-backend
          image: gcr.io/${{ secrets.GCP_PROJECT }}/dashboard-backend:latest
          region: us-central1
```

## 📈 Performance & Scaling

### 1. Caching Strategy
- **Redis Cache**: API responses, dataset search results
- **CDN**: Static assets, dashboard thumbnails
- **Database Indexes**: Optimized queries for dashboard loading

### 2. Rate Limiting
```python
# Rate limiting implementation
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/api/dashboards', methods=['POST'])
@limiter.limit("5 per hour")  # Dashboard creation limit
def create_dashboard():
    pass
```

### 3. Monitoring & Alerting
- **Application Metrics**: Response times, error rates
- **Job Queue Monitoring**: Queue depth, failed jobs
- **Database Performance**: Query performance, connection pools
- **Cost Monitoring**: GCP usage, API call costs

## 🔒 Security Implementation

### 1. Authentication & Authorization
```python
# auth.py
from functools import wraps
from flask import session, jsonify

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_dashboard_access(f):
    @wraps(f)
    def decorated_function(dashboard_id, *args, **kwargs):
        dashboard = Dashboard.query.get_or_404(dashboard_id)
        
        # Check if user owns dashboard or it's public
        if dashboard.user_id != session.get('user_id') and not dashboard.is_public:
            return jsonify({'error': 'Access denied'}), 403
            
        return f(dashboard_id, *args, **kwargs)
    return decorated_function
```

### 2. Data Security
- **Input Validation**: Sanitize all user inputs
- **SQL Injection Protection**: Use parameterized queries
- **GCS Security**: Proper IAM roles and bucket policies
- **API Key Management**: Secure storage of AI service keys

## 📋 Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up project structure and dependencies
- [ ] Implement database models and migrations
- [ ] Create basic API endpoints (CRUD operations)
- [ ] Set up authentication and authorization
- [ ] Configure Celery job queue

### Phase 2: AI Integration (Weeks 3-4)
- [ ] Implement AI service layer (Gemini/Perplexity)
- [ ] Create dataset discovery service
- [ ] Build dataset analysis pipeline
- [ ] Implement visualization generation

### Phase 3: Dashboard Creation (Weeks 5-6)
- [ ] Build complete dashboard creation workflow
- [ ] Implement background job processing
- [ ] Add progress tracking and status updates
- [ ] Create thumbnail generation service

### Phase 4: Advanced Features (Weeks 7-8)
- [ ] Public dashboard sharing
- [ ] Dashboard analytics and view tracking
- [ ] Export functionality (PDF, PNG)
- [ ] Performance optimization and caching

### Phase 5: Testing & Deployment (Weeks 9-10)
- [ ] Comprehensive testing (unit, integration, E2E)
- [ ] Load testing and performance tuning
- [ ] Security audit and penetration testing
- [ ] Production deployment and monitoring setup

## 🧪 Testing Strategy

### 1. Unit Tests
```python
# tests/test_dashboard_service.py
import pytest
from services.dashboard_service import DashboardService

class TestDashboardService:
    def test_create_dashboard(self):
        service = DashboardService()
        dashboard = service.create_dashboard(
            user_id="user123",
            title="Test Dashboard",
            query="sales data analysis"
        )
        assert dashboard.status == 'pending'
        assert dashboard.title == "Test Dashboard"
    
    def test_search_datasets(self):
        # Test dataset search functionality
        pass
```

### 2. Integration Tests
- API endpoint testing
- Database integration testing
- Job queue testing
- AI service integration testing

### 3. Load Testing
```python
# Load testing with locust
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login user
        self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
    
    @task(3)
    def view_dashboard_list(self):
        self.client.get("/api/dashboards")
    
    @task(1)
    def create_dashboard(self):
        self.client.post("/api/dashboards", json={
            "title": "Load Test Dashboard",
            "query": "test data analysis"
        })
```

## 📝 API Documentation

Generate comprehensive API documentation using OpenAPI/Swagger:

```python
# API documentation
from flask_restx import Api, Resource, fields

api = Api(app, doc='/api/docs/')

dashboard_model = api.model('Dashboard', {
    'id': fields.String(required=True),
    'title': fields.String(required=True),
    'description': fields.String(),
    'status': fields.String(enum=['pending', 'processing', 'completed', 'failed'])
})

@api.route('/dashboards')
class DashboardList(Resource):
    @api.marshal_list_with(dashboard_model)
    def get(self):
        """List all dashboards for authenticated user"""
        pass
    
    @api.expect(dashboard_model)
    @api.marshal_with(dashboard_model)
    def post(self):
        """Create a new dashboard"""
        pass
```

This comprehensive backend plan covers all aspects of implementing the AI-powered dashboard system, from database design to deployment strategy. The implementation follows best practices for scalability, security, and maintainability.
