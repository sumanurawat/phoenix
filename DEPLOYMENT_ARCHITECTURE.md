# Phoenix Deployment Architecture - Complete Guide

## 🏗️ Current Deployment Setup

### Overview
Your Phoenix application has **AUTOMATED** deployment for the main app, but **MANUAL** deployment for Cloud Run Jobs.

---

## 🤖 AUTOMATED Deployments (Main App)

### Production (Main Branch)
- **Trigger Name**: `phoenix-deploy`
- **Branch**: `main`
- **Config File**: `cloudbuild.yaml`
- **Cloud Run Service**: `phoenix`
- **How It Works**:
  1. You push code to `main` branch
  2. GitHub webhook notifies Google Cloud Build
  3. Cloud Build automatically runs `cloudbuild.yaml`
  4. Builds Docker image: `gcr.io/phoenix-project-386/phoenix`
  5. Deploys to Cloud Run service `phoenix` in `us-central1`
  6. Updates secrets and environment variables automatically

### Dev (Dev Branch)
- **Trigger Name**: `phoenix-dev-deploy`
- **Branch**: `dev`
- **Config File**: `cloudbuild-dev.yaml`
- **Cloud Run Service**: `phoenix-dev`
- **How It Works**:
  1. You push code to `dev` branch
  2. GitHub webhook notifies Google Cloud Build
  3. Cloud Build automatically runs `cloudbuild-dev.yaml`
  4. Builds Docker image: `gcr.io/phoenix-project-386/phoenix-dev`
  5. Deploys to Cloud Run service `phoenix-dev` in `us-central1`

**✅ What Gets Deployed Automatically:**
- Flask application code (`app.py`, `api/*`, `services/*`)
- Static files (`static/reel_maker/*` including React bundle)
- Templates (`templates/*`)
- Configuration files
- **BUT NOT Cloud Run Jobs** (see below)

---

## 🔧 MANUAL Deployments (Cloud Run Jobs)

### Video Stitching Job
- **Name**: `reel-stitching-job`
- **Config File**: `jobs/video_stitching/cloudbuild.yaml`
- **Image**: `gcr.io/phoenix-project-386/reel-stitching-job`
- **⚠️ NO AUTOMATED TRIGGER**: Must deploy manually

### Why Manual?
1. **Different Build Context**: Jobs use `jobs/video_stitching/Dockerfile` (not main `Dockerfile`)
2. **Separate Deployment**: Cloud Run Jobs are updated via `gcloud run jobs update`, not `gcloud run deploy`
3. **No Automatic Trigger**: There's NO Cloud Build trigger watching for changes to `jobs/` directory

### When to Deploy Manually:
You need to manually deploy the stitching job when you change:
- ✅ `jobs/base/gcs_client.py` (like the fix we just made)
- ✅ `jobs/video_stitching/main.py`
- ✅ `jobs/video_stitching/Dockerfile`
- ✅ Any dependencies in job's requirements

You do **NOT** need to deploy the job when you change:
- ❌ Flask app code (`app.py`, `api/*`)
- ❌ React frontend (`frontend/reel-maker/`)
- ❌ Static files
- ❌ Main `Dockerfile`

---

## 📊 Deployment Matrix

| Component | Main Branch | Dev Branch | Manual |
|-----------|-------------|------------|--------|
| **Flask App** | ✅ Auto | ✅ Auto | ✅ Available |
| **React Frontend** | ✅ Auto (via Flask) | ✅ Auto (via Flask) | ✅ Available |
| **Static Files** | ✅ Auto (via Flask) | ✅ Auto (via Flask) | ✅ Available |
| **Cloud Run Job** | ❌ Manual Only | ❌ Manual Only | ✅ Only Option |

---

## 🚀 How to Deploy Cloud Run Jobs

### Option 1: Using Existing Script (Recommended)
```bash
cd /Users/sumanurawat/Documents/GitHub/phoenix
gcloud builds submit --config jobs/video_stitching/cloudbuild.yaml --project=phoenix-project-386
```

### Option 2: Async Deployment (Faster)
```bash
gcloud builds submit --config jobs/video_stitching/cloudbuild.yaml --project=phoenix-project-386 --async
```

### What Happens:
1. **Builds Docker image** using `jobs/video_stitching/Dockerfile`
2. **Tags image** with:
   - `gcr.io/phoenix-project-386/reel-stitching-job:latest`
   - `gcr.io/phoenix-project-386/reel-stitching-job:BUILD_ID`
3. **Pushes to Container Registry**
4. **⚠️ BUT**: Doesn't automatically update the job!

### Option 3: Build + Deploy (Complete)
After building, you need to update the job:
```bash
# First build
gcloud builds submit --config jobs/video_stitching/cloudbuild.yaml --project=phoenix-project-386

# Then update the job to use new image
gcloud run jobs update reel-stitching-job \
  --image=gcr.io/phoenix-project-386/reel-stitching-job:latest \
  --region=us-central1 \
  --project=phoenix-project-386
```

---

## 🔄 Setting Up Automated Job Deployment (Optional)

If you want to automate Cloud Run Job deployment too, you can create a trigger:

