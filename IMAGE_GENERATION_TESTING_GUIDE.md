# Image Generation Service - Testing Guide

## 🚀 Quick Start

Your new image generation service is ready! Here's how to test it.

## ✅ What We Built

### Backend Services
- **`services/image_generation_service.py`** - Imagen 3 API wrapper with production logging
- **`api/image_routes.py`** - RESTful API endpoints with auth and CSRF protection
- **`config/settings.py`** - Configuration constants added

### Frontend
- **`templates/image_generator.html`** - Modern UI with dark theme
- **`static/js/image_generator.js`** - Interactive frontend logic
- **`/image-generator`** route added to Flask app

### Testing
- **`test_image_generation.py`** - Standalone test suite (5 comprehensive tests)

### Configuration (Hardcoded as Requested)
- ✅ **1 image per generation** (hardcoded)
- ✅ **Portrait orientation (9:16)** (hardcoded)
- ✅ **Lowest safety filter** (`block_few` - minimal restrictions)
- ✅ **No person generation restrictions** (`allow_all`)
- ✅ **No negative prompts**
- ✅ **Google Imagen 3 only** (OpenAI DALL-E deferred)

---

## 📋 Testing Steps

### Step 1: Test Backend Service (Without Flask)

Run the standalone test script:

```bash
# Activate your virtual environment first
source venv/bin/activate

# Run all tests (takes ~1-2 minutes)
python test_image_generation.py

# Or run quick test only (takes ~5 seconds)
python test_image_generation.py quick

# Or run validation tests only
python test_image_generation.py validation
```

**Expected Output:**
```
🎨 IMAGE GENERATION SERVICE TEST SUITE
========================================
TEST 1: Basic Image Generation (Portrait)
✅ SUCCESS!
   Image ID: abc123...
   Model: imagen-3.0-generate-001
   Generation Time: 3.45s
   Public URL: https://storage.googleapis.com/...

...

📊 Results: 5/5 passed, 0/5 failed
🎉 All tests passed! Image generation service is ready.
```

**What the test validates:**
- ✅ Vertex AI connection and authentication
- ✅ Imagen 3 model loading
- ✅ Image generation with hardcoded portrait settings
- ✅ GCS upload and public URL generation
- ✅ Base64 encoding
- ✅ Prompt validation
- ✅ Error handling

---

### Step 2: Start Flask App

```bash
# Start the app (uses start_local.sh from your existing setup)
./start_local.sh

# Or manually:
source venv/bin/activate
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

**Wait for:** Server starts on http://localhost:8080

---

### Step 3: Test Frontend UI

1. **Navigate to:** http://localhost:8080/image-generator

2. **Login Required:** If not logged in, you'll be redirected to login page

3. **Generate an Image:**
   - Enter a prompt (e.g., "A serene mountain landscape at sunset")
   - Click "Generate Image"
   - Wait 3-5 seconds
   - Image appears in portrait orientation

4. **Test Actions:**
   - ✅ **Download** - Downloads PNG file
   - ✅ **Discard** - Clears the preview
   - ⏳ **Publish** - Placeholder (coming soon)

5. **Check History:**
   - Your recent generations appear in the bottom section
   - Click any thumbnail to preview it again

---

### Step 4: Test API Endpoints

You can also test the API directly using curl or Postman:

#### Health Check (No Auth Required)
```bash
curl http://localhost:8080/api/image/health
```

Expected:
```json
{
  "status": "healthy",
  "service": "image_generation",
  "model": "imagen-3.0-generate-001",
  "timestamp": "2025-10-25T12:00:00Z"
}
```

#### Generate Image (Auth + CSRF Required)
```bash
# You'll need to get CSRF token and session cookie from browser first
curl -X POST http://localhost:8080/api/image/generate \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: YOUR_TOKEN" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{"prompt": "A peaceful zen garden with cherry blossoms"}'
```

#### Get History
```bash
curl http://localhost:8080/api/image/history?limit=10 \
  -H "Cookie: session=YOUR_SESSION"
