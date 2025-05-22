"""
Deep Link Service

This service handles the creation, management, and tracking of short links.
It interacts with Google Firestore to store link data and click event details.
It includes functionality for generating unique short codes, differentiating between
guest and authenticated user links, logging click events with geolocation, and
managing link expiration based on click counts for guest users.
The YouTube-specific functions (`extract_video_id`, `validate_video_id`) are
currently unused by the main short linking feature but are kept for potential future use.
"""
import re
from urllib.parse import urlparse, parse_qs
import secrets
import string
from google.cloud import firestore
import firebase_admin # Assuming firebase_admin is initialized in app.py or similar

# Initialize Firestore client
# This requires Firebase Admin SDK to be initialized, typically in the main app setup (e.g., app.py).
# If `firebase_admin.initialize_app()` has not been called, this will fail.
try:
    db = firestore.Client()
except Exception as e:
    # This print statement is for debugging and helps diagnose initialization issues.
    # In a production environment, this should be handled by a proper logging setup.
    # The commented-out code below is an example of how one might attempt a fallback
    # initialization, but it's generally better to ensure explicit initialization at app startup.
    # from firebase_admin import credentials
    # if not firebase_admin._apps:
    #     cred = credentials.ApplicationDefault() # Or use a service account key
    #     firebase_admin.initialize_app(cred)
    #     db = firestore.Client()
    print(f"Error initializing Firestore client in deeplink_service: {e}. Ensure Firebase Admin is initialized before this service module is imported.")
    db = None # Setting db to None ensures functions relying on it will fail clearly if initialization failed.


MAX_GENERATE_ATTEMPTS = 10 # Maximum attempts to generate a unique short code.

def generate_short_code(length=7):
    """
    Generates a cryptographically secure random short code of a specified length.
    It then checks against the Firestore 'links' collection to ensure the generated code is unique.
    If a unique code is not found after MAX_GENERATE_ATTEMPTS, a ValueError is raised.

    Args:
        length (int): The desired length of the short code. Defaults to 7.

    Returns:
        str: A unique short code.

    Raises:
        ConnectionError: If the Firestore client (db) is not initialized.
        ValueError: If a unique short code cannot be generated after MAX_GENERATE_ATTEMPTS.
    """
    if not db:
        raise ConnectionError("Firestore client not initialized. Cannot generate short code.")

    alphabet = string.ascii_letters + string.digits # Define the character set for the short code
    for _ in range(MAX_GENERATE_ATTEMPTS):
        # Generate a random string of the specified length
        short_code = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Check if this short_code already exists as a document ID in the 'links' collection
        link_ref = db.collection('links').document(short_code)
        if not link_ref.get().exists:
            return short_code # Found a unique code
    # If loop completes without returning, all attempts failed
    raise ValueError(f"Could not generate a unique short code after {MAX_GENERATE_ATTEMPTS} attempts.")

