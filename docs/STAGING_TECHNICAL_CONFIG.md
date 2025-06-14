# 🏗️ Phoenix Staging Environment - Technical Configuration

## Infrastructure Overview

### Cloud Run Services Configuration

| Component | Staging (phoenix-dev) | Production (phoenix) |
|-----------|----------------------|---------------------|
| **Service Name** | `phoenix-dev` | `phoenix` |
| **Region** | `us-central1` | `us-central1` |
| **Project ID** | `phoenix-project-386` | `phoenix-project-386` |
| **Image** | `gcr.io/phoenix-project-386/phoenix-dev` | `gcr.io/phoenix-project-386/phoenix` |
| **URL** | `https://phoenix-dev-234619602247.us-central1.run.app` | `https://phoenix-234619602247.us-central1.run.app` |

### Resource Allocation

| Resource | Staging | Production | Reasoning |
|----------|---------|------------|-----------|
| **CPU** | 1 | 2 | Staging needs less processing power |
| **Memory** | 1Gi | 2Gi | Optimized for cost while maintaining functionality |
| **Max Instances** | 5 | 100 | Limited scaling for staging |
| **Concurrency** | 80 | 80 | Same per-instance handling |
| **Timeout** | 300s | 300s | Same timeout for consistency |

## CI/CD Pipeline Configuration

### Cloud Build Triggers

#### Staging Trigger (`phoenix-dev-deploy`)
```yaml
name: phoenix-dev-deploy
github:
  owner: sumanurawat
  name: phoenix
  push:
    branch: ^dev$
filename: cloudbuild-dev.yaml
serviceAccount: projects/phoenix-project-386/serviceAccounts/234619602247-compute@developer.gserviceaccount.com
```

#### Production Trigger (`phoenix-deploy`)
```yaml
name: phoenix-deploy
github:
  owner: sumanurawat
  name: phoenix
  push:
    branch: ^main$
filename: cloudbuild.yaml
serviceAccount: projects/phoenix-project-386/serviceAccounts/234619602247-compute@developer.gserviceaccount.com
```

### Build Configurations

#### Staging Build (`cloudbuild-dev.yaml`)
```yaml
steps:
  # Build container
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/phoenix-dev', '.']
  
  # Push to registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/phoenix-dev']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
    - 'run'
    - 'deploy'
    - 'phoenix-dev'
    - '--image'
    - 'gcr.io/$PROJECT_ID/phoenix-dev'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
    - '--cpu'
    - '1'
    - '--memory'
    - '1Gi'
    - '--max-instances'
    - '5'
    - '--update-secrets'
    - 'GEMINI_API_KEY=phoenix-gemini-api-key:latest,SECRET_KEY=phoenix-secret-key:latest,GOOGLE_API_KEY=phoenix-google-api-key:latest,GOOGLE_SEARCH_ENGINE_ID=phoenix-search-engine-id:latest,NEWSDATA_API_KEY=phoenix-newsdata-api-key:latest'

images:
  - 'gcr.io/$PROJECT_ID/phoenix-dev'

options:
  logging: CLOUD_LOGGING_ONLY
```

## Secrets Management

### Shared Secrets Configuration
Both staging and production use the same secrets for realistic testing:

| Secret Name | Purpose | Version |
|-------------|---------|---------|
| `phoenix-gemini-api-key` | Gemini AI API access | latest |
| `phoenix-secret-key` | Flask session encryption | latest |
| `phoenix-google-api-key` | Google APIs access | latest |
| `phoenix-search-engine-id` | Google Custom Search | latest |
| `phoenix-newsdata-api-key` | News API access | latest |

### Secret Access Configuration
```bash
# Secrets are mounted as environment variables
GEMINI_API_KEY=/secrets/phoenix-gemini-api-key/latest
SECRET_KEY=/secrets/phoenix-secret-key/latest
GOOGLE_API_KEY=/secrets/phoenix-google-api-key/latest
GOOGLE_SEARCH_ENGINE_ID=/secrets/phoenix-search-engine-id/latest
NEWSDATA_API_KEY=/secrets/phoenix-newsdata-api-key/latest
```

## Database Configuration

### Firestore Database
- **Database**: Shared between staging and production
- **Project**: `phoenix-project-386`
- **Collections**: All collections are shared
- **Authentication**: Same Firebase Auth configuration

