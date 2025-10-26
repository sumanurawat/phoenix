#!/bin/bash
# ============================================================================
# Provision Cloud Memorystore (Redis) for Celery Job Queue
# ============================================================================
# Purpose: Create Redis instance for Phoenix video generation job queue
# Cost: ~$40/month (1GB BASIC tier)
# Labels: app=phoenix, service=cache, env=prod, phase=3
# ============================================================================

set -e

PROJECT_ID="phoenix-project-386"
REGION="us-central1"
INSTANCE_NAME="phoenix-cache-prod"

echo "=================================================="
echo "Provisioning Redis for Phoenix Video Job Queue"
echo "=================================================="
echo ""
echo "Instance: $INSTANCE_NAME"
echo "Region: $REGION"
echo "Tier: BASIC (1GB)"
echo "Estimated Cost: ~$40/month"
echo ""

# Check if instance already exists
if gcloud redis instances describe $INSTANCE_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "⚠️  Redis instance '$INSTANCE_NAME' already exists"
    echo ""
    echo "Current configuration:"
    gcloud redis instances describe $INSTANCE_NAME \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format="yaml(name,tier,memorySizeGb,host,port,state)"
    echo ""
    read -p "Do you want to continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
else
    echo "📦 Creating Cloud Memorystore (Redis) instance..."
    gcloud redis instances create $INSTANCE_NAME \
        --size=1 \
        --tier=BASIC \
        --region=$REGION \
        --project=$PROJECT_ID \
        --labels=app=phoenix,service=cache,env=prod,phase=3

    echo ""
    echo "⏳ Waiting for Redis instance to be ready..."
    gcloud redis instances describe $INSTANCE_NAME \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format="value(state)"
fi

echo ""
echo "=================================================="
echo "✅ Redis Instance Provisioned"
echo "=================================================="
echo ""

# Get connection details
REDIS_HOST=$(gcloud redis instances describe $INSTANCE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(host)")

REDIS_PORT=$(gcloud redis instances describe $INSTANCE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(port)")

echo "Connection Details:"
echo "  Host: $REDIS_HOST"
echo "  Port: $REDIS_PORT"
echo ""

# Grant IAM permissions to service account
echo "🔐 Granting Redis access to phoenix-service-account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com" \
    --role="roles/redis.editor" \
    --condition=None

echo ""
echo "=================================================="
echo "Next Steps"
echo "=================================================="
echo ""
echo "1. Store Redis credentials in Secret Manager:"
echo ""
echo "   echo -n \"$REDIS_HOST\" | gcloud secrets create phoenix-redis-host --data-file=- --project=$PROJECT_ID"
echo "   echo -n \"$REDIS_PORT\" | gcloud secrets create phoenix-redis-port --data-file=- --project=$PROJECT_ID"
echo ""
echo "2. Grant service account access to secrets:"
echo ""
echo "   gcloud secrets add-iam-policy-binding phoenix-redis-host \\"
echo "     --member=\"serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com\" \\"
echo "     --role=\"roles/secretmanager.secretAccessor\""
echo ""
echo "   gcloud secrets add-iam-policy-binding phoenix-redis-port \\"
echo "     --member=\"serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com\" \\"
echo "     --role=\"roles/secretmanager.secretAccessor\""
echo ""
echo "3. Update cloudbuild.yaml to include Redis secrets"
echo ""
echo "4. Deploy worker service: gcloud builds submit --config cloudbuild.yaml ."
echo ""
echo "=================================================="
echo "Monitoring & Cost Tracking"
echo "=================================================="
echo ""
echo "View Redis metrics:"
echo "  https://console.cloud.google.com/memorystore/redis/locations/$REGION/instances/$INSTANCE_NAME?project=$PROJECT_ID"
echo ""
echo "Track costs (filtered by labels):"
echo "  https://console.cloud.google.com/billing/[BILLING_ID]/reports?project=$PROJECT_ID&filter=labels.app:phoenix%20labels.phase:3"
echo ""
echo "✅ Provisioning complete!"
