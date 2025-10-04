# Cloud Run Jobs Architecture - Video Processing Microservices

**Version**: 1.0
**Date**: October 3, 2025
**Status**: Design Phase

## 📋 Executive Summary

This document outlines the architecture for migrating video processing operations (generation and stitching) from the main Phoenix application to dedicated Cloud Run Jobs. This microservices approach provides better resource isolation, cost optimization, fault tolerance, and scalability.

## 🎯 Objectives

### Primary Goals
- **Cost Optimization**: Pay only for processing time, auto-shutdown after completion
- **Resource Isolation**: Dedicated memory/CPU for heavy video operations
- **Fault Tolerance**: Checkpoint-based recovery, automatic retries
- **Scalability**: Independent scaling of video processing workloads
- **Maintainability**: Clear separation of concerns, reusable job framework

### Success Metrics
- **Cost Reduction**: 70% reduction in compute costs vs always-on instances
- **Reliability**: 99.5% success rate with automatic recovery
- **Performance**: 50% faster stitching with dedicated resources
- **TTL Compliance**: All jobs complete within 15 minutes or auto-terminate

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Phoenix App   │    │  Cloud Tasks    │    │ Cloud Run Jobs  │
│   (Trigger)     │───▶│  (Orchestrate)  │───▶│  (Process)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Firestore     │    │   Cloud Logging │    │   Cloud Storage │
│   (State)       │    │   (Monitoring)  │    │   (Videos)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Components

#### 1. Job Orchestrator (Phoenix App)
- **Responsibility**: Job creation, triggering, status monitoring
- **Location**: `services/job_orchestrator.py`
- **Triggers**: UI actions (Generate Clips, Stitch Clips)

#### 2. Cloud Tasks Queue
- **Responsibility**: Reliable job delivery, retry logic
- **Configuration**: 3 retries, exponential backoff
- **TTL**: 1 hour maximum

#### 3. Cloud Run Jobs
- **Responsibility**: Heavy video processing workloads
- **Types**: Video Generation, Video Stitching
- **Resource Allocation**: 2-8 GiB RAM, 2-4 vCPUs

#### 4. State Management (Firestore)
- **Collections**: `reel_jobs`, `reel_job_checkpoints`
- **Purpose**: Progress tracking, failure recovery

## 📁 Project Structure

```
phoenix/
├── jobs/                           # 🆕 Cloud Run Jobs directory
│   ├── __init__.py
│   ├── base/                       # Shared job framework
│   │   ├── __init__.py
│   │   ├── job_runner.py          # Base job class
│   │   ├── checkpoint_manager.py   # State persistence
│   │   ├── gcs_client.py          # Storage operations
│   │   └── monitoring.py          # Logging & metrics
│   ├── video_stitching/           # Video stitching job
│   │   ├── __init__.py
│   │   ├── main.py               # Entry point
│   │   ├── stitcher.py           # FFmpeg operations
│   │   ├── Dockerfile            # Job-specific container
│   │   └── requirements.txt      # Job dependencies
│   ├── video_generation/          # Future: Video generation job
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── generator.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── shared/                    # Shared utilities
│       ├── __init__.py
│       ├── config.py             # Environment configuration
│       ├── schemas.py            # Job payload schemas
│       └── utils.py              # Common functions
├── services/
│   ├── job_orchestrator.py       # 🆕 Job management service
│   ├── reel_generation_service.py # Modified to use jobs
│   └── video_stitching_service.py # Modified to use jobs
├── api/
│   └── job_routes.py             # 🆕 Job status APIs
├── config/
│   └── cloud_run_jobs.yaml      # 🆕 Job configurations
└── scripts/
    ├── deploy_jobs.sh            # 🆕 Job deployment script
    └── setup_job_queue.sh       # 🆕 Cloud Tasks setup
```

## 🔧 Detailed Design

### Job Types

#### 1. Video Stitching Job (`reel-stitching-job`)

**Purpose**: Combine multiple video clips into a single reel
**Trigger**: After clip generation completes OR manual stitch request
**Memory**: 4 GiB (handles 15+ videos of 50MB each)
**Timeout**: 15 minutes
**Cost**: ~$0.10 per execution

