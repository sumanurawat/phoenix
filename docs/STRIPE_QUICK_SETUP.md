# 🚀 Quick Setup Guide for Stripe Subscription Integration

## ✅ What's Been Implemented

Your Phoenix application now has a complete Stripe subscription system with:

- ✅ **Backend Services**: Complete Stripe integration with webhook handling
- ✅ **API Endpoints**: RESTful subscription management API
- ✅ **Frontend UI**: Subscription modal in user profile with plan selection
- ✅ **Access Control**: Decorators for feature-based access control
- ✅ **Data Models**: Subscription tiers and user subscription tracking
- ✅ **Error Handling**: Comprehensive error handling and logging

## 🔧 Setup Required

### 1. Stripe Account Setup (5 minutes)

1. **Create Products in Stripe Dashboard:**
   ```
   Product 1: Basic Plan
   - Price: $5.00 USD
   - Billing: Monthly recurring
   - Copy the Price ID (starts with price_)
   
   Product 2: Pro Plan  
   - Price: $20.00 USD
   - Billing: Monthly recurring
   - Copy the Price ID (starts with price_)
   ```

2. **Update Price IDs in Code:**
   ```python
   # In models/subscription.py, update these lines:
   "price_id": "price_your_actual_basic_price_id",    # Line ~75
   "price_id": "price_your_actual_pro_price_id",      # Line ~89
   
   # In api/subscription_routes.py, update these lines:
   valid_price_ids = [
       'price_your_actual_basic_price_id',   # Line ~45
       'price_your_actual_pro_price_id'      # Line ~46
   ]
   
   # In templates/profile.html, update these lines:
   onclick="subscribe('price_your_actual_basic_price_id')"  # Line ~129
   onclick="subscribe('price_your_actual_pro_price_id')"    # Line ~154
   ```

3. **Get API Keys from Stripe Dashboard:**
   - Secret Key (sk_test_...)
   - Publishable Key (pk_test_...)

### 2. Environment Variables (2 minutes)

Add to your `.env` file:
```bash
# Stripe Configuration (Test Mode)
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 3. Webhook Setup (3 minutes)

1. **In Stripe Dashboard > Webhooks:**
   - Add endpoint: `https://your-domain.com/api/subscription/webhook`
   - For local testing: Use ngrok or Stripe CLI
   
2. **Select these events:**
   - `checkout.session.completed`
   - `customer.subscription.updated` 
   - `customer.subscription.deleted`
   - `invoice.payment_failed`

3. **Copy webhook signing secret** to your `.env` file

## 🧪 Local Testing (1 minute)

```bash
# Install dependencies (already done)
pip install stripe==7.0.0

# Start your development server
./start_local.sh

# Visit http://localhost:5000/profile
# Click "Upgrade Plan" to test the subscription flow
```

### Test Credit Cards
- **Success**: `4242424242424242`
- **Decline**: `4000000000000002`
- **3D Secure**: `4000000000003220`

## 🚀 Deployment

### Staging Environment
```bash
# Push to dev branch to deploy to staging
git add .
git commit -m "feat: add Stripe subscription integration"
git push origin dev

# Update staging secrets in Google Cloud
gcloud secrets create phoenix-stripe-secret-key --data-file=<(echo "sk_test_...")
gcloud secrets create phoenix-stripe-webhook-secret --data-file=<(echo "whsec_...")
```

### Update Build Configuration
Add Stripe secrets to `cloudbuild-dev.yaml`:
```yaml
- '--update-secrets'
- 'STRIPE_SECRET_KEY=phoenix-stripe-secret-key:latest,STRIPE_WEBHOOK_SECRET=phoenix-stripe-webhook-secret:latest,...'
```

## 🎯 Features Available Immediately

### For Users:
- ✅ View current subscription status
- ✅ Subscribe to Basic ($5/month) or Pro ($20/month) plans
- ✅ Secure checkout via Stripe
- ✅ Automatic subscription management

### For Developers:
- ✅ Feature-based access control with decorators
- ✅ Usage limit enforcement
- ✅ Subscription status API
- ✅ Webhook event handling
- ✅ Comprehensive error handling

## 🛡️ Security Features

- ✅ **Authentication Required**: All subscription endpoints require login
- ✅ **Input Validation**: Price IDs validated against allowed values
- ✅ **Webhook Verification**: Stripe signatures verified
- ✅ **User Isolation**: Users can only access their own data
- ✅ **Test Mode**: Uses Stripe test keys for development

## 📱 Usage Examples

### Protect Features with Subscriptions
```python
from utils.subscription_decorators import subscription_required, feature_required

@subscription_required("basic")
def premium_feature():
    # Only Basic+ subscribers can access
    pass

@feature_required("API access") 
def api_endpoint():
    # Only Pro subscribers can access
    pass
```

### Check Subscription in Code
```python
from services.subscription_service import SubscriptionService

service = SubscriptionService()
subscription = service.get_subscription_status(user_id)

if subscription.is_premium():
    # User has paid subscription
    pass
```

## 🔄 Next Steps

### Immediate (Optional):
1. **Test the Integration**: Use test credit cards to verify flow
2. **Customize Plans**: Modify features/pricing in `models/subscription.py`
3. **Add Feature Gates**: Use decorators to protect existing features

### Future Enhancements:
1. **Email Notifications**: Integrate SendGrid for subscription emails
2. **Billing Portal**: Add customer self-service billing portal
3. **Usage Analytics**: Track feature usage by subscription tier
4. **Team Plans**: Add multi-user subscription support

## 🆘 Troubleshooting

### Common Issues:
1. **"No such price" error**: Update price IDs in code to match Stripe Dashboard
2. **Webhook not receiving**: Check endpoint URL and selected events
3. **Environment variables**: Ensure `.env` file is loaded correctly

### Testing Webhooks Locally:
```bash
# Install Stripe CLI
# Then forward webhooks to local server
stripe listen --forward-to localhost:5000/api/subscription/webhook
```

---

**🎉 Congratulations!** Your Phoenix application now has a complete subscription system. Users can subscribe to paid plans, and you can control feature access based on subscription tiers.

The implementation is production-ready and follows Stripe best practices for security and reliability.
