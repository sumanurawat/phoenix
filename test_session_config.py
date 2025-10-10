#!/usr/bin/env python3
"""
Test script to verify session configuration changes.
Tests that the app can be configured with cookie-based sessions.
"""
import sys
from datetime import timedelta

def test_config_imports():
    """Test that all session config values can be imported."""
    print("Testing config imports...")
    try:
        from config.settings import (
            SESSION_TYPE, SESSION_PERMANENT, SESSION_USE_SIGNER,
            SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY,
            SESSION_COOKIE_SAMESITE, PERMANENT_SESSION_LIFETIME
        )
        
        print("✓ All config imports successful")
        
        # Verify values
        assert SESSION_TYPE is None, f"Expected SESSION_TYPE to be None, got {SESSION_TYPE}"
        assert SESSION_PERMANENT is True, f"Expected SESSION_PERMANENT to be True, got {SESSION_PERMANENT}"
        assert SESSION_USE_SIGNER is True, f"Expected SESSION_USE_SIGNER to be True, got {SESSION_USE_SIGNER}"
        # SESSION_COOKIE_SECURE can be True or False depending on environment
        assert isinstance(SESSION_COOKIE_SECURE, bool), f"Expected SESSION_COOKIE_SECURE to be bool, got {type(SESSION_COOKIE_SECURE)}"
        assert SESSION_COOKIE_HTTPONLY is True, f"Expected SESSION_COOKIE_HTTPONLY to be True, got {SESSION_COOKIE_HTTPONLY}"
        assert SESSION_COOKIE_SAMESITE == 'Lax', f"Expected SESSION_COOKIE_SAMESITE to be 'Lax', got {SESSION_COOKIE_SAMESITE}"
        assert isinstance(PERMANENT_SESSION_LIFETIME, timedelta), f"Expected PERMANENT_SESSION_LIFETIME to be timedelta, got {type(PERMANENT_SESSION_LIFETIME)}"
        assert PERMANENT_SESSION_LIFETIME.days == 7, f"Expected 7 days, got {PERMANENT_SESSION_LIFETIME.days} days"
        
        print("✓ All config values are correct")
        print(f"  SESSION_TYPE: {SESSION_TYPE}")
        print(f"  SESSION_PERMANENT: {SESSION_PERMANENT}")
        print(f"  SESSION_USE_SIGNER: {SESSION_USE_SIGNER}")
        print(f"  SESSION_COOKIE_SECURE: {SESSION_COOKIE_SECURE}")
        print(f"  SESSION_COOKIE_HTTPONLY: {SESSION_COOKIE_HTTPONLY}")
        print(f"  SESSION_COOKIE_SAMESITE: {SESSION_COOKIE_SAMESITE}")
        print(f"  PERMANENT_SESSION_LIFETIME: {PERMANENT_SESSION_LIFETIME}")
        
        return True
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False


def test_flask_session_setup():
    """Test that Flask app can be configured with new session settings."""
    print("\nTesting Flask session setup...")
    try:
        # Mock minimal env vars needed
        import os
        os.environ.setdefault('SECRET_KEY', 'test-secret-key-minimum-32-chars-required-for-signing')
        os.environ.setdefault('FLASK_ENV', 'development')
        # Test with SECURE=false for local development
        os.environ['SESSION_COOKIE_SECURE'] = 'false'
        
        # Import Flask and flask_session
        from flask import Flask, session as flask_session
        from flask_session import Session
        
        # Reload config to pick up environment variable
        import importlib
        import config.settings
        importlib.reload(config.settings)
        
        from config.settings import (
            SESSION_TYPE, SESSION_PERMANENT, SESSION_USE_SIGNER,
            SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY,
            SESSION_COOKIE_SAMESITE, PERMANENT_SESSION_LIFETIME,
            SECRET_KEY
        )
        
        # Verify SECURE is False in dev mode
        assert SESSION_COOKIE_SECURE is False, f"Expected SESSION_COOKIE_SECURE to be False in dev, got {SESSION_COOKIE_SECURE}"
        print("✓ SESSION_COOKIE_SECURE correctly set to False for local development")
        
        # Create minimal Flask app
        app = Flask(__name__)
        # Ensure we use a proper secret key for signing
        app.secret_key = 'test-secret-key-minimum-32-chars-required-for-signing'
        app.config['SECRET_KEY'] = app.secret_key
        app.config['TESTING'] = True
        
        # Configure session (same as in app.py)
        if SESSION_TYPE is not None:
            # Use flask-session for server-side sessions
            app.config["SESSION_TYPE"] = SESSION_TYPE
            Session(app)
        # else: Use Flask's built-in cookie-based sessions
        
        # Common session configuration
        app.config["SESSION_PERMANENT"] = SESSION_PERMANENT
        app.config["SESSION_USE_SIGNER"] = SESSION_USE_SIGNER
        app.config["SESSION_COOKIE_SECURE"] = SESSION_COOKIE_SECURE
        app.config["SESSION_COOKIE_HTTPONLY"] = SESSION_COOKIE_HTTPONLY
        app.config["SESSION_COOKIE_SAMESITE"] = SESSION_COOKIE_SAMESITE
        app.config["PERMANENT_SESSION_LIFETIME"] = PERMANENT_SESSION_LIFETIME
        
        print("✓ Flask session configured successfully")
        print(f"  App SESSION_TYPE: {app.config.get('SESSION_TYPE')}")
        print(f"  App SESSION_PERMANENT: {app.config.get('SESSION_PERMANENT')}")
        print(f"  App SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
        print(f"  App PERMANENT_SESSION_LIFETIME: {app.config.get('PERMANENT_SESSION_LIFETIME')}")
        
        # Test that session works with a simple route
        @app.route('/test')
        def test_route():
            from flask import session
            session['test_key'] = 'test_value'
            session.permanent = True  # Enable permanent session
            return 'OK'
        
        @app.route('/check')
        def check_route():
            from flask import session
            return session.get('test_key', 'not_found')
        
        with app.test_client() as client:
            # First request - set session
            response = client.get('/test')
            assert response.status_code == 200
            # Check that cookie was set
            assert 'Set-Cookie' in response.headers
            print("✓ Session cookie set successfully")
            
            # Verify cookie attributes
            cookie_header = response.headers['Set-Cookie']
            if app.config['SESSION_COOKIE_HTTPONLY']:
                assert 'HttpOnly' in cookie_header, "HttpOnly attribute missing"
                print("✓ HttpOnly cookie attribute set")
            if app.config['SESSION_COOKIE_SAMESITE']:
                assert 'SameSite=Lax' in cookie_header, "SameSite attribute incorrect"
                print("✓ SameSite=Lax cookie attribute set")
            # Verify Secure is NOT set in development mode
            if not app.config['SESSION_COOKIE_SECURE']:
                assert 'Secure;' not in cookie_header, "Secure attribute should not be set in development"
                print("✓ Secure cookie attribute correctly not set (development mode)")
            
            # Second request - verify session persists with cookie
            response2 = client.get('/check')
            assert response2.status_code == 200
            assert response2.data.decode() == 'test_value', "Session value not persisted"
            print("✓ Session persists across requests (cookie-based)")
        
        return True
    except Exception as e:
        print(f"✗ Flask session setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Session Configuration Test")
    print("=" * 60)
    
    all_passed = True
    
    if not test_config_imports():
        all_passed = False
    
    if not test_flask_session_setup():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        sys.exit(1)
