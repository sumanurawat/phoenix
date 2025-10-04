# Cloud Run Jobs Testing Guide

**Version**: 1.0
**Date**: October 3, 2025
**Status**: Ready for Testing

## 📋 Overview

This guide provides comprehensive testing instructions for the Cloud Run Jobs architecture implemented for the Phoenix Reel Maker service. It covers local testing, integration testing, and production validation.

## 🏗️ Test Environment Setup

### Prerequisites

Before testing, ensure you have:

1. **Development Environment**
   ```bash
   # Required tools
   - gcloud CLI (authenticated)
   - Docker
   - curl
   - jq
   - Python 3.11+
   ```

2. **Phoenix Application**
   ```bash
   # Clone and setup
   cd /path/to/phoenix
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Google Cloud Resources**
   ```bash
   # Required GCP services
   - Cloud Run
   - Cloud Tasks
   - Cloud Storage
   - Firestore
   - Cloud Build
   ```

### Environment Configuration

1. **Set up environment variables**
   ```bash
   export GOOGLE_CLOUD_PROJECT="phoenix-project-386"
   export GCP_REGION="us-central1"
   export VIDEO_STORAGE_BUCKET="phoenix-videos"
   ```

2. **Verify `.env` file**
   ```bash
   # Ensure these are set in .env
   VIDEO_STORAGE_BUCKET=phoenix-videos
   GOOGLE_APPLICATION_CREDENTIALS=./firebase-credentials.json
   JOB_TIMEOUT_MINUTES=15
   MAX_RETRY_ATTEMPTS=3
   ```

## 🚀 Deployment and Setup

### Step 1: Initial Setup

```bash
# 1. Set up Cloud Tasks queue and service accounts
./scripts/setup_job_queue.sh

# 2. Build and deploy job containers
./scripts/deploy_jobs.sh

# 3. Start Phoenix application locally
./start_local.sh
```

### Step 2: Verify Deployment

```bash
# Check Cloud Run Jobs
gcloud run jobs list --region=us-central1

# Check Cloud Tasks queue
gcloud tasks queues describe reel-jobs-queue --location=us-central1

# Check service account permissions
gcloud projects get-iam-policy $GOOGLE_CLOUD_PROJECT
```

## 🧪 Testing Scenarios

### Test 1: API Endpoints

**Purpose**: Verify job management API endpoints work correctly

```bash
# Run API-only tests
./scripts/test_job_execution.sh api
```

**Expected Results**:
- ✅ Health check returns 200
- ✅ Statistics endpoint returns data structure
- ✅ Error conditions return appropriate HTTP codes
- ✅ Authentication is enforced

**Verification**:
```bash
# Manual API tests
curl http://localhost:8080/api/jobs/health
curl http://localhost:8080/api/jobs/stats?days=7
```

### Test 2: Job Orchestration

**Purpose**: Test job creation and status tracking without actual execution

```bash
# Create test project first
curl -X POST http://localhost:8080/api/reel/projects \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Stitching Project"}'

# Trigger stitching job (will fail gracefully without real clips)
curl -X POST http://localhost:8080/api/jobs/trigger/stitching \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test_project_123",
    "clip_paths": ["gs://phoenix-videos/test1.mp4", "gs://phoenix-videos/test2.mp4"],
    "output_path": "gs://phoenix-videos/test_output.mp4"
  }'
```

**Expected Results**:
- ✅ Job ID is returned
- ✅ Job status can be queried
- ✅ Job appears in Cloud Tasks queue
- ✅ Proper error handling for missing files

### Test 3: End-to-End Stitching (with Test Files)

**Purpose**: Complete video stitching workflow with actual video files

#### 3a. Prepare Test Video Files

```bash
# Create test video files (if you don't have real clips)
# Option 1: Use ffmpeg to create test clips
ffmpeg -f lavfi -i testsrc=duration=5:size=1080x1920:rate=30 \
  -c:v libx264 -t 5 test_clip_1.mp4

ffmpeg -f lavfi -i testsrc=duration=5:size=1080x1920:rate=30 \
  -c:v libx264 -t 5 test_clip_2.mp4

# Option 2: Use existing clips from your Reel Maker projects
# Upload to test directory in GCS
gsutil cp test_clip_*.mp4 gs://phoenix-videos/reel-maker/test/
```

#### 3b. Run End-to-End Test

```bash
# Run full stitching test
./scripts/test_job_execution.sh stitching
```

**Expected Results**:
- ✅ Job starts successfully
- ✅ Progress updates are received
- ✅ Files are downloaded from GCS
- ✅ FFmpeg stitching completes
- ✅ Output is uploaded to GCS
- ✅ Project status is updated in Firestore

### Test 4: Direct Cloud Run Job Execution

**Purpose**: Test Cloud Run Job container directly

```bash
# Test Cloud Run Job execution directly
./scripts/test_job_execution.sh direct
```

**Expected Results**:
- ✅ Cloud Run Job starts
- ✅ Job logs are visible
- ✅ Job completes or fails gracefully
- ✅ Proper resource cleanup

**Monitor Execution**:
```bash
# List executions
gcloud run jobs executions list --region=us-central1

