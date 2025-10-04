# Phoenix AI Platform

Phoenix is a Flask-based Python web application featuring multiple AI-powered tools including conversational AI (Derplexity), intelligent search (Doogle), news aggregation (Robin), URL shortener (Deeplink), and dataset discovery with video generation. The platform integrates multiple LLM providers (Google Gemini, Claude, Grok, OpenAI) with Firebase Firestore for persistence and Stripe for subscriptions.

**Architecture**: Multi-service Flask app with Blueprint-based routing, service-oriented design, and Firebase-first authentication.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Environment Setup
- **Python Version**: Requires Python 3.8+ (tested with Python 3.12.3)
- **Virtual Environment**: Always use a virtual environment to avoid dependency conflicts
- **Port**: Application runs on port 8080 by default

### Bootstrap and Build Process
1. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   ```
   - Takes ~4 seconds - Set timeout to 30+ seconds

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   - **NEVER CANCEL**: Takes 1 minute 13 seconds - Set timeout to 120+ seconds
   - Installs 26+ packages including Flask, Firebase Admin, Google Cloud APIs, ML libraries

4. **Create session directory**:
   ```bash
   mkdir -p flask_session
   ```

5. **Set up environment variables** (copy from .env.example):
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Required API Keys and Configuration
The application requires these environment variables in `.env`:
- `GEMINI_API_KEY` - Google Gemini API (required for AI features)
- `GOOGLE_API_KEY` - Google Search API
- `GOOGLE_SEARCH_ENGINE_ID` - Custom Search Engine ID
- `CLAUDE_API_KEY` - Anthropic Claude API (optional)
- `GROK_API_KEY` - xAI Grok API (optional)
- `NEWSDATA_API_KEY` - NewsData.io API (for Robin news feature)
- `FIREBASE_API_KEY` - Firebase authentication
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Firebase service account JSON
- `SECRET_KEY` - Flask session secret

**CRITICAL**: The application CANNOT start without proper Firebase credentials and will fail during initialization with DefaultCredentialsError.

### Starting the Application

#### Using Startup Scripts (Recommended)
```bash
# Development mode with debug and auto-reload
./start_local.sh

# Production mode without debug
./start_production.sh
```
- **NEVER CANCEL**: Startup takes 1-2 minutes - Set timeout to 180+ seconds
- Scripts automatically handle virtual environment activation and port management

#### Manual Startup
```bash
source venv/bin/activate
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

#### Expected Startup Behavior
- Application loads multiple services (LLM, Enhanced LLM, Document, etc.)
- You'll see Firebase Admin SDK initialization logs
- **Normal warnings** about missing optional API keys (Claude, Grok)
- Server starts on http://localhost:8080
- **In debug mode**: Logs appear twice due to Flask auto-reloader

## Testing and Validation

### Test Infrastructure Limitations
- **Main test suite requires Firebase credentials** - will fail without proper setup
- **Tests require pytest** (not in requirements.txt) - use `pip install pytest` if needed
- **Unit tests in `tests/` directory** cannot run without Firebase Firestore access

### Standalone Tests (Work without Firebase)
Some test files can run independently:
```bash
python test_claude_default.py      # Tests Claude API fallback
python test_enhanced_llm.py        # Tests LLM service
python test_unified_llm.py         # Tests unified LLM functionality
```
- **NEVER CANCEL**: These take 2-5 minutes - Set timeout to 300+ seconds
- Expect API timeouts/failures without real API keys (this is normal)

### Manual Validation Steps
After making changes, always validate:
1. **Virtual environment activation works**
2. **Dependencies install successfully**
3. **Application starts without import errors**
4. **Key routes load without 500 errors** (even with placeholder APIs)
5. **Static files load correctly** (CSS, JS)

### No Linting Tools Configured
- **No flake8, black, or pylint** in requirements.txt
- **No pre-commit hooks** or code formatting tools
- **No automated code quality checks** - add manually if needed

## Application Architecture

