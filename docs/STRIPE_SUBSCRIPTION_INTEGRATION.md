# Stripe Subscription Integration Documentation

## Overview
The Phoenix application now includes a complete Stripe subscription system that allows users to subscribe to Basic ($5/month) or Pro ($20/month) plans.

## Architecture

### Components Added
1. **Models**: `models/subscription.py` - Data models and tier configurations
2. **Services**: `services/subscription_service.py` - Stripe integration and subscription management
3. **API Routes**: `api/subscription_routes.py` - REST endpoints for subscription operations
4. **UI Components**: Enhanced `templates/profile.html` with subscription modal
5. **Decorators**: `utils/subscription_decorators.py` - Feature access control

## Setup Instructions

### 1. Stripe Configuration
1. Create a Stripe account (or use existing)
2. Create products in Stripe Dashboard:
   - Basic Plan: $5/month recurring
   - Pro Plan: $20/month recurring
3. Copy the Price IDs and update them in `models/subscription.py`
4. Get your API keys from Stripe Dashboard

### 2. Environment Variables
Add these to your `.env` file:
```bash
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 3. Stripe Webhook Setup
1. In Stripe Dashboard, go to Webhooks
2. Add endpoint: `https://your-domain.com/api/subscription/webhook`
3. Select these events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copy the webhook signing secret to your environment variables

## API Endpoints

### User Subscription Management

#### Create Checkout Session
```http
POST /api/subscription/create-checkout-session
Authorization: Required (login_required)
Content-Type: application/json

{
  "price_id": "price_1RcFAyGgo4tk9CEitD4wp0W"
}
```

#### Get Subscription Status
```http
GET /api/subscription/status
Authorization: Required (login_required)
```

#### Stripe Webhook
```http
POST /api/subscription/webhook
Headers: Stripe-Signature: t=timestamp,v1=signature
```

#### Cancel Subscription
```http
POST /api/subscription/cancel
Authorization: Required (login_required)
```

#### Get Available Plans
```http
GET /api/subscription/plans
Authorization: Not required (public)
```

## Frontend Integration

### Subscription Modal
The profile page now includes a subscription modal that:
- Shows current subscription status
- Displays available plans (Basic and Pro)
- Redirects to Stripe Checkout when a plan is selected
- Handles success/cancel redirects

### JavaScript Functions
- `loadSubscriptionStatus()`: Fetches and displays current subscription
- `subscribe(priceId)`: Creates checkout session and redirects to Stripe

## Feature Access Control

### Using Decorators
```python
from utils.subscription_decorators import subscription_required, feature_required

@subscription_required("basic")
def premium_feature():
    # Only accessible to Basic+ subscribers
    pass

@feature_required("API access")
def api_endpoint():
    # Only accessible to users with "API access" feature
    pass
```

### Subscription Tiers

#### Free Tier
- Basic URL shortening
- Limited analytics (30-day retention)
- 10 link limit
- Community support

#### Basic Tier ($5/month)
- Unlimited URL shortening
- Enhanced analytics (90-day retention)
- 1,000 link limit
- Email support
- Custom aliases

#### Pro Tier ($20/month)
- Everything in Basic
- Advanced analytics (365-day retention)
- Unlimited links
- Priority support
- Custom domains
- API access
- Bulk operations

## Data Storage

### Firestore Collection: `user_subscriptions`
```javascript
{
  "subscription_tier": "basic",
  "stripe_customer_id": "cus_...",
  "stripe_subscription_id": "sub_...",
  "status": "active",
  "current_period_end": "2025-07-20T...",
  "last_updated": "2025-06-20T...",
  "cancel_at_period_end": false
}
```

## Testing

### Local Testing
1. Use Stripe test mode (test API keys)
2. Use test credit card numbers:
   - Success: `4242424242424242`
   - Decline: `4000000000000002`

### Webhook Testing
Use Stripe CLI for local webhook testing:
```bash
stripe listen --forward-to localhost:5000/api/subscription/webhook
```

## Security Features

1. **Authentication**: All subscription endpoints require user login
2. **Input Validation**: Price IDs are validated against allowed values
3. **Webhook Verification**: Stripe signatures are verified for security
4. **User Isolation**: Users can only access their own subscription data

## Error Handling

The system includes comprehensive error handling:
- Stripe API errors are caught and logged
- Invalid requests return appropriate HTTP status codes
- Webhook processing failures are logged but don't affect user experience
- Fallback to free tier if subscription data is unavailable

## Deployment Notes

### Production Environment
1. Switch to live Stripe API keys
2. Update webhook endpoint to production URL
3. Set up Google Cloud Secret Manager for API keys
4. Update `cloudbuild.yaml` to include Stripe secrets

### Staging Environment
1. Use test Stripe API keys
2. Set up separate webhook endpoint for staging
3. Test all subscription flows thoroughly

## Monitoring

### Important Metrics to Monitor
- Subscription signup rate
- Payment failure rate
- Webhook processing success rate
- Feature usage by subscription tier

### Logging
All subscription events are logged with appropriate levels:
- INFO: Successful operations
- WARNING: Non-critical issues
- ERROR: Failed operations that need attention

## Next Steps

1. **Email Notifications**: Integrate with SendGrid for subscription emails
2. **Usage Analytics**: Track feature usage by subscription tier
3. **Billing Portal**: Add customer billing portal link
4. **Proration**: Handle plan upgrades/downgrades with proration
5. **Team Plans**: Add multi-user subscription support

## Support

For Stripe-related issues:
1. Check Stripe Dashboard for payment status
2. Review webhook event logs
3. Monitor application logs for subscription errors
4. Contact Stripe support for payment processing issues
