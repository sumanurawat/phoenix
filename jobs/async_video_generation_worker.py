"""Async Video Generation Worker

Processes video generation requests asynchronously using Celery.
Implements Sora-style drafts system with seamless state management.

State Flow:
  pending → processing → draft (success)
                      → failed (permanent error, refunded)

All states are visible in the user's drafts until explicitly deleted.
The worker ALWAYS updates the creation status before completing, ensuring
no orphaned "processing" states even if the worker crashes.
"""
import logging
import os
import time
import traceback
import subprocess
import tempfile
from typing import Optional
from celery import Task
import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core.exceptions import GoogleAPIError
from google.cloud import storage
from PIL import Image
import io

from celery_app import celery_app
from services.veo_video_generation_service import (
    VeoVideoGenerationService,
    VeoGenerationParams,
    VeoOperationResult
)
from services.token_service import TokenService
from services.creation_service import CreationService
import boto3
from botocore.client import Config

logger = logging.getLogger(__name__)

# R2 Configuration (strip whitespace from secrets)
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID', '').strip()
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY', '').strip()
R2_ENDPOINT_URL = os.getenv('R2_ENDPOINT_URL', '').strip()
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', '').strip()
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', '').strip()

# Lazy-initialized services (initialized on first task execution)
_db = None
_veo_service = None
_token_service = None
_creation_service = None
_s3_client = None

def _get_db():
    """Get Firebase Firestore client (lazy initialization)."""
    global _db
    if _db is None:
        # Initialize Firebase if not already initialized
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _db = firestore.client()
    return _db

def _get_veo_service():
    """Get Veo video generation service (lazy initialization)."""
    global _veo_service
    if _veo_service is None:
        _veo_service = VeoVideoGenerationService()
    return _veo_service

def _get_token_service():
    """Get token service (lazy initialization)."""
    global _token_service
    if _token_service is None:
        _get_db()  # Ensure Firebase is initialized first
        _token_service = TokenService()
    return _token_service

def _get_creation_service():
    """Get creation service (lazy initialization)."""
    global _creation_service
    if _creation_service is None:
        _get_db()  # Ensure Firebase is initialized first
        _creation_service = CreationService()
    return _creation_service

