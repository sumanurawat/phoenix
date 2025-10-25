"""Post Management Service

Manages user-generated content posts (images and future videos) for the social feed.
Handles post creation, retrieval, feed generation, and like count management.

Features:
- Create posts with media URL, caption, and prompt
- Fetch individual posts and user galleries
- Generate chronological feed for discovery
- Atomic like count updates
- Support for both image and video content types
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from google.cloud import firestore
from firebase_admin import firestore as admin_firestore

logger = logging.getLogger(__name__)


class PostType:
    """Content type constants."""
    IMAGE = "image"
    VIDEO = "video"


class PostService:
    """
    Service for managing content posts in the social feed.
    
    Posts are the central entity in the social platform, linking users,
    media content, and social interactions (likes, tips).
    """
    
    def __init__(self, db: firestore.Client = None):
        """
        Initialize post service.
        
        Args:
            db: Firestore client instance (uses default if not provided)
        """
        self.db = db or admin_firestore.client()
        self.collection = 'posts'
        logger.info("PostService initialized")
    
    def create_post(
        self,
        user_id: str,
        media_url: str,
        content_type: str = PostType.IMAGE,
        caption: str = "",
        prompt: str = ""
    ) -> str:
        """
        Create a new post in the social feed.
        
        Args:
            user_id: Firebase Auth UID of post creator
            media_url: Public URL of media (R2/GCS)
            content_type: Type of content (image or video)
            caption: User-written caption/description
            prompt: AI generation prompt (stored but not public by default)
            
        Returns:
            Post document ID
            
        Raises:
            ValueError: If required fields are missing
        """
        if not user_id:
            raise ValueError("user_id is required")
        if not media_url:
            raise ValueError("media_url is required")
        if content_type not in [PostType.IMAGE, PostType.VIDEO]:
            raise ValueError(f"Invalid content_type: {content_type}")
        
        try:
            post_data = {
                'userId': user_id,
                'type': content_type,
                'mediaUrl': media_url,
                'caption': caption.strip() if caption else "",
                'prompt': prompt.strip() if prompt else "",
                'likeCount': 0,
                'createdAt': admin_firestore.SERVER_TIMESTAMP
            }
            
            # Create document with auto-generated ID
            doc_ref = self.db.collection(self.collection).document()
            doc_ref.set(post_data)
            
            logger.info(
                f"Created post {doc_ref.id} | User: {user_id} | "
                f"Type: {content_type} | Caption: {caption[:50]}..."
            )
            
            return doc_ref.id
            
        except Exception as e:
            logger.error(
                f"Failed to create post for {user_id}: {str(e)}",
                exc_info=True
            )
            raise
    
    def get_post(self, post_id: str, include_prompt: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a single post by ID.
        
        Args:
            post_id: Post document ID
            include_prompt: Whether to include the AI prompt (default: False for privacy)
            
        Returns:
            Post data dictionary or None if not found
        """
        try:
            doc_ref = self.db.collection(self.collection).document(post_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.debug(f"Post {post_id} not found")
                return None
            
            post_data = doc.to_dict()
            post_data['id'] = doc.id
            
            # Convert timestamp to ISO string
            if 'createdAt' in post_data and post_data['createdAt']:
                post_data['createdAt'] = post_data['createdAt'].isoformat()
            
            # Remove prompt unless explicitly requested
            if not include_prompt and 'prompt' in post_data:
                del post_data['prompt']
            
            return post_data
            
        except Exception as e:
            logger.error(f"Failed to get post {post_id}: {str(e)}", exc_info=True)
            return None
    
    def get_user_posts(
        self,
        user_id: str,
        limit: int = 50,
        start_after: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all posts by a specific user (for their gallery/profile).
        
        Args:
            user_id: Firebase Auth UID
            limit: Maximum number of posts to return
            start_after: Post ID to start after (for pagination)
            
        Returns:
            List of post dictionaries, newest first
        """
        try:
            query = self.db.collection(self.collection)
            query = query.where('userId', '==', user_id)
            query = query.order_by('createdAt', direction=firestore.Query.DESCENDING)
            
            # Pagination support
            if start_after:
                start_doc = self.db.collection(self.collection).document(start_after).get()
                if start_doc.exists:
                    query = query.start_after(start_doc)
            
            query = query.limit(limit)
            
            posts = []
            for doc in query.stream():
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                
                if 'createdAt' in post_data and post_data['createdAt']:
                    post_data['createdAt'] = post_data['createdAt'].isoformat()
                
                # Don't include prompt in public listings
                if 'prompt' in post_data:
                    del post_data['prompt']
                
                posts.append(post_data)
            
            logger.debug(f"Retrieved {len(posts)} posts for user {user_id}")
            return posts
            
        except Exception as e:
            logger.error(
                f"Failed to get posts for user {user_id}: {str(e)}",
                exc_info=True
            )
            return []
    
    def get_feed(
        self,
        limit: int = 50,
        start_after: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get public feed of all posts (discovery/home feed).
        
        Args:
            limit: Maximum number of posts to return
            start_after: Post ID to start after (for infinite scroll)
            
        Returns:
            List of post dictionaries, newest first
        """
        try:
            query = self.db.collection(self.collection)
            query = query.order_by('createdAt', direction=firestore.Query.DESCENDING)
            
            # Pagination support
            if start_after:
                start_doc = self.db.collection(self.collection).document(start_after).get()
                if start_doc.exists:
                    query = query.start_after(start_doc)
            
            query = query.limit(limit)
            
            posts = []
            for doc in query.stream():
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                
                if 'createdAt' in post_data and post_data['createdAt']:
                    post_data['createdAt'] = post_data['createdAt'].isoformat()
                
                # Don't include prompt in public feed
                if 'prompt' in post_data:
                    del post_data['prompt']
                
                posts.append(post_data)
            
            logger.debug(f"Retrieved {len(posts)} posts for feed")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get feed: {str(e)}", exc_info=True)
            return []
    
    @admin_firestore.transactional
    def _update_like_count_transaction(
        self,
        transaction: firestore.Transaction,
        post_ref: firestore.DocumentReference,
        increment: int
    ) -> None:
        """
        Update like count atomically within a transaction.
        
        Args:
            transaction: Firestore transaction
            post_ref: Post document reference
            increment: Amount to increment (+1 for like, -1 for unlike)
        """
        post_doc = post_ref.get(transaction=transaction)
        
        if not post_doc.exists:
            raise ValueError("Post does not exist")
        
        # Atomically increment like count
        transaction.update(post_ref, {
            'likeCount': admin_firestore.Increment(increment)
        })
    
    def increment_like_count(self, post_id: str) -> bool:
        """
        Increment the like count for a post atomically.
        
        Args:
            post_id: Post document ID
            
        Returns:
            True if successful
        """
        try:
            post_ref = self.db.collection(self.collection).document(post_id)
            transaction = self.db.transaction()
            
            self._update_like_count_transaction(transaction, post_ref, 1)
            logger.debug(f"Incremented like count for post {post_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to increment like count for {post_id}: {str(e)}",
                exc_info=True
            )
            return False
    
    def decrement_like_count(self, post_id: str) -> bool:
        """
        Decrement the like count for a post atomically.
        
        Args:
            post_id: Post document ID
            
        Returns:
            True if successful
        """
        try:
            post_ref = self.db.collection(self.collection).document(post_id)
            transaction = self.db.transaction()
            
            self._update_like_count_transaction(transaction, post_ref, -1)
            logger.debug(f"Decremented like count for post {post_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to decrement like count for {post_id}: {str(e)}",
                exc_info=True
            )
            return False
    
    def delete_post(self, post_id: str, user_id: str) -> bool:
        """
        Delete a post (only by the post creator).
        
        Args:
            post_id: Post document ID
            user_id: Firebase Auth UID (must match post creator)
            
        Returns:
            True if deleted, False if not found or unauthorized
        """
        try:
            post_ref = self.db.collection(self.collection).document(post_id)
            post_doc = post_ref.get()
            
            if not post_doc.exists:
                logger.warning(f"Cannot delete post {post_id}: not found")
                return False
            
            post_data = post_doc.to_dict()
            if post_data.get('userId') != user_id:
                logger.warning(
                    f"User {user_id} attempted to delete post {post_id} "
                    f"owned by {post_data.get('userId')}"
                )
                return False
            
            post_ref.delete()
            logger.info(f"Deleted post {post_id} by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete post {post_id}: {str(e)}", exc_info=True)
            return False
    
    def get_post_count(self, user_id: str) -> int:
        """
        Get total number of posts by a user.
        
        Args:
            user_id: Firebase Auth UID
            
        Returns:
            Total post count
        """
        try:
            query = self.db.collection(self.collection).where('userId', '==', user_id)
            # Use a limit to avoid reading too many documents
            docs = list(query.stream())
            return len(docs)
        except Exception as e:
            logger.error(f"Failed to get post count for {user_id}: {str(e)}", exc_info=True)
            return 0
