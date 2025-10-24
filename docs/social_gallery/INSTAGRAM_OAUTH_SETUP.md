# Instagram OAuth Setup Guide

**Status**: ✅ **IMPLEMENTED** - Instagram Basic Display API OAuth flow complete

## Overview

Phoenix Social Gallery now uses Instagram Basic Display API for secure, reliable access to user media. This replaces the unreliable public scraping approach.

## Why OAuth?

### Problems with Public Scraping
- ❌ Instagram blocks unauthenticated requests
- ❌ Rate limits on public API endpoints
- ❌ Unreliable for production use
- ❌ Risk of account blocks

### Benefits of OAuth
- ✅ Official Instagram API
- ✅ Reliable, no rate limit issues
- ✅ Secure token-based authentication
- ✅ Access to user's own media
- ✅ Long-lived tokens (60 days, auto-refresh)

## Setup Instructions

### 1. Create Facebook App (Required for Instagram API)

Instagram Basic Display API requires a Facebook App:

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click **My Apps** > **Create App**
3. Select **Consumer** as app type
4. Fill in app details:
   - App Name: "Phoenix Social Gallery"
   - App Contact Email: your-email@example.com

### 2. Add Instagram Basic Display Product

1. In your Facebook App dashboard, find **Add Products**
2. Click **Set Up** on **Instagram Basic Display**
3. This creates the Instagram Basic Display configuration

### 3. Configure Instagram Basic Display Settings

Navigate to **Products** > **Instagram Basic Display** > **Basic Display**:

#### Client OAuth Settings:
- **Valid OAuth Redirect URIs**:
  - Development: `http://localhost:8080/api/socials/oauth/instagram/callback`
  - Production: `https://your-domain.com/api/socials/oauth/instagram/callback`
  - Staging: `https://your-staging-domain.com/api/socials/oauth/instagram/callback`

#### Deauthorize Callback URL:
- `https://your-domain.com/api/socials/oauth/instagram/deauthorize`

#### Data Deletion Request URL:
- `https://your-domain.com/api/socials/oauth/instagram/data-deletion`

### 4. Add Instagram Testers (Development Mode)

While your app is in Development Mode:

1. Go to **Instagram Basic Display** > **User Token Generator**
2. Click **Add or Remove Instagram Testers**
3. Enter Instagram usernames
4. Those users must accept the tester invitation in their Instagram app:
   - Go to Settings > Apps and Websites > Tester Invites
   - Accept the invitation

⚠️ **Important**: Only Instagram testers can use OAuth while app is in Development Mode.

### 5. Get API Credentials

1. Go to **Settings** > **Basic**
2. Copy the following:
   - **App ID** (this is your `INSTAGRAM_CLIENT_ID`)
   - **App Secret** (this is your `INSTAGRAM_CLIENT_SECRET`)

### 6. Configure Environment Variables

Add to your `.env` file:

```bash
# Instagram OAuth Configuration
INSTAGRAM_CLIENT_ID=your_app_id_here
INSTAGRAM_CLIENT_SECRET=your_app_secret_here
INSTAGRAM_REDIRECT_URI=http://localhost:8080/api/socials/oauth/instagram/callback

# For production:
# INSTAGRAM_REDIRECT_URI=https://your-domain.com/api/socials/oauth/instagram/callback
```

### 7. Setup Google Cloud Secret Manager (Production)

For Cloud Run deployment:

```bash
# Create secrets
echo -n "your_app_id_here" | gcloud secrets create INSTAGRAM_CLIENT_ID --data-file=-
echo -n "your_app_secret_here" | gcloud secrets create INSTAGRAM_CLIENT_SECRET --data-file=-
echo -n "https://your-domain.com/api/socials/oauth/instagram/callback" | gcloud secrets create INSTAGRAM_REDIRECT_URI --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding INSTAGRAM_CLIENT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding INSTAGRAM_CLIENT_SECRET \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding INSTAGRAM_REDIRECT_URI \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 8. Test OAuth Flow

1. Start your app: `./start_local.sh`
2. Navigate to Social Gallery
3. Click **Connect Instagram Account**
4. Follow Instagram authorization
5. You should be redirected back with success message

## Architecture

### OAuth Flow

```
┌──────────┐                ┌──────────┐                ┌──────────┐
│  User    │                │  Phoenix │                │Instagram │
│  Browser │                │  Backend │                │   API    │
└────┬─────┘                └────┬─────┘                └────┬─────┘
     │                           │                           │
     │ 1. Click "Connect"        │                           │
     │──────────────────────────>│                           │
     │                           │                           │
     │ 2. Generate Auth URL      │                           │
     │<──────────────────────────│                           │
     │                           │                           │
     │ 3. Redirect to Instagram  │                           │
     │───────────────────────────────────────────────────────>│
     │                           │                           │
     │ 4. User Authorizes        │                           │
     │<──────────────────────────────────────────────────────│
     │                           │                           │
     │ 5. Callback with Code     │                           │
     │──────────────────────────>│                           │
     │                           │                           │
     │                           │ 6. Exchange Code for Token│
     │                           │──────────────────────────>│
     │                           │                           │
     │                           │ 7. Return Access Token    │
     │                           │<──────────────────────────│
     │                           │                           │
     │                           │ 8. Store Encrypted Token  │
     │                           │      in Firestore         │
     │                           │                           │
     │ 9. Success Message        │                           │
     │<──────────────────────────│                           │
