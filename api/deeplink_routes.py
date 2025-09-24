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
    get_link_by_short_code
)
from services.click_tracking_service import ClickTrackingService
from functools import wraps
from datetime import datetime
from api.auth_routes import login_required
from middleware.csrf_protection import csrf_protect

deeplink_bp = Blueprint('deeplink', __name__, url_prefix='/apps/deeplink')

# Initialize click tracking service
click_tracking_service = ClickTrackingService()

# NEW COMBINED PAGE ROUTE
@deeplink_bp.route('/profile/links', methods=['GET', 'POST'])
@csrf_protect
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

    # Fetch recent clicks for this user
    recent_clicks = []
    clicks_pagination = None
    try:
        # Get pagination parameters from request
        page_size = int(request.args.get('page_size', 20))  # Default 20 clicks per page
        offset = int(request.args.get('offset', 0))
        
        # Limit page size to prevent abuse
        page_size = min(page_size, 100)
        
        # Get recent clicks for all user's links
        clicks_result = click_tracking_service.get_recent_clicks_for_user(
            user_id, 
            limit=page_size, 
            offset=offset
        )
        
        clicks_pagination = {
            'total_count': clicks_result.get('total_count', 0),
            'current_page_count': clicks_result.get('current_page_count', 0),
            'has_more': clicks_result.get('has_more', False),
            'offset': clicks_result.get('offset', 0),
            'limit': clicks_result.get('limit', page_size),
            'next_offset': offset + page_size if clicks_result.get('has_more', False) else None
        }
        
        for click_data in clicks_result.get('clicks', []):
            # Format click data for display
            clicked_at = click_data.get('clicked_at')
            if isinstance(clicked_at, datetime):
                timezone_str = clicked_at.tzname()
                if timezone_str and timezone_str != "UTC":
                    click_data['clicked_at_display'] = clicked_at.strftime('%Y-%m-%d %H:%M %Z')
                else:
                    click_data['clicked_at_display'] = clicked_at.strftime('%Y-%m-%d %H:%M') + " UTC"
            elif clicked_at:
                click_data['clicked_at_display'] = str(clicked_at)
            else:
                click_data['clicked_at_display'] = 'N/A'
            
            # Add display URL for the short link
            short_code = click_data.get('short_code')
            if short_code:
                click_data['short_url_display'] = url_for('deeplink.redirect_to_original', short_code=short_code, _external=True)
            
            # Format location using geolocation service if available
            if hasattr(click_tracking_service, 'geo_service'):
                location_dict = {
                    'country': click_data.get('country', 'Unknown'),
                    'city': click_data.get('city', 'Unknown'),
                    'region': click_data.get('region', 'Unknown')
                }
                click_data['location_display'] = click_tracking_service.geo_service.get_location_display(location_dict)
            else:
                # Fallback to simple location display
                if click_data.get('country') and click_data.get('country') != 'Unknown':
                    location_parts = [click_data['country']]
                    if click_data.get('city') and click_data['city'] != 'Unknown':
                        location_parts.insert(0, click_data['city'])
                    click_data['location_display'] = ', '.join(location_parts)
                else:
                    click_data['location_display'] = 'Unknown'
            
            recent_clicks.append(click_data)
            
    except Exception as e:
        logging.exception(f"Error fetching recent clicks for user {user_id}: {e}")
        # Don't fail the page load if clicks can't be fetched

    return render_template('manage_links.html',
                           user_email=user_email,
                           links=user_links,
                           recent_clicks=recent_clicks,
                           clicks_pagination=clicks_pagination,
                           original_url=original_url_submitted, # For repopulating form
                           short_link_generated=short_url_display, # The generated/retrieved short URL
                           success_message=success_message,
                           error_message=error_message,
                           title="Manage Links")


@deeplink_bp.route('/profile/links/delete/<string:short_code>', methods=['POST'])
@csrf_protect
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
    """Redirect to the original URL and increment click count with detailed tracking."""
    try:
        original_url = get_original_url(short_code)
        if original_url:
            # Prepare request data for click tracking
            request_data = {
                'user_agent': request.headers.get('User-Agent', ''),
                'referrer': request.headers.get('Referer', ''),
                'X-Forwarded-For': request.headers.get('X-Forwarded-For'),
                'X-Real-IP': request.headers.get('X-Real-IP'),
                'remote_addr': request.remote_addr
            }
            
            # Increment click count with detailed tracking
            increment_click_count(short_code, request_data)
            
            return redirect(original_url, code=302)
        else:
            abort(404, description="Short link not found or expired.")
    except Exception as e:
        logging.exception(f"Error redirecting short code {short_code}: {e}")
        abort(500, description="An error occurred while processing your request.")

@deeplink_bp.route('/debug/analytics/<short_code>')
def debug_analytics(short_code):
    """Debug analytics without authentication for testing."""
    try:
        # Get analytics data directly
        analytics = click_tracking_service.get_click_analytics(short_code)
        
        # Return JSON for easy debugging
        from flask import jsonify
        return jsonify({
            'short_code': short_code,
            'analytics': analytics,
            'analytics_type': type(analytics).__name__,
            'total_clicks': analytics.get('total_clicks', 'KEY_MISSING'),
            'keys': list(analytics.keys()) if isinstance(analytics, dict) else 'NOT_DICT'
        })
        
    except Exception as e:
        from flask import jsonify
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@deeplink_bp.route('/profile/links/<short_code>/analytics')
@login_required
def link_analytics(short_code):
    """Display detailed analytics for a specific link."""
    try:
        user_id = session.get('user_id')
        
        # Verify user owns this link
        link_data = get_link_by_short_code(short_code)
        if not link_data or link_data.get('user_id') != user_id:
            abort(404, description='Link not found or you do not have permission to view it.')
        
        # Get analytics data
        analytics = click_tracking_service.get_click_analytics(short_code)
        
        # Debug logging
        logging.info(f"Analytics route for {short_code}: analytics={analytics}")
        logging.info(f"Analytics total_clicks: {analytics.get('total_clicks', 'KEY_MISSING')}")
        logging.info(f"Analytics type: {type(analytics)}")
        logging.info(f"Analytics keys: {list(analytics.keys()) if isinstance(analytics, dict) else 'NOT_DICT'}")
        
        # Test the exact condition that the template uses
        total_clicks = analytics.get('total_clicks', 0)
        logging.info(f"Template condition test: analytics.total_clicks == 0 -> {total_clicks == 0}")
        logging.info(f"Actual total_clicks value: {total_clicks} (type: {type(total_clicks)})")
        
        return render_template('link_analytics.html', 
                             link_data=link_data,
                             analytics=analytics,
                             short_code=short_code,
                             title='Link Analytics')
        
    except Exception as e:
        logging.error(f"Error getting analytics for {short_code}: {e}")
        abort(500, description='Error loading analytics data.')
