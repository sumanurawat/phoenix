"""
Video stitching implementation using FFmpeg.
"""
import os
import subprocess
import tempfile
import logging
import re
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from jobs.shared.utils import run_command, validate_video_file, get_file_size_mb, safe_filename
from jobs.base.progress_publisher import ProgressPublisher

logger = logging.getLogger(__name__)


class VideoStitcher:
    """Handles video stitching operations using FFmpeg."""

    def __init__(self, temp_dir: str, job_id: Optional[str] = None):
        self.temp_dir = temp_dir
        self.job_id = job_id
        self.progress_callback: Optional[Callable] = None
        self.progress_publisher: Optional[ProgressPublisher] = None
        
        # Initialize progress publisher if job_id is provided
        if job_id:
            self.progress_publisher = ProgressPublisher(job_id)

    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Set callback for progress updates."""
        self.progress_callback = callback

    async def stitch_videos(
        self,
        input_files: List[str],
        output_file: str,
        orientation: str = "portrait",
        compression: str = "optimized",
        audio_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Stitch multiple video files into a single video.

        Args:
            input_files: List of local video file paths
            output_file: Output video file path
            orientation: "portrait" (9:16) or "landscape" (16:9)
            compression: "optimized" or "lossless"
            audio_enabled: Whether to include audio

        Returns:
            Dictionary with stitching results

        Raises:
            Exception: If stitching fails
        """
        logger.info(f"Starting video stitching: {len(input_files)} files → {output_file}")
        
        if self.progress_publisher:
            self.progress_publisher.publish_stage_start(
                'validation',
                f'Validating {len(input_files)} input video files',
                0
            )

        # Validate input files
        valid_files = await self._validate_input_files(input_files)
        if not valid_files:
            if self.progress_publisher:
                self.progress_publisher.publish_error(
                    "No valid video files found for stitching",
                    'validation'
                )
            raise ValueError("No valid video files found for stitching")

        self._update_progress(10, "Input validation complete")
        if self.progress_publisher:
            self.progress_publisher.publish_stage_complete(
                'validation',
                f'Validated {len(valid_files)} videos successfully',
                10
            )

        # Prepare files for concatenation
        if self.progress_publisher:
            self.progress_publisher.publish_stage_start(
                'preparation',
                'Preparing video file list for concatenation',
                15
            )
        concat_file = await self._prepare_concat_file(valid_files)
        self._update_progress(20, "Prepared file list")
        if self.progress_publisher:
            self.progress_publisher.publish_stage_complete(
                'preparation',
                f'Created concat file with {len(valid_files)} entries',
                20
            )

        # Get video parameters
        if self.progress_publisher:
            self.progress_publisher.publish_stage_start(
                'analysis',
                'Analyzing video properties (resolution, framerate, duration)',
                25
            )
        video_params = await self._analyze_videos(valid_files)
        self._update_progress(30, "Analyzed video properties")
        if self.progress_publisher:
            total_duration = video_params.get('total_duration', 0)
            self.progress_publisher.publish_stage_complete(
                'analysis',
                f'Analysis complete: {total_duration:.1f}s total, {video_params.get("common_fps", 30)}fps',
                30
            )

        # Generate FFmpeg command
        if self.progress_publisher:
            self.progress_publisher.publish(
                35,
                'Building FFmpeg command with encoding settings',
                'preparation'
            )
        ffmpeg_cmd = self._build_ffmpeg_command(
            concat_file, output_file, orientation, compression, audio_enabled, video_params
        )
        self._update_progress(40, "Generated FFmpeg command")
        if self.progress_publisher:
            self.progress_publisher.publish_stage_complete(
                'preparation',
                f'FFmpeg command ready: {compression} compression, {orientation} orientation',
                40
            )

        # Execute stitching
        try:
            if self.progress_publisher:
                self.progress_publisher.publish_stage_start(
                    'stitching',
                    'Starting FFmpeg video stitching process',
                    40
                )
            await self._execute_stitching(ffmpeg_cmd, video_params.get('total_duration', 0))
            self._update_progress(90, "Video stitching complete")
            if self.progress_publisher:
                self.progress_publisher.publish_stage_complete(
                    'stitching',
                    'FFmpeg stitching completed successfully',
                    90
                )

            # Validate output
            if self.progress_publisher:
                self.progress_publisher.publish_stage_start(
                    'validation',
                    'Validating stitched output video',
                    92
                )
            output_info = await self._validate_output(output_file)
            self._update_progress(100, "Stitching completed successfully")
            if self.progress_publisher:
                self.progress_publisher.publish_stage_complete(
                    'validation',
                    f'Output validated: {output_info["size_mb"]:.1f}MB, {output_info["duration"]:.1f}s',
                    100
                )

            logger.info(f"Successfully stitched {len(valid_files)} videos into {output_file}")

            return {
                'output_file': output_file,
                'input_count': len(valid_files),
                'output_size_mb': output_info['size_mb'],
                'duration_seconds': output_info['duration'],
                'resolution': output_info['resolution'],
                'compression': compression,
                'orientation': orientation
            }

        finally:
            # Cleanup temporary files
            if os.path.exists(concat_file):
                os.remove(concat_file)

    async def _validate_input_files(self, input_files: List[str]) -> List[str]:
        """Validate and filter input video files."""
        valid_files = []

        for file_path in input_files:
            if not os.path.exists(file_path):
                logger.warning(f"Input file not found: {file_path}")
                continue

            if not validate_video_file(file_path):
                logger.warning(f"Invalid video file: {file_path}")
                continue

            file_size = get_file_size_mb(file_path)
            if file_size == 0:
                logger.warning(f"Empty video file: {file_path}")
                continue

            valid_files.append(file_path)
            logger.info(f"Valid input file: {file_path} ({file_size:.1f} MB)")

        if len(valid_files) < 2:
            raise ValueError(f"Need at least 2 valid videos, found {len(valid_files)}")

        return valid_files

    async def _prepare_concat_file(self, input_files: List[str]) -> str:
        """Create FFmpeg concat file for input videos."""
        concat_file = os.path.join(self.temp_dir, "concat_list.txt")

        with open(concat_file, 'w') as f:
            for file_path in input_files:
                # Escape special characters for FFmpeg
                escaped_path = file_path.replace("'", "\\'")
                f.write(f"file '{escaped_path}'\n")

        logger.info(f"Created concat file: {concat_file}")
        return concat_file

    async def _analyze_videos(self, input_files: List[str]) -> Dict[str, Any]:
        """Analyze video properties to determine optimal stitching parameters."""
        logger.info("Analyzing video properties...")

        total_duration = 0.0
        resolutions = []
        frame_rates = []

        for file_path in input_files:
            try:
                # Use ffprobe to get video info
                cmd = [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    '-show_streams',
                    file_path
                ]

                result = run_command(cmd, timeout=30)
                import json
                info = json.loads(result.stdout)

                # Extract video stream info
                for stream in info.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        duration = float(stream.get('duration', 0))
                        total_duration += duration

                        width = stream.get('width', 0)
                        height = stream.get('height', 0)
                        if width and height:
                            resolutions.append((width, height))

                        frame_rate = stream.get('r_frame_rate', '30/1')
                        if '/' in frame_rate:
                            num, den = frame_rate.split('/')
                            fps = float(num) / float(den) if float(den) != 0 else 30
                            frame_rates.append(fps)

                        break

            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        # Determine common resolution (use most common)
        if resolutions:
            common_resolution = max(set(resolutions), key=resolutions.count)
        else:
            common_resolution = (1080, 1920)  # Default portrait

        # Determine common frame rate
        if frame_rates:
            common_fps = max(set(frame_rates), key=frame_rates.count)
        else:
            common_fps = 30

        analysis = {
            'total_duration': total_duration,
            'common_resolution': common_resolution,
            'common_fps': common_fps,
            'file_count': len(input_files)
        }

        logger.info(f"Video analysis: {analysis}")
        return analysis

    def _build_ffmpeg_command(
        self,
        concat_file: str,
        output_file: str,
        orientation: str,
        compression: str,
        audio_enabled: bool,
        video_params: Dict[str, Any]
    ) -> List[str]:
        """Build FFmpeg command for video stitching."""

        # Base command
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-y'  # Overwrite output file
        ]

        # Video encoding settings
        if compression == "lossless":
            cmd.extend(['-c:v', 'libx264', '-crf', '18', '-preset', 'slow'])
        else:  # optimized
            cmd.extend(['-c:v', 'libx264', '-crf', '23', '-preset', 'medium'])

        # Resolution and aspect ratio
        common_resolution = video_params.get('common_resolution', (1080, 1920))
        if orientation == "portrait":
            target_width, target_height = 1080, 1920
        else:  # landscape
            target_width, target_height = 1920, 1080

        # Scale if needed
        if common_resolution != (target_width, target_height):
            cmd.extend(['-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2'])

        # Frame rate
        common_fps = video_params.get('common_fps', 30)
        cmd.extend(['-r', str(int(common_fps))])

        # Audio settings with proper sync
        if audio_enabled:
            # Use copy for audio to avoid re-encoding issues
            # Add async flag to handle slight A/V sync issues
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '192k',  # Higher bitrate for better quality
                '-ar', '48000',  # Standard sample rate
                '-ac', '2',      # Stereo
                '-async', '1',   # Audio sync method - resample audio to match video
                '-vsync', 'cfr'  # Constant frame rate for video
            ])
        else:
            cmd.extend(['-an'])  # No audio

        # Output format with proper muxing
        cmd.extend([
            '-f', 'mp4',
            '-movflags', '+faststart'  # Enable streaming
        ])

        # Progress reporting
        cmd.extend(['-progress', 'pipe:1'])

        # Output file
        cmd.append(output_file)

        logger.info(f"FFmpeg command: {' '.join(cmd)}")
        return cmd

    async def _execute_stitching(self, ffmpeg_cmd: List[str], estimated_duration: float) -> None:
        """Execute FFmpeg stitching with progress monitoring."""
        logger.info("Starting FFmpeg execution...")

        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Monitor progress
            current_time = 0.0
            fps = None
            speed = None
            last_progress_time = 0.0
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break

                if output:
                    # Parse FFmpeg progress output
                    # Format: out_time_ms=12345678\nfps=30.5\nspeed=1.5x
                    if 'out_time_ms=' in output:
                        try:
                            time_ms = int(output.split('out_time_ms=')[1].strip())
                            current_time = time_ms / 1000000.0  # Convert to seconds

                            # Update progress (report every 2 seconds to avoid spam)
                            if estimated_duration > 0 and (current_time - last_progress_time >= 2.0):
                                progress_percent = min((current_time / estimated_duration) * 50 + 40, 89)
                                message = f"Stitching... {current_time:.1f}s / {estimated_duration:.1f}s"
                                
                                self._update_progress(progress_percent, message)
                                
                                # Publish to Firestore with detailed info
                                if self.progress_publisher:
                                    self.progress_publisher.publish_ffmpeg_progress(
                                        current_time=current_time,
                                        total_duration=estimated_duration,
                                        fps=fps,
                                        speed=speed
                                    )
                                
                                last_progress_time = current_time
                        except (ValueError, IndexError):
                            pass
                    
                    # Parse FPS
                    if 'fps=' in output:
                        try:
                            fps_match = re.search(r'fps=\s*([\d.]+)', output)
                            if fps_match:
                                fps = float(fps_match.group(1))
                        except (ValueError, AttributeError):
                            pass
                    
                    # Parse speed
                    if 'speed=' in output:
                        try:
                            speed_match = re.search(r'speed=\s*([\d.]+)x', output)
                            if speed_match:
                                speed = float(speed_match.group(1))
                        except (ValueError, AttributeError):
                            pass

            # Wait for completion
            return_code = process.wait()

            if return_code != 0:
                stderr_output = process.stderr.read()
                error_msg = f"FFmpeg failed with return code {return_code}"
                logger.error(error_msg)
                logger.error(f"Error output: {stderr_output}")
                
                if self.progress_publisher:
                    self.progress_publisher.publish_error(
                        f"FFmpeg error: {stderr_output[:200]}",
                        'stitching'
                    )
                
                raise subprocess.CalledProcessError(return_code, ffmpeg_cmd, stderr_output)

            logger.info("FFmpeg execution completed successfully")

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed with return code {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            raise Exception(f"Video stitching failed: {e.stderr}")

    async def _validate_output(self, output_file: str) -> Dict[str, Any]:
        """Validate the stitched output video."""
        if not os.path.exists(output_file):
            raise Exception("Output file was not created")

        if not validate_video_file(output_file):
            raise Exception("Output file is not a valid video")

        # Get output file info
        file_size_mb = get_file_size_mb(output_file)

        # Get video duration and resolution
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                output_file
            ]

            result = run_command(cmd, timeout=30)
            import json
            info = json.loads(result.stdout)

            duration = 0.0
            resolution = "unknown"

            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    duration = float(stream.get('duration', 0))
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    if width and height:
                        resolution = f"{width}x{height}"
                    break

            return {
                'size_mb': file_size_mb,
                'duration': duration,
                'resolution': resolution
            }

        except Exception as e:
            logger.warning(f"Failed to get output info: {e}")
            return {
                'size_mb': file_size_mb,
                'duration': 0.0,
                'resolution': "unknown"
            }

    def _update_progress(self, percent: float, message: str) -> None:
        """Update progress via callback."""
        if self.progress_callback:
            self.progress_callback(percent, message)
        else:
            logger.info(f"Progress {percent:.1f}%: {message}")


class StitchingPresets:
    """Predefined stitching configurations for different use cases."""

    @staticmethod
    def social_media_portrait() -> Dict[str, Any]:
        """Settings optimized for social media portrait videos."""
        return {
            'orientation': 'portrait',
            'resolution': (1080, 1920),
            'compression': 'optimized',
            'audio_enabled': True,
            'frame_rate': 30
        }

    @staticmethod
    def social_media_landscape() -> Dict[str, Any]:
        """Settings optimized for social media landscape videos."""
        return {
            'orientation': 'landscape',
            'resolution': (1920, 1080),
            'compression': 'optimized',
            'audio_enabled': True,
            'frame_rate': 30
        }

    @staticmethod
    def high_quality() -> Dict[str, Any]:
        """Settings for high quality output."""
        return {
            'orientation': 'portrait',
            'resolution': (1080, 1920),
            'compression': 'lossless',
            'audio_enabled': True,
            'frame_rate': 60
        }