### Create Trigger for Job Deployment
```bash
gcloud builds triggers create github \
  --name="reel-stitching-job-deploy" \
  --repo-name="phoenix" \
  --repo-owner="sumanurawat" \
  --branch-pattern="^main$" \
  --build-config="jobs/video_stitching/cloudbuild.yaml" \
  --included-files="jobs/**" \
  --project=phoenix-project-386
```

This would:
- ✅ Trigger only when files in `jobs/` directory change
- ✅ Run `jobs/video_stitching/cloudbuild.yaml`
- ✅ Build and push new image
- ⚠️ Still need to add deploy step to cloudbuild.yaml

### Updated cloudbuild.yaml with Deploy Step
```yaml
steps:
  # Build the stitching job image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/reel-stitching-job:latest'
      - '-t'
      - 'gcr.io/$PROJECT_ID/reel-stitching-job:$BUILD_ID'
      - '-f'
      - 'jobs/video_stitching/Dockerfile'
      - '.'
  
  # Push both tags to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/reel-stitching-job:latest']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/reel-stitching-job:$BUILD_ID']

  # 🆕 NEW STEP: Deploy to Cloud Run Jobs
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'jobs'
      - 'update'
      - 'reel-stitching-job'
      - '--image'
      - 'gcr.io/$PROJECT_ID/reel-stitching-job:latest'
      - '--region'
      - 'us-central1'

images:
  - 'gcr.io/$PROJECT_ID/reel-stitching-job:latest'
  - 'gcr.io/$PROJECT_ID/reel-stitching-job:$BUILD_ID'
```

---

## 📝 Current Deployment Status

### ✅ Already Deployed (Latest):

#### Main App (Needs Deployment)
- **Status**: ❌ Not yet deployed with latest changes
- **Last Deploy**: Automatic via main branch
- **Changes Pending**:
  - React bundle with event listener (190.50 kB)
  - Updated App.tsx with stitchJobComplete handler
  - All static files

#### Cloud Run Job
- **Status**: ✅ Deployed with fix (Build: 0a803500-4615-4bfd-88ec-10f65ca6d1ff)
- **Image**: `gcr.io/phoenix-project-386/reel-stitching-job:latest`
- **Changes Included**:
  - Fixed `gcs_client.py` unique filename generation
  - No file overwriting issues

---

## 🎯 Recommended Workflow

### For Main App Changes:
1. Make changes locally
2. Test with `./start_local.sh`
3. Commit and push to `dev` branch → **Auto-deploys to phoenix-dev**
4. Test on dev environment
5. Merge to `main` branch → **Auto-deploys to phoenix (production)**
6. Done! ✅

### For Cloud Run Job Changes:
1. Make changes to files in `jobs/` directory
2. Test locally if possible
3. Commit and push to any branch
4. **Manually deploy**:
   ```bash
   gcloud builds submit --config jobs/video_stitching/cloudbuild.yaml --project=phoenix-project-386
   ```
5. Done! ✅

---

## 💡 Pro Tips

### 1. Check Build Status
```bash
# Recent builds
gcloud builds list --project=phoenix-project-386 --limit=10

# Specific build
gcloud builds describe BUILD_ID --project=phoenix-project-386
```

### 2. Check Cloud Run Services
```bash
# List all services
gcloud run services list --project=phoenix-project-386

# Describe specific service
gcloud run services describe phoenix --region=us-central1 --project=phoenix-project-386
```

### 3. Check Cloud Run Jobs
```bash
# List all jobs
gcloud run jobs list --region=us-central1 --project=phoenix-project-386

# Describe job
gcloud run jobs describe reel-stitching-job --region=us-central1 --project=phoenix-project-386
```

### 4. View Build Triggers
```bash
gcloud builds triggers list --project=phoenix-project-386
```

---

## ⚠️ Important Notes

### Why Jobs Aren't Auto-Deployed:
1. **Stability**: Jobs run critical operations, you want explicit control
2. **Different lifecycle**: Jobs don't serve traffic, they execute tasks
3. **Testing complexity**: Harder to test job changes automatically
4. **Infrequent changes**: Jobs change less often than main app

### Current State:
- ✅ **Cloud Run Job**: Already deployed with gcs_client.py fix
- ⏳ **Main App**: Needs deployment for React bundle changes
- ✅ **Works locally**: All fixes tested and working

### Next Action:
Since main app auto-deploys when you push to main branch:
```bash
git add .
git commit -m "Fix: Video stitching order and auto-refresh UI"
git push origin main
```

This will automatically deploy the main app with all React bundle updates! 🚀

---

## 📚 Summary

| When You Push To... | What Happens | What Doesn't Happen |
|---------------------|--------------|---------------------|
| **`main` branch** | ✅ Flask app rebuilds<br>✅ Static files update<br>✅ React bundle deploys<br>✅ Cloud Run service updates | ❌ Cloud Run Jobs don't update |
| **`dev` branch** | ✅ Flask app rebuilds<br>✅ Static files update<br>✅ React bundle deploys<br>✅ Cloud Run dev service updates | ❌ Cloud Run Jobs don't update |
| **Any branch** | ✅ Code is versioned in GitHub | ❌ No automatic deployments<br>❌ Jobs not affected |

**For Cloud Run Jobs**: Always deploy manually using `gcloud builds submit`

This is actually a **good design** because:
- Main app changes frequently → automated
- Jobs change rarely → manual control
- Prevents accidental job updates
- You explicitly verify job changes work before deploying