### Service-Oriented Design Pattern
Phoenix follows a **service-layer architecture** where business logic is separated from routes:
- **Routes** (`api/*_routes.py`) - Only handle HTTP concerns, delegate to services
- **Services** (`services/`) - Contain all business logic, API integrations, data processing
- **Config** (`config/`) - Centralized settings with environment-based overrides

### Blueprint Registration Pattern
All routes use Flask Blueprints with consistent patterns:
```python
# In api/example_routes.py
example_bp = Blueprint('example', __name__, url_prefix='/api/example')

# In app.py
app.register_blueprint(example_bp)
```

### Authentication & Authorization Patterns
- **`@login_required`** decorator from `api.auth_routes` - Used consistently across protected routes
- **Firebase session-based auth** - User data stored in Flask session after Firebase token verification
- **CSRF protection** via `@csrf_protect` decorator from `middleware.csrf_protection`
- **Subscription gating** via middleware in `services.subscription_middleware`

### Multi-Provider LLM Architecture
**Critical Pattern**: The `services/enhanced_llm_service.py` provides unified interface to multiple LLM providers:
- **ModelProvider enum**: GEMINI, CLAUDE, GROK, OPENAI
- **Fallback chain**: Graceful degradation when primary provider fails
- **Usage tracking**: Token counting and cost calculation per provider
- **Model selection**: Provider-specific model configurations in `config/`

Example usage pattern:
```python
from services.enhanced_llm_service import EnhancedLLMService, ModelProvider
llm = EnhancedLLMService(provider=ModelProvider.GEMINI, model="gemini-1.5-flash")
response = llm.generate_text(prompt, enable_fallback=True)
```

### Database & Persistence
- **Firebase Firestore** - Primary database (user data, links, analytics, subscriptions)
- **Flask sessions** - Filesystem-based sessions in `./flask_session/`
- **No local database** - All persistent data in cloud (Firebase)
- **Service account authentication** - Via `firebase-credentials.json` or Application Default Credentials

## Core Features and Routing Patterns

### Application Structure
Each major feature follows a consistent pattern:
- **Frontend route** in `app.py` (e.g., `/derplexity`, `/doogle`)
- **API blueprint** in `api/` (e.g., `chat_routes.py`, `search_routes.py`)
- **Service layer** in `services/` (e.g., `chat_service.py`, `search_service.py`)

### Feature Breakdown
1. **Derplexity** (`/derplexity`, `/api/chat/`) - Multi-turn conversations with LLM providers
2. **Enhanced Chat** (`/api/enhanced-chat/`) - Advanced chat with model selection and thinking modes
3. **Doogle** (`/doogle`, `/api/search/`) - AI-powered web/news search with Google Custom Search
4. **Robin** (`/api/robin/`) - News aggregation and analysis via NewsData.io API
5. **Deeplink** (`/apps/deeplink/`, `/api/deeplink/`) - URL shortening with click analytics
6. **Dataset Discovery** (`/datasets`, `/api/dataset/`) - Kaggle dataset search with Docker-based analysis
7. **Video Generation** (`/video-generation`, `/api/video/`) - AI video generation with Veo API

### Authentication Patterns
- **Most routes require `@login_required`** - Firebase auth integration
- **Session-based user data** - `session['user_id']`, `session['user_email']`, etc.
- **CSRF protection** on all POST/PUT/DELETE via `@csrf_protect`
- **Subscription middleware** for premium feature gating

## Deployment and Production

### Local Development
- **Port 8080** - Default development port
- **Debug mode enabled** - Shows detailed error pages
- **Auto-reload** - Restarts on file changes
- **Session files** stored in `./flask_session/`

### Production Deployment
- **Google Cloud Run** - Serverless container deployment
- **Docker containerization** using Python 3.9-slim base image
- **Environment secrets** managed via Google Secret Manager
- **Horizontal scaling** supported
- **HTTPS enabled** via Cloud Run

### Build and Deploy
```bash
# Local Docker build (for testing)
docker build -t phoenix .

# Production deployment (requires GCP setup)
gcloud builds submit --config cloudbuild.yaml
```

## Common Tasks and Troubleshooting

