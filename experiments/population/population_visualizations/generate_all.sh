#!/bin/bash

# 🌍 Population Visualization Generator
# This script regenerates all visualizations and saves them to the output/ directory

echo "🚀 Starting Population Visualization Generation"
echo "=" 60

# Set up environment
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Please create one with:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment (adjust path if needed)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment activation script not found"
    echo "   Make sure to activate your environment manually"
fi

echo ""
echo "🎯 Generating 2D Professional Visualizations..."
python main.py

echo ""
echo "🧠 Generating 3D TensorBoard-Style Demographic Clustering..."
python web3d/tensorboard_demographics.py

echo ""
echo "🌍 Generating 3D Migration Flows Globe..."
python web3d/migration_flows_3d.py

echo ""
echo "🏔️  Generating 3D Population Density Surface..."
python web3d/density_surface.py

echo ""
echo "=" 60
echo "🎉 ALL VISUALIZATIONS GENERATED!"
echo "=" 60
echo "📁 Output location: ./output/"
echo "🌐 Main showcase: ./output/web_exports/index.html"
echo "📊 2D charts: ./output/showcase_outputs/"
echo "🎯 3D visualizations: ./output/web_exports/"
echo ""
echo "💡 Open ./output/web_exports/index.html in your browser to view the complete showcase!"

# Open the main showcase if on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🚀 Opening showcase in browser..."
    open output/web_exports/index.html
fi
