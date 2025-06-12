"""
Deep Link Routes

Routes for handling YouTube deep link conversion
"""
from flask import Blueprint, render_template, request, url_for, abort, session, redirect
from services.deeplink_service import extract_video_id, validate_video_id
from functools import wraps

# Placeholder login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: # Assumes 'user_id' is set in session upon login
            return redirect(url_for('auth.login', next=request.url)) # 'auth.login' is typical for a login route
        return f(*args, **kwargs)
    return decorated_function

deeplink_bp = Blueprint('deeplink', __name__)

@deeplink_bp.route('/deeplink', methods=['GET', 'POST'])
def show_deeplink():
    """Handle the deep link converter interface."""
    deep_url = None
    error = None
    
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url', '')
        video_id = extract_video_id(youtube_url)
        
        if not video_id or not validate_video_id(video_id):
            error = "Invalid YouTube URL. Please enter a valid URL."
        else:
            # Generate the deep link URL
            deep_url = url_for('deeplink.dl_redirect', 
                             video_id=video_id, 
                             _external=True)
    
    return render_template('deeplink.html', 
                         deep_url=deep_url,
                         error=error)

@deeplink_bp.route('/dl/<video_id>')
def dl_redirect(video_id):
    """Handle deep link redirection based on User-Agent."""
    if not validate_video_id(video_id):
        abort(404)
        
    return render_template('redirect.html', video_id=video_id)


@deeplink_bp.route('/profile/deeplink', methods=['GET', 'POST'])
@login_required
def user_deeplink_converter_page():
    user_email = session.get('user_email')
    deep_url = None
    error = None
    original_url = None
    success_message = None

    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url', '')
        original_url = youtube_url
        video_id = extract_video_id(youtube_url)

        if not video_id or not validate_video_id(video_id):
            error = "Invalid YouTube URL. Please enter a valid URL."
        else:
            deep_url = url_for('deeplink.dl_redirect', video_id=video_id, _external=True)
            success_message = "Successfully converted your link!"

        return render_template('user_deeplink_converter.html',
                               deep_url=deep_url,
                               error=error,
                               original_url=original_url,
                               user_email=user_email,
                               success_message=success_message)

    return render_template('user_deeplink_converter.html', user_email=user_email)
