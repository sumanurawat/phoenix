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
        isn't available. Falls back to public URL if blob has public access.
        
        Args:
            blob_path: GCS blob path (without gs:// prefix)
            expiration: How long the URL should be valid
            method: HTTP method (GET, PUT, etc.)
            
        Returns:
            URL string (signed or public), or None if generation fails
        """
        blob_path = blob_path.lstrip("/")
        bucket = self._ensure_bucket()
        blob = bucket.blob(blob_path)
        
        # Check if blob exists first
        if not blob.exists():
            logger.error(f"Blob does not exist: {blob_path}")
            return None
        
        logger.debug(f"Generating signed URL for blob: {blob_path}, method: {method}, expiration: {expiration}")
        
        try:
            # Try to generate signed URL with current credentials
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method=method,
                response_type="video/mp4"
            )
            logger.info(f"Successfully generated signed URL with default credentials for {blob_path}")
            return signed_url
        except (AttributeError, NotImplementedError, TypeError) as e:
            # Current credentials don't support signing
            logger.info(f"Default credentials don't support signing ({type(e).__name__}: {e}), trying IAM API fallback")

            # Try IAM signBlob API (works for Cloud Run service accounts)
            try:
                logger.info(f"Attempting IAM signBlob API for {blob_path}")
                signed_url = self._generate_signed_url_with_iam(blob_path, expiration, method)
                if signed_url:
                    logger.info(f"Successfully generated signed URL using IAM API for {blob_path}")
                    return signed_url
                else:
                    logger.warning(f"IAM signBlob returned None for {blob_path}")
            except Exception as iam_error:
                logger.warning(f"IAM signBlob failed for {blob_path}: {iam_error}", exc_info=True)

            # Try to load service account from file (works for local dev with proper credentials)
            # Try firebase-credentials.json first (most common in local dev)
            possible_paths = [
                'firebase-credentials.json',
                os.getenv('GOOGLE_APPLICATION_CREDENTIALS', ''),
                os.path.expanduser('~/.config/gcloud/application_default_credentials.json')
            ]
            
            for service_account_path in possible_paths:
                if not service_account_path or not os.path.exists(service_account_path):
                    continue
                    
                logger.info(f"Attempting to sign with service account file: {service_account_path}")
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        service_account_path
                    )

                    signing_client = storage.Client(credentials=credentials)
                    signing_bucket = signing_client.bucket(self.bucket_name)
                    signing_blob = signing_bucket.blob(blob_path)

                    signed_url = signing_blob.generate_signed_url(
                        version="v4",
                        expiration=expiration,
                        method=method,
                        response_type="video/mp4"
                    )
                    logger.info(f"Successfully generated signed URL with service account file for {blob_path}")
                    return signed_url
                except Exception as sa_error:
                    logger.debug(f"Failed to sign with {service_account_path}: {sa_error}")
                    continue  # Try next path
            else:
                logger.debug(f"Service account file not found at {service_account_path}")

            # Final fallback: try public URL if blob has public access
            logger.info(f"All signing methods failed for {blob_path}, attempting public URL fallback")
            try:
                public_url = self._get_public_url_if_accessible(blob_path)
                if public_url:
                    logger.info(f"Successfully generated public URL for {blob_path}")
                    return public_url
            except Exception as public_error:
                logger.warning(f"Public URL fallback failed: {public_error}")

            logger.error(f"All URL generation methods failed for {blob_path}")
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

        logger.info(f"[IAM Signing] Starting IAM-based URL signing for blob: {blob_path}")

        # Get current credentials and determine service account email
        credentials, project_id = google.auth.default()
        logger.debug(f"[IAM Signing] Default credentials type: {type(credentials).__name__}, project: {project_id}")
        
        if hasattr(credentials, "with_scopes_if_required"):
            credentials = credentials.with_scopes_if_required(["https://www.googleapis.com/auth/cloud-platform"])
            logger.debug(f"[IAM Signing] Credentials scoped for cloud-platform")

        # Get service account email
        if hasattr(credentials, 'service_account_email'):
            service_account_email = credentials.service_account_email
            logger.debug(f"[IAM Signing] Retrieved service_account_email from credentials: {service_account_email}")
        elif hasattr(credentials, 'signer_email'):
            service_account_email = credentials.signer_email
            logger.debug(f"[IAM Signing] Retrieved signer_email from credentials: {service_account_email}")
        elif isinstance(credentials, compute_engine.Credentials):
            # For Compute Engine, need to fetch service account email
            logger.debug(f"[IAM Signing] Detected Compute Engine credentials, fetching from metadata")
            service_account_email = self._get_compute_engine_service_account()
        else:
            service_account_email = None
            logger.debug(f"[IAM Signing] Credentials type {type(credentials).__name__} has no direct email attribute")

        if service_account_email in (None, "default", ""):
            logger.info(f"[IAM Signing] Service account email is placeholder or missing: '{service_account_email}', checking env override")
            # Allow explicit override via environment for edge deployments
            service_account_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
            if service_account_email:
                logger.info(f"[IAM Signing] Using service account from GOOGLE_SERVICE_ACCOUNT_EMAIL: {service_account_email}")

        # Some credential types (notably on Cloud Run) expose "default" as a
        # placeholder service account email. Treat that the same as missing.
        if service_account_email in (None, "default", ""):
            logger.info(f"[IAM Signing] Attempting to fetch service account from metadata server")
            service_account_email = self._get_compute_engine_service_account()

        if not service_account_email or "@" not in service_account_email:
            logger.error(
                "[IAM Signing] Cannot determine service account email for IAM signing; got %s",
                service_account_email or "<empty>"
            )
            return None
        
        if not service_account_email:
            logger.error("[IAM Signing] Service account email is None, cannot sign URL")
            return None
        
        logger.info(f"[IAM Signing] Using service account {service_account_email} for IAM signing")
        
        # Create IAM signer
        logger.debug(f"[IAM Signing] Creating IAM signer with service account: {service_account_email}")
        auth_request = AuthRequest()
        credentials.refresh(auth_request)
        logger.debug(f"[IAM Signing] Credentials refreshed, token valid: {bool(credentials.token)}")
        
        signer = iam.Signer(
            request=auth_request,
            credentials=credentials,
            service_account_email=service_account_email
        )
        logger.debug(f"[IAM Signing] IAM signer created successfully")

        class _IAMCredentials:
            def __init__(self, signer, email):
                self.signer = signer
                self.signer_email = email

            def sign_bytes(self, payload):
                return self.signer.sign(payload)
        
        # Generate signed URL using the signer
        expiration_time = datetime.now(timezone.utc) + expiration
        logger.debug(f"[IAM Signing] Generating signed URL with expiration: {expiration_time}")
        
        try:
            # Use blob's generate_signed_url with the IAM signer
            bucket = self._ensure_bucket()
            blob = bucket.blob(blob_path)

            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=expiration_time,
                method=method,
                service_account_email=service_account_email,
                credentials=_IAMCredentials(signer, service_account_email),
                access_token=credentials.token,
                response_type="video/mp4"
            )
            logger.info(f"[IAM Signing] Successfully generated signed URL for {blob_path}")
            return signed_url
        except Exception as e:
            logger.error(f"[IAM Signing] Failed to generate signed URL with IAM signer: {e}", exc_info=True)
            return None
    
    def _get_public_url_if_accessible(self, blob_path: str) -> Optional[str]:
        """Check if blob is publicly accessible and return public URL.
        
        NOTE: This should NEVER succeed in production as videos must remain private.
        This method exists only for debugging/logging purposes.
        """
        logger.warning(f"[Security] Attempted to get public URL for {blob_path} - this should not be used")
        logger.warning(f"[Security] Videos MUST remain private. If you see this, check IAM permissions.")
        
        # Do NOT return public URLs - videos must remain private
        # Only authenticated users who own the project should access videos
        return None
    
    def _get_compute_engine_service_account(self) -> Optional[str]:
        """Get the service account email for Compute Engine credentials."""
        logger.debug("[IAM Signing] Querying metadata server for service account email")
        try:
            import requests
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
            headers = {"Metadata-Flavor": "Google"}
            response = requests.get(metadata_url, headers=headers, timeout=2)
            if response.status_code == 200:
                email = response.text
                logger.info(f"[IAM Signing] Retrieved service account from metadata: {email}")
                return email
            else:
                logger.warning(f"[IAM Signing] Metadata server returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"[IAM Signing] Failed to get service account from metadata: {e}")
        return None


# Singleton instance (imported by services/routes)
reel_storage_service = ReelStorageService()