**Input Schema**:
```json
{
  "jobId": "job_abc123",
  "projectId": "proj_xyz789",
  "userId": "user_456",
  "clipPaths": ["gs://bucket/clip1.mp4", "gs://bucket/clip2.mp4"],
  "outputPath": "gs://bucket/stitched/reel_final.mp4",
  "orientation": "portrait",
  "compression": "optimized",
  "retryAttempt": 0
}
```

**Processing Steps**:
1. **Initialize** (30s): Download clips, validate files
2. **Process** (5-10min): FFmpeg stitching with progress tracking
3. **Upload** (1-2min): Upload final video to GCS
4. **Cleanup** (10s): Remove temporary files, update Firestore
5. **Shutdown**: Job terminates automatically

#### 2. Video Generation Job (Future)

**Purpose**: Generate multiple clips in parallel using Veo API
**Memory**: 2 GiB
**Timeout**: 30 minutes

### API Interfaces

#### Job Orchestrator Service

```python
class JobOrchestrator:
    async def trigger_stitching_job(
        self,
        project_id: str,
        user_id: str,
        force_restart: bool = False
    ) -> JobExecution:
        """
        Triggers video stitching job with fault tolerance.

        Args:
            project_id: Reel project identifier
            user_id: User identifier for authorization
            force_restart: Skip existing job check

        Returns:
            JobExecution with job_id and status

        Raises:
            JobAlreadyRunningError: If job is already processing
            InsufficientClipsError: If < 2 clips available
            QuotaExceededError: If user exceeds job limits
        """

    async def get_job_status(self, job_id: str) -> JobStatus:
        """Get real-time job status and progress."""

    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel running job (if possible)."""
```

#### Job Status API Endpoints

```yaml
GET /api/jobs/{job_id}/status:
  description: Get job status and progress
  response:
    jobId: string
    status: "queued" | "running" | "completed" | "failed" | "cancelled"
    progress: number (0-100)
    startedAt: timestamp
    estimatedCompletion: timestamp
    error: string (if failed)

POST /api/jobs/{job_id}/cancel:
  description: Cancel running job
  response:
    success: boolean
    message: string

GET /api/projects/{project_id}/jobs:
  description: List all jobs for a project
  response:
    jobs: JobStatus[]
```

### State Management & Checkpoints

#### Firestore Collections

**1. `reel_jobs` Collection**
```json
{
  "jobId": "job_abc123",
  "type": "video_stitching",
  "projectId": "proj_xyz789",
  "userId": "user_456",
  "status": "running",
  "progress": 65,
  "payload": {...},
  "createdAt": "2025-10-03T10:00:00Z",
  "startedAt": "2025-10-03T10:01:00Z",
  "completedAt": null,
  "error": null,
  "retryCount": 0,
  "checkpoints": ["initialized", "clips_downloaded", "stitching_started"]
}
```

**2. `reel_job_checkpoints` Collection**
```json
{
  "jobId": "job_abc123",
  "checkpoint": "clips_downloaded",
  "timestamp": "2025-10-03T10:02:30Z",
  "data": {
    "downloadedFiles": ["clip1.mp4", "clip2.mp4"],
    "totalSizeMB": 150,
    "tempDir": "/tmp/job_abc123"
  }
}
```

#### Checkpoint Strategy

1. **Initialize**: Job started, temporary directory created
2. **Clips Downloaded**: All input files downloaded and validated
3. **Stitching Started**: FFmpeg process initiated
4. **Progress Updates**: Every 30 seconds during processing
5. **Upload Started**: Final video upload initiated
6. **Completed**: Job finished successfully

**Recovery Logic**:
- Job restarts from last successful checkpoint
- Downloads only missing files
- Resumes FFmpeg from last progress point (if possible)
- Maximum 3 retry attempts with exponential backoff

### Fault Tolerance & Corner Cases

#### Error Handling Matrix

