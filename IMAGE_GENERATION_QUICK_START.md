# 🎨 Image Generation - Quick Reference

## 🚀 Start Testing NOW

```bash
# 1. Run backend test (no Flask needed)
python test_image_generation.py quick

# 2. Start Flask app
./start_local.sh

# 3. Open browser
# http://localhost:8080/image-generator
```

---

## 📝 What Was Built

✅ **Service:** `services/image_generation_service.py` (Imagen 3 wrapper)  
✅ **API:** `api/image_routes.py` (6 endpoints with auth)  
✅ **Frontend:** `templates/image_generator.html` + `static/js/image_generator.js`  
✅ **Tests:** `test_image_generation.py` (5 test suites)  

---

## ⚙️ Configuration (Hardcoded)

| Setting | Value | Why |
|---------|-------|-----|
| Images per request | **1** | Simple, fast |
| Aspect ratio | **9:16** (Portrait) | Mobile-first, Instagram-ready |
| Safety filter | **block_few** (Lowest) | Maximum creative freedom |
| Person generation | **allow_all** | No restrictions |
| Model | **imagen-3.0-generate-001** | Google Vertex AI |

---

## 🔗 Key Endpoints

| URL | Method | Purpose |
|-----|--------|---------|
| `/image-generator` | GET | Frontend UI (login required) |
| `/api/image/generate` | POST | Generate image (auth + CSRF) |
| `/api/image/history` | GET | Get user's images (auth) |
| `/api/image/health` | GET | Service status (public) |

---

## 📊 Expected Performance

- **Generation:** 3-5 seconds
- **Upload:** < 1 second
- **Total:** 4-6 seconds per image
- **Cost:** ~$0.008 per image

---

## 🧪 Quick Test Commands

```bash
# Test backend only (fast)
python test_image_generation.py quick

# Test all (comprehensive)
python test_image_generation.py

# Test validation only
python test_image_generation.py validation
```

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Failed to initialize Vertex AI" | Check `firebase-credentials.json` exists |
| "Module 'vertexai' not found" | Run `pip install -r requirements.txt` |
| "GCS bucket not found" | Create bucket: `gsutil mb gs://phoenix-images` |
| "CSRF token missing" | Clear cookies, re-login |

---

## 📁 Files Changed

**New:**
- `services/image_generation_service.py`
- `api/image_routes.py`
- `templates/image_generator.html`
- `static/js/image_generator.js`
- `test_image_generation.py`

**Modified:**
- `config/settings.py` (added IMAGE_* constants)
- `app.py` (registered image_bp, added route)
- `services/website_stats_service.py` (added increment_images_generated)

---

## 🎯 Next Steps

1. ✅ Run `python test_image_generation.py quick` 
2. ✅ Start app with `./start_local.sh`
3. ✅ Visit http://localhost:8080/image-generator
4. ✅ Generate your first image!
5. 🚀 Deploy to production when ready

---

## 📚 Full Documentation

- **Testing Guide:** `IMAGE_GENERATION_TESTING_GUIDE.md`
- **Implementation:** `IMAGE_GENERATION_IMPLEMENTATION_SUMMARY.md`
- **Error Handling & Credits:** `IMAGE_GENERATION_ERROR_HANDLING.md` ⭐ NEW
- **API Docs:** See inline comments in `api/image_routes.py`

---

## ⚠️ Important: Credit Deduction Logic

**Credits are ONLY deducted on successful generations!**

All responses include `should_deduct_credits` field:
- ✅ `true` - Image generated successfully, deduct credit
- ❌ `false` - Generation failed (safety/policy/error), DON'T deduct

See `IMAGE_GENERATION_ERROR_HANDLING.md` for complete details.

---

**Status:** ✅ Ready for testing!  
**Time to first image:** < 2 minutes 🚀
