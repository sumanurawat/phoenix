"""
Centralized CSRF protection middleware for Phoenix AI Platform.

This module provides a unified, decorator-based approach to CSRF protection
that can be consistently applied across all routes and apps.
"""
import functools
import secrets
import logging
from flask import session, request, jsonify, abort
from typing import Optional

logger = logging.getLogger(__name__)

class CSRFProtection:
    """Centralized CSRF protection for Phoenix platform."""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize CSRF protection with Flask app."""
        app.before_request(self._ensure_csrf_token)
        app.context_processor(self._inject_csrf_token)
        
        # Add disable flag for development/testing
        self.disabled = app.config.get('DISABLE_CSRF', False)
    
    def _ensure_csrf_token(self):
        """Ensure CSRF token exists in session."""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
    
    def _inject_csrf_token(self):
        """Inject CSRF token into template context."""
        return {'csrf_token': lambda: session.get('csrf_token')}
    
    def _get_token_from_request(self) -> Optional[str]:
        """Extract CSRF token from request (headers, form, or JSON body)."""
        # Try header first
        token = request.headers.get('X-CSRF-Token')
        if token:
            return token
        
        # Try form data
        token = request.form.get('csrf_token')
        if token:
            return token
        
        # Try JSON body
        if request.is_json:
            try:
                data = request.get_json(silent=True)
                if data and isinstance(data, dict):
                    token = data.get('csrf_token')
                    if token:
                        return token
            except Exception:
                pass
        
        return None
    
    def _validate_token(self, sent_token: str) -> bool:
        """Validate CSRF token against session."""
        session_token = session.get('csrf_token')
        
        if not session_token or not sent_token:
            return False
        
        # Use secrets.compare_digest for timing attack protection
        return secrets.compare_digest(session_token, sent_token)
    
    def protect(self, f):
        """
        Decorator to add CSRF protection to a route.
        
        Usage:
            @app.route('/api/protected', methods=['POST'])
            @csrf.protect
            def protected_route():
                return jsonify({'status': 'success'})
        """
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip CSRF check if disabled
            if self.disabled:
                return f(*args, **kwargs)
            
            # Only protect non-GET requests
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                sent_token = self._get_token_from_request()
                
                if not sent_token or not self._validate_token(sent_token):
                    session_token = session.get('csrf_token', '')
                    header_token = request.headers.get('X-CSRF-Token', '')
                    form_token = request.form.get('csrf_token', '')
                    json_token = self._get_json_token() or ''
                    
                    logger.error('🔒 CSRF validation failed', extra={
                        'method': request.method,
                        'endpoint': request.endpoint,
                        'path': request.path,
                        'remote_addr': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent', ''),
                        'referer': request.headers.get('Referer', ''),
                        'content_type': request.content_type,
                        'has_header_token': bool(header_token),
                        'has_form_token': bool(form_token),
                        'has_json_token': bool(json_token),
                        'session_has_token': bool(session_token),
                        'session_token_length': len(session_token) if session_token else 0,
                        'sent_token_length': len(sent_token) if sent_token else 0,
                        'sent_token_source': 'header' if header_token else ('form' if form_token else ('json' if json_token else 'none')),
                        'tokens_match': bool(sent_token and session_token and secrets.compare_digest(session_token, sent_token))
                    })
                    
                    # Log the actual token values (first 8 chars) for debugging
                    logger.error(f'🔍 CSRF Token Debug - Session: {session_token[:8]}..., Sent: {sent_token[:8] if sent_token else "None"}...')
                    
                    # Return JSON error for API routes
                    if request.path.startswith('/api/'):
                        return jsonify({
                            'success': False,
                            'error': 'Invalid or missing CSRF token',
                            'code': 'csrf_failed'
                        }), 400
                    
                    # Return 400 error for other routes
                    return abort(400, description='Invalid or missing CSRF token')
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def _get_json_token(self) -> Optional[str]:
        """Helper to extract token from JSON body for logging."""
        if request.is_json:
            try:
                data = request.get_json(silent=True)
                if data and isinstance(data, dict):
                    return data.get('csrf_token')
            except Exception:
                pass
        return None

# Global instance to be imported by other modules
csrf = CSRFProtection()

# Convenience decorator for direct import
csrf_protect = csrf.protect