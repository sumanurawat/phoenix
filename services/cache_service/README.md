# Cache Service - Reusable Session & Key-Value Store

**Version:** 1.0.0
**Status:** Production-ready
**Current Backend:** Google Cloud Firestore
**Future Support:** Redis, Memcached

---

## Overview

A production-ready, backend-agnostic caching microservice designed for session management and general key-value caching. Built specifically to solve Cloud Run's ephemeral filesystem limitation, but designed to be reusable across any Flask/Python project.

### Why This Service Exists

**Problem:** friedmomo.com runs on Google Cloud Run, which uses ephemeral containers. The default Flask filesystem-based sessions don't persist between requests, causing OAuth login failures.

**Solution:** This cache service stores sessions in Google Cloud Firestore (persistent database) with automatic TTL-based cleanup. The abstracted design allows future migration to Redis without code changes.

---

## Quick Start (friedmomo.com)

### 1. Install Dependencies

No additional dependencies needed! Uses existing `firebase-admin` and `flask`.

### 2. Run Setup Script

```bash
cd /Users/sumanurawat/documents/github/phoenix
python3 services/cache_service/setup_firestore.py
```

This creates the `cache_sessions` collection in Firestore and enables TTL policy.

### 3. Configure Environment

Add to your Cloud Run environment variables:

```bash
CACHE_BACKEND=firestore
CACHE_COLLECTION_NAME=cache_sessions
```

### 4. Deploy

```bash
gcloud run deploy phoenix --source .
```

That's it! OAuth login will now work on friedmomo.com.

---

## Architecture

```
Flask App (friedmomo.com)
    │
    ├─> Flask Session Cookie (client-side)
    │       ├─ Name: "session"
    │       ├─ Value: UUID (e.g., "abc123-def456")
    │       └─ Attributes: Secure, HttpOnly, SameSite=None
    │
    └─> CacheSessionInterface (server-side)
            │
            ├─> get_cache_service() → FirestoreCache
            │       │
            │       └─> Firestore Collection: cache_sessions
            │               │
            │               └─> Document: friedmomo:session:{UUID}
            │                       ├─ data: {user_id, email, tokens, ...}
            │                       ├─ created_at: Timestamp
            │                       ├─ expires_at: Timestamp (TTL field)
            │                       └─ last_accessed: Timestamp
            │
            └─> Future: RedisCache (swap by changing CACHE_BACKEND env var)
```

---

## Usage Examples

### Basic Key-Value Caching

```python
from services.cache_service import get_cache_service

cache = get_cache_service()

# Store data with 1-hour TTL
cache.set("user:123:preferences", {
    "theme": "dark",
    "language": "en"
}, ttl=3600)

# Retrieve data
prefs = cache.get("user:123:preferences")
# Returns: {"theme": "dark", "language": "en"} or None if expired/not found

# Check if exists
if cache.exists("user:123:preferences"):
    print("Preferences cached!")

# Delete manually
cache.delete("user:123:preferences")
```

### Flask Session Integration (friedmomo.com use case)

```python
# app.py
from flask import Flask
from services.cache_service.flask_adapter import CacheSessionInterface

app = Flask(__name__)
app.session_interface = CacheSessionInterface(
    key_prefix='friedmomo:session:',
    permanent_lifetime=2592000  # 30 days
)

# That's it! Flask sessions now use Firestore
# No other code changes needed
```

### Custom Cache Use Cases

```python
# Rate limiting
def rate_limit(user_id):
    key = f"ratelimit:{user_id}"
    data = cache.get(key) or {"count": 0}
    data["count"] += 1
    cache.set(key, data, ttl=60)  # 1 minute window
    return data["count"] <= 100  # Max 100 requests/minute

# OAuth state management
def store_oauth_state(state_token, next_url):
    cache.set(f"oauth:{state_token}", {"next_url": next_url}, ttl=600)  # 10 minutes

# API response caching
def get_trending_posts():
    cached = cache.get("api:trending_posts")
    if cached:
        return cached

    posts = fetch_from_database()  # Expensive query
    cache.set("api:trending_posts", posts, ttl=300)  # 5 minutes
    return posts
```

---

## Firestore Implementation Details

### Data Structure

**Collection:** `cache_sessions`

