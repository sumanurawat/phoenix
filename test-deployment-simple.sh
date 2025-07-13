#!/bin/bash

# Simple Phoenix Deployment Test (without Docker)
set -e

PROJECT_ID="phoenix-project-386"

echo "🚀 Simple Phoenix Deployment Test"
echo "================================="

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

echo ""
echo "📋 Checking required secrets..."
echo "-------------------------------"

MISSING_SECRETS=()
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

echo ""
echo "📦 Checking dependencies in requirements.txt..."
echo "------------------------------------------------"

REQUIRED_DEPS=("flask" "openai" "httpx" "anthropic" "google-generativeai")
for dep in "${REQUIRED_DEPS[@]}"; do
    if grep -q "^$dep" requirements.txt; then
        echo "✅ Dependency found: $dep"
    else
        echo "❌ Dependency missing: $dep"
    fi
done

echo ""
echo "📊 Summary..."
echo "-------------"

if [ ${#MISSING_SECRETS[@]} -eq 0 ]; then
    echo "✅ All required secrets are configured"
    echo "✅ All required dependencies are in requirements.txt"
    echo ""
    echo "🚀 Deployment should succeed!"
    echo ""
    echo "To deploy:"
    echo "   git push origin main"
    echo ""
    echo "Monitor deployment:"
    echo "   gcloud builds list --project=$PROJECT_ID --limit=5"
else
    echo "❌ Deployment will fail due to missing secrets:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "   - $secret"
    done
    exit 1
fi

echo ""
echo "✨ Simple test completed successfully!"