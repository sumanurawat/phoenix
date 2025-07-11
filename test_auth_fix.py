#!/usr/bin/env python3
"""
Test script to verify the deployed service with authentication fixes.
"""
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://phoenix-hpbuj2rr6q-uc.a.run.app"

def test_fixed_authentication():
    """Test the fixed authentication behavior."""
    logger.info("=== Testing Fixed Authentication Behavior ===")
    
    try:
        # Test chat API without authentication
        url = f"{BASE_URL}/api/chat/message"
        headers = {'Content-Type': 'application/json'}
        data = {'message': 'Hello, test message'}
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Content Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        if response.status_code == 401:
            try:
                json_response = response.json()
                logger.info(f"✅ FIXED: Now returns proper JSON error: {json_response}")
                if 'error' in json_response and 'Authentication required' in json_response['error']:
                    logger.info("✅ Error message is correct")
                if 'redirect' in json_response:
                    logger.info(f"✅ Redirect URL provided: {json_response['redirect']}")
                return True
            except json.JSONDecodeError:
                logger.error("❌ Still returning non-JSON response")
                logger.error(f"Response: {response.text[:200]}...")
                return False
        else:
            logger.error(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def main():
    """Main test function."""
    logger.info("🔧 Testing Authentication Fix")
    logger.info("=" * 40)
    
    # Wait a moment for deployment
    import time
    logger.info("⏳ Waiting for deployment to complete...")
    time.sleep(30)
    
    success = test_fixed_authentication()
    
    if success:
        logger.info("🎉 AUTHENTICATION FIX SUCCESSFUL!")
        logger.info("The API now returns proper JSON errors instead of HTML")
        logger.info("Frontend should no longer get JSON parsing errors")
    else:
        logger.error("❌ Fix not yet deployed or still has issues")
    
    logger.info("=" * 40)

if __name__ == "__main__":
    main()
