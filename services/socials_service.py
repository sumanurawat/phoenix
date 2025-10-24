"""
Social Media Service

Handles social media account connections, post fetching, and OAuth management.
Supports Instagram, YouTube, and Twitter integrations with secure token management.
"""
import os
import logging
import secrets
from datetime import datetime, timezone, timedelta
from firebase_admin import firestore
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class SocialsService:
    """Service for managing social media account connections and posts."""
    
    def __init__(self):
        """Initialize the socials service."""
        self.db = firestore.client()
        self.cipher_suite = self._get_cipher_suite()
    
    def _get_cipher_suite(self):
        """Get or create encryption cipher for token storage."""
        encryption_key = os.environ.get('SOCIAL_TOKEN_ENCRYPTION_KEY')
        
        if not encryption_key:
            # For development only - generate temporary key
            # In production, this MUST be set in environment
            logger.warning(
                "SOCIAL_TOKEN_ENCRYPTION_KEY not set! "
                "Using temporary key - tokens will not persist across restarts. "
                "Set SOCIAL_TOKEN_ENCRYPTION_KEY in production!"
            )
            encryption_key = Fernet.generate_key()
        
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        return Fernet(encryption_key)
    
    # ========== Account Management ==========
    
    def get_user_accounts(self, user_id):
        """
        Get all social accounts for a user.
        
        Args:
            user_id: Firebase user ID
            
        Returns:
            list: List of account dictionaries (no sensitive data)
        """
        try:
            accounts_ref = self.db.collection('user_social_accounts')
            query = accounts_ref.where('user_id', '==', user_id).where('is_active', '==', True)
            accounts = []
            
            for doc in query.stream():
                account_data = doc.to_dict()
                account_data['id'] = doc.id
                
                # SECURITY: Never return sensitive tokens in API responses
                sensitive_fields = [
                    'encrypted_access_token',
                    'encrypted_refresh_token',
                    'access_token',
                    'refresh_token',
                    'oauth_secret'
                ]
                for field in sensitive_fields:
                    account_data.pop(field, None)
                
                # Only return safe display data
                safe_account = {
                    'id': account_data['id'],
                    'platform': account_data['platform'],
                    'username': account_data['username'],
                    'display_name': account_data['display_name'],
                    'account_type': account_data['account_type'],
                    'is_active': account_data['is_active'],
                    'connected_at': account_data['connected_at'],
                    'last_sync': account_data.get('last_sync'),
                    'posts_count': account_data.get('posts_count', 0),
                    'status': account_data.get('status', 'active'),
                    'profile_url': account_data.get('profile_url')
                }
                accounts.append(safe_account)
            
            logger.info(f"Retrieved {len(accounts)} accounts for user {user_id}")
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting user accounts: {str(e)}")
            raise e
    
    def add_public_account(self, user_id, platform, username):
        """
        Add a public social media account (no OAuth required).
        
        Args:
            user_id: Firebase user ID
            platform: Social platform (instagram, youtube, twitter)
            username: Public username
            
        Returns:
            dict: Created account data
        """
        try:
            # Validate platform
            allowed_platforms = ['instagram', 'youtube', 'twitter']
            if platform not in allowed_platforms:
                raise ValueError(f"Invalid platform: {platform}")
            
            # Clean username (remove @ if present)
            username = username.lstrip('@').strip()
            
            if not username:
                raise ValueError("Username cannot be empty")
            
            # Check if account already exists
            existing = self._get_existing_account(user_id, platform, username)
            if existing:
                raise ValueError(f"{platform.title()} account @{username} already connected")
            
            # Create account document
            account_data = {
                'user_id': user_id,
                'platform': platform,
                'account_type': 'public',
                'username': username,
                'display_name': f"@{username}",
                'is_active': True,
                'connected_at': datetime.now(timezone.utc),
                'last_sync': None,
                'posts_count': 0,
                'status': 'active'
            }
            
            # Save to Firestore
            doc_ref = self.db.collection('user_social_accounts').add(account_data)
            account_data['id'] = doc_ref[1].id
            
            logger.info(f"Added public {platform} account @{username} for user {user_id}")
            
            # Remove sensitive fields before returning
            return {k: v for k, v in account_data.items() 
                   if k not in ['encrypted_access_token', 'encrypted_refresh_token']}
            
        except Exception as e:
            logger.error(f"Error adding public account: {str(e)}")
            raise e
    
    def remove_account(self, user_id, account_id):
        """
        Remove a social account (soft delete).
        
        Args:
            user_id: Firebase user ID
            account_id: Account document ID
        """
        try:
            account_ref = self.db.collection('user_social_accounts').document(account_id)
            account = account_ref.get()
            
            if not account.exists:
                raise ValueError("Account not found")
            
            account_data = account.to_dict()
            
            # Verify ownership
            if account_data['user_id'] != user_id:
                raise ValueError("Not authorized to remove this account")
            
            # Soft delete by marking inactive
            account_ref.update({
                'is_active': False,
                'removed_at': datetime.now(timezone.utc)
            })
            
            logger.info(f"Removed account {account_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error removing account: {str(e)}")
            raise e
    
    def _get_existing_account(self, user_id, platform, username):
        """Check if account already exists for user."""
        try:
            query = (self.db.collection('user_social_accounts')
                    .where('user_id', '==', user_id)
                    .where('platform', '==', platform)
                    .where('username', '==', username)
                    .where('is_active', '==', True))
            
            docs = list(query.stream())
            return docs[0] if docs else None
            
        except Exception as e:
            logger.error(f"Error checking existing account: {str(e)}")
            return None
    
    def _get_account_by_id(self, account_id):
        """Get account by document ID."""
        try:
            account_ref = self.db.collection('user_social_accounts').document(account_id)
            account = account_ref.get()
            
            if not account.exists:
                return None
            
            account_data = account.to_dict()
            account_data['id'] = account_id
            return account_data
            
        except Exception as e:
            logger.error(f"Error getting account by ID: {str(e)}")
            return None
    
    # ========== OAuth Flow ==========
    
    def initiate_oauth_flow(self, user_id, platform):
        """
        Start secure OAuth flow with state parameter.
        
        Args:
            user_id: Firebase user ID
            platform: Social platform (instagram, youtube, twitter)
            
        Returns:
            dict: OAuth URL and state token
        """
        try:
            if platform == 'instagram':
                from services.instagram_oauth_service import get_instagram_oauth_service
                ig_service = get_instagram_oauth_service()
                
                if not ig_service.is_configured():
                    raise ValueError("Instagram OAuth not configured. Please set INSTAGRAM_CLIENT_ID, INSTAGRAM_CLIENT_SECRET, and INSTAGRAM_REDIRECT_URI")
                
                # Generate state token for CSRF protection
                state = secrets.token_urlsafe(32)
                
                # Store state in Firestore with expiration (5 minutes)
                state_ref = self.db.collection('oauth_states').document(state)
                state_ref.set({
                    'user_id': user_id,
                    'platform': platform,
                    'created_at': datetime.now(timezone.utc),
                    'expires_at': datetime.now(timezone.utc) + timedelta(minutes=5)
                })
                
                # Generate authorization URL
                auth_url = ig_service.get_authorization_url(state=state)
                
                logger.info(f"Initiated Instagram OAuth for user {user_id}")
                
                return {
                    'authorization_url': auth_url,
                    'state': state,
                    'platform': platform
                }
            
            elif platform == 'youtube':
                # TODO: Implement YouTube OAuth in future
                raise NotImplementedError("YouTube OAuth not yet implemented")
            
            elif platform == 'twitter':
                # TODO: Implement Twitter OAuth in future
                raise NotImplementedError("Twitter/X OAuth not yet implemented")
            
            else:
                raise ValueError(f"Unsupported platform: {platform}")
                
        except Exception as e:
            logger.error(f"Error initiating OAuth flow: {str(e)}")
            raise e
    
    def handle_oauth_callback(self, platform, code, state):
        """
        Handle OAuth callback and exchange code for tokens.
        
        Args:
            platform: Social platform
            code: Authorization code
            state: State parameter for validation
            
        Returns:
            dict: Account data including account_id
        """
        try:
            # Validate state token
            state_ref = self.db.collection('oauth_states').document(state)
            state_doc = state_ref.get()
            
            if not state_doc.exists:
                raise ValueError("Invalid or expired state token")
            
            state_data = state_doc.to_dict()
            
            # Check expiration
            if datetime.now(timezone.utc) > state_data['expires_at']:
                state_ref.delete()
                raise ValueError("State token expired")
            
            # Verify platform matches
            if state_data['platform'] != platform:
                raise ValueError("Platform mismatch")
            
            user_id = state_data['user_id']
            
            # Platform-specific token exchange
            if platform == 'instagram':
                result = self._handle_instagram_oauth(user_id, code)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Delete used state token
            state_ref.delete()
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {str(e)}")
            raise e
    
    def _handle_instagram_oauth(self, user_id, code):
        """
        Handle Instagram OAuth token exchange and account creation.
        
        Args:
            user_id: Firebase user ID
            code: Authorization code
            
        Returns:
            dict: Account data
        """
        from services.instagram_oauth_service import get_instagram_oauth_service
        ig_service = get_instagram_oauth_service()
        
        # Exchange code for short-lived token
        token_data = ig_service.exchange_code_for_token(code)
        short_lived_token = token_data['access_token']
        instagram_user_id = token_data['user_id']
        
        # Exchange for long-lived token (60 days)
        long_lived_data = ig_service.get_long_lived_token(short_lived_token)
        access_token = long_lived_data['access_token']
        expires_in = long_lived_data['expires_in']  # Seconds
        
        # Get user profile
        profile = ig_service.get_user_profile(access_token)
        username = profile['username']
        
        # Check if account already exists
        existing = self._get_existing_account(user_id, 'instagram', username)
        if existing:
            # Update existing account
            account_id = existing.id
            account_ref = self.db.collection('user_social_accounts').document(account_id)
            
            account_ref.update({
                'encrypted_access_token': self._encrypt_token(access_token),
                'token_expires_at': datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                'instagram_user_id': instagram_user_id,
                'account_type': 'oauth',
                'is_active': True,
                'connected_at': datetime.now(timezone.utc),
                'status': 'active'
            })
            
            logger.info(f"Updated existing Instagram account @{username} for user {user_id}")
        else:
            # Create new account
            account_data = {
                'user_id': user_id,
                'platform': 'instagram',
                'account_type': 'oauth',
                'username': username,
                'display_name': f"@{username}",
                'instagram_user_id': instagram_user_id,
                'encrypted_access_token': self._encrypt_token(access_token),
                'token_expires_at': datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                'is_active': True,
                'connected_at': datetime.now(timezone.utc),
                'last_sync': None,
                'posts_count': 0,
                'status': 'active',
                'profile_url': f"https://instagram.com/{username}"
            }
            
            doc_ref = self.db.collection('user_social_accounts').add(account_data)
            account_id = doc_ref[1].id
            
            logger.info(f"Created new Instagram OAuth account @{username} for user {user_id}")
        
        # Return safe account data
        return {
            'account_id': account_id,
            'platform': 'instagram',
            'username': username,
            'account_type': 'oauth'
        }
    
    def _encrypt_token(self, token):
        """Encrypt access token for storage."""
        return self.cipher_suite.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token):
        """Decrypt access token from storage."""
        return self.cipher_suite.decrypt(encrypted_token.encode()).decode()
    
    # ========== Post Fetching (Phase 4+) ==========
    
    def get_user_posts(self, user_id, limit=50, platform_filter=None):
        """
        Get posts from all connected accounts.
        
        Args:
            user_id: Firebase user ID
            limit: Maximum number of posts to return
            platform_filter: Optional platform to filter by
            
        Returns:
            list: List of post dictionaries
        """
        try:
            posts_ref = self.db.collection('social_posts')
            query = posts_ref.where('user_id', '==', user_id)
            
            if platform_filter:
                query = query.where('platform', '==', platform_filter)
            
            # Sort by posted_at descending (newest first)
            query = query.order_by('posted_at', direction=firestore.Query.DESCENDING)
            
            # Apply limit
            query = query.limit(limit)
            
            posts = []
            for doc in query.stream():
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                posts.append(post_data)
            
            logger.info(f"Retrieved {len(posts)} posts for user {user_id}")
            return posts
            
        except Exception as e:
            logger.error(f"Error getting user posts: {str(e)}")
            raise e
    
    def sync_account_posts(self, account_id, max_posts=12):
        """
        Sync posts for a specific account.
        
        Args:
            account_id: Account document ID
            max_posts: Maximum number of posts to fetch (default 12)
            
        Returns:
            dict: Result with posts_fetched count and any errors
        """
        try:
            # Get account details
            account = self._get_account_by_id(account_id)
            if not account:
                raise ValueError("Account not found")
            
            platform = account['platform']
            username = account['username']
            user_id = account['user_id']
            account_type = account.get('account_type', 'public')
            
            logger.info(f"Starting sync for {platform} account @{username} (type: {account_type})")
            
            # Platform-specific sync
            if platform == 'instagram':
                result = self._sync_instagram_posts(account, max_posts)
            elif platform == 'youtube':
                # TODO: Implement YouTube sync in future
                raise NotImplementedError("YouTube sync not yet implemented")
            elif platform == 'twitter':
                # TODO: Implement Twitter sync in future
                raise NotImplementedError("Twitter/X sync not yet implemented")
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Update account last_sync time
            account_ref = self.db.collection('user_social_accounts').document(account_id)
            account_ref.update({
                'last_sync': datetime.now(timezone.utc),
                'posts_count': result.get('posts_fetched', 0),
                'status': 'active'
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error syncing account {account_id}: {str(e)}")
            # Update account status
            try:
                account_ref = self.db.collection('user_social_accounts').document(account_id)
                account_ref.update({
                    'status': 'error',
                    'error_message': str(e)
                })
            except:
                pass
            raise e
    
    def _sync_instagram_posts(self, account, max_posts=12):
        """
        Fetch Instagram posts using OAuth or fallback to public scraping.
        
        Args:
            account: Account dictionary with all fields
            max_posts: Maximum posts to fetch
            
        Returns:
            dict: Result with posts_fetched count
        """
        account_id = account['id']
        user_id = account['user_id']
        username = account['username']
        account_type = account.get('account_type', 'public')
        
        # Try OAuth first if available
        if account_type == 'oauth' and 'encrypted_access_token' in account:
            try:
                return self._sync_instagram_oauth(account, max_posts)
            except Exception as oauth_error:
                logger.warning(f"OAuth sync failed for @{username}: {str(oauth_error)}")
                logger.info(f"Falling back to public scraping for @{username}")
                # Fall through to public scraping
        
        # Fallback to public scraping (for public accounts or OAuth failure)
        return self._sync_instagram_public(account, max_posts)
    
    def _sync_instagram_oauth(self, account, max_posts=12):
        """
        Fetch Instagram posts using OAuth token.
        
        Args:
            account: Account dictionary with encrypted_access_token
            max_posts: Maximum posts to fetch
            
        Returns:
            dict: Result with posts_fetched count
        """
        from services.instagram_oauth_service import get_instagram_oauth_service
        
        account_id = account['id']
        user_id = account['user_id']
        username = account['username']
        
        # Decrypt access token
        encrypted_token = account['encrypted_access_token']
        access_token = self._decrypt_token(encrypted_token)
        
        # Check if token is expired and refresh if needed
        token_expires_at = account.get('token_expires_at')
        if token_expires_at and datetime.now(timezone.utc) > token_expires_at - timedelta(days=7):
            logger.info(f"Token expiring soon for @{username}, refreshing...")
            try:
                ig_service = get_instagram_oauth_service()
                refresh_data = ig_service.refresh_access_token(access_token)
                access_token = refresh_data['access_token']
                
                # Update stored token
                account_ref = self.db.collection('user_social_accounts').document(account_id)
                account_ref.update({
                    'encrypted_access_token': self._encrypt_token(access_token),
                    'token_expires_at': datetime.now(timezone.utc) + timedelta(seconds=refresh_data['expires_in'])
                })
            except Exception as e:
                logger.error(f"Failed to refresh token: {str(e)}")
                raise e
        
        # Fetch media using OAuth
        ig_service = get_instagram_oauth_service()
        media_items = ig_service.get_user_media(access_token, limit=max_posts)
        
        # Save posts to Firestore
        posts_fetched = 0
        posts_ref = self.db.collection('social_posts')
        
        for media in media_items:
            # Check if post already exists
            existing_query = (posts_ref
                            .where('account_id', '==', account_id)
                            .where('post_id', '==', media['id'])
                            .limit(1))
            
            if list(existing_query.stream()):
                continue  # Skip existing posts
            
            # Prepare post data
            post_data = {
                'user_id': user_id,
                'account_id': account_id,
                'platform': 'instagram',
                'post_id': media['id'],
                'username': username,
                'media_type': media.get('media_type', 'IMAGE').lower(),
                'media_url': media.get('media_url'),
                'thumbnail_url': media.get('thumbnail_url'),
                'permalink': media.get('permalink'),
                'caption': media.get('caption', ''),
                'posted_at': datetime.fromisoformat(media['timestamp'].replace('Z', '+00:00')),
                'fetched_at': datetime.now(timezone.utc),
                'likes_count': None,  # Not available in Basic Display API
                'comments_count': None,  # Not available in Basic Display API
                'is_video': media.get('media_type') == 'VIDEO'
            }
            
            # Save to Firestore
            posts_ref.add(post_data)
            posts_fetched += 1
        
        logger.info(f"Fetched {posts_fetched} new posts for @{username} via OAuth")
        
        return {
            'posts_fetched': posts_fetched,
            'method': 'oauth',
            'success': True
        }
    
    def _sync_instagram_public(self, account, max_posts=12):
        """
        Fetch Instagram posts via public scraping (instaloader).
        
        Args:
            account: Account dictionary
            max_posts: Maximum posts to fetch
            
        Returns:
            dict: Result with posts_fetched count
        """
        account_id = account['id']
        user_id = account['user_id']
        username = account['username']
        
        try:
            import instaloader
            
            # Initialize Instaloader
            L = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False
            )
            
            # Get profile
            try:
                profile = instaloader.Profile.from_username(L.context, username)
            except instaloader.exceptions.ProfileNotExistsException:
                raise ValueError(f"Instagram profile @{username} not found")
            except instaloader.exceptions.PrivateProfileNotFollowedException:
                raise ValueError(f"Instagram profile @{username} is private")
            
            # Fetch posts
            posts_fetched = 0
            posts_ref = self.db.collection('social_posts')
            
            for post in profile.get_posts():
                if posts_fetched >= max_posts:
                    break
                
                # Check if post already exists
                existing_query = (posts_ref
                                .where('account_id', '==', account_id)
                                .where('post_id', '==', post.shortcode)
                                .limit(1))
                
                if list(existing_query.stream()):
                    logger.info(f"Post {post.shortcode} already exists, skipping")
                    continue
                
                # Determine media type
                media_type = 'carousel' if post.typename == 'GraphSidecar' else \
                            'video' if post.is_video else 'image'
                
                # Get media URLs
                media_urls = []
                if post.typename == 'GraphSidecar':
                    # Carousel post
                    for node in post.get_sidecar_nodes():
                        if node.is_video:
                            media_urls.append(node.video_url)
                        else:
                            media_urls.append(node.display_url)
                else:
                    # Single image or video
                    if post.is_video:
                        media_urls.append(post.video_url)
                    else:
                        media_urls.append(post.url)
                
                # Create post document
                post_data = {
                    'user_id': user_id,
                    'account_id': account_id,
                    'platform': 'instagram',
                    'post_id': post.shortcode,
                    'post_url': f"https://www.instagram.com/p/{post.shortcode}/",
                    'content': post.caption if post.caption else '',
                    'media_urls': media_urls,
                    'media_type': media_type,
                    'thumbnail_url': post.url,
                    'posted_at': post.date_utc,
                    'fetched_at': datetime.now(timezone.utc),
                    'engagement': {
                        'likes': post.likes,
                        'comments': post.comments,
                        'shares': 0,  # Instagram API doesn't provide shares
                        'views': post.video_view_count if post.is_video else 0
                    },
                    # Future fields for Creator Portfolio (Phase 10+)
                    'short_code': None,
                    'share_url': None,
                    'is_featured': False,
                    'is_hidden': False,
                    'portfolio_order': 0,
                    'phoenix_clicks': 0,
                    'phoenix_views': 0,
                    'last_clicked_at': None
                }
                
                # Save to Firestore
                posts_ref.add(post_data)
                posts_fetched += 1
                
                logger.info(f"Fetched Instagram post {post.shortcode} ({posts_fetched}/{max_posts})")
            
            logger.info(f"Successfully synced {posts_fetched} Instagram posts for @{username}")
            
            return {
                'success': True,
                'posts_fetched': posts_fetched,
                'message': f'Successfully synced {posts_fetched} posts'
            }
            
        except Exception as e:
            logger.error(f"Error syncing Instagram posts: {str(e)}")
            raise e
    
    # ========== Token Management (Phase 6+) ==========
    
    def _get_valid_access_token(self, account_id):
        """Get a valid access token, refreshing if necessary."""
        # Will be implemented in Phase 6
        raise NotImplementedError("Token management will be implemented in Phase 6")
    
    def _encrypt_token(self, token):
        """Encrypt a token for storage."""
        if not token:
            return None
        return self.cipher_suite.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token):
        """Decrypt a stored token."""
        if not encrypted_token:
            return None
        return self.cipher_suite.decrypt(encrypted_token.encode()).decode()
