"""Routes for user profile management and username operations."""
import logging
import os
import uuid as uuid_module
from flask import Blueprint, request, session, jsonify
from api.auth_routes import login_required
from services.user_service import (
    UserService,
    UsernameValidationError,
    UsernameTakenError
)
from services.account_deletion_service import get_deletion_service, AccountDeletionError

logger = logging.getLogger(__name__)

# Instance ID for tracking which Cloud Run instance handles requests
INSTANCE_ID = os.getenv('K_REVISION', 'local')[:20]
CONTAINER_ID = uuid_module.uuid4().hex[:8]

user_bp = Blueprint('user', __name__)
user_service = UserService()


@user_bp.route('/api/users/check-username', methods=['GET'])
def check_username_availability():
    """
    Check if a username is available.

    Query params:
        username: Username to check

    Returns:
        200: { available: true/false, message: "..." }
        400: Invalid request
    """
    username = request.args.get('username', '').strip()

    if not username:
        return jsonify({
            'error': 'Username parameter is required'
        }), 400

    try:
        # Validate format
        user_service.validate_username(username)

        # Check availability
        available = user_service.check_username_availability(username)

        if available:
            return jsonify({
                'available': True,
                'message': f'Username "{username}" is available'
            })
        else:
            return jsonify({
                'available': False,
                'message': f'Username "{username}" is already taken'
            })

    except UsernameValidationError as e:
        return jsonify({
            'available': False,
            'message': str(e)
        })
    except Exception as e:
        logger.error(f"Error checking username availability: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to check username availability'
        }), 500


@user_bp.route('/api/users/set-username', methods=['POST'])
@login_required
def set_username():
    """
    Claim a username for the authenticated user (atomic operation).

    Request body:
        { username: "desired_username" }

    Returns:
        200: { success: true, user: {...} }
        400: Validation error
        409: Username already taken
        500: Server error
    """
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    username = data.get('username', '').strip()

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    try:
        # Atomic username claim
        user_data = user_service.set_username(user_id, username)

        return jsonify({
            'success': True,
            'user': {
                'username': user_data.get('username'),
                'firebase_uid': user_id
            },
            'message': f'Successfully claimed username "{username}"'
        })

    except UsernameValidationError as e:
        return jsonify({
            'error': str(e)
        }), 400

    except UsernameTakenError as e:
        return jsonify({
            'error': str(e)
        }), 409

    except Exception as e:
        logger.error(f"Error setting username for user {user_id}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to set username'
        }), 500


@user_bp.route('/api/users/me', methods=['GET'])
@login_required
def get_current_user():
    """
    Get the authenticated user's profile.

    Returns:
        200: { user: {...} }
        404: User not found
        500: Server error
    """
    # Debug logging for session issues
    all_cookies = list(request.cookies.keys())
    session_cookie = request.cookies.get('__session') or request.cookies.get('session')
    request_id = uuid_module.uuid4().hex[:8]
    
    logger.info(f"[users/me:{request_id}] Request received | instance={INSTANCE_ID}/{CONTAINER_ID}")
    logger.info(f"[users/me:{request_id}] Cookies: {all_cookies} | __session={'present' if session_cookie else 'MISSING'}")
    logger.info(f"[users/me:{request_id}] Session keys: {list(session.keys())} | user_id={session.get('user_id', 'NONE')}")
    logger.info(f"[users/me:{request_id}] Headers - Host: {request.headers.get('Host')} | Origin: {request.headers.get('Origin')}")
    
    user_id = session.get('user_id')

    if not user_id:
        logger.warning(f"[users/me:{request_id}] No user_id in session - returning 401")
        return jsonify({'error': 'User not authenticated'}), 401

    try:
        user_data = user_service.get_user(user_id)

        if not user_data:
            return jsonify({'error': 'User not found'}), 404

        # Return user profile
        return jsonify({
            'success': True,  # ADDED: Missing success flag
            'user': {
                'firebase_uid': user_id,
                'username': user_data.get('username'),
                'email': user_data.get('email'),
                'displayName': user_data.get('displayName'),
                'bio': user_data.get('bio'),
                'profileImageUrl': user_data.get('profileImageUrl'),
                'tokenBalance': user_data.get('tokenBalance', 0),
                'totalTokensEarned': user_data.get('totalTokensEarned', 0),
                'createdAt': user_data.get('createdAt'),
                'updatedAt': user_data.get('updatedAt')
            }
        })

    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch user profile'
        }), 500


