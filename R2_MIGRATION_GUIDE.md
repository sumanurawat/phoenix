# Cloudflare R2 Migration Guide

## 🎯 Why We Switched from GCS to R2

### The Video Economics Problem

**For Images (Current State):**
- GCS egress cost: ~$240 for 1M views (manageable)
- Not a significant cost concern

**For Video (Future State):**
- Average 8s video: ~10MB
- GCS egress for 1M views: **$1,200 per video**
- 10 viral videos: **$12,000 in egress fees**
- Platform success = unsustainable costs

**With Cloudflare R2:**
- Egress cost: **$0** (zero)
- Same 10 viral videos: **$0 in egress fees**
- Platform scales without bankruptcy risk

### Strategic Decision

This isn't premature optimization - it's **foundational architecture** for our video platform future. By switching now while on images, we:
- ✅ Avoid painful migration under cost pressure later
- ✅ Keep the simple in-service approach (no microservice complexity)
- ✅ Future-proof for video launch
- ✅ Save potentially tens of thousands in egress costs

---

## 📦 What Changed

### Files Modified

1. **`config/settings.py`**
   - Added R2 credentials configuration
   - Kept GCS config for video generation (Reel Maker still uses GCS)

2. **`services/image_generation_service.py`**
   - Replaced Google Cloud Storage client with boto3 (S3-compatible)
   - Changed `_save_to_gcs()` → `_save_to_r2()`
   - Updated initialization to use R2 client
   - Kept same interfaces (backwards compatible)

3. **`requirements.txt`**
   - Added `boto3==1.35.0` for S3-compatible R2 access

### What Stayed the Same

- ✅ All API endpoints unchanged
- ✅ Database schema unchanged (still uses `gcs_uri` field name)
- ✅ Error handling unchanged
- ✅ Logging unchanged
- ✅ Frontend unchanged
- ✅ Video generation still uses GCS (unaffected)

---

## 🚀 Deployment Steps

### Step 1: Install boto3

```bash
# Activate virtual environment
source venv/bin/activate

# Install new dependency
pip install boto3==1.35.0

# Or install all requirements
pip install -r requirements.txt
```

### Step 2: Set Environment Variables

Add these to your `.env` file:

```bash
# Cloudflare R2 Configuration
R2_ACCESS_KEY_ID="a42807e1a99ef539b0c6c9762ac63732"
R2_SECRET_ACCESS_KEY="711a6461c2626544ecc72a79efecf4d7b48a00d64f12a6a0c800e08c85890cce"
R2_ENDPOINT_URL="https://c2f4c910044ec85be536a49565a99b27.r2.cloudflarestorage.com"
R2_BUCKET_NAME="ai-image-posts-prod"
R2_PUBLIC_URL="https://pub-1a71386e411e444e9db8b16217b43eca.r2.dev"
```

### Step 3: Test Locally

```bash
# Run image generation test
python test_image_generation.py quick

# Expected: Image uploads to R2 and returns public URL
# URL should start with: https://pub-1a71386e411e444e9db8b16217b43eca.r2.dev/
```

### Step 4: Verify R2 Upload

1. Check Cloudflare R2 dashboard
2. Navigate to `ai-image-posts-prod` bucket
3. Verify `generated-images/` folder contains new uploads
4. Test public URL in browser

### Step 5: Deploy to Production

```bash
# For Cloud Run, add secrets via gcloud
gcloud run services update phoenix-prod \
  --update-secrets=R2_ACCESS_KEY_ID=r2-access-key:latest \
  --update-secrets=R2_SECRET_ACCESS_KEY=r2-secret-key:latest \
  --update-env-vars R2_ENDPOINT_URL="https://c2f4c910044ec85be536a49565a99b27.r2.cloudflarestorage.com" \
  --update-env-vars R2_BUCKET_NAME="ai-image-posts-prod" \
  --update-env-vars R2_PUBLIC_URL="https://pub-1a71386e411e444e9db8b16217b43eca.r2.dev"

# Or use your existing deployment script
./deploy.sh
```

---

## 🔍 Verification Checklist

### Local Testing
- [ ] `pip install boto3` successful
- [ ] `.env` contains all R2 credentials
- [ ] `python test_image_generation.py quick` passes
- [ ] Generated image URL starts with R2_PUBLIC_URL
- [ ] Image accessible via public URL in browser
- [ ] Logs show "Initialized Cloudflare R2 client"

### Production Testing
- [ ] Environment variables set in Cloud Run
- [ ] Application starts without errors
- [ ] First image generation succeeds
- [ ] Image visible at public R2 URL
- [ ] No GCS upload errors in logs
- [ ] Firestore document contains R2 URL

---

## 🐛 Troubleshooting

### "boto3 module not found"
```bash
# Solution: Install boto3
pip install boto3==1.35.0
```

