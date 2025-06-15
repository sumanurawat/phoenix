"""
Firestore Initialization and Schema Documentation Script

This script provides documentation for Firestore collections and can be used
for manual initialization tasks or schema reference.

It requires Firebase Admin SDK to be configured. Ensure you have the
GOOGLE_APPLICATION_CREDENTIALS environment variable set to the path of your
Firebase service account key JSON file.
"""
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

def document_memberships_schema():
    """
    Documents and prints the schema for the 'memberships' collection.
    """
    schema = {
        "collection_name": "memberships",
        "document_id": "userId (string, matches Firebase Auth user ID)",
        "fields": [
            {
                "name": "userId",
                "type": "string",
                "description": "Matches Firebase Auth user ID. This is also the document ID.",
                "example": "firebase_auth_user_uid_123"
            },
            {
                "name": "stripeCustomerId",
                "type": "string",
                "nullable": True,
                "description": "Stripe Customer ID. Set after successful Stripe customer creation.",
                "example": "cus_xxxxxxxxxxxxxx"
            },
            {
                "name": "stripeSubscriptionId",
                "type": "string",
                "nullable": True,
                "description": "Stripe Subscription ID. Set after successful Stripe subscription.",
                "example": "sub_xxxxxxxxxxxxxx"
            },
            {
                "name": "currentTier",
                "type": "string",
                "default": "free",
                "description": "Current membership tier of the user.",
                "example": "'free', 'basic', 'premium'"
            },
            {
                "name": "subscriptionStatus",
                "type": "string",
                "description": "Status of the Stripe subscription or user's membership.",
                "example": "'active', 'inactive', 'trialing', 'canceled', 'past_due', 'free_tier'"
            },
            {
                "name": "subscriptionStartDate",
                "type": "timestamp",
                "nullable": True,
                "description": "Date when the current paid subscription started. Null for free tier.",
                "example": "Firestore Timestamp object"
            },
            {
                "name": "subscriptionEndDate",
                "type": "timestamp",
                "nullable": True,
                "description": "Date when the current subscription is set to end or renew. Null for free tier or non-expiring subscriptions.",
                "example": "Firestore Timestamp object"
            },
            {
                "name": "lastUpdated",
                "type": "timestamp",
                "description": "Server timestamp indicating the last time this document was updated.",
                "example": "Firestore.SERVER_TIMESTAMP"
            }
        ]
    }

    print("=" * 80)
    print(f"Schema for Collection: {schema['collection_name']}")
    print("=" * 80)
    print(f"Document ID: {schema['document_id']}\n")

    print("Fields:")
    for field in schema['fields']:
        print(f"  - Name: {field['name']}")
        print(f"    Type: {field['type']}")
        if field.get('nullable'):
            print("    Nullable: Yes")
        if field.get('default'):
            print(f"    Default: {field['default']}")
        print(f"    Description: {field['description']}")
        print(f"    Example: {field['example']}\n")
    print("=" * 80)

# --- Example Firestore Operation (Commented Out) ---
# This section is for documentation and manual setup.
# It shows how one might add a default membership document for a test user.
# Ensure Firebase Admin SDK is initialized before running any Firestore operations.

# def initialize_firebase_admin():
#     """
#     Initializes the Firebase Admin SDK if not already initialized.
#     Relies on GOOGLE_APPLICATION_CREDENTIALS environment variable.
#     """
#     if not firebase_admin._apps:
#         try:
#             # Attempt to use default credentials (e.g., from environment)
#             cred = credentials.ApplicationDefault()
#             firebase_admin.initialize_app(cred)
#             print("Firebase Admin SDK initialized successfully using Application Default Credentials.")
#         except Exception as e_default:
#             print(f"Failed to initialize with default credentials: {e_default}")
#             # Fallback: Try to use a specific credentials file if GOOGLE_APPLICATION_CREDENTIALS is set
#             # Note: This assumes GOOGLE_APPLICATION_CREDENTIALS points to a valid JSON file.
#             # For this script, explicit path might be more robust if not running in a configured GCP env.
#             # However, for consistency with the rest of the app, relying on the env var is preferred.
#             try:
#                 if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
#                     cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
#                     cred = credentials.Certificate(cred_path)
#                     firebase_admin.initialize_app(cred)
#                     print(f"Firebase Admin SDK initialized successfully using GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")
#                 else:
#                     print("GOOGLE_APPLICATION_CREDENTIALS environment variable not set. Cannot initialize Firebase Admin SDK.")
#                     return False
#             except Exception as e_specific:
#                 print(f"Failed to initialize with specific credentials file: {e_specific}")
#                 return False
#     else:
#         print("Firebase Admin SDK already initialized.")
#     return True

# def add_sample_free_tier_membership(user_id: str):
#     """
#     Adds a sample 'free' tier membership document for a given userId.
#     This is for manual setup or testing purposes.
#
#     Args:
#         user_id (str): The Firebase Auth user ID for whom to create the membership.
#     """
#     if not initialize_firebase_admin():
#         print("Cannot add sample membership, Firebase Admin SDK not initialized.")
#         return
#
#     db = firestore.client()
#     membership_ref = db.collection("memberships").document(user_id)
#
#     doc = membership_ref.get()
#     if doc.exists:
#         print(f"Membership document for user {user_id} already exists.")
#         return
#
#     try:
#         membership_data = {
#             "userId": user_id,
#             "stripeCustomerId": None,
#             "stripeSubscriptionId": None,
#             "currentTier": "free",
#             "subscriptionStatus": "free_tier", # Indicates they are on the free plan, not an ended paid one
#             "subscriptionStartDate": None,
#             "subscriptionEndDate": None,
#             "lastUpdated": firestore.SERVER_TIMESTAMP
#         }
#         membership_ref.set(membership_data)
#         print(f"Successfully created 'free' tier membership for user: {user_id}")
#     except Exception as e:
#         print(f"Error creating sample membership for user {user_id}: {e}")

if __name__ == "__main__":
    print("This script is for documenting Firestore schemas and manual initialization tasks.")
    print("It does not perform any automated database operations when run directly.\n")
    document_memberships_schema()

    # --- To manually add a sample free tier membership for a test user: ---
    # 1. Ensure your GOOGLE_APPLICATION_CREDENTIALS environment variable is set correctly.
    # 2. Uncomment the relevant functions above:
    #    - initialize_firebase_admin()
    #    - add_sample_free_tier_membership(user_id)
    # 3. Call the function with a test user ID:
    #    test_user_firebase_id = "your_test_firebase_user_id"
    #    add_sample_free_tier_membership(test_user_firebase_id)
    #
    # Example:
    # print("\n--- Example Manual Initialization ---")
    # if initialize_firebase_admin(): # Initialize first
    #    add_sample_free_tier_membership("test_user_123")
    # else:
    #    print("Skipping manual initialization example as Firebase Admin SDK could not be initialized.")
