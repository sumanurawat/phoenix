"""Reel Maker storage helpers for working with Google Cloud Storage.

This module centralizes all path construction and GCS operations for the
Reel Maker feature. It keeps business logic in higher-level services focused on
workflow orchestration while encapsulating storage-specific concerns here.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Iterable, Optional
from datetime import timedelta

from google.cloud import storage
from google.api_core import exceptions as gcs_exceptions
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

DEFAULT_BUCKET_ENV_KEYS = (
    "REEL_MAKER_GCS_BUCKET",
    "VIDEO_GENERATION_BUCKET",
    "VIDEO_STORAGE_BUCKET",
)


class ReelStorageService:
    """Helper for constructing Reel Maker storage paths and interacting with GCS."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        client: Optional[storage.Client] = None,
    ):
        self._bucket_name = bucket_name or self._resolve_bucket_name()
        if not self._bucket_name:
            logger.warning(
                "Reel Maker storage bucket is not configured. Set REEL_MAKER_GCS_BUCKET or"
                " VIDEO_STORAGE_BUCKET to enable media persistence."
            )
        self._client: Optional[storage.Client] = client
        self._bucket: Optional[storage.Bucket] = None

    # ------------------------------------------------------------------
    # Bucket and client helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_bucket_name() -> Optional[str]:
        for key in DEFAULT_BUCKET_ENV_KEYS:
            value = os.getenv(key)
            if value:
                return value
        return None

    @property
    def bucket_name(self) -> str:
        return self._require_bucket_name()

    def _require_bucket_name(self) -> str:
        if not self._bucket_name:
            raise RuntimeError(
                "Reel Maker storage bucket is not configured. Set REEL_MAKER_GCS_BUCKET or"
                " VIDEO_STORAGE_BUCKET before triggering media operations."
            )
        return self._bucket_name

    def _ensure_client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client()
        return self._client

    def _ensure_bucket(self) -> storage.Bucket:
        bucket_name = self._require_bucket_name()
        if self._bucket is None:
            client = self._ensure_client()
            self._bucket = client.bucket(bucket_name)
        return self._bucket

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _sanitize_segment(segment: str) -> str:
        return segment.replace("..", "").strip("/")

    @staticmethod
    def _root_prefix(user_id: str, project_id: str) -> str:
        return f"reel-maker/{ReelStorageService._sanitize_segment(user_id)}/{ReelStorageService._sanitize_segment(project_id)}"

    def raw_prefix(self, user_id: str, project_id: str) -> str:
        return f"{self._root_prefix(user_id, project_id)}/raw"

    def stitched_prefix(self, user_id: str, project_id: str) -> str:
        return f"{self._root_prefix(user_id, project_id)}/stitched"

    def job_raw_prefix(self, user_id: str, project_id: str, job_id: str) -> str:
        job_segment = self._sanitize_segment(job_id)
        return f"{self.raw_prefix(user_id, project_id)}/{job_segment}"

    def clip_prefix_for_prompt(self, user_id: str, project_id: str, job_id: str, prompt_index: int) -> str:
        return f"{self.job_raw_prefix(user_id, project_id, job_id)}/prompt-{prompt_index:02d}"

    def clip_destination_path(self, user_id: str, project_id: str, job_id: str, prompt_index: int, filename: str) -> str:
        filename = self._sanitize_segment(filename)
        return f"{self.clip_prefix_for_prompt(user_id, project_id, job_id, prompt_index)}/{filename}"

    def stitched_destination_path(self, user_id: str, project_id: str, filename: str) -> str:
        filename = self._sanitize_segment(filename)
        return f"{self.stitched_prefix(user_id, project_id)}/{filename}"

    def to_gcs_uri(self, relative_path: str) -> str:
        bucket_name = self._require_bucket_name()
        relative_path = relative_path.lstrip("/")
        return f"gs://{bucket_name}/{relative_path}"

    def extract_relative_path(self, gcs_uri: str) -> str:
        if gcs_uri.startswith("gs://"):
            without_scheme = gcs_uri[5:]
            parts = without_scheme.split("/", 1)
            if len(parts) == 1:
                return ""
            bucket, remainder = parts
            configured = self._bucket_name
            if configured and bucket != configured:
                logger.warning("GCS URI bucket %s does not match configured bucket %s", bucket, configured)
            return remainder
        return gcs_uri

    def extract_filename(self, gcs_uri: str) -> str:
        rel = self.extract_relative_path(gcs_uri)
        return Path(rel).name

    # ------------------------------------------------------------------
    # GCS operations
    # ------------------------------------------------------------------
    def download_to_path(self, gcs_uri: str, destination_path: str) -> None:
        blob_path = self.extract_relative_path(gcs_uri)
        if not blob_path:
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")
        bucket = self._ensure_bucket()
        blob = bucket.blob(blob_path)
        logger.debug("Downloading %s to %s", blob_path, destination_path)
        blob.download_to_filename(destination_path)

    def upload_file(self, source_path: str, destination_path: str, content_type: str = "video/mp4") -> str:
        destination_path = destination_path.lstrip("/")
        bucket = self._ensure_bucket()
        blob = bucket.blob(destination_path)
        bucket_name = self._require_bucket_name()
        logger.debug("Uploading %s to gs://%s/%s", source_path, bucket_name, destination_path)
        blob.upload_from_filename(source_path, content_type=content_type)
        return self.to_gcs_uri(destination_path)

    def upload_bytes(self, data: bytes, destination_path: str, content_type: str = "video/mp4") -> str:
        destination_path = destination_path.lstrip("/")
        bucket = self._ensure_bucket()
        blob = bucket.blob(destination_path)
        bucket_name = self._require_bucket_name()
        logger.debug("Uploading %d bytes to gs://%s/%s", len(data), bucket_name, destination_path)
        blob.upload_from_string(data, content_type=content_type)
        return self.to_gcs_uri(destination_path)

    def delete_objects(self, relative_paths: Iterable[str]) -> None:
        bucket = self._ensure_bucket()
        for path in relative_paths:
            clean = path.lstrip("/")
            try:
                bucket.delete_blob(clean)
            except gcs_exceptions.NotFound:
                logger.debug("Blob %s already deleted", clean)
            except Exception:
                logger.exception("Failed deleting blob %s", clean)

    def generate_signed_url(
        self, 
        blob_path: str, 
        expiration: timedelta = timedelta(hours=2),
        method: str = "GET"
    ) -> Optional[str]:
        """Generate a signed URL for accessing a blob.
        
        This method attempts to use service account credentials for signing.
        Falls back to making the blob public if signing fails (local dev).
        
        Args:
            blob_path: GCS blob path (without gs:// prefix)
            expiration: How long the URL should be valid
            method: HTTP method (GET, PUT, etc.)
            
        Returns:
            Signed URL string, or None if generation fails
        """
        blob_path = blob_path.lstrip("/")
        bucket = self._ensure_bucket()
        blob = bucket.blob(blob_path)
        
        try:
            # Try to generate signed URL with current credentials
            return blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method=method,
                response_type="video/mp4"
            )
        except AttributeError as e:
            # Current credentials don't support signing (user OAuth token)
            # Try to use service account credentials explicitly
            logger.warning(f"Default credentials don't support signing, trying service account: {e}")
            
            # Try to load service account from firebase-credentials.json
            service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'firebase-credentials.json')
            if os.path.exists(service_account_path):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        service_account_path
                    )
                    
                    # Create a new storage client with service account credentials
                    signing_client = storage.Client(credentials=credentials)
                    signing_bucket = signing_client.bucket(self.bucket_name)
                    signing_blob = signing_bucket.blob(blob_path)
                    
                    return signing_blob.generate_signed_url(
                        version="v4",
                        expiration=expiration,
                        method=method,
                        response_type="video/mp4"
                    )
                except Exception as sa_error:
                    logger.error(f"Failed to sign with service account: {sa_error}")
            
            # Last resort: make blob public and return public URL
            logger.warning(f"Cannot sign URL for {blob_path}, attempting to make public")
            try:
                blob.make_public()
                return blob.public_url
            except Exception as public_error:
                logger.error(f"Failed to make blob public: {public_error}")
                return None
        except Exception as e:
            logger.exception(f"Unexpected error generating signed URL for {blob_path}")
            return None


# Singleton instance (imported by services/routes)
reel_storage_service = ReelStorageService()
