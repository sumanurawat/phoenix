# Phoenix AI - Stripe Integration Guide

This comprehensive guide explains how to set up and use the Stripe subscription system in Phoenix AI Platform, transforming it into a professional SaaS platform with subscription management capabilities.

## 🚀 Overview

Phoenix AI now includes a complete Stripe integration that provides:

- **Professional Subscription Management** - Like ChatGPT, GitHub Copilot, and other SaaS platforms
- **Secure Payment Processing** - PCI-compliant checkout using Stripe Elements  
- **Firebase Integration** - Seamless user and subscription data management
- **Feature Gating** - Subscription-based access control with usage limits
- **Professional UI** - Modern subscription management interface
- **Webhook Support** - Real-time subscription lifecycle management

## 📋 Quick Start

### 1. Environment Setup

Add these environment variables to your `.env` file or deployment configuration:

```bash
# Stripe Configuration (Required)
STRIPE_SECRET_KEY=sk_test_...  # Your Stripe secret key
STRIPE_PUBLISHABLE_KEY=pk_test_...  # Your Stripe publishable key  
STRIPE_WEBHOOK_SECRET=whsec_...  # Webhook endpoint secret
STRIPE_PREMIUM_MONTHLY_PRICE_ID=price_...  # Your product price ID
```

### 2. Stripe Account Setup

1. **Create Stripe Account**: Sign up at https://stripe.com
2. **Create Product**: 
   - Name: "Premium Monthly"
   - Price: $5.00 USD  
   - Billing: Monthly recurring
3. **Copy Price ID**: Save the price ID (starts with `price_`)
4. **Setup Webhook**: Add endpoint `https://your-domain.com/api/stripe/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`

### 3. Deploy Firestore Changes

```bash
firebase deploy --only firestore:rules
firebase deploy --only firestore:indexes
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 🏗️ Architecture

### Core Components

#### StripeService (`services/stripe_service.py`)
- Payment processing and customer management
- Subscription lifecycle operations
- Webhook event handling
- Usage tracking and analytics

#### Subscription Middleware (`services/subscription_middleware.py`)  
- Feature gating decorators (`@premium_required`, `@feature_limited`)
- Usage limit checking and enforcement
- Template context injection
- Model access control

#### API Routes (`api/stripe_routes.py`)
- Payment and subscription endpoints
- Webhook processing
- Subscription management UI routes

### Database Schema

#### Users Collection
```javascript
{
  firebase_uid: "string",
  email: "string",
  stripe_customer_id: "string",  // Created on first payment
  created_at: "timestamp",
  updated_at: "timestamp" 
}
```

#### User Subscriptions Collection  
```javascript
{
  firebase_uid: "string",
  stripe_customer_id: "string", 
  stripe_subscription_id: "string",
  plan_id: "premium_monthly",
  status: "active|canceled|past_due",
  current_period_start: "timestamp",
  current_period_end: "timestamp",
  cancel_at_period_end: "boolean",
  created_at: "timestamp",
  updated_at: "timestamp"
}
```

#### User Usage Collection
```javascript
{
  firebase_uid: "string",
  date: "string",  // YYYY-MM-DD format
  chat_messages: "number",
  searches: "number", 
  videos_generated: "number",
  created_at: "timestamp",
  updated_at: "timestamp"
}
```

## 💡 Feature Limits

### Free Plan
- ✅ 5 AI conversations per day
- ✅ 10 searches per day  
- ✅ 1 video generation per day
- ✅ Basic AI models (GPT-3.5, Gemini 1.0)
- ❌ Export conversations
- ❌ Advanced analytics
- ❌ Priority support

### Premium Plan ($5/month)
- ✅ **Unlimited** AI conversations
- ✅ **Unlimited** searches
- ✅ 10 video generations per day
- ✅ **All premium AI models** (GPT-4, Claude, etc.)
- ✅ Export conversation history
- ✅ Advanced analytics dashboard
- ✅ Custom AI personalities
- ✅ Priority support
- ✅ Early access to new features

## 🔧 Usage Examples

### Adding Premium Features

```python
from services.subscription_middleware import premium_required

