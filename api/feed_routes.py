"""Feed and Social Interaction API Routes

Handles the public feed (Explore), likes, and social interactions.

Endpoints:
- GET /api/feed/explore - Public feed of published creations
- POST /api/creations/<id>/like - Like a creation
- DELETE /api/creations/<id>/like - Unlike a creation
- GET /api/creations/<id>/likes - Get like count and status
- GET /api/users/<username>/creations - User gallery
"""
import logging
from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore

from api.auth_routes import login_required
from services.like_service import LikeService

logger = logging.getLogger(__name__)

feed_bp = Blueprint('feed', __name__)

# Initialize services
db = firestore.client()
like_service = LikeService()


@feed_bp.route('/api/feed/explore', methods=['GET'])
def get_explore_feed():
    """
    Get the public Explore feed of published creations.

    Query params:
        limit: Max creations to return (default 20, max 50)
        cursor: Pagination cursor (last creationId from previous page)

    Returns:
        200: {
            success: true,
            creations: [{
                creationId: string,
                userId: string,
                username: string,  // denormalized for performance
                prompt: string,
                mediaUrl: string,
                aspectRatio: string,
                duration: number,
                likeCount: number,
                publishedAt: timestamp,
                isLiked: boolean  // only if user is authenticated
            }],
            nextCursor: string | null
        }
    """
    try:
        # Parse query params
        limit = min(int(request.args.get('limit', 20)), 50)
        cursor = request.args.get('cursor')

        # Query published creations
        query = (db.collection('creations')
                .where('status', '==', 'published')
                .order_by('publishedAt', direction=firestore.Query.DESCENDING)
                .limit(limit + 1))  # +1 to check if there are more

        if cursor:
            # Get cursor document for pagination
            cursor_doc = db.collection('creations').document(cursor).get()
            if cursor_doc.exists:
                query = query.start_after(cursor_doc)

        # Execute query
        docs = list(query.stream())
        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]  # Remove extra doc

        # Get current user ID if authenticated
        user_id = session.get('user_id')

        # Collect creation IDs for batch like check
        creation_ids = [doc.id for doc in docs]

        # Batch check likes if user is authenticated
        liked_map = {}
        if user_id and creation_ids:
            liked_map = like_service.check_multiple_likes(user_id, creation_ids)

        # Format response
        creations = []
        for doc in docs:
            data = doc.to_dict()
            creations.append({
                'creationId': doc.id,
                'userId': data.get('userId'),
                'username': data.get('username', 'Unknown'),  # Denormalized
                'prompt': data.get('prompt'),
                'caption': data.get('caption', ''),
                'mediaUrl': data.get('mediaUrl'),
                'aspectRatio': data.get('aspectRatio', '9:16'),
                'duration': data.get('duration', 8),
                'likeCount': data.get('likeCount', 0),
                'publishedAt': data.get('publishedAt'),
                'isLiked': liked_map.get(doc.id, False) if user_id else False
            })

        # Determine next cursor
        next_cursor = docs[-1].id if has_more and docs else None

        return jsonify({
            'success': True,
            'creations': creations,
            'nextCursor': next_cursor,
            'hasMore': has_more
        })

    except Exception as e:
        logger.error(f"Error fetching explore feed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load feed'
        }), 500


@feed_bp.route('/api/users/<username>/creations', methods=['GET'])
def get_user_creations(username):
    """
    Get a user's published creations (public gallery).

    Path params:
        username: Username to look up

    Query params:
        limit: Max creations to return (default 20, max 50)
        cursor: Pagination cursor

    Returns:
        200: { success: true, creations: [...], user: {...}, nextCursor: ... }
        404: User not found
    """
    try:
        # Look up user by username
        username_lower = username.lower()
        username_ref = db.collection('usernames').document(username_lower)
        username_doc = username_ref.get()

        if not username_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        user_id = username_doc.get('userId')

        # Get user profile
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User profile not found'
            }), 404

        user_data = user_doc.to_dict()

        # Parse query params
        limit = min(int(request.args.get('limit', 20)), 50)
        cursor = request.args.get('cursor')

        # Query user's published creations
        query = (db.collection('creations')
                .where('userId', '==', user_id)
                .where('status', '==', 'published')
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

        # Get current user for like status
        current_user_id = session.get('user_id')
        creation_ids = [doc.id for doc in docs]

        # Batch check likes
        liked_map = {}
        if current_user_id and creation_ids:
            liked_map = like_service.check_multiple_likes(current_user_id, creation_ids)

        # Format creations
        creations = []
        for doc in docs:
            data = doc.to_dict()
            creations.append({
                'creationId': doc.id,
                'prompt': data.get('prompt'),
                'caption': data.get('caption', ''),
                'mediaUrl': data.get('mediaUrl'),
                'aspectRatio': data.get('aspectRatio', '9:16'),
                'duration': data.get('duration', 8),
                'likeCount': data.get('likeCount', 0),
                'publishedAt': data.get('publishedAt'),
                'isLiked': liked_map.get(doc.id, False) if current_user_id else False
            })

        next_cursor = docs[-1].id if has_more and docs else None

        return jsonify({
            'success': True,
            'user': {
                'username': user_data.get('username'),
                'displayName': user_data.get('displayName'),
                'bio': user_data.get('bio'),
                'profileImageUrl': user_data.get('profileImageUrl'),
                'totalTokensEarned': user_data.get('totalTokensEarned', 0)
            },
            'creations': creations,
            'nextCursor': next_cursor,
            'hasMore': has_more
        })

    except Exception as e:
        logger.error(f"Error fetching creations for user '{username}': {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load user creations'
        }), 500


