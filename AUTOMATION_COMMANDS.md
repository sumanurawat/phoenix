# Automated Job Deployment - Quick Commands

## 🚀 One-Time Setup

### Create Cloud Build Trigger for Video Stitching Job
```bash
gcloud builds triggers create github \
  --name="reel-stitching-job-deploy" \
  --description="Auto-deploy video stitching job on code changes" \
  --repo-name="phoenix" \
  --repo-owner="sumanurawat" \
  --branch-pattern="^main$" \
  --build-config="jobs/video_stitching/cloudbuild.yaml" \
  --included-files="jobs/video_stitching/**" \
  --region=us-central1 \
  --project=phoenix-project-386
```

## 📋 Daily Commands

### Check Recent Builds
```bash
gcloud builds list --limit=5
```

### View Build Logs
```bash
gcloud builds log $(gcloud builds list --limit=1 --format="value(id)")
```

### Check Job Status
```bash
gcloud run jobs describe reel-stitching-job --region=us-central1 --format="value(metadata.name,status.latestCreatedExecution.name)"
```

### List All Triggers
```bash
gcloud builds triggers list --region=us-central1
```

## 🔧 Troubleshooting

### View Trigger Details
```bash
gcloud builds triggers describe reel-stitching-job-deploy --region=us-central1
```

### Manually Trigger Build (Force Deploy)
```bash
gcloud builds submit --config=jobs/video_stitching/cloudbuild.yaml --project=phoenix-project-386
```

### View Job Execution Logs
```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=reel-stitching-job" --limit=20 --format=json
```

### Check Failed Builds
```bash
gcloud builds list --filter="status=FAILURE" --limit=5
```

## ⚙️ Trigger Management

### Disable Trigger (Temporary)
```bash
gcloud builds triggers update reel-stitching-job-deploy --disabled --region=us-central1
```

### Re-enable Trigger
```bash
gcloud builds triggers update reel-stitching-job-deploy --no-disabled --region=us-central1
```

### Delete Trigger
```bash
gcloud builds triggers delete reel-stitching-job-deploy --region=us-central1
```

## 🔄 Rollback

### Deploy Previous Image Version
```bash
# List available images
gcloud container images list-tags gcr.io/phoenix-project-386/reel-stitching-job

# Deploy specific version
gcloud run jobs update reel-stitching-job \
  --image=gcr.io/phoenix-project-386/reel-stitching-job:[BUILD_ID] \
  --region=us-central1
```

## 📊 Monitoring

### Check Build Success Rate
```bash
gcloud builds list --filter="buildTriggerId:reel-stitching-job-deploy" --limit=20 --format="table(id,status,createTime)"
```

### View Build Duration
```bash
gcloud builds list --limit=5 --format="table(id,status,duration)"
```

## 🆕 Adding New Jobs

### Template for New Job Trigger
```bash
gcloud builds triggers create github \
  --name="[JOB-NAME]-deploy" \
  --description="Auto-deploy [job description]" \
  --repo-name="phoenix" \
  --repo-owner="sumanurawat" \
  --branch-pattern="^main$" \
  --build-config="jobs/[job-directory]/cloudbuild.yaml" \
  --included-files="jobs/[job-directory]/**" \
  --region=us-central1 \
  --project=phoenix-project-386
```

### Create New Cloud Run Job (First Time)
```bash
gcloud run jobs create [job-name] \
  --image=gcr.io/phoenix-project-386/[job-name]:latest \
  --region=us-central1 \
  --cpu=2 \
  --memory=4Gi \
  --timeout=600 \
  --max-retries=2
```

## 🌐 Cloud Console URLs

### View Builds Dashboard
```
https://console.cloud.google.com/cloud-build/builds?project=phoenix-project-386
```

### View Triggers Dashboard
```
https://console.cloud.google.com/cloud-build/triggers?project=phoenix-project-386
```

### View Cloud Run Jobs
```
https://console.cloud.google.com/run/jobs?project=phoenix-project-386
```

### View Container Registry
```
https://console.cloud.google.com/gcr/images/phoenix-project-386?project=phoenix-project-386
```

## 💡 Pro Tips

- **After code changes**: Just `git push` - deployment happens automatically!
- **Check build status**: `gcloud builds list --limit=1` shows most recent
- **Build duration**: Typically 3-5 minutes for video stitching job
- **Cost**: ~$0.012 per build (negligible at current scale)
- **Included files filter**: Trigger only activates for changes in `jobs/video_stitching/`

## 📝 Quick Notes

- **Trigger name**: `reel-stitching-job-deploy`
- **Job name**: `reel-stitching-job`
- **Image**: `gcr.io/phoenix-project-386/reel-stitching-job:latest`
- **Region**: `us-central1`
- **Branch**: `main` only
- **Config file**: `jobs/video_stitching/cloudbuild.yaml`

---

**For full documentation**, see: `AUTOMATED_JOB_DEPLOYMENT.md`
