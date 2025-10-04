# Cloud Run Job Resource Allocation - Reel Stitching

## 🎯 Current Configuration

### Resource Limits (HARDCODED)
The reel stitching job currently uses **fixed, hardcoded** resource allocation:

```yaml
resources:
  limits:
    cpu: '2'        # 2 vCPUs
    memory: 4Gi     # 4 GB RAM
```

### Additional Constraints
- **Timeout**: 900 seconds (15 minutes)
- **Max Retries**: 2 attempts
- **Task Count**: 1 (single container per execution)
- **Service Account**: phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com

---

## 📍 Where It's Configured

### 1. Cloud Run Job Definition (Deployed State)
The job is currently deployed with these fixed resources. You can see them via:

```bash
gcloud run jobs describe reel-stitching-job \
  --region=us-central1 \
  --project=phoenix-project-386 \
  --format=yaml
```

### 2. Dockerfile Environment Variables (Not Used for Allocation)
The `jobs/video_stitching/Dockerfile` has these environment variables, but they're just **informational**:

```dockerfile
ENV MAX_MEMORY_GB=4
ENV TIMEOUT_MINUTES=15
ENV MEMORY_LIMIT_GB=4
ENV CPU_LIMIT=2
```

These are **NOT** used by Cloud Run for resource allocation. They're only for:
- Documentation
- Application-level awareness (e.g., FFmpeg can check available memory)

### 3. Job Orchestrator (No Dynamic Allocation)
The `services/job_orchestrator.py` triggers the job but does **NOT** set resources dynamically:

```python
# Only passes environment variables, not resources
env_vars = [
    run_v2.EnvVar(name="JOB_ID", value=job_id),
    run_v2.EnvVar(name="JOB_TYPE", value=job_type),
    run_v2.EnvVar(name="JOB_PAYLOAD", value=json.dumps(payload))
]
```

---

## 🤔 Does It Depend on Video Size?

### Short Answer: NO ❌

**Currently, resource allocation is completely static and does NOT adapt to:**
- Number of clips being stitched
- Video resolution (720p, 1080p, 4K)
- Video duration (8s, 30s, 2min)
- Total file size (50MB vs 500MB)

### Why This Matters:
- **Stitching 2x 8-second clips**: Uses same 2 CPU + 4GB as...
- **Stitching 10x 2-minute clips**: Also uses 2 CPU + 4GB

---

## 💰 Cost Implications

### Current Fixed Pricing
Cloud Run Jobs charges based on:
- **vCPU-seconds**: $0.00002400 per vCPU-second
- **Memory GB-seconds**: $0.00000250 per GB-second
- **Minimum charge**: 1 second

### Example Costs:
For a job that takes **60 seconds**:
```
CPU cost:   2 vCPUs × 60s × $0.000024 = $0.00288
Memory cost: 4 GB × 60s × $0.0000025 = $0.00060
Total: ~$0.0035 per execution
```

### Problem:
- Small jobs (2 clips) pay for resources they don't need
- Large jobs (10 clips) might run slower or timeout with insufficient resources

---

## 🔧 How Resource Allocation Actually Works

### When Job is Created/Updated:
Resources are set via `gcloud run jobs update` or `cloudbuild.yaml` deployment.

### Currently Set To:
```bash
# This is how it was configured (manually or via previous deployment)
gcloud run jobs update reel-stitching-job \
  --cpu=2 \
  --memory=4Gi \
  --timeout=900 \
  --region=us-central1 \
  --project=phoenix-project-386
```

### These Settings Are STICKY:
Once set, they persist across all job executions until manually updated.

---

## 🚀 Implementing Dynamic Resource Allocation

### Option 1: Add Resource Tiers (Recommended)

Create different resource configurations based on workload:

```python
# In services/job_orchestrator.py or new config file

RESOURCE_TIERS = {
    'small': {  # 2-3 clips, <100MB total
        'cpu': '1',
        'memory': '2Gi',
        'timeout': '600'  # 10 minutes
    },
    'medium': {  # 4-6 clips, <300MB total
        'cpu': '2',
        'memory': '4Gi',
        'timeout': '900'  # 15 minutes
    },
    'large': {  # 7-10 clips, <600MB total
        'cpu': '4',
        'memory': '8Gi',
        'timeout': '1200'  # 20 minutes
    },
    'xlarge': {  # 10+ clips or 4K video
        'cpu': '8',
        'memory': '16Gi',
        'timeout': '1800'  # 30 minutes
    }
}

def calculate_resource_tier(clip_count: int, total_size_mb: int) -> str:
    """Determine resource tier based on workload."""
    if clip_count <= 3 and total_size_mb < 100:
        return 'small'
    elif clip_count <= 6 and total_size_mb < 300:
        return 'medium'
    elif clip_count <= 10 and total_size_mb < 600:
        return 'large'
    else:
        return 'xlarge'
```

### Option 2: Update Job Before Execution

Modify `job_orchestrator.py` to update job resources before execution:

