# Social Media Timeline Feature - Implementation Plan

## Overview
Build a secure social media aggregation feature that allows users to connect Instagram, YouTube, and Twitter accounts and view all their posts in a unified timeline.

**🎯 Long-Term Vision**: Evolve into a **Creator Portfolio Platform** where creators can showcase all their content in a shareable portfolio (like Linktree meets personal gallery) with granular click analytics powered by Phoenix's existing Deeplink infrastructure. See [Creator Portfolio Vision](docs/CREATOR_PORTFOLIO_VISION.md) for the full roadmap.

## Architecture Overview

### Database Schema (Firestore Collections)

#### `user_social_accounts`
```javascript
{
  id: "doc_id",
  user_id: "firebase_uid",
  platform: "instagram|youtube|twitter",
  account_type: "public|oauth",
  username: "user_handle",
  display_name: "@user_handle",
  profile_id: "platform_user_id",
  profile_url: "https://...",
  
  // OAuth only (encrypted)
  encrypted_access_token: "encrypted_string",
  encrypted_refresh_token: "encrypted_string",
  token_expires_at: "timestamp",
  scopes: ["scope1", "scope2"],
  last_token_refresh: "timestamp",
  
  // Status & metadata
  is_active: true,
  status: "active|needs_reconnection|error",
  connected_at: "timestamp",
  last_sync: "timestamp",
  posts_count: 0,
  error_message: "string|null"
}
```

#### `social_posts`
```javascript
{
  id: "doc_id",
  user_id: "firebase_uid",
  account_id: "user_social_accounts_doc_id",
  platform: "instagram|youtube|twitter",
  
  // Post data
  post_id: "platform_post_id",
  post_url: "https://...",
  content: "post_text",
  media_urls: ["url1", "url2"],
  media_type: "image|video|carousel|text",
  thumbnail_url: "https://...",
  
  // Timestamps
  posted_at: "timestamp",
  fetched_at: "timestamp",
  
  // Engagement (from platform)
  engagement: {
    likes: 0,
    comments: 0,
    shares: 0,
    views: 0
  },
  
  // 🔗 Future: Creator Portfolio Integration
  short_code: "abc123",        // Trackable short link (Phase 10+)
  share_url: "https://phoenix.ai/s/abc123",
  is_featured: false,          // Pin to portfolio
  is_hidden: false,            // Hide from public
  portfolio_order: 0,          // Manual ordering
  phoenix_clicks: 0,           // Clicks via Phoenix
  phoenix_views: 0,            // Views on Phoenix
  last_clicked_at: "timestamp" // Last engagement
}
```

#### `oauth_states` (temporary)
```javascript
{
  state: "cryptographic_token", // document ID
  user_id: "firebase_uid",
  platform: "instagram|youtube|twitter",
  created_at: "timestamp",
  expires_at: "timestamp" // 10 minutes from creation
}
```

## Implementation Phases

---

## Phase 1: Setup Basic Infrastructure ✅

### Files to Create:
1. **`services/socials_service.py`** - Core business logic
2. **`api/socials_routes.py`** - API endpoints blueprint
3. **`middleware/social_auth_middleware.py`** - Security middleware

### `services/socials_service.py` Structure:
```python
class SocialsService:
    def __init__(self)
    
    # Account Management
    def get_user_accounts(user_id) -> list
    def add_public_account(user_id, platform, username) -> dict
    def remove_account(user_id, account_id) -> None
    
    # OAuth (Phase 6)
    def initiate_oauth_flow(user_id, platform) -> dict
    def handle_oauth_callback(platform, code, state) -> str
    
    # Token Management (Phase 6)
    def _get_cipher_suite() -> Fernet
    def _get_valid_access_token(account_id) -> str
    def _refresh_access_token(account_data) -> dict
    
    # Post Fetching (Phase 4-5)
    def get_user_posts(user_id, limit=50) -> list
    def sync_account_posts(account_id) -> int
```

### Register Blueprint in `app.py`:
```python
from api.socials_routes import socials_bp
app.register_blueprint(socials_bp)
```

**Test Checkpoint**: Service imports successfully, no errors on app startup.

---

## Phase 2: Add Navigation & Landing Page ✅

### Files to Modify:
1. **`templates/base.html`** - Add Socials nav link
2. **`app.py`** - Add main route
3. **`templates/socials.html`** - Create landing page

### Navigation Link (base.html):
Add inside user dropdown menu:
```html
<li><a class="dropdown-item" href="{{ url_for('socials_page') }}">
    <i class="fas fa-share-alt me-2"></i>Socials
</a></li>
```

