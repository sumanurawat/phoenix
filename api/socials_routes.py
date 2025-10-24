"""
Social Media API Routes

Handles API endpoints for social media account management and timeline features.
"""
import logging
from flask import Blueprint, request, jsonify, session
from middleware.csrf_protection import csrf_protect
from api.auth_routes import login_required
from services.socials_service import SocialsService

logger = logging.getLogger(__name__)

socials_bp = Blueprint('socials', __name__, url_prefix='/api/socials')
socials_service = SocialsService()


@socials_bp.route('/accounts', methods=['GET'])
@login_required
def get_accounts():
    """
    Get user's connected social accounts.
    
    Returns:
        JSON with list of accounts (no sensitive data)
    """
    user_id = session.get('user_id')
    
    try:
        accounts = socials_service.get_user_accounts(user_id)
        return jsonify({
            'success': True,
            'accounts': accounts
        })
        
    except Exception as e:
        logger.error(f"Error getting accounts for user {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load accounts'
        }), 500


@socials_bp.route('/accounts', methods=['POST'])
@login_required
@csrf_protect
def add_account():
    """
    Add a new social account (public or OAuth).
    
    Request JSON:
        {
            "platform": "instagram|youtube|twitter",
            "username": "public_username" (for public accounts)
        }
    
    Returns:
        JSON with created account data
    """
    user_id = session.get('user_id')
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body required'
        }), 400
    
    platform = data.get('platform')
    username = data.get('username')
    
    # Validate required fields
    if not platform:
        return jsonify({
            'success': False,
            'error': 'Platform is required'
        }), 400
    
    if not username:
        return jsonify({
            'success': False,
            'error': 'Username is required'
        }), 400
    
    try:
        # For now, only public accounts (Phase 3)
        # OAuth will be added in Phase 6
        account = socials_service.add_public_account(user_id, platform, username)
        
        return jsonify({
            'success': True,
            'account': account,
            'message': f'{platform.title()} account connected successfully'
        })
        
    except ValueError as e:
        # User-facing validation errors
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Error adding account for user {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to add account. Please try again.'
        }), 500


@socials_bp.route('/accounts/<account_id>', methods=['DELETE'])
@login_required
@csrf_protect
def remove_account(account_id):
    """
    Remove a social account.
    
    Args:
        account_id: Account document ID
        
    Returns:
        JSON with success status
    """
    user_id = session.get('user_id')
    
    try:
        socials_service.remove_account(user_id, account_id)
        
        return jsonify({
            'success': True,
            'message': 'Account removed successfully'
        })
        
    except ValueError as e:
        # User-facing validation errors
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Error removing account {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to remove account'
        }), 500


@socials_bp.route('/timeline', methods=['GET'])
@login_required
def get_timeline():
    """
    Get unified timeline of posts from all connected accounts.
    
    Query parameters:
        limit: Max posts to return (default 50)
        platform: Filter by platform (optional)
        
    Returns:
        JSON with list of posts
    """
    user_id = session.get('user_id')
    
    try:
        limit = int(request.args.get('limit', 50))
        platform_filter = request.args.get('platform')
        
        posts = socials_service.get_user_posts(
            user_id,
            limit=limit,
            platform_filter=platform_filter
        )
        
        return jsonify({
            'success': True,
            'posts': posts,
            'count': len(posts)
        })
        
    except Exception as e:
        logger.error(f"Error getting timeline for user {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load timeline'
        }), 500