**Document ID:** `{key_prefix}{session_id}`
Example: `friedmomo:session:abc123-def456`

**Document Fields:**
```json
{
  "data": {
    "session_data": "pickled_python_dict",
    "user_id": "firebase_uid_123",
    "email": "user@example.com",
    "csrf_token": "random_token"
  },
  "created_at": "2025-11-16T10:30:00Z",
  "expires_at": "2025-12-16T10:30:00Z",  // TTL field
  "last_accessed": "2025-11-16T15:45:00Z"
}
```

### Automatic TTL Cleanup

**How it works:**
1. When you call `cache.set(key, value, ttl=3600)`, we set `expires_at = now + 3600 seconds`
2. Firestore's TTL policy automatically deletes documents where `expires_at < now`
3. Deletion happens within 24 hours of expiration (Firestore background process)
4. No cron jobs or manual cleanup needed!

**Manual cleanup** (if you want immediate deletion):
```python
deleted_count = cache.cleanup_expired()
print(f"Deleted {deleted_count} expired sessions")
```

### When Sessions Are Deleted

1. **User logout** → Immediate deletion via `cache.delete(key)`
2. **TTL expiration** → Automatic deletion by Firestore (within 24h)
3. **Manual cleanup** → Optional via `cleanup_expired()` method

---

## Performance & Cost

### Firestore Performance (Current)

| Operation | Latency | Cost per 100K ops |
|-----------|---------|-------------------|
| Read | 5-20ms | $0.06 |
| Write | 20-50ms | $0.18 |
| Delete | 20-50ms | $0.18 |

### Estimated Monthly Costs

**For friedmomo.com (10K daily active users):**

```
Assumptions:
- 50 requests/user/day
- 20% writes (login, updates), 80% reads (page loads)

Monthly Operations:
- Reads:  10K × 50 × 30 × 0.8 = 12M reads
- Writes: 10K × 50 × 30 × 0.2 = 3M writes

Cost:
- Reads:  12M × ($0.06/100K) = $7.20
- Writes: 3M × ($0.18/100K) = $5.40
- Storage: ~20MB (under 1GB free tier) = $0
- Total: ~$12.60/month
```

**Growth projection:**
- 1K users: ~$1/month
- 10K users: ~$13/month
- 50K users: ~$60/month
- 100K users: ~$120/month *(consider Redis at this scale)*

### When to Migrate to Redis

**Migrate if any of these are true:**
1. Monthly Firestore costs exceed $200
2. You need <5ms latency for real-time features
3. You have >50K daily active users
4. You're building chat, live notifications, or collaborative editing

**Redis costs (Google Cloud Memorystore):**
- Basic M1 (1GB): $42/month - supports ~100K active sessions
- Standard M1 (1GB, HA): $84/month - production-grade with high availability

---

## Migration Guide: Firestore → Redis

When you're ready to migrate to Redis for better performance:

### Step 1: Install Redis Adapter

```python
# services/cache_service/redis_backend.py (will be created)
from .interface import CacheServiceInterface
import redis

class RedisCache(CacheServiceInterface):
    def __init__(self, host, port, password=None):
        self.client = redis.Redis(host=host, port=port, password=password)

    def get(self, key):
        data = self.client.get(key)
        return json.loads(data) if data else None

    def set(self, key, value, ttl=2592000):
        self.client.setex(key, ttl, json.dumps(value))
        return True

    # ... implement other methods
```

### Step 2: Change Environment Variable

```bash
# Before (Firestore)
CACHE_BACKEND=firestore

# After (Redis)
CACHE_BACKEND=redis
REDIS_HOST=10.0.0.3
REDIS_PORT=6379
REDIS_PASSWORD=your_password
```

### Step 3: Deploy

```bash
gcloud run deploy phoenix --source .
```

**That's it!** No application code changes. The factory pattern handles everything.

### Zero-Downtime Migration (Optional)

For extra safety, implement dual-write:

```python
# Temporarily write to both backends
old_cache = FirestoreCache()
new_cache = RedisCache()

def set(key, value, ttl):
    old_cache.set(key, value, ttl)  # Firestore
    new_cache.set(key, value, ttl)  # Redis

def get(key):
    value = new_cache.get(key)  # Try Redis first
    if value is None:
        value = old_cache.get(key)  # Fallback to Firestore
        if value:
            new_cache.set(key, value)  # Backfill Redis
    return value
```

