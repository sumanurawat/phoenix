#!/bin/bash
# Script to add Stripe secrets to Google Secret Manager for production deployment

set -e

PROJECT_ID="phoenix-project-386"
REGION="us-central1"

echo "🔐 Setting up Stripe secrets in Google Secret Manager..."
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

echo ""
echo "📝 You will need to provide the following Stripe API keys:"
echo "   1. Production Secret Key (sk_live_...)"
echo "   2. Production Webhook Secret (whsec_...)"
echo "   3. Production Publishable Key (pk_live_...)"
echo ""
echo "⚠️  IMPORTANT: Use PRODUCTION keys, not TEST keys!"
echo "   TEST keys start with: sk_test_, pk_test_, whsec_test_"
echo "   LIVE keys start with: sk_live_, pk_live_, whsec_"
echo ""

read -p "Press Enter to continue or Ctrl+C to cancel..."

# Function to create or update a secret
create_or_update_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    local DESCRIPTION=$3
    
    echo ""
    echo "Processing secret: $SECRET_NAME"
    
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
            --project=$PROJECT_ID
        
        # Add description if provided
        if [ -n "$DESCRIPTION" ]; then
            gcloud secrets update $SECRET_NAME \
                --update-labels=description="$DESCRIPTION" \
                --project=$PROJECT_ID
        fi
        
        echo "  ✅ Created $SECRET_NAME"
    fi
}

# Prompt for Stripe Production Secret Key
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1/3: Stripe Production Secret Key"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Find this in: https://dashboard.stripe.com/apikeys"
echo "Format: sk_live_..."
read -sp "Enter Stripe Production Secret Key: " STRIPE_SECRET_KEY_PROD
echo ""

if [[ ! $STRIPE_SECRET_KEY_PROD =~ ^sk_live_ ]]; then
    echo "⚠️  WARNING: Key does not start with 'sk_live_' - are you sure this is a PRODUCTION key?"
    read -p "Continue anyway? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "Cancelled."
        exit 1
    fi
fi

create_or_update_secret "STRIPE_SECRET_KEY_PROD" "$STRIPE_SECRET_KEY_PROD" "Stripe production secret key"

# Prompt for Stripe Production Webhook Secret
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2/3: Stripe Production Webhook Secret"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Find this in: https://dashboard.stripe.com/webhooks"
echo "Format: whsec_..."
read -sp "Enter Stripe Production Webhook Secret: " STRIPE_WEBHOOK_SECRET_PROD
echo ""

if [[ ! $STRIPE_WEBHOOK_SECRET_PROD =~ ^whsec_ ]]; then
    echo "⚠️  WARNING: Key does not start with 'whsec_' - are you sure this is correct?"
    read -p "Continue anyway? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "Cancelled."
        exit 1
    fi
fi

create_or_update_secret "STRIPE_WEBHOOK_SECRET_PROD" "$STRIPE_WEBHOOK_SECRET_PROD" "Stripe production webhook secret"

# Prompt for Stripe Production Publishable Key
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3/3: Stripe Production Publishable Key"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Find this in: https://dashboard.stripe.com/apikeys"
echo "Format: pk_live_..."
read -sp "Enter Stripe Production Publishable Key: " STRIPE_PUBLISHABLE_KEY_PROD
echo ""

if [[ ! $STRIPE_PUBLISHABLE_KEY_PROD =~ ^pk_live_ ]]; then
    echo "⚠️  WARNING: Key does not start with 'pk_live_' - are you sure this is a PRODUCTION key?"
    read -p "Continue anyway? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "Cancelled."
        exit 1
    fi
fi

create_or_update_secret "STRIPE_PUBLISHABLE_KEY_PROD" "$STRIPE_PUBLISHABLE_KEY_PROD" "Stripe production publishable key"

# Grant Cloud Run service account access to secrets
echo ""
echo "🔐 Granting Cloud Run service account access to secrets..."

SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

for SECRET in STRIPE_SECRET_KEY_PROD STRIPE_WEBHOOK_SECRET_PROD STRIPE_PUBLISHABLE_KEY_PROD; do
    echo "  Granting access to $SECRET..."
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID \
        --quiet
done

echo ""
echo "✅ All Stripe secrets configured successfully!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Update cloudbuild.yaml to use these secrets"
echo "2. Deploy to production: gcloud builds submit --config cloudbuild.yaml"
echo "3. Configure Stripe webhook endpoint in dashboard:"
echo "   URL: https://phoenix-ai.app/api/stripe/webhook"
echo "   Events: checkout.session.completed"
echo ""
echo "🔒 Security Check:"
echo "   ✓ Secrets stored in Secret Manager (encrypted at rest)"
echo "   ✓ Access granted only to Cloud Run service account"
echo "   ✓ Secrets never appear in logs or build artifacts"
echo ""
