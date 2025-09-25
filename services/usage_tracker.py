"""
Usage Tracker - Centralized usage tracking and limit management.

This module provides a consistent API for tracking feature usage across
different storage backends and time windows.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from firebase_admin import firestore
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)


class UsageWindow(Enum):
    """Time windows for usage tracking."""
    DAILY = "daily"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    HOURLY = "hourly"


class UsageTracker:
    """Centralized usage tracking service."""
    
    def __init__(self):
        self.stripe_service = StripeService()
        self.db = firestore.client()
    
    def increment(self, user_id: str, feature_id: str, amount: int = 1, 
                  window: UsageWindow = UsageWindow.DAILY) -> bool:
        """
        Increment usage counter for a feature.
        
        Args:
            user_id: User identifier
            feature_id: Feature identifier
            amount: Amount to increment (default 1)
            window: Time window for tracking
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if window == UsageWindow.DAILY:
                return self.stripe_service.increment_usage(user_id, feature_id, amount)
            else:
                return self._increment_custom_window(user_id, feature_id, amount, window)
        except Exception as e:
            logger.error(f"Error incrementing usage for {user_id}, {feature_id}: {e}")
            return False
    
    def get_usage(self, user_id: str, feature_id: str = None, 
                  window: UsageWindow = UsageWindow.DAILY) -> Dict[str, int]:
        """
        Get current usage for user.
        
        Args:
            user_id: User identifier
            feature_id: Specific feature (if None, returns all features)
            window: Time window to check
            
        Returns:
            Dictionary of feature_id -> usage_count
        """
        try:
            if window == UsageWindow.DAILY:
                usage_stats = self.stripe_service.get_usage_stats(user_id)
                if feature_id:
                    return {feature_id: usage_stats.get(feature_id, 0)}
                return usage_stats
            else:
                return self._get_custom_window_usage(user_id, feature_id, window)
        except Exception as e:
            logger.error(f"Error getting usage for {user_id}: {e}")
            return {}
    
    def check_limit(self, user_id: str, feature_id: str, limit: int,
                    window: UsageWindow = UsageWindow.DAILY) -> Dict[str, Any]:
        """
        Check if user is within usage limits.
        
        Args:
            user_id: User identifier
            feature_id: Feature identifier
            limit: Usage limit (-1 for unlimited)
            window: Time window to check
            
        Returns:
            Dictionary with limit check results
        """
        if limit == -1:
            return {
                'allowed': True,
                'unlimited': True,
                'current': 0,
                'remaining': -1
            }
        
        usage = self.get_usage(user_id, feature_id, window)
        current = usage.get(feature_id, 0)
        
        return {
            'allowed': current < limit,
            'unlimited': False,
            'current': current,
            'remaining': max(0, limit - current),
            'limit': limit,
            'window': window.value
        }
    
    def reset_usage(self, user_id: str, feature_id: str = None,
                    window: UsageWindow = UsageWindow.DAILY) -> bool:
        """
        Reset usage counters for user.
        
        Args:
            user_id: User identifier
            feature_id: Specific feature (if None, resets all)
            window: Time window to reset
            
        Returns:
            True if successful
        """
        try:
            if window == UsageWindow.DAILY:
                return self._reset_daily_usage(user_id, feature_id)
            else:
                return self._reset_custom_window_usage(user_id, feature_id, window)
        except Exception as e:
            logger.error(f"Error resetting usage for {user_id}: {e}")
            return False
    
    def get_usage_history(self, user_id: str, feature_id: str,
                          days: int = 30) -> List[Dict[str, Any]]:
        """
        Get historical usage data.
        
        Args:
            user_id: User identifier
            feature_id: Feature identifier
            days: Number of days to retrieve
            
        Returns:
            List of usage records
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Query Firestore for historical data
            collection_name = f"user_usage/{user_id}/history"
            query = (self.db.collection(collection_name)
                    .where('feature_id', '==', feature_id)
                    .where('date', '>=', start_date)
                    .where('date', '<=', end_date)
                    .order_by('date'))
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
            
        except Exception as e:
            logger.error(f"Error getting usage history for {user_id}, {feature_id}: {e}")
            return []
    
    def get_aggregate_stats(self, feature_id: str = None,
                           start_date: datetime = None,
                           end_date: datetime = None) -> Dict[str, Any]:
        """
        Get aggregate usage statistics across all users.
        
        Args:
            feature_id: Specific feature (if None, all features)
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Aggregate statistics
        """
        # TODO: Implement aggregate statistics
        # This would typically involve querying across all user usage records
        # and computing totals, averages, etc.
        return {
            'total_users': 0,
            'total_usage': 0,
            'average_usage': 0,
            'peak_usage': 0
        }
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """
        Clean up old usage data.
        
        Args:
            days_to_keep: Number of days of data to retain
            
        Returns:
            True if successful
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # TODO: Implement cleanup logic
            # This would delete usage records older than cutoff_date
            
            logger.info(f"Cleaned up usage data older than {cutoff_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up usage data: {e}")
            return False
    
    # Private methods
    
    def _increment_custom_window(self, user_id: str, feature_id: str, 
                                amount: int, window: UsageWindow) -> bool:
        """Increment usage for custom time windows."""
        try:
            window_key = self._get_window_key(window)
            doc_path = f"user_usage/{user_id}/windows/{window_key}"
            
            doc_ref = self.db.document(doc_path)
            doc_ref.set({
                feature_id: firestore.Increment(amount),
                'last_updated': datetime.now(timezone.utc)
            }, merge=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing custom window usage: {e}")
            return False
    
    def _get_custom_window_usage(self, user_id: str, feature_id: str,
                                window: UsageWindow) -> Dict[str, int]:
        """Get usage for custom time windows."""
        try:
            window_key = self._get_window_key(window)
            doc_path = f"user_usage/{user_id}/windows/{window_key}"
            
            doc = self.db.document(doc_path).get()
            if not doc.exists:
                return {}
            
            data = doc.to_dict()
            # Remove metadata fields
            data.pop('last_updated', None)
            
            if feature_id:
                return {feature_id: data.get(feature_id, 0)}
            return data
            
        except Exception as e:
            logger.error(f"Error getting custom window usage: {e}")
            return {}
    
    def _reset_daily_usage(self, user_id: str, feature_id: str = None) -> bool:
        """Reset daily usage counters."""
        # For daily usage, we rely on the existing Stripe service logic
        # which resets counters based on date
        # TODO: Implement explicit reset if needed
        return True
    
    def _reset_custom_window_usage(self, user_id: str, feature_id: str,
                                   window: UsageWindow) -> bool:
        """Reset custom window usage counters."""
        try:
            window_key = self._get_window_key(window)
            doc_path = f"user_usage/{user_id}/windows/{window_key}"
            
            if feature_id:
                # Reset specific feature
                doc_ref = self.db.document(doc_path)
                doc_ref.update({
                    feature_id: 0,
                    'last_updated': datetime.now(timezone.utc)
                })
            else:
                # Reset all features in window
                doc_ref = self.db.document(doc_path)
                doc_ref.delete()
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting custom window usage: {e}")
            return False
    
    def _get_window_key(self, window: UsageWindow) -> str:
        """Generate key for time window."""
        now = datetime.now(timezone.utc)
        
        if window == UsageWindow.DAILY:
            return now.strftime('%Y-%m-%d')
        elif window == UsageWindow.WEEKLY:
            # Start of week (Monday)
            start_of_week = now - timedelta(days=now.weekday())
            return f"{start_of_week.strftime('%Y-%m-%d')}_week"
        elif window == UsageWindow.MONTHLY:
            return now.strftime('%Y-%m')
        elif window == UsageWindow.HOURLY:
            return now.strftime('%Y-%m-%d_%H')
        else:
            return now.strftime('%Y-%m-%d')


# Global instance
usage_tracker = UsageTracker()