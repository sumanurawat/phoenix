# Reel Maker - Quick Reference

## 🚀 Quick Start

```bash
# 1. Verify setup
./setup_reel_maker.sh

# 2. Start server
./start_local.sh

# 3. Open browser
# http://localhost:8080/reel-maker
```

## 🎬 Using Reel Maker

### Create a Project
1. Click the **+** button in the sidebar
2. Enter a project name
3. Project appears with "Draft" status

### Add Prompts
1. Select your project from the sidebar
2. Click **"Edit Prompts"** button
3. Add prompts in JSON format:
```json
[
  "A serene beach at sunset with waves",
  "Modern city skyline with flying cars"
]
```
4. Click **Save**

### Generate Videos
1. Ensure prompts are added
2. Click **"Generate Clips"** button
3. Watch real-time progress in the toolbar
4. Clips appear in the Scene List when complete

### Project Configuration (Fixed Defaults)
- **Orientation**: Portrait (9:16)
- **Duration**: 8 seconds per clip
- **Model**: veo-3.1-fast-generate-preview
- **Compression**: Optimized
- **Audio**: Enabled

## 🔧 Configuration

### Required Environment Variables
```bash
VIDEO_STORAGE_BUCKET=phoenix-videos
GEMINI_API_KEY=your-key
FIREBASE_API_KEY=your-key
GOOGLE_APPLICATION_CREDENTIALS=./firebase-credentials.json
```

### Check Configuration
```bash
./setup_reel_maker.sh
```

## 🐛 Common Issues

### "Storage bucket is not configured"
**Fix**: Add to `.env`:
```bash
VIDEO_STORAGE_BUCKET=phoenix-videos
```
Restart server: `./start_local.sh`

### "Failed to start generation"
**Causes**:
- Missing Veo API access
- Invalid prompts (policy violations)
- Insufficient GCP quotas

**Debug**:
```bash
# Check logs
tail -f logs/app.log

# Verify bucket access
gcloud storage ls gs://phoenix-videos/reel-maker/
```

### Frontend not loading
**Fix**:
```bash
cd frontend/reel-maker
npm run build
cd ../..
./start_local.sh
```

## 📁 Project Structure

```
phoenix/
├── api/
│   └── reel_routes.py          # API endpoints
├── services/
│   ├── reel_project_service.py # Firestore operations
│   ├── reel_generation_service.py # Veo integration
│   └── reel_storage_service.py # GCS operations
├── frontend/reel-maker/
│   └── src/
│       ├── App.tsx            # Main React app
│       ├── components/        # UI components
│       └── styles/main.css    # Styling
├── templates/
│   └── reel_maker.html        # Flask template
└── static/reel_maker/         # Built React assets
```

## 📊 Firestore Collections

### `reel_maker_projects`
```json
{
  "projectId": "auto-id",
  "userId": "firebase-uid",
  "title": "My Reel",
  "orientation": "portrait",
  "durationSeconds": 8,
  "model": "veo-3.1-fast-generate-preview",
  "promptList": ["prompt1", "prompt2"],
  "clipFilenames": ["clip1.mp4", "clip2.mp4"],
  "status": "ready",
  "createdAt": "timestamp",
  "updatedAt": "timestamp"
}
```

### `reel_maker_jobs`
```json
{
  "jobId": "reeljob-xxx",
  "projectId": "project-id",
  "status": "processing",
  "startedAt": "timestamp"
}
```

## 🎨 UI Layout

```
┌────────────────────────────────────────┐
│ [< Back]          Reel Maker           │
├──────────┬─────────────────────────────┤
│          │                             │
│ Projects │  Project Title  [Rename]    │
│  [+]     │  Status: Ready              │
│          │                             │
│ ┌──────┐ │  Project Details            │
│ │Active│ │  Orientation: Portrait      │
│ └──────┘ │  Duration: 8s               │
│          │                             │
│ ┌──────┐ │  [Generate Clips] Progress  │
│ │Draft │ │                             │
│ └──────┘ │  Prompts (2)                │
│          │  [Edit Prompts]             │
│          │                             │
│          │  Clips (2)                  │
│          │  ┌────┐ ┌────┐             │
│          │  │ 1  │ │ 2  │             │
│          │  └────┘ └────┘             │
└──────────┴─────────────────────────────┘
```

## 🔄 Status Flow

```
Draft → Generating → Ready
  ↓
Error (with message)
```

## 🌐 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reel/projects` | List all projects |
| POST | `/api/reel/projects` | Create new project |
| GET | `/api/reel/projects/:id` | Get project details |
| PUT | `/api/reel/projects/:id` | Update project |
| DELETE | `/api/reel/projects/:id` | Delete project |
| POST | `/api/reel/projects/:id/generate` | Start generation |
| GET | `/api/reel/projects/:id/events` | SSE event stream |
| GET | `/api/reel/projects/:id/clips/:filename` | Stream clip |

## 💾 GCS Bucket Layout

```
gs://phoenix-videos/
  reel-maker/
    {userId}/
      {projectId}/
        raw/
          {jobId}/
            prompt-00/
              clip_20250930_120501.mp4
            prompt-01/
              clip_20250930_120602.mp4
        stitched/
          reel_full_20250930_121500.mp4
```

## 🔒 Security

- ✅ Firebase authentication required
- ✅ CSRF protection on mutations
- ✅ User ownership validated
- ✅ No direct GCS bucket access from client
- ✅ Signed URLs for downloads (when implemented)

## 📈 Monitoring

### Check Generation Status
```python
# In Firebase Console → Firestore
# Collection: reel_maker_jobs
# Filter: status == "processing"
```

### Check Storage Usage
```bash
gcloud storage du gs://phoenix-videos/reel-maker/ --summarize
```

### View Logs
```bash
# Local
tail -f logs/app.log

# Production
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

## 🧪 Testing

### Manual Test Flow
1. Create project: "Test Reel"
2. Add prompts: `["A peaceful garden", "City at night"]`
3. Click Generate
4. Verify status updates in real-time
5. Check clips appear in Scene List
6. Verify clips in GCS: `gsutil ls gs://phoenix-videos/reel-maker/`

### API Test (curl)
```bash
# Create project
curl -X POST http://localhost:8080/api/reel/projects \
  -H "Content-Type: application/json" \
  -d '{"title": "API Test"}'

# List projects
curl http://localhost:8080/api/reel/projects
```

## 📝 TODO (Future Phases)

- [ ] Video stitching (combine clips)
- [ ] Clip regeneration
- [ ] Download as ZIP
- [ ] Share links
- [ ] Prompt templates
- [ ] Advanced settings override
- [ ] Cost tracking
- [ ] Lifecycle policies

## 🔗 Links

- **Setup Guide**: REEL_MAKER_SETUP.md
- **Status**: REEL_MAKER_STATUS.md
- **Technical Plan**: docs/reel_maker_plan.md
- **GCS Console**: https://console.cloud.google.com/storage/browser/phoenix-videos
- **Firebase Console**: https://console.firebase.google.com

## ⚡ Performance Tips

1. **Batch prompts**: Generate multiple clips in one job
2. **Monitor quotas**: Vertex AI has rate limits
3. **Clean old clips**: Set lifecycle policies
4. **Use optimized compression**: Default setting
5. **Cache project list**: Reduces Firestore reads

---

**Need Help?** Check REEL_MAKER_SETUP.md for detailed troubleshooting.
