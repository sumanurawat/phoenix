"""
Checkpoint management for job recovery.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from firebase_admin import firestore
from google.api_core import exceptions as firestore_exceptions

from jobs.shared.config import JobConfig
from jobs.shared.schemas import JobCheckpoint

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages job checkpoints for failure recovery."""

    def __init__(self):
        self.db = firestore.client()
        self.collection = self.db.collection(JobConfig.CHECKPOINTS_COLLECTION)

    async def save_checkpoint(
        self,
        job_id: str,
        checkpoint_name: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Save a checkpoint for a job.

        Args:
            job_id: Unique job identifier
            checkpoint_name: Name of the checkpoint
            data: Checkpoint data to save

        Raises:
            Exception: If checkpoint save fails
        """
        try:
            checkpoint = JobCheckpoint(
                job_id=job_id,
                checkpoint_name=checkpoint_name,
                timestamp=datetime.now(timezone.utc),
                data=data
            )

            # Use job_id + checkpoint_name as document ID for easy retrieval
            doc_id = f"{job_id}_{checkpoint_name}"

            await self._async_firestore_operation(
                self.collection.document(doc_id).set,
                checkpoint.to_dict()
            )

            logger.info(
                f"Saved checkpoint {checkpoint_name} for job {job_id}",
                extra={
                    "job_id": job_id,
                    "checkpoint": checkpoint_name,
                    "data_keys": list(data.keys())
                }
            )

        except Exception as e:
            logger.error(f"Failed to save checkpoint {checkpoint_name} for job {job_id}: {e}")
            raise

    async def get_checkpoint(
        self,
        job_id: str,
        checkpoint_name: str
    ) -> Optional[JobCheckpoint]:
        """
        Get a specific checkpoint for a job.

        Args:
            job_id: Unique job identifier
            checkpoint_name: Name of the checkpoint

        Returns:
            JobCheckpoint if found, None otherwise
        """
        try:
            doc_id = f"{job_id}_{checkpoint_name}"
            doc = await self._async_firestore_operation(
                self.collection.document(doc_id).get
            )

            if doc.exists:
                data = doc.to_dict()
                return JobCheckpoint(
                    job_id=data['jobId'],
                    checkpoint_name=data['checkpointName'],
                    timestamp=data['timestamp'],
                    data=data['data']
                )

            return None

        except Exception as e:
            logger.error(f"Failed to get checkpoint {checkpoint_name} for job {job_id}: {e}")
            return None

    async def get_last_checkpoint(self, job_id: str) -> Optional[JobCheckpoint]:
        """
        Get the most recent checkpoint for a job.

        Args:
            job_id: Unique job identifier

        Returns:
            Most recent JobCheckpoint if found, None otherwise
        """
        try:
            query = self.collection.where('jobId', '==', job_id).order_by(
                'timestamp', direction=firestore.Query.DESCENDING
            ).limit(1)

            docs = await self._async_firestore_operation(query.stream)
            docs_list = [doc async for doc in docs]

            if docs_list:
                data = docs_list[0].to_dict()
                return JobCheckpoint(
                    job_id=data['jobId'],
                    checkpoint_name=data['checkpointName'],
                    timestamp=data['timestamp'],
                    data=data['data']
                )

            return None

        except Exception as e:
            logger.error(f"Failed to get last checkpoint for job {job_id}: {e}")
            return None

    async def get_all_checkpoints(self, job_id: str) -> List[JobCheckpoint]:
        """
        Get all checkpoints for a job, ordered by timestamp.

        Args:
            job_id: Unique job identifier

        Returns:
            List of JobCheckpoint objects
        """
        try:
            query = self.collection.where('jobId', '==', job_id).order_by('timestamp')

            docs = await self._async_firestore_operation(query.stream)
            checkpoints = []

            async for doc in docs:
                data = doc.to_dict()
                checkpoint = JobCheckpoint(
                    job_id=data['jobId'],
                    checkpoint_name=data['checkpointName'],
                    timestamp=data['timestamp'],
                    data=data['data']
                )
                checkpoints.append(checkpoint)

            return checkpoints

        except Exception as e:
            logger.error(f"Failed to get checkpoints for job {job_id}: {e}")
            return []

    async def delete_job_checkpoints(self, job_id: str) -> None:
        """
        Delete all checkpoints for a job.

        Args:
            job_id: Unique job identifier
        """
        try:
            query = self.collection.where('jobId', '==', job_id)
            docs = await self._async_firestore_operation(query.stream)

            batch = self.db.batch()
            count = 0

            async for doc in docs:
                batch.delete(doc.reference)
                count += 1

                # Firestore batch limit is 500 operations
                if count >= 500:
                    await self._async_firestore_operation(batch.commit)
                    batch = self.db.batch()
                    count = 0

            if count > 0:
                await self._async_firestore_operation(batch.commit)

            logger.info(f"Deleted checkpoints for job {job_id}")

        except Exception as e:
            logger.error(f"Failed to delete checkpoints for job {job_id}: {e}")

    async def cleanup_old_checkpoints(self, hours_old: int = 72) -> None:
        """
        Clean up checkpoints older than specified hours.

        Args:
            hours_old: Age threshold in hours (default: 72 hours)
        """
        try:
            from datetime import timedelta

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)

            query = self.collection.where('timestamp', '<', cutoff_time)
            docs = await self._async_firestore_operation(query.stream)

            batch = self.db.batch()
            count = 0

            async for doc in docs:
                batch.delete(doc.reference)
                count += 1

                if count >= 500:
                    await self._async_firestore_operation(batch.commit)
                    batch = self.db.batch()
                    count = 0

            if count > 0:
                await self._async_firestore_operation(batch.commit)

            logger.info(f"Cleaned up {count} old checkpoints (older than {hours_old} hours)")

        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints: {e}")

    async def _async_firestore_operation(self, operation, *args, **kwargs):
        """
        Execute Firestore operation asynchronously.

        This is a workaround since firebase-admin doesn't have native async support.
        """
        import asyncio
        import concurrent.futures

        loop = asyncio.get_event_loop()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(operation, *args, **kwargs)
            return await loop.run_in_executor(None, future.result)


class CheckpointStrategy:
    """Defines common checkpoint strategies for different job types."""

    @staticmethod
    def video_stitching_checkpoints() -> List[str]:
        """Standard checkpoints for video stitching jobs."""
        return [
            "initialized",
            "clips_downloaded",
            "validation_complete",
            "stitching_started",
            "stitching_progress_25",
            "stitching_progress_50",
            "stitching_progress_75",
            "stitching_complete",
            "upload_started",
            "upload_complete"
        ]

    @staticmethod
    def video_generation_checkpoints() -> List[str]:
        """Standard checkpoints for video generation jobs."""
        return [
            "initialized",
            "prompts_validated",
            "generation_started",
            "clips_generated",
            "upload_complete"
        ]