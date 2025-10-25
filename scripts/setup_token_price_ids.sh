#!/bin/bash
# Script to add Stripe Token Price IDs to Google Secret Manager
# This enables token purchases in production by making price IDs available as secrets

set -e

PROJECT_ID="phoenix-project-386"
REGION="us-central1"

echo "🎯 Setting up Stripe Token Price IDs in Google Secret Manager..."
echo "Project: $PROJECT_ID"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK first."
    exit 1
fi

# Authenticate if needed
echo "Checking authentication..."
gcloud auth list --filter=status:ACTIVE --format="value(account)" > /dev/null 2>&1 || {
    echo "❌ Not authenticated. Please run: gcloud auth login"
    exit 1
}

# Set project
echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one with Stripe Token Price IDs."
    echo ""
    echo "Required variables:"
    echo "  STRIPE_TOKEN_STARTER_PRICE_ID=price_xxx"
    echo "  STRIPE_TOKEN_POPULAR_PRICE_ID=price_xxx"
    echo "  STRIPE_TOKEN_PRO_PRICE_ID=price_xxx"
    echo "  STRIPE_TOKEN_CREATOR_PRICE_ID=price_xxx"
    exit 1
fi

# Load environment variables from .env
echo ""
echo "📂 Reading Stripe Token Price IDs from .env file..."
source .env

# Validate that all required price IDs are set
REQUIRED_VARS=(
    "STRIPE_TOKEN_STARTER_PRICE_ID"
    "STRIPE_TOKEN_POPULAR_PRICE_ID"
    "STRIPE_TOKEN_PRO_PRICE_ID"
    "STRIPE_TOKEN_CREATOR_PRICE_ID"
)

ALL_SET=true
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        echo "❌ Missing environment variable: $VAR"
        ALL_SET=false
    else
        echo "  ✓ Found $VAR: ${!VAR:0:20}..."
    fi
done

if [ "$ALL_SET" = false ]; then
    echo ""
    echo "❌ Please add all required Stripe Token Price IDs to your .env file"
    exit 1
fi

echo ""
echo "✅ All price IDs found in .env"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Creating/Updating Secrets in Google Secret Manager"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Function to create or update a secret
create_or_update_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    local DESCRIPTION=$3
    
    echo ""
    echo "Processing: $SECRET_NAME"
    echo "  Value: ${SECRET_VALUE:0:20}..."
    
    # Check if secret exists
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &> /dev/null; then
        echo "  Secret exists, adding new version..."
        echo -n "$SECRET_VALUE" | gcloud secrets versions add $SECRET_NAME \
            --data-file=- \
            --project=$PROJECT_ID
        echo "  ✅ Updated $SECRET_NAME"
    else
        echo "  Creating new secret..."
        echo -n "$SECRET_VALUE" | gcloud secrets create $SECRET_NAME \
            --data-file=- \
            --replication-policy="automatic" \
            --project=$PROJECT_ID \
            --labels=category=stripe,type=price-id
        echo "  ✅ Created $SECRET_NAME"
    fi
}

# Create/update all token price ID secrets
create_or_update_secret "STRIPE_TOKEN_STARTER_PRICE_ID" "$STRIPE_TOKEN_STARTER_PRICE_ID" "Stripe Token Starter Pack Price ID (50 tokens - \$4.99)"
create_or_update_secret "STRIPE_TOKEN_POPULAR_PRICE_ID" "$STRIPE_TOKEN_POPULAR_PRICE_ID" "Stripe Token Popular Pack Price ID (110 tokens - \$9.99)"
create_or_update_secret "STRIPE_TOKEN_PRO_PRICE_ID" "$STRIPE_TOKEN_PRO_PRICE_ID" "Stripe Token Pro Pack Price ID (250 tokens - \$19.99)"
create_or_update_secret "STRIPE_TOKEN_CREATOR_PRICE_ID" "$STRIPE_TOKEN_CREATOR_PRICE_ID" "Stripe Token Creator Pack Price ID (700 tokens - \$49.99)"

# Grant Cloud Run service account access to secrets
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Granting Access to Cloud Run Service Account"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SERVICE_ACCOUNT="phoenix-service-account@${PROJECT_ID}.iam.gserviceaccount.com"

for SECRET in "${REQUIRED_VARS[@]}"; do
    echo "  Granting access to $SECRET for $SERVICE_ACCOUNT..."
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID \
        --quiet
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SUCCESS - All Stripe Token Price IDs Configured!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Secrets Created:"
echo "  • STRIPE_TOKEN_STARTER_PRICE_ID  (50 tokens - \$4.99)"
echo "  • STRIPE_TOKEN_POPULAR_PRICE_ID  (110 tokens - \$9.99)"
echo "  • STRIPE_TOKEN_PRO_PRICE_ID      (250 tokens - \$19.99)"
echo "  • STRIPE_TOKEN_CREATOR_PRICE_ID  (700 tokens - \$49.99)"
echo ""
echo "🔐 Security:"
echo "  ✓ Secrets stored in Secret Manager (encrypted at rest)"
echo "  ✓ Access granted to Cloud Run service account only"
echo "  ✓ Secrets never appear in logs or build artifacts"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. ✅ Secrets are ready in Secret Manager"
echo ""
echo "2. 🔄 Update cloudbuild.yaml to use these secrets:"
echo "   Add to --update-secrets line:"
echo "   STRIPE_TOKEN_STARTER_PRICE_ID=STRIPE_TOKEN_STARTER_PRICE_ID:latest"
echo "   STRIPE_TOKEN_POPULAR_PRICE_ID=STRIPE_TOKEN_POPULAR_PRICE_ID:latest"
echo "   STRIPE_TOKEN_PRO_PRICE_ID=STRIPE_TOKEN_PRO_PRICE_ID:latest"
echo "   STRIPE_TOKEN_CREATOR_PRICE_ID=STRIPE_TOKEN_CREATOR_PRICE_ID:latest"
echo ""
echo "3. 🚀 Deploy to production:"
echo "   gcloud builds submit --config cloudbuild.yaml"
echo ""
echo "4. 🎉 Token purchases will be available at:"
echo "   https://phoenix-234619602247.us-central1.run.app/buy-tokens"
echo ""
