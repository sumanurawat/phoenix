# Quick Visual: Test vs Live Mode Issue

## 🔴 Current Problem (Why It's Broken)

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR APPLICATION                         │
│                                                              │
│  .env file:                                                  │
│  ┌────────────────────────────────────────────────┐        │
│  │ STRIPE_SECRET_KEY=sk_test_51Q...               │◄───┐   │
│  │   ↑ TEST MODE KEY                               │    │   │
│  │                                                  │    │   │
│  │ STRIPE_TOKEN_STARTER_PRICE_ID=price_1SMC...    │    │   │
│  │   ↑ LIVE MODE PRICE ID (PROBLEM!)              │    │   │
│  └────────────────────────────────────────────────┘    │   │
└──────────────────────────────────────────────────────────│──┘
                                                            │
                      Sends request with:                  │
                      Test Key + Live Price ID             │
                                                            │
                                ▼                           │
┌─────────────────────────────────────────────────────────────┐
│                    STRIPE API SERVER                        │
│                                                              │
│  1. Receives: sk_test_... → Routes to TEST DATABASE        │
│  2. Searches for: price_1SMC... in TEST DATABASE           │
│  3. Not Found! ❌                                           │
│  4. Returns Error: "No such price"                         │
│                                                              │
│  ┌─────────────────┐          ┌─────────────────┐         │
│  │  TEST DATABASE  │          │  LIVE DATABASE  │         │
│  │                 │          │                 │         │
│  │ (empty)         │          │ price_1SMC...  │◄────┐   │
│  │                 │          │ price_1SMCl... │     │   │
│  └─────────────────┘          │ price_1SMCw... │     │   │
│                                │ price_1SMCn... │     │   │
│                                └─────────────────┘     │   │
│                                     ▲                  │   │
│                      These exist here, but we can't    │   │
│                      access them with a test key! ─────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Solution (What You Need to Do)

```
┌─────────────────────────────────────────────────────────────┐
│                 STRIPE DASHBOARD (Test Mode)                │
│                                                              │
│  1. Create 4 Products:                                      │
│     ┌─────────────────────────────────────┐                │
│     │ Token Starter Pack    → $4.99       │                │
│     │ Token Popular Pack    → $9.99       │                │
│     │ Token Pro Pack        → $19.99      │                │
│     │ Token Creator Pack    → $49.99      │                │
│     └─────────────────────────────────────┘                │
│                                                              │
│  2. Copy TEST Price IDs:                                    │
│     ┌─────────────────────────────────────┐                │
│     │ price_test_AAAAAAAAAAAAAAAA         │                │
│     │ price_test_BBBBBBBBBBBBBBBB         │                │
│     │ price_test_CCCCCCCCCCCCCCCC         │                │
│     │ price_test_DDDDDDDDDDDDDDDD         │                │
│     └─────────────────────────────────────┘                │
│                          │                                   │
└──────────────────────────│───────────────────────────────────┘
                           │
                           │ Copy these IDs
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     YOUR APPLICATION                         │
│                                                              │
│  Update .env file:                                          │
│  ┌────────────────────────────────────────────────┐        │
│  │ STRIPE_SECRET_KEY=sk_test_51Q...               │        │
│  │   ↑ TEST MODE KEY (no change)                  │        │
│  │                                                  │        │
│  │ STRIPE_TOKEN_STARTER_PRICE_ID=price_test_AAA   │◄───┐   │
│  │ STRIPE_TOKEN_POPULAR_PRICE_ID=price_test_BBB   │    │   │
│  │ STRIPE_TOKEN_PRO_PRICE_ID=price_test_CCC       │    │   │
│  │ STRIPE_TOKEN_CREATOR_PRICE_ID=price_test_DDD   │    │   │
│  │   ↑ NOW USING TEST MODE PRICE IDs ✅           │    │   │
│  └────────────────────────────────────────────────┘    │   │
│                                                          │   │
│  Then restart: ./start_local.sh                         │   │
└──────────────────────────────────────────────────────────│──┘
                                                            │
                      Sends request with:                  │
                      Test Key + Test Price ID             │
                                                            │
                                ▼                           │
┌─────────────────────────────────────────────────────────────┐
│                    STRIPE API SERVER                        │
│                                                              │
│  1. Receives: sk_test_... → Routes to TEST DATABASE        │
│  2. Searches for: price_test_AAA in TEST DATABASE          │
│  3. Found! ✅                                               │
│  4. Creates Checkout Session Successfully                  │
│                                                              │
│  ┌─────────────────┐          ┌─────────────────┐         │
│  │  TEST DATABASE  │          │  LIVE DATABASE  │         │
│  │                 │          │                 │         │
│  │ price_test_AAA ◄┼──────────┤ price_1SMC...  │         │
│  │ price_test_BBB  │  ✅      │ price_1SMCl... │         │
│  │ price_test_CCC  │  Match!  │ price_1SMCw... │         │
│  │ price_test_DDD  │          │ price_1SMCn... │         │
│  └─────────────────┘          └─────────────────┘         │
│         ▲                                                   │
│         │ Now we can access test prices with test key!    │
│         └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 The Fix in 3 Steps

### Step 1: Go to Stripe Dashboard
👉 https://dashboard.stripe.com/test/products
- Make sure you're in **TEST MODE** (top-right toggle)

### Step 2: Create 4 Products
```
Name                    Price    Billing Period
─────────────────────────────────────────────────
Token Starter Pack      $4.99    One time
Token Popular Pack      $9.99    One time  
Token Pro Pack          $19.99   One time
Token Creator Pack      $49.99   One time
```

### Step 3: Update .env File
Replace your current Price IDs with the new **test** Price IDs:
```bash
STRIPE_TOKEN_STARTER_PRICE_ID=price_test_XXXX  # From Stripe dashboard
STRIPE_TOKEN_POPULAR_PRICE_ID=price_test_XXXX  # From Stripe dashboard
STRIPE_TOKEN_PRO_PRICE_ID=price_test_XXXX      # From Stripe dashboard
STRIPE_TOKEN_CREATOR_PRICE_ID=price_test_XXXX  # From Stripe dashboard
```

Then restart: `./start_local.sh`

---

## 🚀 After It Works (Production Launch)

When you're ready to accept real payments:

### Create Live Mode Products
Same process, but in **LIVE MODE**:
1. Switch to Live Mode in Stripe dashboard
2. Create the same 4 products
3. Copy **live** Price IDs (no `_test_` in them)
4. Update production environment secrets

```
DEVELOPMENT                           PRODUCTION
───────────────────────────────────────────────────────────
sk_test_...                    →      sk_live_...
price_test_AAA                 →      price_1SMC... (live)
localhost:8080                 →      your-domain.com
Stripe CLI webhook             →      Real webhook URL
Test card 4242...              →      Real customer cards
```

---

## ❓ Quick FAQ

**Q: Can I test with real cards in test mode?**  
A: No, only test cards like 4242 4242 4242 4242

**Q: Will test mode transactions show in my Stripe balance?**  
A: No, test mode uses fake money

**Q: Do I need to create products in both test and live?**  
A: Yes, they're completely separate databases

**Q: Can I switch between test/live without code changes?**  
A: Yes! Just change the API key and Price IDs in .env

**Q: What if I already have live products?**  
A: Keep them! Create separate test products for testing

---

📖 **For full details, see:** `STRIPE_PRICE_ID_ERROR_GUIDE.md`