### Main Route (app.py):
```python
@app.route('/socials')
@login_required
def socials_page():
    """Render the Social Media Timeline page."""
    return render_template('socials.html', title='Social Timeline')
```

### Landing Page Structure:
- Empty state with icon and "Connect Your Social Accounts" message
- "Add Account" button (non-functional initially)
- Bootstrap 5 styling matching existing Phoenix UI

**Test Checkpoint**: Navigate to `/socials`, see empty state page with consistent header/footer.

---

## Phase 3: Account Management UI ✅

### Files to Create/Modify:
1. **`static/js/socials.js`** - Frontend logic
2. **`templates/socials.html`** - Add modals and account list sections
3. **`api/socials_routes.py`** - Implement API endpoints

### API Endpoints to Implement:
```python
@socials_bp.route('/accounts', methods=['GET'])
@login_required
def get_accounts()

@socials_bp.route('/accounts', methods=['POST'])
@login_required
@csrf_protect
def add_account()

@socials_bp.route('/accounts/<account_id>', methods=['DELETE'])
@login_required
@csrf_protect
def remove_account(account_id)
```

### Frontend Features:
- Add Account Modal with platform selection and username input
- Connected accounts list with platform icons
- Remove account button with confirmation
- Loading states and error messages

**Test Checkpoint**: 
1. Click "Add Account" → modal opens
2. Select platform + enter username → account saved to Firestore
3. Refresh page → see connected account
4. Click remove → account deleted

---

## Phase 4: Public Account Integration (Instagram) 🔄

### Service Methods:
```python
def _fetch_instagram_public_posts(username, limit=12) -> list
def _parse_instagram_post(post_data) -> dict
def sync_public_account_posts(account_id) -> int
```

### API Endpoint:
```python
@socials_bp.route('/accounts/<account_id>/sync', methods=['POST'])
@login_required
@csrf_protect
def sync_account(account_id)
```

### Implementation:
- Use Instagram Basic Display API (or public scraping as fallback)
- Fetch last 12 posts from public profile
- Store in `social_posts` collection
- Handle rate limiting and errors gracefully

**Test Checkpoint**:
1. Add Instagram public account
2. Click "Sync Posts" button
3. Verify posts saved in Firestore
4. Check error handling for invalid usernames

---

## Phase 5: Timeline Display ✅

### Files to Create/Modify:
1. **`templates/socials.html`** - Add timeline section
2. **`static/js/socials.js`** - Timeline rendering logic
3. **`static/css/socials.css`** - Timeline styling

### API Endpoint:
```python
@socials_bp.route('/timeline', methods=['GET'])
@login_required
def get_timeline()
  # Parameters: limit, offset, platform_filter
```

### Features:
- Unified timeline sorted by `posted_at` (newest first)
- Post cards showing:
  - Platform icon + username
  - Post content/caption
  - Media (images/videos)
  - Engagement metrics
  - Link to original post
- Infinite scroll or pagination
- Platform filter buttons (All, Instagram, YouTube, Twitter)
- Empty state when no posts

**Test Checkpoint**:
1. Sync Instagram account
2. View timeline
3. See posts in chronological order
4. Click platform filters
5. Click post link → opens original post

---

## Phase 6: OAuth Infrastructure 🔐

### Environment Variables (.env):
```bash
# Instagram OAuth
INSTAGRAM_CLIENT_ID=your_app_id
INSTAGRAM_CLIENT_SECRET=your_app_secret

# YouTube OAuth (Google)
YOUTUBE_CLIENT_ID=your_google_client_id
YOUTUBE_CLIENT_SECRET=your_google_client_secret

# Twitter OAuth
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret

# Token encryption
SOCIAL_TOKEN_ENCRYPTION_KEY=generate_with_fernet
```

### Setup Requirements:
1. Create Instagram App (Meta Developers)
2. Create Google OAuth App (Google Cloud Console)
3. Create Twitter App (Twitter Developer Portal)
4. Generate encryption key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### Service Methods:
```python
def initiate_oauth_flow(user_id, platform) -> dict
def handle_oauth_callback(platform, code, state) -> str
def _validate_oauth_state(state) -> dict
def _exchange_code_for_tokens(platform, code) -> dict
def _get_user_profile(platform, access_token) -> dict
def _store_oauth_account(user_id, platform, tokens, profile) -> str
```

### OAuth Callback Routes:
```python
@socials_bp.route('/oauth/<platform>/callback')
def oauth_callback(platform)
```

**Test Checkpoint**:
1. Configure OAuth apps on each platform
2. Set environment variables
3. Test OAuth state generation
4. Test token encryption/decryption
5. Verify callback routes work (can use OAuth playground)

