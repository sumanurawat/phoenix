"""
Job Orchestrator Service - Manages Cloud Run Jobs execution and monitoring.
"""
import logging
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from firebase_admin import firestore
try:
    from google.cloud import tasks_v2
    from google.cloud import run_v2
    from google.cloud import storage
    from google.api_core import exceptions as google_exceptions
    CLOUD_TASKS_AVAILABLE = True
except ImportError:
    # Fallback for local development without Cloud Tasks
    CLOUD_TASKS_AVAILABLE = False
    tasks_v2 = None
    run_v2 = None
    storage = None
    google_exceptions = None

from jobs.shared.config import JobConfig
from jobs.shared.schemas import (
    JobStatus, StitchingJobPayload, JobAlreadyRunningError,
    InsufficientResourcesError, JobError
)
from jobs.shared.utils import generate_job_id

logger = logging.getLogger(__name__)


class JobExecution:
    """Represents a job execution instance."""

    def __init__(self, job_id: str, job_type: str, status: str = "queued"):
        self.job_id = job_id
        self.job_type = job_type
        self.status = status
        self.created_at = datetime.now(timezone.utc)


class JobOrchestrator:
    """
    Orchestrates Cloud Run Jobs for video processing operations.

    Handles:
    - Job creation and triggering
    - Status monitoring
    - Retry logic
    - Resource management
    """

    def __init__(self):
        self.db = firestore.client()

        # Initialize Cloud Run Jobs client
        if CLOUD_TASKS_AVAILABLE:
            try:
                self.jobs_client = run_v2.JobsClient()
                self.gcs_client = storage.Client()
                logger.info("Cloud Run Jobs client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Cloud Run Jobs client: {e}")
                self.jobs_client = None
                self.gcs_client = None
        else:
            logger.warning("Cloud Run Jobs not available - running in local mode")
            self.jobs_client = None
            self.gcs_client = None

        # Cloud configuration
        self.project_id = JobConfig.PROJECT_ID
        self.region = JobConfig.REGION
        
        # Auto-cleanup configuration
        self.stale_job_timeout_minutes = 15  # Jobs older than this are considered stale

        # Job type configurations (Cloud Run Job names)
        self.job_configs = {
            "video_stitching": {
                "job_name": "reel-stitching-job",
                "max_concurrent": 5,
                "timeout_minutes": 15,
                "memory_gb": 4
            },
            "video_generation": {
                "job_name": "reel-generation-job",
                "max_concurrent": 10,
                "timeout_minutes": 30,
                "memory_gb": 2
            }
        }

    def trigger_stitching_job(
        self,
        project_id: str,
        user_id: str,
        clip_paths: List[str],
        output_path: str,
        orientation: str = "portrait",
        compression: str = "optimized",
        force_restart: bool = False
    ) -> JobExecution:
        """
        Trigger a video stitching job.

        Args:
            project_id: Reel project ID
            user_id: User ID for authorization
            clip_paths: List of GCS paths to video clips
            output_path: GCS path for output video
            orientation: Video orientation ("portrait" | "landscape")
            compression: Compression setting ("optimized" | "lossless")
            force_restart: Skip existing job check

        Returns:
            JobExecution instance

        Raises:
            JobAlreadyRunningError: If job is already running
            InsufficientResourcesError: If requirements not met
            JobError: If job creation fails
        """
        logger.info(f"Triggering stitching job for project {project_id}")

        # Validate input
        if len(clip_paths) < 2:
            raise InsufficientResourcesError("At least 2 clips required for stitching")

        # Check for existing jobs
        if not force_restart:
            existing_job = self._get_active_job(project_id, "video_stitching")
            if existing_job:
                if existing_job.status in ["queued", "running"]:
                    raise JobAlreadyRunningError(f"Stitching job {existing_job.job_id} already running")
                elif existing_job.status == "failed" and existing_job.retry_count < JobConfig.MAX_RETRY_ATTEMPTS:
                    # Resume failed job
                    logger.info(f"Resuming failed job {existing_job.job_id}")
                    return self._retry_job(existing_job.job_id)

        # Create job payload
        job_id = generate_job_id()
        payload = StitchingJobPayload(
            job_id=job_id,
            project_id=project_id,
            user_id=user_id,
            clip_paths=clip_paths,
            output_path=output_path,
            orientation=orientation,
            compression=compression
        )

        # Create job record in Firestore
        job_status = self._create_job_record(job_id, "video_stitching", payload.to_dict())

        # Trigger via Cloud Run Jobs API
        if self.jobs_client:
            self._enqueue_job(job_id, "video_stitching", payload.to_dict())
        else:
            # Local development mode - simulate job queuing
            logger.warning(f"Local mode: Job {job_id} would be queued (Cloud Run Jobs not available)")
            # Update job status to simulate queuing
            self._update_job_status(job_id, "queued", "Job queued (local simulation)")

        logger.info(f"Successfully triggered stitching job {job_id}")

        return JobExecution(job_id, "video_stitching", "queued")

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """
        Get current status of a job.

        Args:
            job_id: Job identifier

        Returns:
            JobStatus if found, None otherwise
        """
        try:
            doc = self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).get()

            if not doc.exists:
                return None

            data = doc.to_dict()

            return JobStatus(
                job_id=job_id,
                job_type=data.get('jobType', ''),
                status=data.get('status', 'unknown'),
                progress=data.get('progress', 0.0),
                message=data.get('message', ''),
                error=data.get('error'),
                created_at=data.get('createdAt'),
                started_at=data.get('startedAt'),
                completed_at=data.get('completedAt'),
                retry_count=data.get('retryCount', 0),
                checkpoints=data.get('checkpoints', [])
            )

        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None

    def cancel_job(self, job_id: str, user_id: str) -> bool:
        """
        Cancel a running job (if possible).

        Args:
            job_id: Job identifier
            user_id: User requesting cancellation

        Returns:
            True if cancelled, False otherwise
        """
        try:
            job_status = self.get_job_status(job_id)
            if not job_status:
                return False

            # Verify user has permission to cancel
            doc = self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).get()
            if doc.exists:
                payload = doc.to_dict().get('payload', {})
                if payload.get('user_id') != user_id:
                    logger.warning(f"User {user_id} tried to cancel job {job_id} owned by {payload.get('user_id')}")
                    return False

            if job_status.status in ["completed", "failed", "cancelled"]:
                return True  # Already finished

            # Update status to cancelled
            self._update_job_status(job_id, "cancelled", "Job cancelled by user")

            logger.info(f"Job {job_id} cancelled by user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def list_project_jobs(self, project_id: str, limit: int = 10) -> List[JobStatus]:
        """
        List jobs for a specific project.

        Args:
            project_id: Project identifier
            limit: Maximum number of jobs to return

        Returns:
            List of JobStatus objects
        """
        def _materialize_jobs(documents):
            jobs: List[JobStatus] = []
            for doc in documents:
                data = doc.to_dict()
                jobs.append(
                    JobStatus(
                        job_id=doc.id,
                        job_type=data.get('jobType', ''),
                        status=data.get('status', 'unknown'),
                        progress=data.get('progress', 0.0),
                        message=data.get('message', ''),
                        error=data.get('error'),
                        created_at=data.get('createdAt'),
                        started_at=data.get('startedAt'),
                        completed_at=data.get('completedAt'),
                        retry_count=data.get('retryCount', 0)
                    )
                )
            return jobs

        try:
            query = (
                self.db.collection(JobConfig.JOBS_COLLECTION)
                .where('payload.project_id', '==', project_id)
                .order_by('createdAt', direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = list(query.stream())
            return _materialize_jobs(docs)

        except Exception as e:
            logger.warning(
                "Primary job listing query failed for project %s: %s. Falling back to client-side sort.",
                project_id,
                e,
            )

            try:
                fallback_docs = list(
                    self.db.collection(JobConfig.JOBS_COLLECTION)
                    .where('payload.project_id', '==', project_id)
                    .stream()
                )

                fallback_docs.sort(
                    key=lambda doc: doc.to_dict().get('createdAt') or datetime.min,
                    reverse=True,
                )

                return _materialize_jobs(fallback_docs[:limit])

            except Exception as inner:
                logger.error(
                    "Fallback job listing query failed for project %s: %s",
                    project_id,
                    inner,
                )
                return []

    def cleanup_old_jobs(self, days_old: int = 7) -> None:
        """
        Clean up old completed/failed jobs.

        Args:
            days_old: Age threshold in days
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            query = (
                self.db.collection(JobConfig.JOBS_COLLECTION)
                .where('status', 'in', ['completed', 'failed', 'cancelled'])
                .where('completedAt', '<', cutoff_date)
            )

            docs = query.stream()
            batch = self.db.batch()
            count = 0

            for doc in docs:
                batch.delete(doc.reference)
                count += 1

                # Firestore batch limit
                if count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    count = 0

            if count > 0:
                batch.commit()

            logger.info(f"Cleaned up {count} old jobs (older than {days_old} days)")

        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")

    # Private methods
    
    def _check_output_exists_in_gcs(self, output_path: str) -> bool:
        """Check if stitched video already exists in GCS."""
        if not self.gcs_client:
            return False
            
        try:
            # Parse GCS path (format: bucket-name/path/to/file.mp4)
            if output_path.startswith('gs://'):
                output_path = output_path[5:]
            
            parts = output_path.split('/', 1)
            if len(parts) != 2:
                logger.warning(f"Invalid GCS path format: {output_path}")
                return False
                
            bucket_name, blob_path = parts
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            exists = blob.exists()
            if exists:
                logger.info(f"✅ Output file already exists in GCS: {output_path}")
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check GCS output: {e}")
            return False
    
    def _get_cloud_run_execution_status(self, job_id: str) -> Optional[str]:
        """
        Check actual Cloud Run Job execution status.
        Returns: 'RUNNING', 'SUCCEEDED', 'FAILED', or None if not found.
        """
        if not self.jobs_client:
            return None
            
        try:
            # Get job record to find execution name
            doc = self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).get()
            if not doc.exists:
                return None
                
            data = doc.to_dict()
            cloud_run_execution_name = data.get('cloudRunExecutionName')
            
            if not cloud_run_execution_name:
                logger.warning(f"No Cloud Run execution name found for job {job_id}")
                return None
            
            # Query Cloud Run API for execution status
            execution = self.jobs_client.get_execution(name=cloud_run_execution_name)
            
            # Map execution condition to status
            if execution.completed_time:
                # Check if succeeded or failed
                if execution.succeeded_count > 0:
                    return 'SUCCEEDED'
                else:
                    return 'FAILED'
            else:
                return 'RUNNING'
                
        except Exception as e:
            logger.warning(f"Failed to get Cloud Run execution status for {job_id}: {e}")
            return None
    
    def _auto_reconcile_job_state(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Automatically reconcile job state based on actual conditions.
        Returns True if job was updated, False otherwise.
        """
        payload = job_data.get('payload', {})
        output_path = payload.get('output_path')
        current_status = job_data.get('status')
        created_at = job_data.get('createdAt')
        
        logger.info(f"🔍 Reconciling job {job_id} (current status: {current_status})")
        
        # Strategy 1: Check if output exists in GCS
        if output_path and self._check_output_exists_in_gcs(output_path):
            logger.info(f"✅ Found completed output in GCS for job {job_id}")
            self._update_job_status(job_id, "completed", "Output file verified in GCS")
            return True
        
        # Strategy 2: Check Cloud Run execution status
        cloud_run_status = self._get_cloud_run_execution_status(job_id)
        if cloud_run_status:
            if cloud_run_status == 'SUCCEEDED' and current_status != 'completed':
                logger.info(f"✅ Cloud Run execution succeeded for job {job_id}")
                self._update_job_status(job_id, "completed", "Cloud Run execution succeeded")
                return True
            elif cloud_run_status == 'FAILED' and current_status != 'failed':
                logger.info(f"❌ Cloud Run execution failed for job {job_id}")
                self._update_job_status(job_id, "failed", "Cloud Run execution failed")
                return True
        
        # Strategy 3: Check if job is stale (queued/running too long)
        if current_status in ['queued', 'running'] and created_at:
            if isinstance(created_at, datetime):
                job_age_minutes = (datetime.now(timezone.utc) - created_at).total_seconds() / 60
            else:
                job_age_minutes = 0
            
            if job_age_minutes > self.stale_job_timeout_minutes:
                logger.warning(f"⏰ Job {job_id} is stale (age: {job_age_minutes:.1f} minutes)")
                self._update_job_status(
                    job_id, 
                    "failed", 
                    f"Job timed out after {job_age_minutes:.0f} minutes with no progress"
                )
                return True
        
        logger.info(f"No reconciliation needed for job {job_id}")
        return False

    def _get_active_job(self, project_id: str, job_type: str) -> Optional[JobStatus]:
        """Get active job for a project and type."""
        try:
            query = (
                self.db.collection(JobConfig.JOBS_COLLECTION)
                .where('payload.project_id', '==', project_id)
                .where('jobType', '==', job_type)
                .where('status', 'in', ['queued', 'running', 'failed'])
                .order_by('createdAt', direction=firestore.Query.DESCENDING)
                .limit(1)
            )

            docs = list(query.stream())
        except Exception as e:
            logger.warning(
                "Primary active job lookup failed for project %s: %s. Falling back to in-memory filter.",
                project_id,
                e,
            )
            try:
                docs = list(
                    self.db.collection(JobConfig.JOBS_COLLECTION)
                    .where('payload.project_id', '==', project_id)
                    .where('jobType', '==', job_type)
                    .stream()
                )
            except Exception as inner:
                logger.error(
                    "Fallback active job lookup failed for project %s: %s",
                    project_id,
                    inner,
                )
                return None

            docs = [
                doc for doc in docs
                if doc.to_dict().get('status') in ['queued', 'running', 'failed']
            ]
            docs.sort(
                key=lambda doc: doc.to_dict().get('createdAt') or datetime.min,
                reverse=True,
            )

        if docs:
            job_doc = docs[0]
            data = job_doc.to_dict()
            job_id = job_doc.id
            
            # Auto-reconcile job state before returning
            logger.info(f"Found existing job {job_id} for project {project_id}, reconciling state...")
            was_updated = self._auto_reconcile_job_state(job_id, data)
            
            if was_updated:
                # Re-fetch updated data
                updated_doc = self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).get()
                if updated_doc.exists:
                    data = updated_doc.to_dict()
                    logger.info(f"Job {job_id} state updated to: {data.get('status')}")
            
            # Only return if still active after reconciliation
            current_status = data.get('status', '')
            if current_status in ['queued', 'running', 'failed']:
                return JobStatus(
                    job_id=job_id,
                    job_type=data.get('jobType', ''),
                    status=current_status,
                    retry_count=data.get('retryCount', 0)
                )
            else:
                logger.info(f"Job {job_id} no longer active after reconciliation (status: {current_status})")
                return None

        return None

    def _create_job_record(self, job_id: str, job_type: str, payload: Dict[str, Any]) -> JobStatus:
        """Create job record in Firestore."""
        try:
            job_data = {
                'jobType': job_type,
                'status': 'queued',
                'progress': 0.0,
                'message': 'Job queued for execution',
                'payload': payload,
                'createdAt': datetime.now(timezone.utc),
                'retryCount': 0,
                'checkpoints': []
            }

            self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).set(job_data)

            logger.info(f"Created job record for {job_id}")

            return JobStatus(
                job_id=job_id,
                job_type=job_type,
                status='queued',
                created_at=job_data['createdAt']
            )

        except Exception as e:
            logger.error(f"Failed to create job record for {job_id}: {e}")
            raise JobError(f"Failed to create job record: {e}")

    def _enqueue_job(self, job_id: str, job_type: str, payload: Dict[str, Any]) -> None:
        """Execute Cloud Run Job with payload."""
        try:
            # Get job configuration
            job_config = self.job_configs.get(job_type)
            if not job_config:
                raise JobError(f"Unknown job type: {job_type}")

            job_name = job_config['job_name']
            
            # Build the full job path
            job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{job_name}"
            
            logger.info(f"Executing Cloud Run Job: {job_path}")
            
            # Prepare environment variables with job data
            env_vars = [
                run_v2.EnvVar(name="JOB_ID", value=job_id),
                run_v2.EnvVar(name="JOB_TYPE", value=job_type),
                run_v2.EnvVar(name="JOB_PAYLOAD", value=json.dumps(payload))
            ]
            
            # Create execution request with overrides
            execution_request = run_v2.RunJobRequest(
                name=job_path,
                overrides=run_v2.RunJobRequest.Overrides(
                    container_overrides=[
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            env=env_vars
                        )
                    ]
                )
            )
            
            # Execute the job
            operation = self.jobs_client.run_job(request=execution_request)
            
            # Operation is a long-running operation, get the execution from metadata
            if hasattr(operation, 'metadata'):
                execution_name = operation.metadata.name if hasattr(operation.metadata, 'name') else str(operation)
            else:
                execution_name = str(operation)
            
            logger.info(f"Cloud Run Job execution started: {execution_name}")
            logger.info(f"Job {job_id} queued successfully in Cloud Run Jobs")
            
            # Store execution name in Firestore for status tracking
            try:
                self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).update({
                    'cloudRunExecutionName': execution_name,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })
                logger.info(f"Stored Cloud Run execution name for job {job_id}")
            except Exception as update_error:
                logger.warning(f"Failed to store execution name for {job_id}: {update_error}")

        except Exception as e:
            logger.error(f"Failed to execute job {job_id}: {e}", exc_info=True)
            # Update job status to failed
            self._update_job_status(job_id, "failed", f"Failed to execute: {e}")
            raise JobError(f"Failed to execute job: {e}")

    def _retry_job(self, job_id: str) -> JobExecution:
        """Retry a failed job."""
        try:
            doc = self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).get()
            if not doc.exists:
                raise JobError(f"Job {job_id} not found")

            data = doc.to_dict()
            job_type = data.get('jobType')
            payload = data.get('payload', {})
            retry_count = data.get('retryCount', 0)

            if retry_count >= JobConfig.MAX_RETRY_ATTEMPTS:
                raise JobError(f"Job {job_id} has exceeded maximum retry attempts")

            # Update retry count and status
            self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).update({
                'status': 'queued',
                'retryCount': retry_count + 1,
                'message': f'Retrying job (attempt {retry_count + 1})',
                'error': None,
                'updatedAt': datetime.now(timezone.utc)
            })

            # Update payload retry attempt
            payload['retry_attempt'] = retry_count + 1

            # Re-enqueue
            self._enqueue_job(job_id, job_type, payload)

            logger.info(f"Retrying job {job_id} (attempt {retry_count + 1})")

            return JobExecution(job_id, job_type, "queued")

        except Exception as e:
            logger.error(f"Failed to retry job {job_id}: {e}")
            raise JobError(f"Failed to retry job: {e}")

    def _update_job_status(
        self,
        job_id: str,
        status: str,
        message: str,
        progress: Optional[float] = None
    ) -> None:
        """Update job status in Firestore."""
        try:
            update_data = {
                'status': status,
                'message': message,
                'updatedAt': datetime.now(timezone.utc)
            }

            if progress is not None:
                update_data['progress'] = progress

            if status in ["completed", "failed", "cancelled"]:
                update_data['completedAt'] = datetime.now(timezone.utc)

            self.db.collection(JobConfig.JOBS_COLLECTION).document(job_id).update(update_data)

        except Exception as e:
            logger.warning(f"Failed to update job status for {job_id}: {e}")


# Global instance - lazy initialization
job_orchestrator = None

def get_job_orchestrator():
    """Get or create the global job orchestrator instance."""
    global job_orchestrator
    if job_orchestrator is None:
        job_orchestrator = JobOrchestrator()
    return job_orchestrator