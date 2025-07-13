# Common Operations Guide for AI Agents

This document provides standardized procedures for the most frequently performed operations in the Phoenix codebase. These are battle-tested patterns that agents should follow for consistency and reliability.

## 🔍 **Log Analysis & Debugging** (Most Critical!)

### **Primary Log Fetching Tool**
The `scripts/fetch_logs.py` script is your most powerful debugging tool. It provides intelligent error analysis with pattern recognition and specific recommendations.

```bash
# Get recent production errors with analysis
python scripts/fetch_logs.py --environment production --hours 6 --severity ERROR

# Search for specific issues
python scripts/fetch_logs.py --search "dataset" --hours 12
python scripts/fetch_logs.py --search "claude" --hours 6
python scripts/fetch_logs.py --search "404" --hours 2

# Full analysis with JSON export for complex debugging
python scripts/fetch_logs.py --environment staging --hours 24 --save-json

# Focus on warnings and errors
python scripts/fetch_logs.py --severity WARNING --severity ERROR --hours 4
```

### **Log Analysis Features**
The script automatically provides:
- **Error Pattern Recognition**: Categorizes common issues
- **Severity Breakdown**: Shows ERROR/WARNING/INFO counts  
- **Recent Error Summary**: Last 10 errors with context
- **Specific Recommendations**: Actionable fix suggestions
- **Time-based Analysis**: Filters by hours/days

### **Environment Management Script**
```bash
# Check all environments at once
./scripts/manage_env.sh status

# Environment-specific logs
./scripts/manage_env.sh logs staging --hours 6
./scripts/manage_env.sh logs production --search "error"

# Open environments in browser
./scripts/manage_env.sh open staging
./scripts/manage_env.sh open production
```

## 🚀 **Deployment Operations**

### **Standard Deployment Flow**
```bash
# 1. Check current status
./scripts/manage_env.sh status

# 2. Deploy to staging (dev branch)
git checkout dev
git add .
git commit -m "feat: your change description"
git push origin dev

# 3. Monitor staging deployment
sleep 60  # Wait for build
gcloud builds list --limit=3 --project=phoenix-project-386
./scripts/manage_env.sh logs staging --hours 1

# 4. Deploy to production (main branch) - only after staging validation
git checkout main
git merge dev
git push origin main

# 5. Monitor production deployment
./scripts/manage_env.sh logs production --hours 1
```

### **Emergency Hotfix Pattern**
```bash
# 1. Create hotfix branch from main
git checkout main
git checkout -b hotfix/critical-issue

# 2. Make minimal fix and test locally
./start_local.sh  # Test fix

# 3. Deploy immediately to production
git add .
git commit -m "hotfix: critical issue description"
git checkout main
git merge hotfix/critical-issue
git push origin main

# 4. Monitor and merge back to dev
./scripts/manage_env.sh logs production --hours 1
git checkout dev
git merge main
git push origin dev
```

## 🧪 **Testing Procedures**

### **Pre-Deployment Testing**
```bash
# 1. Local environment testing
./start_local.sh

# 2. AI service testing
python test_enhanced_llm.py

# 3. Feature-specific testing
python test_dataset_discovery.py
python test_docker_fallback.py

# 4. Debug specific components
python debug_kaggle_api.py
python debug_dataset_info.py
```

### **Post-Deployment Validation**
```bash
# 1. Check deployment status
gcloud builds list --limit=1 --project=phoenix-project-386

# 2. Verify services are responding
curl -I https://phoenix-234619602247.us-central1.run.app
curl -I https://phoenix-dev-234619602247.us-central1.run.app

# 3. Check for immediate errors
./scripts/manage_env.sh logs production --hours 1
./scripts/manage_env.sh logs staging --hours 1

# 4. Test key functionality
# - Visit the web interface
# - Test dataset discovery
# - Verify AI model selection
```

## 🔧 **Development Patterns**

### **Starting New Work**
```bash
# 1. Switch to dev and pull latest
git checkout dev
git pull origin dev

# 2. Check environment status
./scripts/manage_env.sh status

# 3. Start local development
./start_local.sh

# 4. Create feature branch (for large features)
git checkout -b feature/new-feature-name
```

