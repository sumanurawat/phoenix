"""Feed and Social Interaction API Routes

Handles the public feed (Explore) and social interactions.

Endpoints:
- GET /api/feed/explore - Public feed of published creations
- GET /api/users/<username>/creations - User gallery
- PATCH /api/creations/<id>/caption - Update caption
- POST /api/creations/<id>/comments - Add comment
- GET /api/creations/<id>/comments - Get comments
"""
import logging
from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore

from api.auth_routes import login_required

logger = logging.getLogger(__name__)

feed_bp = Blueprint('feed', __name__)

# Initialize services
db = firestore.client()


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
                .where(filter=firestore.FieldFilter('status', '==', 'published'))
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

        # Get current user ID for privacy checks
        current_user_id = session.get('user_id')

        # Format response
        creations = []
        for doc in docs:
            data = doc.to_dict()
            creation_data = {
                'creationId': doc.id,
                'userId': data.get('userId'),
                'username': data.get('username', 'Unknown'),  # Denormalized
                'caption': data.get('caption', ''),
                'mediaUrl': data.get('mediaUrl'),
                'mediaType': data.get('mediaType', 'video'),
                'aspectRatio': data.get('aspectRatio', '9:16'),
                'duration': data.get('duration', 8),
                'commentCount': data.get('commentCount', 0),  # NEW: Comment count
                'publishedAt': data.get('publishedAt'),
                # PRIVACY: Only include actual prompt if viewing own creation
                'prompt': data.get('prompt', '') if (current_user_id and current_user_id == data.get('userId')) else ''
            }
            
            creations.append(creation_data)

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
                .where(filter=firestore.FieldFilter('userId', '==', user_id))
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

        # Check if current user is viewing their own profile
        current_user_id = session.get('user_id')
        is_own_profile = (current_user_id == user_id)

        # Format creations
        creations = []
        for doc in docs:
            data = doc.to_dict()
            creation_data = {
                'creationId': doc.id,
                'caption': data.get('caption', ''),
                'mediaUrl': data.get('mediaUrl'),
                'mediaType': data.get('mediaType', 'video'),
                'aspectRatio': data.get('aspectRatio', '9:16'),
                'duration': data.get('duration', 8),
                'commentCount': data.get('commentCount', 0),  # NEW: Comment count
                'publishedAt': data.get('publishedAt')
            }
            
            # PRIVACY: Only include prompt if viewing own profile
            if is_own_profile:
                creation_data['prompt'] = data.get('prompt')
            
            creations.append(creation_data)

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


