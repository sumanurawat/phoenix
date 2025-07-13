# Deployment Procedures for AI Agents

This document provides step-by-step deployment procedures that AI agents can follow to safely deploy code changes to the Phoenix platform.

## 🚀 **Standard Deployment Flow**

### **Pre-Deployment Checklist**
```bash
# 1. Verify current environment status
./scripts/manage_env.sh status

# 2. Check for any ongoing builds
gcloud builds list --limit=3 --project=phoenix-project-386

# 3. Review recent production logs for stability
python scripts/fetch_logs.py --environment production --hours 2 --severity ERROR

# 4. Ensure you're on the correct branch
git status
git branch
```

### **Staging Deployment (dev branch)**
```bash
# 1. Switch to dev branch and ensure it's up to date
git checkout dev
git pull origin dev

# 2. Make your changes and commit
git add .
git commit -m "feat: descriptive change message following conventional commits"

# 3. Push to trigger staging deployment
git push origin dev

# 4. Monitor the build process
echo "Waiting for build to start..."
sleep 30
gcloud builds list --limit=1 --project=phoenix-project-386

# 5. Wait for deployment completion (typically 2-3 minutes)
echo "Waiting for deployment to complete..."
sleep 180

# 6. Verify staging deployment
curl -I https://phoenix-dev-234619602247.us-central1.run.app
./scripts/manage_env.sh logs staging --hours 1
```

### **Production Deployment (main branch)**
```bash
# ONLY deploy to production after thorough staging validation

# 1. Verify staging is stable
python scripts/fetch_logs.py --environment staging --hours 2 --severity ERROR
# Should show no recent errors

# 2. Switch to main and merge dev
git checkout main
git pull origin main
git merge dev

# 3. Push to trigger production deployment
git push origin main

# 4. Monitor production deployment closely
echo "Monitoring production deployment..."
sleep 30
gcloud builds list --limit=1 --project=phoenix-project-386

# 5. Wait for completion and verify
sleep 180
curl -I https://phoenix-234619602247.us-central1.run.app
./scripts/manage_env.sh logs production --hours 1
```

## 🔍 **Deployment Monitoring**

### **Build Status Monitoring**
```bash
# Check current build status
gcloud builds list --limit=5 --project=phoenix-project-386

# Monitor specific build (replace BUILD_ID)
gcloud builds log BUILD_ID --project=phoenix-project-386

# Stream logs for ongoing build
gcloud builds log BUILD_ID --stream --project=phoenix-project-386
```

### **Service Health Verification**
```bash
# 1. Check HTTP response codes
curl -I https://phoenix-234619602247.us-central1.run.app      # Production
curl -I https://phoenix-dev-234619602247.us-central1.run.app  # Staging

# 2. Verify service configuration
gcloud run services describe phoenix --region=us-central1 --project=phoenix-project-386
gcloud run services describe phoenix-dev --region=us-central1 --project=phoenix-project-386

# 3. Check for immediate errors
python scripts/fetch_logs.py --environment production --hours 1 --severity ERROR
python scripts/fetch_logs.py --environment staging --hours 1 --severity ERROR
```

### **Functional Testing Post-Deployment**
```bash
# 1. Test key endpoints
curl -f https://phoenix-234619602247.us-central1.run.app/ || echo "Homepage failed"
curl -f https://phoenix-234619602247.us-central1.run.app/datasets || echo "Datasets failed"

# 2. Run automated tests if available
python test_enhanced_llm.py
python test_dataset_discovery.py

# 3. Manual verification checklist:
# - Homepage loads correctly
# - User authentication works
# - AI model selection functions
# - Dataset discovery searches work
# - Error pages display properly
```

## 🚨 **Emergency Procedures**

### **Hotfix Deployment**
For critical production issues requiring immediate fixes:

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-issue-description

# 2. Make minimal, targeted fix
# Edit only the files necessary to resolve the critical issue

# 3. Test fix locally
./start_local.sh
# Verify the fix resolves the issue

# 4. Commit and merge to main immediately
git add .
git commit -m "hotfix: brief description of critical fix"
git checkout main
git merge hotfix/critical-issue-description

# 5. Deploy to production
git push origin main

# 6. Monitor deployment closely
./scripts/manage_env.sh logs production --hours 1

# 7. Merge hotfix back to dev
git checkout dev
git merge main
git push origin dev

# 8. Clean up hotfix branch
git branch -d hotfix/critical-issue-description
```

### **Rollback Procedure**
If deployment fails or causes critical issues:

```bash
# 1. Identify last known good commit
git log --oneline -10

# 2. Create rollback branch
git checkout -b rollback/to-stable-state

# 3. Reset to last stable commit
git reset --hard LAST_GOOD_COMMIT_HASH

# 4. Force push to main (emergency only)
git push origin main --force

# 5. Monitor rollback deployment
./scripts/manage_env.sh logs production --hours 1

# 6. Update dev branch to match
git checkout dev
git reset --hard main
git push origin dev --force
```

## 🔒 **Security Considerations**

### **Secrets and Configuration**
```bash
# 1. Verify secrets are properly configured
gcloud secrets list --project=phoenix-project-386

# 2. Check service account permissions
gcloud run services describe phoenix --region=us-central1 --format="value(spec.template.spec.serviceAccountName)"

# 3. Validate environment variables in deployment
gcloud run services describe phoenix --region=us-central1 --format="value(spec.template.spec.template.spec.containers[0].env[].name)"
```

### **Access Control**
- Never commit sensitive information to git
- Use GCP Secret Manager for all credentials
- Verify service account has minimal required permissions
- Check that secrets are properly mounted in Cloud Run

## 📊 **Deployment Metrics**

### **Performance Benchmarks**
Track these metrics after each deployment:
- **Build Time**: Should be 2-3 minutes
- **Deployment Time**: Should be 30-60 seconds
- **First Response**: Should be <2 seconds after deployment
- **Error Rate**: Should be <1% in first hour

### **Monitoring Commands**
```bash
# Build performance
gcloud builds list --limit=1 --format="table(id,status,duration)"

# Service performance
gcloud run services describe phoenix --region=us-central1 --format="value(status.latestReadyRevisionName)"

# Error tracking
python scripts/fetch_logs.py --environment production --hours 1 --severity ERROR | grep -c "ERROR"
```

## 🔄 **Continuous Improvement**

### **Post-Deployment Review**
After each deployment:
1. **Document Issues**: Note any problems encountered
2. **Update Procedures**: Improve this guide based on experience
3. **Performance Analysis**: Review metrics and identify optimizations
4. **Team Feedback**: Incorporate lessons learned

### **Automation Opportunities**
Consider automating:
- Health checks after deployment
- Rollback triggers for failed deployments
- Notification systems for deployment status
- Performance regression detection

## 📝 **Deployment Log Template**

For major deployments, maintain a log:
```
Date: [YYYY-MM-DD]
Time: [HH:MM UTC]
Deployer: [Agent/User]
Branch: [main/dev]
Commit: [hash]
Build ID: [gcloud build id]
Duration: [X minutes]
Status: [SUCCESS/FAILED]
Issues: [none/description]
Rollback: [none/required]
Notes: [additional context]
```

---

**⚠️ Critical Reminders**:
1. **Never skip staging** - Always test in staging before production
2. **Monitor actively** - Watch logs for at least 30 minutes after production deployment
3. **Have rollback ready** - Know the last stable commit hash
4. **Test thoroughly** - Verify all major functionality after deployment
5. **Document issues** - Update procedures based on real experience