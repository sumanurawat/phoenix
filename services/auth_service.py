"""Service for handling authentication via Firebase Identity Platform.

Enhancements:
 - Properly URL-encode Google OAuth parameters (previous manual join could cause
     redirect_uri_mismatch if characters weren't encoded exactly as Google expects).
 - Add structured debug logging for the computed redirect_uri and state to help
     diagnose production issues (e.g., mismatched domains, missing HTTPS, trailing slash).
"""
import os
import json
import logging
import requests
import urllib.parse
import firebase_admin
from firebase_admin import auth, credentials

class AuthService:
    """Interact with Firebase Authentication."""
    def __init__(self):
        self.api_key = os.getenv("FIREBASE_API_KEY")
        self.base_url = "https://identitytoolkit.googleapis.com/v1"
        
        # Initialize Firebase Admin SDK (for token verification and admin tasks)
        creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
        if not firebase_admin._apps:
            try:
                # Try to load from JSON file
                if os.path.exists(creds_path):
                    cred = credentials.Certificate(creds_path)
                # Alternatively, load from environment variable
                elif os.getenv("FIREBASE_CREDENTIALS"):
                    cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
                    cred = credentials.Certificate(cred_dict)
                else:
                    # Use default credentials (from GCP environment)
                    cred = credentials.ApplicationDefault()
                
                firebase_admin.initialize_app(cred)
            except Exception as e:
                print(f"Firebase Admin initialization error: {e}")

    def signup_email_password(self, email: str, password: str) -> dict:
        """Create a new user using email and password."""
        url = f"{self.base_url}/accounts:signUp?key={self.api_key}"
        resp = requests.post(url, json={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        })
        resp.raise_for_status()
        return resp.json()

    def login_email_password(self, email: str, password: str) -> dict:
        """Sign in a user using email and password."""
        url = f"{self.base_url}/accounts:signInWithPassword?key={self.api_key}"
        resp = requests.post(url, json={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        })
        resp.raise_for_status()
        return resp.json()
        
    def verify_id_token(self, id_token: str) -> dict:
        """Verify an ID token using Firebase Admin SDK."""
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            raise ValueError(f"Invalid ID token: {e}")
            
    def get_google_auth_url(self, redirect_uri: str = None) -> str:
        """Get Google OAuth URL for sign-in."""
        # Generate state token to prevent CSRF
        import secrets
        state = secrets.token_urlsafe(16)
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not client_id:
            logging.error("GOOGLE_CLIENT_ID not set; Google OAuth cannot proceed")
            raise RuntimeError("Missing GOOGLE_CLIENT_ID env var")

        # Use v2 endpoint (recommended). Add 'openid' scope for ID token clarity.
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            # Optional UX improvements (uncomment if needed):
            # "prompt": "select_account",
            # "access_type": "offline",
        }

        # Proper URL encoding (was previously manual concatenation)
        encoded = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, quote_via=urllib.parse.quote)

        # Log (info) the redirect base for debugging redirect_uri_mismatch (exclude state in normal logs?)
        logging.info("Generating Google OAuth URL", extra={
            "oauth_redirect_uri": redirect_uri,
            "oauth_client_id_suffix": client_id[-12:] if len(client_id or '') > 12 else client_id,
        })

        return f"https://accounts.google.com/o/oauth2/v2/auth?{encoded}", state
