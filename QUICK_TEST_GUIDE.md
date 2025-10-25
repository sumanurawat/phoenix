# Quick Test Execution Guide

## 🎯 You're Ready to Test!

Both servers are running. Here's your step-by-step guide:

---

## Step 1: Test Case 1 - Happy Path (5 minutes)

### Actions:
1. Open browser: **http://localhost:8080**
2. Login with your test account
3. Click "Tokens" in user dropdown → Navigate to Buy Tokens page
4. Click **"Buy Now"** on **Popular Pack**
5. On Stripe checkout:
   - Card: `4242 4242 4242 4242`
   - Expiry: `12/30`
   - CVC: `123`
   - Email: your email
   - Name: any name
   - ZIP: `12345`
6. Click **Pay**
7. Watch for success page with confetti! 🎉

### What to Check:
✅ Confetti animation plays  
✅ Balance shows 120 tokens (10 + 110)  
✅ No errors in browser console (F12)

### In Terminal:
Look for these logs:
```
INFO: [Stripe Service] Creating checkout session...
INFO: [Stripe Webhook] Credited 110 tokens to user...
```

---

## Step 2: Test Case 2 - Idempotency (2 minutes)

### In Stripe CLI Terminal:
1. Scroll up to find the event ID (looks like: `evt_test_webhook_xxxxx`)
2. Copy that event ID
3. Run: `stripe events resend evt_test_webhook_xxxxx`

### What to Check:
✅ Server logs show: `WARNING: Duplicate event received...`  
✅ Balance STILL 120 (not 230!)  
✅ Webhook returns 200 OK

---

## Step 3: Test Case 3 - Cancellation (2 minutes)

### Actions:
1. Go to Buy Tokens page again
2. Click any **"Buy Now"** button
3. On Stripe checkout, **click browser back button**
4. You should land on cancel page

### What to Check:
✅ Cancel page shows friendly message  
✅ "Try Again" button works  
✅ Balance unchanged  
✅ No webhook fired (no logs)

---

## 🎉 All Done?

If all 3 tests pass, run:

```bash
git add .
git commit -m "feat: Complete Phase 2 - Token Economy Purchase Flow

- Add 4 Stripe token packages (Starter/Popular/Pro/Creator)
- Build purchase UI with success/cancel pages
- Add token balance widget to navigation
- Enhance logging with [Stripe Webhook] tags
- Implement idempotency for duplicate events
- All test cases PASSING ✅

Test Results:
✅ Test Case 1: Happy Path - PASS
✅ Test Case 2: Idempotency - PASS  
✅ Test Case 3: Cancellation - PASS"

git push origin main
```

---

## 🐛 If Something Breaks:

**Error in browser console?**
- Check Network tab (F12) → Look for failed API calls
- Copy error message and share

**Webhook not firing?**
- Check Stripe CLI terminal - should show "Ready!"
- Verify webhook secret in logs

**Balance not updating?**
- Check Firestore console directly
- Look for user document and tokenBalance field

**Need help?**
- Full test report: `TOKEN_ECONOMY_TEST_REPORT.md`
- Check server logs for ERROR messages

---

**Ready? Let's test! 🚀**