@feed_bp.route('/api/creations/<creation_id>/like', methods=['POST'])
@login_required
def like_creation(creation_id):
    """
    Like a creation (idempotent).

    Path params:
        creation_id: Creation document ID

    Returns:
        200: { success: true, liked: true, likeCount: number }
        404: Creation not found
        500: Server error
    """
    user_id = session.get('user_id')

    try:
        # Verify creation exists and is published
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({
                'success': False,
                'error': 'Creation not found'
            }), 404

        creation_data = creation_doc.to_dict()
        if creation_data.get('status') != 'published':
            return jsonify({
                'success': False,
                'error': 'Cannot like unpublished creation'
            }), 400

        # Attempt to like (idempotent)
        was_added = like_service.like_post(user_id, creation_id)

        # Increment like count on creation (atomic)
        if was_added:
            creation_ref.update({
                'likeCount': firestore.Increment(1)
            })

            logger.info(f"User {user_id} liked creation {creation_id}")

        # Get updated like count
        updated_doc = creation_ref.get()
        like_count = updated_doc.get('likeCount') if updated_doc.exists else 0

        return jsonify({
            'success': True,
            'liked': True,
            'likeCount': like_count,
            'wasAdded': was_added
        })

    except Exception as e:
        logger.error(f"Error liking creation {creation_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to like creation'
        }), 500


@feed_bp.route('/api/creations/<creation_id>/like', methods=['DELETE'])
@login_required
def unlike_creation(creation_id):
    """
    Unlike a creation.

    Path params:
        creation_id: Creation document ID

    Returns:
        200: { success: true, liked: false, likeCount: number }
        404: Creation not found
        500: Server error
    """
    user_id = session.get('user_id')

    try:
        # Verify creation exists
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({
                'success': False,
                'error': 'Creation not found'
            }), 404

        # Attempt to unlike
        was_removed = like_service.unlike_post(user_id, creation_id)

        # Decrement like count (atomic)
        if was_removed:
            creation_ref.update({
                'likeCount': firestore.Increment(-1)
            })

            logger.info(f"User {user_id} unliked creation {creation_id}")

        # Get updated like count
        updated_doc = creation_ref.get()
        like_count = updated_doc.get('likeCount') if updated_doc.exists else 0

        return jsonify({
            'success': True,
            'liked': False,
            'likeCount': like_count,
            'wasRemoved': was_removed
        })

    except Exception as e:
        logger.error(f"Error unliking creation {creation_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to unlike creation'
        }), 500


@feed_bp.route('/api/creations/<creation_id>/likes', methods=['GET'])
def get_creation_likes(creation_id):
    """
    Get like information for a creation.

    Path params:
        creation_id: Creation document ID

    Returns:
        200: {
            success: true,
            likeCount: number,
            isLiked: boolean  // only if authenticated
        }
        404: Creation not found
    """
    try:
        # Get creation
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({
                'success': False,
                'error': 'Creation not found'
            }), 404

        creation_data = creation_doc.to_dict()
        like_count = creation_data.get('likeCount', 0)

        # Check if current user has liked (if authenticated)
        user_id = session.get('user_id')
        is_liked = False
        if user_id:
            is_liked = like_service.check_if_liked(user_id, creation_id)

        return jsonify({
            'success': True,
            'likeCount': like_count,
            'isLiked': is_liked
        })

    except Exception as e:
        logger.error(f"Error fetching likes for creation {creation_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch like information'
        }), 500
