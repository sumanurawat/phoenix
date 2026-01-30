"""Follow Service - Social Relationship Management

Manages follow relationships between users with modular counter operations.
Uses atomic Firestore transactions to maintain consistency.

Features:
- Follow/unfollow with atomic counter updates
- Bidirectional relationship tracking (following + followers arrays)
- Idempotent operations (safe to call multiple times)
- Account deletion cleanup support

Schema (on users/{userId}):
    following: string[]      - Array of user IDs this user follows
    followers: string[]      - Array of user IDs following this user
    followingCount: int      - Denormalized count of following
    followersCount: int      - Denormalized count of followers
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from google.cloud import firestore
from firebase_admin import firestore as admin_firestore

logger = logging.getLogger(__name__)


class FollowError(Exception):
    """Base exception for follow operations."""
    pass


class CannotFollowSelfError(FollowError):
    """Raised when user tries to follow themselves."""
    pass


class UserNotFoundError(FollowError):
    """Raised when target user doesn't exist."""
    pass


class FollowService:
    """
    Service for managing follow relationships between users.
    
    Uses array-based storage on user documents for Firebase free tier optimization.
    All mutations run in Firestore transactions for consistency.
    """
    
    def __init__(self, db: firestore.Client = None):
        """
        Initialize follow service.
        
        Args:
            db: Firestore client (uses default if not provided)
        """
        self.db = db or admin_firestore.client()
        self.users_collection = 'users'
        logger.debug("FollowService initialized")
    
    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================
    
    def follow_user(self, follower_id: str, target_user_id: str) -> Dict[str, Any]:
        """
        Follow a user.
        
        Args:
            follower_id: Firebase UID of the user doing the following
            target_user_id: Firebase UID of the user to follow
            
        Returns:
            Dict with 'success', 'following' (bool), 'message'
            
        Raises:
            CannotFollowSelfError: If trying to follow self
            UserNotFoundError: If target user doesn't exist
        """
        # Validate: can't follow yourself
        if follower_id == target_user_id:
            raise CannotFollowSelfError("You cannot follow yourself")
        
        # Validate: target user must exist
        target_ref = self.db.collection(self.users_collection).document(target_user_id)
        if not target_ref.get().exists:
            raise UserNotFoundError("User not found")
        
        # Check if already following (idempotent)
        if self.is_following(follower_id, target_user_id):
            logger.info(f"User {follower_id} already follows {target_user_id}")
            return {
                'success': True,
                'following': True,
                'message': 'Already following this user'
            }
        
        # Perform atomic follow operation
        try:
            @admin_firestore.transactional
            def follow_transaction(transaction):
                follower_ref = self.db.collection(self.users_collection).document(follower_id)
                target_ref = self.db.collection(self.users_collection).document(target_user_id)
                
                # Update follower's document (add to following)
                self._add_to_following(transaction, follower_ref, target_user_id)
                self._increment_following_count(transaction, follower_ref)
                
                # Update target's document (add to followers)
                self._add_to_followers(transaction, target_ref, follower_id)
                self._increment_followers_count(transaction, target_ref)
            
            transaction = self.db.transaction()
            follow_transaction(transaction)
            
            logger.info(f"User {follower_id} now follows {target_user_id}")
            return {
                'success': True,
                'following': True,
                'message': 'Successfully followed user'
            }
            
        except Exception as e:
            logger.error(f"Failed to follow user: {e}", exc_info=True)
            raise FollowError(f"Failed to follow user: {str(e)}")
    
    def unfollow_user(self, follower_id: str, target_user_id: str) -> Dict[str, Any]:
        """
        Unfollow a user.
        
        Args:
            follower_id: Firebase UID of the user doing the unfollowing
            target_user_id: Firebase UID of the user to unfollow
            
        Returns:
            Dict with 'success', 'following' (bool), 'message'
        """
        # Check if actually following (idempotent)
        if not self.is_following(follower_id, target_user_id):
            logger.info(f"User {follower_id} doesn't follow {target_user_id}")
            return {
                'success': True,
                'following': False,
                'message': 'Not following this user'
            }
        
        # Perform atomic unfollow operation
        try:
            @admin_firestore.transactional
            def unfollow_transaction(transaction):
                follower_ref = self.db.collection(self.users_collection).document(follower_id)
                target_ref = self.db.collection(self.users_collection).document(target_user_id)
                
                # Update follower's document (remove from following)
                self._remove_from_following(transaction, follower_ref, target_user_id)
                self._decrement_following_count(transaction, follower_ref)
                
                # Update target's document (remove from followers)
                self._remove_from_followers(transaction, target_ref, follower_id)
                self._decrement_followers_count(transaction, target_ref)
            
            transaction = self.db.transaction()
            unfollow_transaction(transaction)
            
            logger.info(f"User {follower_id} unfollowed {target_user_id}")
            return {
                'success': True,
                'following': False,
                'message': 'Successfully unfollowed user'
            }
            
        except Exception as e:
            logger.error(f"Failed to unfollow user: {e}", exc_info=True)
            raise FollowError(f"Failed to unfollow user: {str(e)}")
    
    def toggle_follow(self, follower_id: str, target_user_id: str) -> Dict[str, Any]:
        """
        Toggle follow state (Instagram-style).
        
        If following -> unfollow
        If not following -> follow
        
        Args:
            follower_id: Firebase UID of the current user
            target_user_id: Firebase UID of the target user
            
        Returns:
            Dict with 'success', 'following' (new state), 'message'
        """
        if self.is_following(follower_id, target_user_id):
            return self.unfollow_user(follower_id, target_user_id)
        else:
            return self.follow_user(follower_id, target_user_id)
    
    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================
    
    def is_following(self, follower_id: str, target_user_id: str) -> bool:
        """
        Check if follower_id follows target_user_id.
        
        Args:
            follower_id: User to check
            target_user_id: Potential followee
            
        Returns:
            True if follower_id follows target_user_id
        """
        try:
            user_ref = self.db.collection(self.users_collection).document(follower_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return False
            
            following = user_doc.to_dict().get('following', [])
            return target_user_id in following
            
        except Exception as e:
            logger.error(f"Error checking follow status: {e}", exc_info=True)
            return False
    
    def get_following_list(self, user_id: str) -> List[str]:
        """
        Get list of user IDs that this user follows.
        
        Args:
            user_id: User to get following list for
            
        Returns:
            List of user IDs being followed
        """
        try:
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return []
            
            return user_doc.to_dict().get('following', [])
            
        except Exception as e:
            logger.error(f"Error getting following list: {e}", exc_info=True)
            return []
    
    def get_followers_list(self, user_id: str) -> List[str]:
        """
        Get list of user IDs that follow this user.
        
        Args:
            user_id: User to get followers for
            
        Returns:
            List of user IDs following this user
        """
        try:
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return []
            
            return user_doc.to_dict().get('followers', [])
            
        except Exception as e:
            logger.error(f"Error getting followers list: {e}", exc_info=True)
            return []
    
    def get_follow_stats(self, user_id: str) -> Dict[str, int]:
        """
        Get follow statistics for a user.
        
        Args:
            user_id: User to get stats for
            
        Returns:
            Dict with 'followingCount' and 'followersCount'
        """
        try:
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return {'followingCount': 0, 'followersCount': 0}
            
            data = user_doc.to_dict()
            return {
                'followingCount': data.get('followingCount', 0),
                'followersCount': data.get('followersCount', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting follow stats: {e}", exc_info=True)
            return {'followingCount': 0, 'followersCount': 0}
    
    # =========================================================================
    # MODULAR COUNTER OPERATIONS (for transactions)
    # =========================================================================
    
    def _increment_following_count(self, transaction, user_ref) -> None:
        """Increment the followingCount for a user."""
        transaction.update(user_ref, {
            'followingCount': firestore.Increment(1)
        })
    
    def _decrement_following_count(self, transaction, user_ref) -> None:
        """Decrement the followingCount for a user (minimum 0)."""
        # Firestore Increment handles negative, we rely on array operations for accuracy
        transaction.update(user_ref, {
            'followingCount': firestore.Increment(-1)
        })
    
    def _increment_followers_count(self, transaction, user_ref) -> None:
        """Increment the followersCount for a user."""
        transaction.update(user_ref, {
            'followersCount': firestore.Increment(1)
        })
    
    def _decrement_followers_count(self, transaction, user_ref) -> None:
        """Decrement the followersCount for a user (minimum 0)."""
        transaction.update(user_ref, {
            'followersCount': firestore.Increment(-1)
        })
    
    # =========================================================================
    # MODULAR ARRAY OPERATIONS (for transactions)
    # =========================================================================
    
    def _add_to_following(self, transaction, user_ref, target_id: str) -> None:
        """Add target_id to user's following array."""
        transaction.update(user_ref, {
            'following': firestore.ArrayUnion([target_id])
        })
    
    def _remove_from_following(self, transaction, user_ref, target_id: str) -> None:
        """Remove target_id from user's following array."""
        transaction.update(user_ref, {
            'following': firestore.ArrayRemove([target_id])
        })
    
    def _add_to_followers(self, transaction, user_ref, follower_id: str) -> None:
        """Add follower_id to user's followers array."""
        transaction.update(user_ref, {
            'followers': firestore.ArrayUnion([follower_id])
        })
    
    def _remove_from_followers(self, transaction, user_ref, follower_id: str) -> None:
        """Remove follower_id from user's followers array."""
        transaction.update(user_ref, {
            'followers': firestore.ArrayRemove([follower_id])
        })
    
    # =========================================================================
    # CLEANUP OPERATIONS (for account deletion)
    # =========================================================================
    
    def remove_all_follow_relationships(self, user_id: str) -> Dict[str, Any]:
        """
        Remove all follow relationships for a user (called during account deletion).
        
        This removes:
        - The user from all their followers' 'following' arrays
        - The user from all users they follow (their 'followers' arrays)
        - Decrements all related counters
        
        Args:
            user_id: User being deleted
            
        Returns:
            Summary of cleanup performed
        """
        cleanup_summary = {
            'followers_cleaned': 0,
            'following_cleaned': 0,
            'errors': []
        }
        
        try:
            # Get the user's follow data before deletion
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                logger.warning(f"User {user_id} not found for follow cleanup")
                return cleanup_summary
            
            user_data = user_doc.to_dict()
            followers = user_data.get('followers', [])
            following = user_data.get('following', [])
            
            # Remove this user from all their followers' 'following' arrays
            for follower_id in followers:
                try:
                    follower_ref = self.db.collection(self.users_collection).document(follower_id)
                    follower_ref.update({
                        'following': firestore.ArrayRemove([user_id]),
                        'followingCount': firestore.Increment(-1)
                    })
                    cleanup_summary['followers_cleaned'] += 1
                except Exception as e:
                    logger.warning(f"Failed to clean follower {follower_id}: {e}")
                    cleanup_summary['errors'].append(f"follower:{follower_id}")
            
            # Remove this user from all users they follow (their 'followers' arrays)
            for followed_id in following:
                try:
                    followed_ref = self.db.collection(self.users_collection).document(followed_id)
                    followed_ref.update({
                        'followers': firestore.ArrayRemove([user_id]),
                        'followersCount': firestore.Increment(-1)
                    })
                    cleanup_summary['following_cleaned'] += 1
                except Exception as e:
                    logger.warning(f"Failed to clean followed user {followed_id}: {e}")
                    cleanup_summary['errors'].append(f"following:{followed_id}")
            
            logger.info(
                f"Follow cleanup for user {user_id}: "
                f"cleaned {cleanup_summary['followers_cleaned']} followers, "
                f"{cleanup_summary['following_cleaned']} following"
            )
            
            return cleanup_summary
            
        except Exception as e:
            logger.error(f"Error during follow cleanup for {user_id}: {e}", exc_info=True)
            cleanup_summary['errors'].append(str(e))
            return cleanup_summary


# Singleton instance for easy import
_follow_service_instance: Optional[FollowService] = None


def get_follow_service() -> FollowService:
    """Get or create the singleton FollowService instance."""
    global _follow_service_instance
    if _follow_service_instance is None:
        _follow_service_instance = FollowService()
    return _follow_service_instance
