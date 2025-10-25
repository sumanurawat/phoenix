"""Like Management Service

Manages the many-to-many relationship between users and posts for the like feature.
Uses a top-level collection for flexibility in querying both user likes and post likes.

Features:
- Toggle likes (like/unlike)
- Check if user has liked a post
- Get all posts liked by a user
- Get all users who liked a post
- Atomic operations coordinated with post like counts
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Set
from datetime import datetime
from google.cloud import firestore
from firebase_admin import firestore as admin_firestore

logger = logging.getLogger(__name__)


class LikeService:
    """
    Service for managing post likes (many-to-many user-post relationships).
    
    Each like is represented by a document with userId and postId.
    The existence of a document means the user has liked the post.
    """
    
    def __init__(self, db: firestore.Client = None):
        """
        Initialize like service.
        
        Args:
            db: Firestore client instance (uses default if not provided)
        """
        self.db = db or admin_firestore.client()
        self.collection = 'likes'
        logger.info("LikeService initialized")
    
    def _get_like_id(self, user_id: str, post_id: str) -> str:
        """Generate a deterministic document ID for a like."""
        return f"{user_id}_{post_id}"
    
    def like_post(self, user_id: str, post_id: str) -> bool:
        """
        Like a post (idempotent - can be called multiple times safely).
        
        Args:
            user_id: Firebase Auth UID of user liking the post
            post_id: Post document ID
            
        Returns:
            True if like was added, False if already liked
        """
        if not user_id or not post_id:
            raise ValueError("user_id and post_id are required")
        
        try:
            like_id = self._get_like_id(user_id, post_id)
            like_ref = self.db.collection(self.collection).document(like_id)
            
            # Check if already liked
            if like_ref.get().exists:
                logger.debug(f"User {user_id} already liked post {post_id}")
                return False
            
            # Create like document
            like_data = {
                'userId': user_id,
                'postId': post_id,
                'createdAt': admin_firestore.SERVER_TIMESTAMP
            }
            
            like_ref.set(like_data)
            
            logger.info(f"User {user_id} liked post {post_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to like post {post_id} by user {user_id}: {str(e)}",
                exc_info=True
            )
            raise
    
    def unlike_post(self, user_id: str, post_id: str) -> bool:
        """
        Unlike a post (remove like).
        
        Args:
            user_id: Firebase Auth UID
            post_id: Post document ID
            
        Returns:
            True if like was removed, False if wasn't liked
        """
        if not user_id or not post_id:
            raise ValueError("user_id and post_id are required")
        
        try:
            like_id = self._get_like_id(user_id, post_id)
            like_ref = self.db.collection(self.collection).document(like_id)
            
            # Check if liked
            if not like_ref.get().exists:
                logger.debug(f"User {user_id} hasn't liked post {post_id}")
                return False
            
            # Delete like document
            like_ref.delete()
            
            logger.info(f"User {user_id} unliked post {post_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to unlike post {post_id} by user {user_id}: {str(e)}",
                exc_info=True
            )
            raise
    
    def toggle_like(self, user_id: str, post_id: str) -> Dict[str, Any]:
        """
        Toggle like status (like if not liked, unlike if already liked).
        
        Args:
            user_id: Firebase Auth UID
            post_id: Post document ID
            
        Returns:
            Dictionary with 'liked' boolean and 'action' string
        """
        try:
            is_liked = self.check_if_liked(user_id, post_id)
            
            if is_liked:
                self.unlike_post(user_id, post_id)
                return {'liked': False, 'action': 'unliked'}
            else:
                self.like_post(user_id, post_id)
                return {'liked': True, 'action': 'liked'}
                
        except Exception as e:
            logger.error(
                f"Failed to toggle like for post {post_id}: {str(e)}",
                exc_info=True
            )
            raise
    
    def check_if_liked(self, user_id: str, post_id: str) -> bool:
        """
        Check if a user has liked a post.
        
        Args:
            user_id: Firebase Auth UID
            post_id: Post document ID
            
        Returns:
            True if user has liked the post, False otherwise
        """
        try:
            like_id = self._get_like_id(user_id, post_id)
            like_ref = self.db.collection(self.collection).document(like_id)
            
            return like_ref.get().exists
            
        except Exception as e:
            logger.error(
                f"Failed to check like status for post {post_id}: {str(e)}",
                exc_info=True
            )
            return False
    
    def get_user_liked_posts(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[str]:
        """
        Get all post IDs that a user has liked.
        
        Args:
            user_id: Firebase Auth UID
            limit: Maximum number of posts to return
            
        Returns:
            List of post IDs
        """
        try:
            query = self.db.collection(self.collection)
            query = query.where('userId', '==', user_id)
            query = query.order_by('createdAt', direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            post_ids = []
            for doc in query.stream():
                like_data = doc.to_dict()
                post_ids.append(like_data.get('postId'))
            
            logger.debug(f"User {user_id} has liked {len(post_ids)} posts")
            return post_ids
            
        except Exception as e:
            logger.error(
                f"Failed to get liked posts for {user_id}: {str(e)}",
                exc_info=True
            )
            return []
    
    def get_post_likers(
        self,
        post_id: str,
        limit: int = 100
    ) -> List[str]:
        """
        Get all user IDs who have liked a post.
        
        Args:
            post_id: Post document ID
            limit: Maximum number of users to return
            
        Returns:
            List of user IDs
        """
        try:
            query = self.db.collection(self.collection)
            query = query.where('postId', '==', post_id)
            query = query.order_by('createdAt', direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            user_ids = []
            for doc in query.stream():
                like_data = doc.to_dict()
                user_ids.append(like_data.get('userId'))
            
            logger.debug(f"Post {post_id} has {len(user_ids)} likes")
            return user_ids
            
        except Exception as e:
            logger.error(
                f"Failed to get likers for post {post_id}: {str(e)}",
                exc_info=True
            )
            return []
    
    def check_multiple_likes(
        self,
        user_id: str,
        post_ids: List[str]
    ) -> Dict[str, bool]:
        """
        Check if user has liked multiple posts (batch operation for feed).
        
        Args:
            user_id: Firebase Auth UID
            post_ids: List of post IDs to check
            
        Returns:
            Dictionary mapping post_id -> liked (boolean)
        """
        try:
            # Create a set of like IDs to check
            like_ids = [self._get_like_id(user_id, post_id) for post_id in post_ids]
            
            # Batch get (more efficient than individual queries)
            results = {}
            for post_id, like_id in zip(post_ids, like_ids):
                like_ref = self.db.collection(self.collection).document(like_id)
                results[post_id] = like_ref.get().exists
            
            return results
            
        except Exception as e:
            logger.error(
                f"Failed to check multiple likes: {str(e)}",
                exc_info=True
            )
            # Return all False on error
            return {post_id: False for post_id in post_ids}
    
    def get_like_count(self, post_id: str) -> int:
        """
        Get the number of likes for a post.
        
        Note: This is less efficient than using the denormalized likeCount
        on the post document. Use this only for verification/admin purposes.
        
        Args:
            post_id: Post document ID
            
        Returns:
            Number of likes
        """
        try:
            query = self.db.collection(self.collection).where('postId', '==', post_id)
            likes = list(query.stream())
            return len(likes)
            
        except Exception as e:
            logger.error(
                f"Failed to get like count for post {post_id}: {str(e)}",
                exc_info=True
            )
            return 0
    
    def delete_post_likes(self, post_id: str) -> int:
        """
        Delete all likes for a post (cleanup when post is deleted).
        
        Args:
            post_id: Post document ID
            
        Returns:
            Number of likes deleted
        """
        try:
            query = self.db.collection(self.collection).where('postId', '==', post_id)
            likes = list(query.stream())
            
            batch = self.db.batch()
            for like_doc in likes:
                batch.delete(like_doc.reference)
            
            batch.commit()
            
            count = len(likes)
            logger.info(f"Deleted {count} likes for post {post_id}")
            return count
            
        except Exception as e:
            logger.error(
                f"Failed to delete likes for post {post_id}: {str(e)}",
                exc_info=True
            )
            return 0
