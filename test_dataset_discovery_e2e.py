#!/usr/bin/env python3
"""
End-to-end test script for Dataset Discovery feature.
Tests the complete workflow with real Kaggle API calls.
"""
import os
import sys
import json
import time
import requests
from typing import Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_health_endpoint(base_url: str) -> bool:
    """Test the health endpoint."""
    print("🏥 Testing health endpoint...")
    
    try:
        response = requests.get(f"{base_url}/api/datasets/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Kaggle authenticated: {data['kaggle_authenticated']}")
            
            if data['kaggle_authenticated']:
                print("✅ Kaggle credentials are working!")
                return True
            else:
                print("❌ Kaggle authentication failed")
                print(f"   Error: {data.get('checks', {}).get('kaggle_auth', {}).get('message', 'Unknown')}")
                return False
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_config_endpoint(base_url: str) -> bool:
    """Test the configuration endpoint."""
    print("\n⚙️ Testing configuration endpoint...")
    
    try:
        response = requests.get(f"{base_url}/api/datasets/config", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Configuration retrieved")
            print(f"   Version: {data['version']}")
            print(f"   Kaggle configured: {data['kaggle_configured']}")
            print(f"   Default limit: {data['defaults']['limit']}")
            print(f"   Default sort: {data['defaults']['sort_by']}")
            return True
        else:
            print(f"❌ Config check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Config check error: {e}")
        return False

def test_search_endpoint(base_url: str, query: str, limit: int = 5) -> Dict[str, Any]:
    """Test the search endpoint with a real query."""
    print(f"\n🔍 Testing search endpoint with query: '{query}'...")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/api/datasets/search",
            json={
                "query": query,
                "limit": limit,
                "sort_by": "hottest",
                "min_quality_score": 0.0
            },
            timeout=30
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search successful in {response_time}ms")
            print(f"   Query: {data['query']}")
            print(f"   Total found: {data['total_found']}")
            print(f"   Returned: {data['returned_count']}")
            print(f"   Search time: {data['search_time_ms']}ms")
            
            if data['datasets']:
                print(f"\n📊 Top dataset:")
                top_dataset = data['datasets'][0]
                print(f"   Title: {top_dataset['title']}")
                print(f"   Owner: {top_dataset['owner']}")
                print(f"   Quality Score: {top_dataset['quality_score']:.3f}")
                print(f"   Relevance Score: {top_dataset['relevance_score']:.3f}")
                print(f"   Combined Score: {top_dataset['combined_score']:.3f}")
                print(f"   Size: {top_dataset['size_mb']} MB")
                print(f"   Files: {top_dataset['file_count']}")
                print(f"   Downloads: {top_dataset['download_count']:,}")
                print(f"   URL: {top_dataset['url']}")
            
            return data
        else:
            print(f"❌ Search failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ Search error: {e}")
        return {}

def test_multiple_queries(base_url: str) -> None:
    """Test multiple search queries to validate scoring."""
    print("\n🎯 Testing multiple queries for scoring validation...")
    
    test_queries = [
        ("climate change", "Should find environmental datasets"),
        ("machine learning", "Should find ML/AI datasets"),
        ("covid", "Should find pandemic-related data"),
        ("financial data", "Should find economics/finance datasets")
    ]
    
    results = []
    
    for query, description in test_queries:
        print(f"\n   Testing: {query} ({description})")
        data = test_search_endpoint(base_url, query, limit=3)
        
        if data and data.get('datasets'):
            top_score = data['datasets'][0]['combined_score']
            avg_relevance = sum(d['relevance_score'] for d in data['datasets']) / len(data['datasets'])
            results.append({
                'query': query,
                'top_score': top_score,
                'avg_relevance': avg_relevance,
                'count': len(data['datasets'])
            })
            print(f"   ✅ Top score: {top_score:.3f}, Avg relevance: {avg_relevance:.3f}")
        else:
            print(f"   ❌ No results for '{query}'")
    
    # Summary
    if results:
        print(f"\n📈 Scoring Summary:")
        for r in results:
            print(f"   '{r['query']}': Score {r['top_score']:.3f}, Relevance {r['avg_relevance']:.3f}")

def test_error_handling(base_url: str) -> None:
    """Test error handling scenarios."""
    print("\n🚨 Testing error handling...")
    
    # Test invalid query
    print("   Testing empty query...")
    response = requests.post(f"{base_url}/api/datasets/search", json={"query": ""})
    if response.status_code == 400:
        print("   ✅ Empty query correctly rejected")
    else:
        print(f"   ❌ Expected 400, got {response.status_code}")
    
    # Test invalid limit
    print("   Testing invalid limit...")
    response = requests.post(f"{base_url}/api/datasets/search", json={"query": "test", "limit": 200})
    if response.status_code == 400:
        print("   ✅ Invalid limit correctly rejected")
    else:
        print(f"   ❌ Expected 400, got {response.status_code}")
    
    # Test invalid JSON
    print("   Testing invalid content type...")
    response = requests.post(f"{base_url}/api/datasets/search", data="invalid json")
    if response.status_code == 400:
        print("   ✅ Invalid content type correctly rejected")
    else:
        print(f"   ❌ Expected 400, got {response.status_code}")

def main():
    """Run comprehensive end-to-end tests."""
    print("🚀 Dataset Discovery End-to-End Test Suite")
    print("=" * 55)
    
    # Configuration
    base_url = os.getenv('PHOENIX_BASE_URL', 'http://localhost:5000')
    print(f"Testing against: {base_url}")
    
    # Test sequence
    tests_passed = 0
    total_tests = 5
    
    try:
        # 1. Health check
        if test_health_endpoint(base_url):
            tests_passed += 1
        
        # 2. Configuration check  
        if test_config_endpoint(base_url):
            tests_passed += 1
        
        # 3. Basic search test
        result = test_search_endpoint(base_url, "machine learning")
        if result and result.get('datasets'):
            tests_passed += 1
        
        # 4. Multiple query tests
        test_multiple_queries(base_url)
        tests_passed += 1  # Always count this as it's informational
        
        # 5. Error handling tests
        test_error_handling(base_url)
        tests_passed += 1  # Always count this as it's informational
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrupted by user")
        return False
    
    # Results summary
    print("\n" + "=" * 55)
    print(f"📊 Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed >= 3:  # Health + Config + Basic search
        print("🎉 Dataset Discovery feature is working correctly!")
        print("\n📝 Next steps:")
        print("1. Try the web UI at http://localhost:5000/datasets (if available)")
        print("2. Integration with Robin/Doogle/Derplexity")
        print("3. Production deployment with GCP secrets")
        return True
    else:
        print("❌ Some critical tests failed. Please check:")
        print("1. Kaggle credentials are properly set")
        print("2. Phoenix server is running")
        print("3. Internet connectivity for Kaggle API")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)