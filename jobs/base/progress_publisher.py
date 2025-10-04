"""
Real-time progress publishing for Cloud Run Jobs.
Publishes progress logs to Firestore for frontend consumption.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from firebase_admin import firestore

logger = logging.getLogger(__name__)


class ProgressPublisher:
    """
    Publishes job progress to Firestore for real-time monitoring.
    
    Progress logs are stored in a subcollection: reel_jobs/{job_id}/progress_logs
    Each log entry contains:
    - timestamp
    - progress_percent (0-100)
    - message (human-readable description)
    - stage (e.g., "downloading", "stitching", "uploading")
    - metadata (optional additional data)
    """

    def __init__(self, job_id: str, db_client: Optional[firestore.Client] = None):
        self.job_id = job_id
        self.db = db_client or firestore.client()
        self.job_ref = self.db.collection('reel_jobs').document(job_id)
        self.progress_ref = self.job_ref.collection('progress_logs')
        self.log_counter = 0
        
    def publish(
        self,
        progress_percent: float,
        message: str,
        stage: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publish a progress update to Firestore.
        
        Args:
            progress_percent: Progress percentage (0-100)
            message: Human-readable progress message
            stage: Current processing stage
            metadata: Optional additional data
        """
        try:
            self.log_counter += 1
            log_entry = {
                'timestamp': datetime.now(timezone.utc),
                'progress_percent': min(100, max(0, progress_percent)),
                'message': message,
                'stage': stage,
                'log_number': self.log_counter,
                'metadata': metadata or {}
            }
            
            # Use log_counter as document ID for ordering
            doc_id = f"{self.log_counter:05d}"
            self.progress_ref.document(doc_id).set(log_entry)
            
            # Also update the main job document with latest progress
            self.job_ref.update({
                'progress_percent': progress_percent,
                'current_stage': stage,
                'last_progress_message': message,
                'last_progress_update': datetime.now(timezone.utc)
            })
            
            logger.info(
                f"Progress published: {progress_percent:.1f}% - {message}",
                extra={
                    'job_id': self.job_id,
                    'stage': stage,
                    'progress': progress_percent
                }
            )
            
        except Exception as e:
            # Don't fail the job if progress publishing fails
            logger.warning(
                f"Failed to publish progress: {e}",
                extra={'job_id': self.job_id}
            )
    
    def publish_stage_start(self, stage: str, message: str, progress: float) -> None:
        """Publish the start of a processing stage."""
        self.publish(
            progress_percent=progress,
            message=f"🚀 {message}",
            stage=stage
        )
    
    def publish_stage_complete(self, stage: str, message: str, progress: float) -> None:
        """Publish the completion of a processing stage."""
        self.publish(
            progress_percent=progress,
            message=f"✅ {message}",
            stage=stage
        )
    
    def publish_error(self, error_message: str, stage: str) -> None:
        """Publish an error message."""
        self.publish(
            progress_percent=-1,  # Special value indicating error
            message=f"❌ {error_message}",
            stage=stage,
            metadata={'error': True}
        )
    
    def publish_ffmpeg_progress(
        self,
        current_time: float,
        total_duration: float,
        fps: Optional[float] = None,
        speed: Optional[float] = None
    ) -> None:
        """
        Publish FFmpeg processing progress.
        
        Args:
            current_time: Current processing time in seconds
            total_duration: Total video duration in seconds
            fps: Current frames per second
            speed: Processing speed multiplier (e.g., 2.5x)
        """
        if total_duration <= 0:
            return
            
        # Calculate progress (40-90% range reserved for FFmpeg processing)
        base_progress = 40
        ffmpeg_range = 50
        video_progress = (current_time / total_duration) * 100
        actual_progress = base_progress + (video_progress * ffmpeg_range / 100)
        
        # Build message with details
        parts = [f"Stitching video: {video_progress:.1f}%"]
        if fps:
            parts.append(f"{fps:.1f} fps")
        if speed:
            parts.append(f"{speed:.1f}x speed")
        
        message = " | ".join(parts)
        
        # Calculate ETA if we have speed
        eta_seconds = None
        if speed and speed > 0:
            remaining_time = total_duration - current_time
            eta_seconds = remaining_time / speed
        
        metadata = {
            'current_time': current_time,
            'total_duration': total_duration,
            'fps': fps,
            'speed': speed,
            'eta_seconds': eta_seconds
        }
        
        self.publish(
            progress_percent=actual_progress,
            message=message,
            stage='stitching',
            metadata=metadata
        )
    
    def clear_logs(self) -> None:
        """Clear all progress logs for this job (cleanup)."""
        try:
            # Delete all documents in the progress_logs subcollection
            docs = self.progress_ref.stream()
            for doc in docs:
                doc.reference.delete()
            logger.info(f"Cleared progress logs for job {self.job_id}")
        except Exception as e:
            logger.warning(f"Failed to clear progress logs: {e}")
