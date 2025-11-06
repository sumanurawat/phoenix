"""Unified Creation API Routes

Single endpoint for all content generation (images and videos).
Implements the draft-first workflow where all content starts as pending drafts.

Endpoints:
- POST /api/generate/creation - Create new generation (unified for image/video)
- GET /api/generate/drafts - List all user's non-published creations
- GET /api/generate/creation/<id> - Get single creation status
- DELETE /api/generate/creation/<id> - Delete draft/failed creation
- POST /api/generate/creation/<id>/publish - Publish draft to feed
"""
import logging
from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore
from kombu.exceptions import OperationalError as KombuOperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

from api.auth_routes import login_required
from middleware.csrf_protection import csrf_protect
from services.creation_service import CreationService
from services.token_service import InsufficientTokensError
from jobs.async_image_generation_worker import generate_image_task
from jobs.async_video_generation_worker import generate_video_task

logger = logging.getLogger(__name__)

generation_bp = Blueprint('generation', __name__, url_prefix='/api/generate')

# Initialize services
creation_service = CreationService()

QUEUE_UNAVAILABLE_ERROR = (
    "Generation queue is unavailable. Start the Redis service and retry."
)


@generation_bp.route('/creation', methods=['POST'])
@login_required
@csrf_protect
def create_generation():
    """
    Unified creation endpoint for both images and videos.

    Creates a pending draft immediately, debits tokens, and enqueues background job.
    Returns 202 Accepted - user should check drafts tab for progress.

    Request:
        {
            "prompt": "A serene sunset over mountains",
            "type": "image" | "video",
            "aspectRatio": "9:16",  // optional
            "duration": 8            // optional, video only
        }

    Response (202 Accepted):
        {
            "success": true,
            "creationId": "uuid-here",
            "type": "image" | "video",
            "cost": 1 | 10,
            "status": "pending"
        }

    Error Responses:
        400 - Invalid request
        402 - Insufficient tokens
        503 - Queue unavailable (tokens refunded)
        500 - Internal server error
    """
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        # Validate request
        prompt = data.get('prompt', '').strip()
        creation_type = data.get('type', '').lower()

        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400

        if creation_type not in ['image', 'video']:
            return jsonify({
                'success': False,
                'error': 'Type must be "image" or "video"'
            }), 400

        # Get optional parameters
        aspect_ratio = data.get('aspectRatio', '9:16')
        duration = data.get('duration', 8) if creation_type == 'video' else None

        # Validate video-specific parameters
        if creation_type == 'video':
            if aspect_ratio not in ['16:9', '9:16']:
                return jsonify({
                    'success': False,
                    'error': 'Invalid aspect ratio (must be 16:9 or 9:16)'
                }), 400

            if duration not in [4, 6, 8]:
                return jsonify({
                    'success': False,
                    'error': 'Duration must be 4, 6, or 8 seconds'
                }), 400

        logger.info(
            f"🎨 {creation_type.capitalize()} generation request from user {user_id}: "
            f"{prompt[:50]}..."
        )

        # Create pending draft with atomic token debit
        try:
            extra_params = {'aspectRatio': aspect_ratio}
            if creation_type == 'video':
                extra_params['duration'] = duration

            creation_id, transaction_id = creation_service.create_pending_creation(
                user_id=user_id,
                prompt=prompt,
                creation_type=creation_type,
                **extra_params
            )

            logger.info(
                f"✅ Created pending {creation_type} creation {creation_id} "
                f"with transaction {transaction_id}"
            )

        except InsufficientTokensError as e:
            cost = 1 if creation_type == 'image' else 10
            logger.warning(f"Insufficient tokens for {user_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Insufficient tokens',
                'required': cost
            }), 402

        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400

        # Enqueue background job
        try:
            if creation_type == 'image':
                task = generate_image_task.apply_async(
                    args=[creation_id, prompt, transaction_id, user_id],
                    task_id=creation_id,
                    countdown=1
                )
            else:  # video
                task = generate_video_task.apply_async(
                    args=[creation_id],
                    task_id=creation_id,
                    countdown=2
                )

            logger.info(f"🚀 Enqueued {creation_type} generation job: {task.id}")

        except (RedisConnectionError, KombuOperationalError) as queue_error:
            # Queue is down - rollback via creation service
            logger.error(
                f"🚨 Queue unavailable for creation {creation_id}: {queue_error}",
                exc_info=True
            )

            creation_service.handle_generation_failure(
                creation_id=creation_id,
                original_transaction_id=transaction_id,
                error_message='queue_unavailable',
                user_id=user_id
            )

            return jsonify({
                'success': False,
                'error': QUEUE_UNAVAILABLE_ERROR,
                'refunded': True,
                'details': (
                    f'The {creation_type} generation service is temporarily unavailable. '
                    'Your tokens have been refunded automatically.'
                )
            }), 503

        # Return 202 Accepted
        cost = 1 if creation_type == 'image' else 10
        return jsonify({
            'success': True,
            'creationId': creation_id,
            'type': creation_type,
            'cost': cost,
            'status': 'pending',
            'estimatedTime': '10-15 seconds' if creation_type == 'image' else '60-120 seconds'
        }), 202

    except Exception as e:
        logger.error(f"Failed to create generation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@generation_bp.route('/drafts', methods=['GET'])
@login_required
def get_drafts():
    """
    Get all user's non-published creations (draft-first view).

    Returns all creations with status != 'published', sorted by creation time.
    This includes: pending, processing, draft, and failed.

    Query Parameters:
        status: Filter by status (optional)
        limit: Number of results (optional, default 50, max 100)

    Response:
        {
            "success": true,
            "creations": [
                {
                    "id": "uuid",
                    "mediaType": "image" | "video",
                    "prompt": "...",
                    "status": "pending" | "processing" | "draft" | "failed",
                    "mediaUrl": "https://...",  // if status == "draft"
                    "progress": 0.8,            // if status == "processing"
                    "error": "...",             // if status == "failed"
                    "createdAt": "2025-11-06T00:00:00Z",
                    ...
                },
                ...
            ],
            "total": 42
        }
    """
    try:
        user_id = session.get('user_id')

        # Auto-cleanup: Mark stale creations as failed (older than 1 hour)
        # This runs in background to avoid blocking the response
        try:
            stale_count = creation_service.mark_stale_creations_as_failed(max_age_hours=1.0)
            if stale_count > 0:
                logger.info(f"🧹 Auto-cleanup: Marked {stale_count} stale creations as failed")
        except Exception as cleanup_error:
            logger.warning(f"Auto-cleanup failed (non-critical): {cleanup_error}")

        # Get query parameters
        status_filter = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)

        # Query Firestore (without ordering to avoid index requirement)
        db = creation_service.db
        query = db.collection('creations').where('userId', '==', user_id)

        # Filter by status if requested
        if status_filter:
            query = query.where('status', '==', status_filter)
        
        # Note: No order_by to avoid composite index requirement
        # We'll sort in Python after fetching
        query = query.limit(limit)

        docs = query.stream()

        creations = []
        for doc in docs:
            creation_data = doc.to_dict()
            creation_data['id'] = doc.id

            # Filter out published if no specific status requested
            if not status_filter and creation_data.get('status') == 'published':
                continue

            creations.append(creation_data)

        # Sort by createdAt in Python (newest first)
        creations.sort(key=lambda x: x.get('createdAt', 0), reverse=True)

        logger.info(f"📋 Retrieved {len(creations)} drafts for user {user_id}")

        return jsonify({
            'success': True,
            'creations': creations,
            'total': len(creations)
        })

    except Exception as e:
        logger.error(f"Failed to get drafts: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load drafts'
        }), 500
