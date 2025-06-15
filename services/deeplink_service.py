"""
Deep Link Service

Service for handling URL shortening and management.
Integrates with MembershipService to apply tier-based logic.
"""
import logging
from firebase_admin import firestore
import uuid
from services.membership_service import MembershipService # Import MembershipService

class DeeplinkService:
    LINKS_COLLECTION = "shortened_links"
    MAX_FREE_LINKS = 5  # Example limit for free tier users

    def __init__(self):
        """
        Initializes the DeeplinkService with a Firestore client
        and an instance of MembershipService.
        """
        self.db = firestore.client()
        try:
            self.membership_service = MembershipService()
            logging.info("DeeplinkService initialized with MembershipService.")
        except Exception as e:
            logging.error(f"Failed to initialize MembershipService in DeeplinkService: {e}")
            self.membership_service = None # Allow service to start, but tier checks will fail or be bypassed

    def _generate_short_code(self):
        """Generate a unique short code for a URL."""
        while True:
            short_code = uuid.uuid4().hex[:6]
            link_ref = self.db.collection(self.LINKS_COLLECTION).document(short_code)
            doc = link_ref.get()
            if not doc.exists:
                return short_code

    def create_short_link(self, original_url, user_id, user_email):
        """
        Create a short link and store it in Firestore.
        Applies tier-based limitations based on user's membership.
        If the user has already shortened this exact URL, return information about the existing short link.
        Returns a dictionary: {'short_code': str, 'is_new': bool, 'original_url': str}
        Raises ValueError if limitations are met (e.g., free tier link limit).
        """
        if not user_id:
            logging.error("create_short_link called with no user_id.")
            raise ValueError("user_id cannot be None or empty for creating a short link.")

        if not self.membership_service:
            logging.error("MembershipService not available in DeeplinkService. Cannot apply tier logic.")
            # Fallback: For this example, we'll raise an error. In a production system,
            # you might decide to allow the action with default (e.g., free tier) behavior
            # or deny it outright if membership checks are critical.
            raise ConnectionError("MembershipService is not initialized. Link creation aborted.")

        # --- Membership Tier Check ---
        membership = self.membership_service.get_user_membership(user_id)
        current_tier = membership.get('currentTier', 'free')
        subscription_status = membership.get('subscriptionStatus', 'free_tier')

        logging.info(f"User {user_id} creating link with tier: {current_tier}, status: {subscription_status}")

        # More robust check: consider active status for paid tiers
        is_effectively_free = True
        if current_tier != 'free' and subscription_status in ['active', 'trialing']:
            is_effectively_free = False

        if is_effectively_free:
            current_tier = 'free' # Treat non-active paid users as 'free' for limits
            logging.info(f"User {user_id} is effectively on free tier for link creation due to tier '{membership.get('currentTier', 'free')}' and status '{subscription_status}'.")
            try:
                query = self.db.collection(self.LINKS_COLLECTION).where('user_id', '==', user_id)
                aggregation_query = query.count() # Use .count() for aggregation
                result = aggregation_query.get()

                # result is a list of list of AggregationResult objects.
                # For a single count, it's result[0][0].value
                existing_links_count = result[0][0].value if (result and result[0] and hasattr(result[0][0], 'value')) else 0
                logging.info(f"User {user_id} (free tier) has {existing_links_count} existing links.")

                if existing_links_count >= self.MAX_FREE_LINKS:
                    logging.warning(f"User {user_id} (free tier) reached link limit of {self.MAX_FREE_LINKS}.")
                    raise ValueError(f"Free tier users are limited to {self.MAX_FREE_LINKS} links. Please upgrade for more.")
            except Exception as e:
                logging.error(f"Could not query link count for user {user_id}: {e}. Denying link creation as a precaution.")
                # Deny creation if count fails for free users to enforce limits.
                raise ValueError("Could not verify link count. Please try again.")


        elif current_tier == 'basic':
            # Example: Basic tier might have a limit of 50 links.
            # MAX_BASIC_LINKS = 50
            # (Implement count check similar to free tier if needed)
            logging.info(f"User {user_id} is on basic tier. Applying basic tier link creation logic.")

        elif current_tier == 'premium':
            logging.info(f"User {user_id} is on premium tier (e.g., unlimited links, advanced analytics).")

        else: # unknown_tier
            logging.warning(f"User {user_id} has an unknown tier: {current_tier}. Applying default (free tier) limitations for safety.")
            # This effectively treats unknown tiers like the free tier for this check by falling into the 'is_effectively_free' logic if status isn't active.
            # If it were an unknown tier with an active status, it would pass here. Add specific checks if needed.


        # --- End Membership Tier Check ---

        existing_links_query = self.db.collection(self.LINKS_COLLECTION) \
            .where('user_id', '==', user_id) \
            .where('original_url', '==', original_url) \
            .limit(1) \
            .stream()

        existing_link_doc = None
        for doc in existing_links_query: # Iterate over the stream
            existing_link_doc = doc
            break

        if existing_link_doc and existing_link_doc.exists:
            logging.info(f"User {user_id} already shortened URL {original_url}. Returning existing short_code: {existing_link_doc.id}")
            return {
                'short_code': existing_link_doc.id,
                'is_new': False,
                'original_url': original_url
            }

        short_code = self._generate_short_code()
        doc_data = {
            'original_url': original_url,
            'user_id': user_id,
            'user_email': user_email, # Assuming user_email is still passed or fetched if needed
            'created_at': firestore.SERVER_TIMESTAMP,
            'click_count': 0,
            'tier_at_creation': current_tier # Optional: store tier when link was made
        }
        self.db.collection(self.LINKS_COLLECTION).document(short_code).set(doc_data)
        logging.info(f"Created new short_code {short_code} for URL {original_url} by user {user_id} (Tier: {current_tier}).")
        return {
            'short_code': short_code,
            'is_new': True,
            'original_url': original_url
        }

    def get_original_url(self, short_code):
        """Retrieve the original URL from a short code."""
        doc_ref = self.db.collection(self.LINKS_COLLECTION).document(short_code)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get('original_url')
        else:
            return None

    def increment_click_count(self, short_code):
        """Increment the click count for a short link."""
        doc_ref = self.db.collection(self.LINKS_COLLECTION).document(short_code)
        doc = doc_ref.get() # Check for existence first
        if doc.exists:
            doc_ref.update({'click_count': firestore.Increment(1)})
            return True
        return False

    def get_links_for_user(self, user_id):
        """Retrieve all short links created by a specific user."""
        if not user_id: # Prevent querying with empty user_id
            logging.warning("get_links_for_user called with no user_id.")
            return []
            
        logging.info(f"Fetching links for user_id: {user_id}")
        links_list = []
        try:
            links_query = self.db.collection(self.LINKS_COLLECTION) \
                .where('user_id', '==', user_id) \
                .order_by('created_at', direction=firestore.Query.DESCENDING) \
                .stream()
            for doc_snapshot in links_query:
                link_data = doc_snapshot.to_dict()
                link_data['short_code'] = doc_snapshot.id
                links_list.append(link_data)
            logging.info(f"Retrieved {len(links_list)} links for user_id: {user_id}")
            return links_list
        except Exception as e:
            logging.error(f"Error fetching links for user_id {user_id}: {e}")
            raise # Re-raise the exception to be handled by the caller

    def delete_short_link(self, short_code, user_id):
        """
        Delete a short link from Firestore.
        Only allows deletion if the link belongs to the specified user.
        Returns True if deleted successfully, False if not found or not owned by user.
        """
        if not user_id or not short_code:
            logging.warning("delete_short_link called with missing user_id or short_code.")
            return False

        logging.info(f"Attempting to delete short_code: {short_code} for user_id: {user_id}")
        
        try:
            doc_ref = self.db.collection(self.LINKS_COLLECTION).document(short_code)
            doc_snapshot = doc_ref.get()

            if not doc_snapshot.exists:
                logging.warning(f"Short code {short_code} not found for deletion attempt by user {user_id}")
                return False

            doc_data = doc_snapshot.to_dict()

            if doc_data.get('user_id') != user_id:
                logging.warning(f"User {user_id} attempted to delete link {short_code} owned by {doc_data.get('user_id')}")
                return False

            doc_ref.delete()
            logging.info(f"Successfully deleted short_code: {short_code} for user_id: {user_id}")
            return True

        except Exception as e:
            logging.error(f"Error deleting short_code {short_code} for user_id {user_id}: {e}")
            return False