def create_short_link(original_url, user_id=None, user_email=None):
    """
    Creates a new short link document in Firestore.
    The document ID is a newly generated unique short_code.
    Differentiates between 'guest' and 'authenticated' links, setting click limits for guests.

    Args:
        original_url (str): The URL to be shortened.
        user_id (str, optional): The unique ID of the authenticated user. If provided, link type is 'authenticated'.
        user_email (str, optional): The email of a guest user. Used if user_id is None.

    Returns:
        str: The generated unique shortCode for the link.

    Raises:
        ConnectionError: If the Firestore client (db) is not initialized.
        ValueError: If original_url is empty, or if Firestore operation fails.
    """
    if not db:
        raise ConnectionError("Firestore client not initialized. Cannot create short link.")

    if not original_url or not original_url.strip():
        raise ValueError("Original URL cannot be empty.")

    short_code = generate_short_code() # Obtain a unique short code

    # Determine link type and set properties accordingly
    link_type = "authenticated" if user_id else "guest"
    # Guest links have a click limit, authenticated links do not (or this can be a premium feature later)
    max_clicks = None if link_type == "authenticated" else 10

    # Prepare data for the new Firestore document
    link_data = {
        'originalUrl': original_url.strip(),
        'userId': user_id, # Will be null for guest links
        'userEmail': user_email if not user_id and user_email else None, # Store email only for guests, if provided
        'type': link_type,
        'createdAt': firestore.SERVER_TIMESTAMP, # Firestore specific timestamp
        'clickCount': 0, # Initial click count
        'lastClickedAt': None, # Timestamp of the last click
        'isExpired': False, # Link is active by default
        'maxClicks': max_clicks # Maximum clicks allowed (null for no limit)
    }

    try:
        # Create a new document in the 'links' collection with short_code as its ID
        db.collection('links').document(short_code).set(link_data)
        return short_code
    except Exception as e:
        # Catch any exception during Firestore operation and raise a generic error
        # In a production app, log 'e' for debugging
        print(f"Error creating short link in Firestore: {e}") # For debugging
        raise ValueError(f"Failed to create short link in Firestore: {e}")

# --- Functions for fetching link details and logging clicks ---

def get_link_details(short_code):
    """
    Fetches a link document by its short_code from the 'links' collection in Firestore.

    Args:
        short_code (str): The short code (document ID) of the link to fetch.

    Returns:
        dict: The link data as a dictionary if found, otherwise None.

    Raises:
        ConnectionError: If the Firestore client (db) is not initialized.
        Exception: Re-raises Firestore exceptions if the fetch operation fails for other reasons.
    """
    if not db:
        raise ConnectionError("Firestore client not initialized. Cannot get link details.")
    try:
        link_ref = db.collection('links').document(short_code)
        link_doc = link_ref.get() # Retrieve the document
        if link_doc.exists:
            return link_doc.to_dict() # Convert Firestore document to dictionary
        return None # Document not found
    except Exception as e:
        # Log the exception e
        print(f"Error fetching link details for {short_code} from Firestore: {e}") # For debugging
        raise # Re-raise the exception to be handled by the caller

def _get_country_code_from_ip(ip_address):
    """
    Internal helper function to get countryCode from an IP address using the ip-api.com service.
    This is a stretch goal feature for geolocation of clicks.

    Args:
        ip_address (str): The IP address to geolocate.

    Returns:
        str: The two-letter country code (e.g., "US") if successful, otherwise None.
             Returns None if ip_address is None, local, or if the API request fails.
    """
    # Avoid API call for invalid or local IPs where geolocation is not meaningful/possible
    if not ip_address or ip_address == "127.0.0.1" or ip_address == "::1":
        return None
    try:
        # Dynamically import requests only when this function is called
        # This avoids making 'requests' a hard dependency for the entire service if geolocation is unused.
        import requests
        # Construct the API URL for ip-api.com. Only request necessary fields.
        # Consider making the API URL and timeout configurable if this were a more critical feature.
        api_url = f"http://ip-api.com/json/{ip_address}?fields=status,countryCode"
        response = requests.get(api_url, timeout=2) # Set a timeout to avoid long waits
        response.raise_for_status() # Raise an HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        # Check if the API call was successful and a countryCode was returned
        if data.get('status') == 'success' and data.get('countryCode'):
            return data.get('countryCode')
        return None # API call succeeded but no countryCode (e.g., for reserved IPs)
    except requests.exceptions.RequestException as e:
        # Handle network errors, timeouts, or HTTP errors from the API request
        print(f"Geolocation API request failed for IP {ip_address}: {e}") # For debugging
        return None
    except Exception as e:
        # Handle other potential errors (e.g., JSON parsing issues)
        print(f"Error processing geolocation response for IP {ip_address}: {e}") # For debugging
        return None


