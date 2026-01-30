"""Follow API Routes

Handles follow/unfollow operations and following feed.

Endpoints:
- POST /api/users/<username>/follow - Toggle follow (follow if not, unfollow if yes)
- DELETE /api/users/<username>/follow - Unfollow user
- GET /api/users/<username>/follow-status - Check if following
- GET /api/feed/following - Get posts from followed users
"""
import logging
from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore

from api.auth_routes import login_required
from services.follow_service import (
    get_follow_service,
    FollowError,
    CannotFollowSelfError,
    UserNotFoundError
)
from services.user_service import UserService

logger = logging.getLogger(__name__)

follow_bp = Blueprint('follow', __name__)

# Initialize services
db = firestore.client()
user_service = UserService()


def _get_user_id_from_username(username: str) -> str | None:
    """Helper to resolve username to user_id."""
    user_data = user_service.get_user_by_username(username)
    if user_data:
        return user_data.get('firebase_uid')
    return None


@follow_bp.route('/api/users/<username>/follow', methods=['POST'])
@login_required
def toggle_follow(username):
    """
    Toggle follow status for a user (Instagram-style).
    
    If currently following -> unfollow
    If not following -> follow
    
    Path params:
        username: Target user's username
        
    Returns:
        200: { success: true, following: bool, message: string }
        400: Cannot follow yourself
        404: User not found
        500: Server error
    """
    current_user_id = session.get('user_id')
    
    if not current_user_id:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    try:
        # Resolve username to user_id
        target_user_id = _get_user_id_from_username(username)
        
        if not target_user_id:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Toggle follow
        follow_service = get_follow_service()
        result = follow_service.toggle_follow(current_user_id, target_user_id)
        
        return jsonify(result)
        
    except CannotFollowSelfError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except UserNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
        
    except FollowError as e:
        logger.error(f"Follow error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in toggle_follow: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update follow status'
        }), 500


@follow_bp.route('/api/users/<username>/follow', methods=['DELETE'])
@login_required
def unfollow_user(username):
    """
    Unfollow a user.
    
    Path params:
        username: Target user's username
        
    Returns:
        200: { success: true, following: false, message: string }
        404: User not found
        500: Server error
    """
    current_user_id = session.get('user_id')
    
    if not current_user_id:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    try:
        # Resolve username to user_id
        target_user_id = _get_user_id_from_username(username)
        
        if not target_user_id:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Unfollow
        follow_service = get_follow_service()
        result = follow_service.unfollow_user(current_user_id, target_user_id)
        
        return jsonify(result)
        
    except FollowError as e:
        logger.error(f"Unfollow error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in unfollow_user: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to unfollow user'
        }), 500


@follow_bp.route('/api/users/<username>/follow-status', methods=['GET'])
@login_required
def get_follow_status(username):
    """
    Check if current user follows the target user.
    
    Path params:
        username: Target user's username
        
    Returns:
        200: { success: true, following: bool }
        404: User not found
        500: Server error
    """
    current_user_id = session.get('user_id')
    
    if not current_user_id:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    try:
        # Resolve username to user_id
        target_user_id = _get_user_id_from_username(username)
        
        if not target_user_id:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Check status
        follow_service = get_follow_service()
        is_following = follow_service.is_following(current_user_id, target_user_id)
        
        return jsonify({
            'success': True,
            'following': is_following
        })
        
    except Exception as e:
        logger.error(f"Error checking follow status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to check follow status'
        }), 500


@follow_bp.route('/api/feed/following', methods=['GET'])
@login_required
def get_following_feed():
    """
    Get posts from users the current user follows.
    
    Query params:
        limit: Max creations to return (default 20, max 50)
        cursor: Pagination cursor (last creationId from previous page)
        
    Returns:
        200: {
            success: true,
            creations: [...],
            nextCursor: string | null,
            hasMore: bool
        }
        500: Server error
    """
    current_user_id = session.get('user_id')
    
    if not current_user_id:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    try:
        # Parse query params
        limit = min(int(request.args.get('limit', 20)), 50)
        cursor = request.args.get('cursor')
        
        # Get list of users we follow
        follow_service = get_follow_service()
        following_list = follow_service.get_following_list(current_user_id)
        
        # If not following anyone, return empty
        if not following_list:
            return jsonify({
                'success': True,
                'creations': [],
                'nextCursor': None,
                'hasMore': False,
                'message': 'Follow some creators to see their posts here!'
            })
        
        # Query creations from followed users
        # Firestore 'in' operator supports up to 30 values
        # For >30 follows, we chunk and merge (simplified: take first 30 for now)
        query_user_ids = following_list[:30]
        
        query = (db.collection('creations')
                .where(filter=firestore.FieldFilter('userId', 'in', query_user_ids))
                .where(filter=firestore.FieldFilter('status', '==', 'published'))
                .order_by('publishedAt', direction=firestore.Query.DESCENDING)
                .limit(limit + 1))
        
        if cursor:
            cursor_doc = db.collection('creations').document(cursor).get()
            if cursor_doc.exists:
                query = query.start_after(cursor_doc)
        
        # Execute query
        docs = list(query.stream())
        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]
        
        # Format response
        creations = []
        for doc in docs:
            data = doc.to_dict()
            creation_data = {
                'creationId': doc.id,
                'userId': data.get('userId'),
                'username': data.get('username', 'Unknown'),
                'caption': data.get('caption', ''),
                'mediaUrl': data.get('mediaUrl'),
                'mediaType': data.get('mediaType', 'video'),
                'aspectRatio': data.get('aspectRatio', '9:16'),
                'duration': data.get('duration', 8),
                'commentCount': data.get('commentCount', 0),
                'publishedAt': data.get('publishedAt'),
                # Only show prompt for own creations
                'prompt': data.get('prompt', '') if data.get('userId') == current_user_id else ''
            }
            creations.append(creation_data)
        
        next_cursor = docs[-1].id if has_more and docs else None
        
        return jsonify({
            'success': True,
            'creations': creations,
            'nextCursor': next_cursor,
            'hasMore': has_more
        })
        
    except Exception as e:
        logger.error(f"Error fetching following feed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load feed'
        }), 500
