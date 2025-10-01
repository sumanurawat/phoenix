#!/bin/bash

# Quick setup helper for Reel Maker
# This script helps configure the necessary environment variables

set -e

echo "=== Reel Maker Configuration Helper ==="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "=== Configuration Status ==="
echo ""

# Check VIDEO_STORAGE_BUCKET
if grep -q "^VIDEO_STORAGE_BUCKET=.\+$" .env 2>/dev/null; then
    BUCKET_VALUE=$(grep "^VIDEO_STORAGE_BUCKET=" .env | cut -d '=' -f2)
    echo "✅ VIDEO_STORAGE_BUCKET is configured: $BUCKET_VALUE"
else
    echo "❌ VIDEO_STORAGE_BUCKET is NOT configured"
    echo ""
    echo "To configure, edit .env and set:"
    echo "VIDEO_STORAGE_BUCKET=your-bucket-name"
    echo ""
    echo "Need to create a bucket? Run:"
    echo "gcloud storage buckets create gs://your-bucket-name --location=US --uniform-bucket-level-access"
fi

echo ""

# Check GEMINI_API_KEY
if grep -q "^GEMINI_API_KEY=.\+$" .env 2>/dev/null; then
    echo "✅ GEMINI_API_KEY is configured"
else
    echo "⚠️  GEMINI_API_KEY is NOT configured (required for AI features)"
fi

# Check FIREBASE_API_KEY
if grep -q "^FIREBASE_API_KEY=.\+$" .env 2>/dev/null; then
    echo "✅ FIREBASE_API_KEY is configured"
else
    echo "⚠️  FIREBASE_API_KEY is NOT configured (required for authentication)"
fi

# Check firebase-credentials.json
if [ -f firebase-credentials.json ]; then
    echo "✅ firebase-credentials.json exists"
else
    echo "⚠️  firebase-credentials.json is missing (required for Firebase Admin SDK)"
fi

echo ""
echo "=== Next Steps ==="
echo ""

if ! grep -q "^VIDEO_STORAGE_BUCKET=.\+$" .env 2>/dev/null; then
    echo "1. Configure your GCS bucket in .env"
    echo "2. See REEL_MAKER_SETUP.md for detailed instructions"
    echo "3. Run ./start_local.sh to start the application"
else
    echo "Configuration looks good! Run ./start_local.sh to start the application."
fi

echo ""
