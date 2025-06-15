"""
Membership API Routes

Provides endpoints for clients to query user membership status.
"""
from flask import Blueprint, jsonify, current_app, session as flask_session # Renamed to avoid conflict with other 'session' variables
from functools import wraps # For login_required decorator
import logging

from services.membership_service import MembershipService

# Placeholder for authentication - User needs to implement these
# based on their Firebase Authentication setup.
# These are similar to the placeholders in api/stripe_routes.py for consistency.
def get_current_user_id():
    """
    Placeholder: Returns the current authenticated user's ID.
    User should implement this to retrieve user ID from session or token.
    Example: return flask_session.get('user_id')
    """
    user_id = flask_session.get('user_id')
    if not user_id:
        # Use current_app.logger if available and configured, otherwise basic logging
        logger = current_app.logger if hasattr(current_app, 'logger') and current_app.logger else logging.getLogger(__name__)
        logger.warning("get_current_user_id: user_id not found in session.")
    return user_id

def login_required(f):
    """
    Placeholder: Decorator to ensure the user is logged in.
    User should replace this with their actual login_required decorator
    from their authentication system.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in flask_session: # or however user session is identified
            logger = current_app.logger if hasattr(current_app, 'logger') and current_app.logger else logging.getLogger(__name__)
            logger.warning("Access denied: User not logged in for membership status check.")
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

membership_bp = Blueprint('membership_api', __name__, url_prefix='/api/membership')

@membership_bp.route('/status', methods=['GET'])
@login_required # Apply your authentication decorator
def get_membership_status():
    """
    Retrieves the current authenticated user's membership status.
    """
    logger = current_app.logger if hasattr(current_app, 'logger') and current_app.logger else logging.getLogger(__name__)

    user_id = get_current_user_id()

    if not user_id:
        # This should ideally be caught by @login_required if it's robust.
        # If get_current_user_id can return None even after @login_required,
        # this is an additional safeguard.
        logger.error("get_membership_status: No user_id available even after login_required. Auth setup might be incomplete.")
        return jsonify({"error": "User identification failed after login."}), 403 # Forbidden or Internal Server Error

    try:
        membership_service = MembershipService()
        membership_data = membership_service.get_user_membership(user_id)

        # The get_user_membership method already returns a default 'free' structure
        # if the user is not found in Firestore, so we don't need special handling for that here.
        # It includes the 'userId' in the returned dict.

        logger.info(f"Successfully retrieved membership status for user {user_id}. Tier: {membership_data.get('currentTier')}")
        return jsonify(membership_data), 200

    except ConnectionError as ce: # If MembershipService failed to init Firestore or Stripe
        logger.error(f"Connection error while retrieving membership status for user {user_id}: {ce}")
        return jsonify({"error": "Service initialization failed. Please try again later."}), 503
    except Exception as e:
        logger.error(f"Unexpected error retrieving membership status for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred while fetching membership status."}), 500

# Ensure current_app.logger is configured in your main app.py.
# If not, basic logging is used as a fallback.
# Flask session usage here assumes it's initialized and populated by your auth system.
```
