"""
Deep Link Service

Service for handling YouTube URL conversion to deep links and URL shortening.
"""
import firebase_admin
from firebase_admin import firestore
import uuid # For generating initial short codes
import time # For created_at timestamp
import re
from urllib.parse import urlparse, parse_qs

# Firestore Collection Name
SHORTENED_LINKS_COLLECTION = "shortened_links"

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
    """Create a short link and store it in Firestore."""
    db = firestore.client()
    short_code = generate_short_code()
    doc_data = {
        'original_url': original_url,
        'user_id': user_id,
        'user_email': user_email,
        'created_at': firestore.SERVER_TIMESTAMP, # Use server timestamp
        'click_count': 0
    }
    db.collection(SHORTENED_LINKS_COLLECTION).document(short_code).set(doc_data)
    return short_code

def get_original_url(short_code):
    """Retrieve the original URL from a short code."""
    db = firestore.client()
    doc_ref = db.collection(SHORTENED_LINKS_COLLECTION).document(short_code)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('original_url')
    else:
        return None

def increment_click_count(short_code):
    """Increment the click count for a short link."""
    db = firestore.client()
    doc_ref = db.collection(SHORTENED_LINKS_COLLECTION).document(short_code)
    # Check if document exists before trying to increment
    if doc_ref.get().exists:
        doc_ref.update({'click_count': firestore.Increment(1)})
        return True
    return False # Indicate if short_code was not found

def get_links_for_user(user_id):
    """Retrieve all short links created by a specific user."""
    db = firestore.client()
    links_list = []
    links_query = db.collection(SHORTENED_LINKS_COLLECTION) \
                    .where('user_id', '==', user_id) \
                    .order_by('created_at', direction=firestore.Query.DESCENDING) \
                    .stream()
    for doc in links_query:
        link_data = doc.to_dict()
        link_data['short_code'] = doc.id # Add the document ID as short_code
        # Convert timestamp to a readable string or keep as is, depending on frontend needs
        # For simplicity, we'll keep it as a Firestore timestamp for now.
        links_list.append(link_data)
    return links_list

# Existing YouTube-specific functions
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
    """Validate that a video ID matches YouTube's format."""
    if not video_id:
        return False
    # YouTube video IDs are typically 11 characters of alphanumeric and underscore/dash
    return bool(re.match(r'^[A-Za-z0-9_-]{11}$', video_id))
