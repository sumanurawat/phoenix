#!/bin/bash

# Phoenix Deployment Test Script
# Tests deployment configuration before pushing to production

set -e  # Exit on any error

PROJECT_ID="phoenix-project-386"
REGION="us-central1"
SERVICE_NAME="phoenix"

echo "🚀 Phoenix Deployment Test Script"
echo "=================================="

# Function to check if a secret exists
check_secret() {
    local secret_name=$1
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "✅ Secret exists: $secret_name"
        return 0
    else
        echo "❌ Secret missing: $secret_name"
        return 1
    fi
}

# Function to create missing secret
create_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if [ -z "$secret_value" ]; then
        echo "⚠️  Skipping creation of $secret_name (no value provided)"
        return 1
    fi
    
    echo "Creating secret: $secret_name"
    echo "$secret_value" | gcloud secrets create "$secret_name" --data-file=- --project="$PROJECT_ID"
    echo "✅ Created secret: $secret_name"
}

echo ""
echo "📋 Step 1: Checking required secrets..."
echo "----------------------------------------"

MISSING_SECRETS=()

# Check all required secrets from cloudbuild.yaml
REQUIRED_SECRETS=(
    "phoenix-gemini-api-key"
    "phoenix-secret-key" 
    "phoenix-google-api-key"
    "phoenix-search-engine-id"
    "phoenix-newsdata-api-key"
    "phoenix-kaggle-username"
    "phoenix-kaggle-key"
    "phoenix-claude-api-key"
    "phoenix-grok-api-key"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! check_secret "$secret"; then
        MISSING_SECRETS+=("$secret")
    fi
done

if [ ${#MISSING_SECRETS[@]} -ne 0 ]; then
    echo ""
    echo "❌ Missing secrets detected:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "   - $secret"
    done
    echo ""
    echo "🔧 To fix missing secrets, run:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "   gcloud secrets create $secret --data-file=- --project=$PROJECT_ID"
    done
    echo ""
    echo "💡 Or set them manually in Google Cloud Console:"
    echo "   https://console.cloud.google.com/security/secret-manager?project=$PROJECT_ID"
    echo ""
fi

echo ""
echo "🐋 Step 2: Testing Docker build..."
echo "-----------------------------------"

# Test Docker build locally
if docker build -t phoenix-test . --no-cache; then
    echo "✅ Docker build successful"
else
    echo "❌ Docker build failed"
    exit 1
fi

echo ""
echo "📦 Step 3: Checking dependencies..."
echo "------------------------------------"

# Check if requirements.txt has all needed dependencies
REQUIRED_DEPS=("flask" "openai" "httpx" "anthropic" "google-generativeai")
for dep in "${REQUIRED_DEPS[@]}"; do
    if grep -q "^$dep" requirements.txt; then
        echo "✅ Dependency found: $dep"
    else
        echo "❌ Dependency missing: $dep"
    fi
done

echo ""
echo "🔍 Step 4: Validating configuration files..."
echo "----------------------------------------------"

# Check if cloudbuild.yaml exists and is valid
if [ -f "cloudbuild.yaml" ]; then
    echo "✅ cloudbuild.yaml exists"
    
    # Check if all required secrets are referenced
    for secret in "${REQUIRED_SECRETS[@]}"; do
        if grep -q "$secret" cloudbuild.yaml; then
            echo "✅ Secret referenced in cloudbuild.yaml: $secret"
        else
            echo "⚠️  Secret not in cloudbuild.yaml: $secret"
        fi
    done
else
    echo "❌ cloudbuild.yaml missing"
    exit 1
fi

# Check Dockerfile
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile exists"
else
    echo "❌ Dockerfile missing"
    exit 1
fi

echo ""
echo "🌐 Step 5: Testing service configuration..."
echo "--------------------------------------------"

# Check if service account exists
SERVICE_ACCOUNT="phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com"
if gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "✅ Service account exists: $SERVICE_ACCOUNT"
else
    echo "❌ Service account missing: $SERVICE_ACCOUNT"
    echo "🔧 To create:"
    echo "   gcloud iam service-accounts create phoenix-service-account --project=$PROJECT_ID"
fi

echo ""
echo "📊 Step 6: Summary..."
echo "----------------------"

if [ ${#MISSING_SECRETS[@]} -eq 0 ]; then
    echo "✅ All secrets are configured"
    echo "✅ Docker build successful"
    echo "✅ Configuration files valid"
    echo ""
    echo "🚀 Ready for deployment!"
    echo ""
    echo "To deploy manually:"
    echo "   gcloud builds submit --config cloudbuild.yaml --project=$PROJECT_ID"
    echo ""
    echo "Or push to main branch to trigger automatic deployment."
else
    echo "❌ Deployment will fail due to missing secrets"
    echo "🔧 Fix the missing secrets first, then re-run this test"
    exit 1
fi

echo ""
echo "🧹 Cleanup..."
echo "--------------"
# Remove test Docker image
docker rmi phoenix-test >/dev/null 2>&1 || true
echo "✅ Cleanup complete"

echo ""
echo "✨ Test deployment script completed successfully!"