```

### Key Components

#### 1. Instagram OAuth Service (`services/instagram_oauth_service.py`)
- Generates authorization URLs
- Exchanges codes for tokens
- Refreshes expired tokens
- Fetches user media via API

#### 2. Socials Service (`services/socials_service.py`)
- Manages OAuth state tokens
- Stores encrypted access tokens
- Handles account creation/update
- Syncs media from Instagram API

#### 3. API Routes (`api/socials_routes.py`)
- `/api/socials/connect/<platform>` - Initiate OAuth
- `/api/socials/oauth/<platform>/callback` - Handle callback

#### 4. Frontend (`static/js/socials.js`)
- OAuth popup/redirect handling
- Success/error message display
- Account list refresh

### Token Management

**Storage:**
- Access tokens encrypted using Fernet cipher
- Stored in Firestore `user_social_accounts` collection
- Never exposed in API responses

**Lifecycle:**
1. Short-lived token (1 hour) obtained from authorization
2. Exchanged for long-lived token (60 days)
3. Auto-refresh when within 7 days of expiration
4. Refresh extends token by 60 days

**Security:**
- Tokens encrypted with `SOCIAL_TOKEN_ENCRYPTION_KEY`
- State tokens for CSRF protection
- 5-minute expiration on state tokens

### Data Model

**`user_social_accounts` Collection:**
```javascript
{
  user_id: "firebase_user_id",
  platform: "instagram",
  account_type: "oauth",  // or "public" for manual
  username: "john_doe",
  display_name: "@john_doe",
  instagram_user_id: "17841400123456789",
  encrypted_access_token: "gAAAAA...",
  token_expires_at: Timestamp,
  is_active: true,
  connected_at: Timestamp,
  last_sync: Timestamp,
  posts_count: 42,
  status: "active",
  profile_url: "https://instagram.com/john_doe"
}
```

## API Permissions

Instagram Basic Display API provides:

**Scopes:**
- `user_profile` - Basic profile info (username, account type)
- `user_media` - Access to user's media (photos/videos)

**Available Data:**
- Media ID
- Media type (IMAGE, VIDEO, CAROUSEL_ALBUM)
- Media URL
- Permalink (Instagram link)
- Thumbnail URL (for videos)
- Caption
- Timestamp

**Not Available:**
- Likes count (removed by Instagram)
- Comments count (removed by Instagram)
- Follower count
- Following count
- Private account data

## Rate Limits

Instagram Basic Display API:
- **200 requests per hour** per user token
- Sufficient for typical usage patterns
- Phoenix syncs max 25 media items per request

## Troubleshooting

### "Instagram OAuth not configured"
**Solution**: Ensure all environment variables are set:
```bash
echo $INSTAGRAM_CLIENT_ID
echo $INSTAGRAM_CLIENT_SECRET
echo $INSTAGRAM_REDIRECT_URI
```

### "Invalid or expired state token"
**Causes:**
- State token older than 5 minutes
- Already used state token
- CSRF attack attempt

**Solution**: Try connecting again with fresh OAuth flow.

### "OAuth callback validation error"
**Causes:**
- Redirect URI mismatch
- Invalid authorization code
- Network timeout

**Solution**: 
1. Verify redirect URI in Facebook app settings matches your config
2. Check Cloud Run logs for detailed error

### "Failed to exchange code for token"
**Causes:**
- Invalid client credentials
- Expired authorization code
- App not approved

**Solution**:
1. Verify `INSTAGRAM_CLIENT_ID` and `INSTAGRAM_CLIENT_SECRET`
2. Ensure user is added as Instagram tester (Development Mode)
3. Check app status in Facebook Developers

### Connection works but sync fails
**Causes:**
- Token expired and refresh failed
- API rate limit hit
- Private account

**Solution**:
1. Reconnect account (gets fresh token)
2. Wait an hour if rate limited
3. Ensure account is public or properly authorized

## Production Checklist

Before going live:

- [ ] Facebook App submitted for review
- [ ] App approved for Instagram Basic Display
- [ ] Production redirect URI configured
- [ ] Environment variables set in Cloud Run
- [ ] Token encryption key generated and secure
- [ ] Privacy Policy URL added to Facebook app
- [ ] Terms of Service URL added to Facebook app
- [ ] Data Deletion callback implemented
- [ ] Tested with multiple accounts
- [ ] Error handling verified
- [ ] Token refresh tested

## Future Enhancements

### Planned Features:
1. **Instagram Stories** - API access to user stories
2. **Instagram Reels** - Dedicated Reels fetching
3. **Insights & Analytics** - If user upgrades to Creator/Business account
4. **Scheduled Posting** - Via Instagram Content Publishing API
5. **Comment Management** - Reply to comments
6. **Direct Messages** - DM integration (requires Business account)

### Other Platforms:
1. **YouTube OAuth** - YouTube Data API v3
2. **Twitter OAuth** - Twitter API v2
3. **TikTok OAuth** - TikTok for Developers

## References

- [Instagram Basic Display API Docs](https://developers.facebook.com/docs/instagram-basic-display-api)
- [Facebook App Review](https://developers.facebook.com/docs/app-review)
- [OAuth 2.0 Spec](https://oauth.net/2/)
- [Phoenix Social Gallery Docs](./SOCIALS_FEATURE_QUICK_REF.md)

---

**Last Updated**: October 22, 2025
**Status**: Production Ready ✅
