#!/usr/bin/env python3
"""
Test script to debug geolocation and IP detection issues.
"""

import sys
sys.path.append('/Users/sumanurawat/Documents/GitHub/phoenix')

import os
import firebase_admin
from firebase_admin import credentials
from services.geolocation_service import GeolocationService
from services.click_tracking_service import ClickTrackingService

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('/Users/sumanurawat/Documents/GitHub/phoenix/firebase-credentials.json')
    firebase_admin.initialize_app(cred)

def test_geolocation():
    """Test geolocation functionality."""
    
    print("=== Testing Geolocation Service ===")
    
    geo_service = GeolocationService()
    
    # Test with various IP addresses
    test_ips = [
        "127.0.0.1",  # localhost - should return Unknown
        "8.8.8.8",    # Google DNS - should return US location
        "1.1.1.1",    # Cloudflare - should return US location
        "192.168.1.1" # Private IP - should return Unknown
    ]
    
    for ip in test_ips:
        print(f"\n--- Testing IP: {ip} ---")
        try:
            location = geo_service.get_location_from_ip(ip)
            print(f"Location result: {location}")
            
            if location:
                display = geo_service.get_location_display(location)
                print(f"Display format: {display}")
            else:
                print("No location data returned")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

def test_ip_extraction():
    """Test IP extraction from request data."""
    
    print("\n=== Testing IP Extraction ===")
    
    click_service = ClickTrackingService()
    
    # Simulate different request scenarios
    test_requests = [
        {
            'name': 'Local development',
            'data': {
                'remote_addr': '127.0.0.1',
                'user_agent': 'Mozilla/5.0 (test)'
            }
        },
        {
            'name': 'Behind proxy',
            'data': {
                'X-Forwarded-For': '203.0.113.1, 192.168.1.1',
                'remote_addr': '192.168.1.1',
                'user_agent': 'Mozilla/5.0 (test)'
            }
        },
        {
            'name': 'Real IP header',
            'data': {
                'X-Real-IP': '203.0.113.1',
                'remote_addr': '192.168.1.1',
                'user_agent': 'Mozilla/5.0 (test)'
            }
        }
    ]
    
    for test in test_requests:
        print(f"\n--- {test['name']} ---")
        ip = click_service._get_client_ip(test['data'])
        print(f"Extracted IP: {ip}")
        
        if ip:
            try:
                geo_info = click_service._get_geolocation(ip)
                print(f"Geolocation result: {geo_info}")
            except Exception as e:
                print(f"Geolocation error: {e}")

def test_click_recording():
    """Test the full click recording process."""
    
    print("\n=== Testing Click Recording ===")
    
    click_service = ClickTrackingService()
    
    # Simulate a click with public IP
    test_request_data = {
        'remote_addr': '8.8.8.8',  # Use Google DNS for testing
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'referrer': 'http://127.0.0.1:8080/apps/deeplink/profile/links'
    }
    
    print("Recording test click with public IP...")
    
    try:
        # We won't actually record to avoid polluting data, just test the IP extraction and geolocation
        ip = click_service._get_client_ip(test_request_data)
        print(f"Extracted IP: {ip}")
        
        if ip:
            geo_info = click_service._get_geolocation(ip)
            print(f"Geolocation info: {geo_info}")
            
            if geo_info:
                print("✅ Geolocation would be added to click record!")
            else:
                print("❌ No geolocation data would be added")
        else:
            print("❌ No IP address extracted")
            
    except Exception as e:
        print(f"Error in click recording test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting geolocation debug tests...")
    try:
        test_geolocation()
        test_ip_extraction()
        test_click_recording()
        print("\nAll tests completed!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
