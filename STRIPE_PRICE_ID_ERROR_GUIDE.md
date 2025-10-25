# Stripe Price ID Error - Comprehensive Troubleshooting Guide

**Error Date:** October 25, 2025  
**Error Type:** `InvalidRequestError: No such price`  
**Affected Feature:** Token Purchase System (Phase 2)

---

## 🔴 The Error

```
stripe._error.InvalidRequestError: Request req_FfgSHNyBMJ9GYh: 
No such price: 'price_1SMCkkGgo4tk9CEiKRDzvA1L'
```

**Translation:** Your application is trying to use a Stripe Price ID that doesn't exist in the current Stripe environment.

---

## 🧠 Understanding the Problem

### What are Stripe Price IDs?

In Stripe's architecture, selling something requires:
1. **Product** - What you're selling (e.g., "Token Starter Pack")
2. **Price** - How much it costs (e.g., $4.99 one-time payment)
3. **Price ID** - A unique identifier Stripe generates for that price (e.g., `price_1SMCkkGgo4tk9CEiKRDzvA1L`)

When a customer clicks "Buy Now" in your application:
```
User clicks Buy → Your app sends Price ID to Stripe → Stripe creates checkout session → User pays
```

If the Price ID doesn't exist, Stripe rejects the request with the error you're seeing.

---

## 🎯 Root Cause Analysis

### The Problem: Test/Live Mode Mismatch

Stripe has **TWO completely separate environments**:

| Environment | API Key Format | Price ID Format | Usage |
|-------------|----------------|-----------------|-------|
| **Test Mode** | `sk_test_...` | `price_test_...` | Development & Testing |
| **Live Mode** | `sk_live_...` | `price_...` | Production (real payments) |

**Your Current Situation:**
- ✅ Your `.env` file has a **Test Mode API key** (`sk_test_...`)
- ❌ Your `.env` file has **Live Mode Price IDs** (`price_1SMC...`)
- ❌ **Test keys can't see Live prices** → Error!

### How This Happened

Looking at your configuration:
```bash
# In your .env file
STRIPE_SECRET_KEY=sk_test_...  # TEST MODE KEY
STRIPE_TOKEN_STARTER_PRICE_ID=price_1SMCkkGgo4tk9CEiKRDzvA1L  # LIVE MODE PRICE
```

When Phoenix calls `stripe.checkout.Session.create()` with a test key, Stripe searches the **test environment database** for `price_1SMCkkGgo4tk9CEiKRDzvA1L`, doesn't find it, and throws the error.

---

## 🏗️ Phoenix Architecture Context

### Where Price IDs Are Used

**Configuration Layer** (`api/token_routes.py`):
```python
TOKEN_PACKAGES = {
    'starter': {
        'name': 'Starter Pack',
        'tokens': 50,
        'price': 4.99,
        'price_id_env': 'STRIPE_TOKEN_STARTER_PRICE_ID',  # ← Reads from .env
        'description': 'Perfect for trying out our platform'
    },
    # ... 3 more packages
}
```

**Purchase Flow** (`api/token_routes.py` → `services/stripe_service.py`):
```python
# 1. User clicks "Buy Now" on Starter Pack
# 2. Frontend sends: { "package": "starter" }
# 3. Backend looks up price_id from .env:
price_id = os.getenv('STRIPE_TOKEN_STARTER_PRICE_ID')  # Gets the wrong ID!

# 4. Creates checkout session with Stripe:
stripe.checkout.Session.create(
    line_items=[{
        'price': price_id,  # ← This is where the error happens
        'quantity': 1
    }]
)
```

**The Error Point:**
```python
# File: services/stripe_service.py, line 309
checkout_session = stripe.checkout.Session.create(**session_params)
# ↑ Stripe API rejects because price_id doesn't exist in test mode
```

---

## ✅ Solution Options

### Option 1: Use Test Mode (RECOMMENDED for Development)

**Pros:**
- ✅ No real money involved
- ✅ Unlimited test transactions
- ✅ Can test all scenarios safely
- ✅ Standard development practice

**Cons:**
- ❌ Need to create test products
- ❌ Can't test real payment processing

**When to Use:** 
- NOW (for development and testing)
- Before launching to production
- For QA and staging environments

---

### Option 2: Use Live Mode (Only for Production Launch)

**Pros:**
- ✅ Real customer payments
- ✅ Production environment

**Cons:**
- ❌ Real money at risk
- ❌ Can't test freely
- ❌ Mistakes affect real customers
- ❌ Refunds cost fees

**When to Use:**
- After ALL testing complete
- When deploying to production
- Only on live domain (not localhost)

---

## 🛠️ Recommended Fix: Set Up Test Mode