# View logs
gcloud run jobs executions logs <EXECUTION_NAME> --region=us-central1

# Describe execution
gcloud run jobs executions describe <EXECUTION_NAME> --region=us-central1
```

### Test 5: Error Conditions and Recovery

**Purpose**: Verify fault tolerance and error handling

#### 5a. Test Insufficient Resources

```bash
# Test with only one clip (should fail)
curl -X POST http://localhost:8080/api/jobs/trigger/stitching \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test_project",
    "clip_paths": ["gs://phoenix-videos/single.mp4"],
    "output_path": "gs://phoenix-videos/output.mp4"
  }'
```

**Expected**: HTTP 400 with "INSUFFICIENT_CLIPS" error

#### 5b. Test Missing Files

```bash
# Test with non-existent files
curl -X POST http://localhost:8080/api/jobs/trigger/stitching \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test_project",
    "clip_paths": ["gs://phoenix-videos/missing1.mp4", "gs://phoenix-videos/missing2.mp4"],
    "output_path": "gs://phoenix-videos/output.mp4"
  }'
```

**Expected**: Job starts but fails during download phase

#### 5c. Test Job Cancellation

```bash
# Start a job
job_response=$(curl -X POST http://localhost:8080/api/jobs/trigger/stitching \
  -H "Content-Type: application/json" \
  -d '{"project_id": "test", "clip_paths": ["gs://bucket/1.mp4", "gs://bucket/2.mp4"], "output_path": "gs://bucket/out.mp4"}')

job_id=$(echo "$job_response" | jq -r '.job.job_id')

# Cancel the job
curl -X POST http://localhost:8080/api/jobs/$job_id/cancel
```

**Expected**: Job status changes to "cancelled"

### Test 6: Performance and Scalability

**Purpose**: Test system under load

#### 6a. Concurrent Job Limit

```bash
# Create multiple jobs for same project (should prevent duplicates)
for i in {1..5}; do
  curl -X POST http://localhost:8080/api/jobs/trigger/stitching \
    -H "Content-Type: application/json" \
    -d '{
      "project_id": "same_project",
      "clip_paths": ["gs://phoenix-videos/1.mp4", "gs://phoenix-videos/2.mp4"],
      "output_path": "gs://phoenix-videos/out_'$i'.mp4"
    }' &
done
wait
```

**Expected**: Only one job should start, others should return "JOB_ALREADY_RUNNING"

#### 6b. Memory Usage Test

```bash
# Test with larger files (if available)
curl -X POST http://localhost:8080/api/jobs/trigger/stitching \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "memory_test",
    "clip_paths": [
      "gs://phoenix-videos/large_clip_1.mp4",
      "gs://phoenix-videos/large_clip_2.mp4",
      "gs://phoenix-videos/large_clip_3.mp4"
    ],
    "output_path": "gs://phoenix-videos/large_output.mp4"
  }'
```

**Monitor**: Check job logs for memory usage patterns

## 🔍 Monitoring and Debugging

### Log Analysis

```bash
# View application logs
tail -f logs/app.log

# View Cloud Run Job logs
gcloud logging read 'resource.type="cloud_run_job"' --limit=50

# View Cloud Tasks logs
gcloud logging read 'resource.type="cloud_tasks_queue"' --limit=50
```

### Common Log Patterns

**Successful Job**:
```
INFO - Starting job job_abc123
INFO - Validated 3 input files
INFO - Downloaded 3 clips (45.2 MB)
INFO - Stitching complete (8.3s)
INFO - Uploaded result (12.1 MB)
INFO - Job completed successfully
```

**Failed Job**:
```
ERROR - Failed to download clip: gs://bucket/missing.mp4
ERROR - Job failed: File not found
```

### Metrics to Monitor

1. **Job Success Rate**
   ```bash
   # Query for job completion status
   gcloud logging read 'jsonPayload.event_type="job_metrics"' --limit=20
   ```

2. **Job Duration**
   ```bash
   # Look for duration_seconds in job metrics
   gcloud logging read 'jsonPayload.metrics.duration_seconds>300' --limit=10
   ```

3. **Memory Usage**
   ```bash
   # Check for memory-related issues
   gcloud logging read 'textPayload:memory OR jsonPayload.peak_memory_mb' --limit=10
   ```

### Resource Monitoring

```bash
# Check Cloud Run Job resource usage
gcloud run jobs executions describe <EXECUTION_NAME> --region=us-central1

# Check Cloud Tasks queue status
gcloud tasks queues describe reel-jobs-queue --location=us-central1

