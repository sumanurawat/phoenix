"""
Deep Link Service

Service for handling URL shortening and management.
"""
import logging
from firebase_admin import firestore
import uuid
from .website_stats_service import WebsiteStatsService
from .click_tracking_service import ClickTrackingService

# Firestore Collection Name
SHORTENED_LINKS_COLLECTION = "shortened_links"

# Initialize services
website_stats_service = WebsiteStatsService()
click_tracking_service = ClickTrackingService()

def generate_short_code():
    """Generate a unique short code for a URL."""
    db = firestore.client()
    while True:
        short_code = uuid.uuid4().hex[:6] # Generate a 6-character short code
        link_ref = db.collection(SHORTENED_LINKS_COLLECTION).document(short_code)
        doc = link_ref.get()
        if not doc.exists:
            return short_code

def create_short_link(original_url, user_id, user_email):
    """
    Create a short link and store it in Firestore.
    If the user has already shortened this exact URL, return information about the existing short link.
    Returns a dictionary: {'short_code': str, 'is_new': bool, 'original_url': str}
    """
    db = firestore.client()

    # Check if this user has already shortened this original_url
    existing_links_query = db.collection(SHORTENED_LINKS_COLLECTION)         .where('user_id', '==', user_id)         .where('original_url', '==', original_url)         .limit(1)         .stream()

    existing_link_doc = None
    for doc in existing_links_query:
        existing_link_doc = doc
        break

    if existing_link_doc and existing_link_doc.exists:
        logging.info(f"User {user_id} already shortened URL {original_url}. Returning existing short_code: {existing_link_doc.id}")
        return {
            'short_code': existing_link_doc.id,
            'is_new': False,
            'original_url': original_url
        }

    # If no existing link, create a new one
    short_code = generate_short_code()
    doc_data = {
        'original_url': original_url,
        'user_id': user_id,
        'user_email': user_email,
        'created_at': firestore.SERVER_TIMESTAMP,
        'click_count': 0
    }
    db.collection(SHORTENED_LINKS_COLLECTION).document(short_code).set(doc_data)
    
    # Update website stats for new link creation
    website_stats_service.increment_links_created()
    
    logging.info(f"Created new short_code {short_code} for URL {original_url} by user {user_id}")
    return {
        'short_code': short_code,
        'is_new': True,
        'original_url': original_url
    }

def get_original_url(short_code):
    """Retrieve the original URL from a short code."""
    db = firestore.client()
    doc_ref = db.collection(SHORTENED_LINKS_COLLECTION).document(short_code)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('original_url')
    else:
        return None

def increment_click_count(short_code, request_data=None):
    """
    Increment the click count for a short link and record detailed click data.
    """
    db = firestore.client()
    doc_ref = db.collection(SHORTENED_LINKS_COLLECTION).document(short_code)
    
    try:
        doc_snapshot = doc_ref.get()
        if not doc_snapshot.exists:
            return False
        
        # Get link data for click tracking
        link_data = doc_snapshot.to_dict()
        user_id = link_data.get('user_id', '')
        
        # Update click count in shortened_links
        doc_ref.update({'click_count': firestore.Increment(1)})
        
        # Update global website stats
        website_stats_service.increment_total_clicks()
        
        # Record detailed click data if request_data provided
        if request_data:
            click_tracking_service.record_click(short_code, user_id, request_data)
        
        return True
        
    except Exception as e:
        logging.error(f"Error incrementing click count for {short_code}: {e}")
        return False

def get_links_for_user(user_id):
    """Retrieve all short links created by a specific user."""
    logging.info(f"Fetching links for user_id: {user_id}")
    db = firestore.client()
    links_list = []
    try:
        links_query = db.collection(SHORTENED_LINKS_COLLECTION)                         .where('user_id', '==', user_id)                         .order_by('created_at', direction=firestore.Query.DESCENDING)                         .stream()
        for doc in links_query:
            link_data = doc.to_dict()
            link_data['short_code'] = doc.id
            links_list.append(link_data)
        logging.info(f"Retrieved {len(links_list)} links for user_id: {user_id}")
        return links_list
    except Exception as e:
        logging.error(f"Error fetching links for user_id {user_id}: {e}")
        raise

def delete_short_link(short_code, user_id):
    """
    Delete a short link from Firestore.
    Only allows deletion if the link belongs to the specified user.
    Returns True if deleted successfully, False if not found or not owned by user.
    """
    logging.info(f"Attempting to delete short_code: {short_code} for user_id: {user_id}")
    db = firestore.client()
    
    try:
        # Get the document first to verify ownership
        doc_ref = db.collection(SHORTENED_LINKS_COLLECTION).document(short_code)
        doc = doc_ref.get()
        
        if not doc.exists:
            logging.warning(f"Short code {short_code} not found")
            return False
            
        doc_data = doc.to_dict()
        
        # Verify the link belongs to this user
        if doc_data.get('user_id') != user_id:
            logging.warning(f"User {user_id} attempted to delete link {short_code} owned by {doc_data.get('user_id')}")
            return False
            
        # Delete the document
        doc_ref.delete()
        logging.info(f"Successfully deleted short_code: {short_code} for user_id: {user_id}")
        return True
        
    except Exception as e:
        logging.error(f"Error deleting short_code {short_code} for user_id {user_id}: {e}")
        return False

def get_link_by_short_code(short_code):
    """Get link data by short code."""
    try:
        db = firestore.client()
        doc = db.collection(SHORTENED_LINKS_COLLECTION).document(short_code).get()
        if doc.exists:
            data = doc.to_dict()
            data['short_code'] = short_code
            return data
        return None
    except Exception as e:
        logging.error(f"Error fetching link {short_code}: {e}")
        return None