| Error Type | Detection | Recovery Action | User Impact |
|------------|-----------|-----------------|-------------|
| **Network Timeout** | API timeout | Retry with exponential backoff | Transparent |
| **GCS Permission Error** | 403/401 response | Fail fast, notify user | Error message |
| **Insufficient Memory** | OOM kill signal | Retry with higher memory | Transparent |
| **Corrupt Video File** | FFmpeg error | Skip file, continue with others | Warning notification |
| **Disk Space Full** | Write error | Cleanup temp files, retry | Transparent |
| **Job Timeout** | 15min limit | Save progress, schedule retry | Status notification |
| **Quota Exceeded** | API error | Queue for later, notify user | Rate limit message |

#### Corner Cases

**1. Concurrent Job Prevention**
```python
async def ensure_single_job(project_id: str, job_type: str):
    """Prevent multiple jobs of same type for same project."""
    existing = await get_active_jobs(project_id, job_type)
    if existing:
        if existing.status in ["queued", "running"]:
            raise JobAlreadyRunningError(f"Job {existing.job_id} already running")
        elif existing.status == "failed" and existing.retry_count < 3:
            # Resume failed job
            return await retry_job(existing.job_id)
```

**2. Resource Cleanup**
```python
class JobRunner:
    async def __aenter__(self):
        self.temp_dir = f"/tmp/job_{self.job_id}"
        os.makedirs(self.temp_dir, exist_ok=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Always cleanup, even on failure
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        await self.update_job_status("cleaning_up")
```

**3. Graceful Shutdown**
```python
def handle_sigterm(signum, frame):
    """Handle Cloud Run shutdown signal."""
    logger.info("Received SIGTERM, initiating graceful shutdown...")
    # Save current progress to checkpoint
    checkpoint_manager.save_progress()
    # Mark job as interrupted for retry
    job_manager.mark_interrupted()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
```

### Memory & Resource Requirements

#### Memory Analysis

**Video Stitching Job**:
- **Base System**: 200 MB
- **FFmpeg**: 100 MB
- **Input Videos**: 50 MB × 15 clips = 750 MB
- **Processing Buffer**: 1024 MB (FFmpeg working memory)
- **Output Buffer**: 200 MB
- **Safety Margin**: 500 MB
- **Total Required**: 2.8 GB → **Allocated: 4 GB**

**Video Generation Job** (Future):
- **Base System**: 200 MB
- **AI Model Cache**: 512 MB
- **Network Buffers**: 256 MB
- **Safety Margin**: 256 MB
- **Total Required**: 1.2 GB → **Allocated: 2 GB**

#### CPU Requirements
- **Video Stitching**: 2 vCPUs (FFmpeg can utilize multiple cores)
- **Video Generation**: 1 vCPU (I/O bound, waiting for API responses)

#### Cost Estimation

**Per Job Execution**:
```
Stitching Job:
- Memory: 4 GB × $0.003125/GB/hour × 0.15 hours = $0.00188
- CPU: 2 vCPU × $0.024/vCPU/hour × 0.15 hours = $0.0072
- Total per job: ~$0.009 (less than 1 cent)

Monthly (100 projects × 3 iterations):
- Total executions: 300 jobs
- Monthly cost: 300 × $0.009 = $2.70
```

### Security & Permissions

#### IAM Roles Required

**Cloud Run Job Service Account**:
```yaml
roles:
  - roles/storage.objectAdmin      # Read/write GCS videos
  - roles/datastore.user          # Read/write Firestore state
  - roles/logging.logWriter       # Write logs
  - roles/monitoring.metricWriter # Write metrics
  - roles/cloudtasks.enqueuer     # Trigger follow-up jobs

custom_permissions:
  - cloudsql.instances.connect    # If using Cloud SQL (future)
```

**Environment Variables**:
```bash
# Job configuration
GOOGLE_CLOUD_PROJECT=phoenix-project-386
JOB_TIMEOUT_MINUTES=15
MAX_RETRY_ATTEMPTS=3
TEMP_DIR=/tmp

# Storage
VIDEO_STORAGE_BUCKET=phoenix-videos
CHECKPOINT_COLLECTION=reel_job_checkpoints

# Monitoring
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### Monitoring & Observability

#### Metrics Collection

**Custom Metrics**:
```yaml
job_duration_seconds:
  description: "Time taken to complete job"
  labels: [job_type, status, retry_attempt]

