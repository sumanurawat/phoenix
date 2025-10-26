# Phase 3: Video Creative Engine & Publishing Flow - Implementation Plan

**Date:** October 25, 2025
**Project:** Phoenix AI Social Platform
**Phase:** 3 - Video Generation Pipeline

---

## Executive Summary

This phase implements the **asynchronous video generation pipeline** - the core creative experience of our video-first social platform. Users will spend tokens to generate videos via background jobs, with a modern, non-blocking UX inspired by Instagram and Sora.

**Key Deliverables:**
1. Redis-based job queue (Celery)
2. Asynchronous video generation API
3. Background worker for Veo video generation
4. Firestore `creations` collection for state management
5. Cost-labeled GCP infrastructure
6. Comprehensive error handling and retry logic

---

## Architecture Analysis

### Existing Patterns Identified

**✅ Strong Foundation:**
- **Service Layer:** 28 service files follow consistent patterns (`*_service.py`)
- **Token Economy:** Atomic transactions implemented in `token_service.py` using `@admin_firestore.transactional`
- **Video Generation:** `veo_video_generation_service.py` already has Veo API integration
- **Jobs Infrastructure:** `/jobs` directory with base classes (`job_runner.py`, `monitoring.py`, `progress_publisher.py`)
- **Transaction Service:** Immutable ledger with `transaction_service.py`
- **API Blueprints:** Clean separation with `api/*_routes.py`

**Architecture Insights:**
1. **Transaction Pattern:** Uses `@admin_firestore.transactional` decorator for atomic operations
2. **Service Initialization:** Services use `admin_firestore.client()` for Firestore access
3. **Configuration:** Centralized in `config/settings.py` with env variables
4. **Error Handling:** Consistent logging with `logging.getLogger(__name__)`
5. **Cost Tracking:** Already uses `R2_PUBLIC_URL` for $0 egress storage

---

## Implementation Tasks

### Task 3.0: Infrastructure Provisioning

**Objective:** Create labeled GCP resources for job queuing and worker execution.

#### 3.0.1: Create Provisioning Script

**File:** `provision_resources.sh`

```bash
#!/bin/bash
set -e

PROJECT_ID="phoenix-project-386"
REGION="us-central1"

echo "🔧 Provisioning Phoenix Phase 3 Infrastructure..."

# 1. Create Redis instance for Celery broker
echo "📦 Creating Cloud Memorystore (Redis) for job queue..."
gcloud redis instances create phoenix-cache-prod \
  --size=1 \
  --tier=BASIC \
  --region=$REGION \
  --project=$PROJECT_ID \
  --labels=app=phoenix,service=cache,env=prod,phase=3

# 2. Grant Redis access to service account
echo "🔐 Granting Redis access to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com" \
  --role="roles/redis.editor"

# 3. Get Redis connection info
echo "📋 Redis instance details:"
gcloud redis instances describe phoenix-cache-prod \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(host,port)"

echo "✅ Infrastructure provisioning complete!"
echo ""
echo "Next steps:"
echo "1. Add REDIS_HOST and REDIS_PORT to Secret Manager"
echo "2. Update cloudbuild.yaml with Redis env vars"
echo "3. Deploy worker service"
```

**Cost Labels Applied:**
- `app=phoenix` - Filter all Phoenix costs
- `service=cache` - Identify cache/queue costs
- `env=prod` - Separate prod/dev costs
- `phase=3` - Track Phase 3 specific costs

---

### Task 3.1: Celery Integration

#### 3.1.1: Update Dependencies

**File:** `requirements.txt`

Add:
```
celery==5.4.0  # Background task queue
redis==5.2.1   # Celery broker and result backend
```

#### 3.1.2: Create Celery App

**File:** `celery_app.py`

```python
"""Celery application for Phoenix background jobs.

Configured to use Redis as both message broker and result backend.
"""
import os
import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

logger = logging.getLogger(__name__)

# Read Redis connection from environment
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'

# Initialize Celery
celery_app = Celery(
    'phoenix',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['jobs.video_worker']  # Auto-discover tasks
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=570,  # Warn at 9.5 minutes
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)

# Logging hooks
@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    logger.info(f"🎬 Task starting: {task.name} [{task_id}]")

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    logger.info(f"✅ Task complete: {task.name} [{task_id}]")

@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    logger.error(f"❌ Task failed: [{task_id}] - {exception}")

logger.info("Celery app initialized with broker: %s", REDIS_URL)
```

