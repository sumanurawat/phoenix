#!/usr/bin/env python3
"""
Website Stats Initialization Script

This script initializes the website statistics by counting existing links and clicks
from the current Firestore database. Run this once after deploying the stats system.

Usage:
    python scripts/init_website_stats.py
"""
import sys
import os

# Add the parent directory to the path so we can import our services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials
from services.website_stats_service import WebsiteStatsService
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Initialize website statistics from existing data."""
    print("🚀 Initializing Phoenix Website Statistics...")
    print("=" * 50)
    
    try:
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            # Try to use the credentials file if available
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'firebase-credentials.json')
            if os.path.exists(credentials_path):
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin SDK initialized with credentials file")
            else:
                # Fall back to application default credentials
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin SDK initialized with default credentials")
        
        # Initialize the service
        stats_service = WebsiteStatsService()
        
        # Initialize stats from existing data
        result = stats_service.initialize_stats()
        
        if result:
            print("✅ Successfully initialized website statistics!")
            print(f"   📊 Total Links Created: {result.get('total_links_created', 0):,}")
            print(f"   🖱️  Total Clicks: {result.get('total_clicks', 0):,}")
            print(f"   📅 Initialized: {result.get('created_at', 'Now')}")
            print(f"   🔢 Version: {result.get('version', 1)}")
            print()
            print("🎉 Website stats are now ready!")
            print("   - Homepage will display live statistics")
            print("   - Admin can view detailed stats at /admin/stats")
            print("   - All new links and clicks will be automatically tracked")
        else:
            print("❌ Failed to initialize website statistics")
            print("   Please check the logs for error details")
            return 1
    
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        logging.exception("Full error details:")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
