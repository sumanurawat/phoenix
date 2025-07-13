#!/bin/bash

# Setup Claude API Key in GCP Secret Manager for Phoenix project
# Run this script to add the Claude API key to your production environment

echo "🔐 Setting up Claude API key in GCP Secret Manager..."

# Set the project ID
PROJECT_ID="phoenix-project-386"

# Set the secret name and value
SECRET_NAME="phoenix-claude-api-key"
SECRET_VALUE="[ALREADY_SET]"  # API key has been set in GCP Secret Manager

echo "📋 Project: $PROJECT_ID"
echo "🔑 Secret: $SECRET_NAME"

# Create the secret (will fail if it already exists, which is fine)
echo "📝 Creating secret..."
gcloud secrets create $SECRET_NAME --project=$PROJECT_ID 2>/dev/null || echo "Secret already exists, updating..."

# Add the secret value (already done)
echo "💾 Secret value already set in production..."
echo "ℹ️ To update the secret value, run:"
echo "echo -n 'NEW_API_KEY' | gcloud secrets versions add $SECRET_NAME --data-file=- --project=$PROJECT_ID"

# Grant access to the service account
SERVICE_ACCOUNT="phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com"
echo "🔐 Granting access to service account: $SERVICE_ACCOUNT"
gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

echo "✅ Claude API key setup complete!"
echo ""
echo "🚀 Next steps:"
echo "1. Run 'chmod +x setup_claude_secret.sh' to make this script executable"
echo "2. Run './setup_claude_secret.sh' to execute the setup"
echo "3. Deploy your app with: 'gcloud builds submit --config cloudbuild.yaml'"
echo ""
echo "🔍 Verify the secret was created:"
echo "gcloud secrets list --project=$PROJECT_ID | grep claude"