### Dependency Management
- **Main dependencies**: `requirements.txt` (26+ packages)
- **LLM-specific**: `requirements_llm.txt` (optional additional packages)
- **Update dependencies**: Modify requirements.txt, then `pip install -r requirements.txt`

### Environment Issues
- **Virtual environment not activated**: Check `which python` points to venv
- **Missing API keys**: Check .env file exists and has required keys
- **Firebase credentials**: Ensure GOOGLE_APPLICATION_CREDENTIALS path is correct
- **Port conflicts**: Use `./start_local.sh` which handles port cleanup

### Performance Considerations
- **AI API calls**: Can be slow (30-60 seconds) - implement proper timeouts
- **Firebase queries**: Cache results when possible
- **Large file uploads**: Limited by Cloud Run constraints
- **Session management**: Uses filesystem sessions (not scalable)

### Key File Locations
```
phoenix/
├── app.py                     # Main Flask application with Firebase init
├── requirements.txt           # 26+ core dependencies including Flask, Firebase, ML libs
├── start_local.sh            # Development startup (handles venv, port cleanup)
├── start_production.sh       # Production startup script
├── config/
│   ├── settings.py           # Centralized env vars and model configs
│   ├── gemini_models.py      # Gemini model definitions and pricing
│   └── openai_models.py      # OpenAI/Grok model configurations
├── services/                 # Service layer (business logic)
│   ├── enhanced_llm_service.py  # Multi-provider LLM with fallbacks
│   ├── subscription_middleware.py  # Feature gating and limits
│   └── dataset_discovery/    # Kaggle integration and Docker analysis
├── api/                      # Route blueprints (HTTP handling only)
├── middleware/               # CSRF protection, etc.
├── templates/                # Jinja2 templates with shared layouts
├── static/                   # Frontend assets (Bootstrap 5 based)
├── tests/                    # Unit tests (require Firebase setup)
├── scripts/                  # Utility scripts (log fetching, etc.)
└── flask_session/            # Session storage directory
```

## Development Workflow
1. **Always activate virtual environment first**
2. **Set required environment variables** before starting
3. **Use startup scripts** rather than manual python app.py
4. **Test locally** before deploying to production
5. **Check logs** for API rate limits and Firebase quota
6. **Validate Firebase connectivity** before testing auth features

## Limitations and Known Issues
- **Cannot run offline** - requires internet for API calls
- **Firebase dependency** - app won't start without proper credentials
- **API rate limits** - Gemini, Claude APIs have usage quotas
- **No automated testing** without Firebase setup
- **Single-threaded development server** - use gunicorn for production
- **Session storage** - not suitable for multi-instance deployment
## Cloud Run Jobs Integration (Reel Maker Video Stitching)

### Architecture Overview
Phoenix uses **Cloud Run Jobs** for isolated, scalable video processing:
- **Job Orchestrator** (`services/job_orchestrator.py`) - Manages job lifecycle and state
- **Video Stitching Job** (`jobs/video_stitching/`) - FFmpeg-based video processing
- **Progress Monitoring** - Real-time updates via Firestore subcollections
- **Smart Reconciliation** - Automatic detection of completed/stale jobs

### Job Orchestration Patterns

#### Triggering Jobs
```python
from services.job_orchestrator import get_job_orchestrator

orchestrator = get_job_orchestrator()
job = orchestrator.trigger_stitching_job(
    project_id=project_id,
    user_id=user_id,
    clip_paths=['gs://bucket/clip1.mp4', 'gs://bucket/clip2.mp4'],
    output_path='gs://bucket/output.mp4',
    orientation='portrait',  # or 'landscape'
    compression='optimized',  # or 'lossless'
    force_restart=False  # Skip duplicate job check
)
```

#### Job State Management
- **Jobs are tracked in Firestore** (`reel_jobs` collection)
- **Progress logs** stored in subcollection (`reel_jobs/{jobId}/progress_logs`)
- **Automatic reconciliation** checks:
  1. GCS output file exists → mark as completed
  2. Cloud Run execution status → update from API
  3. Job age > 15 minutes with no progress → mark as stale/failed