### **Code Modification Pattern**
```bash
# 1. Make changes following existing patterns
# 2. Test locally first
./start_local.sh

# 3. Run relevant tests
python test_enhanced_llm.py  # For AI changes
python debug_kaggle_api.py   # For dataset features

# 4. Deploy to staging for validation
git add .
git commit -m "feat: descriptive change message"
git push origin dev
```

### **Dependency Management**
```bash
# 1. Check Python compatibility (container uses Python 3.9)
# 2. Update requirements.txt with compatible versions
# 3. Test locally before deployment
pip install -r requirements.txt

# Example: Fix version compatibility issue
# Change: scikit-learn==1.7.0 (requires Python 3.10+)
# To: scikit-learn==1.6.1 (Python 3.9 compatible)
```

## 🔒 **Security & Secrets Management**

### **Environment Variables & Secrets**
```bash
# 1. Local development (.env file)
# - Never commit .env to git
# - Use .env.example for templates

# 2. Production secrets (GCP Secret Manager)
gcloud secrets list --project=phoenix-project-386
gcloud secrets describe phoenix-claude-api-key --project=phoenix-project-386

# 3. Adding new secrets
echo -n "SECRET_VALUE" | gcloud secrets create new-secret-name --data-file=- --project=phoenix-project-386
```

### **API Key Management**
- **Gemini API**: Store in `phoenix-gemini-api-key`
- **Claude API**: Store in `phoenix-claude-api-key` 
- **OpenAI API**: Store in `phoenix-openai-api-key`
- **Firebase**: Store in `phoenix-firebase-key`
- **Kaggle**: Store in `phoenix-kaggle-username` and `phoenix-kaggle-key`

## 🐛 **Troubleshooting Common Issues**

### **Build Failures**
```bash
# 1. Check build logs
gcloud builds list --limit=5 --project=phoenix-project-386
gcloud builds log [BUILD_ID] --project=phoenix-project-386

# 2. Common fixes:
# - Python version compatibility (use Python 3.9 compatible packages)
# - Missing dependencies in requirements.txt
# - Docker syntax errors
# - Import errors in Python code
```

### **Runtime Errors**
```bash
# 1. Check application logs
python scripts/fetch_logs.py --environment production --severity ERROR --hours 2

# 2. Common issues:
# - Missing environment variables
# - API key authentication failures
# - Firebase connection issues
# - Database query errors
```

### **Performance Issues**
```bash
# 1. Monitor resource usage
gcloud run services describe phoenix --region=us-central1
gcloud run services describe phoenix-dev --region=us-central1

# 2. Check for memory/CPU limits
# 3. Analyze slow queries in logs
python scripts/fetch_logs.py --search "timeout" --hours 6
```

## 📊 **Monitoring & Health Checks**

### **Service Health**
```bash
# 1. Check service status
./scripts/manage_env.sh status

# 2. Test endpoints
curl -f https://phoenix-234619602247.us-central1.run.app/health || echo "Health check failed"

# 3. Monitor error rates
python scripts/fetch_logs.py --environment production --hours 1 --severity ERROR
```

### **Cost Monitoring**
- **Production**: Only Gemini Flash 8B (cost-effective)
- **Development**: All models available but monitor usage
- **Localhost**: Full model access for testing

## 🔄 **Routine Maintenance**

### **Daily Checks**
```bash
# 1. Check for errors
python scripts/fetch_logs.py --environment production --hours 24 --severity ERROR

# 2. Monitor staging health  
./scripts/manage_env.sh logs staging --hours 6

# 3. Verify key services
# - Dataset discovery working
# - AI models responding
# - Authentication functioning
```

### **Weekly Reviews**
```bash
# 1. Review logs for patterns
python scripts/fetch_logs.py --environment production --hours 168 --save-json

# 2. Check resource usage
gcloud run services describe phoenix --region=us-central1

# 3. Update dependencies if needed
# 4. Review and merge accumulated changes
```

---

**💡 Remember**: The log fetching script (`scripts/fetch_logs.py`) is your primary diagnostic tool. It provides intelligent analysis and specific recommendations that save significant debugging time.