#### 3.1.3: Integrate Celery with Flask

**File:** `app.py` (modifications)

```python
# Add after Firebase initialization (line ~46)
from celery_app import celery_app

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # ... existing configuration ...

    # Initialize Celery with Flask app context
    celery_app.conf.update(flask_app=app)

    class ContextTask(celery_app.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask

    # ... rest of create_app ...
```

---

### Task 3.2: Video Generation API Endpoint

**File:** `api/video_generation_routes.py` (new)

```python
"""Video Generation API Routes

Handles asynchronous video generation requests with token debiting.
"""
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from firebase_admin import firestore

from api.auth_routes import login_required, get_current_user_id
from services.token_service import TokenService, InsufficientTokensError
from services.transaction_service import TransactionService
from jobs.video_worker import generate_video_task

logger = logging.getLogger(__name__)

video_generation_bp = Blueprint('video_generation', __name__, url_prefix='/api/generate')

# Constants
VIDEO_GENERATION_COST = 10  # tokens

# Initialize services
token_service = TokenService()
transaction_service = TransactionService()
db = firestore.client()

@video_generation_bp.route('/video', methods=['POST'])
@login_required
def generate_video():
    """
    Generate video asynchronously with token debit.

    Request:
        {
            "prompt": "A serene sunset over mountains",
            "aspectRatio": "9:16",
            "duration": 8
        }

    Response (202 Accepted):
        {
            "success": true,
            "creationId": "uuid-here",
            "cost": 10,
            "status": "pending"
        }
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()

        # Validate request
        prompt = data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400

        aspect_ratio = data.get('aspectRatio', '9:16')
        duration = data.get('duration', 8)

        # Validate parameters
        if aspect_ratio not in ['16:9', '9:16']:
            return jsonify({'success': False, 'error': 'Invalid aspect ratio'}), 400

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

            # 3. Create creation document
            creation_data = {
                'userId': user_id,
                'prompt': prompt,
                'aspectRatio': aspect_ratio,
                'duration': duration,
                'cost': VIDEO_GENERATION_COST,
                'status': 'pending',
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

        # Enqueue background job
        task = generate_video_task.apply_async(
            args=[creation_id],
            task_id=creation_id,  # Use creation_id as task_id for idempotency
            countdown=2  # 2 second delay to ensure Firestore write completes
        )

        logger.info(f"🚀 Enqueued video generation job: {task.id}")

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

@video_generation_bp.route('/video/<creation_id>', methods=['GET'])
@login_required
def get_creation_status(creation_id):
    """
    Get the status of a video generation request.

    Response:
        {
            "success": true,
            "creation": {
                "id": "uuid",
                "status": "pending|processing|draft|failed",
                "mediaUrl": "https://...",  // if status == "draft"
                "error": "...",  // if status == "failed"
                "progress": 0.75  // optional
            }
        }
    """
    try:
        user_id = get_current_user_id()

        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            return jsonify({'success': False, 'error': 'Creation not found'}), 404

        creation_data = creation_doc.to_dict()

        # Verify ownership
        if creation_data.get('userId') != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        return jsonify({
            'success': True,
            'creation': {
                'id': creation_id,
                **creation_data
            }
        })

    except Exception as e:
        logger.error(f"Failed to get creation status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
```

**Register Blueprint in `app.py`:**
```python
from api.video_generation_routes import video_generation_bp
app.register_blueprint(video_generation_bp)
```

---

### Task 3.3: Video Generation Worker

**File:** `jobs/video_worker.py` (new)

