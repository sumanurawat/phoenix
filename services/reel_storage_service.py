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
from datetime import timedelta, datetime, timezone
import binascii
from urllib.parse import quote

from google.cloud import storage
from google.api_core import exceptions as gcs_exceptions
from google.oauth2 import service_account
from google.auth.transport.requests import Request as AuthRequest
from google.auth import compute_engine
import google.auth

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
        
        Uses IAM signBlob API for Cloud Run environments where direct signing
        isn't available. Falls back gracefully through multiple strategies.
        
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
        
        # Check if blob exists first
        if not blob.exists():
            logger.error(f"Blob does not exist: {blob_path}")
            return None
        
        try:
            # Try to generate signed URL with current credentials
            return blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method=method,
                response_type="video/mp4"
            )
        except (AttributeError, NotImplementedError, TypeError) as e:
            # Current credentials don't support signing
            logger.warning(f"Default credentials don't support signing, trying alternative methods: {e}")

            # Try IAM signBlob API (works for Cloud Run service accounts)
            try:
                signed_url = self._generate_signed_url_with_iam(blob_path, expiration, method)
                if signed_url:
                    logger.info(f"Successfully generated signed URL using IAM API for {blob_path}")
                    return signed_url
            except Exception as iam_error:
                logger.warning(f"IAM signBlob failed: {iam_error}")

            # Try to load service account from file (works for local dev with proper credentials)
            service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'firebase-credentials.json')
            if os.path.exists(service_account_path):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        service_account_path
                    )

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
                    logger.warning(f"Failed to sign with service account file: {sa_error}")

            logger.error(f"All signing methods failed for {blob_path}")
            return None
        except Exception:
            logger.exception(f"Unexpected error generating signed URL for {blob_path}")
            return None

    def _generate_signed_url_with_iam(
        self,
        blob_path: str,
        expiration: timedelta,
        method: str = "GET"
    ) -> Optional[str]:
        """Generate signed URL using IAM signBlob API.
        
        This works for Cloud Run service accounts that don't have direct
        private key access but can use the IAM API to sign blobs.
        """
        from google.auth import iam

        # Get current credentials and determine service account email
        credentials, project_id = google.auth.default()
        if hasattr(credentials, "with_scopes_if_required"):
            credentials = credentials.with_scopes_if_required(["https://www.googleapis.com/auth/cloud-platform"])

        # Get service account email
        if hasattr(credentials, 'service_account_email'):
            service_account_email = credentials.service_account_email
        elif hasattr(credentials, 'signer_email'):
            service_account_email = credentials.signer_email
        elif isinstance(credentials, compute_engine.Credentials):
            # For Compute Engine, need to fetch service account email
            service_account_email = self._get_compute_engine_service_account()
        else:
            logger.error("Cannot determine service account email for IAM signing")
            return None
        
        if not service_account_email:
            logger.error("Service account email is None, cannot sign URL")
            return None
        
        logger.info(f"Using service account {service_account_email} for IAM signing")
        
        # Create IAM signer
        auth_request = AuthRequest()
        credentials.refresh(auth_request)
        signer = iam.Signer(
            request=auth_request,
            credentials=credentials,
            service_account_email=service_account_email
        )

        class _IAMCredentials:
            def __init__(self, signer, email):
                self.signer = signer
                self.signer_email = email

            def sign_bytes(self, payload):
                return self.signer.sign(payload)
        
        # Generate signed URL using the signer
        expiration_time = datetime.now(timezone.utc) + expiration
        
        try:
            # Use blob's generate_signed_url with the IAM signer
            bucket = self._ensure_bucket()
            blob = bucket.blob(blob_path)

            return blob.generate_signed_url(
                version="v4",
                expiration=expiration_time,
                method=method,
                service_account_email=service_account_email,
                credentials=_IAMCredentials(signer, service_account_email),
                access_token=credentials.token,
                response_type="video/mp4"
            )
        except Exception as e:
            logger.error(f"Failed to generate signed URL with IAM signer: {e}")
            return None
    
    def _get_compute_engine_service_account(self) -> Optional[str]:
        """Get the service account email for Compute Engine credentials."""
        try:
            import requests
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
            headers = {"Metadata-Flavor": "Google"}
            response = requests.get(metadata_url, headers=headers, timeout=2)
            if response.status_code == 200:
                email = response.text
                logger.info(f"Retrieved Compute Engine service account: {email}")
                return email
        except Exception as e:
            logger.error(f"Failed to get Compute Engine service account: {e}")
        return None


# Singleton instance (imported by services/routes)
reel_storage_service = ReelStorageService()
