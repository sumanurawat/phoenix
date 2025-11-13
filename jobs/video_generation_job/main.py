"""
Video Generation Job - Cloud Run Job entry point.

Triggered directly via Cloud Run Jobs API. Implements money-safe contract.
Uses Veo 3.1 for video generation, ffmpeg for thumbnails, R2 for storage.

State Flow:
  pending → processing → draft (success)
                      → failed (error + refund)
"""
import json
import logging
import os
import sys
import time
import traceback
import subprocess
import tempfile
from typing import Dict, Any
from PIL import Image
import io

# Add parent directory to path
sys.path.insert(0, '/app')

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage
import boto3
from botocore.client import Config

from services.veo_video_generation_service import (
    VeoVideoGenerationService,
    VeoGenerationParams,
    VeoOperationResult
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
_veo_service = None
_s3_client = None


def get_db():
    """Get Firestore client (lazy init)."""
    global _db
    if _db is None:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _db = firestore.client()
    return _db


def get_veo_service():
    """Get Veo service (lazy init)."""
    global _veo_service
    if _veo_service is None:
        _veo_service = VeoVideoGenerationService()
    return _veo_service


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
                'type': 'video_generation_refund',
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


def extract_video_thumbnail(video_bytes: bytes, duration_seconds: int) -> bytes:
    """
    Extract thumbnail from video using ffmpeg.

    Returns JPEG thumbnail bytes.
    """
    middle_time = duration_seconds / 2.0

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_temp:
        video_temp.write(video_bytes)
        video_path = video_temp.name

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as thumb_temp:
        thumb_path = thumb_temp.name

    try:
        cmd = [
            'ffmpeg',
            '-ss', str(middle_time),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-vf', 'scale=640:-1',
            '-y',
            thumb_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"ffmpeg failed: {result.stderr}")

        with open(thumb_path, 'rb') as f:
            thumbnail_bytes = f.read()

        # Optimize with PIL
        img = Image.open(io.BytesIO(thumbnail_bytes))
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)

        return output.getvalue()

    finally:
        try:
            os.unlink(video_path)
            os.unlink(thumb_path)
        except Exception:
            pass


def generate_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main video generation logic.

    Payload: {"creationId": "..."}

    Returns: {"success": bool, ...}
    """
    creation_id = payload['creationId']
    user_id = None
    cost = 45  # Video generation cost

    try:
        logger.info(f"🎬 Starting video generation for {creation_id}")

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
        aspect_ratio = creation_data.get('aspectRatio', '9:16')
        duration = creation_data.get('duration', 8)
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

        # 4. Call Veo API
        logger.info(f"📡 Calling Veo API")
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
            storage_uri=f"gs://phoenix-videos/temp/{creation_id}.mp4"
        )

        update_creation_state(creation_id, progress=0.3)

        start_time = time.time()
        veo_service = get_veo_service()
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
            logger.error(f"❌ Veo failed: {error_msg}")

            # Mark as failed
            update_creation_state(
                creation_id,
                status='failed',
                error=f"Generation failed: {error_msg}",
                failedAt=firestore.SERVER_TIMESTAMP
            )

            # Refund tokens
            refund_tokens(creation_id, user_id, cost, error_msg)

            return {
                'success': False,
                'error': error_msg,
                'refunded': True
            }

        # 6. Download from GCS
        if not result.gcs_uris:
            error_msg = "No video generated by Veo"
            logger.error(f"❌ {error_msg}")
            update_creation_state(
                creation_id,
                status='failed',
                error=error_msg,
                failedAt=firestore.SERVER_TIMESTAMP
            )
            refund_tokens(creation_id, user_id, cost, error_msg)
            return {'success': False, 'error': error_msg, 'refunded': True}

        gcs_uri = result.gcs_uris[0]
        logger.info(f"📥 Downloading from GCS: {gcs_uri}")

        update_creation_state(creation_id, progress=0.7)

        storage_client = storage.Client()
        bucket_name = gcs_uri.split('/')[2]
        blob_name = '/'.join(gcs_uri.split('/')[3:])
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        video_bytes = blob.download_as_bytes()

        logger.info(f"📦 Downloaded {len(video_bytes)} bytes")

        update_creation_state(creation_id, progress=0.75)

        # 7. Extract thumbnail
        logger.info(f"📸 Extracting thumbnail...")
        try:
            thumbnail_bytes = extract_video_thumbnail(video_bytes, duration)
            logger.info(f"✅ Thumbnail extracted")
        except Exception as e:
            logger.error(f"Thumbnail extraction failed: {e}")
            thumbnail_bytes = None

        update_creation_state(creation_id, progress=0.8)

        # 8. Upload to R2
        logger.info(f"📤 Uploading to R2...")
        r2_key = f"videos/{user_id}/{creation_id}.mp4"

        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=r2_key,
            Body=video_bytes,
            ContentType='video/mp4',
            Metadata={
                'user_id': user_id,
                'creation_id': creation_id,
                'app': 'phoenix',
                'prompt': prompt[:200]
            }
        )

        media_url = f"{R2_PUBLIC_URL}/{r2_key}"
        logger.info(f"✅ Video uploaded: {media_url}")

        # Upload thumbnail
        thumbnail_url = None
        if thumbnail_bytes:
            try:
                thumbnail_key = f"videos/{user_id}/{creation_id}_thumb.jpg"
                s3_client.put_object(
                    Bucket=R2_BUCKET_NAME,
                    Key=thumbnail_key,
                    Body=thumbnail_bytes,
                    ContentType='image/jpeg'
                )
                thumbnail_url = f"{R2_PUBLIC_URL}/{thumbnail_key}"
                logger.info(f"✅ Thumbnail uploaded: {thumbnail_url}")
            except Exception as e:
                logger.error(f"Thumbnail upload failed: {e}")

        update_creation_state(creation_id, progress=0.9)

        # Clean up GCS temp file
        try:
            blob.delete()
            logger.info(f"🗑️  Cleaned up GCS temp file")
        except Exception as e:
            logger.warning(f"Failed to delete GCS temp: {e}")

        # 9. Mark as draft (SUCCESS!)
        update_fields = {
            'status': 'draft',
            'mediaUrl': media_url,
            'duration': duration,
            'generationTime': generation_time,
            'modelUsed': params.model,
            'progress': 1.0,
            'completedAt': firestore.SERVER_TIMESTAMP
        }

        if thumbnail_url:
            update_fields['thumbnailUrl'] = thumbnail_url

        update_creation_state(creation_id, **update_fields)

        logger.info(f"🎉 Video generation complete!")
        logger.info(f"   Media URL: {media_url}")
        logger.info(f"   Thumbnail: {thumbnail_url or 'N/A'}")

        return {
            'success': True,
            'creation_id': creation_id,
            'media_url': media_url,
            'thumbnail_url': thumbnail_url,
            'generation_time': generation_time
        }

    except Exception as e:
        # Unexpected error - mark failed and refund
        logger.error(f"💥 Unexpected error: {e}")
        logger.error(traceback.format_exc())

        error_msg = f"Internal error: {str(e)}"

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
            logger.error(f"Failed to cleanup after error: {cleanup_error}")

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

    logger.info(f"🚀 Starting video generation for creation: {creation_id}")

    # Build payload
    payload = {"creationId": creation_id}

    # Execute job
    result = generate_video(payload)

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
