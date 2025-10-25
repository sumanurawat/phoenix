# Token Economy - Quick Reference Card

## 🚀 Quick Start Commands

```bash
# Local development
./start_local.sh

# Deploy Firestore rules
firebase deploy --only firestore:rules

# Set up production secrets
./setup_stripe_secrets.sh

# Deploy to production
git push origin main

# Check logs
gcloud run logs read phoenix-ai --region=us-central1 --limit=50

# Verify token balance
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/tokens/balance
```

---

## 📦 Token Packages

| Package | Tokens | Price | Price ID (Test) |
|---------|--------|-------|-----------------|
| Starter | 50 | $4.99 | price_1SMCieGgo4tk9CEiC4Cesg9H |
| Basic | 200 | $14.99 | price_1SMCkUGgo4tk9CEiOiBdCNXJ |
| Pro | 500 | $29.99 | price_1SMClkGgo4tk9CEiE6vIXCxP |
| Premium | 1000 | $49.99 | price_1SMCmMGgo4tk9CEisgHdgcth |

---

## 🔒 Security Features

- ✅ Webhook signature verification
- ✅ Idempotency (duplicate prevention)
- ✅ Rate limiting (5/hour, 20/day)
- ✅ Price validation
- ✅ Firestore security rules
- ✅ Atomic transactions
- ✅ Suspicious activity logging

---

## 📊 Key Metrics

### Success Indicators
```
✅ Webhook signature verified successfully!
✅ Successfully added X tokens
✅ Recorded transaction: purchase
```

### Warning Signs
```
⚠️ Duplicate event received
⚠️ Rate limit exceeded
❌ Package validation failed
❌ Failed to credit tokens
```

---

## 🐛 Troubleshooting

### Tokens not credited
```bash
# Check webhook logs
gcloud run logs read phoenix-ai | grep "checkout.session.completed"

# Verify webhook secret
gcloud secrets versions access latest --secret="STRIPE_WEBHOOK_SECRET_PROD"

# Check Firestore transaction
# Look for "Successfully added X tokens"
```

### Rate limit issues
```python
# Temporarily increase limits in token_security_service.py
MAX_PURCHASES_PER_HOUR = 10  # From 5
MAX_PURCHASES_PER_DAY = 50   # From 20
```

### Webhook not received
1. Check Stripe dashboard: https://dashboard.stripe.com/webhooks
2. Verify endpoint URL: https://phoenix-ai.app/api/stripe/webhook
3. Check webhook secret matches Secret Manager
4. Look for events in Stripe logs

---

## 📁 Key Files

```
services/
├── stripe_service.py          # Stripe integration + webhooks
├── token_service.py            # Token balance management
├── token_security_service.py   # Rate limiting, validation
└── transaction_service.py      # Transaction ledger

api/
├── token_routes.py             # /api/tokens/* endpoints
└── stripe_routes.py            # /api/stripe/webhook

firestore.rules                 # Security rules (CRITICAL)
setup_stripe_secrets.sh         # Secret management script
```

---

## 🔐 Secret Manager

```bash
# List secrets
gcloud secrets list --project=phoenix-project-386

# View secret value (NEVER log this!)
gcloud secrets versions access latest --secret="STRIPE_SECRET_KEY_PROD"

# Update secret
echo -n "new_value" | gcloud secrets versions add STRIPE_SECRET_KEY_PROD --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding STRIPE_SECRET_KEY_PROD \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 📈 Monitoring Queries

```bash
# Failed token credits (last hour)
gcloud logging read 'resource.type="cloud_run_revision"
  AND textPayload=~"Failed to credit.*tokens"
  AND timestamp>="2025-10-25T15:00:00Z"' \
  --limit=50 \
  --format=json

# Rate limit triggers (last day)
gcloud logging read 'resource.type="cloud_run_revision"
  AND textPayload=~"Rate limit exceeded"
  AND timestamp>="-1d"' \
  --limit=100

# Successful purchases (last hour)
gcloud logging read 'resource.type="cloud_run_revision"
  AND textPayload=~"Successfully added.*tokens"
  AND timestamp>="2025-10-25T15:00:00Z"' \
  --limit=50
```

---

## 🧪 Testing

### Local Test
```bash
# Start server
./start_local.sh

# Open buy tokens page
open http://localhost:8080/buy-tokens

# Use test card
# Card: 4242 4242 4242 4242
# Expiry: Any future date
# CVC: Any 3 digits
```

### Production Test
```bash
# Use REAL card (you'll be charged!)
# Or request test mode deployment first

# Verify in logs
gcloud run logs read phoenix-ai --region=us-central1 --limit=50
```

---

## 🔄 Rollback

```bash
# List revisions
gcloud run revisions list --service=phoenix-ai --region=us-central1

# Rollback to previous
gcloud run services update-traffic phoenix-ai \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1

# Revert Firestore rules
git checkout main~1 firestore.rules
firebase deploy --only firestore:rules
```

---

## 📞 Emergency Contacts

- **Stripe Support**: https://support.stripe.com/
- **Google Cloud Support**: https://cloud.google.com/support
- **Firebase Support**: https://firebase.google.com/support

---

## ✅ Deployment Checklist

```
[ ] Firestore rules deployed
[ ] Production secrets in Secret Manager
[ ] Cloud Build updated with secret injection
[ ] Code deployed to production
[ ] Stripe webhook configured
[ ] Smoke test passed
[ ] Monitoring alerts active
[ ] Team trained on troubleshooting
```

---

**Version**: 1.0  
**Last Updated**: October 25, 2025  
**Status**: Production Ready ✅
