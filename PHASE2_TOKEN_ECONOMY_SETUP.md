# Token Economy Implementation Guide

## Overview
This guide documents the complete setup and deployment of Phoenix's token purchase system - Phase 2 of the platform's economic engine.

## Completed: Backend Implementation ✅

### API Endpoints Created

#### 1. **GET /api/tokens/packages** (Public)
Returns available token packages with pricing and bonus information.

**Response:**
```json
{
  "success": true,
  "packages": [
    {
      "id": "starter",
      "name": "Starter Pack",
      "tokens": 50,
      "price": 4.99,
      "bonus": 0,
      "description": "Perfect for trying out our platform",
      "available": true
    },
    {
      "id": "popular",
      "name": "Popular Pack",
      "tokens": 110,
      "price": 9.99,
      "bonus": 10,
      "description": "Most popular choice - 10% bonus!",
      "badge": "MOST POPULAR",
      "available": true
    },
    {
      "id": "pro",
      "name": "Pro Pack",
      "tokens": 250,
      "price": 19.99,
      "bonus": 50,
      "description": "For power users - 25% bonus!",
      "available": true
    },
    {
      "id": "creator",
      "name": "Creator Pack",
      "tokens": 700,
      "price": 49.99,
      "bonus": 200,
      "description": "Maximum value - 40% bonus!",
      "badge": "BEST VALUE",
      "available": true
    }
  ]
}
```

#### 2. **POST /api/tokens/create-checkout-session** (Protected)
Creates Stripe checkout session for token purchase.

**Request:**
```json
{
  "package": "popular"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "cs_test_xxxxx",
  "url": "https://checkout.stripe.com/c/pay/cs_test_xxxxx"
}
```

**Error Responses:**
- `400` - Invalid or missing package ID
- `401` - Authentication required
- `500` - Stripe not configured or customer creation failed

#### 3. **GET /api/tokens/balance** (Protected)
Returns user's current token balance.

**Response:**
```json
{
  "success": true,
  "balance": 150
}
```

#### 4. **GET /api/tokens/transactions** (Protected)
Returns user's token purchase history with pagination.

**Query Parameters:**
- `limit` (optional, default=20, max=100)
- `offset` (optional, default=0)

**Response:**
```json
{
  "success": true,
  "transactions": [
    {
      "id": "tx_xxxxx",
      "userId": "user123",
      "type": "purchase",
      "amount": 110,
      "timestamp": "2025-10-25T10:30:00Z",
      "details": {
        "packageId": "popular",
        "stripeSessionId": "cs_test_xxxxx",
                "stripeCustomerId": "cus_xxxxx",
        "paymentAmountUSD": 9.99
      }
    }
  ],
  "limit": 20,
  "offset": 0
}
```

### Stripe Service Enhancements

#### New Methods Added to `StripeService`

**`get_or_create_customer(firebase_uid, email)`**
- Checks for existing Stripe customer by Firebase UID
- Creates new customer if not found
- Returns Stripe customer ID

**`create_token_checkout_session(customer_id, price_id, metadata)`**
- Creates one-time payment checkout session (mode='payment')
- Includes metadata: firebase_uid, package_id, tokens, purchase_type='token_package'
- Returns session ID and checkout URL

**`_handle_token_purchase(session)`**
- Webhook handler for token purchase completion
- Performs idempotency check via `transaction_service.get_by_stripe_session()`
- Credits tokens atomically via `token_service.add_tokens()`
- Records immutable transaction via `transaction_service.record_purchase()`
- Logs all steps with emoji indicators for easy debugging

#### Webhook Flow Enhancement

Modified `_handle_checkout_completed()` to detect purchase type:
```python
purchase_type = metadata.get('purchase_type')
if purchase_type == 'token_package':
    return self._handle_token_purchase(session)
# Otherwise, handle as subscription...
```

This allows the same webhook endpoint to handle both subscriptions and token purchases.

### Transaction Service Updates

#### Enhanced `record_purchase()` Method

**New Signature:**
```python
def record_purchase(
    self,
    user_id: str,
    amount: int,
    package_id: str,
    stripe_session_id: str,
    stripe_customer_id: str,
    amount_paid: float
) -> str
```

