# Phoenix AI Platform

Phoenix is a Flask-based Python web application featuring multiple AI-powered tools including conversational AI (Derplexity), intelligent search (Doogle), news aggregation (Robin), and a URL shortener with analytics. The platform integrates Google Gemini, Claude, Grok APIs and uses Firebase Firestore for data persistence.

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

### Core Components
- **`app.py`** - Main Flask application entry point
- **`config/settings.py`** - Centralized configuration management
- **`services/`** - Backend services (LLM, auth, search, etc.)
- **`api/`** - Flask route blueprints for different features
- **`templates/`** - Jinja2 HTML templates
- **`static/`** - CSS, JavaScript, and image assets

### Key Services
- **LLM Service** (`services/llm_service.py`) - Google Gemini integration
- **Enhanced LLM Service** (`services/enhanced_llm_service.py`) - Multi-provider LLM
- **Auth Service** (`services/auth_service.py`) - Firebase authentication
- **Document Service** (`services/document_service.py`) - File processing
- **Search Service** (`services/search_service.py`) - Google Custom Search

### Database
- **Firebase Firestore** - Primary database for user data, links, analytics
- **No local database** - all data stored in cloud
- **Requires service account JSON** for local development

## Main Features and Routes

### Core Applications
1. **Derplexity** (`/apps/derplexity`) - Conversational AI interface
2. **Doogle** (`/apps/doogle`) - AI-powered search engine  
3. **Robin** (`/apps/robin`) - News aggregation and analysis
4. **URL Shortener** (`/apps/deeplink`) - Link shortening with analytics
5. **Dataset Discovery** (`/apps/dataset-discovery`) - Kaggle dataset search

### User Management
- **Authentication required** for most features
- **Firebase Auth integration** for login/signup
- **User profiles** and subscription management
- **Analytics tracking** for user interactions

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

### File Locations Reference
```
phoenix/
├── app.py                     # Main Flask application
├── requirements.txt           # Python dependencies  
├── requirements_llm.txt       # Additional LLM dependencies
├── .env.example              # Environment template
├── start_local.sh            # Development startup script
├── start_production.sh       # Production startup script
├── config/
│   ├── settings.py           # Application configuration
│   └── gemini_models.py      # AI model definitions
├── services/                 # Backend service modules
├── api/                      # Flask route blueprints
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS, JS, images
├── tests/                    # Test files (require Firebase)
└── scripts/                  # Utility scripts
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