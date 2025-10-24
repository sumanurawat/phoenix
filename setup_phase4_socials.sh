#!/bin/bash

# Social Gallery Phase 4 - Quick Setup Script

echo "======================================"
echo "  Social Gallery Phase 4 Setup"
echo "======================================"
echo ""

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Virtual environment not active!"
    echo "Please run: source venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment active: $VIRTUAL_ENV"
echo ""

# Install instaloader
echo "📦 Installing instaloader..."
pip install instaloader==4.13

if [ $? -eq 0 ]; then
    echo "✅ instaloader installed successfully!"
else
    echo "❌ Failed to install instaloader"
    exit 1
fi

echo ""
echo "======================================"
echo "  Setup Complete! 🎉"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Restart your Flask server:"
echo "   ./start_local.sh"
echo ""
echo "2. Navigate to: http://localhost:8080/socials"
echo ""
echo "3. Click the sync button (🔄) on your Instagram account"
echo ""
echo "4. See docs/social_gallery/PHASE_4_COMPLETE.md for full testing guide"
echo ""
