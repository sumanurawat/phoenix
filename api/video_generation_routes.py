"""Video Generation API Routes

Handles asynchronous video generation requests with Sora-style drafts management.

Endpoints:
- POST /api/generate/video - Create new generation (debit tokens, queue job)
- GET /api/generate/drafts - List all user's creations (pending, processing, draft, failed)
- GET /api/generate/video/<id> - Get single creation status
- DELETE /api/generate/video/<id> - Delete draft/failed creation
- POST /api/generate/video/<id>/publish - Publish draft to feed
"""
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore
from kombu.exceptions import OperationalError as KombuOperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

from api.auth_routes import login_required
from services.token_service import TokenService, InsufficientTokensError
from services.transaction_service import TransactionService
from jobs.async_video_generation_worker import generate_video_task

logger = logging.getLogger(__name__)

QUEUE_UNAVAILABLE_ERROR = (
    "Video generation queue is unavailable. Start the Redis service and retry."
)

video_generation_bp = Blueprint('video_generation', __name__, url_prefix='/api/generate')

# Constants
VIDEO_GENERATION_COST = 10  # tokens

# Initialize services
token_service = TokenService()
transaction_service = TransactionService()
db = firestore.client()


def _handle_enqueue_failure(user_id: str, creation_id: str, queue_error: Exception) -> None:
    """Rollback token debit and mark creation as failed when queue is down."""

    logger.error(
        "🚨 Video generation queue unavailable for creation %s: %s",
        creation_id,
        queue_error,
        exc_info=True
    )

    try:
        @firestore.transactional
        def rollback(transaction):
            user_ref = db.collection('users').document(user_id)
            creation_ref = db.collection('creations').document(creation_id)

            # Refund tokens and revert spend counter
            transaction.update(user_ref, {
                'tokenBalance': firestore.Increment(VIDEO_GENERATION_COST),
                'totalTokensSpent': firestore.Increment(-VIDEO_GENERATION_COST)
            })

            creation_snapshot = creation_ref.get(transaction=transaction)
            if creation_snapshot.exists:
                transaction.update(creation_ref, {
                    'status': 'failed',
                    'error': 'queue_unavailable',
                    'queueErrorCode': 'redis_connection_refused',
                    'queueErrorMessage': str(queue_error)[:200],
                    'refunded': True,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })

                # Record refund transaction to keep ledger balanced
                refund_ref = db.collection('transactions').document()
                transaction.set(refund_ref, {
                    'userId': user_id,
                    'type': 'video_generation_refund',
                    'amount': VIDEO_GENERATION_COST,
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'details': {
                        'creationId': creation_id,
                        'reason': 'queue_unavailable'
                    }
                })

        transaction = db.transaction()
        rollback(transaction)
        logger.info(
            "💰 Refunded tokens and marked creation %s as failed due to queue outage",
            creation_id
        )

    except Exception as rollback_error:
        logger.error(
            "Failed to rollback after queue outage for creation %s: %s",
            creation_id,
            rollback_error,
            exc_info=True
        )

