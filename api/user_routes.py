"""Routes for user profile management and username operations."""
import logging
from flask import Blueprint, request, session, jsonify
from api.auth_routes import login_required
from services.user_service import (
    UserService,
    UsernameValidationError,
    UsernameTakenError
)

logger = logging.getLogger(__name__)

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
    user_id = session.get('user_id')

    if not user_id:
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
        200: { success: true, user: {...}, isOwnProfile: boolean }
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
        is_own_profile = False
        
        if current_user_id:
            # Compare Firebase UID
            is_own_profile = (user_data.get('firebase_uid') == current_user_id)

        # Return public profile (hide sensitive data)
        return jsonify({
            'success': True,
            'isOwnProfile': is_own_profile,
            'user': {
                'username': user_data.get('username'),
                'displayName': user_data.get('displayName'),
                'bio': user_data.get('bio'),
                'profileImageUrl': user_data.get('profileImageUrl'),
                'totalTokensEarned': user_data.get('totalTokensEarned', 0)
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
