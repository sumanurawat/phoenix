"""
Membership Service

This service handles interactions related to user memberships,
integrating with Firebase Firestore for data storage and Stripe for payment processing.
"""
import stripe
from firebase_admin import firestore
from datetime import datetime, timezone

# Assuming your Stripe keys are loaded in config.settings
# You might need to adjust the import path based on your project structure
from config import settings as app_config

# Initialize Firestore client globally or within the class
# Global initialization is fine if the service is instantiated once per app context
try:
    db = firestore.client()
except Exception as e:
    # This might happen if Firebase Admin SDK is not initialized yet.
    # Depending on your app's startup sequence, you might initialize Firebase Admin
    # elsewhere (e.g., in app.py) before this service is imported or used.
    # For now, we'll assume it's initialized. If not, db operations will fail.
    print(f"Warning: Firestore client might not be initialized if Firebase Admin SDK is not ready: {e}")
    db = None # Or handle appropriately

# Configure Stripe API Key
if app_config.STRIPE_SECRET_KEY:
    stripe.api_key = app_config.STRIPE_SECRET_KEY
else:
    # This will cause Stripe API calls to fail.
    # The app should ideally not start if keys are missing (as per config/settings.py checks)
    print("Warning: Stripe Secret Key is not configured. Stripe API calls will fail.")


