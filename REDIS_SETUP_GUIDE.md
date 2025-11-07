# Redis Setup for Video Generation - URGENT FIX

## 🚨 Problem
Your Cloud Run service has no Redis instance, so video generation is broken.

## ✅ Solution: Upstash Redis (Free Tier)

### Step 1: Create Upstash Account
1. Go to https://upstash.com/
2. Sign up (free account)
3. Create new Redis database:
   - **Name**: phoenix-video-queue
   - **Region**: us-east-1 (closest to us-central1)
   - **Type**: Regional (cheaper)

### Step 2: Get Connection Details
After creating database, you'll see:
```
REDIS_HOST: us1-xxx-xxxx.upstash.io
REDIS_PORT: 6379
REDIS_PASSWORD: AxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxQ==
```

### Step 3: Add to Google Secret Manager
```bash
# Create secrets
echo -n "us1-xxx-xxxx.upstash.io" | gcloud secrets create phoenix-redis-host \
  --data-file=- --replication-policy=automatic

echo -n "6379" | gcloud secrets create phoenix-redis-port \
  --data-file=- --replication-policy=automatic

echo -n "AxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxQ==" | gcloud secrets create phoenix-redis-password \
  --data-file=- --replication-policy=automatic
```

### Step 4: Update Cloud Build Config
Edit `cloudbuild-dev.yaml` - add to `--update-secrets` line:
```yaml
REDIS_HOST=phoenix-redis-host:latest,REDIS_PORT=phoenix-redis-port:latest,REDIS_PASSWORD=phoenix-redis-password:latest
```

### Step 5: Redeploy
```bash
gcloud builds submit --config cloudbuild-dev.yaml
```

### Step 6: Verify
Check logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR AND textPayload=~'Redis'" --limit 10
```

Should see:
```
Initializing Celery with broker: redis://us1-xxx-xxxx.upstash.io:6379/0
```

---

## Alternative: Google Memorystore (Production)

If you need production-grade Redis:

### Step 1: Enable APIs
```bash
gcloud services enable redis.googleapis.com vpcaccess.googleapis.com
```

### Step 2: Create Redis Instance
```bash
gcloud redis instances create phoenix-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=basic
```

**Cost**: ~$30/month

### Step 3: Create VPC Connector
```bash
gcloud compute networks vpc-access connectors create phoenix-redis-connector \
  --region=us-central1 \
  --network=default \
  --range=10.8.0.0/28
```

**Cost**: ~$8/month

### Step 4: Get Connection Info
```bash
gcloud redis instances describe phoenix-redis --region=us-central1
```

Note the `host` IP address (e.g., `10.x.x.x`)

### Step 5: Update Cloud Build
Add to `cloudbuild-dev.yaml`:
```yaml
- '--vpc-connector'
- 'phoenix-redis-connector'
- '--vpc-egress'
- 'private-ranges-only'
```

Add secrets as in Upstash steps.

---

## Testing Locally

Your local setup works because you have Redis running on localhost.

To test Upstash locally:
```bash
# Add to .env
REDIS_HOST=us1-xxx-xxxx.upstash.io
REDIS_PORT=6379
REDIS_PASSWORD=AxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxQ==

# Restart worker
./start_local.sh
```

---

## Troubleshooting

### Still seeing "Connection to Redis lost"?
1. Check secrets are deployed:
   ```bash
   gcloud run services describe phoenix-dev --region=us-central1 --format=yaml | grep -A 20 "env:"
   ```

2. Check Upstash dashboard for connection attempts

3. Verify password doesn't have extra quotes or spaces

### Worker not processing jobs?
```bash
# Check Celery is starting
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~'Celery'" --limit 20

# Should see:
# "Initializing Celery with broker..."
# "Celery worker starting..."
```

---

## Why This Happened

Cloud Run is **stateless** - each instance runs in isolation with no shared memory.

**Local development**: Redis runs on your Mac (started with `brew services start redis`)
**Production**: No Redis instance configured → Celery can't queue tasks

**The fix ensures Celery can connect to a persistent Redis instance accessible from Cloud Run.**
