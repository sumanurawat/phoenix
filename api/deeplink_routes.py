"""
Deep Link Routes

Routes for handling YouTube deep link conversion and generic URL shortening.
"""
import logging
from flask import Blueprint, render_template, request, url_for, abort, session, redirect
from services.deeplink_service import (
    create_short_link,
    get_original_url,
    increment_click_count,
    get_links_for_user,
    delete_short_link,
    extract_video_id,
    validate_video_id
)
from functools import wraps
from datetime import datetime

# Placeholder login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

deeplink_bp = Blueprint('deeplink', __name__, url_prefix='/apps/deeplink')

# NEW COMBINED PAGE ROUTE
@deeplink_bp.route('/profile/links', methods=['GET', 'POST'])
@login_required
def manage_short_links_page():
    user_id = session.get('user_id')
    user_email = session.get('user_email')

    short_url_display = None
    error_message = None
    success_message = None
    original_url_submitted = None
    user_links = []

    if not user_id or not user_email:
        # This case should ideally be handled by @login_required,
        # but as a fallback:
        error_message = "User identity not found. Please log in again."
        # Render a minimal page or redirect, as we can't fetch user-specific data.
        return render_template('manage_links.html', # Or a more generic error template
                               error_message=error_message,
                               user_email=user_email, # Might be None
                               links=user_links,
                               original_url=original_url_submitted,
                               short_link_generated=short_url_display,
                               success_message=success_message,
                               title="Manage Links")

    if request.method == 'POST':
        original_url_submitted = request.form.get('original_url', '').strip()

        if not original_url_submitted:
            error_message = "Please enter a URL to shorten."
        elif not (original_url_submitted.startswith('http://') or original_url_submitted.startswith('https://')):
            error_message = "Invalid URL. Please ensure it starts with http:// or https://"
        else:
            try:
                link_info = create_short_link(original_url_submitted, user_id, user_email)
                # link_info is {'short_code': str, 'is_new': bool, 'original_url': str}
                
                short_url_display = url_for('deeplink.redirect_to_original', short_code=link_info['short_code'], _external=True)
                
                if link_info['is_new']:
                    success_message = "🎉 Successfully created your new short link!"
                else:
                    success_message = "📎 This URL was already shortened by you. Here's your existing short link:"
                # original_url_submitted is already set from form
                
            except Exception as e:
                logging.exception(f"Error creating short link for user {user_id} with URL {original_url_submitted}: {e}")
                error_message = "Could not process your link. Please try again later."
                # Potentially check here if it's a Firestore index error for the duplicate check
                # and provide a more specific message or log for admin.

    # Fetch user links for display, for both GET and after POST
    try:
        fetched_links = get_links_for_user(user_id)
        for link_data in fetched_links:
            link_data['short_url_display'] = url_for('deeplink.redirect_to_original', short_code=link_data['short_code'], _external=True)
            created_at_val = link_data.get('created_at')
            if isinstance(created_at_val, datetime):
                timezone_str = created_at_val.tzname()
                if timezone_str and timezone_str != "UTC":
                    link_data['created_at_display'] = created_at_val.strftime('%Y-%m-%d %H:%M %Z')
                else:
                    link_data['created_at_display'] = created_at_val.strftime('%Y-%m-%d %H:%M') + " UTC"
            elif created_at_val:
                link_data['created_at_display'] = str(created_at_val)
            else:
                link_data['created_at_display'] = 'N/A'
            user_links.append(link_data)
    except Exception as e:
        logging.exception(f"Error fetching links list for user {user_id}: {e}")
        # If error_message is already set (e.g. from POST), append or decide which is more critical.
        # For now, link creation errors might be more immediate to the user action.
        if not error_message:
            error_message = "Could not load your existing links at this time. Please try again later."

    return render_template('manage_links.html',
                           user_email=user_email,
                           links=user_links,
                           original_url=original_url_submitted, # For repopulating form
                           short_link_generated=short_url_display, # The generated/retrieved short URL
                           success_message=success_message,
                           error_message=error_message,
                           title="Manage Links")


@deeplink_bp.route('/profile/links/delete/<string:short_code>', methods=['POST'])
@login_required
def delete_short_link_route(short_code):
    """Delete a short link. Returns JSON response for AJAX calls."""
    user_id = session.get('user_id')
    
    if not user_id:
        return {'success': False, 'error': 'User not authenticated'}, 401
    
    # Basic CSRF protection - check for required headers
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {'success': False, 'error': 'Invalid request'}, 403
    
    try:
        success = delete_short_link(short_code, user_id)
        
        if success:
            logging.info(f"User {user_id} successfully deleted link {short_code}")
            return {'success': True, 'message': 'Link deleted successfully'}, 200
        else:
            logging.warning(f"User {user_id} failed to delete link {short_code} - not found or not owned")
            return {'success': False, 'error': 'Link not found or you do not have permission to delete it'}, 404
            
    except Exception as e:
        logging.exception(f"Error in delete route for user {user_id}, short_code {short_code}: {e}")
        return {'success': False, 'error': 'An error occurred while deleting the link'}, 500

@deeplink_bp.route('/r/<string:short_code>')
def redirect_to_original(short_code):
    original_url = get_original_url(short_code)
    if original_url:
        increment_click_count(short_code)
        return redirect(original_url)
    else:
        abort(404, description="Short link not found or expired.")

@deeplink_bp.route('/youtube-converter', methods=['GET', 'POST'])
def show_deeplink_youtube():
    deep_url = None
    error = None
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url', '')
        video_id = extract_video_id(youtube_url)
        if not video_id or not validate_video_id(video_id):
            error = "Invalid YouTube URL. Please enter a valid URL."
        else:
            deep_url = url_for('deeplink.dl_redirect_youtube', video_id=video_id, _external=True)
    return render_template('deeplink.html', deep_url=deep_url, error=error)

@deeplink_bp.route('/dl-yt/<video_id>')
def dl_redirect_youtube(video_id):
    if not validate_video_id(video_id):
        abort(404)
    return render_template('redirect.html', video_id=video_id)
