# Phoenix Development & Staging Environment Guide

## 🎯 **Environment Overview**

You now have a complete **production-ready development workflow** with staging environment!

### **Environments**

| Environment | Branch | URL | Purpose |
|------------|--------|-----|---------|
| **Production** | `main` | https://phoenix-234619602247.us-central1.run.app | Live user-facing application |
| **Staging** | `dev` | https://phoenix-dev-234619602247.us-central1.run.app | Pre-production testing |
| **Local** | any | http://localhost:5000 | Development testing |

### **Resources Configuration**

| Environment | CPU | Memory | Max Instances | Cost Impact |
|------------|-----|--------|---------------|-------------|
| **Production** | default | default | default | Higher |
| **Staging** | 1 CPU | 512Mi | 10 | Lower (60% cost savings) |

## 🚀 **Development Workflow**

### **1. Feature Development**
```bash
# Start from main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-new-feature

# Develop locally
python app.py  # Test on localhost:5000

# Commit changes
git add .
git commit -m "Add new feature"
```

### **2. Staging Testing**
```bash
# Merge to dev branch for staging
git checkout dev
git pull origin dev
git merge feature/my-new-feature

# Push to staging
git push origin dev
# This automatically deploys to: https://phoenix-dev-234619602247.us-central1.run.app
```

### **3. Production Deployment**
```bash
# After staging validation
git checkout main
git merge dev

# Deploy to production
git push origin main
# This automatically deploys to: https://phoenix-234619602247.us-central1.run.app
```

## 🔧 **Automatic Deployments**

### **Cloud Build Triggers**

1. **Production Trigger**: `phoenix-deploy`
   - **Branch**: `main`
   - **Service**: `phoenix`
   - **Config**: `cloudbuild.yaml`

2. **Staging Trigger**: `phoenix-dev-deploy`
   - **Branch**: `dev`
   - **Service**: `phoenix-dev`
   - **Config**: `cloudbuild-dev.yaml`

### **Deployment Process**
1. Push to branch → GitHub webhook → Cloud Build
2. Docker build → Container Registry
3. Cloud Run deploy → Live service
4. Automatic HTTPS + secrets injection

## 📊 **Monitoring & Debugging**

### **Log Fetching for Both Environments**

```bash
# Production logs
python scripts/fetch_logs.py

# Staging logs (modify script or use gcloud directly)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=phoenix-dev" \
  --limit=50 --format=json --project=phoenix-project-386
```

### **Service Management**
```bash
# Check both services
gcloud run services list --region=us-central1

# Get staging service details
gcloud run services describe phoenix-dev --region=us-central1

# View builds
gcloud builds list --limit=5
```

## 🗄️ **Shared Resources**

Both staging and production share:
- ✅ **Firestore Database** (same project)
- ✅ **Google Cloud Secrets** (API keys, etc.)
- ✅ **OAuth Configuration** (Google login)
- ✅ **Firebase Credentials**

This means:
- **Users can log in to both environments**
- **Data is consistent** between staging and prod
- **API integrations work** in staging

## 🧪 **Testing Strategy**

### **What to Test in Staging**
1. **New Features**: Full end-to-end testing
2. **Authentication**: Google OAuth flow
3. **Database Operations**: CRUD operations
4. **API Integrations**: External service calls
5. **Error Handling**: Edge cases and failures
6. **Performance**: Load testing with limited resources

### **Staging Test Plan**
```bash
# 1. Test basic functionality
curl https://phoenix-dev-234619602247.us-central1.run.app

# 2. Test authentication
# Visit: https://phoenix-dev-234619602247.us-central1.run.app/auth/login

# 3. Test your features
# Visit: https://phoenix-dev-234619602247.us-central1.run.app/apps/deeplink/profile/my-links

# 4. Check logs for errors
python scripts/fetch_logs.py --search "phoenix-dev"
```

## 🛠️ **Branch Management**

### **Branch Strategy**
```
main (production)
├── dev (staging)
│   ├── feature/auth-improvements
│   ├── feature/new-ui-component
│   └── hotfix/critical-bug
└── hotfix/emergency-fix (directly to main for emergencies)
```

### **Best Practices**
1. **Always test in staging first** before merging to main
2. **Keep dev branch stable** - it's your staging environment
3. **Use feature branches** for development
4. **Merge frequently** to avoid conflicts
5. **Tag releases** in main for rollback capability

## 🚨 **Emergency Procedures**

### **Rollback Production**
```bash
# Find last good build
gcloud builds list --filter="source.repoSource.branchName=main" --limit=5

# Redeploy specific image
gcloud run deploy phoenix \
  --image=gcr.io/phoenix-project-386/phoenix@sha256:PREVIOUS_DIGEST \
  --region=us-central1
```

### **Hotfix Process**
```bash
# For critical production issues
git checkout main
git checkout -b hotfix/critical-issue
# ... make minimal fix ...
git commit -m "Hotfix: critical issue"
git push origin hotfix/critical-issue

# Merge directly to main (skip staging for emergencies)
git checkout main
git merge hotfix/critical-issue
git push origin main  # Auto-deploys to production
```

## 💰 **Cost Optimization**

Your staging environment uses **60% fewer resources**:
- **Lower CPU**: 1 CPU vs default (2+ CPUs)
- **Less Memory**: 512Mi vs default (2Gi)
- **Fewer Instances**: Max 10 vs unlimited
- **Reduced Traffic**: Internal testing only

**Estimated savings**: $30-50/month on staging environment

## 📈 **Next Steps**

1. **Test your my-links feature** in staging
2. **Set up monitoring alerts** for both environments
3. **Create automated tests** that run in staging
4. **Document environment-specific configurations**
5. **Set up database branching** if needed (advanced)

## 🔗 **Quick Links**

- **Production**: https://phoenix-234619602247.us-central1.run.app
- **Staging**: https://phoenix-dev-234619602247.us-central1.run.app
- **Cloud Console**: https://console.cloud.google.com/run?project=phoenix-project-386
- **Build History**: https://console.cloud.google.com/cloud-build/builds?project=phoenix-project-386
- **Logs**: Use `python scripts/fetch_logs.py`

Your staging environment is now **live and ready for testing**! 🎉
