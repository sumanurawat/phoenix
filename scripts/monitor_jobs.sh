#!/bin/bash

# Cloud Run Jobs Monitoring Script
# Usage: ./scripts/monitor_jobs.sh

echo "🔍 Cloud Run Jobs Monitor"
echo "=========================="

# Set project
export GOOGLE_CLOUD_PROJECT=phoenix-project-386

echo "📊 Recent Job Executions:"
gcloud run jobs executions list --region=us-central1 --limit=5 --format="table(
  metadata.name:label=EXECUTION,
  spec.taskTemplate.spec.template.spec.template.spec.containers[0].name:label=JOB,
  status.conditions[0].type:label=STATUS,
  status.startTime:label=STARTED,
  status.completionTime:label=COMPLETED
)" 2>/dev/null || echo "No executions found (jobs not deployed yet)"

echo ""
echo "📋 Queue Status:"
gcloud tasks queues describe reel-jobs-queue --location=us-central1 --format="table(
  name:label=QUEUE,
  state:label=STATE,
  rateLimits.maxDispatchesPerSecond:label=MAX_RATE
)" 2>/dev/null

echo ""
echo "📝 Recent Job Logs (last 10 minutes):"
gcloud logging read 'resource.type="cloud_run_job" AND timestamp>="$(date -u -d "10 minutes ago" +%Y-%m-%dT%H:%M:%S)"' \
  --limit=10 \
  --format="table(timestamp,severity,textPayload)" 2>/dev/null || echo "No recent logs found"

echo ""
echo "🔗 Useful Links:"
echo "  📊 Jobs Dashboard: https://console.cloud.google.com/run/jobs?project=phoenix-project-386"
echo "  📋 Queue Dashboard: https://console.cloud.google.com/cloudtasks/queue/us-central1/reel-jobs-queue?project=phoenix-project-386"
echo "  📝 Logs: https://console.cloud.google.com/logs/query?project=phoenix-project-386"
echo ""
echo "🔄 To watch in real-time: watch -n 5 ./scripts/monitor_jobs.sh"