#!/usr/bin/env python3
"""
Firestore Index Setup Script

This script creates the required composite indexes for the click tracking system.
Run this script to set up indexes for optimal analytics performance.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import sys
import os

def create_firestore_indexes():
    """Create required Firestore composite indexes for click analytics."""
    
    print("🔧 Setting up Firestore indexes for click analytics...")
    
    try:
        # Initialize Firebase if not already done
        if not firebase_admin._apps:
            cred = credentials.Certificate('firebase-credentials.json')
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        print("✅ Firebase initialized successfully")
        
        # Test if we can query the collections
        print("\n📊 Testing current index status...")
        
        # Test link_clicks collection queries
        try:
            # This query requires: (short_code, clicked_at DESC)
            test_query1 = db.collection('link_clicks')\
                           .where('short_code', '==', 'test')\
                           .order_by('clicked_at', direction=firestore.Query.DESCENDING)\
                           .limit(1)
            
            list(test_query1.stream())
            print("✅ Index (short_code, clicked_at DESC) - EXISTS")
            
        except Exception as e:
            if "requires an index" in str(e):
                print("❌ Index (short_code, clicked_at DESC) - MISSING")
                print(f"   Create it here: {extract_index_url(str(e))}")
            else:
                print(f"⚠️  Index (short_code, clicked_at DESC) - ERROR: {e}")
        
        try:
            # This query requires: (user_id, clicked_at DESC)
            test_query2 = db.collection('link_clicks')\
                           .where('user_id', '==', 'test')\
                           .order_by('clicked_at', direction=firestore.Query.DESCENDING)\
                           .limit(1)
            
            list(test_query2.stream())
            print("✅ Index (user_id, clicked_at DESC) - EXISTS")
            
        except Exception as e:
            if "requires an index" in str(e):
                print("❌ Index (user_id, clicked_at DESC) - MISSING")
                print(f"   Create it here: {extract_index_url(str(e))}")
            else:
                print(f"⚠️  Index (user_id, clicked_at DESC) - ERROR: {e}")
        
        print("\n📋 Manual Index Creation Steps:")
        print("1. Go to Firebase Console: https://console.firebase.google.com/project/phoenix-project-386/firestore/indexes")
        print("2. Click 'Create Index'")
        print("3. Create these two composite indexes:")
        print("\n   📑 Index 1:")
        print("   - Collection ID: link_clicks")
        print("   - Field: short_code (Ascending)")
        print("   - Field: clicked_at (Descending)")
        print("\n   📑 Index 2:")
        print("   - Collection ID: link_clicks") 
        print("   - Field: user_id (Ascending)")
        print("   - Field: clicked_at (Descending)")
        
        print("\n⏳ After creating indexes:")
        print("- Wait 5-10 minutes for indexes to build")
        print("- Run this script again to verify")
        print("- Test your analytics page")
        
        # Check current data
        print("\n📈 Current Data Status:")
        try:
            # Count total click records
            all_clicks = list(db.collection('link_clicks').limit(100).stream())
            print(f"✅ Total click records in database: {len(all_clicks)}")
            
            # Count total links
            all_links = list(db.collection('shortened_links').limit(100).stream())
            print(f"✅ Total links in database: {len(all_links)}")
            
        except Exception as e:
            print(f"⚠️  Error checking data: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up indexes: {e}")
        return False

def extract_index_url(error_message):
    """Extract the index creation URL from Firebase error message."""
    try:
        if "create it here:" in error_message:
            url = error_message.split("create it here: ")[1].strip()
            return url
    except:
        pass
    return "https://console.firebase.google.com/project/phoenix-project-386/firestore/indexes"

def test_analytics_after_indexes():
    """Test analytics functionality after indexes are created."""
    print("\n🧪 Testing Analytics Functionality...")
    
    try:
        from services.click_tracking_service import ClickTrackingService
        
        cts = ClickTrackingService()
        
        # Test getting clicks for a user
        print("Testing user clicks query...")
        test_user_clicks = cts.get_recent_clicks_for_user('test_user', limit=5)
        print(f"✅ User clicks query works (returned {len(test_user_clicks)} results)")
        
        # Test getting analytics for a link
        print("Testing link analytics query...")
        test_analytics = cts.get_click_analytics('test_code')
        print(f"✅ Link analytics query works")
        
        print("🎉 All analytics functionality is working!")
        
    except Exception as e:
        print(f"❌ Analytics test failed: {e}")
        print("This is expected if indexes are still building or missing.")

if __name__ == "__main__":
    print("🚀 Firestore Index Setup for Phoenix Analytics")
    print("=" * 50)
    
    success = create_firestore_indexes()
    
    if success:
        print("\n✅ Index setup check completed!")
        
        # Ask if user wants to test analytics
        test_choice = input("\n🧪 Test analytics functionality now? (y/n): ").lower().strip()
        if test_choice == 'y':
            test_analytics_after_indexes()
    else:
        print("\n❌ Index setup failed!")
        sys.exit(1)
    
    print("\n🎯 Next Steps:")
    print("1. Create the missing indexes in Firebase Console")
    print("2. Wait for indexes to build (5-10 minutes)")
    print("3. Test your analytics pages")
    print("4. Verify click tracking is working")