@user_bp.route('/api/users/<username>', methods=['GET'])
def get_user_by_username(username):
    """
    Get a user's public profile by username.

    Path params:
        username: Username to look up

    Returns:
        200: { success: true, user: {...}, isOwnProfile: boolean, isFollowing: boolean }
        404: User not found
        500: Server error
    """
    try:
        user_data = user_service.get_user_by_username(username)

        if not user_data:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Check if viewing own profile
        current_user_id = session.get('user_id')
        target_user_id = user_data.get('firebase_uid')
        is_own_profile = False
        is_following = False
        
        if current_user_id:
            # Compare Firebase UID
            is_own_profile = (target_user_id == current_user_id)
            
            # Check if current user follows this profile (only if not own profile)
            if not is_own_profile and target_user_id:
                from services.follow_service import get_follow_service
                follow_service = get_follow_service()
                is_following = follow_service.is_following(current_user_id, target_user_id)

        # Return public profile (hide sensitive data)
        return jsonify({
            'success': True,
            'isOwnProfile': is_own_profile,
            'isFollowing': is_following,
            'user': {
                'username': user_data.get('username'),
                'displayName': user_data.get('displayName'),
                'bio': user_data.get('bio'),
                'profileImageUrl': user_data.get('profileImageUrl'),
                'totalTokensEarned': user_data.get('totalTokensEarned', 0),
                'followersCount': user_data.get('followersCount', 0),
                'followingCount': user_data.get('followingCount', 0)
                # Note: tokenBalance is private (not included)
            }
        })

    except Exception as e:
        logger.error(f"Error fetching user by username '{username}': {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch user profile'
        }), 500


@user_bp.route('/api/users/me/profile', methods=['PATCH'])
@login_required
def update_profile():
    """
    Update the authenticated user's profile (bio, display name, etc).

    Request body:
        {
            bio?: "User bio",
            displayName?: "Display Name",
            profileImageUrl?: "https://..."
        }

    Returns:
        200: { success: true, user: {...} }
        400: Invalid request
        500: Server error
    """
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    try:
        # Update profile
        user_data = user_service.update_profile(
            user_id=user_id,
            bio=data.get('bio'),
            display_name=data.get('displayName'),
            profile_image_url=data.get('profileImageUrl')
        )

        return jsonify({
            'success': True,
            'user': {
                'firebase_uid': user_id,
                'username': user_data.get('username'),
                'displayName': user_data.get('displayName'),
                'bio': user_data.get('bio'),
                'profileImageUrl': user_data.get('profileImageUrl')
            },
            'message': 'Profile updated successfully'
        })

    except Exception as e:
        logger.error(f"Error updating profile for user {user_id}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to update profile'
        }), 500


@user_bp.route('/api/users/me', methods=['DELETE'])
@login_required
def delete_account():
    """
    Delete the authenticated user's account and all associated data.

    This permanently deletes:
    - User profile
    - All creations (images/videos)
    - All transactions
    - Social media connections
    - Comments on other users' creations
    - Session data
    - Username (becomes available for others)

    Returns:
        200: { success: true, message: "...", summary: {...} }
        401: Not authenticated
        500: Deletion failed
    """
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User not authenticated'
        }), 401

    logger.warning(f"Account deletion requested by user: {user_id}")

    try:
        # Get deletion service
        deletion_service = get_deletion_service()

        # First, get summary of what will be deleted
        summary = deletion_service.get_user_data_summary(user_id)

        if not summary.get('exists'):
            return jsonify({
                'success': False,
                'error': 'User account not found'
            }), 404

        # Perform the deletion
        result = deletion_service.delete_account(user_id)

        # Clear the session
        session.clear()

        if result['success']:
            logger.info(
                f"Account deleted successfully: {result.get('username', user_id)} | "
                f"Summary: {result.get('cleanup_summary')}"
            )

            return jsonify({
                'success': True,
                'message': 'Your account and all associated data have been permanently deleted.',
                'summary': result.get('cleanup_summary'),
                'username_released': result.get('username')
            })
        else:
            logger.error(
                f"Account deletion completed with errors for {user_id}: "
                f"{result.get('errors')}"
            )

            return jsonify({
                'success': False,
                'error': 'Account deletion completed with some errors',
                'details': result.get('errors'),
                'partial_summary': result.get('cleanup_summary')
            }), 500

    except AccountDeletionError as e:
        logger.error(f"Account deletion failed for {user_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Account deletion failed: {str(e)}'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error during account deletion for {user_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while deleting your account'
        }), 500


@user_bp.route('/api/users/me/data-summary', methods=['GET'])
@login_required
def get_data_summary():
    """
    Get a summary of all data associated with the current user's account.
    Useful for showing users what will be deleted before account deletion.

    Returns:
        200: {
            success: true,
            summary: {
                user_id: string,
                username: string,
                data_counts: {
                    creations: number,
                    transactions: number,
                    social_accounts: number
                }
            }
        }
        401: Not authenticated
        500: Server error
    """
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User not authenticated'
        }), 401

    try:
        deletion_service = get_deletion_service()
        summary = deletion_service.get_user_data_summary(user_id)

        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        logger.error(f"Error getting data summary for {user_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get data summary'
        }), 500
