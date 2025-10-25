# 🎯 Token Economy - Completion Roadmap

## Current Status: 5/8 Complete ✅

### ✅ Already Done (Backend Complete!)
1. ✅ Review existing Stripe integration
2. ✅ Build token purchase API endpoint  
3. ✅ Enhance webhook handler
4. ✅ Implement atomic token crediting
5. ✅ Documentation and deployment prep

### 🎯 Remaining Tasks (In Order)

---

## Task #1: Configure Stripe Products (15 min) 🔧
**Status:** ⏳ BLOCKED - Requires YOUR action  
**Who:** YOU (I can't access your Stripe Dashboard)

### Quick Steps:
```
1. Go to: https://dashboard.stripe.com/test/products
2. Click "Add product" (4 times, one for each package)
3. For each product:
   - Set name, description, price
   - Choose "One time" billing
   - Copy the Price ID (starts with price_)
4. Add all 4 Price IDs to .env file
```

### Detailed Instructions:

#### Product 1: Starter Pack
```
Name: Token Starter Pack
Description: 50 tokens for trying out Phoenix
Price: $4.99 USD
Billing: One time
```
→ **Copy Price ID:** `price_xxxxxxxxxxxxx`

#### Product 2: Popular Pack  
```
Name: Token Popular Pack
Description: 110 tokens - most popular choice! (10% bonus)
Price: $9.99 USD
Billing: One time
```
→ **Copy Price ID:** `price_xxxxxxxxxxxxx`

#### Product 3: Pro Pack
```
Name: Token Pro Pack
Description: 250 tokens for power users (25% bonus)
Price: $19.99 USD
Billing: One time
```
→ **Copy Price ID:** `price_xxxxxxxxxxxxx`

#### Product 4: Creator Pack
```
Name: Token Creator Pack
Description: 700 tokens - maximum value! (40% bonus)
Price: $49.99 USD
Billing: One time
```
→ **Copy Price ID:** `price_xxxxxxxxxxxxx`

### Then Update .env:
```bash
# Add these lines to .env
STRIPE_TOKEN_STARTER_PRICE_ID=price_1ABC123...
STRIPE_TOKEN_POPULAR_PRICE_ID=price_1DEF456...
STRIPE_TOKEN_PRO_PRICE_ID=price_1GHI789...
STRIPE_TOKEN_CREATOR_PRICE_ID=price_1JKL012...
```

### Verification:
```bash
# After adding to .env, test the API
curl http://localhost:8080/api/tokens/packages | jq

# All 4 packages should show "available": true
```

---

## Task #2: Build Token Purchase UI (30 min) 🎨
**Status:** ⏳ READY - I can do this now  
**Who:** ME (AI Assistant)

### What I'll Create:

**1. Buy Tokens Page** (`/buy-tokens`)
- 4 beautiful package cards with hover effects
- Show current token balance at top
- Highlight "MOST POPULAR" and "BEST VALUE" badges
- Responsive grid layout (Bootstrap 5)
- Click button → Create checkout → Redirect to Stripe

**2. Success Page** (`/token-purchase-success`)
- Confetti animation 🎉
- Show new token balance
- Display package purchased
- Link to start creating content

**3. Cancel Page** (`/token-purchase-cancel`)
- Friendly "no worries" message
- Retry button to go back
- Link to contact support

**4. Token Balance Widget**
- Add to navbar/header
- Real-time balance display
- Link to purchase more

### Files I'll Create:
```
templates/buy_tokens.html
templates/token_purchase_success.html
templates/token_purchase_cancel.html
static/css/token_purchase.css
static/js/buy_tokens.js
```

### Files I'll Modify:
```
app.py (add 3 new routes)
templates/base.html (add token balance widget)
```

**Just say:** "Build the frontend" and I'll create everything!

---

## Task #3: End-to-End Testing (20 min) 🧪
**Status:** ⏳ WAITING - Needs Task #1 & #2 complete  
**Who:** BOTH (collaborative testing)

### Test Scenarios:

#### Test 1: API Endpoints
```bash
# 1. List packages
curl http://localhost:8080/api/tokens/packages | jq

# 2. Get balance (requires login)
curl -b cookies.txt http://localhost:8080/api/tokens/balance

# 3. Get transaction history
curl -b cookies.txt http://localhost:8080/api/tokens/transactions?limit=10
```

#### Test 2: Purchase Flow (Happy Path)
```
1. Start server: ./start_local.sh
2. Login to app
3. Navigate to /buy-tokens
4. Click "Buy Now" on Popular Pack ($9.99)
5. Redirected to Stripe checkout
6. Enter test card: 4242 4242 4242 4242
   - CVV: 123
   - Expiry: 12/34
   - ZIP: 12345
7. Click "Pay"
8. Redirected to success page
9. Verify: Balance shows +110 tokens
10. Check Firestore: Transaction recorded
```

#### Test 3: Webhook Idempotency
```bash
# Setup Stripe CLI
stripe listen --forward-to localhost:8080/api/stripe/webhook

# Complete a purchase, then:
# Manually replay webhook
stripe trigger checkout.session.completed

# Expected: "Session already processed - skipping duplicate"
# Balance should NOT double
```

#### Test 4: Error Handling
```
1. Try invalid package: {"package": "invalid"}
   → Expect: 400 error
2. Try without login
   → Expect: 401 error
3. Try declined card: 4000 0000 0000 0002
   → Expect: Redirect to cancel page
```

---

## 📊 Time Estimates

| Task | Who | Time | Status |
|------|-----|------|--------|
| 1. Stripe Config | YOU | 15 min | ⏳ Todo |
| 2. Build UI | ME | 30 min | ✅ Ready |
| 3. Testing | BOTH | 20 min | ⏳ Waiting |
| **TOTAL** | - | **65 min** | **~1 hour** |

---

## 🚀 Recommended Order

### Option A: Sequential (Safest)
```
1. You configure Stripe (15 min)
2. I build frontend (30 min)  
3. We test together (20 min)
Total: 65 minutes
```

### Option B: Parallel (Faster)
```
1. I build frontend NOW (30 min) 
   - Works without Stripe config
   - Shows "Package unavailable" until configured
   
2. You configure Stripe (15 min)
   - Can do while I'm building
   
3. We test together (20 min)
Total: 30 minutes (overlapped tasks)
```

---

## 💡 What Should We Do First?

### Say ONE of these:

**Option 1:** "Build the frontend now"  
→ I'll create all UI pages immediately (works without Stripe)

**Option 2:** "I'll configure Stripe first"  
→ I'll give you step-by-step Stripe Dashboard instructions

**Option 3:** "Show me what the UI will look like"  
→ I'll show you mockups/wireframes first

**Option 4:** "Let's test what we have so far"  
→ I'll test the API endpoints that work now

---

## 📋 My Recommendation

**Do this RIGHT NOW:**

1. **Me:** Build frontend (30 min) - No dependencies needed
2. **You:** Configure Stripe in parallel (15 min) - Independent task
3. **Both:** Test together (20 min) - Once both are done

This gets us to **100% complete in ~30 minutes** instead of 65!

---

## 🎯 Decision Time

**What do you want me to do first?**

A) Build the frontend NOW (recommended)  
B) Wait for you to configure Stripe  
C) Show me mockups/designs first  
D) Test existing API endpoints  

Just tell me A, B, C, or D (or anything else you want)! 🚀