@firestore.transactional
def _update_link_and_log_click_transaction(transaction, link_ref, click_data_for_subcollection):
    """
    Atomically increments the link's clickCount, updates lastClickedAt, and retrieves the link data
    within a Firestore transaction. This ensures that the read and update operations are atomic.
    The actual logging of detailed click data to a subcollection happens outside this transaction.

    Args:
        transaction (google.cloud.firestore.Transaction): The Firestore transaction object.
        link_ref (google.cloud.firestore.DocumentReference): Reference to the link document.
        click_data_for_subcollection (dict): Data for the click subcollection (unused in this function,
                                             but kept for potential future use within transaction if requirements change).

    Returns:
        dict: The link document's data (as a dictionary) after the transaction attempts to read it.
              Includes a 'clickCount' field updated to reflect the increment for immediate use.

    Raises:
        ValueError: If the link document does not exist.
    """
    link_doc = link_ref.get(transaction=transaction) # Read the document within the transaction
    if not link_doc.exists:
        raise ValueError(f"Link {link_ref.id} not found during transaction.")

    # Simulate the new click count for immediate return, as Increment happens server-side.
    # The actual 'clickCount' in Firestore is updated atomically by Increment().
    current_click_count = link_doc.to_dict().get('clickCount', 0)
    updated_click_count_for_return = current_click_count + 1
    
    # Perform atomic updates within the transaction
    transaction.update(link_ref, {
        'clickCount': firestore.Increment(1),       # Atomically increment the click count
        'lastClickedAt': firestore.SERVER_TIMESTAMP # Update the last clicked timestamp
    })
    
    # Note on subcollection writes:
    # Writing to a subcollection (creating a new document) is generally not performed
    # within the same transaction that updates the parent document if the subcollection
    # document ID is new or randomly generated. Transactions require predetermined paths.
    # Thus, logging to 'clicks' subcollection is done after this transaction completes.

    link_data = link_doc.to_dict()
    # Return the link data with the click count updated for immediate use by the calling function.
    link_data['clickCount'] = updated_click_count_for_return 
    return link_data


def log_click_event(short_code, ip_address, user_agent, referrer_url):
    """
    Logs a click event for a given short_code. This involves:
    1. Attempting IP-based geolocation to get a country code.
    2. Atomically updating the parent link document's clickCount and lastClickedAt timestamp
       using a Firestore transaction.
    3. Creating a new document in the 'clicks' subcollection of the parent link, storing
       details of this specific click event (IP, user agent, referrer, country code).
    4. Checking if a 'guest' link has reached its maxClicks and updating its 'isExpired' status if so.

    Args:
        short_code (str): The short code of the link that was clicked.
        ip_address (str): IP address of the clicker.
        user_agent (str): User agent string of the clicker's browser/client.
        referrer_url (str): Referrer URL, if available.

    Returns:
        tuple: (original_url, is_expired)
               - original_url (str): The original URL to redirect to.
               - is_expired (bool): True if the link is expired or not found, False otherwise.
               Returns (None, True) if the link is not found, or if any critical error occurs.
    """
    if not db:
        raise ConnectionError("Firestore client not initialized. Cannot log click event.")

    link_ref = db.collection('links').document(short_code) # Reference to the main link document
    
    try:
        # 1. Attempt IP Geolocation (can be done outside the main transaction)
        country_code = _get_country_code_from_ip(ip_address)

        # 2. Prepare data for the 'clicks' subcollection document
        # This document will be created after the main link update transaction is successful.
        click_subcollection_doc_ref = link_ref.collection('clicks').document() # Auto-generate ID for the click entry
        click_log_data = {
            'clickedAt': firestore.SERVER_TIMESTAMP, # Firestore server-side timestamp for accuracy
            'ipAddress': ip_address,
            'userAgent': user_agent,
            'referrerUrl': referrer_url,
            'countryCode': country_code # May be None if geolocation failed
        }

        # 3. Execute Firestore Transaction to update the parent link document
        # The _update_link_and_log_click_transaction function handles the atomic increment and timestamp update.
        transaction = db.transaction()
        # Pass None for click_data_for_subcollection as it's not used within the transaction itself.
        updated_link_data = _update_link_and_log_click_transaction(transaction, link_ref, None) 
        
        # 4. If the transaction was successful, create the click log in the subcollection.
        # This is done outside the transaction to allow for auto-generated document IDs in the subcollection.
        click_subcollection_doc_ref.set(click_log_data)

        # 5. Check for link expiration (especially for 'guest' links)
        is_expired = updated_link_data.get('isExpired', False) # Get current expiration status

        # If the link isn't already marked as expired, check if this click makes it expire (for guest links)
        if not is_expired and updated_link_data.get('type') == 'guest':
            max_clicks_allowed = updated_link_data.get('maxClicks')
            # updated_link_data['clickCount'] already reflects the count *after* this click
            current_total_clicks = updated_link_data.get('clickCount') 
            if max_clicks_allowed is not None and current_total_clicks >= max_clicks_allowed:
                is_expired = True
                link_ref.update({'isExpired': True}) # Persist the expiration status to Firestore
        
        return updated_link_data.get('originalUrl'), is_expired

    except ValueError as ve: # Specific error, e.g., "Link not found" from the transaction
        print(f"Value error logging click for {short_code}: {ve}") # For debugging
        return None, True # Link not found or invalid state, treat as expired for redirection purposes
    except Exception as e:
        # Catch any other exceptions during the process
        print(f"Generic error logging click event for {short_code}: {e}") # For debugging
        # In case of any error, assume the link is unusable/expired to prevent unintended redirection
        return None, True


