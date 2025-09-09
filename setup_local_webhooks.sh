#!/bin/bash
# Phoenix AI - Local Webhook Setup Script

echo "🚀 Setting up Stripe webhook forwarding for local development"
echo "=================================================="
echo ""

# Check if Stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI is not installed!"
    echo ""
    echo "Please install it first:"
    echo "  Mac: brew install stripe/stripe-cli/stripe"
    echo "  Or download from: https://github.com/stripe/stripe-cli/releases"
    exit 1
fi

echo "✅ Stripe CLI found"
echo ""

# Get the local port
PORT=${1:-8080}
echo "📍 Using local port: $PORT"
echo ""

# Login to Stripe (if needed)
echo "🔐 Checking Stripe authentication..."
stripe login --interactive false 2>/dev/null || {
    echo "Please login to Stripe:"
    stripe login
}

echo ""
echo "🎯 Starting webhook forwarding..."
echo "This will forward Stripe webhooks to your local server"
echo ""
echo "IMPORTANT: Keep this terminal open while testing!"
echo "=================================================="
echo ""

# Forward webhooks to local server
stripe listen --forward-to localhost:$PORT/api/stripe/webhook \
    --events checkout.session.completed,customer.subscription.updated,customer.subscription.deleted,invoice.payment_failed

# The command above will output a webhook signing secret like:
# Ready! Your webhook signing secret is whsec_xxxxx
# Copy that secret and update your .env file with it!