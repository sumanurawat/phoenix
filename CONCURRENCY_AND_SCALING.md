# Phoenix Concurrency and Scaling Architecture

## Gunicorn Configuration Explained

```dockerfile
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 3600 app:app
```

### Component Breakdown

| Parameter | Value | Meaning | Impact |
|-----------|-------|---------|--------|
| `--workers` | 1 | Number of separate Python processes | 1 process = shared memory for Firebase connections, caches |
| `--threads` | 8 | Concurrent threads per worker | **8 simultaneous requests per container** |
| `--timeout` | 3600 | Request timeout (seconds) | Allows 1-hour video generation jobs |

### Why 1 Worker Instead of Multiple?

**Single worker benefits:**
- ✅ **Shared Firebase connections** - Single Firestore client, connection pooling works
- ✅ **Shared in-memory state** - SSE event bus, active job tracking
- ✅ **Simpler debugging** - One process to monitor
- ✅ **Lower memory overhead** - ~200MB vs ~400MB for 2 workers

**Multi-worker drawbacks:**
- ❌ Each worker duplicates Firebase connections
- ❌ SSE events don't work across workers (user on worker 1 won't see events from worker 2)
- ❌ Higher memory usage (Cloud Run charges per GB-second)

**Cloud Run philosophy:** Scale horizontally (more containers) instead of vertically (more workers per container)

---

## The Three Queue Layers

### Layer 1: Cloud Run Load Balancer
```
Internet Request
    ↓
[Google Cloud Load Balancer]
    ├→ Queue capacity: ~10,000s of requests
    ├→ Auto-scaling trigger: When containers hit concurrency limit
    ├→ Health checks: Ensures containers are responsive
    └→ Routes to: Available containers
```

**Configuration:**
```yaml
--concurrency: 8          # NEW! Tells Cloud Run each container can handle 8 requests
--max-instances: 100      # NEW! Max containers to create
```

**Before our fix:**
- Default concurrency: 80 requests per container
- Reality: Only 8 threads available
- Result: 72 requests would queue INSIDE container unnecessarily

**After our fix:**
- Concurrency: 8 (matches threads)
- When 9th request arrives → Cloud Run creates Container 2 immediately
- Result: Faster auto-scaling, shorter queues

---

### Layer 2: Gunicorn Socket Backlog
```
Cloud Run → Container
    ↓
[Gunicorn Process]
    ├→ Queue capacity: 2048 connections (default --backlog)
    ├→ When full: Returns 502 Bad Gateway
    └→ Hands off to: Thread pool
```

**Default configuration:**
```bash
--backlog 2048   # Not explicitly set, using OS default
```

**What happens:**
- Requests 1-8: Assigned to threads immediately
- Requests 9-2056: Wait in socket backlog queue
- Request 2057+: Connection refused (502 error)

**Typical wait times:**
- If threads process quickly (< 1s): Queue clears fast
- If threads stuck on long operations (video generation = 60s each):
  - Request 9 waits up to 60 seconds
  - Request 16 waits up to 120 seconds (2 × 60s)

---

### Layer 3: Thread Pool (Active Processing)
```
Gunicorn → Thread Pool
    ↓
[Worker Process - 8 threads]
    Thread 1 → Flask app → Video generation (60s)
    Thread 2 → Flask app → Search request (0.5s)
    Thread 3 → Flask app → Firebase read (0.1s)
    Thread 4 → Flask app → Video generation (60s)
    Thread 5 → Flask app → Chat request (5s)
    Thread 6 → Flask app → Waiting for Veo API...
    Thread 7 → Flask app → SSE connection (streaming)
    Thread 8 → Flask app → Stitch job (30s)
```

**No queue at this layer** - threads execute immediately once assigned.

---

## Auto-Scaling Behavior

### Scenario: 50 Users Start Video Generation Simultaneously