class MembershipService:
    """
    Manages user memberships, subscriptions, and interactions with Stripe.
    """
    MEMBERSHIPS_COLLECTION = 'memberships'

    # This should ideally be in config or a more dynamic mapping
    # User must replace these with their actual Stripe Price IDs.
    PRICE_ID_TO_TIER_MAPPING = {
        'price_placeholder_basic_monthly': 'basic',
        'price_placeholder_premium_monthly': 'premium',
        'price_placeholder_basic_yearly': 'basic',
        'price_placeholder_premium_yearly': 'premium',
        # Add more Price IDs as needed
    }

    def __init__(self):
        """
        Initializes the MembershipService.
        Relies on global `db` and `stripe.api_key` being configured.
        """
        if db is None:
            # Attempt to initialize db again if it wasn't available at module load time
            # This is a fallback, proper initialization order is preferred.
            global db
            db = firestore.client()
            if db is None:
                raise ConnectionError("Firestore client could not be initialized. Ensure Firebase Admin SDK is initialized.")

        if not stripe.api_key:
            raise ValueError("Stripe API key is not configured. Cannot initialize MembershipService.")

    def get_user_membership(self, user_id: str) -> dict:
        """
        Retrieves a user's membership document from Firestore.
        If not found, returns a default 'free' tier structure conceptually
        without writing to the database.

        Args:
            user_id (str): The Firebase Authentication user ID.

        Returns:
            dict: The user's membership data or a default free tier structure.
        """
        if not user_id:
            raise ValueError("user_id cannot be empty.")

        doc_ref = db.collection(self.MEMBERSHIPS_COLLECTION).document(user_id)
        doc = doc_ref.get()

        if doc.exists:
            return doc.to_dict()
        else:
            # Return a default structure for a user not yet in the database
            # This record is NOT created in Firestore here.
            return {
                'userId': user_id,
                'stripeCustomerId': None,
                'stripeSubscriptionId': None,
                'currentTier': 'free',
                'subscriptionStatus': 'free_tier', # Indicates they are on a conceptual free plan
                'subscriptionStartDate': None,
                'subscriptionEndDate': None,
                'lastUpdated': None # Not setting SERVER_TIMESTAMP as we are not writing this conceptual record
            }

    def ensure_stripe_customer(self, user_id: str, email: str, name: str = None) -> str:
        """
        Ensures a Stripe customer exists for the user.
        If one exists (based on Firestore record), returns the ID.
        If not, creates one in Stripe and updates Firestore.

        Args:
            user_id (str): The Firebase Authentication user ID.
            email (str): The user's email address.
            name (str, optional): The user's full name. Defaults to None.

        Returns:
            str: The Stripe Customer ID.
        """
        if not user_id or not email:
            raise ValueError("user_id and email are required.")

        membership_data = self.get_user_membership(user_id) # This won't create a doc if user is new

        if membership_data and membership_data.get('stripeCustomerId'):
            return membership_data['stripeCustomerId']

        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={'app_user_id': user_id}
            )
            stripe_customer_id = customer.id

            user_membership_ref = db.collection(self.MEMBERSHIPS_COLLECTION).document(user_id)
            # Prepare data, ensuring default fields if this is the first time we're creating the doc
            data_to_set = {
                'stripeCustomerId': stripe_customer_id,
                'userId': user_id,
                'lastUpdated': firestore.SERVER_TIMESTAMP
            }
            if not membership_data or not membership_data.get('currentTier'): # If it was a conceptual free user
                data_to_set['currentTier'] = 'free'
                data_to_set['subscriptionStatus'] = 'free_tier'
                # Set other fields to their defaults if necessary

            user_membership_ref.set(data_to_set, merge=True)
            return stripe_customer_id
        except stripe.error.StripeError as e:
            # Handle Stripe errors (e.g., network issues, invalid request)
            print(f"Stripe error while creating customer for user {user_id}: {e}")
            raise  # Re-raise the exception to be handled by the caller

    def _get_tier_from_price_id(self, price_id: str) -> str:
        """
        Maps a Stripe Price ID to an internal application tier name.
        IMPORTANT: User must update PRICE_ID_TO_TIER_MAPPING with their actual Stripe Price IDs.

        Args:
            price_id (str): The Stripe Price ID.

        Returns:
            str: The corresponding tier name or 'unknown_tier' if not found.
        """
        tier = self.PRICE_ID_TO_TIER_MAPPING.get(price_id)
        if tier is None:
            print(f"Warning: Unknown Stripe Price ID '{price_id}'. Tier mapping needs update.")
            return 'unknown_tier'
        return tier

    def update_membership_from_stripe_checkout_session(self, session: stripe.checkout.Session) -> None:
        """
        Updates a user's membership in Firestore based on a completed Stripe Checkout Session.
        This should be called when handling 'checkout.session.completed' webhook events.

        Args:
            session (stripe.checkout.Session): The Stripe Checkout Session object.
        """
        stripe_customer_id = session.customer
        stripe_subscription_id = session.subscription
        app_user_id = session.client_reference_id # Crucial: Must be set to your app's user_id during Checkout Session creation
        payment_status = session.payment_status

        if payment_status != 'paid':
            print(f"Checkout session {session.id} not paid. Status: {payment_status}. No membership update.")
            return

        if not app_user_id:
            print(f"Error: client_reference_id (app_user_id) not found in checkout session {session.id}. Cannot update membership.")
            # This indicates an issue with how the Checkout Session was created.
            return

        try:
            stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)

            if not stripe_subscription.items.data:
                print(f"Error: No items found in Stripe subscription {stripe_subscription_id} for user {app_user_id}.")
                return

            price_id = stripe_subscription.items.data[0].price.id
            current_tier = self._get_tier_from_price_id(price_id)
            subscription_status = stripe_subscription.status  # e.g., 'active', 'trialing'

            # Convert Stripe timestamps to datetime objects
            start_date = datetime.fromtimestamp(stripe_subscription.current_period_start, tz=timezone.utc)
            end_date = datetime.fromtimestamp(stripe_subscription.current_period_end, tz=timezone.utc)

            membership_ref = db.collection(self.MEMBERSHIPS_COLLECTION).document(app_user_id)
            membership_data = {
                'stripeCustomerId': stripe_customer_id,
                'stripeSubscriptionId': stripe_subscription_id,
                'currentTier': current_tier,
                'subscriptionStatus': subscription_status,
                'subscriptionStartDate': start_date,
                'subscriptionEndDate': end_date,
                'lastUpdated': firestore.SERVER_TIMESTAMP,
                'userId': app_user_id  # Ensure userId is part of the record
            }
            membership_ref.set(membership_data, merge=True)
            print(f"Membership updated for user {app_user_id} from checkout session {session.id}.")

        except stripe.error.StripeError as e:
            print(f"Stripe error while updating membership for user {app_user_id} from checkout session: {e}")
            # Potentially re-raise or handle more gracefully depending on webhook retry logic
        except Exception as e:
            print(f"Unexpected error updating membership for {app_user_id}: {e}")


    def update_membership_from_stripe_subscription_event(self, subscription_event: stripe.Subscription) -> None:
        """
        Updates a user's membership based on Stripe subscription events
        (e.g., customer.subscription.updated, customer.subscription.deleted).

        Args:
            subscription_event (stripe.Subscription): The Stripe Subscription object from the webhook.
        """
        stripe_customer_id = subscription_event.customer
        stripe_subscription_id = subscription_event.id
        status = subscription_event.status  # e.g., 'active', 'canceled', 'past_due'

        if not stripe_customer_id:
            print(f"Error: stripe_customer_id not found in subscription event {stripe_subscription_id}. Cannot update.")
            return

        if not subscription_event.items.data:
            print(f"Warning: No items found in subscription event {stripe_subscription_id} for customer {stripe_customer_id}. May not be able to determine tier.")
            # If it's a cancellation of a subscription that had items, this might be okay.
            # If it's an update and items are missing, that's unusual.
            # For cancellation, we might not get price_id, so tier update might be tricky.

        price_id = None
        current_tier = None

        if subscription_event.items.data:
            price_id = subscription_event.items.data[0].price.id
            current_tier = self._get_tier_from_price_id(price_id)
        else:
            # If no items (e.g. subscription fully deleted), we might not get a price_id.
            # We need to decide what the tier should be.
            # It's possible the tier was already set to 'free' if cancel_at_period_end was true
            # and handled by a previous 'customer.subscription.updated' event.
            print(f"No price_id in subscription event {stripe_subscription_id}. Tier may not be updated from this event.")


        # Query Firestore for the user document by stripeCustomerId
        query = db.collection(self.MEMBERSHIPS_COLLECTION).where('stripeCustomerId', '==', stripe_customer_id).limit(1).stream()

        user_doc_snapshot = None
        for doc_snap in query: # stream() returns an iterator
            user_doc_snapshot = doc_snap
            break # We only expect one due to limit(1)

        if not user_doc_snapshot:
            print(f"Error: User not found in Firestore with stripeCustomerId {stripe_customer_id}. Cannot update membership from subscription event.")
            # This could happen if the customer was created in Stripe but not yet synced to your DB,
            # or if there's a data inconsistency.
            return

        app_user_id = user_doc_snapshot.id
        membership_ref = db.collection(self.MEMBERSHIPS_COLLECTION).document(app_user_id)

        membership_update_data = {
            'stripeSubscriptionId': stripe_subscription_id, # Keep this for reference even if canceled
            'subscriptionStatus': status,
            'lastUpdated': firestore.SERVER_TIMESTAMP
        }

        if current_tier: # Only update tier if we could determine it
            membership_update_data['currentTier'] = current_tier

        # Handle dates and tier changes based on status
        if status == 'active' or status == 'trialing':
            membership_update_data['subscriptionStartDate'] = datetime.fromtimestamp(subscription_event.current_period_start, tz=timezone.utc)
            membership_update_data['subscriptionEndDate'] = datetime.fromtimestamp(subscription_event.current_period_end, tz=timezone.utc)
        elif status == 'canceled':
            # If a subscription is canceled, it might be immediate or at period end.
            # Stripe usually sets 'ended_at' when fully canceled.
            # If cancel_at_period_end was true, current_period_end is the relevant date.
            if subscription_event.ended_at:
                membership_update_data['subscriptionEndDate'] = datetime.fromtimestamp(subscription_event.ended_at, tz=timezone.utc)
            else: # Should use current_period_end if not ended_at, but usually ended_at is set for 'canceled'
                 membership_update_data['subscriptionEndDate'] = datetime.fromtimestamp(subscription_event.current_period_end, tz=timezone.utc)

            # Decide what the tier becomes upon cancellation.
            # It might be 'free' or a specific 'canceled' tier.
            # For now, let's assume if it's 'canceled', currentTier from price_id might still be valid
            # until it truly ends, or we explicitly set it to 'free'.
            # If 'cancel_at_period_end' is true, the status might still be 'active' until period_end.
            # This logic might need refinement based on how "cancel_at_period_end" vs immediate cancellation is handled.
            if subscription_event.cancel_at_period_end and status == 'active':
                 # It's active now but will be canceled. Status is still 'active'.
                 # The 'customer.subscription.updated' event for cancel_at_period_end=true will trigger this.
                 # The actual 'canceled' status comes later.
                 pass
            else: # Truly canceled or past_due that led to cancellation
                membership_update_data['currentTier'] = 'free' # Or another appropriate status
                # Clear subscription-specific dates if they are no longer relevant
                # membership_update_data['subscriptionStartDate'] = None # Optional: clear start date?
        elif status == 'past_due':
            # Subscription is still active but payment failed. End date might be extended by Stripe grace periods.
            membership_update_data['subscriptionEndDate'] = datetime.fromtimestamp(subscription_event.current_period_end, tz=timezone.utc)
            # Tier remains the same, but status is 'past_due'.

        # For 'unpaid', 'incomplete', 'incomplete_expired', these also often mean the subscription isn't active.
        # The logic for tier changes on these statuses should be considered.
        # For simplicity, if not 'active' or 'trialing', we might revert to 'free' or a specific inactive tier.
        if status not in ['active', 'trialing']:
            # If the subscription is no longer active (e.g. canceled, unpaid, past_due that results in cancellation)
            # And we didn't already set it to 'free' for 'canceled'
            if 'currentTier' not in membership_update_data or membership_update_data.get('currentTier') != 'free':
                 if not subscription_event.cancel_at_period_end or status == 'canceled': # if not just pending cancellation
                    membership_update_data['currentTier'] = 'free' # Default to free if subscription is non-active

        try:
            membership_ref.set(membership_update_data, merge=True)
            print(f"Membership updated for user {app_user_id} (Stripe Customer: {stripe_customer_id}) from subscription event {stripe_subscription_id}. New status: {status}")
        except Exception as e:
            print(f"Error updating Firestore for user {app_user_id} from subscription event: {e}")

