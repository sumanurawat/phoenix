"""Stub Video Prompt Parser

This is a minimal stub implementation to satisfy imports while video features are disabled.
TODO: Implement full video prompt parsing functionality.
"""

import logging

logger = logging.getLogger(__name__)


class VideoPromptParser:
    """Stub video prompt parser."""
    
    def __init__(self):
        logger.warning("VideoPromptParser is using stub implementation")
    
    def parse_prompt(self, *args, **kwargs):
        """Stub method - not implemented."""
        raise NotImplementedError("Video prompt parsing is not currently implemented")