**Rationale for Sharing Database:**
- Realistic testing with production data
- Simplified configuration management
- Consistent behavior across environments
- Cost optimization

## Networking & Security

### Service Permissions
```yaml
# Both services use the same service account
serviceAccount: 234619602247-compute@developer.gserviceaccount.com

# Both allow unauthenticated access (public web app)
allowUnauthenticated: true

# Both use managed platform
platform: managed
```

### IAM Roles
The service account has the following roles:
- Cloud Run Service Agent
- Cloud Build Service Account
- Secret Manager Secret Accessor
- Firebase Admin SDK Service Account

## Monitoring Configuration

### Log Separation
Each environment has separate log streams:

#### Staging Logs
```bash
# Filter for staging logs
resource.type=cloud_run_revision 
AND resource.labels.service_name=phoenix-dev 
AND resource.labels.location=us-central1
```

#### Production Logs
```bash
# Filter for production logs
resource.type=cloud_run_revision 
AND resource.labels.service_name=phoenix 
AND resource.labels.location=us-central1
```

### Enhanced Log Fetching Script Configuration

#### Environment Detection Logic
```python
class CloudRunLogFetcher:
    def __init__(self, environment="production"):
        self.environment = environment
        self.region = "us-central1"
        
        if environment == "staging":
            self.service_name = "phoenix-dev"
            self.service_url = "https://phoenix-dev-234619602247.us-central1.run.app"
        else:  # production
            self.service_name = "phoenix"
            self.service_url = "https://phoenix-234619602247.us-central1.run.app"
```

## Development Tools Configuration

### Environment Management Script
Location: `scripts/manage_env.sh`

#### Key Functions:
- `check_service_status()` - Validates service health
- `deploy_staging()` - Handles staging deployments
- `deploy_production()` - Handles production deployments with confirmation
- `fetch_logs()` - Fetches environment-specific logs
- `open_environment()` - Opens environment URLs

### Log Analysis Features
- **Error Pattern Recognition**: Categorizes common error types
- **Severity Analysis**: Breaks down log levels
- **Search Functionality**: Keyword-based log filtering
- **JSON Export**: Machine-readable format for analysis
- **Recommendations**: Actionable fix suggestions

## Performance Optimizations

### Staging Resource Limits
```yaml
# Optimized for cost while maintaining functionality
cpu: "1"
memory: "1Gi"
maxInstances: 5
```

### Build Optimizations
```yaml
# Same base image and dependencies
# Separate image tags for environment isolation
# Optimized layer caching
options:
  logging: CLOUD_LOGGING_ONLY  # Efficient logging
```

## Backup & Recovery

### Container Images
- **Staging**: Tagged as `gcr.io/phoenix-project-386/phoenix-dev:latest`
- **Production**: Tagged as `gcr.io/phoenix-project-386/phoenix:latest`
- **Retention**: 30 days automatic retention in Container Registry

### Configuration Backup
All configuration files are version controlled:
- `cloudbuild.yaml` (production)
- `cloudbuild-dev.yaml` (staging)
- `trigger-dev.yaml` (trigger configuration)

### Rollback Strategy
```bash
# List available revisions
gcloud run revisions list --service=phoenix-dev --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic phoenix-dev \
  --to-revisions=[REVISION_NAME]=100 \
  --region=us-central1
```

## Cost Optimization

### Staging Cost Savings
- **50% CPU reduction**: 1 vs 2 cores
- **50% Memory reduction**: 1Gi vs 2Gi  
- **95% Instance reduction**: 5 vs 100 max instances
- **Estimated Savings**: ~70% of production costs

### Shared Resources
- Database: No additional costs
- Secrets: No additional costs
- IAM: No additional costs
- Networking: Minimal additional costs

## Future Enhancements

### Planned Improvements
1. **Automated Testing**: Add test suites to CI/CD pipeline
2. **Environment Variables**: Separate environment-specific configs
3. **Blue/Green Deployments**: Zero-downtime deployment strategy
4. **Monitoring Alerts**: Automated error detection and notification
5. **Performance Metrics**: Resource usage tracking and optimization

### Monitoring Improvements
1. **Health Check Endpoints**: Custom health monitoring
2. **Uptime Monitoring**: External service monitoring
3. **Performance Dashboards**: Real-time metrics visualization
4. **Log Aggregation**: Centralized log analysis

---

*This configuration provides a robust, cost-effective staging environment that mirrors production behavior while optimizing for development workflows.*