def _get_s3_client():
    """Get R2 S3 client (lazy initialization)."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
    return _s3_client

class VideoGenerationError(Exception):
    """Base exception for video generation errors."""
    pass

class ContentPolicyViolationError(VideoGenerationError):
    """Raised when prompt violates content policy (permanent failure)."""
    pass

class TransientAPIError(VideoGenerationError):
    """Raised for temporary API failures (retriable)."""
    pass

def _update_creation_state(
    creation_id: str,
    status: str,
    **extra_fields
) -> None:
    """
    Update creation document state atomically.

    This is a compatibility wrapper around CreationService.update_creation_status
    for existing code that uses this function directly.

    Args:
        creation_id: UUID of creation
        status: New status (pending, processing, draft, failed)
        **extra_fields: Additional fields to update (mediaUrl, error, etc.)
    """
    creation_service = _get_creation_service()
    creation_service.update_creation_status(creation_id, status, **extra_fields)


def _refund_tokens(creation_id: str, user_id: str, error_message: str) -> bool:
    """
    Refund tokens to user after a failed generation.

    This is a compatibility wrapper around CreationService.handle_generation_failure
    for existing code. New code should call handle_generation_failure directly.

    Args:
        creation_id: Creation document ID
        user_id: User ID to refund
        error_message: Error message for logging

    Returns:
        bool: True if refund successful, False otherwise
    """
    creation_service = _get_creation_service()
    
    # Note: We don't have the original transaction ID here in the old code path
    # The new CreationService.handle_generation_failure can work without it
    return creation_service.handle_generation_failure(
        creation_id=creation_id,
        original_transaction_id='',  # Empty for legacy calls
        error_message=error_message,
        user_id=user_id
    )


def _extract_video_thumbnail(video_bytes: bytes, duration_seconds: int) -> bytes:
    """
    Extract a thumbnail image from video bytes using ffmpeg.

    Extracts a frame from the middle of the video and converts to JPEG.

    Args:
        video_bytes: Video file bytes
        duration_seconds: Duration of the video in seconds

    Returns:
        bytes: JPEG thumbnail image bytes

    Raises:
        Exception: If ffmpeg extraction fails
    """
    try:
        # Calculate middle timestamp
        middle_time = duration_seconds / 2.0

        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_temp:
            video_temp.write(video_bytes)
            video_path = video_temp.name

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as thumb_temp:
            thumb_path = thumb_temp.name

        try:
            # Use ffmpeg to extract frame
            # -ss: seek to timestamp
            # -i: input file
            # -vframes 1: extract 1 frame
            # -q:v 2: high quality (1-31, lower is better)
            # -vf scale: resize to reasonable dimensions (maintain aspect ratio)
            cmd = [
                'ffmpeg',
                '-ss', str(middle_time),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-vf', 'scale=640:-1',  # Width 640, height auto
                '-y',  # Overwrite output
                thumb_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg failed: {result.stderr}")
                raise Exception(f"ffmpeg extraction failed: {result.stderr}")

            # Read thumbnail bytes
            with open(thumb_path, 'rb') as f:
                thumbnail_bytes = f.read()

            # Optimize thumbnail size using PIL
            img = Image.open(io.BytesIO(thumbnail_bytes))
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            optimized_bytes = output.getvalue()

            logger.info(f"📸 Extracted thumbnail: {len(optimized_bytes)} bytes")
            return optimized_bytes

        finally:
            # Cleanup temp files
            try:
                os.unlink(video_path)
                os.unlink(thumb_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files: {e}")

    except subprocess.TimeoutExpired:
        logger.error("ffmpeg thumbnail extraction timed out")
        raise Exception("Thumbnail extraction timed out")
    except Exception as e:
        logger.error(f"Failed to extract thumbnail: {e}", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    name='jobs.async_video_generation_worker.generate_video_task',
    max_retries=3,
    autoretry_for=(TransientAPIError,),
    retry_backoff=60,  # 60s, 120s, 240s
    retry_backoff_max=300,
    retry_jitter=True
)
def generate_video_task(self: Task, creation_id: str) -> dict:
    """
    Generate video from prompt and upload to R2.

    State Management (Sora-style):
    - Creation document is ALWAYS updated before worker exits
    - Failed generations remain in drafts with 'failed' status
    - User can see all generations (pending, processing, draft, failed)
    - Failed generations show error message and are refunded
    - User can delete failed drafts manually

    Idempotency:
    - Safe to retry - checks current status first
    - Refunds are atomic and checked for duplicates
    - Already-processed videos return immediately

    Args:
        creation_id: UUID of the creation document in Firestore

    Returns:
        dict: Result metadata
    """
    user_id = None

    try:
        logger.info(f"🎬 Starting video generation for creation: {creation_id}")

        # 1. Fetch creation document (source of truth)
        db = _get_db()
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            logger.error(f"❌ Creation {creation_id} not found in Firestore")
            # Can't update state if document doesn't exist
            return {'success': False, 'error': 'Creation not found'}

        creation_data = creation_doc.to_dict()
        user_id = creation_data.get('userId')
        prompt = creation_data.get('prompt')
        aspect_ratio = creation_data.get('aspectRatio', '9:16')
        duration = creation_data.get('duration', 8)
        current_status = creation_data.get('status')

        logger.info(f"📋 Creation {creation_id} - User: {user_id}, Status: {current_status}")

        # 2. Check if already processed (idempotency)
        if current_status == 'draft':
            logger.info(f"✅ Creation {creation_id} already completed (status: draft)")
            return {
                'success': True,
                'status': 'draft',
                'cached': True,
                'mediaUrl': creation_data.get('mediaUrl')
            }

        if current_status == 'published':
            logger.info(f"✅ Creation {creation_id} already published")
            return {
                'success': True,
                'status': 'published',
                'cached': True
            }

        # 3. Update status to 'processing' (visible in drafts)
        _update_creation_state(
            creation_id,
            status='processing',
            workerStartedAt=firestore.SERVER_TIMESTAMP,
            progress=0.1
        )

        # 4. Call Veo API
        logger.info(f"📡 Calling Veo API for creation {creation_id}")
        logger.info(f"   Prompt: {prompt[:80]}...")
        logger.info(f"   Aspect: {aspect_ratio}, Duration: {duration}s")

        params = VeoGenerationParams(
            model="veo-3.1-fast-generate-preview",
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration,
            enhance_prompt=True,
            sample_count=1,
            generate_audio=False,
            # Store in GCS temporarily (Veo requirement)
            storage_uri=f"gs://phoenix-videos/temp/{creation_id}.mp4"
        )

        # Update progress
        _update_creation_state(creation_id, status='processing', progress=0.3)

        start_time = time.time()
        veo_service = _get_veo_service()
        result: VeoOperationResult = veo_service.start_generation(
            params,
            poll=True,
            poll_interval=5.0,
            timeout=300.0
        )
        generation_time = time.time() - start_time

        logger.info(f"⏱️  Veo generation took {generation_time:.1f}s")

        # 5. Handle API errors
        if not result.success:
            error_msg = result.error or "Unknown Veo API error"
            logger.error(f"❌ Veo generation failed for {creation_id}: {error_msg}")

            # Check if it's a content policy violation (permanent failure)
            if any(keyword in error_msg.lower() for keyword in ['content policy', 'safety', 'prohibited', 'violates']):
                logger.warning(f"🚫 Content policy violation for creation {creation_id}")

                # Mark as failed and refund
                _update_creation_state(
                    creation_id,
                    status='failed',
                    error=f"Content policy violation: {error_msg}",
                    failedAt=firestore.SERVER_TIMESTAMP
                )

                _refund_tokens(creation_id, user_id, error_msg)

                # Don't retry - this is permanent
                return {
                    'success': False,
                    'error': 'Content policy violation',
                    'refunded': True
                }

            # Otherwise, treat as transient error (will auto-retry via Celery)
            logger.warning(f"⚠️  Transient API error for creation {creation_id}: {error_msg}")

            # Update retry count
            _update_creation_state(
                creation_id,
                status='pending',  # Back to pending for retry
                lastError=error_msg,
                retryCount=firestore.Increment(1)
            )

            # Raise to trigger Celery retry
            raise TransientAPIError(error_msg)

        # 6. Download from GCS and upload to R2
        if not result.gcs_uris:
            logger.error(f"❌ No GCS URIs returned for creation {creation_id}")
            error_msg = "No video generated by Veo API"
            _update_creation_state(
                creation_id,
                status='failed',
                error=error_msg,
                failedAt=firestore.SERVER_TIMESTAMP
            )
            _refund_tokens(creation_id, user_id, error_msg)
            return {'success': False, 'error': error_msg, 'refunded': True}

        gcs_uri = result.gcs_uris[0]
        logger.info(f"📥 Downloading video from GCS: {gcs_uri}")

        # Update progress
        _update_creation_state(creation_id, status='processing', progress=0.7)

        # Download from GCS
        storage_client = storage.Client()
        bucket_name = gcs_uri.split('/')[2]
        blob_name = '/'.join(gcs_uri.split('/')[3:])
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        video_bytes = blob.download_as_bytes()

        logger.info(f"📦 Downloaded {len(video_bytes)} bytes from GCS")

        # Update progress
        _update_creation_state(creation_id, status='processing', progress=0.75)

        # Extract thumbnail from video
        logger.info(f"📸 Extracting thumbnail from video...")
        try:
            thumbnail_bytes = _extract_video_thumbnail(video_bytes, duration)
            logger.info(f"✅ Thumbnail extracted successfully")
        except Exception as e:
            logger.error(f"Failed to extract thumbnail: {e}")
            # Continue without thumbnail (non-critical)
            thumbnail_bytes = None

        # Update progress
        _update_creation_state(creation_id, status='processing', progress=0.8)

        # Upload video to R2
        logger.info(f"📤 Uploading video to R2...")
        r2_key = f"videos/{user_id}/{creation_id}.mp4"

        s3_client = _get_s3_client()
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=r2_key,
            Body=video_bytes,
            ContentType='video/mp4',
            Metadata={
                'user_id': user_id,
                'creation_id': creation_id,
                'app': 'phoenix',
                'service': 'video-generation',
                'phase': '3',
                'prompt': prompt[:200]  # Store prompt snippet
            }
        )

        media_url = f"{R2_PUBLIC_URL}/{r2_key}"
        logger.info(f"✅ Video uploaded to R2: {media_url}")

        # Upload thumbnail to R2 if extraction succeeded
        thumbnail_url = None
        if thumbnail_bytes:
            try:
                thumbnail_key = f"videos/{user_id}/{creation_id}_thumb.jpg"
                s3_client.put_object(
                    Bucket=R2_BUCKET_NAME,
                    Key=thumbnail_key,
                    Body=thumbnail_bytes,
                    ContentType='image/jpeg',
                    Metadata={
                        'user_id': user_id,
                        'creation_id': creation_id,
                        'app': 'phoenix',
                        'service': 'video-generation',
                        'type': 'thumbnail'
                    }
                )
                thumbnail_url = f"{R2_PUBLIC_URL}/{thumbnail_key}"
                logger.info(f"✅ Thumbnail uploaded to R2: {thumbnail_url}")
            except Exception as e:
                logger.error(f"Failed to upload thumbnail to R2: {e}")
                # Continue without thumbnail (non-critical)

        # Update progress
        _update_creation_state(creation_id, status='processing', progress=0.9)

        # Clean up GCS temporary file
        try:
            blob.delete()
            logger.info(f"🗑️  Cleaned up GCS temp file: {gcs_uri}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to delete GCS temp file: {e}")

        # 7. Mark as draft (success!)
        update_fields = {
            'status': 'draft',
            'mediaUrl': media_url,
            'duration': duration,
            'generationTime': generation_time,
            'modelUsed': params.model,
            'progress': 1.0,
            'completedAt': firestore.SERVER_TIMESTAMP
        }

        # Add thumbnail URL if available
        if thumbnail_url:
            update_fields['thumbnailUrl'] = thumbnail_url

        _update_creation_state(creation_id, **update_fields)

        logger.info(f"🎉 Video generation complete for creation {creation_id}")
        logger.info(f"   Media URL: {media_url}")
        logger.info(f"   Thumbnail URL: {thumbnail_url or 'N/A'}")
        logger.info(f"   Duration: {duration}s")
        logger.info(f"   Generation time: {generation_time:.1f}s")

        return {
            'success': True,
            'creation_id': creation_id,
            'media_url': media_url,
            'generation_time': generation_time,
            'status': 'draft'
        }

    except TransientAPIError:
        # Re-raise to let Celery handle retry
        raise

    except Exception as e:
        # Unexpected error - log full traceback
        logger.error(f"💥 Unexpected error for creation {creation_id}: {e}")
        logger.error(traceback.format_exc())

        # Update state to failed
        error_msg = f"Internal error: {str(e)}"
        _update_creation_state(
            creation_id,
            status='failed',
            error=error_msg,
            failedAt=firestore.SERVER_TIMESTAMP
        )

        # Refund tokens if we have user_id
        if user_id:
            _refund_tokens(creation_id, user_id, error_msg)

        # If we've exhausted retries, return failure
        if self.request.retries >= self.max_retries:
            logger.error(f"❌ Max retries exceeded for creation {creation_id}")
            return {
                'success': False,
                'error': 'Max retries exceeded',
                'refunded': True
            }

        # Otherwise retry
        raise self.retry(exc=e, countdown=60)

@celery_app.task(name='jobs.async_video_generation_worker.cleanup_orphaned_processing')
def cleanup_orphaned_processing():
    """
    Cleanup task: Find creations stuck in 'processing' state.

    If a worker crashes, creations might be stuck in 'processing' state forever.
    This task finds and resets them to 'failed' with refund.

    Run periodically (every 10 minutes) to catch orphaned jobs.
    """
    try:
        logger.info("🔍 Checking for orphaned 'processing' creations...")

        # Find creations in 'processing' state for more than 15 minutes
        from datetime import datetime, timedelta
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)

        db = _get_db()
        orphaned = db.collection('creations')\
            .where('status', '==', 'processing')\
            .where('workerStartedAt', '<', cutoff_time)\
            .limit(50)\
            .stream()

        count = 0
        for creation in orphaned:
            creation_id = creation.id
            creation_data = creation.to_dict()
            user_id = creation_data.get('userId')

            logger.warning(f"🚨 Found orphaned creation: {creation_id}")

            # Mark as failed
            _update_creation_state(
                creation_id,
                status='failed',
                error='Worker timeout or crash - generation did not complete',
                failedAt=firestore.SERVER_TIMESTAMP
            )

            # Refund tokens
            if user_id:
                _refund_tokens(
                    creation_id,
                    user_id,
                    'Worker timeout or crash'
                )

            count += 1

        if count > 0:
            logger.info(f"✅ Cleaned up {count} orphaned creations")
        else:
            logger.info("✅ No orphaned creations found")

        return {'cleaned': count}

    except Exception as e:
        logger.error(f"Failed to cleanup orphaned creations: {e}", exc_info=True)
        return {'error': str(e)}
