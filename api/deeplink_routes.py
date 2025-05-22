"""
Deep Link Routes (Short Link Feature)

This blueprint handles routes related to the short link generation and redirection feature.
It provides an interface for users to create short links and handles the redirection
logic for accessing these short links, including click logging and expiration checks.
"""
from flask import Blueprint, render_template, request, url_for, abort, current_app, redirect
from services.deeplink_service import create_short_link, log_click_event
from services.auth_service import AuthService # Assumed to handle Firebase Admin initialization and ID token verification

# Note on AuthService:
# This service is expected to be initialized or configured at the application level.
# It's used here to verify Firebase ID tokens for identifying authenticated users.
# If Firebase Admin SDK is not initialized, AuthService calls might fail.

deeplink_bp = Blueprint('deeplink', __name__, template_folder='../templates') # Define blueprint

def is_valid_url(url_string):
    """
    Performs basic validation for a URL string.
    Checks if the URL is not empty and starts with 'http://' or 'https://'.
    This is a simple check and can be expanded for more robust validation if needed.
    """
    if not url_string:
        return False
    # Ensure the URL has a scheme, which is a basic requirement for web URLs.
    return url_string.startswith('http://') or url_string.startswith('https://')


@deeplink_bp.route('/deeplink', methods=['GET', 'POST'])
def show_deeplink():
    """
    Handles the short link creation page.
    GET: Displays the form to enter a URL.
    POST: Processes the form submission, attempts to create a short link,
          and displays the result (either the short URL or an error message).
          Handles both guest users and authenticated users (via Firebase ID token).
    """
    short_url = None  # Will hold the generated short URL to display to the user
    error = None      # Will hold any error message to display

    if request.method == 'POST':
        original_url = request.form.get('original_url', '').strip()
        user_email = request.form.get('user_email', '').strip() # Optional email for guest users

        user_id = None # Initialize user_id as None (for guest users)
        
        # Attempt to identify authenticated user via Firebase ID Token
        # The token is expected in the 'Authorization: Bearer <token>' header.
        auth_header = request.headers.get('Authorization')
        id_token = None
        if auth_header and auth_header.startswith('Bearer '):
            id_token = auth_header.split('Bearer ')[1]

        if id_token:
            try:
                # Initialize AuthService (assuming it might need app config, e.g., for Firebase project details)
                # In a real app, AuthService might be a global or app-context-bound instance.
                auth_service = AuthService(current_app.config) 
                decoded_token = auth_service.verify_id_token(id_token)
                if decoded_token:
                    user_id = decoded_token.get('uid') # Extract user ID from the verified token
                else:
                    # This case implies the token was considered invalid by verify_id_token
                    # but it didn't raise an exception (e.g., returned None).
                    error = "Invalid authentication token. Please log in again."
                    current_app.logger.warning(f"Token verification returned None for token: {id_token[:20]}...") # Log part of token
            except Exception as e:
                # Catch any exception during token verification (e.g., token expired, malformed, network issue with Firebase)
                current_app.logger.error(f"Firebase ID token verification failed: {e}")
                error = "Authentication failed. Please ensure you are logged in and try again."
        
        # Validate the original URL provided by the user
        if not error and not is_valid_url(original_url):
            error = "Invalid URL. Please enter a complete and valid URL (e.g., https://example.com)."
        
        # If no errors so far, proceed to create the short link
        if not error:
            try:
                # Log the attempt to create a short link
                log_message_user_part = f"User ID: {user_id}" if user_id else f"Guest Email: {user_email if user_email else 'N/A'}"
                current_app.logger.info(f"Attempting to create short link for URL: '{original_url}', {log_message_user_part}")
                
                # Call the service function to create the short link.
                # user_email is passed only if user_id is None (i.e., for guest users).
                short_code = create_short_link(
                    original_url, 
                    user_id=user_id, 
                    user_email=user_email if not user_id and user_email else None
                )
                # Construct the full short URL to display to the user
                short_url = url_for('.dl_redirect', short_code=short_code, _external=True)
                current_app.logger.info(f"Successfully created short_code: {short_code} for URL: {original_url}")

            except ValueError as e: # Handles errors from create_short_link (e.g., failed to generate unique code)
                current_app.logger.error(f"Failed to create short link for '{original_url}': {e}")
                error = str(e) # Display the service layer's error message
            except ConnectionError as e: # Handles Firestore connection issues
                current_app.logger.error(f"Firestore connection error while creating short link for '{original_url}': {e}")
                error = "The service is temporarily unavailable. Please try again later."
            except Exception as e: # Catch-all for other unexpected errors
                current_app.logger.error(f"An unexpected error occurred while creating short link for '{original_url}': {e}")
                error = "An unexpected error occurred. Please try again."

    # Render the template, passing the generated short_url and any error message.
    # For a GET request, short_url and error will be None.
    return render_template('deeplink.html', 
                         short_url=short_url,
                         error=error)

