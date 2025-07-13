#!/usr/bin/env python3
"""
Debug script for Kaggle API integration.
Helps diagnose issues with the Dataset Discovery feature.
"""
import os
import sys
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_kaggle_import():
    """Test if kaggle package can be imported."""
    print("🧪 Testing Kaggle package import...")
    try:
        import kaggle
        print("✅ Kaggle package imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import kaggle package: {e}")
        return False

def test_credentials():
    """Test if Kaggle credentials are available."""
    print("\n🔑 Testing Kaggle credentials...")
    
    username = os.getenv('KAGGLE_USERNAME')
    key = os.getenv('KAGGLE_KEY')
    
    if not username:
        print("❌ KAGGLE_USERNAME not found in environment")
        return False
    
    if not key:
        print("❌ KAGGLE_KEY not found in environment")
        return False
    
    print(f"✅ KAGGLE_USERNAME: {username}")
    print(f"✅ KAGGLE_KEY: {key[:8]}..." if len(key) > 8 else f"✅ KAGGLE_KEY: {key}")
    return True

def test_kaggle_authentication():
    """Test direct Kaggle API authentication."""
    print("\n🔐 Testing Kaggle API authentication...")
    
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        
        api = KaggleApi()
        
        # Set credentials manually
        username = os.getenv('KAGGLE_USERNAME')
        key = os.getenv('KAGGLE_KEY')
        
        api.username = username
        api.key = key
        
        # Test authentication
        api.authenticate()
        print("✅ Kaggle API authentication successful")
        return api
        
    except Exception as e:
        print(f"❌ Kaggle API authentication failed: {e}")
        print(f"Full error: {traceback.format_exc()}")
        return None

def test_simple_search(api):
    """Test a simple dataset search."""
    print("\n🔍 Testing simple dataset search...")
    
    if not api:
        print("❌ Skipping search test - no authenticated API")
        return False
    
    try:
        # Test with a simple query
        print("Searching for 'covid' datasets...")
        datasets = list(api.dataset_list(search='covid', max_size=5))
        
        print(f"✅ Search successful! Found {len(datasets)} datasets")
        
        if datasets:
            print("\n📊 First result:")
            first = datasets[0]
            print(f"   Title: {first.title}")
            print(f"   Ref: {first.ref}")
            print(f"   Size: {getattr(first, 'totalBytes', 'unknown')} bytes")
            print(f"   Downloads: {getattr(first, 'downloadCount', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        print(f"Full error: {traceback.format_exc()}")
        return False

def test_dataset_files(api):
    """Test dataset file listing."""
    print("\n📁 Testing dataset file listing...")
    
    if not api:
        print("❌ Skipping file test - no authenticated API")
        return False
    
    try:
        # Test with a well-known dataset
        print("Getting files for 'alexandrec/world-happiness-report'...")
        files = list(api.dataset_list_files('alexandrec', 'world-happiness-report'))
        
        print(f"✅ File listing successful! Found {len(files)} files")
        
        if files:
            print("\n📄 Files:")
            for file in files[:3]:  # Show first 3 files
                print(f"   - {file.name} ({getattr(file, 'size', 'unknown')} bytes)")
        
        return True
        
    except Exception as e:
        print(f"❌ File listing failed: {e}")
        print(f"Full error: {traceback.format_exc()}")
        return False

def test_phoenix_service():
    """Test Phoenix dataset discovery service."""
    print("\n🐦 Testing Phoenix Dataset Discovery Service...")
    
    try:
        # Add Phoenix to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from services.dataset_discovery.config import DatasetConfig
        from services.dataset_discovery.kaggle_service import KaggleSearchService
        
        print("✅ Phoenix services imported successfully")
        
        # Test config
        config = DatasetConfig()
        print("✅ Configuration created")
        
        # Test Kaggle service
        kaggle_service = KaggleSearchService(config)
        print("✅ Kaggle service created")
        
        # Test authentication
        kaggle_service.authenticate()
        print("✅ Service authentication successful")
        
        # Test search
        print("🔍 Testing service search...")
        results = kaggle_service.search_datasets("covid", limit=3)
        print(f"✅ Service search successful! Found {len(results)} results")
        
        if results:
            print("\n📊 First result:")
            first = results[0]
            print(f"   Title: {first.get('title', 'N/A')}")
            print(f"   Ref: {first.get('ref', 'N/A')}")
            print(f"   Owner: {first.get('ownerName', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phoenix service test failed: {e}")
        print(f"Full error: {traceback.format_exc()}")
        return False

def main():
    """Run all debug tests."""
    print("🔧 Kaggle API Debug Tool")
    print("=" * 50)
    
    tests = [
        test_kaggle_import,
        test_credentials,
        test_kaggle_authentication,
    ]
    
    api = None
    
    # Run basic tests
    for test in tests:
        if not test():
            print(f"\n❌ Test {test.__name__} failed. Stopping here.")
            return False
        
        # Capture the API instance from authentication test
        if test.__name__ == 'test_kaggle_authentication':
            try:
                from kaggle.api.kaggle_api_extended import KaggleApi
                api = KaggleApi()
                api.username = os.getenv('KAGGLE_USERNAME')
                api.key = os.getenv('KAGGLE_KEY')
                api.authenticate()
            except:
                pass
    
    # Run advanced tests
    test_simple_search(api)
    test_dataset_files(api)
    test_phoenix_service()
    
    print("\n" + "=" * 50)
    print("🎯 Debug Summary:")
    print("If all tests passed, the Kaggle integration should work.")
    print("If any tests failed, check the error messages above.")
    print("\n📝 Common issues:")
    print("1. Invalid credentials - check KAGGLE_USERNAME and KAGGLE_KEY")
    print("2. Network issues - check internet connection")
    print("3. Kaggle API rate limits - wait and try again")
    print("4. Package issues - try: pip install --upgrade kaggle")

if __name__ == "__main__":
    main()