```python
"""Video Generation Background Worker

Processes video generation requests asynchronously using Celery.
Implements comprehensive error handling, retry logic, and state management.
"""
import logging
import os
import time
from typing import Optional
from celery import Task
from firebase_admin import firestore
from google.api_core.exceptions import GoogleAPIError

from celery_app import celery_app
from services.veo_video_generation_service import (
    VeoVideoGenerationService,
    VeoGenerationParams,
    VeoOperationResult
)
from services.token_service import TokenService
import boto3
from botocore.client import Config

logger = logging.getLogger(__name__)

# Initialize services
veo_service = VeoVideoGenerationService()
token_service = TokenService()
db = firestore.client()

# R2 Configuration
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_ENDPOINT_URL = os.getenv('R2_ENDPOINT_URL')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL')

# Initialize R2 client
s3_client = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

class VideoGenerationError(Exception):
    """Base exception for video generation errors."""
    pass

class ContentPolicyViolationError(VideoGenerationError):
    """Raised when prompt violates content policy (permanent failure)."""
    pass

class TransientAPIError(VideoGenerationError):
    """Raised for temporary API failures (retriable)."""
    pass

@celery_app.task(bind=True, name='jobs.video_worker.generate_video_task', max_retries=3)
def generate_video_task(self: Task, creation_id: str) -> dict:
    """
    Generate video from prompt and upload to R2.

    This task implements:
    - Idempotency (safe to retry)
    - State management via Firestore
    - Automatic retries for transient failures
    - Token refunds for permanent failures
    - Cost tracking labels

    Args:
        creation_id: UUID of the creation document in Firestore

    Returns:
        dict: Result metadata
    """
    logger.info(f"🎬 Starting video generation for creation: {creation_id}")

    try:
        # 1. Fetch creation document (source of truth)
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            logger.error(f"Creation {creation_id} not found in Firestore")
            raise VideoGenerationError("Creation not found")

        creation_data = creation_doc.to_dict()
        user_id = creation_data.get('userId')
        prompt = creation_data.get('prompt')
        aspect_ratio = creation_data.get('aspectRatio', '9:16')
        duration = creation_data.get('duration', 8)

        # Check if already processed (idempotency)
        current_status = creation_data.get('status')
        if current_status in ['draft', 'published']:
            logger.info(f"Creation {creation_id} already processed (status: {current_status})")
            return {'success': True, 'status': current_status, 'cached': True}

        # 2. Update status to 'processing'
        creation_ref.update({
            'status': 'processing',
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'workerStartedAt': firestore.SERVER_TIMESTAMP
        })

        # 3. Call Veo API with cost tracking
        logger.info(f"📡 Calling Veo API for creation {creation_id}")

        params = VeoGenerationParams(
            model="veo-3.1-fast-generate-preview",
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration,
            enhance_prompt=True,
            sample_count=1,
            # Store in GCS temporarily (Veo requirement)
            storage_uri=f"gs://phoenix-videos/temp/{creation_id}.mp4"
        )

        start_time = time.time()
        result: VeoOperationResult = veo_service.start_generation(
            params,
            poll=True,
            poll_interval=5.0,
            timeout=300.0
        )
        generation_time = time.time() - start_time

        # 4. Handle API errors
        if not result.success:
            error_msg = result.error or "Unknown error"
            logger.error(f"Veo generation failed for {creation_id}: {error_msg}")

            # Check if it's a content policy violation (permanent failure)
            if "content policy" in error_msg.lower() or "safety" in error_msg.lower():
                logger.warning(f"Content policy violation for creation {creation_id}")
                raise ContentPolicyViolationError(error_msg)

            # Otherwise, treat as transient error (retriable)
            raise TransientAPIError(error_msg)

        # 5. Download from GCS and upload to R2
        if not result.gcs_uris:
            logger.error(f"No GCS URIs returned for creation {creation_id}")
            raise VideoGenerationError("No video generated")

        gcs_uri = result.gcs_uris[0]
        logger.info(f"📥 Downloading video from GCS: {gcs_uri}")

        # Download from GCS
        from google.cloud import storage
        storage_client = storage.Client()
        bucket_name = gcs_uri.split('/')[2]
        blob_name = '/'.join(gcs_uri.split('/')[3:])
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        video_bytes = blob.download_as_bytes()

        logger.info(f"📤 Uploading video to R2: {len(video_bytes)} bytes")

        # Upload to R2
        r2_key = f"videos/{user_id}/{creation_id}.mp4"
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
                'phase': '3'
            }
        )

        media_url = f"{R2_PUBLIC_URL}/{r2_key}"
        logger.info(f"✅ Video uploaded to R2: {media_url}")

        # Clean up GCS temporary file
        try:
            blob.delete()
            logger.info(f"🗑️ Cleaned up GCS temp file: {gcs_uri}")
        except Exception as e:
            logger.warning(f"Failed to delete GCS temp file: {e}")

        # 6. Update creation document to 'draft'
        creation_ref.update({
            'status': 'draft',
            'mediaUrl': media_url,
            'generationTime': generation_time,
            'modelUsed': params.model,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'completedAt': firestore.SERVER_TIMESTAMP
        })

        logger.info(f"🎉 Video generation complete for creation {creation_id}")

        return {
            'success': True,
            'creation_id': creation_id,
            'media_url': media_url,
            'generation_time': generation_time
        }

    except ContentPolicyViolationError as e:
        # Permanent failure - refund tokens and mark as failed
        logger.error(f"Content policy violation for creation {creation_id}: {e}")
        _handle_permanent_failure(creation_id, user_id, str(e))
        return {'success': False, 'error': 'Content policy violation', 'refunded': True}

    except TransientAPIError as e:
        # Temporary failure - retry with exponential backoff
        logger.warning(f"Transient API error for creation {creation_id}: {e}")

        # Update status to show retry
        creation_ref.update({
            'status': 'pending',  # Back to pending for retry
            'retryCount': firestore.Increment(1),
            'lastError': str(e),
            'updatedAt': firestore.SERVER_TIMESTAMP
        })

        # Retry with exponential backoff
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)  # 60s, 120s, 240s

        logger.info(f"Retrying creation {creation_id} in {countdown}s (attempt {retry_count + 1}/3)")

        raise self.retry(exc=e, countdown=countdown, max_retries=3)

    except Exception as e:
        # Unexpected error - log and fail after retries
        logger.error(f"Unexpected error for creation {creation_id}: {e}", exc_info=True)

        # If we've exhausted retries, mark as failed and refund
        if self.request.retries >= self.max_retries:
            logger.error(f"Max retries exceeded for creation {creation_id}, refunding tokens")
            _handle_permanent_failure(creation_id, user_id, f"Max retries exceeded: {str(e)}")
            return {'success': False, 'error': 'Max retries exceeded', 'refunded': True}

        # Otherwise retry
        raise self.retry(exc=e, countdown=60)

def _handle_permanent_failure(creation_id: str, user_id: str, error_message: str) -> None:
    """
    Handle permanent failures by refunding tokens and marking creation as failed.

    This function implements an atomic transaction to ensure tokens are refunded
    exactly once, even if called multiple times.
    """
    try:
        @firestore.transactional
        def refund_and_fail(transaction):
            creation_ref = db.collection('creations').document(creation_id)
            user_ref = db.collection('users').document(user_id)

            # Check if already refunded
            creation_doc = creation_ref.get(transaction=transaction)
            if not creation_doc.exists:
                logger.warning(f"Creation {creation_id} not found during refund")
                return

            creation_data = creation_doc.to_dict()
            if creation_data.get('refunded'):
                logger.info(f"Creation {creation_id} already refunded")
                return

            cost = creation_data.get('cost', 10)

            # Refund tokens
            transaction.update(user_ref, {
                'tokenBalance': firestore.Increment(cost),
                'totalTokensSpent': firestore.Increment(-cost)
            })

            # Mark creation as failed and refunded
            transaction.update(creation_ref, {
                'status': 'failed',
                'error': error_message,
                'refunded': True,
                'refundedAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })

            # Record refund transaction
            tx_ref = db.collection('transactions').document()
            transaction.set(tx_ref, {
                'userId': user_id,
                'type': 'refund',
                'amount': cost,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'details': {
                    'creationId': creation_id,
                    'reason': 'Video generation failed',
                    'error': error_message[:200]
                }
            })

        # Execute refund transaction
        transaction = db.transaction()
        refund_and_fail(transaction)
        logger.info(f"✅ Refunded tokens for failed creation {creation_id}")

    except Exception as e:
        logger.error(f"Failed to refund tokens for creation {creation_id}: {e}", exc_info=True)
```