@feed_bp.route('/api/creations/<creation_id>/caption', methods=['PATCH'])
@login_required
def update_caption(creation_id):
    """
    Update the caption of a creation (owner only).

    Path params:
        creation_id: Creation document ID

    Request body:
        {
            "caption": "New caption text"
        }

    Returns:
        200: { success: true, caption: "..." }
        403: Not authorized (not owner)
        404: Creation not found
        500: Server error
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400

        caption = data.get('caption', '').strip()

        # Get the creation document
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({
                'success': False,
                'error': 'Creation not found'
            }), 404

        creation_data = creation_doc.to_dict()

        # Check if user is the owner
        if creation_data.get('userId') != user_id:
            return jsonify({
                'success': False,
                'error': 'You can only edit your own creations'
            }), 403

        # Update caption
        creation_ref.update({
            'caption': caption,
            'updatedAt': firestore.SERVER_TIMESTAMP
        })

        logger.info(f"Updated caption for creation {creation_id} by user {user_id}")

        return jsonify({
            'success': True,
            'caption': caption
        })

    except Exception as e:
        logger.error(f"Error updating caption for creation {creation_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update caption'
        }), 500


@feed_bp.route('/api/creations/<creation_id>/comments', methods=['POST'])
@login_required
def add_comment(creation_id):
    """
    Add a comment to a creation.

    Path params:
        creation_id: Creation document ID

    Request body:
        {
            "commentText": "The comment text"
        }

    Returns:
        200: {
            success: true,
            comment: {
                commentId: string,
                userId: string,
                username: string,
                avatarUrl: string,
                commentText: string,
                createdAt: timestamp
            }
        }
        400: Invalid request
        404: Creation not found
        500: Server error
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400

        comment_text = data.get('commentText', '').strip()
        if not comment_text:
            return jsonify({
                'success': False,
                'error': 'Comment text is required'
            }), 400

        if len(comment_text) > 500:
            return jsonify({
                'success': False,
                'error': 'Comment text must be 500 characters or less'
            }), 400

        # Get creation document
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({
                'success': False,
                'error': 'Creation not found'
            }), 404

        # Get user data for denormalization
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        user_data = user_doc.to_dict()

        # Use transaction to atomically add comment and increment count
        @firestore.transactional
        def create_comment_transaction(transaction):
            # Create comment document in subcollection
            comment_ref = creation_ref.collection('comments').document()
            comment_data = {
                'userId': user_id,
                'username': user_data.get('username', 'Unknown'),
                'avatarUrl': user_data.get('profileImageUrl', ''),
                'commentText': comment_text,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'replyToCommentId': None  # Future-proofing for threaded comments
            }

            transaction.set(comment_ref, comment_data)

            # Increment comment count on parent creation
            transaction.update(creation_ref, {
                'commentCount': firestore.Increment(1)
            })

            return comment_ref.id, comment_data

        # Execute transaction
        transaction = db.transaction()
        comment_id, comment_data = create_comment_transaction(transaction)

        logger.info(f"User {user_id} added comment to creation {creation_id}")

        # Fetch the created comment to get the actual timestamp
        comment_ref = creation_ref.collection('comments').document(comment_id)
        created_comment = comment_ref.get()

        if created_comment.exists:
            final_comment_data = created_comment.to_dict()
        else:
            # Fallback if fetch fails - use current time
            from datetime import datetime
            final_comment_data = {
                **comment_data,
                'createdAt': datetime.utcnow()
            }

        # Return the created comment with actual timestamp
        return jsonify({
            'success': True,
            'comment': {
                'commentId': comment_id,
                'userId': final_comment_data['userId'],
                'username': final_comment_data['username'],
                'avatarUrl': final_comment_data['avatarUrl'],
                'commentText': final_comment_data['commentText'],
                'createdAt': final_comment_data.get('createdAt')
            }
        })

    except Exception as e:
        logger.error(f"Error adding comment to creation {creation_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to add comment'
        }), 500


@feed_bp.route('/api/creations/<creation_id>/comments', methods=['GET'])
def get_comments(creation_id):
    """
    Get comments for a creation with pagination.

    Path params:
        creation_id: Creation document ID

    Query params:
        limit: Max comments to return (default 20, max 50)
        startAfter: Comment ID to start after (for pagination)

    Returns:
        200: {
            success: true,
            comments: [{
                commentId: string,
                userId: string,
                username: string,
                avatarUrl: string,
                commentText: string,
                createdAt: timestamp
            }],
            hasMore: boolean
        }
        404: Creation not found
        500: Server error
    """
    try:
        # Verify creation exists
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({
                'success': False,
                'error': 'Creation not found'
            }), 404

        # Parse query params
        limit = min(int(request.args.get('limit', 20)), 50)
        start_after = request.args.get('startAfter')

        # Build query - chronological order (oldest first)
        query = (creation_ref.collection('comments')
                .order_by('createdAt', direction=firestore.Query.ASCENDING)
                .limit(limit + 1))  # +1 to check if there are more

        if start_after:
            # Get cursor document for pagination
            cursor_doc = creation_ref.collection('comments').document(start_after).get()
            if cursor_doc.exists:
                query = query.start_after(cursor_doc)

        # Execute query
        docs = list(query.stream())
        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]  # Remove extra doc

        # Format response
        comments = []
        for doc in docs:
            data = doc.to_dict()
            comments.append({
                'commentId': doc.id,
                'userId': data.get('userId'),
                'username': data.get('username', 'Unknown'),
                'avatarUrl': data.get('avatarUrl', ''),
                'commentText': data.get('commentText'),
                'createdAt': data.get('createdAt')
            })

        return jsonify({
            'success': True,
            'comments': comments,
            'hasMore': has_more
        })

    except Exception as e:
        logger.error(f"Error fetching comments for creation {creation_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch comments'
        }), 500
