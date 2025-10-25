# Image Generation - Error Handling & Credit Deduction Guide

## 🎯 Critical Concept: Only Successful Generations Deduct Credits

This implementation ensures that **credits are ONLY deducted when an image is actually generated**. Failed generations (due to safety filters, policy violations, or errors) will NOT deduct credits.

---

## 📊 Response Structure

### Successful Generation
```json
{
  "success": true,
  "should_deduct_credits": true,  // ✅ DEDUCT CREDITS
  "image": {
    "image_id": "abc-123",
    "image_url": "https://...",
    "gcs_uri": "gs://...",
    "prompt": "...",
    "generation_time_seconds": 3.45,
    "timestamp": "2025-10-25T12:00:00Z"
  }
}
```

### Failed Generation (Safety Filter)
```json
{
  "success": false,
  "should_deduct_credits": false,  // ❌ DO NOT DEDUCT CREDITS
  "error": "Image generation was blocked...",
  "error_type": "safety_filter",
  "message": "Your prompt was blocked by content safety filters..."
}
```

### Failed Generation (Policy Violation)
```json
{
  "success": false,
  "should_deduct_credits": false,  // ❌ DO NOT DEDUCT CREDITS
  "error": "Image generation blocked due to content policy...",
  "error_type": "policy_violation",
  "message": "Your prompt violates content policies..."
}
```

### Failed Generation (Validation Error)
```json
{
  "success": false,
  "should_deduct_credits": false,  // ❌ DO NOT DEDUCT CREDITS
  "error": "Prompt cannot be empty",
  "error_type": "validation_error"
}
```

### Failed Generation (Unexpected Error)
```json
{
  "success": false,
  "should_deduct_credits": false,  // ❌ DO NOT DEDUCT CREDITS
  "error": "Image generation failed: ...",
  "error_type": "unexpected_error"
}
```

---

## 🚨 Exception Types

### 1. `SafetyFilterError`
**When:** Google's safety filters block the generation
**Cause:** Prompt contains potentially sensitive content
**Credits:** ❌ DO NOT DEDUCT
**User Message:** "Your prompt was blocked by content safety filters. Please try a different prompt."

**Example Triggers:**
- Violent content
- Explicit content (even with lowest safety)
- Harmful stereotypes
- Dangerous activities

### 2. `PolicyViolationError`
**When:** Google's content policies are violated
**Cause:** Prompt violates Google's usage policies
**Credits:** ❌ DO NOT DEDUCT
**User Message:** "Your prompt violates content policies. Please modify your prompt and try again."

**Example Triggers:**
- Copyright violations (famous people, brands)
- Illegal activities
- Misinformation
- Terms of service violations

### 3. `ValueError`
**When:** Invalid input parameters
**Cause:** Empty prompt, too short/long, etc.
**Credits:** ❌ DO NOT DEDUCT
**User Message:** Specific validation error message

**Example Triggers:**
- Empty or whitespace-only prompt
- Prompt < 3 characters
- Prompt > 5000 characters

### 4. `ImageGenerationError` (Base)
**When:** General generation failures
**Cause:** Various technical issues
**Credits:** ❌ DO NOT DEDUCT
**User Message:** Generic error message

### 5. `RuntimeError`
**When:** Unexpected API failures
**Cause:** Network issues, API timeouts, etc.
**Credits:** ❌ DO NOT DEDUCT
**User Message:** "Image generation failed: [details]"

---

## 🔍 Detection Logic

### In Service Layer (`image_generation_service.py`)

```python
# Check if API returned images
if not response.images or len(response.images) == 0:
    # This usually means safety/policy block
    raise SafetyFilterError("Image generation was blocked...")

# Check error messages for keywords
error_msg = str(e).lower()
if any(keyword in error_msg for keyword in ['safety', 'policy', 'blocked', 'inappropriate', 'violation']):
    raise PolicyViolationError(f"Image generation blocked due to content policy: {str(e)}")
```

### In API Layer (`api/image_routes.py`)

```python
generation_successful = False

try:
    result = service.generate_image(...)
    generation_successful = True  # ✅ Only set on success
    
except SafetyFilterError as e:
    return jsonify({"success": False, "should_deduct_credits": False, ...})
    
except PolicyViolationError as e:
    return jsonify({"success": False, "should_deduct_credits": False, ...})
    
except ValueError as e:
    return jsonify({"success": False, "should_deduct_credits": False, ...})

# Only increment stats/deduct credits if generation_successful is True
if generation_successful:
    website_stats_service.increment_images_generated(1)
    return jsonify({"success": True, "should_deduct_credits": True, ...})
```

---

## 💡 Implementation for Credit System

### Frontend Logic
```javascript
async function generateImage(prompt) {
    const response = await fetch('/api/image/generate', {
        method: 'POST',
        body: JSON.stringify({ prompt })
    });
    
    const data = await response.json();
    
    // Check if credits should be deducted
    if (data.success && data.should_deduct_credits) {
        // ✅ Successful generation - deduct credit
        updateUserCredits(-1);
    } else {
        // ❌ Failed generation - do NOT deduct credit
        showError(data.error || data.message);
    }
}
```

### Subscription Middleware (Future Implementation)
```python
@app.before_request
def check_image_generation_credits():
    if request.endpoint == 'image.generate_image':
        user_credits = get_user_credits(session['user_id'])
        
        if user_credits <= 0:
            return jsonify({
                "success": False,
                "should_deduct_credits": False,
                "error": "Insufficient credits"
            }), 403

@app.after_request
def deduct_credits_on_success(response):
    if request.endpoint == 'image.generate_image':
        try:
            data = response.get_json()
            if data.get('should_deduct_credits', False):
                # ✅ Only deduct if generation was successful
                deduct_user_credits(session['user_id'], 1)
        except:
            pass
    
    return response
```