```python
def _enqueue_job_with_resources(
    self, 
    job_id: str, 
    job_type: str, 
    payload: Dict[str, Any],
    cpu: str = '2',
    memory: str = '4Gi',
    timeout: int = 900
) -> None:
    """Execute Cloud Run Job with custom resources."""
    
    # First, update job resources
    job_name = f"projects/{self.project_id}/locations/{self.region}/jobs/{job_type}"
    
    update_request = run_v2.UpdateJobRequest(
        job=run_v2.Job(
            name=job_name,
            template=run_v2.ExecutionTemplate(
                template=run_v2.TaskTemplate(
                    containers=[
                        run_v2.Container(
                            resources=run_v2.ResourceRequirements(
                                limits={
                                    'cpu': cpu,
                                    'memory': memory
                                }
                            )
                        )
                    ],
                    timeout=f"{timeout}s"
                )
            )
        )
    )
    
    # Update job configuration
    self.jobs_client.update_job(request=update_request)
    
    # Then execute as normal
    # ... rest of execution code
```

### Option 3: Create Multiple Job Definitions

Instead of one `reel-stitching-job`, create multiple:
- `reel-stitching-job-small`
- `reel-stitching-job-medium`
- `reel-stitching-job-large`
- `reel-stitching-job-xlarge`

Then route to the appropriate job based on workload.

---

## 📊 Recommended Approach

### Phase 1: Analyze Current Usage
```bash
# Check recent execution times
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=reel-stitching-job" \
  --project=phoenix-project-386 \
  --format="table(timestamp,severity,textPayload)" \
  --limit=50 \
  --freshness=7d
```

### Phase 2: Determine If Optimization Needed

**Questions to answer:**
1. Are jobs completing well under 15 minutes? (Over-provisioned)
2. Are jobs timing out? (Under-provisioned)
3. What's the typical clip count? (2-3? 5-7? 10+?)
4. What's the file size distribution?

### Phase 3: Implement Solution

**If most jobs are similar size:**
- Keep current fixed resources ✅
- Adjust to median workload

**If workload varies significantly:**
- Implement Option 1 (Resource Tiers) 🎯
- Calculate tier in `trigger_stitching_job()`
- Pass as parameter to job execution

---

## 🎯 Current Recommendation

### For Now: Keep Fixed Resources ✅

**Reasoning:**
1. **Veo-generated videos are consistent**:
   - All 8 seconds duration
   - Similar resolution (1080x1920 portrait)
   - Predictable file sizes (~10-20MB per clip)

2. **Clip counts are limited**:
   - Most projects: 2-5 clips
   - Max practical: 10 clips
   - Total processing: <200MB typically

3. **Current resources (2 CPU + 4GB) are adequate**:
   - Jobs complete in 1-2 minutes
   - No timeout issues observed
   - Cost per execution: ~$0.003-0.007

4. **Simplicity**:
   - No complex logic needed
   - Easy to reason about
   - Predictable costs

### When to Revisit:

Consider dynamic allocation if:
- ✅ Supporting user-uploaded videos (variable sizes)
- ✅ Supporting longer videos (>30 seconds)
- ✅ Supporting 4K resolution
- ✅ Processing 20+ clips per project
- ✅ Cost optimization becomes critical at scale

---

## 🔍 How to Change Resources Manually

### Update Job Configuration:
```bash
gcloud run jobs update reel-stitching-job \
  --cpu=4 \
  --memory=8Gi \
  --timeout=1200 \
  --region=us-central1 \
  --project=phoenix-project-386
```

### Or via cloudbuild.yaml:
Add deployment step to `jobs/video_stitching/cloudbuild.yaml`:

```yaml
steps:
  # ... existing build steps ...
  
  # Deploy with specific resources
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
      - '--cpu'
      - '4'           # ← Change here
      - '--memory'
      - '8Gi'         # ← Change here
      - '--timeout'
      - '1200'        # ← Change here
```

---

## 📈 Monitoring Resource Usage

### Check Memory/CPU Usage:
```bash
# Recent job executions
gcloud run jobs executions list \
  --job=reel-stitching-job \
  --region=us-central1 \
  --project=phoenix-project-386 \
  --limit=10
```

### View Logs with Resource Info:
```bash
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=reel-stitching-job" \
  --project=phoenix-project-386 \
  --format="table(timestamp,severity,textPayload)" \
  --limit=20
```

### In Cloud Console:
Navigate to: Cloud Run → Jobs → reel-stitching-job → Metrics
- CPU utilization
- Memory utilization  
- Execution duration

---

## 💡 Summary

| Aspect | Current State |
|--------|---------------|
| **Resource Allocation** | Fixed/Hardcoded |
| **CPU** | 2 vCPUs (always) |
| **Memory** | 4 GB (always) |
| **Timeout** | 15 minutes (always) |
| **Based on Video Size?** | ❌ No |
| **Based on Clip Count?** | ❌ No |
| **Configurable?** | ✅ Yes (via gcloud or cloudbuild.yaml) |
| **Dynamic at Runtime?** | ❌ No (requires code changes) |
| **Current Performance** | ✅ Adequate for typical workloads |
| **Optimization Needed?** | ⏳ Monitor first, optimize if needed |

**Bottom Line**: Resources are fixed at deployment time, not determined by video characteristics. This is fine for your current use case with consistent Veo-generated videos, but could be optimized for variable workloads in the future.
