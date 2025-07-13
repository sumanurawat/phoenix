#!/usr/bin/env python3
"""
Debug script to examine dataset information from Kaggle API
to understand the file count and size issues.
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_kaggle_dataset_info():
    """Debug the raw dataset information from Kaggle API."""
    print("🔍 Debugging Kaggle Dataset Information...")
    
    try:
        from services.dataset_discovery.config import DatasetConfig
        from services.dataset_discovery.kaggle_service import KaggleSearchService
        from services.dataset_discovery.models import DatasetInfo
        
        # Initialize services
        config = DatasetConfig()
        service = KaggleSearchService(config)
        service.authenticate()
        
        # Search for a few datasets
        raw_results = service.search_datasets("population", limit=3)
        
        print(f"\n📊 Found {len(raw_results)} raw datasets")
        
        for i, raw_dataset in enumerate(raw_results):
            print(f"\n🔍 Dataset {i+1}:")
            print(f"   Title: {raw_dataset.get('title', 'N/A')}")
            print(f"   Ref: {raw_dataset.get('ref', 'N/A')}")
            
            # Show all available fields
            print("   📋 Available fields:")
            for key, value in raw_dataset.items():
                if key not in ['description']:  # Skip long description
                    print(f"      {key}: {value} ({type(value).__name__})")
            
            # Check specific size/file fields
            print("   📁 File/Size Info:")
            print(f"      totalBytes: {raw_dataset.get('totalBytes', 'Missing')}")
            print(f"      fileCount: {raw_dataset.get('fileCount', 'Missing')}")
            print(f"      file_count: {raw_dataset.get('file_count', 'Missing')}")
            print(f"      size: {raw_dataset.get('size', 'Missing')}")
            
            # Test conversion to DatasetInfo
            print("   🔄 Converting to DatasetInfo...")
            try:
                dataset_info = DatasetInfo.from_kaggle_dataset(raw_dataset, [])
                print(f"      Converted file_count: {dataset_info.file_count}")
                print(f"      Converted total_bytes: {dataset_info.total_bytes}")
                print(f"      Converted size_mb: {dataset_info.size_mb}")
            except Exception as e:
                print(f"      ❌ Conversion failed: {e}")
            
            print()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_kaggle_dataset_info()