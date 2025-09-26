"""Video Stitching Service for combining multiple video clips into a single reel"""
from __future__ import annotations
import logging
import os
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from services.gcs_media_service import GCSMediaService

logger = logging.getLogger(__name__)

class VideoStitchingService:
    """Service for stitching multiple video clips into a single reel"""
    
    def __init__(self):
        self.gcs_service = GCSMediaService()
        
    def check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available in the system"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
            
    def stitch_videos(
        self,
        user_id: str,
        project_id: str,
        clip_filenames: List[str],
        project_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stitch multiple video clips into a single reel"""
        
        if not self.check_ffmpeg_available():
            return {
                "success": False,
                "error": "FFmpeg not available on system"
            }
            
        if len(clip_filenames) < 2:
            return {
                "success": False,
                "error": "At least 2 clips required for stitching"
            }
            
        temp_dir = None
        try:
            # Create temporary working directory
            temp_dir = tempfile.mkdtemp(prefix=f"reel_stitch_{project_id}_")
            logger.info(f"Created temp directory for stitching: {temp_dir}")
            
            # Download clips from GCS
            downloaded_clips = self.gcs_service.download_clips_for_stitching(
                user_id, project_id, clip_filenames, temp_dir
            )
            
            if not downloaded_clips:
                return {
                    "success": False,
                    "error": "No clips could be downloaded for stitching"
                }
                
            if len(downloaded_clips) != len(clip_filenames):
                logger.warning(f"Only {len(downloaded_clips)} of {len(clip_filenames)} clips downloaded")
                
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            output_filename = f"reel_full_{timestamp}.mp4"
            output_path = os.path.join(temp_dir, output_filename)
            
            # Create concat file for FFmpeg
            concat_file_path = os.path.join(temp_dir, "concat_list.txt")
            self._create_concat_file(downloaded_clips, concat_file_path)
            
            # Run FFmpeg stitching
            stitch_result = self._run_ffmpeg_concat(
                concat_file_path, output_path, project_config
            )
            
            if not stitch_result["success"]:
                return stitch_result
                
            # Upload stitched video to GCS
            upload_success = self.gcs_service.upload_stitched_video(
                user_id, project_id, output_path, output_filename
            )
            
            if not upload_success:
                return {
                    "success": False,
                    "error": "Failed to upload stitched video to storage"
                }
                
            # Get video duration
            duration = self._get_video_duration(output_path)
            
            return {
                "success": True,
                "filename": output_filename,
                "duration": duration,
                "clip_count": len(downloaded_clips)
            }
            
        except Exception as e:
            logger.error(f"Error stitching videos: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory: {e}")
                    
    def _create_concat_file(self, clip_paths: List[str], concat_file_path: str):
        """Create FFmpeg concat file listing all clips"""
        with open(concat_file_path, 'w') as f:
            for clip_path in clip_paths:
                # Escape special characters in file paths
                escaped_path = clip_path.replace("'", "'\"'\"'")
                f.write(f"file '{escaped_path}'\n")
                
        logger.debug(f"Created concat file with {len(clip_paths)} clips")
        
    def _run_ffmpeg_concat(
        self,
        concat_file_path: str,
        output_path: str,
        project_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run FFmpeg to concatenate videos"""
        try:
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file_path,
                '-c:v', 'libx264',  # Re-encode video for consistency
                '-c:a', 'aac',      # Re-encode audio for consistency
                '-preset', 'fast',   # Balance between speed and compression
                '-crf', '23',        # Good quality level
                '-movflags', '+faststart',  # Optimize for streaming
                '-y',  # Overwrite output file
                output_path
            ]
            
            # Add audio options based on project config
            if not project_config.get('audioEnabled', True):
                cmd.extend(['-an'])  # Remove audio
                
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg failed with return code {result.returncode}")
                logger.error(f"FFmpeg stderr: {result.stderr}")
                return {
                    "success": False,
                    "error": f"Video stitching failed: {result.stderr}"
                }
                
            if not os.path.exists(output_path):
                return {
                    "success": False,
                    "error": "Output video file was not created"
                }
                
            logger.info(f"Successfully stitched video: {output_path}")
            return {"success": True}
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Video stitching timed out after 5 minutes"
            }
        except Exception as e:
            logger.error(f"Error running FFmpeg: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def _get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                duration = data.get('format', {}).get('duration')
                if duration:
                    return float(duration)
                    
        except Exception as e:
            logger.warning(f"Could not get video duration: {e}")
            
        return None
        
    def normalize_clip_properties(
        self,
        input_path: str,
        output_path: str,
        target_width: int = 720,
        target_height: int = 1280,
        target_fps: int = 30
    ) -> bool:
        """Normalize a video clip's properties for consistent stitching"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2',
                '-r', str(target_fps),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                '-crf', '23',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return result.returncode == 0 and os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"Error normalizing clip: {e}")
            return False
            
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get detailed information about a video file"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
                
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            
        return {}