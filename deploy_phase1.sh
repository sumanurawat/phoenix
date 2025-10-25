#!/bin/bash
# Phase 1 Commit & Push Script
# Run after verifying all three milestones are green

set -e  # Exit on error

echo "🚀 Phase 1 Deployment Script"
echo "============================"
echo ""

# Stage all changes
echo "📦 Staging changes..."
git add firestore.rules app.py cloudbuild*.yaml config/settings.py requirements.txt \
        services/website_stats_service.py api/image_routes.py \
        services/image_generation_service.py services/post_service.py \
        services/like_service.py services/token_service.py \
        services/transaction_service.py templates/image_generator.html \
        static/js/image_generator.js test_r2_upload.py test_image_generation.py \
        PHASE1_TEST_REPORT.md R2_INTEGRATION_COMPLETE.md IMAGE_GENERATION*.md \
        R2_MIGRATION_GUIDE.md SOCIAL_PLATFORM_PROGRESS.md

echo "✅ Files staged"
echo ""

# Show what will be committed
echo "📋 Files to commit:"
git status --short
echo ""

# Confirm
read -p "Continue with commit? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ Aborted"
    exit 1
fi

# Commit
echo "💾 Creating commit..."
git commit -m "feat(phase1): AI social platform foundation - Imagen + R2 + secure Firestore

- Image generation with Google Imagen 3 (portrait, low safety filters)
- Cloudflare R2 storage integration (\$0 egress for viral scalability)
- Hardened Firestore security rules (user-scoped posts, likes, transactions)
- Token economy services (wallet, ledger, tips)
- Social platform primitives (posts, likes, feeds)
- Production logging and error handling
- Comprehensive test suites for R2 and Imagen

Phase 1 milestones: ✅ R2 storage | ✅ Firestore vault | ✅ Imagen API
Test evidence: PHASE1_TEST_REPORT.md"

echo "✅ Commit created"
echo ""

# Push
echo "🚢 Pushing to origin/main (will trigger Cloud Build)..."
read -p "Push to production? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ Push cancelled (commit saved locally)"
    exit 1
fi

git push origin main

echo ""
echo "🎉 Phase 1 deployed successfully!"
echo ""
echo "📊 Monitor deployment:"
echo "   Cloud Build: https://console.cloud.google.com/cloud-build/builds?project=phoenix-project-386"
echo "   Cloud Run: https://console.cloud.google.com/run/detail/us-central1/phoenix/metrics?project=phoenix-project-386"
echo ""
echo "🧪 After deployment, test:"
echo "   Production: https://phoenix-234619602247.us-central1.run.app/image-generator"
echo "   Dev: https://phoenix-dev-234619602247.us-central1.run.app/image-generator"