**Changes:**
- Added `package_id` parameter to identify which package was purchased
- Added `stripe_customer_id` for customer tracking
- Renamed `payment_amount_usd` to `amount_paid` for consistency
- Stores all data in transaction `details` field for audit trail

#### New `get_by_stripe_session()` Method

```python
def get_by_stripe_session(self, stripe_session_id: str) -> Optional[Dict[str, Any]]
```

- Queries `transactions` collection by `details.stripeSessionId`
- Returns existing transaction if found (idempotency check)
- Returns `None` if session hasn't been processed yet
- Critical for preventing double-crediting on webhook retries

### Configuration Updates

Added to `config/settings.py`:
```python
# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Token Package Price IDs
STRIPE_TOKEN_STARTER_PRICE_ID = os.getenv("STRIPE_TOKEN_STARTER_PRICE_ID")   # 50 tokens - $4.99
STRIPE_TOKEN_POPULAR_PRICE_ID = os.getenv("STRIPE_TOKEN_POPULAR_PRICE_ID")   # 110 tokens - $9.99
STRIPE_TOKEN_PRO_PRICE_ID = os.getenv("STRIPE_TOKEN_PRO_PRICE_ID")           # 250 tokens - $19.99
STRIPE_TOKEN_CREATOR_PRICE_ID = os.getenv("STRIPE_TOKEN_CREATOR_PRICE_ID")   # 700 tokens - $49.99

# Application Base URL (for Stripe redirects)
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080")
```

### Blueprint Registration

Added to `app.py`:
```python
from api.token_routes import token_bp
# ...
app.register_blueprint(token_bp)
```

Token routes are now available at `/api/tokens/*`

## Required: Stripe Dashboard Configuration 🔧

### Step 1: Create Token Products

Log in to https://dashboard.stripe.com/ and create 4 products:

#### Product 1: Starter Pack
- **Product Name:** Token Starter Pack
- **Description:** 50 tokens for trying out Phoenix
- **Pricing:** $4.99 USD, one-time
- **Price ID:** Copy the generated price ID (starts with `price_`)

#### Product 2: Popular Pack
- **Product Name:** Token Popular Pack  
- **Description:** 110 tokens - our most popular choice! (10% bonus)
- **Pricing:** $9.99 USD, one-time
- **Price ID:** Copy the generated price ID

#### Product 3: Pro Pack
- **Product Name:** Token Pro Pack
- **Description:** 250 tokens for power users (25% bonus)
- **Pricing:** $19.99 USD, one-time
- **Price ID:** Copy the generated price ID

#### Product 4: Creator Pack
- **Product Name:** Token Creator Pack
- **Description:** 700 tokens - maximum value! (40% bonus)
- **Pricing:** $49.99 USD, one-time
- **Price ID:** Copy the generated price ID

### Step 2: Configure Environment Variables

Add to `.env` file:
```bash
# Stripe Token Package Price IDs (from Stripe Dashboard)
STRIPE_TOKEN_STARTER_PRICE_ID=price_xxxxx
STRIPE_TOKEN_POPULAR_PRICE_ID=price_xxxxx
STRIPE_TOKEN_PRO_PRICE_ID=price_xxxxx
STRIPE_TOKEN_CREATOR_PRICE_ID=price_xxxxx

# App Base URL for redirects
APP_BASE_URL=http://localhost:8080  # Development
# APP_BASE_URL=https://phoenix-dev-946035996889.us-central1.run.app  # Dev
# APP_BASE_URL=https://deeprplexity.com  # Production
```

### Step 3: Set Google Cloud Secrets (for Cloud Run)

```bash
# Development environment
echo -n "price_xxxxx" | gcloud secrets versions add stripe-token-starter-price-id --data-file=-
echo -n "price_xxxxx" | gcloud secrets versions add stripe-token-popular-price-id --data-file=-
echo -n "price_xxxxx" | gcloud secrets versions add stripe-token-pro-price-id --data-file=-
echo -n "price_xxxxx" | gcloud secrets versions add stripe-token-creator-price-id --data-file=-
echo -n "https://phoenix-dev-946035996889.us-central1.run.app" | gcloud secrets versions add app-base-url --data-file=-

# Update cloudbuild-dev.yaml to include these secrets
```

## Pending: Frontend Implementation 🎨

### Pages to Create

