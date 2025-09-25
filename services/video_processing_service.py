"""Stub Video Processing Service

This is a minimal stub implementation to satisfy imports while video features are disabled.
TODO: Implement full video processing functionality.
"""

import logging

logger = logging.getLogger(__name__)


class VideoProcessingService:
    """Stub video processing service."""
    
    def __init__(self):
        logger.warning("VideoProcessingService is using stub implementation")
    
    def process_video(self, *args, **kwargs):
        """Stub method - not implemented."""
        raise NotImplementedError("Video processing is not currently implemented")