#### With OLD config (concurrency=80 default):
```
Time 0s:
  Container 1: Requests 1-80 queued
    - Threads 1-8: Processing (8 users generating)
    - Queue: 72 users waiting
  
Time 60s: (first 8 videos complete)
  Container 1: Requests 9-16 start processing
    - Queue: 64 users still waiting
  
Time 120s: (next 8 videos complete)
  Container 1: Requests 17-24 start processing
    - Queue: 56 users still waiting

Result: Takes 50 × 60s / 8 = 375 seconds (6 minutes) for all users
```

#### With NEW config (concurrency=8):
```
Time 0s:
  Container 1: Requests 1-8 (all threads busy)
  Container 2: Requests 9-16 (created immediately) ← AUTO-SCALED
  Container 3: Requests 17-24 (created immediately)
  Container 4: Requests 25-32 (created immediately)
  Container 5: Requests 33-40 (created immediately)
  Container 6: Requests 41-48 (created immediately)
  Container 7: Requests 49-50 (2 threads used)

Time 60s: All 50 users complete simultaneously!

Result: Takes 60 seconds total (10× faster than old config)
```

**Cost difference:**
- Old: 1 container × 375s = 375 container-seconds
- New: 7 containers × 60s = 420 container-seconds (12% more expensive)
- **Trade-off:** Pay 12% more for 6× better user experience

---

## Current Limits and Capacity

### Per Container
```
Threads: 8
Memory: 1 GB
CPU: 1 vCPU
Concurrent requests: 8 (now correctly configured)
Socket backlog: 2048
```

### Fleet-Wide
```
Max containers: 100
Max concurrent users: 100 × 8 = 800 users
Max queued requests: 100 × 2048 = 204,800 (theoretical, never reached)
```

### Practical Limits
**For video generation (60s per video):**
- 800 users can generate simultaneously
- If all 800 users generate 15 clips each = 12,000 videos in ~15 minutes
- Cost: ~$1.50 per 15-minute burst (at $0.00002400 per GB-second)

**For quick requests (< 1s):**
- Can handle 800 × (1 request/second) = **800 requests/second**
- Or 2.8 million requests per hour

---

## Why Video Generation is Sequential (Not Parallel)

### Current Implementation
```python
# In reel_generation_service.py line 285-320
for idx, prompt in enumerate(ctx.prompts):
    # Generate ONE video at a time
    clip_paths_for_prompt = self._generate_single_prompt(ctx, idx, prompt)
    completed += 1
```

**Timeline for 15 videos:**
```
Video 1: [====================] 60s
Video 2:                        [====================] 60s  
Video 3:                                                [====================] 60s
...
Video 15:                                                                              [====================] 60s
Total: 15 × 60s = 900 seconds (15 minutes)
```

### Why Not Parallel?