---

## 📝 Logging Strategy

### Successful Generation
```
INFO - Starting image generation for prompt: '...'
INFO - Image generated successfully in 3.45s
INFO - Image saved to GCS: gs://...
INFO - Image generation completed successfully - ID: abc123
INFO - Incremented images generated counter (generation was successful)
```

### Safety Filter Block
```
INFO - Starting image generation for prompt: '...'
ERROR - No images returned from Imagen API after 3.12s
ERROR - This usually means the prompt was blocked by safety filters or policy violations
WARNING - Image generation blocked by safety filter for user user@example.com: Image generation was blocked...
```

### Policy Violation
```
INFO - Starting image generation for prompt: '...'
ERROR - Content policy violation after 2.87s: [Google API error message]
WARNING - Image generation blocked by policy violation for user user@example.com: ...
```

---

## 🧪 Testing Credit Deduction

### Test Case 1: Successful Generation
```bash
curl -X POST http://localhost:8080/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset over mountains"}'

# Expected: 
# - success: true
# - should_deduct_credits: true ✅
```

### Test Case 2: Safety Filter (Don't Deduct)
```bash
curl -X POST http://localhost:8080/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "[potentially sensitive prompt]"}'

# Expected:
# - success: false
# - should_deduct_credits: false ❌
# - error_type: "safety_filter"
```

### Test Case 3: Empty Prompt (Don't Deduct)
```bash
curl -X POST http://localhost:8080/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": ""}'

# Expected:
# - success: false
# - should_deduct_credits: false ❌
# - error_type: "validation_error"
```

---

## 🎯 Credit Deduction Decision Tree

```
User submits prompt
    ↓
Validate prompt
    ├─ Invalid → Return 400, should_deduct_credits: false ❌
    └─ Valid → Continue
        ↓
Call Imagen 3 API
    ├─ No images returned → SafetyFilterError, should_deduct_credits: false ❌
    ├─ Policy error → PolicyViolationError, should_deduct_credits: false ❌
    ├─ API error → RuntimeError, should_deduct_credits: false ❌
    └─ Success → Continue
        ↓
Save to GCS (optional failure won't affect credits)
    ↓
Save to Firestore (optional failure won't affect credits)
    ↓
Increment stats counter ✅
    ↓
Return success: true, should_deduct_credits: true ✅
```

---

## 📋 Firestore Schema for Failed Generations

You may want to log failed attempts for analytics:

```javascript
Collection: image_generation_failures
Document fields:
{
  user_id: string,
  prompt: string,
  error_type: "safety_filter" | "policy_violation" | "validation_error" | "unexpected_error",
  error_message: string,
  timestamp: timestamp,
  user_agent: string,
  ip_address: string (optional)
}
```

This helps you:
- Track patterns in blocked prompts
- Improve user guidance
- Detect abuse attempts
- Understand why generations fail

---

## 🚦 Error Type Frequency (Expected)

Based on typical usage:

| Error Type | Frequency | Impact on UX |
|------------|-----------|--------------|
| Successful | 90-95% | ✅ Good |
| Safety Filter | 3-5% | ⚠️ Moderate - User can rephrase |
| Policy Violation | 1-2% | ⚠️ Moderate - User can rephrase |
| Validation Error | 1-2% | 🔴 Low - User mistake |
| Unexpected Error | <1% | 🔴 High - Technical issue |

---

## 🔧 Monitoring & Alerts

### Metrics to Track
1. **Success Rate:** `successful_generations / total_attempts`
2. **Safety Block Rate:** `safety_filter_errors / total_attempts`
3. **Policy Block Rate:** `policy_violation_errors / total_attempts`
4. **Error Rate:** `unexpected_errors / total_attempts`

### Alert Thresholds
- 🚨 **Critical:** Success rate < 80%
- ⚠️ **Warning:** Safety block rate > 10%
- ⚠️ **Warning:** Error rate > 2%

### Query Examples (Firestore)
```javascript
// Count successful generations today
db.collection('image_generations')
  .where('created_at', '>=', startOfDay)
  .where('status', '==', 'generated')
  .count()

// Count failed attempts today
db.collection('image_generation_failures')
  .where('timestamp', '>=', startOfDay)
  .where('error_type', '==', 'safety_filter')
  .count()
```

---

## ✅ Best Practices

1. **Always check `should_deduct_credits` before deducting**
2. **Log all failure types separately** for analytics
3. **Provide helpful error messages** to users
4. **Don't expose sensitive API details** in error messages
5. **Monitor success rates** to detect API issues
6. **Track safety filter patterns** to improve prompts
7. **Test edge cases** regularly
8. **Update error handling** as Google's policies evolve

---

## 🔮 Future Enhancements

1. **Retry Logic:** Automatically retry on transient errors (not policy/safety)
2. **Prompt Rewriting:** Suggest alternative phrasings for blocked prompts
3. **Pre-validation:** Check prompts against common block patterns before API call
4. **Credit Refunds:** Manual admin tool to refund credits for false positives
5. **User Feedback:** Let users report incorrect blocks
6. **A/B Testing:** Test different safety filter levels per user segment

---

## 📚 Key Takeaways

✅ **Credits are ONLY deducted on successful generations**  
✅ **All failures return `should_deduct_credits: false`**  
✅ **Proper error types help future credit management**  
✅ **Comprehensive logging enables debugging**  
✅ **User-friendly messages improve experience**  

**Status:** ✅ Production-ready error handling implemented!