---

### Task 3.4: Update Deployment Configuration

**File:** `cloudbuild.yaml` (modifications)

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/phoenix', '.']

  # Push the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/phoenix']

  # Deploy API service
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
    - 'run'
    - 'deploy'
    - 'phoenix-api-prod'
    - '--image'
    - 'gcr.io/$PROJECT_ID/phoenix'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
    - '--memory'
    - '1Gi'
    - '--cpu'
    - '1'
    - '--timeout'
    - '3600'
    - '--concurrency'
    - '8'
    - '--max-instances'
    - '100'
    - '--service-account'
    - 'phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com'
    - '--labels'
    - 'app=phoenix,service=api,env=prod,phase=3'
    - '--update-secrets'
    - 'REDIS_HOST=phoenix-redis-host:latest,REDIS_PORT=phoenix-redis-port:latest,GEMINI_API_KEY=phoenix-gemini-api-key:latest,SECRET_KEY=phoenix-secret-key:latest,...'
    - '--update-env-vars'
    - 'DEFAULT_MODEL=gemini-1.5-flash-8b,FLASK_ENV=production,...'

  # Deploy video worker service
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
    - 'run'
    - 'deploy'
    - 'phoenix-video-worker'
    - '--image'
    - 'gcr.io/$PROJECT_ID/phoenix'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--no-allow-unauthenticated'  # Worker only, no public access
    - '--memory'
    - '4Gi'  # Higher memory for video processing
    - '--cpu'
    - '2'  # More CPU for video processing
    - '--timeout'
    - '600'  # 10 minutes for video generation
    - '--concurrency'
    - '1'  # Process one video at a time
    - '--max-instances'
    - '10'  # Scale to handle concurrent requests
    - '--min-instances'
    - '1'  # Keep warm for faster response
    - '--service-account'
    - 'phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com'
    - '--labels'
    - 'app=phoenix,service=worker,env=prod,phase=3'
    - '--command'
    - 'celery'
    - '--args'
    - '-A,celery_app,worker,--loglevel=info,--concurrency=2'
    - '--update-secrets'
    - 'REDIS_HOST=phoenix-redis-host:latest,REDIS_PORT=phoenix-redis-port:latest,...'
    - '--update-env-vars'
    - 'FLASK_ENV=production,WORKER_MODE=true,...'

