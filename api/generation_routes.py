"""Unified Creation API Routes

Single endpoint for all content generation (images and videos).
Implements the draft-first workflow where all content starts as pending drafts.

**ARCHITECTURE**:
- Images: Cloud Run Jobs API (serverless) ✅
- Videos: Cloud Run Jobs API (serverless) ✅
- Legacy Celery/Redis infrastructure: FULLY DECOMMISSIONED ✅

Endpoints:
- POST /api/generate/creation - Create new generation (unified for image/video)
- GET /api/generate/drafts - List all user's non-published creations
- GET /api/generate/creation/<id> - Get single creation status
- DELETE /api/generate/creation/<id> - Delete draft/failed creation
- POST /api/generate/creation/<id>/publish - Publish draft to feed
"""
import json
import logging
import os
from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore

try:
    from google.cloud import run_v2
    CLOUD_RUN_AVAILABLE = True
except ImportError:
    CLOUD_RUN_AVAILABLE = False
    run_v2 = None

from api.auth_routes import login_required
from middleware.csrf_protection import csrf_protect
from services.creation_service import CreationService
from services.token_service import InsufficientTokensError

logger = logging.getLogger(__name__)

generation_bp = Blueprint('generation', __name__, url_prefix='/api/generate')

# Initialize services
creation_service = CreationService()

# Cloud Run Jobs configuration
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'phoenix-project-386')
REGION = 'us-central1'
IMAGE_JOB_NAME = 'image-generation-job'
VIDEO_JOB_NAME = 'video-generation-job'

QUEUE_UNAVAILABLE_ERROR = (
    "Generation queue is unavailable. Please try again."
)


def execute_cloud_run_job(job_name: str, payload: dict) -> str:
    """
    Execute a Cloud Run Job directly.

    Args:
        job_name: Name of the Cloud Run Job to execute
        payload: JSON payload to pass as environment variables

    Returns:
        Execution name/ID

    Raises:
        Exception: If job execution fails
    """
    if not CLOUD_RUN_AVAILABLE:
        raise Exception("Cloud Run API not available in this environment")

    client = run_v2.JobsClient()

    # Construct the fully qualified job name
    job_path = f"projects/{PROJECT_ID}/locations/{REGION}/jobs/{job_name}"

    # Create execution with payload as environment variable
    request = run_v2.RunJobRequest(
        name=job_path,
        overrides=run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(
                    env=[
                        run_v2.EnvVar(
                            name="CREATION_ID",
                            value=payload.get("creationId", "")
                        )
                    ]
                )
            ]
        )
    )

    # Execute the job
    operation = client.run_job(request=request)
    execution_name = operation.metadata.name

    logger.info(f"Started Cloud Run Job execution: {execution_name}")
    return execution_name


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
            cost = 1 if creation_type == 'image' else 45
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
                # Execute Cloud Run Job directly for images (serverless)
                execution_name = execute_cloud_run_job(
                    job_name=IMAGE_JOB_NAME,
                    payload={"creationId": creation_id}
                )
                logger.info(f"🚀 Started image generation via Cloud Run Job: {execution_name}")

            else:  # video
                # Execute Cloud Run Job directly for videos (serverless)
                execution_name = execute_cloud_run_job(
                    job_name=VIDEO_JOB_NAME,
                    payload={"creationId": creation_id}
                )
                logger.info(f"🚀 Started video generation via Cloud Run Job: {execution_name}")

        except Exception as task_error:
            # Cloud Run Job execution error
            logger.error(
                f"🚨 Cloud Run Job unavailable for creation {creation_id}: {task_error}",
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
        cost = 1 if creation_type == 'image' else 45
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
        query = db.collection('creations').where(filter=firestore.FieldFilter('userId', '==', user_id))

        # Filter by status if requested
        if status_filter:
            query = query.where(filter=firestore.FieldFilter('status', '==', status_filter))
        
        # Note: No order_by to avoid composite index requirement
        # We'll sort in Python after fetching
        query = query.limit(limit)

        docs = query.stream()

        creations = []
        for doc in docs:
            creation_data = doc.to_dict()
            creation_data['id'] = doc.id

            status = creation_data.get('status')

            # Filter out published and deleted drafts unless explicitly requested
            if not status_filter and status in {'published', 'deleted'}:
                continue
            if status == 'deleted' and status_filter != 'deleted':
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


@generation_bp.route('/creation/<creation_id>', methods=['GET'])
@login_required
def get_creation_detail(creation_id):
    """Return a single creation owned by the current user."""
    try:
        user_id = session.get('user_id')
        creation = creation_service.get_creation(creation_id)

        if not creation or creation.get('status') == 'deleted':
            return jsonify({
                'success': False,
                'error': 'Creation not found'
            }), 404

        if creation.get('userId') != user_id:
            return jsonify({
                'success': False,
                'error': 'You can only view your own creations'
            }), 403

        creation['id'] = creation_id

        return jsonify({
            'success': True,
            'creation': creation
        })

    except Exception as e:
        logger.error(f"Failed to fetch creation {creation_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch creation'
        }), 500