---

## Phase 7: OAuth Instagram Integration 📸

### Replace Public with OAuth:
- Update "Add Account" flow to use OAuth button
- Implement Instagram Basic Display API
- Fetch user's media (photos/videos)
- Handle token refresh automatically

### Instagram API Endpoints:
- `/me` - Get user profile
- `/me/media` - Get user's posts
- `/refresh_access_token` - Refresh expired token

### Token Management:
```python
def _get_valid_access_token(account_id) -> str
def _is_token_valid(account_data) -> bool
def _refresh_instagram_token(refresh_token) -> dict
def _update_account_tokens(account_id, new_tokens) -> None
```

**Test Checkpoint**:
1. Connect Instagram via OAuth
2. See posts fetched automatically
3. Wait for token to expire (or force expiry)
4. Verify automatic token refresh
5. Test reconnection flow when refresh fails

---

## Phase 8: YouTube Integration 📹

### YouTube Data API v3:
- Fetch user's uploaded videos
- Get video metadata (title, description, thumbnail)
- Get engagement metrics (views, likes, comments)

### Service Methods:
```python
def _fetch_youtube_videos(access_token, limit) -> list
def _parse_youtube_video(video_data) -> dict
def _refresh_google_token(refresh_token) -> dict
```

### Display Enhancements:
- Video thumbnails with play icon
- View count display
- Video duration
- Embed YouTube player on click

**Test Checkpoint**:
1. Connect YouTube account
2. Fetch videos from channel
3. Display in timeline with Instagram posts
4. Click video → open in modal/new tab
5. Test token refresh

---

## Phase 9: Twitter Integration 🐦

### Twitter API v2:
- Fetch user's tweets
- Get tweet text, media, metrics
- Handle retweets and quoted tweets

### Service Methods:
```python
def _fetch_twitter_tweets(access_token, limit) -> list
def _parse_twitter_tweet(tweet_data) -> dict
def _refresh_twitter_token(refresh_token) -> dict
```

### Display Features:
- Tweet text with @mentions and #hashtags
- Quoted tweets display
- Retweet indication
- Twitter card styling

**Test Checkpoint**:
1. Connect Twitter account
2. Fetch recent tweets
3. Display in unified timeline
4. Test all three platforms together
5. Verify sorting across platforms

---

## Phase 10: Polish & Security Audit ✨

### Features to Add:
1. **Rate Limiting**: Protect API endpoints
2. **Subscription Gating**: Limit free tier to X accounts
3. **Error Handling**: User-friendly error messages
4. **Loading States**: Spinners during API calls
5. **Account Health Check**: Notify users when reconnection needed
6. **Background Sync**: Scheduled job to refresh posts
7. **Analytics**: Track feature usage
8. **Export**: Allow users to export their timeline

### Security Checklist:
- [ ] All OAuth states validated
- [ ] CSRF tokens on all POST/DELETE
- [ ] Tokens encrypted at rest
- [ ] No sensitive data in logs
- [ ] Rate limiting on all endpoints
- [ ] Input validation and sanitization
- [ ] User ownership checks on all operations
- [ ] HTTPS enforcement in production
- [ ] Secure session management
- [ ] Token expiry handled gracefully

### Documentation:
- [ ] User guide for connecting accounts
- [ ] API documentation
- [ ] Developer setup instructions
- [ ] Troubleshooting guide
- [ ] Privacy policy update

**Final Test Checkpoint**:
1. Complete user flow from signup to viewing timeline
2. Test all error scenarios
3. Test with multiple accounts per platform
4. Test reconnection flow
5. Load testing with many posts
6. Security penetration testing
7. Mobile responsiveness testing
8. Cross-browser compatibility

---

## Environment Setup Requirements

### Python Packages (add to requirements.txt):
```
cryptography>=41.0.0  # For token encryption
requests>=2.31.0      # Already included
```

### OAuth App Setup:

#### Instagram Basic Display API:
1. Go to https://developers.facebook.com/
2. Create App → "Consumer" type
3. Add "Instagram Basic Display" product
4. Configure OAuth Redirect URIs: `https://yourdomain.com/api/socials/oauth/instagram/callback`
5. Get App ID and App Secret

#### Google OAuth (YouTube):
1. Go to https://console.cloud.google.com/
2. Create OAuth 2.0 Client ID
3. Add authorized redirect URI: `https://yourdomain.com/api/socials/oauth/youtube/callback`
4. Enable YouTube Data API v3
5. Get Client ID and Client Secret

#### Twitter API v2:
1. Go to https://developer.twitter.com/
2. Create App with OAuth 2.0
3. Add callback URL: `https://yourdomain.com/api/socials/oauth/twitter/callback`
4. Get Client ID and Client Secret
5. Request elevated access if needed