@premium_required
def advanced_analytics():
    """Premium-only feature"""
    return generate_analytics()
```

### Feature Limiting

```python
from services.subscription_middleware import feature_limited

@feature_limited('chat_messages')
def chat_endpoint():
    """Limited feature with automatic usage tracking"""
    return process_chat()
```

### Manual Usage Checking

```python
from services.subscription_middleware import check_feature_limit

limit_result = check_feature_limit('chat_messages', current_usage=8, free_limit=5)
if not limit_result['allowed']:
    return {
        "error": "Upgrade required",
        "message": limit_result['message'],
        "upgrade_url": "/subscription"
    }
```

### Template Integration

```html
{% if subscription.is_premium %}
    <span class="badge bg-success">
        <i class="fas fa-crown"></i> Premium User
    </span>
    <p>Unlimited access to all features!</p>
{% else %}
    <div class="alert alert-info">
        <strong>Usage Today:</strong> 
        {{ subscription.usage.chat_messages or 0 }}/5 conversations
        <a href="/subscription" class="btn btn-primary btn-sm">
            Upgrade to Premium
        </a>
    </div>
{% endif %}
```

### Model Access Control

```python
from services.subscription_middleware import model_allowed, get_available_models

# Check if user can access a specific model
if model_allowed('gpt-4'):
    response = call_gpt4(prompt)
else:
    return {"error": "Premium subscription required for GPT-4"}