### "Failed to initialize R2 client"
**Cause:** Missing or incorrect R2 credentials

**Check:**
```bash
# Verify env vars are set
echo $R2_ACCESS_KEY_ID
echo $R2_ENDPOINT_URL

# Check .env file
cat .env | grep R2_
```

### "403 Forbidden" on R2 upload
**Cause:** Incorrect access key or secret

**Solution:**
- Verify credentials in Cloudflare dashboard
- Ensure bucket permissions allow write
- Check endpoint URL matches your R2 account

### "Image URL not accessible"
**Cause:** Bucket not set to public or wrong public URL

**Check:**
1. Cloudflare R2 Dashboard → Bucket Settings
2. Verify "Public Access" is enabled
3. Confirm R2_PUBLIC_URL matches dashboard

### "NoSuchBucket" error
**Cause:** Bucket name incorrect or doesn't exist

**Solution:**
- Verify `R2_BUCKET_NAME="ai-image-posts-prod"` in env
- Check bucket exists in Cloudflare dashboard
- Ensure no typos in bucket name

---

## 📊 Cost Comparison

### Image Generation (Current)
| Metric | GCS | R2 |
|--------|-----|-----|
| Storage (per GB/month) | $0.020 | $0.015 |
| Egress (per GB) | $0.12 | **$0.00** |
| 1M image views (2TB) | $240 | **$0** |

### Video Platform (Future)
| Metric | GCS | R2 |
|--------|-----|-----|
| Storage (per GB/month) | $0.020 | $0.015 |
| Egress (per GB) | $0.12 | **$0.00** |
| 1M video views (10TB) | **$1,200** | **$0** |
| 10 viral videos (100TB) | **$12,000** | **$0** |

**Annual Savings Projection:**
- 100 videos @ 1M views each: **$120,000 saved**

---

## 🔄 Rollback Plan (If Needed)

If R2 integration has issues, you can quickly rollback:

### Step 1: Revert Code Changes

```bash
# Checkout previous commit
git checkout HEAD~1 services/image_generation_service.py
git checkout HEAD~1 config/settings.py
```

### Step 2: Remove boto3 (Optional)

```bash
pip uninstall boto3 -y
```

### Step 3: Restart Application

```bash
./start_local.sh
```

All new images will go back to GCS. Existing R2 images will still be accessible (URLs don't change).

---

## 📈 Migration of Existing Images (Optional)

If you want to migrate existing GCS images to R2:

### Option 1: Leave Them on GCS
- **Pros:** No work, URLs stay valid
- **Cons:** Mixed storage, still pay GCS egress for old images
- **Recommendation:** Best for MVP/early stage

### Option 2: Batch Migration Script
```python
# migrate_gcs_to_r2.py (not implemented yet)
# This would:
# 1. List all images in GCS
# 2. Download each image
# 3. Upload to R2
# 4. Update Firestore URLs
# 5. Delete from GCS (optional)
```

**When to do this:** Only if GCS costs become significant (>$100/month)

---

## 🎯 Success Metrics

After deployment, monitor:
1. **Upload Success Rate:** Should stay >99%
2. **Image Load Time:** Should be similar or faster than GCS
3. **Error Rate:** Should not increase
4. **Cost:** Track R2 storage costs (should be minimal)

### Monitoring Commands

```bash
# Check recent image generations
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.message:\"Image saved to R2\"" --limit 10

# Check for R2 errors
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR AND jsonPayload.message:R2" --limit 10
```

---

## ✅ Post-Migration Checklist

- [ ] All new images upload to R2 successfully
- [ ] Public URLs work in browser
- [ ] No increase in error rates
- [ ] Logs show R2 uploads, not GCS
- [ ] Firestore contains R2 URLs (https://pub-...)
- [ ] Application performance unchanged
- [ ] Cost tracking configured for R2

---

## 🔮 Future: Video Integration

When we add video:

1. **Same R2 bucket** - Use `ai-image-posts-prod` for videos too
2. **Same code pattern** - Copy image upload logic for videos
3. **Folder structure:**
   ```
   ai-image-posts-prod/
   ├── generated-images/
   │   └── {user_id}/{timestamp}_{id}.png
   └── generated-videos/
       └── {user_id}/{timestamp}_{id}.mp4
   ```
4. **$0 egress** - Videos benefit from same cost savings

---

## 📚 Key Takeaways

✅ **Strategic decision** - Not premature optimization  
✅ **Simple implementation** - No microservice complexity  
✅ **Future-proof** - Ready for video platform  
✅ **Backwards compatible** - No breaking changes  
✅ **Cost-effective** - $0 egress saves thousands  
✅ **Production-ready** - Full logging and error handling  

**Status:** ✅ Ready to deploy!
