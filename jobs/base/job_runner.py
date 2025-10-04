"""
Base job runner framework for Cloud Run Jobs.
"""
import asyncio
import logging
import os
import signal
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import firebase_admin
from firebase_admin import credentials

from jobs.shared.config import JobConfig
from jobs.shared.schemas import JobPayload, JobStatus, JobError
from jobs.base.checkpoint_manager import CheckpointManager
from jobs.base.monitoring import JobMonitor


logger = logging.getLogger(__name__)


# Initialize Firebase Admin SDK (only once)
def _initialize_firebase():
    """Initialize Firebase Admin SDK with Application Default Credentials."""
    try:
        # Check if already initialized
        firebase_admin.get_app()
        logger.info("Firebase Admin SDK already initialized")
    except ValueError:
        # Not initialized, initialize now
        try:
            # Try with Application Default Credentials (works in Cloud Run)
            firebase_admin.initialize_app()
            logger.info("✅ Firebase Admin SDK initialized with ADC")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase: {e}")
            raise

# Initialize on module load
_initialize_firebase()


class BaseJobRunner(ABC):
    """
    Abstract base class for all Cloud Run Jobs.

    Provides common functionality:
    - Job lifecycle management
    - Progress tracking
    - Checkpoint/recovery
    - Error handling
    - Resource cleanup
    - Graceful shutdown
    """

    def __init__(self, job_type: str):
        self.job_type = job_type
        self.job_id: Optional[str] = None
        self.payload: Optional[JobPayload] = None
        self.start_time: Optional[datetime] = None
        self.temp_dir: Optional[str] = None
        self.is_shutting_down = False

        # Initialize components
        self.checkpoint_manager = CheckpointManager()
        self.monitor = JobMonitor(job_type)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)

    async def run(self, payload_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for job execution.

        Args:
            payload_dict: Job payload as dictionary

        Returns:
            Job result dictionary

        Raises:
            JobError: If job fails
        """
        try:
            # Parse payload
            self.payload = await self._parse_payload(payload_dict)
            self.job_id = self.payload.job_id

            logger.info(
                f"Starting job {self.job_id}",
                extra={
                    "job_id": self.job_id,
                    "job_type": self.job_type,
                    "project_id": self.payload.project_id,
                    "retry_attempt": self.payload.retry_attempt
                }
            )

            # Initialize job
            await self._initialize()

            # Check for existing checkpoints
            last_checkpoint = await self.checkpoint_manager.get_last_checkpoint(self.job_id)

            if last_checkpoint and self.payload.retry_attempt > 0:
                logger.info(f"Resuming from checkpoint: {last_checkpoint.checkpoint_name}")
                await self._restore_from_checkpoint(last_checkpoint)
            else:
                logger.info("Starting fresh job execution")

            # Update status to running
            await self._update_status("running", "Job started")

            # Execute main job logic
            result = await self._execute_with_monitoring()

            # Mark as completed
            await self._update_status("completed", "Job completed successfully")

            logger.info(
                f"Job {self.job_id} completed successfully",
                extra={
                    "job_id": self.job_id,
                    "duration_seconds": self._get_duration(),
                    "result_keys": list(result.keys()) if result else []
                }
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Job {self.job_id} failed: {error_msg}",
                extra={
                    "job_id": self.job_id,
                    "error": error_msg,
                    "duration_seconds": self._get_duration()
                },
                exc_info=True
            )

            await self._update_status("failed", error_msg)
            raise JobError(f"Job failed: {error_msg}") from e

        finally:
            await self._cleanup()

    async def _initialize(self) -> None:
        """Initialize job resources."""
        self.start_time = datetime.now(timezone.utc)

        # Create temporary directory
        self.temp_dir = JobConfig.get_temp_dir(self.job_id)
        os.makedirs(self.temp_dir, exist_ok=True)

        logger.info(f"Initialized job with temp dir: {self.temp_dir}")

        # Validate configuration
        JobConfig.validate()

        # Custom initialization
        await self.initialize()

    async def _execute_with_monitoring(self) -> Dict[str, Any]:
        """Execute job with progress monitoring."""
        try:
            # Start monitoring
            self.monitor.start_job(self.job_id)

            # Execute main job logic
            result = await self.process(self.payload)

            # Record success metrics
            self.monitor.record_success(self._get_duration())

            return result

        except Exception as e:
            # Record failure metrics
            self.monitor.record_failure(str(e), self._get_duration())
            raise

    async def _cleanup(self) -> None:
        """Clean up job resources."""
        try:
            # Custom cleanup
            await self.cleanup()

            # Remove temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temp directory: {self.temp_dir}")

        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    def _handle_sigterm(self, signum, frame):
        """Handle SIGTERM signal for graceful shutdown."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_shutting_down = True

        # Save current progress if job is running
        if self.job_id:
            try:
                asyncio.create_task(self._save_shutdown_checkpoint())
            except Exception as e:
                logger.error(f"Failed to save shutdown checkpoint: {e}")

        sys.exit(0)

    async def _save_shutdown_checkpoint(self) -> None:
        """Save checkpoint when shutting down gracefully."""
        try:
            checkpoint_data = await self.get_checkpoint_data()
            if checkpoint_data:
                await self.checkpoint_manager.save_checkpoint(
                    self.job_id,
                    "shutdown_interrupt",
                    checkpoint_data
                )
                logger.info("Saved shutdown checkpoint for recovery")
        except Exception as e:
            logger.error(f"Failed to save shutdown checkpoint: {e}")

    def _get_duration(self) -> float:
        """Get job duration in seconds."""
        if not self.start_time:
            return 0.0
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    async def _update_status(self, status: str, message: str, progress: float = None) -> None:
        """Update job status in Firestore."""
        try:
            from firebase_admin import firestore

            db = firestore.client()

            update_data = {
                'status': status,
                'message': message,
                'updatedAt': datetime.now(timezone.utc)
            }

            if progress is not None:
                update_data['progress'] = progress

            if status == "running" and not hasattr(self, '_start_time_saved'):
                update_data['startedAt'] = self.start_time
                self._start_time_saved = True

            if status in ["completed", "failed"]:
                update_data['completedAt'] = datetime.now(timezone.utc)

            db.collection(JobConfig.JOBS_COLLECTION).document(self.job_id).update(update_data)

        except Exception as e:
            logger.warning(f"Failed to update job status: {e}")

    async def save_checkpoint(self, checkpoint_name: str, data: Dict[str, Any]) -> None:
        """Save a checkpoint for recovery."""
        await self.checkpoint_manager.save_checkpoint(self.job_id, checkpoint_name, data)
        logger.info(f"Saved checkpoint: {checkpoint_name}")

    async def update_progress(self, progress: float, message: str = None) -> None:
        """Update job progress."""
        if message:
            logger.info(f"Progress {progress:.1f}%: {message}")
        else:
            logger.info(f"Progress: {progress:.1f}%")

        await self._update_status("running", message or f"Processing... {progress:.1f}%", progress)

    # Abstract methods that subclasses must implement

    @abstractmethod
    async def _parse_payload(self, payload_dict: Dict[str, Any]) -> JobPayload:
        """Parse and validate job payload."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize job-specific resources."""
        pass

    @abstractmethod
    async def process(self, payload: JobPayload) -> Dict[str, Any]:
        """Main job processing logic."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Job-specific cleanup."""
        pass

    @abstractmethod
    async def get_checkpoint_data(self) -> Dict[str, Any]:
        """Get current state for checkpointing."""
        pass

    @abstractmethod
    async def _restore_from_checkpoint(self, checkpoint) -> None:
        """Restore job state from checkpoint."""
        pass


class JobExecutor:
    """
    Utility class to execute jobs from command line or Cloud Run.
    """

    @staticmethod
    async def execute_job(job_runner: BaseJobRunner, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a job with proper error handling and logging setup.

        Args:
            job_runner: Job runner instance
            payload: Job payload dictionary

        Returns:
            Job result dictionary
        """
        # Set up logging
        logging.basicConfig(
            level=getattr(logging, JobConfig.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        try:
            result = await job_runner.run(payload)
            return {"success": True, "result": result}

        except JobError as e:
            return {"success": False, "error": str(e)}

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {"success": False, "error": f"Unexpected error: {e}"}