### Step 1: Verify Current Stripe Mode

Check your `.env` file:
```bash
# Look for your Stripe secret key
STRIPE_SECRET_KEY=sk_test_...  # If starts with sk_test_ → TEST MODE ✅
STRIPE_SECRET_KEY=sk_live_...  # If starts with sk_live_ → LIVE MODE ⚠️
```

**Your Current Status:** TEST MODE (correct for development)

---

### Step 2: Create Test Mode Products in Stripe Dashboard

You need to create 4 products in Stripe's **Test Mode** dashboard.

#### Why Create New Products?

Live mode and test mode are **completely separate databases**. Even if you have products in live mode, they don't exist in test mode. You must create them in both environments.

#### Access Stripe Test Mode Dashboard

1. Go to: https://dashboard.stripe.com/
2. Look at **top-right corner** for mode toggle
3. Click to switch to **"Test mode"** (toggle should be on left, colored)
4. Or go directly to: https://dashboard.stripe.com/test/products

---

### Step 3: Create Each Token Package

For each of the 4 packages, follow this process:

#### Package 1: Starter Pack
1. **Navigate to Products:**
   - URL: https://dashboard.stripe.com/test/products
   - Click **"+ Add product"** button (top right)

2. **Fill Product Details:**
   ```
   Name: Token Starter Pack
   Description: 50 AI generation tokens - Perfect for trying out our platform
   ```

3. **Set Pricing:**
   - **Pricing model:** Standard pricing
   - **Price:** 4.99
   - **Currency:** USD
   - **Billing period:** One time ⚠️ IMPORTANT!
   
   ⚠️ **Common Mistake:** Don't select "Recurring" - tokens are one-time purchases, not subscriptions!

4. **Save and Copy Price ID:**
   - Click **"Save product"**
   - Stripe shows the product page
   - Find **"Pricing"** section
   - Copy the **Price ID** (format: `price_test_XXXXXXXXXXXX`)
   - Save it as: `STRIPE_TOKEN_STARTER_PRICE_ID`

#### Package 2: Popular Pack
```
Name: Token Popular Pack
Description: 110 AI generation tokens (10% bonus!) - Most popular choice
Price: 9.99
Billing period: One time
```
Save Price ID as: `STRIPE_TOKEN_POPULAR_PRICE_ID`

#### Package 3: Pro Pack
```
Name: Token Pro Pack
Description: 250 AI generation tokens (25% bonus!) - For power users
Price: 19.99
Billing period: One time
```
Save Price ID as: `STRIPE_TOKEN_PRO_PRICE_ID`

#### Package 4: Creator Pack
```
Name: Token Creator Pack
Description: 700 AI generation tokens (40% bonus!) - Maximum value
Price: 49.99
Billing period: One time
```
Save Price ID as: `STRIPE_TOKEN_CREATOR_PRICE_ID`

---

### Step 4: Update .env File

Replace the current live mode Price IDs with your new test mode IDs:

**Before (Current - BROKEN):**
```bash
STRIPE_TOKEN_STARTER_PRICE_ID=price_1SMCkkGgo4tk9CEiKRDzvA1L
STRIPE_TOKEN_POPULAR_PRICE_ID=price_1SMClKGgo4tk9CEiGBbGyANR
STRIPE_TOKEN_PRO_PRICE_ID=price_1SMClwGgo4tk9CEitpOgCIyN
STRIPE_TOKEN_CREATOR_PRICE_ID=price_1SMCnBGgo4tk9CEiUR9MYPLK
```

**After (Test Mode - WORKING):**
```bash
STRIPE_TOKEN_STARTER_PRICE_ID=price_test_XXXXXXXXXXXX  # Your test starter ID
STRIPE_TOKEN_POPULAR_PRICE_ID=price_test_XXXXXXXXXXXX  # Your test popular ID
STRIPE_TOKEN_PRO_PRICE_ID=price_test_XXXXXXXXXXXX     # Your test pro ID
STRIPE_TOKEN_CREATOR_PRICE_ID=price_test_XXXXXXXXXXXX # Your test creator ID
```

---

### Step 5: Restart Application

After updating `.env`:
```bash
# Stop the running server (Ctrl+C in terminal)
# Restart it
source venv/bin/activate
./start_local.sh
```

The server will reload the new Price IDs from `.env`.

---

### Step 6: Test the Fix

1. Open: http://localhost:8080/buy-tokens
2. Click **"Buy Now"** on any package
3. You should see Stripe Checkout (no error)
4. Use test card: `4242 4242 4242 4242`

**Expected Logs (Success):**
```
INFO: [Stripe Service] Creating checkout session for user ...
INFO: Successfully created checkout session cs_test_...
```

