"""
Instagram OAuth Service
Handles Instagram Basic Display API OAuth flow for Social Gallery feature.

Instagram Basic Display API Flow:
1. Generate authorization URL
2. User authorizes the app
3. Exchange code for access token
4. Fetch user profile and media
"""
import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from config.settings import (
    INSTAGRAM_CLIENT_ID,
    INSTAGRAM_CLIENT_SECRET,
    INSTAGRAM_REDIRECT_URI
)

logger = logging.getLogger(__name__)

class InstagramOAuthService:
    """
    Service for Instagram OAuth authentication and API interactions.
    Uses Instagram Basic Display API.
    """
    
    # Instagram API endpoints
    AUTHORIZATION_URL = "https://api.instagram.com/oauth/authorize"
    TOKEN_URL = "https://api.instagram.com/oauth/access_token"
    REFRESH_TOKEN_URL = "https://graph.instagram.com/refresh_access_token"
    GRAPH_API_BASE = "https://graph.instagram.com"
    
    def __init__(self):
        """Initialize Instagram OAuth service."""
        self.client_id = INSTAGRAM_CLIENT_ID
        self.client_secret = INSTAGRAM_CLIENT_SECRET
        self.redirect_uri = INSTAGRAM_REDIRECT_URI
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            logger.warning("Instagram OAuth credentials not fully configured")
    
    def is_configured(self) -> bool:
        """Check if Instagram OAuth is properly configured."""
        return all([self.client_id, self.client_secret, self.redirect_uri])
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate Instagram authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL to redirect user to
        """
        if not self.is_configured():
            raise ValueError("Instagram OAuth not configured")
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'user_profile,user_media',
            'response_type': 'code'
        }
        
        if state:
            params['state'] = state
        
        # Build URL with parameters
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTHORIZATION_URL}?{param_string}"
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Instagram callback
            
        Returns:
            Dict containing:
                - access_token: Short-lived access token
                - user_id: Instagram user ID
                
        Raises:
            Exception if token exchange fails
        """
        if not self.is_configured():
            raise ValueError("Instagram OAuth not configured")
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info(f"Successfully exchanged code for token. User ID: {token_data.get('user_id')}")
            
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to exchange code for token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Instagram token exchange failed: {str(e)}")
    
    def get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """
        Exchange short-lived token for long-lived token (60 days).
        
        Args:
            short_lived_token: Short-lived access token
            
        Returns:
            Dict containing:
                - access_token: Long-lived access token
                - token_type: "bearer"
                - expires_in: Seconds until expiration (60 days)
        """
        if not self.is_configured():
            raise ValueError("Instagram OAuth not configured")
        
        url = f"{self.GRAPH_API_BASE}/access_token"
        params = {
            'grant_type': 'ig_exchange_token',
            'client_secret': self.client_secret,
            'access_token': short_lived_token
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully obtained long-lived token")
            
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get long-lived token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Instagram long-lived token exchange failed: {str(e)}")
    
    def refresh_access_token(self, access_token: str) -> Dict[str, Any]:
        """
        Refresh a long-lived access token (extends by 60 days).
        Should be called before token expires.
        
        Args:
            access_token: Current long-lived access token
            
        Returns:
            Dict containing:
                - access_token: Refreshed access token
                - token_type: "bearer"
                - expires_in: Seconds until expiration (60 days)
        """
        params = {
            'grant_type': 'ig_refresh_token',
            'access_token': access_token
        }
        
        try:
            response = requests.get(self.REFRESH_TOKEN_URL, params=params, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully refreshed access token")
            
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Instagram token refresh failed: {str(e)}")
    
    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch user profile information.
        
        Args:
            access_token: Instagram access token
            
        Returns:
            Dict containing:
                - id: Instagram user ID
                - username: Instagram username
                - account_type: Account type (BUSINESS, CREATOR, PERSONAL)
                - media_count: Number of media items
        """
        url = f"{self.GRAPH_API_BASE}/me"
        params = {
            'fields': 'id,username,account_type,media_count',
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            profile = response.json()
            logger.info(f"Fetched profile for user: {profile.get('username')}")
            
            return profile
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch user profile: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Instagram profile fetch failed: {str(e)}")
    
    def get_user_media(self, access_token: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetch user's media (photos/videos).
        
        Args:
            access_token: Instagram access token
            limit: Maximum number of media items to fetch (default: 25)
            
        Returns:
            List of media items, each containing:
                - id: Media ID
                - media_type: IMAGE, VIDEO, or CAROUSEL_ALBUM
                - media_url: URL to the media file
                - permalink: Instagram permalink
                - thumbnail_url: Thumbnail URL (for videos)
                - timestamp: ISO 8601 timestamp
                - caption: Media caption
        """
        url = f"{self.GRAPH_API_BASE}/me/media"
        params = {
            'fields': 'id,media_type,media_url,permalink,thumbnail_url,timestamp,caption',
            'access_token': access_token,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            media_items = data.get('data', [])
            
            logger.info(f"Fetched {len(media_items)} media items")
            
            return media_items
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch user media: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Instagram media fetch failed: {str(e)}")
    
    def get_media_details(self, media_id: str, access_token: str) -> Dict[str, Any]:
        """
        Fetch detailed information about a specific media item.
        
        Args:
            media_id: Instagram media ID
            access_token: Instagram access token
            
        Returns:
            Dict containing detailed media information
        """
        url = f"{self.GRAPH_API_BASE}/{media_id}"
        params = {
            'fields': 'id,media_type,media_url,permalink,thumbnail_url,timestamp,caption,username',
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            media = response.json()
            logger.info(f"Fetched details for media: {media_id}")
            
            return media
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch media details: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Instagram media details fetch failed: {str(e)}")


# Singleton instance
_instagram_oauth_service = None

def get_instagram_oauth_service() -> InstagramOAuthService:
    """Get or create singleton Instagram OAuth service instance."""
    global _instagram_oauth_service
    if _instagram_oauth_service is None:
        _instagram_oauth_service = InstagramOAuthService()
    return _instagram_oauth_service