#### Fallback Strategy
- **Cloud Run Jobs unavailable?** → Falls back to local `video_stitching_service`
- **Import fails?** → Gracefully degrades to local processing
- **GCS client missing?** → Uses local file paths
- **Always backward compatible** with existing code

### Deployment Workflow

#### Local Development
```bash
# Activate environment
source venv/bin/activate

# Start app (uses local stitching automatically)
./start_local.sh

# Jobs won't execute but app remains fully functional
```

#### Dev Environment Deployment
```bash
# Deploy main app
gcloud builds submit --config cloudbuild-dev.yaml

# Deploy Cloud Run Jobs (one-time setup)
./scripts/setup_job_queue.sh
./scripts/deploy_jobs.sh
```

#### Production Deployment
```bash
# Deploy main app (automated via GitHub webhook)
git push origin main  # Triggers Cloud Build automatically

# Deploy jobs (if job code changed)
gcloud builds submit --config=jobs/video_stitching/cloudbuild.yaml

# Monitor deployment
gcloud run jobs describe reel-stitching-job --region=us-central1
```

### Cloud Run Jobs Configuration

#### Resource Allocation
- **CPU**: 2 vCPUs (hardcoded in cloudbuild.yaml)
- **Memory**: 4Gi (adequate for Veo videos at 1080x1920, 8s)
- **Timeout**: 900 seconds (15 minutes)
- **Max Retries**: 2
- **Region**: us-central1

**Why Static Resources?**
- Veo-generated videos have consistent specs (8s, 1080x1920)
- Predictable resource requirements
- Simpler configuration
- Cost-effective (~$0.003 per execution)

#### Job Structure
```
jobs/
├── video_stitching/
│   ├── main.py           # Entry point, handles Cloud Run execution
│   ├── stitcher.py       # FFmpeg video processing logic
│   ├── Dockerfile        # Container with Python 3.11 + FFmpeg
│   ├── cloudbuild.yaml   # Build AND deploy configuration
│   └── requirements.txt  # Job-specific dependencies
├── shared/               # Shared utilities (config, schemas, utils)
├── base/                 # Base framework (runners, monitoring, GCS)
└── cloudbuild-all-jobs.yaml  # Master config for bulk deployment
```

### Progress Monitoring Pattern

#### Publishing Progress (in Job)
```python
from jobs.base.progress_publisher import ProgressPublisher

publisher = ProgressPublisher(job_id)

# Publish progress update
publisher.publish(
    progress_percent=45.0,
    message='Stitching video: 50%',
    stage='stitching',
    metadata={'fps': 30.5, 'speed': 1.2}
)

# Publish FFmpeg progress (auto-calculates percentage)
publisher.publish_ffmpeg_progress(
    current_time=25.5,
    total_duration=60.0,
    fps=30.0,
    speed=1.5
)
```

#### Consuming Progress (in Frontend)
```javascript
// Fetch progress logs
const response = await fetch(`/api/reel/projects/${projectId}/jobs/${jobId}/progress?since=0`);
const { logs, job_status } = await response.json();

// Use JobProgressMonitor component
const monitor = new JobProgressMonitor({
  container: document.getElementById('progress-container'),
  fetchProgress: async () => {
    const res = await fetch(progressEndpoint);
    return res.json();
  },
  pollInterval: 3500  // 3.5 seconds
});
```

### Common Patterns and Best Practices

#### Pattern 1: Check for Existing Jobs Before Starting
```python
# In api/reel_routes.py stitch_clips endpoint
existing_job = orchestrator._get_active_job(project_id, "video_stitching")
if existing_job and existing_job.status in ['queued', 'running']:
    return jsonify({
        "success": False,
        "error": "Job already in progress"
    }), 409
```

