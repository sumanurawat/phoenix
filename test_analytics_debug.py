#!/usr/bin/env python3
"""
Debug script to test analytics functionality and identify template rendering issue.
"""

import os
import sys
sys.path.append('/Users/sumanurawat/Documents/GitHub/phoenix')

import firebase_admin
from firebase_admin import credentials
from flask import Flask, session, render_template_string
from services.click_tracking_service import ClickTrackingService
from services.deeplink_service import DeeplinkService

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('/Users/sumanurawat/Documents/GitHub/phoenix/config/deeplink-27a12-firebase-adminsdk-7vgp4-f90013ed19.json')
    firebase_admin.initialize_app(cred)

def test_analytics_data():
    """Test the analytics data retrieval and template rendering."""
    
    print("=== Testing Analytics Data ===")
    
    try:
        # Initialize services
        print("Initializing services...")
        click_service = ClickTrackingService()
        deeplink_service = DeeplinkService()
        print("Services initialized successfully")
        
        short_code = "8a1ab7"
        user_id = "HlZNOXwSHwXllDJYqz2AcD4hk8p1"  # From session data
        
        # 1. Test click service data
        print("\n1. Testing ClickTrackingService.get_analytics()...")
        analytics = click_service.get_analytics(short_code)
        print(f"Analytics result: {analytics}")
        print(f"Type: {type(analytics)}")
        print(f"Analytics.total_clicks: {analytics.get('total_clicks')}")
        print(f"Analytics.total_clicks type: {type(analytics.get('total_clicks'))}")
        print(f"Analytics.total_clicks == 0: {analytics.get('total_clicks') == 0}")
        
        # 2. Test deeplink service
        print("\n2. Testing DeeplinkService.get_user_short_link()...")
        link = deeplink_service.get_user_short_link(user_id, short_code)
        print(f"Link found: {link is not None}")
        if link:
            print(f"Link title: {link.get('title')}")
            print(f"Link URL: {link.get('url')}")
        
        # 3. Test template rendering
        print("\n3. Testing template rendering...")
        template_test = """
Analytics Data Debug:
- analytics: {{ analytics }}
- analytics type: {{ analytics.__class__.__name__ if analytics else 'None' }}
- total_clicks: {{ analytics.total_clicks if analytics else 'N/A' }}
- total_clicks type: {{ analytics.total_clicks.__class__.__name__ if analytics and analytics.total_clicks is defined else 'N/A' }}
- total_clicks == 0: {{ analytics.total_clicks == 0 if analytics else 'N/A' }}
- total_clicks is 0: {{ analytics.total_clicks is 0 if analytics else 'N/A' }}

Condition Test:
{% if analytics and analytics.total_clicks == 0 %}
CONDITION TRUE: No click data
{% else %}
CONDITION FALSE: Has click data ({{ analytics.total_clicks if analytics else 'no analytics' }})
{% endif %}
"""
        
        # Create minimal Flask app to test template
        app = Flask(__name__)
        with app.app_context():
            rendered = render_template_string(template_test, analytics=analytics, link=link)
            print("Template output:")
            print(rendered)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analytics_data()
