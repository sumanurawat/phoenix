# Phoenix Monitoring Setup Guide

## Quick Links

**Cloud Monitoring Console**: https://console.cloud.google.com/monitoring?project=phoenix-project-386

**Alerting Policies**: https://console.cloud.google.com/monitoring/alerting/policies?project=phoenix-project-386

---

## Recommended Alert Policies

### 1. Cloud Run Jobs - High Failure Rate

**Alert for video-generation-job and image-generation-job failures >5%**

**Setup Steps:**
1. Go to [Alerting Policies](https://console.cloud.google.com/monitoring/alerting/policies?project=phoenix-project-386)
2. Click **"+ Create Policy"**
3. **Add Condition**:
   - Resource type: `Cloud Run Job`
   - Metric: `Completed execution count` (filter by `response_code=failed`)
   - Filter: `job_name = "video-generation-job"` OR `job_name = "image-generation-job"`
   - Threshold: Failure rate > 5%
   - Duration: 5 minutes
4. **Configure Notifications**:
   - Add notification channel: Email to `sumanurawat12@gmail.com`
5. **Name**: "Cloud Run Jobs - High Failure Rate (>5%)"
6. Save

### 2. Phoenix Service - High Error Rate

**Alert for phoenix service HTTP 5xx errors >1%**

**Setup Steps:**
1. Click **"+ Create Policy"**
2. **Add Condition**:
   - Resource type: `Cloud Run Revision`
   - Metric: `Request count` (filter by `response_code_class=5xx`)
   - Filter: `service_name = "phoenix"`
   - Threshold: Error rate > 1%
   - Duration: 5 minutes
3. **Configure Notifications**:
   - Email to `sumanurawat12@gmail.com`
4. **Name**: "Phoenix Service - High Error Rate (>1%)"
5. Save

### 3. Phoenix Service - Service Unavailable

**Alert if phoenix service is down**

**Setup Steps:**
1. Click **"+ Create Policy"**
2. **Add Condition**:
   - Resource type: `Cloud Run Revision`
   - Metric: `Request count`
   - Filter: `service_name = "phoenix"`
   - Condition: No data received for 10 minutes
3. **Configure Notifications**:
   - Email to `sumanurawat12@gmail.com`
4. **Name**: "Phoenix Service - No Traffic (Possible Downtime)"
5. Save

---

## Notification Channels

Make sure you have an email notification channel configured:

1. Go to [Notification Channels](https://console.cloud.google.com/monitoring/alerting/notifications?project=phoenix-project-386)
2. Click **"+ Add New"**
3. Select **Email**
4. Enter: `sumanurawat12@gmail.com`
5. Verify the email address

---

## Metrics to Monitor

### Cloud Run Jobs
- **Execution count** (total runs)
- **Execution time** (duration)
- **Billable time** (for cost tracking)
- **Failed execution count** (errors)

### Phoenix Service
- **Request count** (traffic)
- **Request latencies** (performance)
- **Container CPU utilization** (resource usage)
- **Container memory utilization** (memory usage)

### Quick Metrics Dashboard
https://console.cloud.google.com/run/detail/us-central1/phoenix/metrics?project=phoenix-project-386

---

## Cost Monitoring

**Billing Dashboard**: https://console.cloud.google.com/billing?project=phoenix-project-386

Set up budget alerts:
1. Go to [Budgets & Alerts](https://console.cloud.google.com/billing/budgets?project=phoenix-project-386)
2. Create budget: $10/month
3. Set alert thresholds: 50%, 75%, 100%
4. Get notified if costs spike unexpectedly

---

## Logs Explorer

**Live Logs**: https://console.cloud.google.com/logs/query?project=phoenix-project-386

**Useful queries:**

```
# Phoenix service errors
resource.type="cloud_run_revision"
resource.labels.service_name="phoenix"
severity>=ERROR

# Video generation job logs
resource.type="cloud_run_job"
resource.labels.job_name="video-generation-job"

# Image generation job logs
resource.type="cloud_run_job"
resource.labels.job_name="image-generation-job"

# All 5xx errors
resource.type="cloud_run_revision"
httpRequest.status>=500
```

---

## Current Status (Post-Migration)

✅ **Phoenix Service**: phoenix-00226-pxc (deployed, healthy)  
✅ **Video Generation Job**: video-generation-job (tested, working)  
✅ **Image Generation Job**: image-generation-job (tested, working)  
✅ **Monthly Cost**: ~$3-5 (down from ~$73)  
✅ **Infrastructure**: 100% serverless (no Redis, no workers, no VPC)

---

## Quick Health Checks

```bash
# Check service status
curl -s -o /dev/null -w "%{http_code}" https://phoenix-hpbuj2rr6q-uc.a.run.app/

# Check recent builds
gcloud builds list --limit=3 --project=phoenix-project-386

# Check for errors in last hour
gcloud logging read "severity>=ERROR" --limit=20 --project=phoenix-project-386 --freshness=1h
```