#### 1. Buy Tokens Page (`/buy-tokens`)
- **Route:** Add to `app.py`
- **Template:** `templates/buy_tokens.html`
- **JavaScript:** `static/js/buy_tokens.js`

**Features:**
- Display 4 package cards with pricing and bonus badges
- Show current token balance
- Highlight "MOST POPULAR" and "BEST VALUE" badges
- Stripe checkout integration on button click
- Loading states during checkout creation

#### 2. Purchase Success Page (`/token-purchase-success`)
- **Template:** `templates/token_purchase_success.html`
- **Features:**
  - Confetti animation on load
  - Display updated token balance
  - Show purchased package details
  - Link to start creating content
  - Transaction ID for reference

#### 3. Purchase Cancel Page (`/token-purchase-cancel`)
- **Template:** `templates/token_purchase_cancel.html`
- **Features:**
  - Friendly message explaining cancellation
  - Retry button to return to buy tokens page
  - Link to contact support

### UI Components Needed

**Token Balance Widget** (for navbar/header):
```html
<div class="token-balance">
  <i class="bi bi-coin"></i>
  <span id="token-count">150</span> tokens
</div>
```

**Package Card Component**:
```html
<div class="token-package-card">
  <div class="package-badge">MOST POPULAR</div>
  <h3 class="package-name">Popular Pack</h3>
  <div class="package-price">$9.99</div>
  <div class="package-tokens">110 tokens</div>
  <div class="package-bonus">+10 bonus tokens!</div>
  <p class="package-description">Most popular choice - 10% bonus!</p>
  <button class="btn-buy-tokens" data-package="popular">
    Buy Now
  </button>
</div>
```

## Testing Guide 🧪

### Local Testing

#### 1. Start Local Environment
```bash
./start_local.sh
```

#### 2. Test Package Listing
```bash
curl http://localhost:8080/api/tokens/packages | jq
```

**Expected:** JSON with 4 packages, `available: true` for all

#### 3. Test Authenticated Endpoints

**Get Balance:**
```bash
# Must be logged in first
curl -b cookies.txt http://localhost:8080/api/tokens/balance
```

**Create Checkout Session:**
```bash
curl -X POST http://localhost:8080/api/tokens/create-checkout-session \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <token>" \
  -b cookies.txt \
  -d '{"package": "popular"}'
```

**Expected:** Session ID and Stripe checkout URL

### Stripe Test Cards

Use these test cards for checkout:

- **Success:** `4242 4242 4242 4242`
- **Decline:** `4000 0000 0000 0002`
- **Requires Authentication:** `4000 0025 0000 3155`

**CVV:** Any 3 digits  
**Expiry:** Any future date  
**ZIP:** Any 5 digits

### Webhook Testing

#### Option 1: Stripe CLI (Recommended)
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8080/api/stripe/webhook

# Test specific event
stripe trigger checkout.session.completed
```

#### Option 2: ngrok
```bash
# Start ngrok
ngrok http 8080

# Configure webhook in Stripe Dashboard
# URL: https://xxxxx.ngrok.io/api/stripe/webhook
# Events: checkout.session.completed