# Example usage (for testing, not part of the service itself)
# if __name__ == '__main__':
#     # This requires Firebase to be initialized with credentials
#     # and Stripe API key to be set.
#     # Ensure GOOGLE_APPLICATION_CREDENTIALS is set.
#     try:
#         if not firebase_admin._apps:
#             cred = credentials.ApplicationDefault()
#             firebase_admin.initialize_app(cred)
#
#         membership_service = MembershipService()
#
#         # Test get_user_membership (assuming a user 'test_user_id' may or may not exist)
#         # print(membership_service.get_user_membership('test_user_id_nonexistent'))
#
#         # Test ensure_stripe_customer (requires a valid email and user_id)
#         # test_user_id = "firebase_user_test_002"
#         # test_email = "testuser002@example.com"
#         # test_name = "Test User Two"
#         # customer_id = membership_service.ensure_stripe_customer(test_user_id, test_email, test_name)
#         # print(f"Ensured Stripe Customer ID for {test_user_id}: {customer_id}")
#         # print(membership_service.get_user_membership(test_user_id))

#     except Exception as e:
#         print(f"Error in example usage: {e}")
#         print("Ensure Firebase Admin SDK is initialized (e.g., GOOGLE_APPLICATION_CREDENTIALS set) and Stripe keys are configured.")
