# Automated Cloud Run Jobs Deployment Guide

## Overview
This guide explains how to set up automated deployments for Cloud Run Jobs, enabling them to deploy automatically on code changes just like the main Phoenix application.

## Deployment Architecture

### Current Setup
- **Main App (Cloud Run Service)**: Auto-deploys via Cloud Build triggers on push to `main` or `dev` branches
- **Cloud Run Jobs**: Can now auto-deploy via dedicated Cloud Build triggers

### Two Deployment Strategies

#### Strategy 1: Individual Job Triggers (Recommended for Production)
Each job has its own trigger that activates only when that job's code changes.

**Advantages:**
- Faster builds (only affected job rebuilds)
- Clearer logs (one job per build)
- Better resource utilization
- Independent versioning per job

**Use Case:** Production environment with multiple stable jobs

#### Strategy 2: Unified Job Trigger
Single trigger rebuilds ALL jobs when any job code changes.

**Advantages:**
- Simpler trigger management
- Ensures all jobs stay in sync
- Good for monolithic job releases

**Use Case:** Development environment or when jobs have shared dependencies

## Setup Instructions

### Prerequisites
```bash
# Ensure you have gcloud CLI installed and authenticated
gcloud auth login
gcloud config set project phoenix-project-386

# Verify GitHub repo is connected to Cloud Build
gcloud builds triggers list
```

### Option A: Individual Job Triggers (Recommended)

#### 1. Create Trigger for Video Stitching Job
```bash
gcloud builds triggers create github \
  --name="reel-stitching-job-deploy" \
  --description="Auto-deploy video stitching job on code changes" \
  --repo-name="phoenix" \
  --repo-owner="sumanurawat" \
  --branch-pattern="^main$" \
  --build-config="jobs/video_stitching/cloudbuild.yaml" \
  --included-files="jobs/video_stitching/**" \
  --region=us-central1
```

**Trigger Details:**
- **Name**: `reel-stitching-job-deploy`
- **Activates When**: Changes to `jobs/video_stitching/` directory on main branch
- **Builds From**: `jobs/video_stitching/cloudbuild.yaml`
- **Deploys To**: `reel-stitching-job` Cloud Run Job

#### 2. Add Future Jobs (Template)
```bash
gcloud builds triggers create github \
  --name="[JOB-NAME]-deploy" \
  --description="Auto-deploy [job description]" \
  --repo-name="phoenix" \
  --repo-owner="sumanurawat" \
  --branch-pattern="^main$" \
  --build-config="jobs/[job-directory]/cloudbuild.yaml" \
  --included-files="jobs/[job-directory]/**" \
  --region=us-central1
```

### Option B: Unified Job Trigger

#### Create Single Trigger for All Jobs
```bash
gcloud builds triggers create github \
  --name="all-jobs-deploy" \
  --description="Auto-deploy all Cloud Run Jobs on any job code change" \
  --repo-name="phoenix" \
  --repo-owner="sumanurawat" \
  --branch-pattern="^main$" \
  --build-config="jobs/cloudbuild-all-jobs.yaml" \
  --included-files="jobs/**" \
  --region=us-central1
```

**Trigger Details:**
- **Name**: `all-jobs-deploy`
- **Activates When**: ANY change to `jobs/` directory on main branch
- **Builds From**: `jobs/cloudbuild-all-jobs.yaml` (master config)
- **Deploys To**: All jobs defined in master config

## Development Workflow

### With Automated Deployment

#### 1. Make Changes to Job Code
```bash
# Example: Update video stitching logic
vim jobs/video_stitching/main.py

# Or update job dependencies
vim jobs/video_stitching/requirements.txt
```

#### 2. Commit and Push
```bash
git add jobs/video_stitching/
git commit -m "feat(stitching): improved video quality"
git push origin main
```