@video_generation_bp.route('/video', methods=['POST'])
@login_required
def generate_video():
    """
    Generate video asynchronously with token debit.

    Creates a creation document in 'pending' state and enqueues background job.
    Returns immediately (202 Accepted) - user polls for status.

    Request:
        {
            "prompt": "A serene sunset over mountains",
            "aspectRatio": "9:16",  // optional, default "9:16"
            "duration": 8            // optional, default 8, must be 4|6|8
        }

    Response (202 Accepted):
        {
            "success": true,
            "creationId": "uuid-here",
            "cost": 10,
            "status": "pending",
            "estimatedTime": "60-120 seconds"
        }

    Error Responses:
        400 - Invalid request (missing prompt, invalid params)
        402 - Insufficient tokens
        500 - Internal server error
    """
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        # Validate request
        prompt = data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400

        if len(prompt) > 500:
            return jsonify({'success': False, 'error': 'Prompt must be 500 characters or less'}), 400

        aspect_ratio = data.get('aspectRatio', '9:16')
        duration = data.get('duration', 8)

        # Validate parameters
        if aspect_ratio not in ['16:9', '9:16']:
            return jsonify({'success': False, 'error': 'Invalid aspect ratio (must be 16:9 or 9:16)'}), 400

        if duration not in [4, 6, 8]:
            return jsonify({'success': False, 'error': 'Duration must be 4, 6, or 8 seconds'}), 400

        logger.info(f"🎬 Video generation request from user {user_id}: {prompt[:50]}...")

        # Generate creation ID
        creation_id = str(uuid.uuid4())

        # Check token balance first (fast failure)
        current_balance = token_service.get_balance(user_id)
        if current_balance < VIDEO_GENERATION_COST:
            logger.warning(f"Insufficient tokens for {user_id}: has {current_balance}, needs {VIDEO_GENERATION_COST}")
            return jsonify({
                'success': False,
                'error': 'Insufficient tokens',
                'required': VIDEO_GENERATION_COST,
                'balance': current_balance
            }), 402  # Payment Required

        # Atomic transaction: debit tokens + create transaction record + create creation document
        @firestore.transactional
        def debit_and_create(transaction):
            user_ref = db.collection('users').document(user_id)
            creation_ref = db.collection('creations').document(creation_id)

            # 1. Check balance again (within transaction)
            user_doc = user_ref.get(transaction=transaction)
            if not user_doc.exists:
                raise ValueError("User not found")

            balance = user_doc.to_dict().get('tokenBalance', 0)
            if balance < VIDEO_GENERATION_COST:
                raise InsufficientTokensError(f"Insufficient tokens: {balance} < {VIDEO_GENERATION_COST}")

            # 2. Debit tokens
            transaction.update(user_ref, {
                'tokenBalance': firestore.Increment(-VIDEO_GENERATION_COST),
                'totalTokensSpent': firestore.Increment(VIDEO_GENERATION_COST)
            })

            # 3. Create creation document (visible in drafts immediately)
            creation_data = {
                'userId': user_id,
                'prompt': prompt,
                'aspectRatio': aspect_ratio,
                'duration': duration,
                'cost': VIDEO_GENERATION_COST,
                'status': 'pending',
                'progress': 0.0,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            transaction.set(creation_ref, creation_data)

            # 4. Record transaction
            tx_ref = db.collection('transactions').document()
            transaction.set(tx_ref, {
                'userId': user_id,
                'type': 'video_generation',
                'amount': -VIDEO_GENERATION_COST,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'details': {
                    'creationId': creation_id,
                    'prompt': prompt[:100]  # Truncate for storage
                }
            })

        # Execute transaction
        try:
            transaction = db.transaction()
            debit_and_create(transaction)
            logger.info(f"✅ Debited {VIDEO_GENERATION_COST} tokens from {user_id} for creation {creation_id}")
        except InsufficientTokensError as e:
            logger.warning(f"Insufficient tokens during transaction: {e}")
            return jsonify({
                'success': False,
                'error': 'Insufficient tokens',
                'required': VIDEO_GENERATION_COST
            }), 402

        # Enqueue background job (with queue failure handling)
        try:
            task = generate_video_task.apply_async(
                args=[creation_id],
                task_id=creation_id,  # Use creation_id as task_id for idempotency
                countdown=2  # 2 second delay to ensure Firestore write completes
            )
            logger.info(f"🚀 Enqueued video generation job: {task.id}")
        except (RedisConnectionError, KombuOperationalError) as queue_error:
            # Queue is down (Redis not running locally or network issues in prod)
            _handle_enqueue_failure(user_id, creation_id, queue_error)

            return jsonify({
                'success': False,
                'error': QUEUE_UNAVAILABLE_ERROR,
                'refunded': True,
                'details': (
                    'The video generation service is temporarily unavailable. '
                    'Your tokens have been refunded automatically.'
                )
            }), 503  # Service Unavailable

        return jsonify({
            'success': True,
            'creationId': creation_id,
            'cost': VIDEO_GENERATION_COST,
            'status': 'pending',
            'estimatedTime': '60-120 seconds'
        }), 202  # Accepted

    except Exception as e:
        logger.error(f"Failed to generate video: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@video_generation_bp.route('/drafts', methods=['GET'])
@login_required
def get_drafts():
    """
    Get all user's creations (Sora-style drafts view).

    Returns all creations regardless of status (pending, processing, draft, failed).
    Sorted by creation time (most recent first).

    Query Parameters:
        status: Filter by status (optional) - "pending" | "processing" | "draft" | "failed"
        limit: Number of results (optional, default 50, max 100)

    Response:
        {
            "success": true,
            "creations": [
                {
                    "id": "uuid",
                    "prompt": "...",
                    "status": "draft",
                    "mediaUrl": "https://...",  // if status == "draft"
                    "progress": 0.8,            // if status == "processing"
                    "error": "...",             // if status == "failed"
                    "createdAt": "2025-01-01T00:00:00Z",
                    "updatedAt": "2025-01-01T00:02:00Z",
                    "aspectRatio": "9:16",
                    "duration": 8
                },
                ...
            ],
            "total": 42
        }
    """
    try:
        user_id = session.get('user_id')

        # Query parameters
        status_filter = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)

        logger.info(f"📋 Fetching drafts for user {user_id} (status={status_filter}, limit={limit})")

        # Build query
        query = db.collection('creations').where('userId', '==', user_id)

        # Filter by status if provided
        if status_filter and status_filter in ['pending', 'processing', 'draft', 'failed', 'published']:
            query = query.where('status', '==', status_filter)

        # Order by creation time (most recent first)
        query = query.order_by('createdAt', direction=firestore.Query.DESCENDING).limit(limit)

        # Execute query
        creations_docs = query.stream()

        creations = []
        for doc in creations_docs:
            creation_data = doc.to_dict()
            creation_data['id'] = doc.id

            # Convert timestamps to ISO format
            if 'createdAt' in creation_data and creation_data['createdAt']:
                creation_data['createdAt'] = creation_data['createdAt'].isoformat()
            if 'updatedAt' in creation_data and creation_data['updatedAt']:
                creation_data['updatedAt'] = creation_data['updatedAt'].isoformat()

            creations.append(creation_data)

        logger.info(f"✅ Found {len(creations)} creations for user {user_id}")

        return jsonify({
            'success': True,
            'creations': creations,
            'total': len(creations)
        })

    except Exception as e:
        logger.error(f"Failed to get drafts: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@video_generation_bp.route('/creation/<creation_id>', methods=['GET'])
@video_generation_bp.route('/video/<creation_id>', methods=['GET'])
@login_required
def get_creation_status(creation_id):
    """
    Get the status of a single creation.

    Response:
        {
            "success": true,
            "creation": {
                "id": "uuid",
                "status": "pending|processing|draft|failed",
                "mediaUrl": "https://...",  // if status == "draft"
                "error": "...",  // if status == "failed"
                "progress": 0.75,  // if status == "processing"
                ...
            }
        }
    """
    try:
        user_id = session.get('user_id')

        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({'success': False, 'error': 'Creation not found'}), 404

        creation_data = creation_doc.to_dict()

        # Verify ownership
        if creation_data.get('userId') != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Convert timestamps
        if 'createdAt' in creation_data and creation_data['createdAt']:
            creation_data['createdAt'] = creation_data['createdAt'].isoformat()
        if 'updatedAt' in creation_data and creation_data['updatedAt']:
            creation_data['updatedAt'] = creation_data['updatedAt'].isoformat()

        creation_data['id'] = creation_id

        return jsonify({
            'success': True,
            'creation': creation_data
        })

    except Exception as e:
        logger.error(f"Failed to get creation status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@video_generation_bp.route('/creation/<creation_id>', methods=['DELETE'])
@video_generation_bp.route('/creation/<creation_id>', methods=['DELETE'])
@video_generation_bp.route('/video/<creation_id>', methods=['DELETE'])
@login_required
def delete_creation(creation_id):
    """
    Delete a draft or failed creation.

    Only allowed for status: draft, failed
    Not allowed for: pending, processing, published

    Response:
        {
            "success": true,
            "message": "Creation deleted"
        }
    """
    try:
        user_id = session.get('user_id')

        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({'success': False, 'error': 'Creation not found'}), 404

        creation_data = creation_doc.to_dict()

        # Verify ownership
        if creation_data.get('userId') != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Check status - only allow deletion of draft or failed
        status = creation_data.get('status')
        if status not in ['draft', 'failed']:
            return jsonify({
                'success': False,
                'error': f'Cannot delete creation with status: {status}',
                'allowedStatuses': ['draft', 'failed']
            }), 400

        # Delete from Firestore
        creation_ref.delete()

        logger.info(f"🗑️  Deleted creation {creation_id} (status: {status}) for user {user_id}")

        # TODO: Also delete video from R2 if mediaUrl exists
        # (Implement in Phase 4 to avoid leaving orphaned files)

        return jsonify({
            'success': True,
            'message': 'Creation deleted'
        })

    except Exception as e:
        logger.error(f"Failed to delete creation: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@video_generation_bp.route('/creation/<creation_id>/publish', methods=['POST'])
@video_generation_bp.route('/video/<creation_id>/publish', methods=['POST'])
@login_required
def publish_creation(creation_id):
    """
    Publish a draft creation to the social feed.

    Changes status from 'draft' to 'published' and denormalizes user data for feed performance.

    Request:
        {
            "caption": "Check out my AI-generated video!" // optional
        }

    Response:
        {
            "success": true,
            "creationId": "uuid",
            "message": "Creation published"
        }
    """
    try:
        user_id = session.get('user_id')
        data = request.get_json() or {}

        caption = data.get('caption', '').strip()

        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({'success': False, 'error': 'Creation not found'}), 404

        creation_data = creation_doc.to_dict()

        # Verify ownership
        if creation_data.get('userId') != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Check status - only allow publishing drafts
        if creation_data.get('status') != 'draft':
            return jsonify({
                'success': False,
                'error': f'Cannot publish creation with status: {creation_data.get("status")}',
                'requiredStatus': 'draft'
            }), 400

        # Check if mediaUrl exists
        media_url = creation_data.get('mediaUrl')
        if not media_url:
            return jsonify({
                'success': False,
                'error': 'Creation has no media URL'
            }), 400

        # Get user profile for denormalization
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        username = 'Unknown'
        if user_doc.exists:
            user_data = user_doc.to_dict()
            username = user_data.get('username', 'Unknown')

        # Update creation to published status with denormalized data
        creation_ref.update({
            'status': 'published',
            'publishedAt': firestore.SERVER_TIMESTAMP,
            'caption': caption,
            'username': username,  # Denormalize for feed performance
            'likeCount': 0,
            'updatedAt': firestore.SERVER_TIMESTAMP
        })

        logger.info(f"🚀 Published creation {creation_id} for user {user_id} (@{username})")

        return jsonify({
            'success': True,
            'creationId': creation_id,
            'message': 'Creation published to feed'
        })

    except Exception as e:
        logger.error(f"Failed to publish creation: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