@deeplink_bp.route('/dl/<short_code>')
def dl_redirect(short_code):
    """
    Handles the redirection for a given short_code.
    This route is accessed when a user clicks a generated short link.
    It performs the following steps:
    1. Validates the short_code.
    2. Retrieves client information (IP, User-Agent, Referrer) for logging.
    3. Calls the `log_click_event` service function, which:
        a. Atomically increments the click count for the link.
        b. Logs detailed click information (including geolocation attempt) to a subcollection.
        c. Checks if the link has expired (e.g., for guest links reaching max clicks).
        d. Returns the original URL and the link's expiration status.
    4. If the link is valid and not expired, redirects the client to the original URL.
    5. If the link is expired, not found, or an error occurs, displays an appropriate error page.
    """
    if not short_code or not short_code.strip():
        current_app.logger.warning("Attempted redirect with an empty or invalid short_code.")
        abort(404) # Not Found

    # Gather client information for click logging.
    # Use 'X-Forwarded-For' if behind a proxy, otherwise 'request.remote_addr'.
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.user_agent.string if request.user_agent else "Unknown"
    # Get referrer from request.referrer (more reliable) or "Referer" header.
    referrer_url = request.referrer or request.headers.get("Referer") or "Unknown" 
    
    original_url = None
    is_expired = True # Assume link is expired or invalid by default

    try:
        current_app.logger.info(f"Processing redirect for short_code: '{short_code}', IP: {ip_address}, User-Agent: '{user_agent}'")
        
        # Call the service to log the click and get link details
        original_url, is_expired = log_click_event(short_code, ip_address, user_agent, referrer_url)
        
        # If log_click_event returns original_url as None, it means the link was not found or an error occurred in the service.
        if original_url is None:
            is_expired = True # Ensure is_expired is true for consistent error handling below
            current_app.logger.warning(f"Short_code '{short_code}' not found or error during log_click_event. Service returned no original_url.")
            # Render link_expired.html; service indicates link is effectively invalid/expired.
            # HTTP 404: Not Found is appropriate here.
            return render_template('link_expired.html', short_code=short_code, error_message="The link you followed may be invalid or expired."), 404

    except ConnectionError as e: # Handles Firestore connection issues from the service layer
        current_app.logger.error(f"Firestore connection error processing short_code '{short_code}': {e}")
        # HTTP 503: Service Unavailable
        return render_template('link_expired.html', short_code=short_code, error_message="Service is temporarily unavailable. Please try again later."), 503
    except ValueError as e: # Handles errors like "Link not found" from within the service's transaction
        current_app.logger.warning(f"ValueError (e.g., link not found) processing short_code '{short_code}': {e}")
        # HTTP 404: Not Found
        return render_template('link_expired.html', short_code=short_code, error_message="The link you followed was not found."), 404
    except Exception as e: # Catch-all for other unexpected errors from the service layer
        current_app.logger.error(f"Unexpected error processing redirect for short_code '{short_code}': {e}")
        # HTTP 500: Internal Server Error
        return render_template('link_expired.html', short_code=short_code, error_message="An unexpected error occurred while trying to process your link."), 500

    # After processing the click, check if the link is expired or original_url is still None
    if is_expired or not original_url: # original_url check is redundant if service guarantees None for errors, but safe
        current_app.logger.info(f"Short_code '{short_code}' is expired or has no valid original URL. Displaying expired page.")
        # HTTP 410: Gone - Indicates the resource is permanently unavailable.
        return render_template('link_expired.html', short_code=short_code, error_message="This link has expired or is no longer active."), 410
    else:
        # If link is valid and not expired, perform the redirection
        current_app.logger.info(f"Redirecting short_code '{short_code}' to its original URL: {original_url}")
        return redirect(original_url)