#### 3. Automatic Deployment Happens
- Cloud Build trigger activates automatically
- Builds Docker image with new code
- Pushes to Container Registry
- Updates Cloud Run Job with new image
- **No manual deployment needed!**

#### 4. Verify Deployment
```bash
# Check build status
gcloud builds list --limit=5

# Verify job was updated
gcloud run jobs describe reel-stitching-job --region=us-central1 --format="value(status.observedGeneration)"

# Check job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=reel-stitching-job" --limit=20 --format=json
```

### Manual Deployment (Still Available)
You can still manually deploy if needed:

```bash
# Deploy single job
gcloud builds submit --config=jobs/video_stitching/cloudbuild.yaml

# Deploy all jobs
gcloud builds submit --config=jobs/cloudbuild-all-jobs.yaml
```

## Trigger Management

### List All Triggers
```bash
gcloud builds triggers list --region=us-central1
```

### View Trigger Details
```bash
gcloud builds triggers describe reel-stitching-job-deploy --region=us-central1
```

### Update Trigger
```bash
gcloud builds triggers update reel-stitching-job-deploy \
  --region=us-central1 \
  --branch-pattern="^main$|^release/.*$"  # Add release branches
```

### Disable Trigger Temporarily
```bash
gcloud builds triggers update reel-stitching-job-deploy \
  --region=us-central1 \
  --disabled
```

### Re-enable Trigger
```bash
gcloud builds triggers update reel-stitching-job-deploy \
  --region=us-central1 \
  --no-disabled
```

### Delete Trigger
```bash
gcloud builds triggers delete reel-stitching-job-deploy --region=us-central1
```

## Adding New Jobs

### Step-by-Step Guide

#### 1. Create Job Directory Structure
```bash
mkdir -p jobs/new_job
cd jobs/new_job
```

#### 2. Create Dockerfile
```dockerfile
# jobs/new_job/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY jobs/new_job/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY jobs/new_job/ .
COPY services/ ./services/
COPY config/ ./config/

# Run job
CMD ["python", "main.py"]
```

#### 3. Create Cloud Build Config
```yaml
# jobs/new_job/cloudbuild.yaml
steps:
  # Build image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/new-job:latest'
      - '-f'
      - 'jobs/new_job/Dockerfile'
      - '.'

  # Push image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/new-job:latest']

  # Deploy to Cloud Run Jobs
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'jobs'
      - 'update'
      - 'new-job'
      - '--image'
      - 'gcr.io/$PROJECT_ID/new-job:latest'
      - '--region'
      - 'us-central1'
      - '--cpu'
      - '2'
      - '--memory'
      - '4Gi'
      - '--timeout'
      - '600'
      - '--max-retries'
      - '2'

images:
  - 'gcr.io/$PROJECT_ID/new-job:latest'

timeout: '1200s'
```

#### 4. Create Cloud Run Job (First Time)
```bash
gcloud run jobs create new-job \
  --image=gcr.io/phoenix-project-386/new-job:latest \
  --region=us-central1 \
  --cpu=2 \
  --memory=4Gi \
  --timeout=600 \
  --max-retries=2
```

#### 5. Create Automated Trigger
```bash
gcloud builds triggers create github \
  --name="new-job-deploy" \
  --description="Auto-deploy new job on code changes" \
  --repo-name="phoenix" \
  --repo-owner="sumanurawat" \
  --branch-pattern="^main$" \
  --build-config="jobs/new_job/cloudbuild.yaml" \
  --included-files="jobs/new_job/**" \
  --region=us-central1
```

#### 6. Update Master Config (Optional)
If using unified deployment, add to `jobs/cloudbuild-all-jobs.yaml`:

```yaml
# Add to steps section
- name: 'gcr.io/cloud-builders/docker'
  id: 'build-new-job'
  args:
    - 'build'
    - '-t'
    - 'gcr.io/$PROJECT_ID/new-job:latest'
    - '-f'
    - 'jobs/new_job/Dockerfile'
    - '.'

# Add to images section
images:
  - 'gcr.io/$PROJECT_ID/new-job:latest'
```

