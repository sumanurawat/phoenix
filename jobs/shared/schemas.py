"""
Job payload schemas and data models.
"""
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


@dataclass
class JobPayload:
    """Base job payload."""
    job_id: str
    project_id: str
    user_id: str
    retry_attempt: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobPayload':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class StitchingJobPayload:
    """Payload for video stitching jobs."""
    job_id: str
    project_id: str
    user_id: str
    clip_paths: List[str]
    output_path: str
    retry_attempt: int = 0
    orientation: str = "portrait"  # "portrait" | "landscape"
    compression: str = "optimized"  # "optimized" | "lossless"
    audio_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StitchingJobPayload':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class GenerationJobPayload:
    """Payload for video generation jobs (future)."""
    job_id: str
    project_id: str
    user_id: str
    prompts: List[str]
    output_dir: str
    retry_attempt: int = 0
    model: str = "veo-3.1-fast-generate-preview"
    duration_seconds: int = 8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerationJobPayload':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class JobStatus:
    """Job execution status."""
    job_id: str
    job_type: str
    status: str  # "queued" | "running" | "completed" | "failed" | "cancelled"
    progress: float = 0.0  # 0-100
    message: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    checkpoints: List[str] = None

    def __post_init__(self):
        if self.checkpoints is None:
            self.checkpoints = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for field in ['created_at', 'started_at', 'completed_at']:
            if data[field] and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
        return data


@dataclass
class JobCheckpoint:
    """Job checkpoint data for recovery."""
    job_id: str
    checkpoint_name: str
    timestamp: datetime
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore."""
        return {
            'jobId': self.job_id,
            'checkpointName': self.checkpoint_name,
            'timestamp': self.timestamp,
            'data': self.data
        }


class JobError(Exception):
    """Base exception for job-related errors."""
    pass


class JobAlreadyRunningError(JobError):
    """Raised when trying to start a job that's already running."""
    pass


class InsufficientResourcesError(JobError):
    """Raised when job requirements can't be met."""
    pass


class JobTimeoutError(JobError):
    """Raised when job exceeds maximum execution time."""
    pass


class CheckpointError(JobError):
    """Raised when checkpoint operations fail."""
    pass