job_memory_usage_mb:
  description: "Peak memory usage during job"
  labels: [job_type]

job_success_rate:
  description: "Percentage of successful jobs"
  labels: [job_type, error_type]

video_processing_rate_mbps:
  description: "Video processing throughput"
  labels: [job_type, video_count]
```

**Alerting Rules**:
- Job failure rate > 5% in 1 hour
- Job duration > 10 minutes
- Memory usage > 90% of allocated
- Queue depth > 10 jobs

#### Logging Strategy

```python
import structlog

logger = structlog.get_logger()

# Structured logging for correlation
logger.info(
    "job_started",
    job_id=job_id,
    project_id=project_id,
    job_type="video_stitching",
    input_files=len(clip_paths),
    estimated_duration_minutes=5
)
```

### Deployment Strategy

#### Docker Configuration

**Base Job Image** (`jobs/base/Dockerfile`):
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy shared utilities
COPY jobs/base/ /app/base/
COPY jobs/shared/ /app/shared/

WORKDIR /app
CMD ["python", "main.py"]
```

**Job-Specific Image** (`jobs/video_stitching/Dockerfile`):
```dockerfile
FROM phoenix-job-base:latest

# Copy job-specific code
COPY jobs/video_stitching/ /app/

# Job configuration
ENV JOB_TYPE=video_stitching
ENV MAX_MEMORY_GB=4
ENV TIMEOUT_MINUTES=15

CMD ["python", "main.py"]
```

#### Cloud Run Job Configuration

```yaml
# config/cloud_run_jobs.yaml
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: reel-stitching-job
  namespace: phoenix-project-386
spec:
  template:
    spec:
      template:
        spec:
          serviceAccountName: reel-jobs-sa
          timeoutSeconds: 900  # 15 minutes
          containers:
          - name: stitcher
            image: gcr.io/phoenix-project-386/reel-stitching-job
            resources:
              limits:
                memory: "4Gi"
                cpu: "2000m"
              requests:
                memory: "2Gi"
                cpu: "1000m"
            env:
            - name: GOOGLE_CLOUD_PROJECT
              value: phoenix-project-386
            - name: VIDEO_STORAGE_BUCKET
              value: phoenix-videos
          restartPolicy: Never
          maxRetries: 3
```

#### Deployment Scripts

**`scripts/deploy_jobs.sh`**:
```bash
#!/bin/bash
set -e

echo "🚀 Deploying Cloud Run Jobs..."

# Build base image
docker build -t gcr.io/$PROJECT_ID/phoenix-job-base:latest jobs/base/
docker push gcr.io/$PROJECT_ID/phoenix-job-base:latest

# Build and deploy each job
for job_dir in jobs/*/; do
    if [[ -f "$job_dir/Dockerfile" ]]; then
        job_name=$(basename "$job_dir")
        echo "📦 Building $job_name..."

        docker build -t gcr.io/$PROJECT_ID/reel-$job_name-job:latest "$job_dir"
        docker push gcr.io/$PROJECT_ID/reel-$job_name-job:latest

        echo "☁️ Deploying to Cloud Run..."
        gcloud run jobs replace config/cloud_run_jobs/$job_name.yaml \
          --region=us-central1
    fi
done

echo "✅ All jobs deployed successfully!"
```

### Integration Points

#### Triggering from Phoenix App

**Modified `reel_generation_service.py`**:
```python
class ReelGenerationService:
    async def start_stitching(self, project_id: str, user_id: str):
        """Trigger stitching job instead of inline processing."""

        # Validate prerequisites
        project = await reel_project_service.get_project(project_id)
        if len(project.clip_filenames) < 2:
            raise InsufficientClipsError("Need at least 2 clips")

        if project.stitched_filename:
            logger.info("Stitched video already exists", project_id=project_id)
            return

        # Create job payload
        payload = StitchingJobPayload(
            project_id=project_id,
            user_id=user_id,
            clip_paths=[f"gs://{bucket}/{clip}" for clip in project.clip_filenames],
            output_path=f"gs://{bucket}/stitched/{project_id}_final.mp4",
            orientation=project.orientation,
            compression=project.compression
        )

        # Trigger via Cloud Tasks
        job_execution = await job_orchestrator.trigger_stitching_job(payload)

        # Update project status
        await reel_project_service.update_status(project_id, "stitching")

        return job_execution
```