# Check storage usage
gsutil du -s gs://phoenix-videos/reel-maker/
```

## 🛠️ Troubleshooting Guide

### Issue: Job Never Starts

**Symptoms**: Job status remains "queued" indefinitely

**Debug Steps**:
1. Check Cloud Tasks queue
   ```bash
   gcloud tasks list --queue=reel-jobs-queue --location=us-central1
   ```

2. Check service account permissions
   ```bash
   gcloud projects get-iam-policy $GOOGLE_CLOUD_PROJECT
   ```

3. Check job image availability
   ```bash
   gcloud container images list --repository=gcr.io/$GOOGLE_CLOUD_PROJECT
   ```

**Common Fixes**:
- Re-run `./scripts/setup_job_queue.sh`
- Rebuild and redeploy jobs: `./scripts/deploy_jobs.sh`

### Issue: Job Fails During Download

**Symptoms**: Job starts but fails with "Download failed" error

**Debug Steps**:
1. Verify file exists
   ```bash
   gsutil ls gs://phoenix-videos/path/to/file.mp4
   ```

2. Check service account storage permissions
   ```bash
   gsutil iam get gs://phoenix-videos
   ```

3. Test manual download
   ```bash
   gsutil cp gs://phoenix-videos/test.mp4 /tmp/
   ```

**Common Fixes**:
- Grant storage.objectAdmin role to job service account
- Verify bucket name in configuration

### Issue: FFmpeg Stitching Fails

**Symptoms**: Job fails during stitching phase

**Debug Steps**:
1. Check job logs for FFmpeg errors
   ```bash
   gcloud run jobs executions logs <EXECUTION_NAME> --region=us-central1
   ```

2. Test FFmpeg command locally
   ```bash
   # Download clips and test locally
   ffmpeg -f concat -safe 0 -i clip_list.txt -c copy output.mp4
   ```

**Common Fixes**:
- Ensure input videos have compatible formats
- Check for corrupted video files
- Increase job memory allocation if needed

### Issue: High Memory Usage

**Symptoms**: Job killed with "out of memory" error

**Debug Steps**:
1. Check memory allocation
   ```bash
   gcloud run jobs describe reel-stitching-job --region=us-central1
   ```

2. Monitor memory usage in logs
   ```bash
   gcloud logging read 'jsonPayload.peak_memory_mb>3500' --limit=10
   ```

**Fixes**:
- Increase memory allocation in job configuration
- Optimize video processing pipeline
- Implement video transcoding before stitching

## ✅ Test Checklist

### Pre-deployment Tests
- [ ] All required APIs are enabled
- [ ] Service accounts have correct permissions
- [ ] Cloud Tasks queue is created
- [ ] Job containers build successfully
- [ ] Environment variables are configured

### API Tests
- [ ] Health check endpoints respond correctly
- [ ] Authentication is enforced
- [ ] Error conditions return appropriate codes
- [ ] Job status API works
- [ ] Job cancellation works

### Integration Tests
- [ ] Job orchestrator creates jobs correctly
- [ ] Cloud Tasks delivers job payloads
- [ ] Job status updates are persisted
- [ ] Project status is updated after completion

### End-to-End Tests
- [ ] Complete stitching workflow succeeds
- [ ] Files are downloaded from GCS correctly
- [ ] FFmpeg stitching produces valid output
- [ ] Result is uploaded to correct location
- [ ] Cleanup removes temporary files

### Performance Tests
- [ ] Jobs complete within expected timeframe
- [ ] Memory usage stays within limits
- [ ] Concurrent job prevention works
- [ ] System handles multiple projects

### Error Handling Tests
- [ ] Missing files are handled gracefully
- [ ] Invalid input produces helpful errors
- [ ] Job timeouts work correctly
- [ ] Recovery from partial failures

## 📊 Success Criteria

### Performance Metrics
- **Job Success Rate**: >95%
- **Average Stitching Time**: <10 minutes for 5 clips
- **Memory Usage**: <3.5GB peak for typical workloads
- **Cost per Job**: <$0.02

### Reliability Metrics
- **Recovery Rate**: 100% for transient failures
- **Data Consistency**: 100% (no orphaned files)
- **Error Reporting**: Clear, actionable error messages

### User Experience
- **Time to Start**: <30 seconds from trigger to start
- **Progress Updates**: Every 30 seconds during processing
- **Status Accuracy**: Real-time status reflects actual job state

## 🔄 Continuous Testing

### Automated Testing

1. **Set up CI/CD pipeline**
   ```yaml
   # .github/workflows/test-jobs.yml
   name: Test Cloud Run Jobs
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - name: Setup Cloud SDK
           uses: google-github-actions/setup-gcloud@v0
         - name: Run job tests
           run: ./scripts/test_job_execution.sh api
   ```

2. **Regular integration tests**
   ```bash
   # Add to cron job
   0 2 * * * cd /path/to/phoenix && ./scripts/test_job_execution.sh all
   ```

### Monitoring Alerts

Set up alerts for:
- Job failure rate >5% in 1 hour
- Job duration >15 minutes
- Memory usage >90%
- Queue depth >10 jobs

---

**Next Steps**: After successful testing, the Cloud Run Jobs system is ready for production use. Monitor the metrics and adjust resource allocations based on real usage patterns.