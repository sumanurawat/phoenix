# 🎉 Token Purchase Fix - Complete Setup Guide

## 🔍 Problem Identified

**Issue:** Token purchase buttons showed "Unavailable" in production  
**Root Cause:** Missing Stripe Token Price IDs in Google Cloud Run environment variables  
**Date Fixed:** October 25, 2025

### Why It Happened

The token purchase feature checks if Stripe Price IDs exist in environment variables before showing the "Buy Now" button:

```python
# api/token_routes.py, line 96
'available': os.getenv(config['price_id_env']) is not None
```

If the environment variable is `None`, the button displays as "Unavailable".

**Where they existed:**
- ✅ Local `.env` file - Present
- ❌ Production (Cloud Run) - **MISSING**

---

## ✅ Solution Implemented

### 1. Created Automated Setup Script

**File:** `scripts/setup_token_price_ids.sh`

**What it does:**
- Reads Stripe Token Price IDs from local `.env` file
- Creates/updates 4 secrets in Google Secret Manager:
  - `STRIPE_TOKEN_STARTER_PRICE_ID` (50 tokens - $4.99)
  - `STRIPE_TOKEN_POPULAR_PRICE_ID` (110 tokens - $9.99)
  - `STRIPE_TOKEN_PRO_PRICE_ID` (250 tokens - $19.99)
  - `STRIPE_TOKEN_CREATOR_PRICE_ID` (700 tokens - $49.99)
- Grants Cloud Run service account access to secrets
- Validates all secrets before proceeding

**Usage:**
```bash
./scripts/setup_token_price_ids.sh
```

### 2. Updated Cloud Build Configurations

**Files Modified:**
- `cloudbuild.yaml` (production)
- `cloudbuild-dev.yaml` (development)

**Changes:** Added Token Price ID secrets to `--update-secrets` parameter:
```yaml
STRIPE_TOKEN_STARTER_PRICE_ID=STRIPE_TOKEN_STARTER_PRICE_ID:latest,
STRIPE_TOKEN_POPULAR_PRICE_ID=STRIPE_TOKEN_POPULAR_PRICE_ID:latest,
STRIPE_TOKEN_PRO_PRICE_ID=STRIPE_TOKEN_PRO_PRICE_ID:latest,
STRIPE_TOKEN_CREATOR_PRICE_ID=STRIPE_TOKEN_CREATOR_PRICE_ID:latest
```

### 3. Successfully Created Secrets

**Verification:**
```bash
gcloud secrets list --filter="name~STRIPE_TOKEN" --project=phoenix-project-386
```

**Output:**
- ✅ STRIPE_TOKEN_STARTER_PRICE_ID - Created
- ✅ STRIPE_TOKEN_POPULAR_PRICE_ID - Created
- ✅ STRIPE_TOKEN_PRO_PRICE_ID - Created
- ✅ STRIPE_TOKEN_CREATOR_PRICE_ID - Created

---

## 🚀 Deployment Instructions

### Step 1: Deploy to Production

```bash
# From project root
gcloud builds submit --config cloudbuild.yaml
```

**Expected behavior:**
- Builds Docker image (~2-3 minutes)
- Deploys to Cloud Run (~1-2 minutes)
- Injects secrets as environment variables
- Token purchase buttons become active

### Step 2: Verify Deployment

1. **Check Cloud Run service:**
   ```bash
   gcloud run services describe phoenix --region=us-central1 --format="value(status.url)"
   ```

2. **Visit buy tokens page:**
   ```
   https://phoenix-234619602247.us-central1.run.app/buy-tokens
   ```

3. **Verify buttons show "Buy Now" instead of "Unavailable"**

### Step 3: Test Token Purchase Flow

1. Navigate to `/buy-tokens`
2. Click "Buy Now" on any package
3. Verify redirect to Stripe Checkout
4. Complete test purchase (use test card if in test mode)
5. Verify redirect to success page
6. Check Firestore for token balance update

---

## 📦 What Gets Deployed

### Environment Variables Available in Production

After deployment, the Cloud Run service will have:

```bash
# Existing secrets (already configured)
GEMINI_API_KEY=*****
SECRET_KEY=*****
STRIPE_SECRET_KEY=*****
STRIPE_WEBHOOK_SECRET=*****
STRIPE_PUBLISHABLE_KEY=*****

# NEW: Token Price IDs (now configured)
STRIPE_TOKEN_STARTER_PRICE_ID=price_1SMCieGgo4tk9CEiC4Cesg9H
STRIPE_TOKEN_POPULAR_PRICE_ID=price_1SMCkBGgo4tk9CEiOXcl4Qgl
STRIPE_TOKEN_PRO_PRICE_ID=price_1SMClkGgo4tk9CEiE6vIXCxP
STRIPE_TOKEN_CREATOR_PRICE_ID=price_1SMCnBGgo4tk9CEiUR9MYPLK
```

---

## 🔐 Security Features

### Why Secrets Instead of Environment Variables?

1. **Encrypted at rest** - Secret Manager encrypts all secrets
2. **Audit logging** - Track who accessed secrets and when
3. **Version control** - Roll back to previous secret versions
4. **IAM-based access** - Only authorized service accounts can read
5. **Never in logs** - Secrets don't appear in Cloud Build logs

### IAM Permissions

**Service Account:** `phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com`

**Granted Roles:**
- `roles/secretmanager.secretAccessor` on all 4 Token Price ID secrets

