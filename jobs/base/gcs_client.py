"""
Google Cloud Storage client for job operations.
"""
import os
import logging
from typing import List, Optional, Tuple
from pathlib import Path

from google.cloud import storage
from google.api_core import exceptions as gcs_exceptions

from jobs.shared.config import JobConfig
from jobs.shared.utils import get_file_size_mb

logger = logging.getLogger(__name__)


class JobGCSClient:
    """Google Cloud Storage client optimized for job operations."""

    def __init__(self):
        self.client = storage.Client()
        self.bucket_name = JobConfig.get_bucket_name()
        self.bucket = self.client.bucket(self.bucket_name)

    async def download_file(
        self,
        gcs_path: str,
        local_path: str,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        Download a file from GCS to local storage.

        Args:
            gcs_path: GCS path (e.g., "gs://bucket/path/file.mp4" or "path/file.mp4")
            local_path: Local file path to save to
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful, False otherwise
        """
        try:
            # Clean GCS path (remove gs://bucket/ prefix if present)
            blob_name = self._clean_gcs_path(gcs_path)

            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            blob = self.bucket.blob(blob_name)

            # Check if file exists
            if not await self._async_operation(blob.exists):
                logger.error(f"File does not exist in GCS: {gcs_path}")
                return False

            # Get file size for progress tracking
            await self._async_operation(blob.reload)
            file_size_mb = blob.size / (1024 * 1024) if blob.size else 0

            logger.info(f"Downloading {gcs_path} ({file_size_mb:.1f} MB) to {local_path}")

            # Download file
            await self._async_operation(blob.download_to_filename, local_path)

            # Verify download
            if os.path.exists(local_path):
                downloaded_size_mb = get_file_size_mb(local_path)
                logger.info(f"Successfully downloaded {gcs_path} ({downloaded_size_mb:.1f} MB)")

                if progress_callback:
                    progress_callback(local_path, downloaded_size_mb)

                return True
            else:
                logger.error(f"Download failed: {local_path} not found after download")
                return False

        except gcs_exceptions.NotFound:
            logger.error(f"File not found in GCS: {gcs_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to download {gcs_path}: {e}")
            return False

    async def upload_file(
        self,
        local_path: str,
        gcs_path: str,
        content_type: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        Upload a file from local storage to GCS.

        Args:
            local_path: Local file path
            gcs_path: GCS destination path
            content_type: MIME type (auto-detected if None)
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(local_path):
                logger.error(f"Local file does not exist: {local_path}")
                return False

            # Clean GCS path
            blob_name = self._clean_gcs_path(gcs_path)

            # Get file info
            file_size_mb = get_file_size_mb(local_path)

            logger.info(f"Uploading {local_path} ({file_size_mb:.1f} MB) to {gcs_path}")

            blob = self.bucket.blob(blob_name)

            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            elif local_path.endswith('.mp4'):
                blob.content_type = 'video/mp4'

            # Upload file
            await self._async_operation(blob.upload_from_filename, local_path)

            logger.info(f"Successfully uploaded {local_path} to {gcs_path}")

            if progress_callback:
                progress_callback(gcs_path, file_size_mb)

            return True

        except Exception as e:
            logger.error(f"Failed to upload {local_path} to {gcs_path}: {e}")
            return False

    async def download_multiple_files(
        self,
        gcs_paths: List[str],
        local_dir: str,
        progress_callback: Optional[callable] = None
    ) -> List[Tuple[str, str, bool]]:
        """
        Download multiple files from GCS.

        Args:
            gcs_paths: List of GCS paths to download
            local_dir: Local directory to save files
            progress_callback: Optional callback for progress updates

        Returns:
            List of tuples (gcs_path, local_path, success)
        """
        os.makedirs(local_dir, exist_ok=True)

        results = []
        total_files = len(gcs_paths)

        for i, gcs_path in enumerate(gcs_paths):
            # Generate unique local filename to avoid overwriting
            # Use index to ensure each file has a unique name
            filename = os.path.basename(self._clean_gcs_path(gcs_path))
            name_parts = os.path.splitext(filename)
            unique_filename = f"{name_parts[0]}_{i}{name_parts[1]}"
            local_path = os.path.join(local_dir, unique_filename)

            # Download file
            success = await self.download_file(gcs_path, local_path)

            results.append((gcs_path, local_path, success))

            if progress_callback:
                progress_callback(i + 1, total_files, gcs_path, success)

        return results

    async def file_exists(self, gcs_path: str) -> bool:
        """Check if a file exists in GCS."""
        try:
            blob_name = self._clean_gcs_path(gcs_path)
            blob = self.bucket.blob(blob_name)
            return await self._async_operation(blob.exists)
        except Exception as e:
            logger.error(f"Error checking if file exists {gcs_path}: {e}")
            return False

    async def get_file_info(self, gcs_path: str) -> Optional[dict]:
        """Get file information from GCS."""
        try:
            blob_name = self._clean_gcs_path(gcs_path)
            blob = self.bucket.blob(blob_name)

            if not await self._async_operation(blob.exists):
                return None

            await self._async_operation(blob.reload)

            return {
                'name': blob.name,
                'size_bytes': blob.size,
                'size_mb': (blob.size / (1024 * 1024)) if blob.size else 0,
                'content_type': blob.content_type,
                'created': blob.time_created,
                'updated': blob.updated
            }

        except Exception as e:
            logger.error(f"Error getting file info for {gcs_path}: {e}")
            return None

    async def delete_file(self, gcs_path: str) -> bool:
        """Delete a file from GCS."""
        try:
            blob_name = self._clean_gcs_path(gcs_path)
            blob = self.bucket.blob(blob_name)

            await self._async_operation(blob.delete)
            logger.info(f"Deleted file from GCS: {gcs_path}")
            return True

        except gcs_exceptions.NotFound:
            logger.warning(f"File not found for deletion: {gcs_path}")
            return True  # Consider it successful if file doesn't exist
        except Exception as e:
            logger.error(f"Failed to delete file {gcs_path}: {e}")
            return False

    def _clean_gcs_path(self, gcs_path: str) -> str:
        """
        Clean GCS path by removing gs://bucket/ prefix if present.

        Args:
            gcs_path: GCS path that might include gs://bucket/ prefix

        Returns:
            Clean blob name for the bucket
        """
        if gcs_path.startswith(f"gs://{self.bucket_name}/"):
            return gcs_path[len(f"gs://{self.bucket_name}/"):]
        elif gcs_path.startswith("gs://"):
            # Handle case where path has different bucket
            parts = gcs_path[5:].split("/", 1)
            if len(parts) > 1:
                return parts[1]
            return parts[0]
        else:
            # Already a clean path
            return gcs_path

    async def _async_operation(self, operation, *args, **kwargs):
        """Execute GCS operation asynchronously."""
        import asyncio
        import concurrent.futures

        loop = asyncio.get_event_loop()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(operation, *args, **kwargs)
            return await loop.run_in_executor(None, future.result)


class BatchGCSOperations:
    """Optimized batch operations for multiple files."""

    def __init__(self, gcs_client: JobGCSClient):
        self.gcs_client = gcs_client

    async def validate_input_files(self, gcs_paths: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate that all input files exist in GCS.

        Args:
            gcs_paths: List of GCS paths to validate

        Returns:
            Tuple of (valid_paths, missing_paths)
        """
        valid_paths = []
        missing_paths = []

        for gcs_path in gcs_paths:
            if await self.gcs_client.file_exists(gcs_path):
                valid_paths.append(gcs_path)
            else:
                missing_paths.append(gcs_path)

        logger.info(f"Validated input files: {len(valid_paths)} valid, {len(missing_paths)} missing")

        if missing_paths:
            logger.warning(f"Missing files: {missing_paths}")

        return valid_paths, missing_paths

    async def get_total_input_size(self, gcs_paths: List[str]) -> float:
        """
        Get total size of input files in MB.

        Args:
            gcs_paths: List of GCS paths

        Returns:
            Total size in MB
        """
        total_size_mb = 0.0

        for gcs_path in gcs_paths:
            file_info = await self.gcs_client.get_file_info(gcs_path)
            if file_info:
                total_size_mb += file_info['size_mb']

        return total_size_mb