#### Technical Limitations:
1. **Veo API Rate Limits**
   - Per-project quota: Unknown (Google doesn't publish)
   - Likely: 5-10 concurrent requests max
   - Risk: Parallel requests could hit 429 Too Many Requests

2. **Memory Constraints**
   - Each video generation: ~100-200MB memory for encoding
   - 15 parallel videos: 1.5-3 GB memory needed
   - Your container: Only 1 GB allocated → Would crash with OOM

3. **CPU Bottleneck**
   - 1 vCPU shared across all operations
   - 15 parallel API calls = 15 threads competing for 1 CPU
   - Actually slower due to context switching overhead

4. **Thread Pool Exhaustion**
   - You only have 8 threads total
   - If one user uses all 8 threads for parallel generation:
     - Other 7 users get blocked completely
     - Better to use 1 thread per user, serve 8 users concurrently

### Could We Make It Parallel?

**Option 1: Use ThreadPoolExecutor for controlled parallelism**
```python
from concurrent.futures import ThreadPoolExecutor

# Generate 3 videos at a time (safe for 1GB memory, 1 CPU)
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(self._generate_single_prompt, ctx, idx, prompt) 
               for idx, prompt in enumerate(ctx.prompts)]
    results = [f.result() for f in futures]

# Timeline for 15 videos with 3 parallel:
# Batch 1 (videos 1-3):   [====================] 60s
# Batch 2 (videos 4-6):                          [====================] 60s
# Batch 3 (videos 7-9):                                                 [====================] 60s
# Batch 4 (videos 10-12):                                                                      [====================] 60s
# Batch 5 (videos 13-15):                                                                                             [====================] 60s
# Total: 5 × 60s = 300 seconds (5 minutes) - 3× faster!
```

**Option 2: Cloud Run Jobs (Background processing)**
- Already implemented for stitching!
- Could extend to video generation
- Benefits:
  - Dedicated resources (2 CPU, 4GB RAM)
  - Can do 5-10 parallel videos safely
  - Doesn't block web server threads
  - Better cost efficiency

**Recommendation:** Use Cloud Run Jobs for video generation too (like stitching)

---

## Monitoring Queue Depth

### Check Gunicorn Queue (requires custom metrics)
```python
# Add to app.py
import psutil
from flask import request

@app.before_request
def log_queue_depth():
    # Count active threads
    active_threads = threading.active_count()
    logger.info(f"Active threads: {active_threads}/8")
```

### Check Cloud Run Metrics (Google Cloud Console)
```
Metrics → Cloud Run → phoenix service
  - Request count (per container)
  - Request latency (p50, p95, p99)
  - Container instance count (auto-scaling)
  - CPU utilization
  - Memory utilization
```

**Warning signs:**
- ⚠️ p95 latency > 10s (queue building up)
- ⚠️ Container count not scaling (concurrency misconfigured)
- ⚠️ Memory > 900MB (approaching 1GB limit)

---

## Recommended Configuration Changes

### 1. Optimize for Video Generation Workload
```yaml
# In cloudbuild.yaml
- '--memory'
- '2Gi'              # Increase from 1Gi (allows 2-3 parallel videos)
- '--cpu'
- '2'                # Increase from 1 (faster video encoding)
- '--concurrency'
- '8'                # Keep at 8 (matches threads)
- '--max-instances'
- '100'              # Keep at 100 (or increase if you expect >800 concurrent users)
```

**Cost impact:** ~2× current cost, but better user experience

### 2. Add Min Instances for Production
```yaml
- '--min-instances'
- '1'                # Keep 1 container always warm (avoids cold starts)
```

**Cost impact:** $7-10/month for always-on container, but instant response times

### 3. Use Cloud Tasks + Cloud Run Jobs for Video Generation
```
User clicks "Generate" 
  ↓
Flask creates Cloud Task (instant response)
  ↓
Cloud Task triggers Cloud Run Job (dedicated 4GB RAM, 2 CPU)
  ↓
Job generates 15 videos in parallel (5 at a time)
  ↓
Job updates Firestore → User sees progress via SSE
```

**Benefits:**
- Web server threads freed immediately
- Better resource utilization
- Cheaper (pay only for generation time)
- Already implemented for stitching!

---

## Summary

### Your Current Architecture
```
1 Worker × 8 Threads = 8 concurrent requests per container
Cloud Run: Up to 100 containers = 800 max concurrent users
Queue Layers:
  1. Cloud Load Balancer (huge, managed by Google)
  2. Gunicorn backlog (2048 connections per container)
  3. Thread pool (8 active executions per container)
```

### Key Fixes Applied
✅ Set `--concurrency 8` (matches thread count)
✅ Set `--max-instances 100` (explicit limit)
✅ Timeout `3600s` (allows long video generation)

### Next Optimizations (Optional)
- [ ] Increase memory to 2Gi for parallel video generation
- [ ] Move video generation to Cloud Run Jobs (like stitching)
- [ ] Add `--min-instances 1` to avoid cold starts
- [ ] Implement request queuing metrics/monitoring

### Performance Expectations
- Quick requests (< 1s): 800 req/sec sustained
- Video generation: 800 concurrent users, each taking 15 min for 15 videos
- Auto-scaling: New container every 8 requests (5-10 second startup)
- Cost: ~$50-100/month at moderate load (1000 hours container time)
