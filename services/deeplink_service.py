"""
Deep Link Service

Service for handling YouTube URL conversion to deep links
"""
import re
from urllib.parse import urlparse, parse_qs

def extract_video_id(youtube_url):
    """Extract the video ID from a YouTube URL.
    
    Supports formats:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID
    """
    try:
        url = urlparse(youtube_url)
        
        if url.hostname in ('youtu.be', 'www.youtu.be'):
            # youtu.be format
            return url.path[1:]  # Remove leading '/'
        
        if url.hostname in ('youtube.com', 'www.youtube.com'):
            # youtube.com format
            query_params = parse_qs(url.query)
            return query_params['v'][0]
            
        return None
    except Exception:
        return None

def validate_video_id(video_id):
    """Validate that a video ID matches YouTube's format."""
    if not video_id:
        return False
    # YouTube video IDs are typically 11 characters of alphanumeric and underscore/dash
    return bool(re.match(r'^[A-Za-z0-9_-]{11}$', video_id))