---

## Using This Service in Other Projects

This cache service is designed to be **100% reusable**. Here's how to extract it for other projects:

### 1. Copy the Service

```bash
cp -r services/cache_service /path/to/your/project/
```

### 2. Install Dependencies

```bash
pip install firebase-admin flask
```

### 3. Initialize Firestore

```bash
python cache_service/setup_firestore.py
```

### 4. Use in Your Flask App

```python
from cache_service.flask_adapter import CacheSessionInterface

app = Flask(__name__)
app.session_interface = CacheSessionInterface()
```

### 5. (Optional) Use as Standalone Cache

```python
from cache_service import get_cache_service

cache = get_cache_service()
cache.set("mykey", {"data": "value"}, ttl=3600)
```

---

## Future: Microservice API

**Vision:** Turn this into a standalone HTTP microservice that multiple projects can call.

### Planned Features (v2.0)

1. **RESTful API**
   ```
   POST /cache/{key}         → Set value
   GET  /cache/{key}         → Get value
   DELETE /cache/{key}       → Delete value
   GET  /cache/{key}/exists  → Check existence
   ```

2. **Multi-Tenancy**
   - Each client gets an API key
   - Keys are prefixed: `{client_id}:{user_key}`
   - Isolation between clients

3. **Authentication**
   - API key validation
   - Rate limiting per client
   - Usage quotas

4. **Deployment**
   ```bash
   docker build -t cache-service .
   docker run -p 8080:8080 cache-service
   ```

5. **Client Libraries**
   ```python
   # Python client
   from cache_service_client import CacheClient

   cache = CacheClient(api_key="your_key", endpoint="https://cache.api.com")
   cache.set("key", {"value": "data"})
   ```

---

## Troubleshooting

### Issue: "Session not found" after OAuth callback

**Cause:** Firestore write didn't complete before redirect

**Solution:**
```python
# In auth_routes.py, after setting session:
session['oauth_state'] = state
session.modified = True  # Force save
time.sleep(0.1)  # Give Firestore time to write
```

### Issue: High latency (>100ms)

**Cause:** Firestore quota limits or network issues

**Solutions:**
1. Check Firestore dashboard for quota limits
2. Add Firestore indexes for queries
3. Consider Redis migration

### Issue: Sessions expire too quickly

**Cause:** TTL is too short

**Solution:**
```python
app.session_interface = CacheSessionInterface(
    permanent_lifetime=7776000  # 90 days instead of 30
)
```

### Issue: Cost is too high

**Cause:** Too many read/write operations

**Solutions:**
1. Implement client-side caching (reduce reads)
2. Batch session updates (reduce writes)
3. Migrate to Redis (fixed cost)

---

## API Reference

### `get_cache_service()`

Returns singleton cache service instance.

```python
cache = get_cache_service(force_recreate=False)
```

### `cache.set(key, value, ttl)`

Store data in cache.

**Args:**
- `key` (str): Unique identifier
- `value` (dict): Data to cache (must be JSON-serializable)
- `ttl` (int): Time-to-live in seconds (default: 2592000 = 30 days)

**Returns:** `bool` - True if successful

### `cache.get(key)`

Retrieve data from cache.

**Args:**
- `key` (str): Unique identifier

**Returns:** `dict` or `None`

### `cache.delete(key)`

Remove data from cache.

**Args:**
- `key` (str): Unique identifier

**Returns:** `bool` - True if deleted

### `cache.exists(key)`

Check if key exists and is not expired.

**Args:**
- `key` (str): Unique identifier

**Returns:** `bool`

### `cache.update_access_time(key)`

Update last_accessed timestamp.

**Args:**
- `key` (str): Unique identifier

**Returns:** `bool`

---

## Support

**Owner:** Phoenix AI Platform / friedmomo.com
**GitHub:** /documents/github/phoenix
**Questions:** Open an issue or contact the team

---

## License

Internal use for Phoenix AI Platform projects.
Can be extracted and reused in other projects with attribution.

---

**Last Updated:** 2025-11-16
**Next Review:** 2026-02-16 (Quarterly)