**Verification:**
```bash
gcloud secrets get-iam-policy STRIPE_TOKEN_STARTER_PRICE_ID
```

---

## 🧪 Testing Checklist

### Before Deployment
- [x] Secrets created in Secret Manager
- [x] IAM permissions granted to service account
- [x] `cloudbuild.yaml` updated with secret references
- [x] `cloudbuild-dev.yaml` updated for consistency

### After Deployment
- [ ] Production URL loads without errors
- [ ] `/buy-tokens` page renders correctly
- [ ] All 4 token packages show "Buy Now" buttons
- [ ] Clicking "Buy Now" redirects to Stripe Checkout
- [ ] Successful purchase adds tokens to Firestore
- [ ] Token balance displays correctly

---

## 📊 Token Package Configuration

| Package | Tokens | Bonus | Price | Price ID |
|---------|--------|-------|-------|----------|
| Starter | 50 | 0 | $4.99 | `STRIPE_TOKEN_STARTER_PRICE_ID` |
| Popular | 110 | 10 | $9.99 | `STRIPE_TOKEN_POPULAR_PRICE_ID` |
| Pro | 250 | 50 | $19.99 | `STRIPE_TOKEN_PRO_PRICE_ID` |
| Creator | 700 | 200 | $49.99 | `STRIPE_TOKEN_CREATOR_PRICE_ID` |

---

## 🐛 Troubleshooting

### Problem: Buttons still show "Unavailable" after deployment

**Check:**
1. Verify secrets exist:
   ```bash
   gcloud secrets list --filter="name~STRIPE_TOKEN"
   ```

2. Check Cloud Run environment:
   ```bash
   gcloud run services describe phoenix --region=us-central1 --format="yaml(spec.template.spec.containers[0].env)"
   ```

3. Check production logs:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=phoenix" --limit=50 --format=json
   ```

### Problem: "Secret not found" error during deployment

**Solution:**
1. Re-run setup script:
   ```bash
   ./scripts/setup_token_price_ids.sh
   ```

2. Verify secret names match exactly in `cloudbuild.yaml`

### Problem: "Permission denied" accessing secrets

**Solution:**
Grant permissions to service account:
```bash
for SECRET in STRIPE_TOKEN_STARTER_PRICE_ID STRIPE_TOKEN_POPULAR_PRICE_ID STRIPE_TOKEN_PRO_PRICE_ID STRIPE_TOKEN_CREATOR_PRICE_ID; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## 🔄 Future Updates

### To Update Price IDs (e.g., changing prices in Stripe)

1. **Update local `.env` file** with new Price IDs

2. **Re-run setup script:**
   ```bash
   ./scripts/setup_token_price_ids.sh
   ```
   (Script automatically creates new versions of existing secrets)

3. **Redeploy to production:**
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

### To Add New Token Packages

1. **Create product in Stripe Dashboard**
2. **Copy new Price ID**
3. **Add to `config/settings.py`:**
   ```python
   STRIPE_TOKEN_ENTERPRISE_PRICE_ID = os.getenv("STRIPE_TOKEN_ENTERPRISE_PRICE_ID")
   ```

4. **Add to `api/token_routes.py`:**
   ```python
   'enterprise': {
       'name': 'Enterprise Pack',
       'tokens': 2000,
       'price': 99.99,
       'bonus': 500,
       'price_id_env': 'STRIPE_TOKEN_ENTERPRISE_PRICE_ID',
       'description': 'For enterprises - 25% bonus!'
   }
   ```

5. **Update setup script** to include new secret
6. **Run setup script and redeploy**

---

## 📝 Files Modified

### Created
- `scripts/setup_token_price_ids.sh` - Automated secret setup script

### Modified
- `cloudbuild.yaml` - Added Token Price ID secrets to production deployment
- `cloudbuild-dev.yaml` - Added Token Price ID secrets to dev deployment

### No Changes Required
- `api/token_routes.py` - Already checks for Price IDs correctly
- `templates/buy_tokens.html` - Already handles unavailable state
- `config/settings.py` - Already defines Price ID environment variables

---

## ✅ Completion Status

**All Steps Completed:**
1. ✅ Created automated setup script
2. ✅ Updated production Cloud Build config
3. ✅ Updated dev Cloud Build config
4. ✅ Created secrets in Google Secret Manager
5. ✅ Granted IAM permissions to service account
6. ⏳ **READY TO DEPLOY** - Run `gcloud builds submit --config cloudbuild.yaml`

---

## 🎯 Expected Outcome

After deploying to production:

**Before:**
```
[Starter Pack]
[Buy Now] ← Shows "Unavailable" (grayed out)
```

**After:**
```
[Starter Pack]
[Buy Now] ← Shows "Buy Now" (active, clickable)
```

**User Flow:**
1. User clicks "Buy Now"
2. Redirects to Stripe Checkout
3. User completes payment
4. Webhook triggers token credit
5. User sees success page with new balance

---

## 📞 Support

**If issues persist after deployment:**

1. Check production logs:
   ```bash
   ./scripts/fetch_logs.py --hours 1 --severity ERROR
   ```

2. Verify Stripe webhook endpoint:
   - URL: `https://phoenix-234619602247.us-central1.run.app/api/stripe/webhook`
   - Events: `checkout.session.completed`

3. Test API endpoint directly:
   ```bash
   curl https://phoenix-234619602247.us-central1.run.app/api/tokens/packages
   ```

---

**Date:** October 25, 2025  
**Author:** GitHub Copilot  
**Status:** ✅ Ready for Production Deployment
