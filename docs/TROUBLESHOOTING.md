# Phoenix AI - Stripe Integration Troubleshooting

## Common Issues and Solutions

### 1. "Failed to cancel subscription: No such subscription" Error

**Problem**: You're trying to cancel a subscription that doesn't exist in Stripe, but exists in your Firestore database.

**Cause**: This usually happens when:
- Test data was manually added to Firestore
- A subscription was deleted directly in Stripe but not cleaned up locally
- Development/testing created invalid subscription records

**Solution**:
```bash
# 1. List all subscription records to see what's in your database
python cleanup_test_subscriptions.py --list

# 2. Clean up invalid subscriptions (dry run first)
python cleanup_test_subscriptions.py --cleanup

# 3. If you want to proceed with cleanup, confirm:
python cleanup_test_subscriptions.py --cleanup --confirm

# 4. For a specific user cleanup:
python cleanup_test_subscriptions.py --user YOUR_FIREBASE_UID --confirm
```

**Prevention**: 
- Only create subscriptions through the proper Stripe checkout flow
- Don't manually add subscription records to Firestore
- Use the webhook system to keep data synchronized

### 2. Firestore Query Warning

**Problem**: Warning about using positional arguments in Firestore queries.

**Cause**: Older Firestore query syntax being used.

**Solution**: ✅ Already fixed in the code - queries now use `FieldFilter` syntax.

### 3. "Stripe not configured" Error

**Problem**: Subscription features not working.

**Cause**: Missing Stripe environment variables.

**Solution**:
```bash
# Check your configuration
python setup_stripe.py --test

# Generate environment template if needed
python setup_stripe.py --env
```

Required variables:
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PREMIUM_MONTHLY_PRICE_ID`

### 4. Webhook Signature Verification Failed

**Problem**: Webhooks not being processed.

**Cause**: Incorrect webhook secret or endpoint configuration.

**Solution**:
1. In Stripe Dashboard > Webhooks, verify:
   - Endpoint URL: `https://your-domain.com/api/stripe/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, etc.
2. Copy the **signing secret** (not the webhook ID)
3. Set `STRIPE_WEBHOOK_SECRET=whsec_...`

### 5. User Can't Cancel Subscription

**Problem**: "No active subscription found" when user tries to cancel.

**Cause**: Mismatch between Firestore records and Stripe reality.

**Solution**:
```bash
# Check specific user's subscription status
python cleanup_test_subscriptions.py --list

# Clean up user's invalid records
python cleanup_test_subscriptions.py --user FIREBASE_UID --confirm
```

### 6. Payment Flow Not Working

**Problem**: Users can't complete payment.

**Cause**: Various configuration issues.

**Debugging Steps**:
```bash
# 1. Test configuration
python setup_stripe.py --test

# 2. Check browser console for JavaScript errors
# 3. Verify in Stripe Dashboard that checkout sessions are being created
# 4. Test with Stripe test cards:
#    - 4242 4242 4242 4242 (success)
#    - 4000 0000 0000 0002 (declined)
```

### 7. Features Not Properly Gated

**Problem**: Free users can access premium features.

**Cause**: Decorators not applied or subscription status not being checked.

**Solution**:
```python
# Add to your route
from services.subscription_middleware import premium_required

@your_bp.route('/premium-feature')
@login_required
@premium_required  # Add this decorator
def premium_feature():
    return "Premium content"
```

### 8. Usage Limits Not Working

**Problem**: Users exceed free plan limits.

**Cause**: Usage tracking not implemented.

**Solution**:
```python
# Add usage limits
from services.subscription_middleware import feature_limited

@your_bp.route('/api/chat')
@login_required
@feature_limited('chat_messages')  # Automatically tracks and limits
def chat_api():
    return process_chat()
```

## Quick Diagnosis Commands

### Check Current State
```bash
# See all subscription records
python cleanup_test_subscriptions.py --list

# Test your configuration
python setup_stripe.py --test
```

### Clean Up Issues
```bash
# Safe dry run cleanup
python cleanup_test_subscriptions.py --cleanup

# Actually clean up invalid records
python cleanup_test_subscriptions.py --cleanup --confirm
```

### Monitor Logs
```bash
# In development, watch for these log messages:
# ✅ "Stripe service initialized successfully"
# ❌ "Stripe not configured"
# ❌ "Failed to cancel subscription"
# ❌ "Webhook signature verification failed"
```

## Development vs Production

### Development Setup
- Use Stripe test keys (`sk_test_...`, `pk_test_...`)
- Test with Stripe CLI: `stripe listen --forward-to localhost:5000/api/stripe/webhook`
- Use test card numbers for payments

### Production Setup
- Use live Stripe keys (`sk_live_...`, `pk_live_...`)
- Configure real webhook endpoint
- Set up monitoring and alerting
- Test with real payment methods (small amounts)

## Getting Help

1. **Check the logs** - Most issues are logged with detailed error messages
2. **Test configuration** - Run `python setup_stripe.py --test`
3. **Validate data consistency** - Use the cleanup script to audit your data
4. **Stripe Dashboard** - Check webhook logs and payment history
5. **Firebase Console** - Verify Firestore data and security rules

## Emergency Cleanup

If your database is corrupted with test data:

```bash
# ⚠️  DANGER: This will delete ALL subscription records
# Only use if you're sure you want to start fresh

# First, backup your data
# Then, for complete cleanup of a test environment:
python cleanup_test_subscriptions.py --cleanup --confirm

# Or clean up specific user:
python cleanup_test_subscriptions.py --user FIREBASE_UID --confirm
```

## Best Practices

1. **Always use test mode** during development
2. **Don't manually edit Firestore** subscription records
3. **Use webhooks** to keep data synchronized
4. **Test the complete flow** from signup to cancellation
5. **Monitor for errors** and set up alerts
6. **Keep Stripe and local data in sync**

Remember: The subscription system is designed to be robust and handle edge cases, but proper configuration and testing are essential for smooth operation.