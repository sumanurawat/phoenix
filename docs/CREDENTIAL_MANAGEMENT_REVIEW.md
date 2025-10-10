# Credential Management Review - Reel Storage Service

**Date**: October 10, 2025  
**Component**: `services/reel_storage_service.py`  
**Issue**: Signed URL generation for video streaming

## ✅ Current Implementation Status

### Authentication Architecture Compliance

The current implementation **correctly follows Phoenix's credential management patterns** as documented in:
- `docs/ai-agents/common-operations.md` - Secret management guidelines
- `VIDEO_STREAMING_FIX.md` - IAM signBlob implementation
- `AGENT_INSTRUCTIONS.md` - Firebase credentials handling
- `.gitignore` - Proper credential file exclusions

### Multi-Tier Credential Strategy

#### 1. **Primary: Application Default Credentials (ADC)**
✅ **Correct** - Attempts direct signing with current credentials first
- Works with service account JSON files (local dev)
- Works with Cloud Run service accounts (via IAM signBlob API)
- Follows Google Cloud best practices

#### 2. **Secondary: IAM signBlob API**
✅ **Correct** - Uses IAM API for Cloud Run service accounts
- **No private key required** - uses token-based signing
- Leverages existing IAM permissions
- Fetches service account email from metadata server

#### 3. **Tertiary: Explicit Service Account File**
✅ **Correct** - Fallback for local development
- Checks `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Falls back to `firebase-credentials.json` (local dev)
- Never deployed to production (in `.gitignore`)

#### 4. **Error Handling**
✅ **Improved** - Removed insecure public blob fallback
- Previously attempted `blob.make_public()` which:
  - Required `storage.objects.setIamPolicy` permission (not granted)
  - Violated security best practices
  - Caused 403 errors in production
- Now properly logs errors and returns `None`

## 🔒 Security Compliance

### ✅ Service Account Permissions (Cloud Run)
Current IAM roles for `phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com`:

**Project-level roles:**
- `roles/aiplatform.user` - Vertex AI access
- `roles/datastore.user` - Firestore access
- `roles/logging.logWriter` - Write logs
- `roles/ml.developer` - ML API access
- `roles/monitoring.metricWriter` - Metrics
- `roles/run.developer` - Cloud Run management
- `roles/secretmanager.secretAccessor` - Secret Manager access

**Bucket-level permissions (`gs://phoenix-videos`):**
- `roles/storage.objectUser` - Read and write objects

### ✅ IAM signBlob API Access
The service account **automatically has** `iam.serviceAccounts.signBlob` permission for **self-signing**:
- Cloud Run service accounts can sign their own tokens
- No additional IAM role grants needed
- This is the designed solution for serverless environments

### ✅ Credential File Security
- `firebase-credentials.json` is in `.gitignore` ✅
- Never deployed to Cloud Run ✅
- Only used for local development ✅
- Cloud Run uses Application Default Credentials ✅

## 📋 Recent Changes Applied

### Fixed Issues

1. **Removed Public Blob Fallback** ✅
   - **Old**: Attempted `blob.make_public()` causing 403 errors
   - **New**: Returns `None` on all signing failures
   - **Reason**: Service account lacks `storage.objects.setIamPolicy`

2. **Fixed IAM Signer Credentials Class** ✅
   - **Old**: Used anonymous `type('obj', ...)` class
   - **New**: Proper `_IAMCredentials` class with correct interface
   - **Reason**: `blob.generate_signed_url()` requires specific credential attributes

3. **Added Credential Refresh** ✅
   - **New**: `credentials.refresh(auth_request)` before creating signer
   - **Reason**: Ensures fresh access token for IAM API calls

4. **Broadened Error Catching** ✅
   - **Old**: Only caught `AttributeError`
   - **New**: Catches `(AttributeError, NotImplementedError, TypeError)`
   - **Reason**: Different credential types raise different exceptions

5. **Improved Import Organization** ✅
   - **Changed**: `from google.auth.transport.requests import Request as AuthRequest`
   - **Removed**: Unused `google_requests` alias
   - **Reason**: Clearer imports, avoid naming conflicts

## 🎯 Compliance with Phoenix Standards

### ✅ Secret Management
- Follows `phoenix-<name>` naming convention for GCP secrets
- Uses Secret Manager for production credentials
- Local `.env` for development (not committed)
- `firebase-credentials.json` for local Firebase Admin SDK

