# Dashboard API Specification

## Overview
This document outlines the API endpoints needed to support the dashboard frontend functionality.

## Base URL
```
/api/dashboards
```

## Authentication
All endpoints require user authentication via session or token.

## Endpoints

### 1. Dashboard Management

#### GET /api/dashboards
List all dashboards for the authenticated user
```json
{
  "dashboards": [
    {
      "id": "dash_123",
      "title": "Sales Analytics",
      "description": "Monthly sales performance",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-20T14:22:00Z",
      "view_count": 45,
      "is_public": false,
      "thumbnail_url": "/api/dashboards/dash_123/thumbnail",
      "widget_count": 4
    }
  ],
  "total": 1
}
```

#### POST /api/dashboards
Create a new dashboard
```json
// Request
{
  "title": "New Dashboard",
  "description": "Dashboard description",
  "query": "User's original query for AI processing",
  "preferred_sources": ["kaggle", "google-dataset"],
  "visualization_types": ["line-charts", "bar-charts"]
}

// Response
{
  "id": "dash_124",
  "title": "New Dashboard",
  "status": "processing",
  "job_id": "job_456"
}
```

#### GET /api/dashboards/{dashboard_id}
Get specific dashboard data
```json
{
  "id": "dash_123",
  "title": "Sales Analytics",
  "description": "Monthly sales performance",
  "created_by": "user123",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-20T14:22:00Z",
  "view_count": 45,
  "is_public": false,
  "refresh_interval": 15,
  "tags": ["sales", "analytics"],
  "widgets": [
    {
      "id": "widget_1",
      "title": "Revenue Trend",
      "type": "line",
      "position": {"x": 0, "y": 0, "width": 6, "height": 4},
      "data_source": "dataset_1"
    }
  ],
  "datasets": [
    {
      "id": "dataset_1",
      "name": "Sales Data",
      "source": "kaggle",
      "url": "gs://bucket/sales_data.csv",
      "schema": [
        {"name": "date", "type": "datetime"},
        {"name": "revenue", "type": "float"}
      ]
    }
  ]
}
```

#### PUT /api/dashboards/{dashboard_id}
Update dashboard settings
```json
// Request
{
  "title": "Updated Dashboard Title",
  "description": "Updated description",
  "refresh_interval": 30,
  "tags": ["analytics", "sales", "kpi"],
  "is_public": true,
  "widgets": [...]
}

// Response
{
  "success": true,
  "updated_at": "2025-01-20T15:30:00Z"
}
```

#### DELETE /api/dashboards/{dashboard_id}
Delete a dashboard

### 2. Widget Management

#### GET /api/dashboards/{dashboard_id}/widgets/{widget_id}
Get widget data and configuration
```json
{
  "id": "widget_1",
  "title": "Revenue Trend",
  "type": "line",
  "data_source": "dataset_1",
  "config": {
    "x_axis": "date",
    "y_axis": "revenue",
    "chart_options": {...}
  },
  "chartConfig": {
    "type": "line",
    "data": {
      "labels": ["Jan", "Feb", "Mar"],
      "datasets": [{
        "label": "Revenue",
        "data": [35000, 42000, 38000],
        "borderColor": "#007bff"
      }]
    },
    "options": {...}
  },
  "last_updated": "2025-01-20T12:00:00Z"
}
```

#### POST /api/dashboards/{dashboard_id}/widgets
Add new widget to dashboard

#### PUT /api/dashboards/{dashboard_id}/widgets/{widget_id}
Update widget configuration

#### DELETE /api/dashboards/{dashboard_id}/widgets/{widget_id}
Remove widget from dashboard

### 3. Dataset Discovery

#### POST /api/datasets/search
Search for datasets based on query
```json
// Request
{
  "query": "climate change temperature data",
  "sources": ["kaggle", "google-dataset", "world-bank"],
  "limit": 10
}

// Response
{
  "datasets": [
    {
      "title": "Global Temperature Anomalies",
      "source": "NOAA Climate Data",
      "description": "Historical temperature data from 1880-2023",
      "url": "https://example.com/dataset",
      "format": "CSV",
      "size": "45 MB",
      "last_updated": "2024-01-15",
      "relevance_score": 0.95,
      "schema_preview": [
        {"column": "year", "type": "int"},
        {"column": "temperature_anomaly", "type": "float"}
      ]
    }
  ],
  "total_found": 25,
  "search_time_ms": 1250
}
```

