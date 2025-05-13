"""
Deep Link Routes

Routes for handling YouTube deep link conversion
"""
from flask import Blueprint, render_template, request, url_for, abort
from services.deeplink_service import extract_video_id, validate_video_id

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
