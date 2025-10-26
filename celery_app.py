"""Celery Application for Phoenix Background Jobs

Configured for async video generation with Redis as broker.
Integrates with Flask app context for database access.
"""
import os
import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

logger = logging.getLogger(__name__)

# Read Redis connection from environment (populated from Secret Manager in production)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')  # Optional auth

# Build Redis URL
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'

logger.info(f"Initializing Celery with broker: redis://{REDIS_HOST}:{REDIS_PORT}/0")

# Initialize Celery app
celery_app = Celery(
    'phoenix',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['jobs.async_video_generation_worker']  # Auto-discover tasks
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max (hard limit)
    task_soft_time_limit=570,  # 9.5 minutes (warning)

    # Worker configuration
    worker_prefetch_multiplier=1,  # Process one task at a time (for video jobs)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory cleanup)

    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'redis-master'  # For Redis Sentinel (if used)
    },

    # Retry policy
    task_acks_late=True,  # Acknowledge task only after completion
    task_reject_on_worker_lost=True,  # Re-queue task if worker crashes

    # Performance
    worker_disable_rate_limits=True,  # No rate limiting (we control cost via tokens)

    # Logging
    worker_redirect_stdouts=True,
    worker_redirect_stdouts_level='INFO'
)

# Logging hooks for monitoring
@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Log when task starts."""
    logger.info(f"🎬 Task starting: {task.name} [ID: {task_id}]")

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, retval=None, **kwargs):
    """Log when task completes."""
    logger.info(f"✅ Task complete: {task.name} [ID: {task_id}]")
    if retval and isinstance(retval, dict):
        status = retval.get('status', retval.get('success'))
        logger.info(f"   Result: {status}")

@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    """Log when task fails."""
    logger.error(f"❌ Task failed: [ID: {task_id}]")
    logger.error(f"   Exception: {exception}")

# Periodic tasks configuration (for cleanup)
celery_app.conf.beat_schedule = {
    'cleanup-orphaned-processing': {
        'task': 'jobs.async_video_generation_worker.cleanup_orphaned_processing',
        'schedule': 600.0,  # Every 10 minutes
    },
}

logger.info("✅ Celery app initialized successfully")
logger.info(f"   Broker: redis://{REDIS_HOST}:{REDIS_PORT}/0")
logger.info(f"   Tasks: {celery_app.conf.include}")
logger.info(f"   Time limit: {celery_app.conf.task_time_limit}s")
