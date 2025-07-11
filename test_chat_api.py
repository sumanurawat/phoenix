#!/usr/bin/env python3
"""
Test script to verify the chat API endpoints and authentication.
This will help debug the Derplexity frontend issue.
"""
import requests
import json
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://phoenix-hpbuj2rr6q-uc.a.run.app"
LOCAL_URL = "http://localhost:5000"

def test_health_check(base_url):
    """Test if the service is running."""
    logger.info(f"=== Testing Health Check: {base_url} ===")
    
    try:
        response = requests.get(base_url, timeout=10)
        logger.info(f"✓ Status Code: {response.status_code}")
        logger.info(f"✓ Content Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        if response.status_code == 200:
            logger.info("✓ Service is running")
            return True
        else:
            logger.warning(f"⚠ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return False

def test_derplexity_page(base_url):
    """Test if the Derplexity page loads."""
    logger.info("=== Testing Derplexity Page ===")
    
    try:
        url = urljoin(base_url, "/derplexity")
        response = requests.get(url, timeout=10)
        
        logger.info(f"✓ Status Code: {response.status_code}")
        logger.info(f"✓ Content Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        if response.status_code == 200:
            # Check if it's HTML
            if 'text/html' in response.headers.get('Content-Type', ''):
                logger.info("✓ Derplexity page loads successfully")
                # Check for key elements
                if 'derplexity' in response.text.lower():
                    logger.info("✓ Page contains Derplexity content")
                return True
            else:
                logger.warning("⚠ Response is not HTML")
                return False
        else:
            logger.error(f"✗ Failed to load page: {response.status_code}")
            logger.error(f"Response: {response.text[:200]}...")
            return False
    except Exception as e:
        logger.error(f"✗ Failed to test Derplexity page: {e}")
        return False

def test_chat_api_without_auth(base_url):
    """Test the chat API without authentication."""
    logger.info("=== Testing Chat API (No Auth) ===")
    
    try:
        url = urljoin(base_url, "/api/chat/message")
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            'message': 'Hello, this is a test message'
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        logger.info(f"✓ Status Code: {response.status_code}")
        logger.info(f"✓ Content Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        # Log response content
        try:
            if 'application/json' in response.headers.get('Content-Type', ''):
                json_response = response.json()
                logger.info(f"✓ JSON Response: {json.dumps(json_response, indent=2)}")
            else:
                logger.info(f"✓ Text Response: {response.text[:300]}...")
        except:
            logger.info(f"✓ Raw Response: {response.text[:300]}...")
        
        if response.status_code == 401:
            logger.info("✓ Correctly returns 401 (Unauthorized) - authentication required")
            return True
        elif response.status_code == 200:
            logger.warning("⚠ Unexpected 200 status - should require authentication")
            return False
        else:
            logger.error(f"✗ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Failed to test chat API: {e}")
        return False

def simulate_frontend_error(base_url):
    """Simulate the exact frontend error scenario."""
    logger.info("=== Simulating Frontend Error Scenario ===")
    
    try:
        # This mimics what the frontend JavaScript does
        url = urljoin(base_url, "/api/chat/message")
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            'message': 'Test message from simulation'
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Content Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        # Check if response starts with <!DOCTYPE (the error mentioned)
        response_text = response.text
        if response_text.startswith('<!DOCTYPE'):
            logger.error("✗ FOUND THE ISSUE: API returning HTML instead of JSON")
            logger.error("This matches the frontend error: 'Unexpected token '<', \"<!DOCTYPE \"... is not valid JSON'")
            logger.info("Response preview:")
            logger.info(response_text[:200] + "...")
            
            # Check if it's a login/auth page
            if 'login' in response_text.lower() or 'auth' in response_text.lower():
                logger.error("→ The API is redirecting to a login page")
                logger.error("→ This indicates authentication is not working properly")
            
            return False
        else:
            try:
                json_response = response.json()
                logger.info(f"✓ Valid JSON response: {json.dumps(json_response, indent=2)}")
                return True
            except json.JSONDecodeError:
                logger.error(f"✗ Invalid JSON response: {response_text[:200]}...")
                return False
                
    except Exception as e:
        logger.error(f"✗ Failed to simulate frontend error: {e}")
        return False

def check_authentication_flow(base_url):
    """Check the authentication flow."""
    logger.info("=== Checking Authentication Flow ===")
    
    try:
        # Try to access a page that might show auth status
        session = requests.Session()
        
        # First, try to get the main page
        response = session.get(base_url, timeout=10)
        logger.info(f"Main page status: {response.status_code}")
        
        # Check for Firebase auth or other auth indicators
        if 'firebase' in response.text.lower():
            logger.info("✓ Firebase authentication detected")
        
        # Check cookies/session
        cookies = session.cookies.get_dict()
        if cookies:
            logger.info(f"✓ Cookies set: {list(cookies.keys())}")
        else:
            logger.info("⚠ No cookies set")
        
        # Try the derplexity page with the session
        derplexity_response = session.get(urljoin(base_url, "/derplexity"), timeout=10)
        logger.info(f"Derplexity page status: {derplexity_response.status_code}")
        
        # Try the API with the session
        api_response = session.post(
            urljoin(base_url, "/api/chat/message"),
            json={'message': 'test'},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        logger.info(f"API status with session: {api_response.status_code}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to check authentication flow: {e}")
        return False

def main():
    """Main test function."""
    logger.info("🔍 Starting Chat API and Authentication Test")
    logger.info("=" * 60)
    
    # Test both remote and local if available
    urls_to_test = [BASE_URL]
    
    for base_url in urls_to_test:
        logger.info(f"\n🌐 Testing: {base_url}")
        logger.info("-" * 40)
        
        # Basic health check
        if not test_health_check(base_url):
            logger.error(f"Skipping further tests for {base_url}")
            continue
        
        print()
        
        # Test Derplexity page
        test_derplexity_page(base_url)
        print()
        
        # Test chat API without auth
        test_chat_api_without_auth(base_url)
        print()
        
        # Simulate the exact frontend error
        simulate_frontend_error(base_url)
        print()
        
        # Check authentication flow
        check_authentication_flow(base_url)
        print()
    
    logger.info("=" * 60)
    logger.info("🏁 Test completed!")
    
    logger.info("\n💡 DEBUGGING TIPS:")
    logger.info("1. If API returns HTML instead of JSON, check authentication")
    logger.info("2. If getting 401 errors, verify Firebase auth is working")
    logger.info("3. Check browser dev tools Network tab for actual requests")
    logger.info("4. Verify session cookies are being set properly")

if __name__ == "__main__":
    main()