**No More Error!** ✅

---

## 🔍 Verification Checklist

Before considering this fixed, verify:

- [ ] Stripe dashboard shows **"Test mode"** active (top-right toggle)
- [ ] All 4 products created with **"One time"** billing
- [ ] All 4 Price IDs copied (each starts with `price_test_`)
- [ ] `.env` file updated with all 4 test Price IDs
- [ ] Application restarted to load new configuration
- [ ] `/buy-tokens` page loads without errors
- [ ] Clicking "Buy Now" redirects to Stripe Checkout
- [ ] No `InvalidRequestError` in server logs

---

## 🚀 When to Switch to Live Mode

**After successful testing**, when you're ready to accept real payments:

### Step 1: Create Live Mode Products

Repeat the entire product creation process in **Live Mode**:
1. Switch Stripe dashboard to **Live mode** (toggle right)
2. Go to: https://dashboard.stripe.com/products
3. Create the same 4 products with same prices
4. Copy the live Price IDs (they'll start with `price_`, not `price_test_`)

### Step 2: Update Production Environment

**For Cloud Run Production:**
```bash
# Update secrets in Google Cloud
gcloud secrets versions add STRIPE_TOKEN_STARTER_PRICE_ID --data-file=- <<< "price_XXXX"
gcloud secrets versions add STRIPE_TOKEN_POPULAR_PRICE_ID --data-file=- <<< "price_XXXX"
gcloud secrets versions add STRIPE_TOKEN_PRO_PRICE_ID --data-file=- <<< "price_XXXX"
gcloud secrets versions add STRIPE_TOKEN_CREATOR_PRICE_ID --data-file=- <<< "price_XXXX"

# Also update your live secret key
gcloud secrets versions add STRIPE_SECRET_KEY --data-file=- <<< "sk_live_XXXX"
```

**For Local Testing Live Mode (NOT RECOMMENDED):**
```bash
# Update .env with live keys
STRIPE_SECRET_KEY=sk_live_XXXXXXXXXXXX
STRIPE_TOKEN_STARTER_PRICE_ID=price_XXXXXXXXXXXX  # Live IDs (no _test_)
# ... other live Price IDs
```

⚠️ **Warning:** Never commit live API keys to git! Use environment variables or secret managers.

---

## 🎓 Understanding Stripe Environments

### Test Mode vs Live Mode

| Aspect | Test Mode | Live Mode |
|--------|-----------|-----------|
| **Purpose** | Development & Testing | Production |
| **Money** | Fake (no charges) | Real (actual payments) |
| **API Keys** | `sk_test_...`, `pk_test_...` | `sk_live_...`, `pk_live_...` |
| **Price IDs** | `price_test_...` | `price_...` |
| **Customer IDs** | `cus_test_...` | `cus_...` |
| **Test Cards** | 4242 4242 4242 4242 | Real cards only |
| **Webhooks** | Use Stripe CLI | Real HTTPS endpoint |
| **Refunds** | Free, unlimited | Costs fees |

### Why Separate Environments?

**Safety:** Can't accidentally charge real customers during testing  
**Isolation:** Test data doesn't pollute production data  
**Flexibility:** Unlimited testing without financial risk  
**Standard Practice:** Industry standard for payment systems

---

## 🏗️ Architecture Implications

### How Phoenix Handles Multiple Environments

**Environment Detection (automatic):**
```python
# In services/stripe_service.py
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Stripe SDK automatically detects test vs live based on key format
# sk_test_ → routes to test.stripe.com
# sk_live_ → routes to api.stripe.com
```

**Configuration Management:**
```bash
# Development (.env file)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_TOKEN_STARTER_PRICE_ID=price_test_...

# Production (Google Secret Manager)
STRIPE_SECRET_KEY=sk_live_...  # Injected at runtime
STRIPE_TOKEN_STARTER_PRICE_ID=price_...  # No test prefix
```

**Webhook Endpoints:**
```bash
# Local Development (Stripe CLI forwards)
stripe listen --forward-to localhost:8080/api/stripe/webhook

# Production (Real endpoint)
https://phoenix-ai-platform-xyz.run.app/api/stripe/webhook
```

### Why This Design?

1. **Same codebase** works in both environments
2. **Environment-specific configuration** via `.env` or secrets
3. **No code changes** needed when switching environments
4. **Safe testing** without production impact

---

## 🐛 Common Mistakes to Avoid

### Mistake 1: Mixing Test and Live Keys
```bash
# ❌ WRONG - Will fail!
STRIPE_SECRET_KEY=sk_test_...
STRIPE_TOKEN_STARTER_PRICE_ID=price_1SMC...  # Live price with test key

# ✅ CORRECT - Must match!
STRIPE_SECRET_KEY=sk_test_...
STRIPE_TOKEN_STARTER_PRICE_ID=price_test_...  # Test price with test key
```

### Mistake 2: Selecting "Recurring" Instead of "One time"
```
❌ WRONG: Billing period = Monthly/Yearly (creates subscriptions)
✅ CORRECT: Billing period = One time (one-time payment)
```

**Why it matters:** Subscriptions require different webhook handling and cancellation logic. Token purchases are simple one-time payments.

### Mistake 3: Forgetting to Create Products in BOTH Environments
```
❌ Created products in Live mode only
❌ Trying to test with live Price IDs
✅ Create products in Test mode for testing
✅ Create products in Live mode for production
```

### Mistake 4: Not Restarting Application After .env Changes
```bash
# ❌ WRONG - App still using old Price IDs from memory
# Edit .env
# Immediately test → Still fails!

# ✅ CORRECT - Reload configuration
# Edit .env
./start_local.sh  # Restarts app, loads new .env
# Now test → Works!
```

---

## 📊 Testing Checklist

Once you fix the Price IDs, verify everything works:

### Phase 1: Configuration Validation
- [ ] All 4 test Price IDs in `.env`
- [ ] All Price IDs start with `price_test_`
- [ ] Stripe secret key starts with `sk_test_`
- [ ] Application restarted

### Phase 2: Frontend Validation
- [ ] Navigate to `/buy-tokens` - page loads
- [ ] All 4 packages display correctly
- [ ] Current balance shows in header
- [ ] No console errors (F12 → Console)

### Phase 3: Checkout Flow
- [ ] Click "Buy Now" on any package
- [ ] Redirects to Stripe Checkout (not error page)
- [ ] Stripe Checkout shows correct price
- [ ] Can fill in test card details

### Phase 4: Payment Processing
- [ ] Complete payment with test card
- [ ] Redirects to success page
- [ ] Confetti animation plays
- [ ] Balance updated correctly
- [ ] Server logs show webhook received

### Phase 5: Database Validation
- [ ] Firestore `users/{userId}/tokenBalance` updated
- [ ] Transaction document created in `transactions` collection
- [ ] Transaction has correct `amount`, `packageId`, `stripeSessionId`

---

## 🆘 If You're Still Getting Errors

### Error: "No such price" (after updating .env)
**Cause:** Application not restarted  
**Fix:** Stop server (Ctrl+C), run `./start_local.sh`

### Error: "No such customer"
**Cause:** Customer created in different environment  
**Fix:** Delete and recreate customer in current environment

### Error: "Invalid API Key"
**Cause:** Wrong Stripe secret key  
**Fix:** Verify `STRIPE_SECRET_KEY` in `.env` matches your Stripe account

### Error: Webhook not firing
**Cause:** Stripe CLI not running  
**Fix:** Run `stripe listen --forward-to localhost:8080/api/stripe/webhook`

### Error: "Resource already exists"
**Cause:** Trying to create duplicate product  
**Fix:** Check existing products in Stripe dashboard first

---

## 📞 Getting Help

### Check Stripe Dashboard
- Test mode: https://dashboard.stripe.com/test/products
- Live mode: https://dashboard.stripe.com/products
- Logs: https://dashboard.stripe.com/test/logs

### Check Phoenix Logs
```bash
# Server logs show detailed error messages
# Look for lines with ERROR: or WARNING:
# Example: ERROR:services.stripe_service:Failed to create token checkout session
```

### Stripe Documentation
- Products & Prices: https://stripe.com/docs/products-prices/overview
- Checkout Sessions: https://stripe.com/docs/payments/checkout
- Test Cards: https://stripe.com/docs/testing

---

## ✅ Success Criteria

You'll know it's working when:
1. ✅ `/buy-tokens` page loads without errors
2. ✅ Clicking "Buy Now" opens Stripe Checkout
3. ✅ Completing test payment redirects to success page
4. ✅ Token balance increases correctly
5. ✅ Server logs show: `[Stripe Webhook] Credited X tokens to user...`
6. ✅ Firestore shows updated balance and transaction

---

## 🎯 Next Steps After Fix

Once Price IDs are working:
1. Complete Test Case 1 (Happy Path)
2. Complete Test Case 2 (Idempotency)
3. Complete Test Case 3 (Cancellation)
4. Commit all changes
5. Plan production deployment with live Price IDs

---

**Last Updated:** October 25, 2025  
**Status:** Awaiting test mode Price ID creation  
**Action Required:** Create 4 products in Stripe Test Mode dashboard
