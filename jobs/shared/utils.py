"""
Common utilities for job operations.
"""
import os
import shutil
import tempfile
import uuid
from typing import List, Optional
import subprocess
import logging

logger = logging.getLogger(__name__)


def generate_job_id() -> str:
    """Generate a unique job ID."""
    return f"job_{uuid.uuid4().hex[:12]}"


def ensure_directory(path: str) -> None:
    """Ensure directory exists, create if necessary."""
    os.makedirs(path, exist_ok=True)


def cleanup_directory(path: str) -> None:
    """Safely remove directory and all contents."""
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            logger.info(f"Cleaned up directory: {path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup directory {path}: {e}")


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes."""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0.0


def run_command(
    command: List[str],
    cwd: Optional[str] = None,
    timeout: Optional[int] = None
) -> subprocess.CompletedProcess:
    """
    Run a shell command safely with logging.

    Args:
        command: Command and arguments as list
        cwd: Working directory
        timeout: Timeout in seconds

    Returns:
        CompletedProcess result

    Raises:
        subprocess.CalledProcessError: If command fails
        subprocess.TimeoutExpired: If command times out
    """
    logger.info(f"Running command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )

        if result.stdout:
            logger.debug(f"Command output: {result.stdout}")

        return result

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        raise

    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout} seconds")
        raise


def validate_video_file(file_path: str) -> bool:
    """
    Validate that a file is a valid video file.

    Args:
        file_path: Path to video file

    Returns:
        True if valid video file
    """
    if not os.path.exists(file_path):
        return False

    try:
        # Use ffprobe to validate video file
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            file_path
        ]

        result = run_command(command, timeout=30)

        # If ffprobe succeeds, it's a valid video
        return result.returncode == 0

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def estimate_processing_time(input_files: List[str]) -> int:
    """
    Estimate processing time in seconds based on input files.

    Args:
        input_files: List of video file paths

    Returns:
        Estimated processing time in seconds
    """
    if not input_files:
        return 0

    total_size_mb = sum(get_file_size_mb(f) for f in input_files if os.path.exists(f))

    # Rough estimate: 2 seconds per MB for stitching
    base_time = int(total_size_mb * 2)

    # Add overhead for file operations
    overhead = 30 + (len(input_files) * 5)

    return max(base_time + overhead, 60)  # Minimum 1 minute


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def safe_filename(filename: str) -> str:
    """Create a safe filename by removing/replacing problematic characters."""
    # Remove or replace characters that might cause issues
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    return ''.join(c if c in safe_chars else '_' for c in filename)