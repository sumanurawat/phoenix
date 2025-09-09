# Stripe Subscription Integration Guide

This document explains how to set up and use the Stripe subscription integration in Phoenix AI Platform.

## Overview

The Phoenix AI Platform now includes a complete Stripe subscription system that provides:

- Professional subscription management similar to ChatGPT/GitHub Copilot
- Secure payment processing with Stripe Elements
- Firebase Firestore integration for subscription data
- Feature limiting based on subscription status
- Webhook handling for subscription lifecycle events

## Setup Instructions

### 1. Stripe Account Configuration

1. Create a Stripe account at https://stripe.com
2. In the Stripe Dashboard, create a new Product:
   - Name: "Premium Monthly"
   - Price: $5.00 USD
   - Billing: Monthly recurring
3. Copy the Price ID (starts with `price_`)

### 2. Environment Variables

Add these environment variables to your deployment:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_... # or sk_test_... for testing
STRIPE_PUBLISHABLE_KEY=pk_live_... # or pk_test_... for testing
STRIPE_WEBHOOK_SECRET=whsec_... # From Stripe webhook configuration
STRIPE_PREMIUM_MONTHLY_PRICE_ID=price_... # From your Stripe product
```

### 3. Webhook Configuration

1. In Stripe Dashboard, go to Webhooks
2. Add endpoint: `https://your-domain.com/api/stripe/webhook`
3. Select these events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copy the webhook signing secret

### 4. Firebase Deployment

Deploy the updated Firestore rules and indexes:

```bash
firebase deploy --only firestore:rules
firebase deploy --only firestore:indexes
```

## Usage Examples

### 1. Checking Subscription Status

```python
from services.stripe_service import StripeService

stripe_service = StripeService()

# Check if user has premium subscription
firebase_uid = "user123"
is_premium = stripe_service.is_user_premium(firebase_uid)

if is_premium:
    print("User has premium access")
else:
    print("User is on free plan")
```

### 2. Using Premium-Required Decorator

```python
from services.subscription_middleware import premium_required
from flask import Blueprint

api_bp = Blueprint('api', __name__)

@api_bp.route('/premium-feature')
@premium_required
def premium_feature():
    """This route requires premium subscription."""
    return {"message": "Premium feature accessed"}
```

### 3. Feature Limiting

```python
from services.subscription_middleware import check_feature_limit

# Check if user can use a feature
limit_result = check_feature_limit('chat_messages', current_usage=8, free_limit=5)

if limit_result['allowed']:
    # Allow feature usage
    process_chat_message()
else:
    # Show upgrade prompt
    return {"error": "Feature limit reached", "upgrade_url": "/subscription"}
```

### 4. Template Integration

In your templates, subscription status is automatically available:

```html
{% if subscription.is_premium %}
    <span class="badge bg-success">Premium User</span>
{% else %}
    <a href="/subscription" class="btn btn-primary">Upgrade to Premium</a>
{% endif %}
```

## API Endpoints

### Subscription Management
- `GET /api/stripe/config` - Get Stripe configuration
- `POST /api/stripe/create-checkout-session` - Create payment session
- `GET /api/stripe/subscription/status` - Get user subscription status
- `POST /api/stripe/subscription/cancel` - Cancel subscription

### Webhooks
- `POST /api/stripe/webhook` - Handle Stripe events

### UI Pages
- `/subscription` - Subscription management page
- `/subscription/success` - Post-payment success page
- `/subscription/cancel` - Payment cancellation page

## Database Schema

### Users Collection
```javascript
{
  firebase_uid: "string",
  email: "string", 
  stripe_customer_id: "string", // Created on first payment
  created_at: "timestamp",
  updated_at: "timestamp"
}
```

### User Subscriptions Collection
```javascript
{
  firebase_uid: "string",
  stripe_customer_id: "string",
  stripe_subscription_id: "string",
  plan_id: "string", // e.g., "premium_monthly"
  status: "string", // "active", "canceled", "past_due", etc.
  current_period_start: "timestamp",
  current_period_end: "timestamp", 
  cancel_at_period_end: "boolean",
  created_at: "timestamp",
  updated_at: "timestamp"
}
```

## Security Features

### Firestore Rules
- Users can only access their own subscription data
- Authentication required for all subscription operations
- Webhook operations bypass authentication with signature verification

### Stripe Security
- Webhook signature verification prevents unauthorized calls
- Secure customer ID linking with Firebase users
- PCI-compliant payment processing through Stripe

## Feature Limits

### Free Plan
- 5 AI conversations per day
- Basic search features
- Standard AI models

### Premium Plan ($5/month)
- Unlimited AI conversations
- Advanced analytics dashboard
- Premium AI models access
- Priority support
- Export conversation history
- Custom AI personalities

## Testing

Run the included tests to verify integration:

```bash
# Test basic Stripe functionality
python test_stripe_basic.py

# Test app startup with Stripe integration
python test_app_startup.py
```

## Troubleshooting

### Common Issues

1. **Stripe not configured error**
   - Ensure all environment variables are set
   - Check Stripe keys are valid

2. **Webhook signature verification failed**
   - Verify webhook secret is correct
   - Check endpoint URL matches Stripe configuration

3. **Customer creation failed**
   - Ensure Firebase user is authenticated
   - Check Firestore permissions

4. **Subscription status not updating**
   - Verify webhook events are being received
   - Check Firestore write permissions

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

1. Set production Stripe keys
2. Configure production webhook endpoint
3. Deploy Firestore rules and indexes
4. Test webhook delivery
5. Monitor subscription metrics in Stripe Dashboard

## Support

For issues with the Stripe integration:

1. Check the logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test webhook delivery in Stripe Dashboard
4. Review Firestore security rules and indexes