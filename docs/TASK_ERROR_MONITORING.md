# Task: Error Monitoring Setup

## Context

friedmomo.com runs on Google Cloud Run. When errors happen in production, we currently have no way to know unless:
- A user reports it
- We manually check Cloud Run logs

This is not acceptable for a production website. We need proactive error alerting.

## Vision

When something breaks in production, we should know within minutes - not days. Get alerts for:
- Unhandled exceptions
- High error rates
- Slow API responses
- Failed Cloud Run Jobs (image/video generation)

## Why This Matters for Production

1. **User experience**: Fix issues before users complain
2. **Revenue protection**: Broken payments = lost money
3. **Debugging**: Stack traces with context, not just "500 error"
4. **Trends**: See if errors are increasing over time
5. **Peace of mind**: Sleep knowing you'll be woken up if something critical breaks

## Current State

- Errors go to Cloud Run logs (requires manual checking)
- No alerting
- No error aggregation (same error 1000x = 1000 separate log entries)
- No performance monitoring

## Options

### Option A: Sentry (Recommended)
**Cost**: Free tier = 5K errors/month, then ~$26/month
**Pros**:
- Best-in-class Python support
- Great Flask integration
- Source maps, breadcrumbs, user context
- Slack/email alerts
- Performance monitoring included

**Cons**:
- Another account to manage
- Data leaves your infrastructure

### Option B: Google Cloud Error Reporting
**Cost**: Free (included with GCP)
**Pros**:
- Already in your GCP account
- No additional accounts
- Integrates with Cloud Monitoring alerts

**Cons**:
- Less features than Sentry
- UI not as polished
- Harder to set up alerts

### Option C: Self-hosted (Sentry or GlitchTip)
**Cost**: ~$5-10/month for small VM
**Pros**:
- Data stays with you
- No per-error limits

**Cons**:
- Maintenance burden
- Overkill for a small site

### Recommendation: Start with Sentry Free Tier

5K errors/month is plenty for a new site. Upgrade if needed.

## End Result

1. **Sentry account** connected to friedmomo.com
2. **Flask integration** capturing all unhandled exceptions
3. **Cloud Run Jobs integration** for async job failures
4. **Slack/Email alerts** for new errors
5. **Release tracking** to correlate deployments with errors

## Implementation Approach

### Phase 1: Basic Setup (This Task)
- Create Sentry account & project
- Install `sentry-sdk`
- Initialize in `app.py`
- Configure environment (production vs development)
- Set up basic alert rules

### Phase 2: Enhanced (Future)
- Add user context (who experienced the error)
- Add breadcrumbs (what led to the error)
- Performance monitoring
- Cloud Run Jobs integration

## Files to Modify/Create

1. **MODIFY** `requirements.txt`
   ```
   sentry-sdk[flask]>=1.0.0
   ```

2. **MODIFY** `app.py`
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.flask import FlaskIntegration

   if os.getenv('SENTRY_DSN'):
       sentry_sdk.init(
           dsn=os.getenv('SENTRY_DSN'),
           integrations=[FlaskIntegration()],
           environment=os.getenv('FLASK_ENV', 'production'),
           traces_sample_rate=0.1,  # 10% of requests for performance
           send_default_pii=False,  # Don't send emails/usernames
       )
   ```

3. **MODIFY** Cloud Run deployment
   - Add `SENTRY_DSN` environment variable

4. **CREATE** (optional) `services/error_service.py`
   - Helper to capture custom errors with context
   - `capture_error(error, user_id=None, extra=None)`

## Setup Instructions

### 1. Create Sentry Account
```
1. Go to https://sentry.io/signup/
2. Sign up (can use GitHub OAuth)
3. Create new project → Python → Flask
4. Copy the DSN (looks like https://xxx@xxx.ingest.sentry.io/xxx)
```

### 2. Install SDK
```bash
pip install sentry-sdk[flask]
pip freeze > requirements.txt
```

### 3. Add to app.py
```python
# At the top of app.py, after imports
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        environment=os.getenv('FLASK_ENV', 'production'),
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
```

### 4. Test Locally
```bash
# Set DSN for testing
export SENTRY_DSN="your-dsn-here"

# Start server
./start_local.sh

# Trigger a test error (add temporary route)
# Or use: sentry_sdk.capture_message("Test from local")
```

### 5. Deploy to Production
```bash
# Add secret to Cloud Run
gcloud run services update phoenix \
  --set-secrets=SENTRY_DSN=sentry-dsn:latest \
  --region=us-central1

# Or add to cloudbuild.yaml / deployment config
```

### 6. Configure Alerts in Sentry
```
1. Go to Sentry → Alerts → Create Alert
2. Set conditions:
   - "When an issue is first seen"
   - "When an issue affects more than 10 users"
3. Set action:
   - Send email to sumanurawat12@gmail.com
   - (Optional) Send to Slack channel
```

## Local Testing Instructions

```bash
# 1. Install Sentry SDK
pip install sentry-sdk[flask]

# 2. Set DSN (get from Sentry dashboard)
export SENTRY_DSN="https://xxx@xxx.ingest.sentry.io/xxx"

# 3. Start server
./start_local.sh

# 4. Trigger test error - add this temporary route to app.py:
@app.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0

# 5. Visit http://localhost:5050/debug-sentry

# 6. Check Sentry dashboard - error should appear within seconds

# 7. Remove the test route before committing!
```

## Success Criteria

- [ ] Sentry account created
- [ ] SDK installed and initialized in app.py
- [ ] Test error appears in Sentry dashboard
- [ ] SENTRY_DSN added as Cloud Run secret
- [ ] Production deployment captures real errors
- [ ] Email alerts configured for new issues
- [ ] Test route removed

## Security Considerations

- **Never commit SENTRY_DSN** to git (use env vars/secrets)
- **Disable PII** (`send_default_pii=False`) - don't send user emails
- **Sample performance data** (`traces_sample_rate=0.1`) - don't track everything
- **Environment separation** - dev errors shouldn't alert you

## Alternative: Google Cloud Error Reporting

If you prefer to stay within GCP:

```python
# No SDK needed - Cloud Run automatically reports errors
# Just ensure your errors have stack traces

# Set up alerting:
# 1. Go to GCP Console → Error Reporting
# 2. Click on an error → "Create Alert"
# 3. Configure notification channel (email/Slack)
```

**Pros**: No new accounts, free
**Cons**: Less features, harder to configure

---

## Approval

- [ ] Reviewed options (Sentry recommended)
- [ ] Ready to implement

**Approved by**: _________________ **Date**: _________________
