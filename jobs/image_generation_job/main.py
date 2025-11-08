"""
Image Generation Job - Cloud Run Job entry point.

Triggered directly via Cloud Run Jobs API. Implements money-safe contract.
Simpler and faster than video generation.

State Flow:
  pending → processing → draft (success)
                      → failed (error + refund)
"""
import json
import logging
import os
import sys
import base64
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, '/app')

import firebase_admin
from firebase_admin import credentials, firestore
import boto3
from botocore.client import Config

from services.image_generation_service import (
    ImageGenerationService,
    SafetyFilterError,
    PolicyViolationError,
    ImageGenerationError
)

logger = logging.getLogger(__name__)

# R2 Configuration
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID', '').strip()
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY', '').strip()
R2_ENDPOINT_URL = os.getenv('R2_ENDPOINT_URL', '').strip()
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', '').strip()
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', '').strip()

# Lazy initialized globals
_db = None
_image_service = None
_s3_client = None


def get_db():
    """Get Firestore client (lazy init)."""
    global _db
    if _db is None:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _db = firestore.client()
    return _db


def get_image_service():
    """Get image generation service (lazy init)."""
    global _image_service
    if _image_service is None:
        _image_service = ImageGenerationService()
    return _image_service


def get_s3_client():
    """Get R2 S3 client (lazy init)."""
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


def update_creation_state(creation_id: str, **fields) -> None:
    """Update creation document in Firestore."""
    try:
        db = get_db()
        creation_ref = db.collection('creations').document(creation_id)
        fields['updatedAt'] = firestore.SERVER_TIMESTAMP
        creation_ref.update(fields)
    except Exception as e:
        logger.error(f"Failed to update creation {creation_id}: {e}")


def refund_tokens(creation_id: str, user_id: str, cost: int, error_message: str) -> bool:
    """
    Refund tokens after failed generation (Money Contract).

    Returns True if refund successful, False otherwise.
    """
    try:
        db = get_db()

        @firestore.transactional
        def refund_transaction(transaction):
            user_ref = db.collection('users').document(user_id)
            creation_ref = db.collection('creations').document(creation_id)
            refund_tx_ref = db.collection('transactions').document()

            # Check if already refunded (idempotency)
            creation_snapshot = creation_ref.get(transaction=transaction)
            if creation_snapshot.exists and creation_snapshot.to_dict().get('refunded'):
                logger.info(f"Creation {creation_id} already refunded")
                return

            # 1. Refund tokens
            transaction.update(user_ref, {
                'tokenBalance': firestore.Increment(cost),
                'totalTokensSpent': firestore.Increment(-cost)
            })

            # 2. Mark creation as refunded
            transaction.update(creation_ref, {
                'refunded': True,
                'refundedAt': firestore.SERVER_TIMESTAMP
            })

            # 3. Log refund transaction
            transaction.set(refund_tx_ref, {
                'userId': user_id,
                'type': 'image_generation_refund',
                'amount': cost,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'details': {
                    'creationId': creation_id,
                    'reason': 'generation_failed',
                    'error': error_message[:200]
                }
            })

        transaction = db.transaction()
        refund_transaction(transaction)
        logger.info(f"💰 Refunded {cost} tokens to user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to refund tokens for {creation_id}: {e}", exc_info=True)
        return False


