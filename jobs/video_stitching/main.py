"""
Video Stitching Job - Cloud Run Job entry point.

Handles video stitching operations in an isolated Cloud Run Job environment.
"""
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

# Add parent directories to path for imports
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/jobs')

from jobs.base.job_runner import BaseJobRunner, JobExecutor
from jobs.base.gcs_client import JobGCSClient, BatchGCSOperations
from jobs.shared.config import JobConfig
from jobs.shared.schemas import StitchingJobPayload, JobError
from jobs.video_stitching.stitcher import VideoStitcher

logger = logging.getLogger(__name__)


class VideoStitchingJob(BaseJobRunner):
    """
    Cloud Run Job for video stitching operations.

    Processes multiple video clips and combines them into a single reel.
    """

    def __init__(self):
        super().__init__("video_stitching")
        self.gcs_client: JobGCSClient = None
        self.stitcher: VideoStitcher = None
        self.local_input_dir: str = None
        self.local_output_file: str = None
        self.downloaded_files: list = []

    async def _parse_payload(self, payload_dict: Dict[str, Any]) -> StitchingJobPayload:
        """Parse and validate stitching job payload."""
        try:
            if isinstance(payload_dict, str):
                payload_dict = json.loads(payload_dict)

            return StitchingJobPayload(
                job_id=payload_dict['job_id'],
                project_id=payload_dict['project_id'],
                user_id=payload_dict['user_id'],
                clip_paths=payload_dict['clip_paths'],
                output_path=payload_dict['output_path'],
                orientation=payload_dict.get('orientation', 'portrait'),
                compression=payload_dict.get('compression', 'optimized'),
                audio_enabled=payload_dict.get('audio_enabled', True),
                retry_attempt=payload_dict.get('retry_attempt', 0)
            )

        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise JobError(f"Invalid payload format: {e}")

    async def initialize(self) -> None:
        """Initialize job-specific resources."""
        logger.info("Initializing video stitching job...")

        # Initialize GCS client
        self.gcs_client = JobGCSClient()

        # Initialize video stitcher with job_id for progress publishing
        self.stitcher = VideoStitcher(self.temp_dir, job_id=self.job_id)
        self.stitcher.set_progress_callback(self._on_stitching_progress)

        # Create local directories
        self.local_input_dir = os.path.join(self.temp_dir, "input")
        os.makedirs(self.local_input_dir, exist_ok=True)

        logger.info(f"Initialized with temp dir: {self.temp_dir}")

    async def process(self, payload: StitchingJobPayload) -> Dict[str, Any]:
        """Main processing logic for video stitching."""
        logger.info(f"Processing stitching job for project {payload.project_id}")

        try:
            # Step 1: Validate input files in GCS
            await self.save_checkpoint("validation_started", {
                "clip_paths": payload.clip_paths,
                "output_path": payload.output_path
            })

            batch_ops = BatchGCSOperations(self.gcs_client)
            valid_paths, missing_paths = await batch_ops.validate_input_files(payload.clip_paths)

            if missing_paths:
                logger.warning(f"Missing input files: {missing_paths}")

            if len(valid_paths) < 2:
                raise JobError(f"Insufficient valid clips: {len(valid_paths)} (need at least 2)")

            await self.update_progress(15, f"Validated {len(valid_paths)} input files")

            # Step 2: Download input files
            await self.save_checkpoint("download_started", {
                "valid_paths": valid_paths,
                "local_input_dir": self.local_input_dir
            })

            download_results = await self.gcs_client.download_multiple_files(
                valid_paths,
                self.local_input_dir,
                self._on_download_progress
            )

            # Track successfully downloaded files
            self.downloaded_files = [
                local_path for gcs_path, local_path, success in download_results if success
            ]

            if len(self.downloaded_files) < 2:
                raise JobError(f"Failed to download sufficient clips: {len(self.downloaded_files)}")

            await self.update_progress(35, f"Downloaded {len(self.downloaded_files)} clips")

            await self.save_checkpoint("download_complete", {
                "downloaded_files": [str(f) for f in self.downloaded_files],
                "file_count": len(self.downloaded_files)
            })

            # Step 3: Stitch videos
            await self.save_checkpoint("stitching_started", {
                "input_files": [str(f) for f in self.downloaded_files],
                "orientation": payload.orientation,
                "compression": payload.compression
            })

            self.local_output_file = os.path.join(self.temp_dir, "stitched_output.mp4")

            stitching_result = await self.stitcher.stitch_videos(
                input_files=self.downloaded_files,
                output_file=self.local_output_file,
                orientation=payload.orientation,
                compression=payload.compression,
                audio_enabled=payload.audio_enabled
            )

            await self.save_checkpoint("stitching_complete", {
                "output_file": str(self.local_output_file),
                "stitching_result": stitching_result
            })

            # Step 4: Delete old stitched video if it exists (for re-stitch)
            await self._delete_old_stitched_video(payload.output_path)

            # Step 5: Upload result
            await self.save_checkpoint("upload_started", {
                "local_output": str(self.local_output_file),
                "gcs_output": payload.output_path
            })

            upload_success = await self.gcs_client.upload_file(
                self.local_output_file,
                payload.output_path,
                content_type="video/mp4",
                progress_callback=self._on_upload_progress
            )

            if not upload_success:
                raise JobError("Failed to upload stitched video to GCS")

            await self.save_checkpoint("upload_complete", {
                "gcs_output_path": payload.output_path
            })

            # Step 5: Update project in Firestore
            await self._update_project_status(payload.project_id, payload.output_path)

            # Prepare final result
            result = {
                'project_id': payload.project_id,
                'output_path': payload.output_path,
                'input_count': len(self.downloaded_files),
                'stitching_result': stitching_result,
                'processing_stats': {
                    'valid_clips': len(valid_paths),
                    'downloaded_clips': len(self.downloaded_files),
                    'missing_clips': len(missing_paths)
                }
            }

            logger.info(f"Successfully completed stitching for project {payload.project_id}")
            return result

        except Exception as e:
            logger.error(f"Stitching job failed: {e}", exc_info=True)
            await self._handle_job_failure(payload.project_id, str(e))
            raise

    async def cleanup(self) -> None:
        """Clean up job-specific resources."""
        logger.info("Cleaning up video stitching job...")

        # Clean up downloaded files
        for file_path in self.downloaded_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")

        # Clean up output file
        if self.local_output_file and os.path.exists(self.local_output_file):
            try:
                os.remove(self.local_output_file)
            except Exception as e:
                logger.warning(f"Failed to remove output file: {e}")

    async def get_checkpoint_data(self) -> Dict[str, Any]:
        """Get current state for checkpointing."""
        return {
            'downloaded_files': self.downloaded_files,
            'local_output_file': self.local_output_file,
            'temp_dir': self.temp_dir
        }

    async def _restore_from_checkpoint(self, checkpoint) -> None:
        """Restore job state from checkpoint."""
        logger.info(f"Restoring from checkpoint: {checkpoint.checkpoint_name}")

        checkpoint_data = checkpoint.data

        # Restore downloaded files list
        self.downloaded_files = checkpoint_data.get('downloaded_files', [])

        # Restore output file path
        self.local_output_file = checkpoint_data.get('local_output_file')

        # Verify files still exist
        existing_files = [f for f in self.downloaded_files if os.path.exists(f)]
        if len(existing_files) != len(self.downloaded_files):
            logger.warning(f"Some checkpoint files missing: {len(existing_files)}/{len(self.downloaded_files)}")
            self.downloaded_files = existing_files

        logger.info(f"Restored state: {len(self.downloaded_files)} files, output: {self.local_output_file}")

    # Progress callbacks

    def _on_download_progress(self, completed: int, total: int, current_file: str, success: bool) -> None:
        """Handle download progress updates."""
        progress = 15 + (completed / total) * 20  # 15-35% range
        status = "✓" if success else "✗"
        message = f"Downloading clips... {completed}/{total} {status}"
        asyncio.create_task(self.update_progress(progress, message))

    def _on_stitching_progress(self, progress: float, message: str) -> None:
        """Handle stitching progress updates."""
        # Stitching uses 35-85% range
        asyncio.create_task(self.update_progress(progress, message))

    def _on_upload_progress(self, gcs_path: str, size_mb: float) -> None:
        """Handle upload progress updates."""
        asyncio.create_task(self.update_progress(95, f"Uploaded {size_mb:.1f} MB to GCS"))

    # Helper methods

    async def _delete_old_stitched_video(self, output_path: str) -> None:
        """
        Delete old stitched video if it exists (for re-stitch scenarios).
        This ensures clean slate before uploading new version.
        """
        try:
            blob_name = self.gcs_client._clean_gcs_path(output_path)
            blob = self.gcs_client.bucket.blob(blob_name)
            
            if await self.gcs_client._async_operation(blob.exists):
                logger.info(f"Deleting old stitched video: {output_path}")
                await self.gcs_client._async_operation(blob.delete)
                logger.info(f"✅ Deleted old stitched video: {output_path}")
            else:
                logger.info(f"No existing stitched video to delete at {output_path}")
        except Exception as e:
            # Non-fatal error - log and continue
            logger.warning(f"Failed to delete old stitched video (continuing anyway): {e}")

    async def _update_project_status(self, project_id: str, output_path: str) -> None:
        """Update project status in Firestore."""
        try:
            from firebase_admin import firestore

            db = firestore.client()

            # Store the full GCS path (without gs://bucket/ prefix) so it can be used with the stream_clip route
            # The output_path already comes without the gs://bucket/ prefix from the payload
            update_data = {
                'status': 'ready',
                'stitchedFilename': output_path,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }

            db.collection('reel_maker_projects').document(project_id).update(update_data)

            logger.info(f"Updated project {project_id} with stitched file: {output_path}")

        except Exception as e:
            logger.error(f"Failed to update project status: {e}")
            # Don't fail the job for this

    async def _handle_job_failure(self, project_id: str, error_message: str) -> None:
        """Handle job failure by updating project status."""
        try:
            from firebase_admin import firestore

            db = firestore.client()

            update_data = {
                'status': 'error',
                'errorInfo': {
                    'message': f"Stitching failed: {error_message}",
                    'timestamp': firestore.SERVER_TIMESTAMP
                },
                'updatedAt': firestore.SERVER_TIMESTAMP
            }

            db.collection('reel_maker_projects').document(project_id).update(update_data)

            logger.info(f"Updated project {project_id} with error status")

        except Exception as e:
            logger.error(f"Failed to update project error status: {e}")


async def main():
    """Main entry point for Cloud Run Job."""
    # Job payload should be passed via environment variable or stdin
    payload_json = os.getenv('JOB_PAYLOAD')

    if not payload_json:
        # Try reading from stdin (Cloud Tasks HTTP request body)
        try:
            payload_json = sys.stdin.read()
        except Exception:
            payload_json = None

    if not payload_json:
        logger.error("No job payload provided")
        sys.exit(1)

    try:
        payload_dict = json.loads(payload_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        sys.exit(1)

    # Execute the job
    job_runner = VideoStitchingJob()
    result = await JobExecutor.execute_job(job_runner, payload_dict)

    if result['success']:
        logger.info("Job completed successfully")
        print(json.dumps(result['result']))
        sys.exit(0)
    else:
        logger.error(f"Job failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    # Set up logging for Cloud Run
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run the job
    asyncio.run(main())