@generation_bp.route('/creation/<creation_id>', methods=['DELETE'])
@login_required
@csrf_protect
def delete_creation(creation_id):
    """Soft delete a draft, failed, or pending creation."""
    try:
        user_id = session.get('user_id')
        success, error_code = creation_service.delete_creation(creation_id, user_id)

        if success:
            logger.info(f"🗑️ Deleted creation {creation_id} for user {user_id}")
            return jsonify({'success': True})

        if error_code == 'not_found':
            return jsonify({'success': False, 'error': 'Creation not found'}), 404

        if error_code == 'forbidden':
            return jsonify({'success': False, 'error': 'You can only manage your own creations'}), 403

        if error_code == 'invalid_status':
            return jsonify({'success': False, 'error': 'Creation cannot be deleted in its current state'}), 400

        logger.error(f"Failed to delete creation {creation_id}: {error_code}")
        return jsonify({'success': False, 'error': 'Failed to delete creation'}), 500

    except Exception as e:
        logger.error(f"Failed to delete creation {creation_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to delete creation'}), 500


@generation_bp.route('/creation/<creation_id>/publish', methods=['POST'])
@login_required
@csrf_protect
def publish_creation(creation_id):
    """Publish a draft creation to the public feed."""
    try:
        user_id = session.get('user_id')
        data = request.get_json(silent=True) or {}
        caption = data.get('caption')

        success, error_code, creation = creation_service.publish_creation(
            creation_id=creation_id,
            user_id=user_id,
            caption=caption
        )

        if success:
            logger.info(f"📣 Published creation {creation_id} for user {user_id}")
            response_creation = creation or {}
            response_creation['id'] = creation_id
            return jsonify({'success': True, 'creation': response_creation})

        if error_code == 'not_found':
            return jsonify({'success': False, 'error': 'Creation not found'}), 404

        if error_code == 'forbidden':
            return jsonify({'success': False, 'error': 'You can only publish your own drafts'}), 403

        if error_code == 'invalid_status':
            return jsonify({'success': False, 'error': 'Creation is not ready to publish'}), 400

        if error_code == 'deleted':
            return jsonify({'success': False, 'error': 'Creation has been deleted'}), 400

        if error_code == 'missing_media':
            return jsonify({'success': False, 'error': 'Creation is missing generated media'}), 400

        if error_code == 'caption_too_long':
            return jsonify({'success': False, 'error': 'Caption must be 500 characters or less'}), 400

        logger.error(f"Failed to publish creation {creation_id}: {error_code}")
        return jsonify({'success': False, 'error': 'Failed to publish creation'}), 500

    except Exception as e:
        logger.error(f"Failed to publish creation {creation_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to publish creation'}), 500
