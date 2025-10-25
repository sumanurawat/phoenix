# Phase 2: Token Economy Implementation Plan

## Overview
Building the economic engine to enable users to purchase tokens and support artists through tipping.

## Architecture Review ✅

### Existing Infrastructure (Already Built)
- ✅ `services/token_service.py` - Atomic balance operations with Firestore transactions
- ✅ `services/transaction_service.py` - Immutable financial ledger
- ✅ `services/stripe_service.py` - Stripe integration with customer management
- ✅ `api/stripe_routes.py` - Webhook handler for subscription events
- ✅ `users` collection in Firestore with `tokenBalance` field support
- ✅ `transactions` collection for audit trail

### What We're Adding
- Token purchase products in Stripe (4 packages)
- New API endpoint for token checkout sessions
- Enhanced webhook handler for `checkout.session.completed`
- Token purchase UI with package selection
- Success/failure pages for checkout flow

---

## Token Packages Design

| Package | Name | Price | Tokens | Value per $ |
|---------|------|-------|--------|-------------|
| 1 | Starter Token Pack | $4.99 | 50 | 10.02 tokens/$ |
| 2 | Popular Token Pack | $9.99 | 110 | 11.01 tokens/$ (+10% bonus) |
| 3 | Pro Token Pack | $19.99 | 250 | 12.51 tokens/$ (+25% bonus) |
| 4 | Creator Token Pack | $49.99 | 700 | 14.00 tokens/$ (+40% bonus) |

**Token Economy:**
- 1 token = 1 image generation (cost: ~$0.10 per 10 tokens)
- Tipping: Users can tip creators any amount
- Platform take: None on tips (100% goes to creator)

---

## Implementation Tasks

### Task 2.1: Stripe Product Configuration
**Owner:** You (manual Stripe Dashboard setup)
**Time:** 10 minutes