# Complete a test purchase and check logs
```

### End-to-End Test Scenario

1. **Setup:**
   - User logs in
   - Has 0 tokens initially

2. **Purchase:**
   - User clicks "Buy Tokens"
   - Selects "Popular Pack" ($9.99, 110 tokens)
   - Redirected to Stripe checkout
   - Enters test card `4242 4242 4242 4242`
   - Clicks "Pay"

3. **Webhook:**
   - Stripe sends `checkout.session.completed` event
   - Phoenix processes webhook:
     - Detects `purchase_type=token_package`
     - Routes to `_handle_token_purchase()`
     - Checks idempotency (first time)
     - Credits 110 tokens to user
     - Records transaction in ledger

4. **Verification:**
   - User redirected to success page
   - Balance shows 110 tokens
   - Transaction history shows purchase
   - Firestore `users` collection: `tokenBalance: 110`
   - Firestore `transactions` collection: New document with purchase details

5. **Idempotency Test:**
   - Manually replay webhook (same session_id)
   - Should see log: "Session already processed - skipping duplicate"
   - Balance remains 110 (not doubled)

## Monitoring & Logging 📊

### Key Log Messages

**Checkout Creation:**
```
Created token checkout session cs_test_xxxxx for customer cus_xxxxx
Package: popular, Tokens: 110
```

**Webhook Receipt:**
```
🛒 Processing checkout.session.completed event
🪙 Detected token purchase - routing to token handler
```

**Token Crediting:**
```
🪙 Starting token purchase processing...
👤 User: user123
📦 Package: popular
🪙 Tokens: 110
💰 Crediting 110 tokens to user user123
📝 Recording transaction in ledger
✅ Token purchase completed successfully for user user123
```

**Idempotency:**
```
✅ Session cs_test_xxxxx already processed - skipping duplicate
```

### Error Scenarios

**Missing Metadata:**
```
❌ Missing required metadata for token purchase
```
**Action:** Check Stripe checkout session creation includes all metadata

**Invalid Token Amount:**
```
❌ Invalid token amount: abc
```
**Action:** Verify metadata.tokens is numeric string

**Token Credit Failure:**
```
❌ Failed to credit tokens to user user123
```
**Action:** Check Firestore permissions and token_service logs

## Deployment Checklist ✈️

### Pre-Deployment

- [ ] Stripe products created in dashboard
- [ ] Price IDs copied to `.env`
- [ ] Secrets added to Google Cloud Secret Manager
- [ ] `cloudbuild-dev.yaml` updated with new secrets
- [ ] Frontend pages created and tested locally
- [ ] End-to-end flow tested with Stripe test cards
- [ ] Webhook tested with Stripe CLI
- [ ] Idempotency verified (duplicate webhooks handled)

### Deployment Steps

```bash
# 1. Commit changes
git add -A
git commit -m "feat: implement token purchase system (Phase 2)