def generate_image(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main image generation logic.

    Payload: {"creationId": "..."}

    Returns: {"success": bool, ...}
    """
    creation_id = payload['creationId']
    user_id = None
    cost = 1  # Image generation cost

    try:
        logger.info(f"🎨 Starting image generation for {creation_id}")

        # 1. Fetch creation document
        db = get_db()
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            logger.error(f"Creation {creation_id} not found")
            return {'success': False, 'error': 'Creation not found'}

        creation_data = creation_doc.to_dict()
        user_id = creation_data.get('userId')
        prompt = creation_data.get('prompt')
        current_status = creation_data.get('status')

        logger.info(f"📋 Creation: user={user_id}, status={current_status}")

        # 2. Check if already completed (idempotency)
        if current_status in ['draft', 'published']:
            logger.info(f"✅ Already completed (status: {current_status})")
            return {
                'success': True,
                'status': current_status,
                'cached': True,
                'mediaUrl': creation_data.get('mediaUrl')
            }

        # 3. Mark as processing
        update_creation_state(
            creation_id,
            status='processing',
            progress=0.1,
            workerStartedAt=firestore.SERVER_TIMESTAMP
        )

        # 4. Call Imagen API
        logger.info(f"📡 Calling Imagen API")
        logger.info(f"   Prompt: {prompt[:80]}...")

        update_creation_state(creation_id, progress=0.3)

        image_service = get_image_service()
        result = image_service.generate_image(
            prompt=prompt,
            user_id=user_id,
            save_to_gcs=False  # We'll upload directly to R2
        )

        logger.info(
            f"✅ Image generated successfully "
            f"(took {result.generation_time_seconds:.2f}s)"
        )

        # 5. Upload to R2
        logger.info(f"📤 Uploading to R2...")
        update_creation_state(creation_id, progress=0.7)

        r2_key = f"images/{user_id}/{creation_id}.png"

        # Get image data from base64
        image_data = base64.b64decode(result.base64_data)

        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=r2_key,
            Body=image_data,
            ContentType='image/png',
            Metadata={
                'user_id': user_id,
                'creation_id': creation_id,
                'app': 'phoenix',
                'prompt': prompt[:200]
            }
        )

        media_url = f"{R2_PUBLIC_URL}/{r2_key}"
        logger.info(f"✅ Image uploaded: {media_url}")

        update_creation_state(creation_id, progress=0.9)

        # 6. Mark as draft (SUCCESS!)
        update_creation_state(
            creation_id,
            status='draft',
            mediaUrl=media_url,
            thumbnailUrl=media_url,  # Same as mediaUrl for images
            generationTimeSeconds=result.generation_time_seconds,
            model=result.model,
            progress=1.0,
            completedAt=firestore.SERVER_TIMESTAMP
        )

        logger.info(f"🎉 Image generation complete!")
        logger.info(f"   Media URL: {media_url}")

        return {
            'success': True,
            'creation_id': creation_id,
            'media_url': media_url,
            'generation_time': result.generation_time_seconds
        }

    except (SafetyFilterError, PolicyViolationError) as e:
        # Content policy violation - permanent failure, refund
        error_msg = f"Content blocked: {str(e)}"
        logger.warning(f"❌ Content blocked for {creation_id}: {e}")

        try:
            update_creation_state(
                creation_id,
                status='failed',
                error=error_msg,
                failedAt=firestore.SERVER_TIMESTAMP
            )

            if user_id:
                refund_tokens(creation_id, user_id, cost, error_msg)
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup after policy violation: {cleanup_error}")

        return {
            'success': False,
            'error': error_msg,
            'refunded': True
        }

    except ImageGenerationError as e:
        # Image generation API error - permanent failure, refund
        error_msg = f"Generation failed: {str(e)}"
        logger.error(f"❌ Image generation failed for {creation_id}: {e}")

        try:
            update_creation_state(
                creation_id,
                status='failed',
                error=error_msg,
                failedAt=firestore.SERVER_TIMESTAMP
            )

            if user_id:
                refund_tokens(creation_id, user_id, cost, error_msg)
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup after generation error: {cleanup_error}")

        return {
            'success': False,
            'error': error_msg,
            'refunded': True
        }

    except Exception as e:
        # Unexpected error - mark failed and refund
        error_msg = f"Internal error: {str(e)}"
        logger.error(f"💥 Unexpected error: {e}", exc_info=True)

        try:
            update_creation_state(
                creation_id,
                status='failed',
                error=error_msg,
                failedAt=firestore.SERVER_TIMESTAMP
            )

            if user_id:
                refund_tokens(creation_id, user_id, cost, error_msg)
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup after unexpected error: {cleanup_error}")

        return {
            'success': False,
            'error': error_msg,
            'refunded': True
        }


def main():
    """Cloud Run Job entry point."""
    # Get creation_id from environment variable (set by Cloud Run Jobs API)
    creation_id = os.getenv('CREATION_ID')

    if not creation_id:
        logger.error("No CREATION_ID environment variable provided")
        sys.exit(1)

    logger.info(f"🚀 Starting image generation for creation: {creation_id}")

    # Build payload
    payload = {"creationId": creation_id}

    # Execute job
    result = generate_image(payload)

    if result['success']:
        logger.info("✅ Job completed successfully")
        print(json.dumps(result))
        sys.exit(0)
    else:
        logger.error(f"❌ Job failed: {result.get('error')}")
        print(json.dumps(result))
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    main()