#### Pattern 2: Graceful Error Handling with Fallbacks
```python
try:
    from services.job_orchestrator import get_job_orchestrator
    JOB_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    JOB_ORCHESTRATOR_AVAILABLE = False
    logger.warning("Cloud Run Jobs unavailable, using local processing")

if JOB_ORCHESTRATOR_AVAILABLE:
    # Use Cloud Run Jobs
    job = orchestrator.trigger_stitching_job(...)
else:
    # Fall back to local processing
    video_stitching_service.stitch_clips(...)
```

#### Pattern 3: Smart Job Reconciliation on Project Load
```python
# When loading a project with status='stitching', reconcile state
existing_job = orchestrator._get_active_job(project_id, "video_stitching")
if existing_job:
    job_data = db.collection('reel_jobs').document(existing_job.job_id).get().to_dict()
    was_updated = orchestrator._auto_reconcile_job_state(existing_job.job_id, job_data)
    if was_updated:
        # Job state changed, re-fetch project
        project = reel_project_service.get_project(project_id, user_id)
```

#### Pattern 4: Progress Logs with Structured Data
```python
# Store progress in Firestore with metadata
progress_ref.document(f"{log_counter:05d}").set({
    'timestamp': datetime.now(timezone.utc),
    'progress_percent': 65.0,
    'message': 'Stitching video: 70%',
    'stage': 'stitching',
    'log_number': log_counter,
    'metadata': {
        'fps': 30.5,
        'speed': 1.2,
        'eta_seconds': 45
    }
})
```

### Troubleshooting Cloud Run Jobs

#### Job Not Starting
1. **Check Cloud Tasks queue**: `gcloud tasks queues describe reel-jobs-queue --location=us-central1`
2. **Check job exists**: `gcloud run jobs describe reel-stitching-job --region=us-central1`
3. **Check IAM permissions**: Service account needs Cloud Run Admin, Storage Object Admin, Firestore User

#### Job Stuck in "Running"
- **Reconciliation runs automatically** when project is loaded
- **Manual reconciliation**: Call `orchestrator._auto_reconcile_job_state(job_id, job_data)`
- **Check Cloud Run execution**: `gcloud run jobs executions list --region=us-central1`

#### Progress Not Updating
1. **Check Firestore writes**: Look for `progress_logs` subcollection in job document
2. **Check ProgressPublisher initialization**: Must pass `job_id` to VideoStitcher
3. **Verify polling**: Frontend should poll every 3.5 seconds

#### GCS Output Missing
- **Reconciliation checks GCS automatically**: If file exists, marks job as completed
- **Manual check**: `gsutil ls gs://phoenix-videos/reel-maker/[project-id]/`
- **Verify permissions**: Job service account needs Storage Object Admin

### Key Files for Cloud Run Jobs

```
📁 Core Service
services/job_orchestrator.py        # Job lifecycle management

📁 Job Implementation  
jobs/video_stitching/main.py        # Job entry point
jobs/video_stitching/stitcher.py    # FFmpeg processing
jobs/base/progress_publisher.py     # Firestore progress updates
jobs/base/gcs_client.py             # GCS operations

📁 API Integration
api/reel_routes.py                  # stitch_clips endpoint, progress endpoint

📁 Deployment
jobs/video_stitching/cloudbuild.yaml     # Build & deploy config
scripts/setup_job_queue.sh               # One-time infrastructure setup
scripts/deploy_jobs.sh                   # Deploy jobs

📁 Frontend
static/reel_maker/components/JobProgressMonitor.js    # Progress UI
static/reel_maker/components/progress-monitor-integration.js
```

### Cost Considerations
- **Cloud Run Jobs**: Pay only when running (~$0.003 per execution)
- **Cloud Tasks**: Free tier covers typical usage
- **Firestore**: Progress logs cleaned up after completion
- **GCS**: Standard storage costs for videos
- **Monthly estimate** (1000 stitching jobs): ~$3.50

### Future Enhancements Roadmap
1. **Dynamic resource allocation** - Scale CPU/RAM based on video specs
2. **Batch processing** - Multiple projects in single job
3. **GPU acceleration** - For faster encoding
4. **Webhook notifications** - Alert users on completion
5. **Analytics dashboard** - Job success rate, avg duration, cost tracking