@socials_bp.route('/accounts/<account_id>/sync', methods=['POST'])
@login_required
@csrf_protect
def sync_account(account_id):
    """
    Manually sync posts for a specific account.
    
    Args:
        account_id: Account document ID
        
    Request JSON (optional):
        max_posts: Maximum posts to fetch (default 12)
        
    Returns:
        JSON with sync status
    """
    user_id = session.get('user_id')
    
    try:
        # Get optional max_posts from request
        data = request.get_json() or {}
        max_posts = data.get('max_posts', 12)
        
        # Validate max_posts
        if not isinstance(max_posts, int) or max_posts < 1 or max_posts > 50:
            return jsonify({
                'success': False,
                'error': 'max_posts must be between 1 and 50'
            }), 400
        
        # Sync posts
        result = socials_service.sync_account_posts(account_id, max_posts=max_posts)
        
        return jsonify({
            'success': True,
            'posts_fetched': result.get('posts_fetched', 0),
            'message': result.get('message', 'Sync completed')
        })
        
    except ValueError as e:
        # User-facing validation errors
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except NotImplementedError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 501
        
    except Exception as e:
        logger.error(f"Error syncing account {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to sync posts. Please try again.'
        }), 500


# OAuth routes (Phase 6+)

@socials_bp.route('/connect/<platform>', methods=['POST'])
@login_required
@csrf_protect
def initiate_connection(platform):
    """
    Start OAuth flow for connecting social account.
    
    Args:
        platform: Social platform to connect
        
    Returns:
        JSON with OAuth URL
    """
    user_id = session.get('user_id')
    
    # Validate platform
    allowed_platforms = ['instagram', 'youtube', 'twitter']
    if platform not in allowed_platforms:
        return jsonify({
            'success': False,
            'error': 'Unsupported platform'
        }), 400
    
    try:
        # Initiate OAuth flow
        oauth_data = socials_service.initiate_oauth_flow(user_id, platform)
        
        return jsonify({
            'success': True,
            'authorization_url': oauth_data['authorization_url'],
            'state': oauth_data['state']
        })
        
    except NotImplementedError as e:
        # Platform OAuth not yet implemented
        return jsonify({
            'success': False,
            'error': str(e)
        }), 501
        
    except ValueError as e:
        # Configuration error
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Error initiating OAuth for {platform}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to start authentication'
        }), 500


@socials_bp.route('/oauth/<platform>/callback')
def oauth_callback(platform):
    """
    Handle OAuth callback from social platforms.
    
    Args:
        platform: Social platform
        
    Query params:
        code: Authorization code
        state: State parameter for validation
        error: OAuth error if denied
    """
    from flask import redirect, url_for
    
    # Check for OAuth errors
    error = request.args.get('error')
    if error:
        error_description = request.args.get('error_description', 'Authentication failed')
        logger.warning(f"OAuth error for {platform}: {error} - {error_description}")
        return redirect(f"/apps/social-gallery?error={error}&error_description={error_description}")
    
    # Get authorization code and state
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        logger.error("Missing code or state parameter in OAuth callback")
        return redirect("/apps/social-gallery?error=missing_parameters")
    
    try:
        # Handle OAuth callback and create/update account
        result = socials_service.handle_oauth_callback(platform, code, state)
        
        logger.info(f"Successfully connected {platform} account: {result.get('username')}")
        
        # Redirect back to social gallery with success
        return redirect(f"/apps/social-gallery?connected={platform}&username={result.get('username')}")
        
    except ValueError as e:
        # Validation errors (invalid state, expired token, etc.)
        logger.error(f"OAuth callback validation error for {platform}: {str(e)}")
        return redirect(f"/apps/social-gallery?error=validation_failed&message={str(e)}")
        
    except Exception as e:
        # Unexpected errors
        logger.error(f"OAuth callback error for {platform}: {str(e)}")
        return redirect(f"/apps/social-gallery?error=oauth_failed")


@socials_bp.route('/accounts/health', methods=['GET'])
@login_required
def check_account_health():
    """
    Check if any accounts need reconnection.
    
    Returns:
        JSON with list of accounts needing reconnection
    """
    user_id = session.get('user_id')
    
    try:
        # Will be implemented in Phase 7
        return jsonify({
            'success': True,
            'needs_reconnection': []
        })
        
    except Exception as e:
        logger.error(f"Error checking account health: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to check account status'
        }), 500
