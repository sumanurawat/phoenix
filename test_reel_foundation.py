#!/usr/bin/env python3
"""
Quick test script for the reel maker backend foundation.
Run this after ./start_local.sh to test the API endpoints.
"""
import requests
import json

BASE_URL = "http://localhost:8080"

def test_health_endpoint():
    """Test the health check endpoint (no auth required)."""
    try:
        response = requests.get(f"{BASE_URL}/api/reel/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_projects_endpoint_no_auth():
    """Test projects endpoint without authentication (should fail)."""
    try:
        response = requests.get(f"{BASE_URL}/api/reel/projects")
        print(f"Projects (no auth): {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 302  # Expect redirect to login
    except Exception as e:
        print(f"Projects test failed: {e}")
        return False

def main():
    print("🧪 Testing Reel Maker Backend Foundation")
    print("=" * 50)
    
    print("\n1. Testing health endpoint...")
    health_ok = test_health_endpoint()
    
    print("\n2. Testing authentication protection...")
    auth_ok = test_projects_endpoint_no_auth()
    
    print("\n" + "=" * 50)
    if health_ok and auth_ok:
        print("✅ Basic backend foundation is working!")
        print("\n📋 Next steps for manual testing:")
        print("1. Visit http://localhost:8080 and log in")
        print("2. Open browser dev tools (F12)")
        print("3. Run in console:")
        print("   fetch('/api/reel/projects').then(r => r.json()).then(console.log)")
        print("4. Should return: {success: true, projects: [], count: 0}")
        print("\n5. Test project creation:")
        print("   fetch('/api/reel/projects', {")
        print("     method: 'POST',")
        print("     headers: {'Content-Type': 'application/json'},")
        print("     body: JSON.stringify({title: 'Test Project'})")
        print("   }).then(r => r.json()).then(console.log)")
    else:
        print("❌ Some tests failed. Check server logs.")

if __name__ == "__main__":
    main()