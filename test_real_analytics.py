#!/usr/bin/env python3
"""
Firebase-enabled analytics test to identify the template rendering issue.
"""

import os
import sys
sys.path.insert(0, '/Users/sumanurawat/Documents/GitHub/phoenix')

import firebase_admin
from firebase_admin import credentials

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate('/Users/sumanurawat/Documents/GitHub/phoenix/config/deeplink-27a12-firebase-adminsdk-7vgp4-f90013ed19.json')
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully")
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        sys.exit(1)

def test_analytics_service():
    """Test the analytics service with real data."""
    
    print("=== Testing Real Analytics Service ===")
    
    try:
        from services.click_tracking_service import ClickTrackingService
        
        click_service = ClickTrackingService()
        short_code = "8a1ab7"  # Known short code from conversation
        
        print(f"Testing analytics for short_code: {short_code}")
        
        # Call the exact method that the route uses
        analytics = click_service.get_click_analytics(short_code)
        
        print(f"Service returned: {analytics}")
        print(f"Type: {type(analytics)}")
        
        if isinstance(analytics, dict):
            print(f"Keys: {list(analytics.keys())}")
            print(f"total_clicks: {analytics.get('total_clicks', 'MISSING')}")
            print(f"total_clicks type: {type(analytics.get('total_clicks'))}")
            print(f"total_clicks == 0: {analytics.get('total_clicks') == 0}")
            
            # Test all keys
            for key, value in analytics.items():
                print(f"  {key}: {value} ({type(value)})")
        else:
            print("❌ Analytics is not a dictionary!")
            
        # Test template-like access
        try:
            total_clicks = analytics.get('total_clicks', 0)
            condition_result = total_clicks == 0
            print(f"Template condition simulation: {condition_result}")
            
            if condition_result:
                print("🔍 This would show 'No Click Data Yet' in template")
            else:
                print("✅ This would show analytics data in template")
                
        except Exception as e:
            print(f"❌ Template access simulation failed: {e}")
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analytics_service()
