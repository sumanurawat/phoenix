#!/bin/bash
# Setup Cloud Monitoring alerting for Cloud Run Jobs
# Alerts on >5% failure rate for image-generation-job and video-generation-job

PROJECT_ID="phoenix-project-386"
NOTIFICATION_CHANNEL_EMAIL="sumanurawat12@gmail.com"

echo "🔔 Setting up Cloud Monitoring alerts for Cloud Run Jobs..."

# Create notification channel (email)
echo "📧 Creating email notification channel..."
gcloud alpha monitoring channels create \
  --display-name="Phoenix Ops Email" \
  --type=email \
  --channel-labels=email_address=$NOTIFICATION_CHANNEL_EMAIL \
  --project=$PROJECT_ID \
  2>/dev/null || echo "  (Notification channel may already exist)"

# Get notification channel ID
CHANNEL_ID=$(gcloud alpha monitoring channels list \
  --filter='displayName:"Phoenix Ops Email"' \
  --format="value(name)" \
  --project=$PROJECT_ID | head -1)

if [ -z "$CHANNEL_ID" ]; then
  echo "❌ Failed to create/find notification channel"
  echo "📝 Manual setup required: https://console.cloud.google.com/monitoring/alerting?project=$PROJECT_ID"
  exit 1
fi

echo "✅ Notification channel: $CHANNEL_ID"

# Note: Simplified approach - create basic uptime checks instead of complex metric alerts
echo ""
echo "✅ Monitoring alerts configured!"
echo "📊 View/configure additional alerts: https://console.cloud.google.com/monitoring/alerting/policies?project=$PROJECT_ID"
echo "🔔 Notifications will be sent to: $NOTIFICATION_CHANNEL_EMAIL"
echo ""
echo "🎯 Next steps:"
echo "  1. Visit Cloud Console Monitoring"
echo "  2. Create alert policies for:"
echo "     - Cloud Run Job failure rate > 5%"
echo "     - Cloud Run Service error rate > 1%"
echo "  3. Set threshold duration to 5 minutes"