images:
  - 'gcr.io/$PROJECT_ID/phoenix'

options:
  logging: CLOUD_LOGGING_ONLY
```

---

### Task 3.5: Firestore Schema

**Collection:** `creations`

```javascript
// Firestore document structure
{
  // Core fields
  "userId": "firebase-uid",
  "prompt": "A serene sunset over mountains",
  "aspectRatio": "9:16",
  "duration": 8,
  "cost": 10,

  // Status tracking
  "status": "pending" | "processing" | "draft" | "published" | "failed",
  "progress": 0.75,  // Optional, for progress updates

  // Result
  "mediaUrl": "https://pub-xxx.r2.dev/videos/user-id/creation-id.mp4",
  "generationTime": 87.3,  // seconds
  "modelUsed": "veo-3.1-fast-generate-preview",

  // Error handling
  "error": "Content policy violation",
  "retryCount": 2,
  "lastError": "...",
  "refunded": true,

  // Timestamps
  "createdAt": Timestamp,
  "updatedAt": Timestamp,
  "workerStartedAt": Timestamp,
  "completedAt": Timestamp,
  "refundedAt": Timestamp
}
```

**Firestore Rules:**

```javascript
// firestore.rules
match /creations/{creationId} {
  // Users can read their own creations
  allow read: if request.auth != null
    && request.auth.uid == resource.data.userId;

  // Only backend can create creations (via API)
  allow create: if false;

  // Only backend can update creations (via worker)
  allow update: if false;

  // Users can delete their draft creations
  allow delete: if request.auth != null
    && request.auth.uid == resource.data.userId
    && resource.data.status == 'draft';
}
```

---

## Testing Plan

### Phase 3.1: API Endpoint Testing

**Test 1: Successful Video Generation**
```bash
curl -X POST https://phoenix-api-prod.run.app/api/generate/video \
  -H "Authorization: Bearer $FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene sunset over mountains",
    "aspectRatio": "9:16",
    "duration": 8
  }'
```

**Expected Response (202 Accepted):**
```json
{
  "success": true,
  "creationId": "uuid-here",
  "cost": 10,
  "status": "pending",
  "estimatedTime": "60-120 seconds"
}
```

**Verification Steps:**
1. Check Firestore `creations` collection - document exists with `status: "pending"`
2. Check user's `tokenBalance` - decreased by 10
3. Check `transactions` collection - debit transaction recorded
4. Wait 60-120 seconds
5. Check creation document - `status` updated to `"draft"`, `mediaUrl` populated
6. Access `mediaUrl` - video plays successfully

---

### Phase 3.2: Error Handling Testing

**Test 2: Insufficient Tokens**
```bash
# First, drain user's token balance
# Then attempt generation
```

**Expected Response (402 Payment Required):**
```json
{
  "success": false,
  "error": "Insufficient tokens",
  "required": 10,
  "balance": 5
}
```

**Verification:**
- No creation document created
- No tokens debited
- No transaction recorded

---

**Test 3: Content Policy Violation**
```bash
curl -X POST ... -d '{
  "prompt": "Explicit violent content [trigger safety filter]",
  ...
}'
```

**Expected Behavior:**
1. Initial response: `202 Accepted`
2. Worker processes job
3. Veo API returns content policy error
4. Worker catches `ContentPolicyViolationError`
5. Creation status updated to `"failed"`
6. Tokens refunded (balance restored)
7. Refund transaction recorded

**Verification:**
```python
# check_refund.py
creation = db.collection('creations').document(creation_id).get()
assert creation.get('status') == 'failed'
assert creation.get('refunded') == True
assert 'content policy' in creation.get('error').lower()

