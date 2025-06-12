"""
Deep Link Routes

Routes for handling YouTube deep link conversion and generic URL shortening.
"""
from flask import Blueprint, render_template, request, url_for, abort, session, redirect
from services.deeplink_service import (
    create_short_link,
    get_original_url,
    increment_click_count,
    get_links_for_user, # Added import
    extract_video_id,
    validate_video_id
)
from functools import wraps
from datetime import datetime # Added import
from google.cloud.firestore_v1.types import Timestamp as FirestoreTimestamp # Added import

# Placeholder login_required decorator (ensure this is correctly implemented in your auth system)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: # Assumes 'user_id' is set in session upon login
            # Redirect to login, preserving the originally requested page
            return redirect(url_for('auth_bp.login', next=request.url)) # Assuming 'auth_bp.login' is your login route
        return f(*args, **kwargs)
    return decorated_function

deeplink_bp = Blueprint('deeplink', __name__, url_prefix='/apps/deeplink') # Added url_prefix for consistency if needed

@deeplink_bp.route('/profile/converter', methods=['GET', 'POST']) # Renamed route slightly for clarity
@login_required
def user_deeplink_converter_page():
    user_id = session.get('user_id')
    user_email = session.get('user_email')

    short_url_display = None
    error = None
    original_url_submitted = None
    success_message = None

    if not user_id or not user_email: # Ensure user identity is fully available
        error = "User identity not found. Please log in again."
        # It might be better to redirect to login or show a more generic error page
        return render_template('user_deeplink_converter.html', error=error, user_email=user_email)

    if request.method == 'POST':
        original_url_submitted = request.form.get('original_url', '').strip()

        if not original_url_submitted:
            error = "Please enter a URL to shorten."
        elif not (original_url_submitted.startswith('http://') or original_url_submitted.startswith('https://')):
            error = "Invalid URL. Please ensure it starts with http:// or https://"
        else:
            try:
                short_code = create_short_link(original_url_submitted, user_id, user_email)
                short_url_display = url_for('deeplink.redirect_to_original', short_code=short_code, _external=True)
                success_message = "Successfully created your short link!"
            except Exception as e:
                # Log the exception e with logger for server-side diagnosis
                # logger.error(f"Error creating short link for user {user_id}: {e}")
                error = "Could not create short link. Please try again later."

    return render_template('user_deeplink_converter.html',
                           deep_url=short_url_display, # Changed from short_url to deep_url to match template
                           error=error,
                           original_url=original_url_submitted,
                           user_email=user_email,
                           success_message=success_message)

@deeplink_bp.route('/r/<string:short_code>')
def redirect_to_original(short_code):
    original_url = get_original_url(short_code)
    if original_url:
        increment_click_count(short_code) # Increment before redirecting
        return redirect(original_url)
    else:
        # Render a custom 404 page for broken links if available
        # return render_template('404_link_not_found.html'), 404
        abort(404, description="Short link not found or expired.")

# --- Existing YouTube-specific routes (kept for now) ---
@deeplink_bp.route('/youtube-converter', methods=['GET', 'POST']) # Changed route to avoid conflict
def show_deeplink_youtube(): # Renamed function
    """Handle the YouTube-specific deep link converter interface."""
    deep_url = None
    error = None
    
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url', '')
        video_id = extract_video_id(youtube_url)
        
        if not video_id or not validate_video_id(video_id):
            error = "Invalid YouTube URL. Please enter a valid URL."
        else:
            # Generate the deep link URL
            deep_url = url_for('deeplink.dl_redirect_youtube', # Renamed redirect function
                             video_id=video_id, 
                             _external=True)
    
    return render_template('deeplink.html', # This template might need to be specific for YouTube or updated
                         deep_url=deep_url,
                         error=error)

@deeplink_bp.route('/dl-yt/<video_id>') # Changed route to avoid conflict
def dl_redirect_youtube(video_id): # Renamed function
    """Handle YouTube-specific deep link redirection based on User-Agent."""
    if not validate_video_id(video_id):
        abort(404)
        
    # This template likely shows options for opening in YouTube app vs. browser
    return render_template('redirect.html', video_id=video_id)


@deeplink_bp.route('/profile/my-links', methods=['GET'])
@login_required
def my_links_page():
    user_id = session.get('user_id')
    user_email = session.get('user_email')

    if not user_id: # Should be caught by @login_required, but good for defense
        return redirect(url_for('auth_bp.login', next=request.url)) # Corrected to auth_bp.login

    user_links = []
    try:
        fetched_links = get_links_for_user(user_id)
        for link_data in fetched_links:
            link_data['short_url_display'] = url_for('deeplink.redirect_to_original', short_code=link_data['short_code'], _external=True)
            created_at_val = link_data.get('created_at')
            if isinstance(created_at_val, FirestoreTimestamp):
                dt_obj = created_at_val.to_datetime()
                # Format datetime with timezone if available, otherwise assume UTC
                link_data['created_at_display'] = dt_obj.strftime('%Y-%m-%d %H:%M') + (f" {dt_obj.tzname()}" if dt_obj.tzinfo else " UTC")
            elif isinstance(created_at_val, datetime): # Handle if it's already a Python datetime
                link_data['created_at_display'] = created_at_val.strftime('%Y-%m-%d %H:%M') + (f" {created_at_val.tzname()}" if created_at_val.tzinfo else " UTC")
            else:
                link_data['created_at_display'] = str(created_at_val) if created_at_val else 'N/A'
            user_links.append(link_data)
    except Exception as e:
        # In a real app, log this error: logger.error(f"Error fetching links for user {user_id}: {e}")
        # For now, we can set an error message for the template if needed
        # error_message = "Could not load your links at this time. Please try again later."
        pass # Silently fail for now, or pass an error to the template

    return render_template('my_links.html',
                           user_email=user_email,
                           links=user_links,
                           title="My Shortened Links")