## Monitoring and Debugging

### Check Build History
```bash
# Recent builds
gcloud builds list --limit=10

# Builds for specific trigger
gcloud builds list --filter="buildTriggerId:reel-stitching-job-deploy"
```

### View Build Logs
```bash
# Get build ID from list above
gcloud builds log [BUILD_ID]

# Or view in Cloud Console
echo "https://console.cloud.google.com/cloud-build/builds?project=phoenix-project-386"
```

### Debug Failed Builds

#### Common Issues

**1. Dockerfile Not Found**
```
Error: Cannot find Dockerfile at jobs/video_stitching/Dockerfile
```
**Fix:** Check path in cloudbuild.yaml matches actual file location

**2. Permission Denied**
```
Error: Permission denied: Cloud Build service account cannot update job
```
**Fix:** Grant Cloud Run Admin role to Cloud Build service account
```bash
PROJECT_NUMBER=$(gcloud projects describe phoenix-project-386 --format="value(projectNumber)")
gcloud projects add-iam-policy-binding phoenix-project-386 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
```

**3. Image Not Found During Deployment**
```
Error: Image not found: gcr.io/phoenix-project-386/reel-stitching-job:latest
```
**Fix:** Ensure push step completes before deploy step (use `waitFor`)

**4. Job Not Found**
```
Error: Resource not found: Job 'new-job' not found
```
**Fix:** Create job manually first before automated deployment can update it

### View Job Execution Logs
```bash
# Logs from job executions
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=reel-stitching-job" \
  --limit=50 \
  --format=json

# Filter by severity
gcloud logging read \
  "resource.type=cloud_run_job AND severity>=ERROR" \
  --limit=20
```

## Cost Considerations

### Cloud Build Costs
- **Free tier**: 120 build-minutes per day
- **Paid tier**: $0.003 per build-minute after free tier
- **Average job build**: 3-5 minutes = ~$0.01-0.015 per build

### Optimization Tips
1. **Use smaller base images**: `python:3.9-slim` vs `python:3.9` saves ~500MB
2. **Layer caching**: Order Dockerfile commands for better caching
3. **Targeted triggers**: Use `--included-files` to avoid unnecessary builds
4. **Parallel builds**: Individual triggers build only affected jobs

### Example Monthly Cost
Assuming 50 code changes/month to jobs:
- **Strategy 1 (Individual)**: 50 builds × $0.012 = **$0.60/month**
- **Strategy 2 (Unified)**: 50 builds × $0.015 = **$0.75/month**

## Best Practices

### 1. Use Semantic Versioning for Job Images
```yaml
# In cloudbuild.yaml
- name: 'gcr.io/cloud-builders/docker'
  args:
    - 'build'
    - '-t'
    - 'gcr.io/$PROJECT_ID/job-name:latest'
    - '-t'
    - 'gcr.io/$PROJECT_ID/job-name:v1.2.3'  # Semantic version
    - '-t'
    - 'gcr.io/$PROJECT_ID/job-name:$SHORT_SHA'  # Git commit hash
```

### 2. Tag Images with Build Metadata
```yaml
images:
  - 'gcr.io/$PROJECT_ID/job-name:latest'
  - 'gcr.io/$PROJECT_ID/job-name:$BUILD_ID'
  - 'gcr.io/$PROJECT_ID/job-name:$SHORT_SHA'
```

### 3. Test in Dev Environment First
```bash
# Create dev branch trigger
gcloud builds triggers create github \
  --name="reel-stitching-job-dev" \
  --branch-pattern="^dev$" \
  --build-config="jobs/video_stitching/cloudbuild.yaml" \
  --substitutions="_JOB_SUFFIX=-dev"  # Deploy to dev job
```