---

## Testing Strategy

### Manual Testing Checklist:
- [ ] Phase 1: App starts without errors
- [ ] Phase 2: Navigation link works, page loads
- [ ] Phase 3: Account CRUD operations work
- [ ] Phase 4: Instagram posts fetch successfully
- [ ] Phase 5: Timeline displays posts correctly
- [ ] Phase 6: OAuth apps configured properly
- [ ] Phase 7: Instagram OAuth works end-to-end
- [ ] Phase 8: YouTube OAuth works end-to-end
- [ ] Phase 9: Twitter OAuth works end-to-end
- [ ] Phase 10: All security checks pass

### Automated Testing (Future):
- Unit tests for service methods
- Integration tests for OAuth flows
- API endpoint tests
- Frontend component tests

---

## Rollout Plan

### Development (localhost):
1. Implement phases 1-5 with public accounts
2. Test basic functionality
3. Set up OAuth apps (use localhost callbacks)
4. Implement phases 6-9
5. Complete phase 10 polish

### Staging (Dev Cloud Run):
1. Deploy with staging OAuth credentials
2. Test with real OAuth flows
3. Invite beta testers
4. Gather feedback and fix bugs
5. Security audit

### Production:
1. Create production OAuth apps
2. Update environment variables
3. Deploy to main Cloud Run
4. Monitor error rates
5. Gradual rollout to users

---

## Success Metrics

### Feature Adoption:
- % of users who connect at least 1 account
- Average number of accounts per user
- Daily active users viewing timeline

### Technical:
- OAuth success rate
- Token refresh success rate
- API error rate < 1%
- Page load time < 2s

### User Satisfaction:
- User feedback/ratings
- Feature request votes
- Support ticket volume

---

## Future Enhancements

### Phase 11 (Optional):
- TikTok integration
- LinkedIn integration
- Facebook Pages integration
- Mastodon/Bluesky integration

### Phase 12 (Optional):
- AI-powered post insights
- Scheduled posting (write capability)
- Cross-posting to multiple platforms
- Analytics dashboard
- Content calendar view
- Hashtag analytics
- Engagement predictions

---

## Notes

- Start with **public accounts** (Phase 1-5) to validate UI/UX before OAuth complexity
- **Security first**: All tokens encrypted, OAuth properly implemented
- **User experience**: Automatic token refresh, graceful error handling
- **Scalability**: Consider caching posts, background sync jobs
- **Cost**: Monitor API quotas (Instagram: 200 calls/hour, YouTube: 10,000 units/day)

### 🔗 Integration Points with Existing Infrastructure

#### Deeplink Service Integration (Phase 10+)
The existing `services/deeplink_service.py` and `services/click_tracking_service.py` will be leveraged for:
- **Trackable Post Links**: Each post gets a short link via `create_short_link()`
- **Click Analytics**: All clicks tracked with geo, device, referrer data
- **Profile Links**: Social platform profiles become trackable
- **Custom Links**: Creators add custom links (website, Substack, etc.)

#### Database Connections
- `social_posts.short_code` → `shortened_links.short_code`
- `link_clicks.post_id` → `social_posts.id` (new field)
- `link_clicks.click_source` → "creator_profile|social_post|custom_link" (new field)

#### Service Dependencies
```python
# Future integration example (Phase 10+)
from services.deeplink_service import create_short_link
from services.click_tracking_service import ClickTrackingService

class SocialsService:
    def create_trackable_post_link(self, post_id):
        """Create short link for a post that tracks clicks."""
        post = self._get_post_by_id(post_id)
        short_code = create_short_link(
            original_url=post['post_url'],
            user_id=post['user_id'],
            metadata={'post_id': post_id, 'source': 'social_post'}
        )
        # Update post with short_code
        self._update_post(post_id, {'short_code': short_code})
        return f"https://phoenix.ai/s/{short_code}"
```

This design ensures we're building the foundation now while keeping seamless integration with your existing analytics infrastructure for the future Creator Portfolio Platform.

---

## Resources

### Documentation:
- Instagram Basic Display API: https://developers.facebook.com/docs/instagram-basic-display-api
- YouTube Data API: https://developers.google.com/youtube/v3
- Twitter API v2: https://developer.twitter.com/en/docs/twitter-api

### Libraries:
- `cryptography` for token encryption
- `requests` for API calls
- Firebase Admin SDK for Firestore

### Security:
- OWASP OAuth 2.0 Security Best Practices
- Firebase Security Rules for Firestore
- Content Security Policy headers