def extract_video_id(youtube_url):
    """Extract the video ID from a YouTube URL.
    
    Supports formats:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID
    """
    try:
        url = urlparse(youtube_url)
        
        if url.hostname in ('youtu.be', 'www.youtu.be'):
            # youtu.be format
            return url.path[1:]  # Remove leading '/'
        
        if url.hostname in ('youtube.com', 'www.youtube.com'):
            # youtube.com format
            query_params = parse_qs(url.query)
            return query_params['v'][0]
            
        return None
    except Exception:
        return None

def validate_video_id(video_id):
    """
    Extracts the video ID from various YouTube URL formats.
    This function is part of the original deep linking functionality for YouTube URLs
    and is not directly used by the generic short link creation feature. Kept for posterity
    or potential future integration.

    Args:
        youtube_url (str): The YouTube URL.

    Returns:
        str: The extracted YouTube video ID, or None if extraction fails.
    """
    if not youtube_url:
        return None
    try:
        url = urlparse(youtube_url) # Parse the URL into components
        
        # Handle 'youtu.be/VIDEO_ID' format
        if url.hostname in ('youtu.be', 'www.youtu.be'):
            return url.path[1:]  # Remove leading '/' to get the ID
        
        # Handle 'youtube.com/watch?v=VIDEO_ID' format
        if url.hostname in ('youtube.com', 'www.youtube.com'):
            if url.path == '/watch':
                query_params = parse_qs(url.query)
                return query_params.get('v', [None])[0] # Get 'v' parameter
            # Could also handle '/embed/VIDEO_ID' or other paths if needed
            
        return None # URL is not a recognized YouTube video format
    except Exception as e:
        print(f"Error parsing YouTube URL {youtube_url}: {e}") # For debugging
        return None

def validate_video_id(video_id):
    """
    Validates if a given string matches the typical format of a YouTube video ID.
    YouTube video IDs are generally 11 characters long and use alphanumeric characters,
    underscores, and hyphens. This function is also part of the original YouTube
    deep linking functionality.

    Args:
        video_id (str): The video ID string to validate.

    Returns:
        bool: True if the video_id seems valid, False otherwise.
    """
    if not video_id:
        return False
    # Standard YouTube video IDs are 11 characters long and consist of A-Z, a-z, 0-9, _, -
    return bool(re.match(r'^[A-Za-z0-9_-]{11}$', video_id))
