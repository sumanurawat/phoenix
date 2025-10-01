# Reel Maker Setup Guide

## Overview
The Reel Maker feature allows users to create short-form video projects using Google's Veo AI. This guide covers the setup requirements and configuration.

## Prerequisites

### 1. Google Cloud Platform Setup
- **GCP Project**: Active project with billing enabled
- **Service Account**: With appropriate permissions for Cloud Storage and Vertex AI
- **Firebase Credentials**: `firebase-credentials.json` in project root

### 2. Required APIs
Enable these APIs in your GCP project:
- Cloud Storage API
- Vertex AI API
- Firebase Admin SDK

### 3. Google Cloud Storage Bucket
You need a GCS bucket to store generated video clips and stitched reels.

#### Creating a Bucket
```bash
# Using gcloud CLI
gcloud storage buckets create gs://YOUR-BUCKET-NAME \
  --location=US \
  --uniform-bucket-level-access

# Or use the Google Cloud Console:
# https://console.cloud.google.com/storage/browser
```

#### Bucket Permissions
Ensure your service account has these roles:
- `roles/storage.objectAdmin` - For reading/writing video files
- `roles/storage.objectCreator` - For uploading generated videos

```bash
# Grant permissions to your service account
gcloud storage buckets add-iam-policy-binding gs://YOUR-BUCKET-NAME \
  --member="serviceAccount:YOUR-SERVICE-ACCOUNT@PROJECT-ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

## Environment Configuration

### 1. Copy Environment Template
```bash
cp .env.example .env
```

### 2. Configure Video Storage Bucket
Add your bucket name to `.env`:

```bash
# Option 1: Use shared bucket for all video features
VIDEO_STORAGE_BUCKET=your-bucket-name

# Option 2: Use separate bucket just for Reel Maker (optional)
REEL_MAKER_GCS_BUCKET=your-reel-maker-bucket-name

# The service will check in this order:
# 1. REEL_MAKER_GCS_BUCKET
# 2. VIDEO_GENERATION_BUCKET
# 3. VIDEO_STORAGE_BUCKET
```

### 3. Required Environment Variables
Ensure these are also set in your `.env`:

```bash
# Google Cloud Authentication
GOOGLE_APPLICATION_CREDENTIALS=./firebase-credentials.json

# Firebase
FIREBASE_API_KEY=your-firebase-api-key

# Gemini API (for AI features)
GEMINI_API_KEY=your-gemini-api-key

# Flask
SECRET_KEY=your-secret-key
FLASK_ENV=development
FLASK_DEBUG=1
```

## GCS Bucket Layout

The Reel Maker uses the following structure in your bucket:

```
reel-maker/
  {userId}/
    {projectId}/
      raw/
        {jobId}/
          prompt-00/
            clip_timestamp.mp4
          prompt-01/
            clip_timestamp.mp4
      stitched/
        reel_full_timestamp.mp4
```

This structure:
- **Isolates user data** for security
- **Organizes by project** for easy management
- **Separates raw clips from stitched reels** for efficient storage
- **Groups clips by generation job** for tracking

## Local Development Setup

### 1. Install Dependencies
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Build React Frontend
```bash
cd frontend/reel-maker
npm install
npm run build
cd ../..
```

### 3. Start Application
```bash
./start_local.sh
```

The script will:
- Activate virtual environment
- Check and build React frontend if needed
- Start Flask on port 8080

Visit: http://localhost:8080/reel-maker

## Testing Configuration

### Verify Bucket Access
```python
# Run in Python with venv activated
from services.reel_storage_service import reel_storage_service

# Check if bucket is configured
try:
    bucket_name = reel_storage_service.bucket_name
    print(f"✅ Bucket configured: {bucket_name}")
except RuntimeError as e:
    print(f"❌ Error: {e}")
```

### Test Video Generation (requires bucket + Veo API access)
```bash
# Create a test project via API
curl -X POST http://localhost:8080/api/reel/projects \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Project"}'

# This should return a project with default settings
```

## Troubleshooting

### Error: "Reel Maker storage bucket is not configured"
**Cause**: No GCS bucket configured in environment variables.

**Solution**:
1. Check `.env` file exists (not just `.env.example`)
2. Verify `VIDEO_STORAGE_BUCKET` is set with actual bucket name
3. Restart Flask application after changing `.env`

### Error: "403 Forbidden" when accessing bucket
**Cause**: Service account lacks permissions.

**Solution**:
```bash
# Check current IAM policy
gcloud storage buckets get-iam-policy gs://YOUR-BUCKET-NAME

# Add required role
gcloud storage buckets add-iam-policy-binding gs://YOUR-BUCKET-NAME \
  --member="serviceAccount:EMAIL@PROJECT-ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### Error: "DefaultCredentialsError"
**Cause**: Google Cloud credentials not properly configured.

**Solution**:
1. Ensure `firebase-credentials.json` exists in project root
2. Verify `GOOGLE_APPLICATION_CREDENTIALS` points to this file
3. Check service account JSON is valid and not expired

### React Frontend Not Loading
**Cause**: Build artifacts missing or outdated.

**Solution**:
```bash
cd frontend/reel-maker
npm install
npm run build
cd ../..
./start_local.sh
```

### Videos Not Appearing After Generation
**Cause**: Could be several issues:
1. Veo API not returning proper storage URIs
2. Bucket permissions issue
3. Wrong bucket path configuration

**Debug Steps**:
```bash
# Check application logs
tail -f logs/app.log

# Verify files in bucket
gsutil ls gs://YOUR-BUCKET-NAME/reel-maker/

# Check Firestore for project status
# Look at reel_maker_projects collection
```

## Production Deployment

### Cloud Build Configuration
The `cloudbuild.yaml` should include:

```yaml
steps:
  # Install Node dependencies and build React
  - name: 'node:20'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        cd frontend/reel-maker
        npm ci
        npm run build
  
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/phoenix', '.']
```

### Environment Secrets
Store in Google Cloud Secret Manager:
```bash
# Store bucket name
echo -n "your-bucket-name" | gcloud secrets create video-storage-bucket --data-file=-

# Update Cloud Run service to use secret
gcloud run services update phoenix \
  --update-secrets=VIDEO_STORAGE_BUCKET=video-storage-bucket:latest
```

## Cost Considerations

### Storage Costs
- **Standard Storage**: ~$0.020/GB/month
- **Nearline Storage** (for archives): ~$0.010/GB/month
- **Network Egress**: Varies by region

### Recommendations
1. **Set lifecycle policies** to auto-delete old raw clips:
```bash
gsutil lifecycle set lifecycle.json gs://YOUR-BUCKET-NAME
```

Example `lifecycle.json`:
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["reel-maker/*/*/raw/"]
        }
      }
    ]
  }
}
```

2. **Monitor usage** in GCP Console
3. **Consider regional buckets** to reduce egress costs

## Security Best Practices

1. **Never expose bucket name** in client-side code
2. **Use signed URLs** with short expiration for downloads
3. **Validate user ownership** before serving media
4. **Implement rate limiting** on generation endpoints
5. **Log all access** for audit trails
6. **Regularly rotate service account keys**

## Next Steps

After setup:
1. Create a test project via UI
2. Add prompts and generate clips
3. Verify clips appear in GCS bucket
4. Test stitching feature (requires ≥2 clips)
5. Check Firestore for proper data persistence

## Support

For issues:
1. Check logs: `tail -f logs/app.log`
2. Review Firestore collections: `reel_maker_projects`, `reel_maker_jobs`
3. Verify GCP quotas: Vertex AI, Storage API
4. Check service account permissions

## References

- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Vertex AI Veo Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/video/overview)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