1. Log in to [Stripe Dashboard](https://dashboard.stripe.com/test/products)
2. Create 4 products with "Standard pricing" and "One time" purchase:
   - Starter Token Pack: $4.99
   - Popular Token Pack: $9.99
   - Pro Token Pack: $19.99
   - Creator Token Pack: $49.99
3. Copy the 4 Price IDs (format: `price_1P...`)
4. Add to `.env` file:
   ```
   STRIPE_TOKEN_STARTER_PRICE_ID=price_xxx
   STRIPE_TOKEN_POPULAR_PRICE_ID=price_xxx
   STRIPE_TOKEN_PRO_PRICE_ID=price_xxx
   STRIPE_TOKEN_CREATOR_PRICE_ID=price_xxx
   ```

---

### Task 2.2: Backend - Token Checkout API
**Files:** `api/stripe_routes.py`, `services/stripe_service.py`

#### New Route: `POST /api/tokens/create-checkout-session`
- **Auth:** Required (`@login_required`)
- **Input:** `{ "package": "starter" | "popular" | "pro" | "creator" }`
- **Output:** `{ "url": "https://checkout.stripe.com/..." }`
- **Logic:**
  1. Validate package name
  2. Map package to (price_id, token_amount)
  3. Create Stripe checkout session with metadata:
     - `user_id`: Firebase UID
     - `tokens`: Number of tokens to credit
     - `package`: Package name (for logging)
  4. Return session URL

#### New Method in `StripeService`:
```python
def create_token_checkout_session(
    self,
    user_id: str,
    email: str,
    package: str
) -> str:
    """Create checkout session for token purchase."""
```

**Metadata Strategy:**
- Store `user_id` and `tokens` in session metadata
- Webhook will read metadata to credit correct user
- Session ID used for idempotency (prevent double-credit)

---

### Task 2.3: Backend - Enhanced Webhook Handler
**File:** `api/stripe_routes.py`, `services/stripe_service.py`

#### Updates to `handle_webhook_event()`:
1. Add handler for `checkout.session.completed` event type
2. Check event metadata to determine if it's a token purchase
3. Implement idempotency check:
   ```python
   # Check if already processed
   existing_tx = transaction_service.get_by_stripe_session(session_id)
   if existing_tx:
       return 200  # Already processed
   ```
4. Call `token_service.credit_tokens_from_purchase()`

#### New Method in `TokenService`:
```python
def credit_tokens_from_purchase(
    self,
    user_id: str,
    tokens: int,
    stripe_session_id: str,
    payment_amount_usd: float
) -> bool:
    """Credit tokens from successful Stripe purchase (atomic)."""
```

**Atomic Transaction Flow:**
1. Start Firestore transaction
2. Update `users/{user_id}`: Increment `tokenBalance`
3. Create `transactions/{tx_id}`: Record purchase with Stripe session ID
4. Commit transaction (all-or-nothing)

---

### Task 2.4: Frontend - Token Purchase UI
**Files:** 
- `templates/buy_tokens.html` (new)
- `static/js/buy_tokens.js` (new)
- `app.py` (add route)

#### Page Structure:
- Header: "Fuel Your Creativity"
- 4 package cards with:
  - Token amount (large, bold)
  - Price
  - Value indicator ("Best Value" badge)
  - "Buy Now" button
- Real-time balance display
- Recent transaction history (last 5)

#### Buy Button Flow:
1. Click "Buy Now" → Call `/api/tokens/create-checkout-session`
2. Receive session URL
3. Redirect to Stripe checkout
4. After payment:
   - Success → Redirect to `/tokens/success`
   - Cancel → Redirect to `/tokens/cancel`

---

### Task 2.5: Success/Failure Pages
**Files:**
- `templates/token_purchase_success.html` (new)
- `templates/token_purchase_cancel.html` (new)

#### Success Page:
- Confetti animation
- "Purchase Successful!" message
- Show new balance
- "Start Creating" button → `/image-generator`
- Transaction receipt (tokens, amount, date)

#### Cancel Page:
- "Purchase Canceled" message
- "Try Again" button → `/buy-tokens`
- FAQ section (why tokens, refund policy)

---

## Testing Strategy

### Test 1: Happy Path (Full Purchase Flow)
**Steps:**
1. Navigate to `/buy-tokens` page
2. Click "Popular Token Pack" ($9.99)
3. Redirect to Stripe checkout
4. Use test card: `4242 4242 4242 4242`
5. Complete payment
6. Verify redirect to `/tokens/success`
7. **Firestore Verification:**
   - `users/{uid}.tokenBalance` increased by 110
   - `transactions` collection has new doc with:
     - `type: "purchase"`
     - `amount: 110`
     - `userId: {uid}`
     - `details.stripeSessionId: {session_id}`

### Test 2: Idempotency (Double Webhook)
**Steps:**
1. Complete a purchase
2. Manually trigger webhook again with same session ID
3. **Verify:** Balance only credited once (check transaction ledger)

### Test 3: Failed Payment
**Steps:**
1. Start checkout flow
2. Use test card: `4000 0000 0000 0002` (decline)
3. **Verify:** No balance change, no transaction record

### Test 4: Concurrent Purchases
**Steps:**
1. Open 2 browser tabs
2. Simultaneously complete 2 purchases
3. **Verify:** Both credited correctly (no race conditions)

---

## Security Considerations

### ✅ Already Implemented
- Firestore atomic transactions (prevents race conditions)
- Session-based authentication
- CSRF protection on POST routes
- Webhook signature verification

### Additional Safeguards
1. **Idempotency:** Check transaction ledger before crediting
2. **Validation:** Verify package names and amounts
3. **Audit Trail:** Every credit logged with Stripe session ID
4. **User Isolation:** Users can only buy for themselves

---

## Configuration Files to Update

### `.env` (Local Development)
```bash
# Token Package Price IDs (from Stripe Dashboard)
STRIPE_TOKEN_STARTER_PRICE_ID=price_xxx
STRIPE_TOKEN_POPULAR_PRICE_ID=price_xxx
STRIPE_TOKEN_PRO_PRICE_ID=price_xxx
STRIPE_TOKEN_CREATOR_PRICE_ID=price_xxx
```

### `config/settings.py`
```python
# Token Package Configuration
TOKEN_PACKAGES = {
    'starter': {
        'name': 'Starter Token Pack',
        'price_usd': 4.99,
        'tokens': 50,
        'price_id': os.getenv('STRIPE_TOKEN_STARTER_PRICE_ID')
    },
    # ... (all 4 packages)
}
```

### Cloud Build Secrets
Add 4 new secrets to GCP Secret Manager:
- `phoenix-stripe-token-starter-price-id`
- `phoenix-stripe-token-popular-price-id`
- `phoenix-stripe-token-pro-price-id`
- `phoenix-stripe-token-creator-price-id`

Update `cloudbuild.yaml` and `cloudbuild-dev.yaml` to inject these.

---

## Firestore Schema Changes

### `users` Collection
```javascript
{
  "tokenBalance": 0,          // Already exists
  "totalTokensEarned": 0,     // For tips received
  "totalTokensSpent": 0,      // For image generation tracking
  "totalTokensPurchased": 0,  // Lifetime purchases
  "stripe_customer_id": "...", // Already exists
  // ... existing fields
}
```

### `transactions` Collection (Already Exists)
```javascript
{
  "userId": "firebase_uid",
  "type": "purchase",  // "purchase", "generation_spend", "tip_sent", "tip_received"
  "amount": 110,       // Positive for credit, negative for debit
  "timestamp": Timestamp,
  "details": {
    "stripeSessionId": "cs_test_...",  // For idempotency
    "paymentAmountUSD": 9.99,
    "package": "popular"
  }
}
```

---

## Success Metrics

### User Metrics
- [ ] Users can view token packages
- [ ] Users can complete purchase with test card
- [ ] Balance updates correctly in real-time
- [ ] Transaction history shows purchase

### Technical Metrics
- [ ] Zero double-credits (idempotency works)
- [ ] 100% webhook success rate
- [ ] < 2 second balance update after payment
- [ ] Atomic transactions prevent race conditions

### Business Metrics
- [ ] Conversion rate on /buy-tokens page
- [ ] Average token purchase size
- [ ] Monthly recurring token revenue
- [ ] Token burn rate (usage vs purchase)

---

## Rollout Plan

### Phase 2a: Development (This Week)
1. Configure Stripe products
2. Build API endpoints
3. Implement webhook handler
4. Create frontend UI
5. Local testing with Stripe test mode

### Phase 2b: Staging (Next Week)
1. Deploy to dev environment
2. End-to-end testing
3. Load testing (concurrent purchases)
4. Security audit

### Phase 2c: Production (Week 3)
1. Create production Stripe products
2. Update environment secrets
3. Deploy to production
4. Monitor first 100 purchases
5. Gradual rollout (10% → 50% → 100%)

---

## Monitoring & Alerts

### Key Metrics to Watch
- Webhook processing latency
- Failed webhook retry count
- Balance discrepancies (audit job)
- Payment failures by reason
- Average purchase amount

### Alert Thresholds
- Webhook failure rate > 1%
- Balance update delay > 5 seconds
- Transaction ledger gap detected
- Duplicate credit attempt

---

## Documentation Deliverables

1. **Token Economy User Guide** - How to buy and use tokens
2. **API Documentation** - Token purchase endpoints
3. **Webhook Integration Guide** - For future payment methods
4. **Troubleshooting Guide** - Common issues and fixes
5. **Phase 2 Test Report** - Validation evidence

---

## Next: Phase 3 Teaser

After tokens are working, we'll build:
- **Tipping System** - Users tip creators directly
- **Image Generation Deduction** - Auto-deduct tokens on generation
- **Earnings Dashboard** - Creators see tip income
- **Withdrawal System** - Creators cash out earnings

---

**Status:** Planning Complete ✅  
**Ready to Build:** Yes  
**Estimated Time:** 2-3 days for full implementation