- Add token purchase API endpoints (/api/tokens/*)
- Enhance StripeService with token checkout methods
- Add webhook handler for token purchases
- Implement idempotency checks via transaction ledger
- Add frontend buy tokens page with Stripe integration
- Configure 4 token packages (starter, popular, pro, creator)
- Add success/cancel redirect pages

Closes #TOKEN-ECONOMY-PHASE-2"

# 2. Push to dev
git push origin main

# 3. Monitor Cloud Build
gcloud builds list --limit=1 --format="table(id,status,logUrl)"

# 4. Test on dev environment
curl https://phoenix-dev-946035996889.us-central1.run.app/api/tokens/packages

# 5. Complete test purchase on dev

# 6. If successful, merge to production (manual trigger)
```

### Post-Deployment Verification

```bash
# Check API availability
curl https://deeprplexity.com/api/tokens/packages

# Monitor webhook events
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"token purchase\"" --limit=50

# Check Firestore transactions
# Go to Firebase Console > Firestore > transactions collection
# Verify purchase records appearing

# Test with real Stripe checkout (small amount first!)
```

## Architecture Decisions 📐

### Why Firestore Over RDBMS?

**Atomic Transactions:**
- Firestore supports atomic operations via `Firestore.Increment`
- Token credits/debits happen atomically without race conditions
- No need for row-level locking or serializable isolation

**Horizontal Scalability:**
- Firestore scales automatically
- No connection pool limits
- No manual sharding required

**Existing Infrastructure:**
- Already using Firestore for users, posts, subscriptions
- No additional database to manage
- Consistent data model across platform

### Idempotency Strategy

**Problem:** Stripe may send duplicate webhooks  
**Solution:** Transaction ledger with `stripeSessionId` lookup

```python
existing = transaction_service.get_by_stripe_session(session_id)
if existing:
    return {'success': True, 'message': 'Already processed'}
```

**Why It Works:**
- Firestore query is fast (indexed field)
- Immutable ledger ensures transactions never deleted
- Safe to check before crediting tokens

### Metadata in Checkout Session

**Critical Fields:**
```python
metadata = {
    'firebase_uid': user_id,           # For token crediting
    'package_id': 'popular',            # For analytics
    'tokens': 110,                      # Amount to credit
    'purchase_type': 'token_package'    # Routing key for webhook
}
```

**Why `purchase_type`?**
- Allows webhook to distinguish token purchases from subscriptions
- Single webhook endpoint handles multiple payment types
- Simplifies Stripe configuration

## Cost Analysis 💰

### Stripe Fees (Standard Pricing)

| Package | Price | Stripe Fee (2.9% + $0.30) | Net Revenue | % Margin |
|---------|-------|---------------------------|-------------|----------|
| Starter | $4.99 | $0.44 | $4.55 | 91.2% |
| Popular | $9.99 | $0.59 | $9.40 | 94.1% |
| Pro | $19.99 | $0.88 | $19.11 | 95.6% |
| Creator | $49.99 | $1.75 | $48.24 | 96.5% |

**Monthly Projections (1000 transactions):**

Assuming distribution:
- 30% Starter = 300 × $4.55 = $1,365
- 50% Popular = 500 × $9.40 = $4,700
- 15% Pro = 150 × $19.11 = $2,867
- 5% Creator = 50 × $48.24 = $2,412

**Total Net Revenue:** $11,344/month  
**Stripe Fees:** $1,656/month  
**Gross Revenue:** $13,000/month

### Infrastructure Costs

- **Cloud Run:** ~$50/month (existing)
- **Firestore:** ~$25/month (reads/writes)
- **Cloud Storage (R2):** $0 (egress included)

**Total Infrastructure:** ~$75/month  
**Net Profit (1000 transactions):** $11,269/month

## Security Considerations 🔒

### CSRF Protection
All POST endpoints protected with `@csrf_protect` decorator

### Authentication
All token endpoints (except `/packages`) require `@login_required`

### Webhook Signature Verification
```python
event = stripe.Webhook.construct_event(
    payload, sig_header, self.webhook_secret
)
```

### Metadata Validation
```python
if not all([firebase_uid, package_id, tokens]):
    logger.error("❌ Missing required metadata")
    return {'error': 'Incomplete token purchase data'}
```

### Amount Validation
- Tokens must be integer
- Must match package configuration
- Server-side validation before crediting

## Troubleshooting 🔧

### "Package not available - contact support"
- **Cause:** Price ID not configured in environment
- **Fix:** Add `STRIPE_TOKEN_*_PRICE_ID` to `.env`

### "Failed to create customer"
- **Cause:** Stripe API key invalid or missing
- **Fix:** Check `STRIPE_SECRET_KEY` in environment

### Tokens not credited after payment
- **Cause:** Webhook not received or failed
- **Fix:** Check webhook logs, verify `STRIPE_WEBHOOK_SECRET`

### Duplicate token credits
- **Cause:** Idempotency check failing
- **Fix:** Verify `transaction_service.get_by_stripe_session()` working

### "Already processed" but user has no tokens
- **Cause:** Token crediting failed after transaction recorded
- **Fix:** Check `token_service.add_tokens()` logs, may need manual credit

## Next Steps 🚀

1. **Create Frontend Pages** (Task 6)
   - Buy tokens page with package cards
   - Success page with confetti
   - Cancel page with retry option

2. **Integration Testing** (Task 7)
   - Test with Stripe test cards
   - Verify balance updates
   - Check transaction history

3. **Documentation** (Task 8)
   - Update README with token economy info
   - Create user guide for buying tokens
   - Add troubleshooting section

4. **Production Launch**
   - Deploy to production Cloud Run
   - Monitor initial purchases
   - Collect user feedback

## Files Modified/Created

### Created:
- `api/token_routes.py` - Token purchase API endpoints
- `scripts/add_token_methods.py` - Script to enhance StripeService
- `services/stripe_extensions.py` - Reference implementation
- `PHASE2_TOKEN_ECONOMY_SETUP.md` - This document

### Modified:
- `services/stripe_service.py` - Added token checkout and webhook methods
- `services/transaction_service.py` - Enhanced record_purchase(), added get_by_stripe_session()
- `config/settings.py` - Added token price ID configuration
- `app.py` - Registered token_bp blueprint

### Pending:
- `templates/buy_tokens.html`
- `templates/token_purchase_success.html`
- `templates/token_purchase_cancel.html`
- `static/js/buy_tokens.js`
- `static/css/token_purchase.css`

## Support & Contact

For questions or issues:
- GitHub Issues: https://github.com/sumanurawat/phoenix/issues
- Email: support@deeprplexity.com

---

**Last Updated:** October 25, 2025  
**Author:** AI Assistant (Claude)  
**Version:** 1.0.0
