"""Async Image Generation Worker

Processes image generation requests asynchronously using Celery.
Implements unified draft-first workflow matching video generation.

State Flow:
  pending → processing → draft (success)
                      → failed (permanent error, refunded)

All states are visible in the user's drafts until explicitly deleted.
"""
import logging
import os
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
import boto3
from botocore.client import Config

from celery_app import celery_app
from services.image_generation_service import (
    ImageGenerationService,
    SafetyFilterError,
    PolicyViolationError,
    ImageGenerationError
)
from services.creation_service import CreationService

logger = logging.getLogger(__name__)

# R2 Configuration
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID', '').strip()
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY', '').strip()
R2_ENDPOINT_URL = os.getenv('R2_ENDPOINT_URL', '').strip()
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', '').strip()
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', '').strip()

# Lazy-initialized services
_db = None
_image_service = None
_creation_service = None
_s3_client = None


def _get_db():
    """Get Firebase Firestore client (lazy initialization)."""
    global _db
    if _db is None:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _db = firestore.client()
    return _db


def _get_image_service():
    """Get image generation service (lazy initialization)."""
    global _image_service
    if _image_service is None:
        _image_service = ImageGenerationService()
    return _image_service


def _get_creation_service():
    """Get creation service (lazy initialization)."""
    global _creation_service
    if _creation_service is None:
        _get_db()  # Ensure Firebase is initialized
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


@celery_app.task(
    bind=True,
    name='jobs.async_image_generation_worker.generate_image_task',
    max_retries=0,  # No retries for content policy violations
    acks_late=True,
    reject_on_worker_lost=True
)
def generate_image_task(
    self,
    creation_id: str,
    prompt: str,
    original_transaction_id: str,
    user_id: Optional[str] = None
):
    """
    Generate image asynchronously and upload to R2.

    Args:
        creation_id: UUID of the creation document
        prompt: User's text prompt
        original_transaction_id: Transaction ID for potential refund
        user_id: Optional user ID (fetched from creation if not provided)

    State Transitions:
        pending → processing → draft (success)
                            → failed (error, refunded)
    """
    creation_service = _get_creation_service()
    image_service = _get_image_service()
    s3_client = _get_s3_client()

    logger.info(f"🎨 Starting image generation task: {creation_id}")

    # Fetch creation to get user_id if not provided
    if not user_id:
        creation_data = creation_service.get_creation(creation_id)
        if not creation_data:
            logger.error(f"Creation {creation_id} not found - cannot process")
            return
        user_id = creation_data.get('userId')

    try:
        # Update status to processing
        creation_service.update_creation_status(
            creation_id,
            'processing',
            progress=0.1
        )

        # Generate image using existing service
        logger.info(f"Calling Imagen API for creation {creation_id}...")

        result = image_service.generate_image(
            prompt=prompt,
            user_id=user_id,
            save_to_gcs=True  # Save to GCS for backup
        )

        logger.info(
            f"✅ Image generated successfully: {result.image_id} "
            f"(took {result.generation_time_seconds:.2f}s)"
        )

        # Upload to R2 for public access
        creation_service.update_creation_status(
            creation_id,
            'processing',
            progress=0.7
        )

        r2_key = f"images/{creation_id}.png"

        try:
            # Download from GCS and upload to R2
            # (result.image_url is the GCS URL, but we want R2 for public access)
            import requests
            import base64

            # Get image data
            if result.base64_data:
                image_data = base64.b64decode(result.base64_data)
            else:
                # Fallback: download from GCS URL
                response = requests.get(result.image_url, timeout=30)
                response.raise_for_status()
                image_data = response.content

            # Upload to R2
            s3_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=r2_key,
                Body=image_data,
                ContentType='image/png',
                ACL='public-read'
            )

            # Construct public URL
            media_url = f"{R2_PUBLIC_URL}/{r2_key}"

            logger.info(f"📤 Uploaded image to R2: {media_url}")

        except Exception as upload_error:
            logger.error(
                f"Failed to upload to R2 for {creation_id}: {upload_error}",
                exc_info=True
            )
            # Fallback to GCS URL if R2 upload fails
            media_url = result.image_url

        # Update creation to draft status with media URL
        creation_service.update_creation_status(
            creation_id,
            'draft',
            mediaUrl=media_url,
            thumbnailUrl=media_url,  # Same as mediaUrl for images
            generationTimeSeconds=result.generation_time_seconds,
            model=result.model,
            progress=1.0
        )

        logger.info(f"🎉 Image generation complete for creation {creation_id}")

    except SafetyFilterError as e:
        # Safety filter violation - permanent failure, refund tokens
        error_msg = f"Content blocked by safety filter: {str(e)}"
        logger.warning(f"❌ Safety filter blocked creation {creation_id}: {e}")

        creation_service.handle_generation_failure(
            creation_id=creation_id,
            original_transaction_id=original_transaction_id,
            error_message=error_msg,
            user_id=user_id
        )

    except PolicyViolationError as e:
        # Policy violation - permanent failure, refund tokens
        error_msg = f"Content policy violation: {str(e)}"
        logger.warning(f"❌ Policy violation for creation {creation_id}: {e}")

        creation_service.handle_generation_failure(
            creation_id=creation_id,
            original_transaction_id=original_transaction_id,
            error_message=error_msg,
            user_id=user_id
        )

    except ImageGenerationError as e:
        # Image generation API error - permanent failure, refund tokens
        error_msg = f"Image generation failed: {str(e)}"
        logger.error(f"❌ Image generation failed for {creation_id}: {e}", exc_info=True)

        creation_service.handle_generation_failure(
            creation_id=creation_id,
            original_transaction_id=original_transaction_id,
            error_message=error_msg,
            user_id=user_id
        )

    except Exception as e:
        # Unexpected error - permanent failure, refund tokens
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(
            f"❌ Unexpected error during image generation for {creation_id}: {e}",
            exc_info=True
        )

        creation_service.handle_generation_failure(
            creation_id=creation_id,
            original_transaction_id=original_transaction_id,
            error_message=error_msg,
            user_id=user_id
        )

    finally:
        logger.info(f"✓ Image generation task completed for {creation_id}")