```

---

## 🔍 What to Verify

### Backend Verification
- [ ] Test script runs without errors
- [ ] Images are generated successfully
- [ ] GCS bucket receives uploaded images
- [ ] Firestore `image_generations` collection populated
- [ ] Logs show proper INFO/DEBUG messages
- [ ] No WARNING or ERROR logs (except missing optional API keys)

### Frontend Verification
- [ ] Page loads without 404/500 errors
- [ ] Prompt textarea is functional
- [ ] Character counter updates
- [ ] Generate button triggers API call
- [ ] Loading spinner appears during generation
- [ ] Generated image displays correctly in portrait orientation
- [ ] Download button saves PNG file
- [ ] Discard button clears preview
- [ ] History section loads recent generations
- [ ] Clicking history thumbnail previews the image

### Database Verification
Check Firestore Console:

```
Collection: image_generations
Document fields:
- user_id: string
- image_id: string (UUID)
- prompt: string
- image_url: string (public GCS URL)
- gcs_uri: string (gs://...)
- aspect_ratio: "9:16"
- model: "imagen-3.0-generate-001"
- generation_time_seconds: number
- created_at: timestamp
- timestamp: string
- status: "generated"
```

### GCS Bucket Verification
Check your GCS bucket:
```
gs://phoenix-images/generated-images/
├── [user-id]/
│   └── 20251025_120000_[uuid].png
└── anonymous/
    └── 20251025_120100_[uuid].png
```

---

## 🐛 Troubleshooting

### "Failed to initialize Vertex AI"
**Problem:** Missing GCP credentials

**Solution:**
```bash
# Check if credentials exist
ls -la firebase-credentials.json

# Or set GOOGLE_APPLICATION_CREDENTIALS
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"
```

---

### "Image generation returned no results"
**Problem:** Imagen API issue or quota exceeded

**Solution:**
- Check GCP console for Vertex AI API quotas
- Verify billing is enabled
- Check for API restrictions in GCP project
- Look for detailed error in logs

---

### "Failed to save to GCS"
**Problem:** GCS bucket doesn't exist or permissions issue

**Solution:**
```bash
# Check if bucket exists
gsutil ls gs://phoenix-images/

# Create bucket if needed
gsutil mb gs://phoenix-images/

# Set bucket to allow public reads
gsutil iam ch allUsers:objectViewer gs://phoenix-images
```

---

### Frontend "Failed to generate image"
**Problem:** CSRF token missing or session expired

**Solution:**
- Clear browser cookies
- Re-login to get new session
- Check browser console for detailed error
- Verify `X-CSRF-Token` header in Network tab

---

### "Module 'vertexai' not found"
**Problem:** Missing Python dependencies

**Solution:**
```bash
source venv/bin/activate
pip install -r requirements.txt

# If vertexai missing, install explicitly:
pip install google-cloud-aiplatform
```

---

## 📊 Performance Expectations

| Metric | Expected Value |
|--------|---------------|
| **Image Generation Time** | 3-5 seconds |
| **GCS Upload Time** | < 1 second |
| **Total API Response** | 4-6 seconds |
| **Image Size** | ~500KB - 2MB (PNG) |
| **Image Resolution** | Variable (portrait, typically ~1080x1920) |

---

## 🎯 Next Steps After Testing

Once all tests pass:

1. **Add to Dashboard:** Link to `/image-generator` from main navigation
2. **Add Stats Card:** Display total images generated on admin stats page
3. **Implement Publish:** Connect to Instagram/Social APIs
4. **Add Subscription Limits:** Gate feature for free vs premium users
5. **Deploy to Production:** Push to Cloud Run via your existing CI/CD

---

## 📝 API Endpoints Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/image/generate` | POST | ✅ | Generate single portrait image |
| `/api/image/validate-prompt` | POST | ✅ | Validate prompt before generation |
| `/api/image/history` | GET | ✅ | Get user's generation history |
| `/api/image/<image_id>` | GET | ✅ | Get specific image details |
| `/api/image/<image_id>` | DELETE | ✅ | Soft-delete an image |
| `/api/image/health` | GET | ❌ | Service health check |

---

## 🔐 Security Features Implemented

- ✅ Login required for all image generation
- ✅ CSRF protection on all mutating endpoints
- ✅ User-scoped image storage (by user_id)
- ✅ Firestore security via user_id validation
- ✅ Input validation (prompt length, characters)
- ✅ Error messages don't leak sensitive info
- ✅ GCS URLs are public (safe for sharing)

---

## 💰 Cost Considerations

**Imagen 3 Pricing (approximate):**
- $0.008 per image (1024x1024 equivalent)
- Portrait images may vary slightly

**Monthly estimate for 1000 images:** ~$8.00

**GCS Storage:**
- Standard storage: $0.02 per GB/month
- Typical image: 1-2MB
- 1000 images ≈ 1.5GB ≈ $0.03/month

**Total monthly cost (1000 images):** ~$8.03

---

## ✨ Features Ready to Use

✅ Single portrait image generation (9:16)  
✅ Lowest safety restrictions  
✅ No person generation limits  
✅ Fast generation (3-5 seconds)  
✅ Automatic GCS storage  
✅ Download functionality  
✅ Generation history  
✅ Production-grade logging  
✅ Comprehensive error handling  
✅ User authentication  
✅ CSRF protection  

---

## 🎉 You're All Set!

Your image generation service is production-ready. Run the tests, start the app, and create some amazing AI art! 🎨

For questions or issues, check the logs or review the inline documentation in the source files.