### 4. Use Substitutions for Flexibility
```yaml
# cloudbuild.yaml
substitutions:
  _REGION: us-central1
  _CPU: '2'
  _MEMORY: 4Gi

steps:
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - '--region'
      - '${_REGION}'
      - '--cpu'
      - '${_CPU}'
      - '--memory'
      - '${_MEMORY}'
```

### 5. Add Health Checks
```python
# In job main.py
def health_check():
    """Verify job dependencies before execution"""
    required_env = ['GCS_BUCKET', 'FIREBASE_PROJECT']
    missing = [var for var in required_env if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing: {', '.join(missing)}")

if __name__ == "__main__":
    health_check()
    run_job()
```

## Migration from Manual to Automated

### Current State (Manual)
```bash
# Developer has to remember to run this after code changes
./deploy_stitching_job.sh
```

### Future State (Automated)
```bash
# Developer just commits code
git commit -am "feat: improved stitching"
git push origin main

# Deployment happens automatically! ✨
```

### Migration Checklist
- [ ] Create Cloud Build trigger for each job
- [ ] Test trigger with small code change
- [ ] Verify automated deployment works
- [ ] Update team documentation
- [ ] Archive manual deployment scripts (but keep as backup)
- [ ] Monitor first few automated deployments
- [ ] Update CI/CD documentation

## Rollback Strategy

### Option 1: Deploy Previous Image
```bash
# Find previous working image
gcloud container images list-tags gcr.io/phoenix-project-386/reel-stitching-job

# Deploy specific version
gcloud run jobs update reel-stitching-job \
  --image=gcr.io/phoenix-project-386/reel-stitching-job:$PREVIOUS_BUILD_ID \
  --region=us-central1
```

### Option 2: Revert Git Commit and Re-trigger
```bash
# Revert problematic commit
git revert HEAD
git push origin main

# Trigger auto-deploys reverted version
```

### Option 3: Disable Trigger and Deploy Manually
```bash
# Disable automated trigger
gcloud builds triggers update reel-stitching-job-deploy --disabled --region=us-central1

# Deploy known-good version manually
gcloud builds submit --config=jobs/video_stitching/cloudbuild.yaml

# Re-enable trigger after fix
gcloud builds triggers update reel-stitching-job-deploy --no-disabled --region=us-central1
```

## Next Steps

### Immediate Actions
1. ✅ Created `jobs/video_stitching/cloudbuild.yaml` with deployment step
2. ✅ Created `jobs/cloudbuild-all-jobs.yaml` for unified deployment
3. ⏳ **Next:** Create Cloud Build trigger
4. ⏳ **Next:** Test automated deployment with small change
5. ⏳ **Next:** Add frontend validation for 20-clip limit

### Future Enhancements
- Add automated testing before deployment
- Implement canary deployments for jobs
- Add Slack/Discord notifications for deployments
- Create dashboard for job deployment status
- Add automated rollback on failure

## Quick Reference

### Create Trigger (Copy-Paste Ready)
```bash
gcloud builds triggers create github \
  --name="reel-stitching-job-deploy" \
  --description="Auto-deploy video stitching job" \
  --repo-name="phoenix" \
  --repo-owner="sumanurawat" \
  --branch-pattern="^main$" \
  --build-config="jobs/video_stitching/cloudbuild.yaml" \
  --included-files="jobs/video_stitching/**" \
  --region=us-central1 \
  --project=phoenix-project-386
```

### Check Deployment Status
```bash
# List recent builds
gcloud builds list --limit=5

# Check job version
gcloud run jobs describe reel-stitching-job --region=us-central1 --format="value(metadata.name,status.latestCreatedExecution)"
```

### Manual Override
```bash
# Force manual deployment
gcloud builds submit --config=jobs/video_stitching/cloudbuild.yaml --project=phoenix-project-386
```

---

**Pro Tip:** Start with individual job triggers for production. Once comfortable, consider unified triggers for environments where all jobs should deploy together.
