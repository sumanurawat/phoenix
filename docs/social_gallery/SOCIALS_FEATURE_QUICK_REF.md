# Social Media Feature - Quick Reference

## What's Built (Phases 1-4)

### Infrastructure
- `services/socials_service.py` - Account management, token encryption
- `services/instagram_oauth_service.py` - Instagram OAuth flow
- `api/socials_routes.py` - RESTful API endpoints with OAuth support
- Blueprint registered in `app.py`
- `cryptography` added to requirements.txt
- Instagram Basic Display API integration

### UI/UX
- "Socials" link in user dropdown menu
- `/socials` route with empty state
- `templates/socials.html` - Landing page with OAuth and manual options
- `static/js/socials.js` - Account management + OAuth popup handling
- Add/remove accounts with CSRF protection
- Toast notifications for feedback
- OAuth callback success/error handling

### Features Working Now
- **Instagram OAuth Connection** - Secure authentication via Instagram Basic Display API
- Add Instagram via OAuth (recommended) or public username
- Add social account (Instagram, YouTube, Twitter) by username
- View connected accounts with platform icons
- Remove accounts with confirmation
- Sync Instagram posts via OAuth or public scraping
- Data persisted in Firestore `user_social_accounts` collection
- Secure token encryption with auto-refresh (60-day tokens)
- Fallback from OAuth to public scraping if token fails

### OAuth Implementation Details
- State-based CSRF protection
- Short-lived token exchange for long-lived tokens (60 days)
- Automatic token refresh when within 7 days of expiration
- Encrypted token storage in Firestore
- Instagram testers support for development mode
- Popup and redirect OAuth flows
- Detailed error handling and user feedback

**See**: [Instagram OAuth Setup Guide](./INSTAGRAM_OAUTH_SETUP.md) for complete configuration instructions.

## Testing Checklist

### Phase 1-3 (Current)
- [ ] App starts without errors
- [ ] Navigate to `/socials` - see empty state
- [ ] Click "Add Account" - modal opens
- [ ] Add Instagram account @testuser
- [ ] Account appears in list with icon
- [ ] Remove account - confirms and deletes
- [ ] Refresh page - accounts persist
- [ ] Error handling for duplicate accounts

### Phase 4 (Next)
- [ ] Instagram posts fetch successfully
- [ ] Posts stored in Firestore
- [ ] Error handling for invalid usernames
- [ ] Rate limiting respected

## Key Design Decisions

### Why Public Accounts First?
- Faster to implement (no OAuth complexity)
- Validates user interest
- Tests UI/UX before investing in OAuth
- Can add OAuth later without breaking changes

## Related Docs

- [Full Implementation Plan](./SOCIALS_FEATURE_IMPLEMENTATION_PLAN.md)
- [Creator Portfolio Vision](./CREATOR_PORTFOLIO_VISION.md)
- [Instagram OAuth Setup](./INSTAGRAM_OAUTH_SETUP.md)
