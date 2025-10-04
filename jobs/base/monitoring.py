"""
Monitoring and metrics for Cloud Run Jobs.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class JobMonitor:
    """Handles job monitoring, logging, and metrics collection."""

    def __init__(self, job_type: str):
        self.job_type = job_type
        self.start_time: Optional[float] = None
        self.metrics: Dict[str, Any] = {}

    def start_job(self, job_id: str) -> None:
        """Mark job start time and initialize metrics."""
        self.start_time = time.time()
        self.metrics = {
            'job_id': job_id,
            'job_type': self.job_type,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'memory_usage_mb': self._get_memory_usage(),
            'progress_updates': []
        }

        logger.info(
            f"Job {job_id} started",
            extra={
                'job_id': job_id,
                'job_type': self.job_type,
                'memory_mb': self.metrics['memory_usage_mb']
            }
        )

    def record_progress(self, progress: float, message: str = None) -> None:
        """Record progress update."""
        progress_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'progress': progress,
            'message': message,
            'elapsed_seconds': self._get_elapsed_time()
        }

        self.metrics['progress_updates'].append(progress_entry)

        logger.info(
            f"Progress update: {progress:.1f}%",
            extra={
                'progress': progress,
                'message': message,
                'elapsed_seconds': progress_entry['elapsed_seconds']
            }
        )

    def record_success(self, duration_seconds: float) -> None:
        """Record successful job completion."""
        self.metrics.update({
            'status': 'completed',
            'duration_seconds': duration_seconds,
            'end_time': datetime.now(timezone.utc).isoformat(),
            'peak_memory_mb': self._get_memory_usage()
        })

        logger.info(
            f"Job completed successfully",
            extra={
                'job_type': self.job_type,
                'duration_seconds': duration_seconds,
                'peak_memory_mb': self.metrics['peak_memory_mb']
            }
        )

        # Send metrics to monitoring system (if configured)
        self._send_metrics()

    def record_failure(self, error_message: str, duration_seconds: float) -> None:
        """Record job failure."""
        self.metrics.update({
            'status': 'failed',
            'error_message': error_message,
            'duration_seconds': duration_seconds,
            'end_time': datetime.now(timezone.utc).isoformat(),
            'peak_memory_mb': self._get_memory_usage()
        })

        logger.error(
            f"Job failed: {error_message}",
            extra={
                'job_type': self.job_type,
                'error': error_message,
                'duration_seconds': duration_seconds,
                'peak_memory_mb': self.metrics['peak_memory_mb']
            }
        )

        # Send failure metrics
        self._send_metrics()

    def _get_elapsed_time(self) -> float:
        """Get elapsed time since job start."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            return round(memory_mb, 2)
        except (ImportError, Exception):
            # If psutil is not available or fails, return 0
            return 0.0

    def _send_metrics(self) -> None:
        """Send metrics to monitoring system."""
        try:
            # This would integrate with Google Cloud Monitoring
            # For now, we'll just log the metrics
            self._log_structured_metrics()

        except Exception as e:
            logger.warning(f"Failed to send metrics: {e}")

    def _log_structured_metrics(self) -> None:
        """Log metrics in structured format for Cloud Logging."""
        # Remove progress_updates for cleaner logs (they're already logged individually)
        metrics_summary = {k: v for k, v in self.metrics.items() if k != 'progress_updates'}

        logger.info(
            "Job metrics summary",
            extra={
                'event_type': 'job_metrics',
                'metrics': metrics_summary
            }
        )


class PerformanceTracker:
    """Tracks performance metrics for different job operations."""

    def __init__(self):
        self.operation_times: Dict[str, float] = {}
        self.operation_start_times: Dict[str, float] = {}

    def start_operation(self, operation_name: str) -> None:
        """Start timing an operation."""
        self.operation_start_times[operation_name] = time.time()

    def end_operation(self, operation_name: str) -> float:
        """End timing an operation and return duration."""
        start_time = self.operation_start_times.get(operation_name)
        if start_time is None:
            logger.warning(f"No start time recorded for operation: {operation_name}")
            return 0.0

        duration = time.time() - start_time
        self.operation_times[operation_name] = duration

        logger.info(
            f"Operation '{operation_name}' completed",
            extra={
                'operation': operation_name,
                'duration_seconds': round(duration, 2)
            }
        )

        return duration

    def get_performance_summary(self) -> Dict[str, float]:
        """Get summary of all operation timings."""
        return self.operation_times.copy()


class ResourceMonitor:
    """Monitors system resources during job execution."""

    def __init__(self):
        self.peak_memory_mb = 0.0
        self.peak_cpu_percent = 0.0

    def update_resource_usage(self) -> Dict[str, float]:
        """Update and return current resource usage."""
        try:
            import psutil

            # Memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)

            # CPU usage
            cpu_percent = process.cpu_percent()
            self.peak_cpu_percent = max(self.peak_cpu_percent, cpu_percent)

            return {
                'current_memory_mb': round(memory_mb, 2),
                'peak_memory_mb': round(self.peak_memory_mb, 2),
                'current_cpu_percent': round(cpu_percent, 2),
                'peak_cpu_percent': round(self.peak_cpu_percent, 2)
            }

        except (ImportError, Exception) as e:
            logger.debug(f"Could not get resource usage: {e}")
            return {
                'current_memory_mb': 0.0,
                'peak_memory_mb': 0.0,
                'current_cpu_percent': 0.0,
                'peak_cpu_percent': 0.0
            }