### 4. Dashboard Creation Job Status

#### GET /api/dashboards/{dashboard_id}/status
Get creation job status
```json
{
  "status": "processing", // "pending", "processing", "completed", "failed"
  "progress": 65,
  "current_step": "analyzing_datasets",
  "steps": [
    {
      "name": "search_datasets",
      "status": "completed",
      "message": "Found 3 relevant datasets"
    },
    {
      "name": "download_datasets",
      "status": "completed",
      "message": "Downloaded to GCS"
    },
    {
      "name": "analyzing_datasets",
      "status": "processing",
      "message": "Analyzing data structure and relationships"
    },
    {
      "name": "generate_visualizations",
      "status": "pending",
      "message": "Pending"
    }
  ],
  "estimated_completion": "2025-01-20T16:45:00Z"
}
```

### 5. Public Dashboard Access

#### GET /api/public/dashboards/{dashboard_id}
Access public dashboard (no authentication required)

### 6. Dashboard Analytics

#### POST /api/dashboards/{dashboard_id}/view
Record dashboard view (for analytics)

#### GET /api/dashboards/{dashboard_id}/analytics
Get dashboard usage analytics (owner only)

### 7. Export and Sharing

#### GET /api/dashboards/{dashboard_id}/export
Export dashboard data (PDF, PNG, etc.)

#### POST /api/dashboards/{dashboard_id}/share
Generate or update share settings

## Database Schema Requirements

### Tables Needed:

1. **dashboards**
   - id, user_id, title, description, created_at, updated_at
   - is_public, view_count, refresh_interval, tags, status

2. **dashboard_datasets**
   - id, dashboard_id, name, source, gcs_path, schema, metadata

3. **dashboard_widgets**
   - id, dashboard_id, title, type, config, position, data_source

4. **dashboard_jobs**
   - id, dashboard_id, status, progress, steps, created_at, completed_at

5. **dashboard_views**
   - id, dashboard_id, user_id, viewed_at, ip_address

## Background Job Processing

### Job Queue Structure:
1. **Dataset Search Job** - Search and evaluate datasets
2. **Dataset Download Job** - Download datasets to GCS
3. **Dataset Analysis Job** - Analyze schema and generate insights
4. **Visualization Generation Job** - Create charts and widgets
5. **Dashboard Finalization Job** - Assemble final dashboard

### Technologies Needed:
- **Queue System**: Celery with Redis/RabbitMQ
- **Storage**: Google Cloud Storage
- **Database**: PostgreSQL
- **AI/ML APIs**: Google Gemini, Perplexity API
- **Data Processing**: Pandas, BigQuery

## Error Handling

All endpoints should return consistent error responses with appropriate HTTP status codes:

### 400 Bad Request
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request parameters",
    "details": {
      "field": "title",
      "issue": "Title is required and must be between 1-100 characters"
    }
  }
}
```

### 401 Unauthorized
```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication required to access this resource",
    "details": {}
  }
}
```

### 403 Forbidden
```json
{
  "error": {
    "code": "ACCESS_DENIED",
    "message": "You don't have permission to access this dashboard",
    "details": {
      "dashboard_id": "dash_123",
      "required_permission": "edit"
    }
  }
}
```

### 404 Not Found
```json
{
  "error": {
    "code": "DASHBOARD_NOT_FOUND",
    "message": "Dashboard not found or access denied",
    "details": {
      "dashboard_id": "dash_123"
    }
  }
}
```

### 422 Unprocessable Entity
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dashboard validation failed",
    "details": {
      "errors": [
        {
          "field": "widgets[0].chart_type",
          "message": "Unsupported chart type 'invalid_type'"
        },
        {
          "field": "dataset_id",
          "message": "Dataset does not exist or is not accessible"
        }
      ]
    }
  }
}
```

### 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "limit": 5,
      "window": "1 hour",
      "retry_after": 3600
    }
  }
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "details": {
      "request_id": "req_abc123"
    }
  }
}
```

## Rate Limiting

- Dashboard creation: 5 per hour per user
- Dataset search: 50 per hour per user
- Dashboard views: 1000 per hour per dashboard

## Security Considerations

1. **Authentication**: Session-based auth for dashboard management
2. **Authorization**: Owner/public access control
3. **Data Privacy**: Anonymize sensitive data in public dashboards
4. **Input Validation**: Sanitize all user inputs
5. **GCS Security**: Proper IAM roles and bucket permissions
