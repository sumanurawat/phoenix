"""
Website Stats Service

Service for managing global website statistics and analytics.
"""
import logging
from firebase_admin import firestore
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class WebsiteStatsService:
    def __init__(self):
        self.db = firestore.client()
        self.stats_doc_id = "global_stats"
        self.stats_collection = "website_stats"
    
    def initialize_stats(self) -> Dict:
        """Initialize website stats with current data from existing links."""
        try:
            # Get current stats from existing shortened_links collection
            existing_links = self.db.collection('shortened_links').stream()
            
            total_links = 0
            total_clicks = 0
            
            for doc in existing_links:
                total_links += 1
                doc_data = doc.to_dict()
                total_clicks += doc_data.get('click_count', 0)
            
            # Create initial stats document
            stats_data = {
                'total_links_created': total_links,
                'total_clicks': total_clicks,
                'last_updated': firestore.SERVER_TIMESTAMP,
                'created_at': firestore.SERVER_TIMESTAMP,
                'version': 1
            }
            
            # Set the document (will overwrite if exists)
            self.db.collection(self.stats_collection).document(self.stats_doc_id).set(stats_data)
            
            logger.info(f"Initialized website stats: {total_links} links, {total_clicks} clicks")
            return stats_data
            
        except Exception as e:
            logger.error(f"Error initializing website stats: {e}")
            return {}
    
    def increment_links_created(self) -> bool:
        """Increment the total links created counter."""
        try:
            stats_ref = self.db.collection(self.stats_collection).document(self.stats_doc_id)
            stats_ref.update({
                'total_links_created': firestore.Increment(1),
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            logger.info("Incremented total_links_created")
            return True
        except Exception as e:
            logger.error(f"Error incrementing links created: {e}")
            return False
    
    def increment_total_clicks(self) -> bool:
        """Increment the total clicks counter."""
        try:
            stats_ref = self.db.collection(self.stats_collection).document(self.stats_doc_id)
            stats_ref.update({
                'total_clicks': firestore.Increment(1),
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            logger.info("Incremented total_clicks")
            return True
        except Exception as e:
            logger.error(f"Error incrementing total clicks: {e}")
            return False
    
    def get_website_stats(self) -> Dict:
        """Get current website statistics."""
        try:
            stats_doc = self.db.collection(self.stats_collection).document(self.stats_doc_id).get()
            
            if stats_doc.exists:
                return stats_doc.to_dict()
            else:
                # Initialize if doesn't exist
                return self.initialize_stats()
                
        except Exception as e:
            logger.error(f"Error fetching website stats: {e}")
            return {}
    
    def get_stats_for_display(self) -> Dict:
        """Get formatted stats for display in UI."""
        stats = self.get_website_stats()
        
        if not stats:
            return {
                'total_links': '0',
                'total_clicks': '0',
                'last_updated': 'Never'
            }
        
        return {
            'total_links': f"{stats.get('total_links_created', 0):,}",
            'total_clicks': f"{stats.get('total_clicks', 0):,}",
            'last_updated': stats.get('last_updated', 'Unknown')
        }
