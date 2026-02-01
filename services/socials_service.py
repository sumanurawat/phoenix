"""
Social Media Service

Handles social media account connections and post fetching.
Supports Instagram via public scraping (instaloader).

Note: OAuth-based connections have been removed. All syncing uses public scraping.
"""
import logging
from datetime import datetime, timezone
from firebase_admin import firestore

logger = logging.getLogger(__name__)


class SocialsService:
    """Service for managing social media account connections and posts.

    Note: OAuth-based connections have been removed. All social media
    syncing now uses public scraping via instaloader for Instagram.
    """

    def __init__(self):
        """Initialize the socials service."""
        self.db = firestore.client()
    
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
    
    # ========== OAuth Flow (Removed - Using Public Scraping Only) ==========
    # Note: Instagram OAuth was removed as the service is no longer maintained.
    # All Instagram syncing now uses public scraping via instaloader.

    def initiate_oauth_flow(self, user_id, platform):
        """
        OAuth flow is not currently supported.
        Use add_public_account() to connect accounts via public scraping.
        """
        raise NotImplementedError(
            f"{platform.title()} OAuth is not currently supported. "
            "Please use public account connection instead."
        )

    def handle_oauth_callback(self, platform, code, state):
        """
        OAuth callback is not currently supported.
        """
        raise NotImplementedError(
            f"{platform.title()} OAuth is not currently supported. "
            "Please use public account connection instead."
        )
    
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
        Fetch Instagram posts using public scraping (instaloader).

        Args:
            account: Account dictionary with all fields
            max_posts: Maximum posts to fetch

        Returns:
            dict: Result with posts_fetched count
        """
        # All Instagram syncing uses public scraping
        return self._sync_instagram_public(account, max_posts)
    
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
    
