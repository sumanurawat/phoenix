"""User Profile Management Service

Manages user identities, profiles, and username uniqueness.
Handles username claims with atomic operations to prevent race conditions.

Features:
- Unique username registration (atomic)
- Username availability checking
- User profile CRUD operations
- Username lookup (find user by username)
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Dict, Any
from google.cloud import firestore
from firebase_admin import firestore as admin_firestore

logger = logging.getLogger(__name__)


class UsernameValidationError(Exception):
    """Raised when username fails validation rules."""
    pass


class UsernameTakenError(Exception):
    """Raised when attempting to claim an already-taken username."""
    pass


class UserService:
    """
    Service for managing user profiles and usernames.

    Implements the Instagram-style username uniqueness pattern:
    - Separate 'usernames' collection as a lookup table
    - Document IDs are lowercase usernames
    - Atomic transactions prevent race conditions
    """

    def __init__(self, db: firestore.Client = None):
        """
        Initialize user service.

        Args:
            db: Firestore client instance (uses default if not provided)
        """
        self.db = db or admin_firestore.client()
        self.users_collection = 'users'
        self.usernames_collection = 'usernames'
        logger.info("UserService initialized")

    def validate_username(self, username: str) -> str:
        """
        Validate username format and return normalized version.

        Rules:
        - 3-20 characters
        - Alphanumeric, underscores, dots only
        - Must start with letter or number
        - Cannot end with dot
        - No consecutive dots or underscores

        Args:
            username: Proposed username

        Returns:
            Normalized username (original casing preserved)

        Raises:
            UsernameValidationError: If validation fails
        """
        if not username:
            raise UsernameValidationError("Username is required")

        # Strip whitespace
        username = username.strip()

        # Length check
        if len(username) < 3:
            raise UsernameValidationError("Username must be at least 3 characters")
        if len(username) > 20:
            raise UsernameValidationError("Username must be 20 characters or less")

        # Character validation
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._]*$', username):
            raise UsernameValidationError(
                "Username must start with a letter or number and contain only "
                "letters, numbers, dots, and underscores"
            )

        # Cannot end with dot
        if username.endswith('.'):
            raise UsernameValidationError("Username cannot end with a dot")

        # No consecutive special chars
        if '..' in username or '__' in username or '._' in username or '_.' in username:
            raise UsernameValidationError("Username cannot contain consecutive dots or underscores")

        # Reserved usernames
        reserved = {'admin', 'root', 'system', 'phoenix', 'api', 'www', 'support', 'help'}
        if username.lower() in reserved:
            raise UsernameValidationError("This username is reserved")

        return username

    def check_username_availability(self, username: str) -> bool:
        """
        Check if a username is available (non-atomic, use for UI hints).

        Args:
            username: Username to check (will be lowercased)

        Returns:
            True if available, False if taken
        """
        try:
            # Validate first
            self.validate_username(username)

            # Check lookup table
            username_lower = username.lower()
            doc_ref = self.db.collection(self.usernames_collection).document(username_lower)
            return not doc_ref.get().exists

        except UsernameValidationError:
            return False
        except Exception as e:
            logger.error(f"Error checking username availability: {e}", exc_info=True)
            return False

    def _claim_username_in_transaction(
        self,
        transaction: firestore.Transaction,
        user_id: str,
        username: str
    ) -> None:
        """
        Atomic transaction logic to claim a username.

        This runs inside a Firestore transaction to prevent race conditions.
        Called by the @transactional decorated wrapper.

        Args:
            transaction: Firestore transaction object
            user_id: Firebase Auth UID
            username: Username to claim (already validated)

        Raises:
            UsernameTakenError: If username is already claimed
        """
        username_lower = username.lower()

        # 1. Get user's current username (if any) to release it
        user_ref = self.db.collection(self.users_collection).document(user_id)
        user_doc = user_ref.get(transaction=transaction)

        old_username_lower = None
        if user_doc.exists:
            user_data = user_doc.to_dict()
            old_username_lower = user_data.get('usernameLower')

        # 2. Check if new username is available (unless it's the same as current)
        username_ref = self.db.collection(self.usernames_collection).document(username_lower)
        username_doc = username_ref.get(transaction=transaction)

        if username_doc.exists:
            # Check if it's claimed by a different user
            claimed_user_id = username_doc.to_dict().get('userId')
            if claimed_user_id != user_id:
                raise UsernameTakenError(f"Username '{username}' is already taken")
            # If it's the same user, we're just updating (no-op on username)

        # 3. Delete old username claim (if user had a different username before)
        if old_username_lower and old_username_lower != username_lower:
            old_username_ref = self.db.collection(self.usernames_collection).document(old_username_lower)
            transaction.delete(old_username_ref)
            logger.info(f"Released old username claim: {old_username_lower}")

        # 4. Create new username claim
        transaction.set(username_ref, {
            'userId': user_id,
            'claimedAt': admin_firestore.SERVER_TIMESTAMP
        })

        # 5. Update user document
        transaction.set(user_ref, {
            'username': username,  # Preserve original casing
            'usernameLower': username_lower,
            'updatedAt': admin_firestore.SERVER_TIMESTAMP
        }, merge=True)

    def set_username(self, user_id: str, username: str) -> Dict[str, Any]:
        """
        Set or update a user's username (atomic operation).

        Args:
            user_id: Firebase Auth UID
            username: Desired username

        Returns:
            User document data with new username

        Raises:
            UsernameValidationError: If username format is invalid
            UsernameTakenError: If username is already claimed
        """
        if not user_id:
            raise ValueError("user_id is required")

        # Validate username format
        validated_username = self.validate_username(username)

        # Check if user already has this username (case-insensitive)
        user_ref = self.db.collection(self.users_collection).document(user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            current_username = user_data.get('username')
            if current_username and current_username.lower() == validated_username.lower():
                logger.info(f"User {user_id} already has username '{validated_username}'")
                return user_data

        try:
            # Define transactional function that captures user_id and validated_username
            @admin_firestore.transactional
            def claim_username_transaction(transaction):
                """Inner transactional function."""
                self._claim_username_in_transaction(transaction, user_id, validated_username)

            # Run atomic transaction
            transaction = self.db.transaction()
            claim_username_transaction(transaction)

            logger.info(f"User {user_id} claimed username '{validated_username}'")

            # Return updated user data
            return user_ref.get().to_dict()

        except UsernameTakenError:
            logger.warning(f"Username claim failed - already taken: {validated_username}")
            raise
        except Exception as e:
            logger.error(f"Failed to set username for user {user_id}: {e}", exc_info=True)
            raise

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by their username.

        Args:
            username: Username to look up (case-insensitive)

        Returns:
            User document data or None if not found
        """
        try:
            username_lower = username.lower()

            # Look up username claim
            username_ref = self.db.collection(self.usernames_collection).document(username_lower)
            username_doc = username_ref.get()

            if not username_doc.exists:
                return None

            # Get user ID from claim
            user_id = username_doc.get('userId')
            if not user_id:
                logger.error(f"Username document '{username}' missing userId field")
                return None

            # Fetch user document
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
                logger.error(f"User {user_id} not found for username '{username}'")
                return None

            return user_doc.to_dict()

        except Exception as e:
            logger.error(f"Error looking up username '{username}': {e}", exc_info=True)
            return None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile by Firebase UID.

        Args:
            user_id: Firebase Auth UID

        Returns:
            User document data or None if not found
        """
        try:
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
                return None

            return user_doc.to_dict()

        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}", exc_info=True)
            return None

    def update_profile(
        self,
        user_id: str,
        bio: Optional[str] = None,
        display_name: Optional[str] = None,
        profile_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user profile fields (non-username fields).

        Args:
            user_id: Firebase Auth UID
            bio: User bio/description
            display_name: Display name (different from username)
            profile_image_url: URL to profile image

        Returns:
            Updated user document data
        """
        if not user_id:
            raise ValueError("user_id is required")

        try:
            user_ref = self.db.collection(self.users_collection).document(user_id)

            update_data = {
                'updatedAt': admin_firestore.SERVER_TIMESTAMP
            }

            if bio is not None:
                update_data['bio'] = bio.strip() if bio else ""

            if display_name is not None:
                update_data['displayName'] = display_name.strip() if display_name else ""

            if profile_image_url is not None:
                update_data['profileImageUrl'] = profile_image_url.strip() if profile_image_url else ""

            user_ref.set(update_data, merge=True)

            logger.info(f"Updated profile for user {user_id}")

            return user_ref.get().to_dict()

        except Exception as e:
            logger.error(f"Failed to update profile for user {user_id}: {e}", exc_info=True)
            raise
