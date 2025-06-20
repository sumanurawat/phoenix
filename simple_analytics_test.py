#!/usr/bin/env python3
"""
Simplified analytics test to identify the template rendering issue.
"""

import os
import sys
import json
sys.path.append('/Users/sumanurawat/Documents/GitHub/phoenix')

def simple_test():
    """Simple test without Firebase dependencies."""
    
    print("=== Testing Template Logic ===")
    print("Script is running...")
    
    try:
        # Simulate the analytics data structure from the service
        analytics = {
            'total_clicks': 5,
            'unique_visitors': 1,
            'top_countries': [('United States', 3), ('Canada', 2)],
            'device_breakdown': {'Desktop': 4, 'Mobile': 1},
            'browser_breakdown': {'Chrome': 5},
            'recent_clicks': []
        }
        
        print(f"Analytics object: {analytics}")
        print(f"Analytics type: {type(analytics)}")
        print(f"total_clicks value: {analytics.get('total_clicks')}")
        print(f"total_clicks type: {type(analytics.get('total_clicks'))}")
        print(f"total_clicks == 0: {analytics.get('total_clicks') == 0}")
        
        # Test the exact Jinja2 condition
        # The template uses: {% if analytics.total_clicks == 0 %}
        
        # In Python, this would be:
        condition_result = analytics['total_clicks'] == 0
        print(f"Python condition (analytics['total_clicks'] == 0): {condition_result}")
        
        # Test dot notation access
        class AnalyticsDict(dict):
            def __getattr__(self, key):
                return self[key]
        
        analytics_obj = AnalyticsDict(analytics)
        print(f"Dot notation access (analytics_obj.total_clicks): {analytics_obj.total_clicks}")
        print(f"Dot notation condition (analytics_obj.total_clicks == 0): {analytics_obj.total_clicks == 0}")
        
        # JSON serialization test (like Jinja2 might do)
        json_str = json.dumps(analytics)
        analytics_from_json = json.loads(json_str)
        print(f"From JSON: {analytics_from_json}")
        print(f"From JSON condition: {analytics_from_json['total_clicks'] == 0}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_test()