**Modified UI Flow**:
```typescript
// In ActionToolbar.tsx
const handleStitchClips = async () => {
  try {
    const { jobId } = await stitchProject(activeProjectId);

    // Start polling for job status
    pollJobStatus(jobId, (status) => {
      if (status.status === 'completed') {
        // Refresh project to show stitched video
        refetchProject();
      } else if (status.status === 'failed') {
        setErrorMessage(status.error);
      }

      setStitchProgress(status.progress);
    });

  } catch (error) {
    setErrorMessage(error.message);
  }
};
```

### Future Extensibility

#### Job Framework

The base job framework supports any video processing job:

```python
from jobs.base import JobRunner

class CustomVideoJob(JobRunner):
    async def validate_input(self, payload: dict) -> bool:
        """Validate job input parameters."""

    async def process(self, payload: dict) -> dict:
        """Main job processing logic."""

    async def cleanup(self) -> None:
        """Job-specific cleanup."""
```

#### Orchestration (Phase 3)

**Cloud Workflows Integration**:
```yaml
# workflows/reel_generation_pipeline.yaml
main:
  steps:
  - generate_clips:
      call: http.post
      args:
        url: https://reel-generation-job-url
        body: ${input.prompts}
      result: generation_result

  - wait_for_generation:
      call: sys.sleep
      args:
        seconds: 30

  - stitch_videos:
      call: http.post
      args:
        url: https://reel-stitching-job-url
        body: ${generation_result.clips}
      result: final_result

  - return_result:
      return: ${final_result}
```

### Risk Assessment

#### High Risk Items
1. **Cost Overrun**: Malicious users triggering many jobs
   - **Mitigation**: Rate limiting, user quotas, job monitoring

2. **Job Stuck**: FFmpeg hangs indefinitely
   - **Mitigation**: Hard timeout at 15 minutes, progress monitoring

3. **Data Loss**: Temporary files lost during processing
   - **Mitigation**: Checkpoint system, retry logic

#### Medium Risk Items
1. **Memory Spikes**: Large videos causing OOM
   - **Mitigation**: Input validation, 4GB memory allocation

2. **Network Failures**: GCS connectivity issues
   - **Mitigation**: Exponential backoff, retry logic

### Success Criteria & KPIs

#### Performance Metrics
- **Job Success Rate**: > 99%
- **Average Job Duration**: < 8 minutes
- **Cost per Job**: < $0.01
- **Time to First Frame**: < 30 seconds

#### Business Metrics
- **User Satisfaction**: Faster stitching experience
- **Cost Reduction**: 70% vs current monolithic approach
- **System Reliability**: 99.9% uptime
- **Developer Velocity**: Easier to add new job types

## 🚀 Implementation Plan

### Phase 1: Foundation (Week 1)
1. ✅ Create job folder structure
2. ✅ Implement base job framework
3. ✅ Set up Cloud Tasks queue
4. ✅ Create job orchestrator service

### Phase 2: Stitching Job (Week 2)
1. ✅ Implement video stitching job
2. ✅ Add checkpoint system
3. ✅ Create deployment scripts
4. ✅ Integration testing

### Phase 3: Production (Week 3)
1. ✅ Deploy to staging environment
2. ✅ Load testing and optimization
3. ✅ Production deployment
4. ✅ Monitoring setup

### Phase 4: Enhancement (Week 4)
1. ✅ Add video generation job
2. ✅ Implement advanced monitoring
3. ✅ Performance optimization
4. ✅ Documentation and training

---

**Document Approval**:
- [ ] Technical Review
- [ ] Security Review
- [ ] Cost Review
- [ ] Business Approval

**Next Steps**: Upon approval, begin Phase 1 implementation with job framework and folder structure setup.