# Get list of available models for user
available_models = get_available_models()
```

## 🌐 API Endpoints

### Stripe API Routes (`/api/stripe/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/config` | GET | Get Stripe configuration for frontend |
| `/create-checkout-session` | POST | Create payment session |
| `/subscription/status` | GET | Get user subscription status |
| `/subscription/cancel` | POST | Cancel subscription at period end |
| `/subscription/reactivate` | POST | Reactivate cancelled subscription |
| `/webhook` | POST | Handle Stripe webhook events |
| `/usage/check/<feature>` | GET | Check feature usage limits |

### UI Routes

| Endpoint | Description |
|----------|-------------|
| `/subscription` | Subscription management page |
| `/subscription/success` | Post-payment success page |
| `/subscription/cancel` | Payment cancellation page |

## 🎨 Professional UI Features

### Subscription Management Page
- **Real-time subscription status** with billing information
- **Usage statistics dashboard** showing daily limits and usage
- **Professional pricing cards** with feature comparisons
- **One-click upgrade/downgrade** with Stripe Checkout
- **Subscription controls** (cancel, reactivate) 
- **Responsive design** that works on all devices

### Enhanced Authentication
- **Modern login/signup forms** with professional styling
- **Password strength indicators** and validation
- **Social login integration** (Google OAuth)
- **Loading states and animations** for better UX
- **Mobile-responsive design**

### Profile Integration
- **Subscription status badge** (Free/Premium)
- **"Manage Membership" button** prominently displayed
- **Usage insights** and upgrade prompts

## 🔒 Security Features

### Payment Security
- **PCI-compliant processing** through Stripe Checkout
- **Webhook signature verification** prevents unauthorized calls
- **No sensitive payment data** stored in your database
- **HTTPS enforcement** for all payment pages

### Data Security  
- **Firebase security rules** restrict access to user's own data
- **Authentication required** for all subscription operations
- **Webhook signature validation** with Stripe's signing secret
- **Secure session management** with existing Flask-Session setup

### Access Control
- **Subscription-based feature gating** with decorators
- **Usage limit enforcement** prevents abuse
- **Model access restrictions** based on subscription tier
- **Template-level access control** for UI features

## 🔄 Webhook Events

The system handles these Stripe webhook events:

### `checkout.session.completed`
- Creates new subscription record in Firestore
- Links Stripe customer to Firebase user
- Sends welcome email (optional)

### `customer.subscription.updated`  
- Updates subscription status and billing period
- Handles plan changes and renewals
- Updates cancellation status

### `customer.subscription.deleted`
- Marks subscription as canceled in Firestore
- Preserves user data for potential reactivation
- Sends cancellation confirmation (optional)

### `invoice.payment_failed`
- Logs payment failures for monitoring
- Can trigger dunning email sequences (optional)
- Updates subscription status if needed

## 📊 Analytics & Monitoring

### Usage Tracking
- **Daily usage counters** per user per feature
- **Subscription conversion metrics** 
- **Feature utilization analytics**
- **Churn and retention tracking**

### Monitoring Integration
- **Structured logging** for all subscription events
- **Error tracking** for payment failures
- **Performance monitoring** for API endpoints
- **Webhook delivery monitoring**

## 🚀 Production Deployment

### Environment Variables
```bash
# Production Stripe Keys
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PREMIUM_MONTHLY_PRICE_ID=price_...
```

### Deployment Checklist
- [ ] Set production Stripe API keys
- [ ] Configure production webhook endpoint
- [ ] Deploy Firestore rules and indexes  
- [ ] Test webhook delivery in Stripe dashboard
- [ ] Verify SSL certificate for webhook endpoint
- [ ] Set up monitoring and alerting
- [ ] Test complete payment flow end-to-end

### Scaling Considerations
- **Webhook retry handling** for failed deliveries
- **Rate limiting** on payment endpoints
- **Database indexing** for subscription queries
- **Caching** for subscription status checks
- **Background jobs** for usage aggregation

## 🐛 Troubleshooting

### Common Issues

#### "Stripe not configured" Error
**Cause**: Missing environment variables
**Solution**: Verify all STRIPE_* environment variables are set

#### Webhook Signature Verification Failed  
**Cause**: Incorrect webhook secret or malformed payload
**Solution**: Check webhook secret matches Stripe dashboard

#### Customer Creation Failed
**Cause**: User not authenticated or Firestore permissions issue
**Solution**: Ensure user is logged in and Firestore rules allow writes

#### Subscription Status Not Updating
**Cause**: Webhook not being received or processed correctly
**Solution**: Check webhook logs in Stripe dashboard and application logs

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Webhooks

Use Stripe CLI for local testing:
```bash
stripe listen --forward-to localhost:5000/api/stripe/webhook
```

## 📈 Future Enhancements

### Planned Features
- **Annual subscription discounts**
- **Team/organization plans** 
- **Usage-based pricing tiers**
- **Custom enterprise features**
- **Affiliate/referral program**
- **Free trial periods**
- **Promotional pricing**
- **Multiple payment methods**

### Integration Opportunities
- **Email marketing** (Mailchimp, SendGrid)
- **Customer support** (Zendesk, Intercom)
- **Analytics** (Mixpanel, Amplitude)
- **A/B testing** for pricing optimization

## 🤝 Support

For issues with the Stripe integration:

1. **Check the logs** for detailed error messages
2. **Verify environment variables** are set correctly  
3. **Test webhook delivery** in Stripe Dashboard
4. **Review Firestore security rules** and indexes
5. **Check Stripe API limits** and quotas

## 🎯 Success Metrics

Track these KPIs to measure success:

### Conversion Metrics
- **Sign-up to trial conversion rate**
- **Trial to paid conversion rate** 
- **Monthly recurring revenue (MRR)**
- **Annual recurring revenue (ARR)**

### User Engagement
- **Feature usage by subscription tier**
- **Daily/Monthly active users**
- **Session duration by user type**
- **Feature limit hit rate**

### Business Metrics
- **Customer lifetime value (CLV)**
- **Churn rate by cohort**
- **Net revenue retention**
- **Cost per acquisition (CPA)**

---

This implementation transforms Phoenix AI into a professional SaaS platform with enterprise-grade subscription management, ready for production deployment once Stripe credentials are configured. The system provides a solid foundation for scaling and monetizing your AI platform effectively.