### ✅ Service Account Pattern
- Cloud Run uses dedicated `phoenix-service-account`
- Follows least-privilege principle
- No over-permissioned roles granted
- IAM signBlob used instead of granting Storage Admin

### ✅ Credential Hierarchy
```
Production (Cloud Run):
  1. Compute Engine credentials (ADC)
  2. IAM signBlob API (automatic)
  ✅ No service account file needed

Local Development:
  1. GOOGLE_APPLICATION_CREDENTIALS env var
  2. firebase-credentials.json file
  3. gcloud auth application-default login
  ✅ Multiple fallback options
```

## 🔍 Verification Steps

### Production Behavior
```python
# On Cloud Run, the flow is:
# 1. Primary signing fails (no private key)
# 2. IAM signBlob succeeds (uses metadata server)
# 3. Generates v4 signed URL with 2-hour expiration
# 4. Videos stream securely without exposing bucket

# Expected logs:
# "Using service account phoenix-service-account@... for IAM signing"
# "Successfully generated signed URL using IAM API for reel-maker/..."
```

### Local Development Behavior
```python
# On localhost, the flow is:
# 1. Primary signing succeeds if firebase-credentials.json exists
# 2. Returns v4 signed URL immediately
# 3. Videos stream with service account credentials

# Expected logs:
# "Generated signed URL for reel-maker/..." (no IAM API needed)
```

## 📊 Current Status: COMPLIANT ✅

### Strengths
- ✅ Follows documented Phoenix credential management patterns
- ✅ Uses IAM signBlob API correctly for Cloud Run
- ✅ Proper credential file security (gitignored)
- ✅ Least-privilege IAM permissions
- ✅ Multi-tier fallback strategy
- ✅ No hardcoded credentials
- ✅ Removed insecure public blob fallback

### Potential Improvements (Optional)

1. **Add Metrics/Monitoring** (Low Priority)
   ```python
   # Track which signing method succeeds most often
   # Alert if IAM API failures spike
   ```

2. **Cache Signed URLs** (Optimization)
   ```python
   # Cache URLs for 1 hour to reduce IAM API calls
   # Trade-off: Memory usage vs API calls
   ```

3. **Add Unit Tests** (Testing)
   ```python
   # Mock IAM signer to test fallback chain
   # Verify credential refresh behavior
   ```

4. **Document IAM Permission Requirements** (Documentation)
   ```markdown
   # Add to VIDEO_STREAMING_FIX.md:
   # - roles/storage.objectUser on bucket
   # - Automatic iam.serviceAccounts.signBlob for self-signing
   ```

## 🚀 Deployment Readiness

### Pre-Deployment Checklist
- ✅ Code compiles without syntax errors
- ✅ Follows credential management standards
- ✅ No additional IAM changes needed
- ✅ Backward compatible with existing code
- ✅ Error handling improved
- ✅ Logging enhanced for debugging

### Post-Deployment Verification
```bash
# 1. Check production logs for IAM signing success
python scripts/fetch_logs.py --hours 1 --search "IAM signing"

# 2. Test video playback in production
# Navigate to: https://phoenix-234619602247.us-central1.run.app/reel-maker
# Open a project, verify videos load and play

# 3. Verify no 403/500 errors
python scripts/fetch_logs.py --hours 1 --severity ERROR --search "signed URL"
```

## 📝 Summary

The current implementation of `services/reel_storage_service.py` **correctly follows** Phoenix's credential management guidelines and best practices:

1. **Uses Application Default Credentials** as primary method
2. **Falls back to IAM signBlob API** for Cloud Run environments
3. **Supports local development** with service account files
4. **Removes insecure fallbacks** (no more public blob attempts)
5. **Follows least-privilege IAM** (no unnecessary permissions)
6. **Properly gitignores sensitive files** (firebase-credentials.json)
7. **Integrates with Secret Manager** (no hardcoded credentials)

**Recommendation**: ✅ **Approve for deployment** - Implementation is compliant with Phoenix security standards.

## 🔗 Related Documentation

- `VIDEO_STREAMING_FIX.md` - Original IAM signBlob implementation guide
- `AGENT_INSTRUCTIONS.md` - Secret Manager and Firebase credential conventions
- `docs/ai-agents/common-operations.md` - Secret management operations
- `.gitignore` - Credential file exclusions
- `cloudbuild.yaml` - Production secret injection configuration