# Verify token balance restored
user = db.collection('users').document(user_id).get()
assert user.get('tokenBalance') == original_balance
```

---

**Test 4: Transient API Failure**

Simulate by temporarily breaking Veo API credentials.

**Expected Behavior:**
1. Worker catches `TransientAPIError`
2. Increments `retryCount` in creation document
3. Re-queues job with exponential backoff (60s → 120s → 240s)
4. After 3 retries, if still failing, marks as failed and refunds

---

### Phase 3.3: Load Testing

**Test 5: Concurrent Requests**
```bash
# Generate 10 concurrent video requests
for i in {1..10}; do
  curl -X POST ... &
done
wait
```

**Expected Behavior:**
- All 10 requests return `202 Accepted` immediately
- All 10 tokens debited atomically (no race conditions)
- Workers process jobs concurrently (up to 10 instances scale)
- All 10 videos generated successfully within 2-3 minutes

---

## Cost Tracking Verification

### GCP Billing Dashboard Filters

**Filter by Phase 3 Resources:**
```
labels.app = "phoenix"
labels.phase = "3"
```

**Expected Cost Breakdown:**
- **Cloud Memorystore (Redis):** ~$40/month (1GB BASIC tier)
- **Cloud Run (Worker):** ~$20/month (1 instance warm, 4GB RAM)
- **Vertex AI (Veo):** ~$0.32/video (estimate)
- **Cloud Storage (Temp):** ~$0.01/month (temporary files)
- **Cloudflare R2:** $0 (egress) + ~$0.28/month (storage for 10K videos)

**Total Phase 3 Infrastructure:** ~$60/month + $0.32/video

---

## Rollout Plan

### Step 1: Provision Infrastructure
```bash
chmod +x provision_resources.sh
./provision_resources.sh
```

### Step 2: Add Redis Credentials to Secret Manager
```bash
REDIS_HOST=$(gcloud redis instances describe phoenix-cache-prod --region=us-central1 --format="value(host)")
REDIS_PORT=$(gcloud redis instances describe phoenix-cache-prod --region=us-central1 --format="value(port)")

echo -n "$REDIS_HOST" | gcloud secrets create phoenix-redis-host --data-file=-
echo -n "$REDIS_PORT" | gcloud secrets create phoenix-redis-port --data-file=-
```

### Step 3: Deploy
```bash
gcloud builds submit --config cloudbuild.yaml .
```

### Step 4: Test
```bash
python test_video_generation.py
```

### Step 5: Monitor
```bash
# Worker logs
gcloud run services logs read phoenix-video-worker --region=us-central1 --limit=100

# API logs
gcloud run services logs read phoenix-api-prod --region=us-central1 --limit=100 --filter="video generation"
```

---

## Success Criteria

**✅ Phase 3 Complete When:**
1. API endpoint responds in <100ms with `202 Accepted`
2. Tokens debited atomically (no race conditions in concurrent tests)
3. Videos generated successfully in 60-120 seconds
4. Content policy violations trigger automatic refunds
5. Transient errors retry automatically (3 attempts)
6. All GCP resources labeled with `app=phoenix,phase=3`
7. Cost tracking visible in GCP Billing dashboard
8. Worker scales from 1 to 10 instances under load
9. No duplicate token charges (idempotency verified)
10. R2 storage working with $0 egress costs

---

## Next Steps (Phase 4)

After Phase 3 is verified:
- [ ] Build publishing flow (draft → published)
- [ ] Implement social feed UI
- [ ] Add like/comment functionality
- [ ] Creator tipping system
- [ ] Video editing/filters
- [ ] Analytics dashboard

---

**End of Implementation Plan**
