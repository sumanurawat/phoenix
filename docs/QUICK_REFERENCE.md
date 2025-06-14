# 🚀 Phoenix Development - Quick Reference

## 🔗 Environment URLs
- **Local**: `http://localhost:5000`
- **Staging**: `https://phoenix-dev-234619602247.us-central1.run.app`
- **Production**: `https://phoenix-234619602247.us-central1.run.app`

## ⚡ Quick Commands

### Environment Management
```bash
# Check status of both environments
./scripts/manage_env.sh status

# Open environments in browser
./scripts/manage_env.sh open staging
./scripts/manage_env.sh open production

# Deploy to environments
./scripts/manage_env.sh deploy staging     # Pushes current dev branch
./scripts/manage_env.sh deploy production  # Pushes current main branch
```

### Log Monitoring
```bash
# Fetch logs from environments
./scripts/manage_env.sh logs staging --hours 6
./scripts/manage_env.sh logs production --hours 2

# Search for specific issues
python scripts/fetch_logs.py --environment staging --search "error"
python scripts/fetch_logs.py --environment staging --search "my-links"

# Advanced log fetching
python scripts/fetch_logs.py --environment staging --severity ERROR --save-json
python scripts/fetch_logs.py --environment production --hours 24 --limit 1000
```

### Git Workflow
```bash
# Start working on new feature
git checkout dev
git pull origin dev
git checkout -b feature/your-feature

# Push to staging for testing
git checkout dev
git merge feature/your-feature
git push origin dev  # Auto-deploys to staging

# Release to production
git checkout main
git merge dev
git push origin main  # Auto-deploys to production
```

### Local Development
```bash
# Start local server
./start_local.sh

# Run in background and monitor logs
./start_local.sh &
tail -f logs/app.log
```

## 🔧 Build & Deployment

### Check Build Status
```bash
# List recent builds
gcloud builds list --limit=5

# Monitor current build
gcloud builds list --limit=1 --filter="status=WORKING"

# View build logs
gcloud builds log [BUILD_ID]
```

### Service Management
```bash
# Check service details
gcloud run services describe phoenix-dev --region=us-central1
gcloud run services describe phoenix --region=us-central1

# List all services
gcloud run services list --region=us-central1
```

## 🚨 Emergency Commands

### Quick Rollback (if needed)
```bash
# Get previous revision
gcloud run revisions list --service=phoenix --region=us-central1

# Rollback to previous version
gcloud run services update-traffic phoenix \
  --to-revisions=[PREVIOUS_REVISION]=100 \
  --region=us-central1
```

### Force Redeploy
```bash
# If deployment seems stuck, trigger manual deployment
gcloud builds submit --config=cloudbuild-dev.yaml  # For staging
gcloud builds submit --config=cloudbuild.yaml      # For production
```

## 📊 Monitoring Shortcuts

### Health Checks
```bash
# Quick health check
curl -I https://phoenix-dev-234619602247.us-central1.run.app
curl -I https://phoenix-234619602247.us-central1.run.app

# Check specific endpoints
curl https://phoenix-dev-234619602247.us-central1.run.app/health
```

### Error Investigation
```bash
# Check for recent errors in staging
python scripts/fetch_logs.py --environment staging --severity ERROR --hours 2

# Check for specific error patterns
python scripts/fetch_logs.py --environment staging --search "BuildError"
python scripts/fetch_logs.py --environment staging --search "Firebase"
python scripts/fetch_logs.py --environment staging --search "auth_bp"
```

## 🎯 Testing Checklist

### Before Staging Deploy
- [ ] Local tests pass
- [ ] `./start_local.sh` runs without errors
- [ ] All new features work locally

### Before Production Deploy
- [ ] Staging environment tested thoroughly
- [ ] No errors in staging logs: `./scripts/manage_env.sh logs staging --hours 2`
- [ ] All critical user flows verified
- [ ] Performance acceptable

### After Production Deploy
- [ ] Monitor logs: `./scripts/manage_env.sh logs production --hours 1`
- [ ] Test critical endpoints
- [ ] Verify metrics in Cloud Console

## 🛠️ File Locations

### Configuration Files
- `cloudbuild.yaml` - Production build config
- `cloudbuild-dev.yaml` - Staging build config
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies

### Scripts
- `scripts/manage_env.sh` - Environment management
- `scripts/fetch_logs.py` - Log fetching and analysis
- `start_local.sh` - Local development server

### Documentation
- `docs/DEVELOPMENT_WORKFLOW_GUIDE.md` - Complete workflow guide
- `docs/STAGING_SETUP_COMPLETE.md` - Setup completion summary
- `docs/LOG_FETCHING_USAGE.md` - Log fetching usage guide

---

💡 **Pro Tip**: Bookmark this file and use `./scripts/manage_env.sh status` as your daily starting command!
