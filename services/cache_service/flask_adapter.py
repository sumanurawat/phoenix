"""
Flask-Session Adapter for Cache Service

Integrates the cache service with Flask's session management.
This adapter allows Flask to use our cache service (Firestore/Redis)
as the session backend.

Usage in Flask app:
    from services.cache_service.flask_adapter import CacheSessionInterface

    app = Flask(__name__)
    app.session_interface = CacheSessionInterface()
"""

import pickle
import logging
from uuid import uuid4
from datetime import datetime, timedelta
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict

from .factory import get_cache_service


logger = logging.getLogger(__name__)


class CacheSession(CallbackDict, SessionMixin):
    """
    Custom session class that works with our cache service.
    """

    def __init__(self, initial=None, sid=None, new=False):
        def on_update(self):
            self.modified = True

        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False


class CacheSessionInterface(SessionInterface):
    """
    Flask session interface using cache service backend.

    This allows Flask sessions to be stored in Firestore (or Redis)
    instead of the default filesystem, making it work on Cloud Run.

    Features:
    - Automatic session ID generation
    - Configurable TTL (default: 30 days)
    - Secure session cookies
    - Works with any cache backend (Firestore, Redis, etc.)
    """

    serializer = pickle  # Use pickle for session serialization
    session_class = CacheSession

    def __init__(self, key_prefix: str = 'session:', permanent_lifetime: int = 2592000):
        """
        Initialize session interface.

        Args:
            key_prefix: Prefix for session keys (default: 'session:')
            permanent_lifetime: Session TTL in seconds (default: 30 days)
        """
        self.key_prefix = key_prefix
        self.permanent_lifetime = permanent_lifetime
        self.cache = get_cache_service()
        logger.info(f"CacheSessionInterface initialized with {type(self.cache).__name__}")

    def _generate_sid(self) -> str:
        """Generate a unique session ID."""
        return str(uuid4())

    def _get_cache_key(self, sid: str) -> str:
        """Convert session ID to cache key."""
        return f"{self.key_prefix}{sid}"

    def open_session(self, app, request):
        """
        Load session from cache.

        Called by Flask for each request to load the session.

        Args:
            app: Flask app instance
            request: Flask request object

        Returns:
            Session object
        """
        # Get session ID from cookie
        cookie_name = self.get_cookie_name(app)
        sid = request.cookies.get(cookie_name)

        logger.info(f"🔓 OPEN_SESSION: path={request.path} | cookie_name={cookie_name}")

        if not sid:
            # No session cookie - create new session
            sid = self._generate_sid()
            logger.info(f"🆕 Creating new session (no cookie): {sid[:8]}...")
            return self.session_class(sid=sid, new=True)

        logger.info(f"🔑 Found session cookie: {sid[:8]}...")

        # Try to load existing session from cache
        cache_key = self._get_cache_key(sid)
        cached_data = self.cache.get(cache_key)

        if cached_data is None:
            # Session not found or expired - create new one
            logger.warning(f"⚠️  Session not found in cache, creating new: {sid[:8]}...")
            sid = self._generate_sid()
            return self.session_class(sid=sid, new=True)

        # Deserialize session data
        try:
            session_data = self.serializer.loads(cached_data.get('session_data', b''))
            logger.info(f"✅ Loaded session: {sid[:8]}... | keys={list(session_data.keys())}")
            return self.session_class(session_data, sid=sid)
        except Exception as e:
            logger.error(f"💥 Error deserializing session {sid[:8]}...: {e}")
            # Create new session on deserialization error
            sid = self._generate_sid()
            return self.session_class(sid=sid, new=True)

    def save_session(self, app, session, response):
        """
        Save session to cache.

        Called by Flask after each request to save the session.

        Args:
            app: Flask app instance
            session: Session object
            response: Flask response object
        """
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)

        logger.info(f"💾 SAVE_SESSION: sid={session.sid[:8]}... | modified={session.modified} | new={session.new}")

        # If session is empty and not new, delete it
        if not session:
            logger.info(f"🗑️  Session empty, deleting: {session.sid[:8]}...")
            if session.modified:
                self.cache.delete(self._get_cache_key(session.sid))
                response.delete_cookie(
                    self.get_cookie_name(app),
                    domain=domain,
                    path=path
                )
            return

        # Determine session expiration
        if session.permanent:
            ttl = self.permanent_lifetime
        else:
            ttl = int(timedelta(hours=24).total_seconds())  # 24 hours for non-permanent

        logger.info(f"⏱️  Session TTL: {ttl}s ({ttl/3600:.1f}h) | permanent={session.permanent}")

        # Set cookie expiration
        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        samesite = self.get_cookie_samesite(app)
        expires = datetime.utcnow() + timedelta(seconds=ttl)

        # Serialize and save session data to cache
        if session.modified or session.new:
            try:
                session_dict = dict(session)
                session_data = self.serializer.dumps(session_dict)
                cache_key = self._get_cache_key(session.sid)

                logger.info(f"📝 Session data keys: {list(session_dict.keys())}")

                # Store in cache
                success = self.cache.set(
                    key=cache_key,
                    value={'session_data': session_data},
                    ttl=ttl
                )

                if success:
                    logger.info(f"✅ Saved session: {session.sid[:8]}... (TTL: {ttl}s)")
                else:
                    logger.error(f"❌ Failed to save session: {session.sid[:8]}...")

            except Exception as e:
                logger.error(f"💥 Error saving session {session.sid[:8]}...: {e}", exc_info=True)

        # Set session cookie
        logger.info(f"🍪 Setting cookie: {self.get_cookie_name(app)} | domain={domain} | path={path} | secure={secure} | httponly={httponly} | samesite={samesite}")
        response.set_cookie(
            self.get_cookie_name(app),
            session.sid,
            expires=expires,
            httponly=httponly,
            domain=domain,
            path=path,
            secure=secure,
            samesite=samesite
        )
