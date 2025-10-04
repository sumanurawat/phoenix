"""
Configuration management for Cloud Run Jobs.
"""
import os
from typing import Optional


class JobConfig:
    """Centralized configuration for all job types."""

    # Google Cloud
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "phoenix-project-386")
    REGION = os.getenv("GCP_REGION", "us-central1")

    # Storage
    VIDEO_STORAGE_BUCKET = os.getenv("VIDEO_STORAGE_BUCKET", "phoenix-videos")

    # Job settings
    JOB_TIMEOUT_MINUTES = int(os.getenv("JOB_TIMEOUT_MINUTES", "15"))
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    TEMP_DIR = os.getenv("TEMP_DIR", "/tmp")

    # Firestore collections
    JOBS_COLLECTION = "reel_jobs"
    CHECKPOINTS_COLLECTION = "reel_job_checkpoints"
    PROJECTS_COLLECTION = "reel_maker_projects"

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"

    # Memory limits (in MB)
    STITCHING_JOB_MEMORY_MB = int(os.getenv("STITCHING_JOB_MEMORY_MB", "4096"))
    GENERATION_JOB_MEMORY_MB = int(os.getenv("GENERATION_JOB_MEMORY_MB", "2048"))

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        required_vars = [
            "VIDEO_STORAGE_BUCKET",
            "PROJECT_ID"
        ]

        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)

        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

    @classmethod
    def get_bucket_name(cls) -> str:
        """Get the configured storage bucket name."""
        bucket = cls.VIDEO_STORAGE_BUCKET
        if not bucket:
            raise ValueError("VIDEO_STORAGE_BUCKET environment variable is required")
        return bucket

    @classmethod
    def get_temp_dir(cls, job_id: str) -> str:
        """Get temporary directory path for a job."""
        return os.path.join(cls.TEMP_DIR, f"job_{job_id}")