"""
Video Stitching Service - Combines multiple video clips into a single reel.

Uses FFmpeg to concatenate clips with consistent encoding.
"""
import logging
import os
import tempfile
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from services.reel_storage_service import reel_storage_service
from services.realtime_event_bus import realtime_event_bus

logger = logging.getLogger(__name__)


class VideoStitchingService:
    """Service for stitching multiple video clips into a single reel."""

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable in system PATH."""
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            logger.warning("FFmpeg not found in PATH. Video stitching will fail.")
            return 'ffmpeg'  # Will fail if not installed
        return ffmpeg

    def is_available(self) -> bool:
        """Check if FFmpeg is available and working."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"FFmpeg availability check failed: {e}")
            return False

    def stitch_clips(
        self,
        user_id: str,
        project_id: str,
        clip_paths: List[str],
        job_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Stitch multiple clips into a single video.
        
        Args:
            user_id: User ID for storage organization
            project_id: Project ID for storage organization
            clip_paths: List of GCS paths to video clips
            job_id: Optional job ID for progress tracking
            
        Returns:
            GCS path to stitched video, or None on failure
        """
        if not self.is_available():
            logger.error("FFmpeg not available - cannot stitch videos")
            self._emit_progress(job_id, "error", "FFmpeg not installed")
            return None

        if len(clip_paths) < 2:
            logger.error("Need at least 2 clips to stitch")
            self._emit_progress(job_id, "error", "Need at least 2 clips")
            return None

        temp_dir = None
        try:
            # Create temporary workspace
            temp_dir = tempfile.mkdtemp(prefix='reel_stitch_')
            logger.info(f"Created temp directory: {temp_dir}")
            
            # Step 1: Download clips
            self._emit_progress(job_id, "downloading", f"Downloading {len(clip_paths)} clips")
            local_clips = self._download_clips(temp_dir, clip_paths)
            
            if not local_clips:
                raise ValueError("Failed to download clips")
            
            # Step 2: Create FFmpeg concat file
            concat_file = os.path.join(temp_dir, 'concat_list.txt')
            self._create_concat_file(concat_file, local_clips)
            
            # Step 3: Stitch videos
            self._emit_progress(job_id, "stitching", "Combining clips with FFmpeg")
            output_file = os.path.join(temp_dir, 'stitched_output.mp4')
            
            if not self._run_ffmpeg_concat(concat_file, output_file):
                raise RuntimeError("FFmpeg concatenation failed")
            
            # Step 4: Upload to GCS
            self._emit_progress(job_id, "uploading", "Uploading stitched reel")
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
            stitched_filename = f"reel_full_{timestamp}.mp4"
            gcs_path = f"reel-maker/{user_id}/{project_id}/stitched/{stitched_filename}"
            
            if not self._upload_to_gcs(output_file, gcs_path):
                raise RuntimeError("Failed to upload stitched video")
            
            self._emit_progress(job_id, "complete", "Stitching complete")
            logger.info(f"Successfully stitched video: {gcs_path}")
            
            return gcs_path
            
        except Exception as e:
            logger.exception(f"Video stitching failed: {e}")
            self._emit_progress(job_id, "error", str(e))
            return None
            
        finally:
            # Cleanup temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.error(f"Failed to cleanup temp directory: {e}")

    def _download_clips(self, temp_dir: str, clip_paths: List[str]) -> List[str]:
        """Download clips from GCS to local temp directory."""
        local_clips = []
        bucket = reel_storage_service._ensure_bucket()
        
        for i, clip_path in enumerate(clip_paths):
            try:
                blob = bucket.blob(clip_path)
                if not blob.exists():
                    logger.error(f"Clip not found in GCS: {clip_path}")
                    continue
                
                local_path = os.path.join(temp_dir, f"clip_{i:03d}.mp4")
                blob.download_to_filename(local_path)
                local_clips.append(local_path)
                logger.info(f"Downloaded clip {i+1}/{len(clip_paths)}: {clip_path}")
                
            except Exception as e:
                logger.error(f"Failed to download clip {clip_path}: {e}")
                continue
        
        return local_clips

    def _create_concat_file(self, concat_file: str, local_clips: List[str]):
        """Create FFmpeg concat demuxer input file."""
        with open(concat_file, 'w') as f:
            for clip in local_clips:
                # Escape single quotes and write in FFmpeg concat format
                escaped_path = clip.replace("'", r"'\''")
                f.write(f"file '{escaped_path}'\n")
        logger.info(f"Created concat file with {len(local_clips)} entries")

    def _run_ffmpeg_concat(self, concat_file: str, output_file: str) -> bool:
        """
        Run FFmpeg to concatenate videos.
        
        Uses concat demuxer with re-encoding to ensure compatibility.
        """
        try:
            # Use concat demuxer with re-encoding for maximum compatibility
            # This ensures all clips have the same codec, resolution, and framerate
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',        # Re-encode to H.264
                '-preset', 'medium',      # Balance speed/quality
                '-crf', '23',             # Good quality
                '-c:a', 'aac',            # AAC audio
                '-b:a', '128k',           # Audio bitrate
                '-movflags', '+faststart', # Enable streaming
                '-y',                     # Overwrite output
                output_file
            ]
            
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg failed with code {result.returncode}")
                logger.error(f"FFmpeg stderr: {result.stderr}")
                return False
            
            if not os.path.exists(output_file):
                logger.error("FFmpeg completed but output file not found")
                return False
            
            file_size = os.path.getsize(output_file)
            logger.info(f"FFmpeg concatenation successful. Output size: {file_size} bytes")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg process timed out after 5 minutes")
            return False
        except Exception as e:
            logger.exception(f"FFmpeg execution failed: {e}")
            return False

    def _upload_to_gcs(self, local_file: str, gcs_path: str) -> bool:
        """Upload stitched video to GCS."""
        try:
            bucket = reel_storage_service._ensure_bucket()
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(local_file)
            logger.info(f"Uploaded stitched video to GCS: {gcs_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            return False

    def _emit_progress(self, job_id: Optional[str], status: str, message: str):
        """Emit progress event via SSE."""
        if not job_id:
            return
        
        try:
            event_data = {
                "jobId": job_id,
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            realtime_event_bus.publish(f"reel_stitch_{job_id}", event_data)
            logger.debug(f"Emitted progress event: {status} - {message}")
        except Exception as e:
            logger.error(f"Failed to emit progress event: {e}")


# Singleton instance
video_stitching_service = VideoStitchingService()
