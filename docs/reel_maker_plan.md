# Reel Maker Feature Technical Plan

_Last updated: September 26, 2025_

## 1. Objectives & Scope
- **Deliver a dedicated "Reel Maker" experience** that allows authenticated users to create and manage short-form video projects separate from the existing video generation beta page.
- **Persist project state** (metadata, prompts, generated asset references) so users can return to a project at any time without losing progress.
- **Adopt React within the Flask app** using an embedded, build-step based approach to establish the migration path toward a componentized frontend.
- **Integrate Google Cloud Storage (GCS)** for durable video asset storage while guarding direct bucket access.
- **Provide backend-managed video stitching** to produce a combined reel from generated clips.

**Out of scope for the initial cut**
- Regenerating videos within an existing project (users can create a new project instead).
- Advanced prompt history, multi-user collaboration, or share links.
- Fine-grained AI configuration overrides beyond the defaulted settings defined below.

## 2. User Experience Overview
1. **Homepage Tile**: Add a "Reel Generator" tile on `templates/index.html` that links to the new `/reel-maker` route (login required).
2. **Profile Shortcuts**: Update profile/dashboard templates to include quick-access buttons to both `/video-generation` and `/reel-maker`.
3. **Project List View** (left column, React): Users see existing projects with title, created date, and clip count. Create button opens a modal to name a new project.
4. **Project Workspace** (main pane):
   - Configuration header with fixed defaults (orientation, duration, compression, model, audio toggle).
   - JSON prompt textarea with validation + sample prompt injection.
   - Action buttons: Validate, Generate, Fetch Sample Prompts, Clear.
   - Generation results grid rendering video previews sourced from backend-streamed GCS assets.
   - Error panel for Veo policy violations or backend failures.
   - "Stitch Reel" button becomes active when ≥2 clips exist; result displayed alongside clip list.

## 3. Architecture Decisions
| Area | Decision | Rationale |
| --- | --- | --- |
| React integration | **Hybrid approach** – build React bundle with Vite and embed via Flask template (`reel_maker.html`). | Enables gradual migration without reorganizing routing. |
| Data persistence | New Firestore collection **`reel_maker_projects`**. | Keeps video projects isolated from chat conversation schema; easier lifecycle management. |
| Asset storage | GCS hierarchy `gs://<bucket>/reel-maker/{userId}/{projectId}/{clipName}.mp4`. | Predictable layout for both generated clips and stitched reel; facilitates cleanup. |
| Video generation | Reuse existing Veo service + server-side polling. | Minimizes duplication; ensure storage URI passed so Veo writes directly to GCS. |
| Video stitching | Backend FFmpeg job invoked via authenticated API. | Guarantees consistent rendering, avoids exposing bucket or requiring client CPU. |
| Access control | Backend-only GCS access + signed streaming endpoints. | Prevents users from accessing arbitrary bucket paths while still allowing download through Flask. |
| Status updates | Continue using Server-Sent Events via `realtime_event_bus`. | Aligns with current video generation flow; allows near-real-time UI updates. |
| Build pipeline | Add `frontend/reel-maker/` Vite app; extend `start_local.sh` to run `npm install` (if needed) and `npm run build` once per launch. | Keeps "one-command" local startup; no separate dev server required initially. |

## 4. Firestore Data Model
Collection: `reel_maker_projects`

Each document (`projectId` = Firestore-generated UUID):
```json
{
  "projectId": "auto-id",
  "userId": "firebase-uid",
  "userEmail": "user@example.com",
  "title": "Spring Collection Reel",
  "orientation": "portrait",           // "portrait" | "landscape"
  "durationSeconds": 8,
  "compression": "optimized",           // enum
  "model": "veo-3.0-fast-generate-001",
  "audioEnabled": true,
  "promptList": ["prompt 1", "prompt 2"],
  "clipFilenames": ["clip_20250926T120501.mp4", "clip_20250926T121010.mp4"],
  "stitchedFilename": "reel_full_20250926T121500.mp4", // optional
  "status": "ready",                  // "draft" | "generating" | "error" | "ready"
  "errorInfo": { "code": "POLICY_VIOLATION", "message": "…" },
  "createdAt": <server timestamp>,
  "updatedAt": <server timestamp>
}
```

**Notes**
- `clipFilenames` + `stitchedFilename` store file names only. Full GCS paths constructed at runtime using user/project IDs.
- `promptList` replaced whenever generation runs to maintain latest definition.
- `status` drives UI badges.
- Consider future subcollection `activity_log` if we need audit trails.

## 5. GCS Layout
```
reel-maker/
  {userId}/
    {projectId}/
      raw/
        clip_20250926T120501.mp4
        clip_20250926T121010.mp4
      stitched/
        reel_full_20250926T121500.mp4
```
- Storage URI passed to Veo: `gs://<bucket>/reel-maker/{userId}/{projectId}/raw/`.
- Backend has service account with read/write; clients never receive signed upload URLs.
- Download pipeline: Flask endpoint verifies ownership, generates short-lived signed URL, or streams via `send_file` after downloading to temp file.

## 6. Backend Enhancements
### 6.1 Routing
- New blueprint `api/reel_routes.py` with URL prefix `/api/reel`.
- Routes (all `@login_required`, `@csrf_protect` on mutating operations):
  | Method | Path | Purpose |
  | --- | --- | --- |
  | GET | `/projects` | List projects for current user (ordered by `updatedAt` desc). |
  | POST | `/projects` | Create project with default settings + user-provided title. |
  | GET | `/projects/<id>` | Fetch project details & computed asset URLs. |
  | PUT | `/projects/<id>` | Update title and configuration (orientation, audio). |
  | DELETE | `/projects/<id>` | Soft delete (mark `status":"archived"`) or hard delete + asset cleanup. |
  | POST | `/projects/<id>/generate` | Trigger Veo generation for supplied prompt list. |
  | POST | `/projects/<id>/stitch` | Start stitching job for existing clips. |
  | GET | `/projects/<id>/clips/<filename>` | Stream single clip through backend after ownership check. |
  | GET | `/projects/<id>/status/stream` | SSE channel for job updates (reuse `realtime_event_bus`). |

### 6.2 Services
- **`services/reel_project_service.py`** (new): Firestore CRUD helpers, validation, ownership enforcement.
- **`services/gcs_media_service.py`**: Utility for constructing paths, uploading stitched files, generating signed URLs, and cleaning up directories.
- **`services/video_stitching_service.py`**: Wrap FFmpeg operations. Steps:
  1. Download raw clips to temp path (`/tmp/reel_maker/<jobId>/`).
  2. Generate concat file for FFmpeg.
  3. Run `ffmpeg -f concat -safe 0 -i list.txt -c copy` (or re-encode for consistent codecs).
  4. Upload result to `stitched/` folder.
  5. Update Firestore doc with new filename + status.
- Extend **`VeoGenerationParams`** usage to set `storage_uri` automatically based on project metadata.
- Update **`video_batch_orchestrator`** or introduce dedicated `ReelGenerationOrchestrator` for simplified defaults.

### 6.3 Background Execution
- Reuse existing threading model for MVP (consistent with `/api/video`).
- Log job IDs & statuses to Firestore collection `reel_maker_jobs` for observability.
- Consider promoting to Celery/Cloud Tasks later (catalogued in risk section).

## 7. Frontend (React) Implementation
### 7.1 Project Structure
```
frontend/
  reel-maker/
    package.json
    vite.config.ts
    src/
      main.tsx
      App.tsx
      components/
        ProjectSidebar.tsx
        ProjectForm.tsx
        PromptEditor.tsx
        ClipGallery.tsx
        StitchPanel.tsx
      hooks/
        useProjects.ts
        useGenerationStream.ts
      services/api.ts
      styles/
        variables.scss
```
- **State management**: React Query (TanStack Query) for server state (projects, job status). Simple `useState` for local form state.
- **Styling**: SCSS modules compiled via Vite; final CSS emitted to `static/reel_maker/`.
- **Icons**: Continue using Font Awesome via existing CDN to stay consistent.

### 7.2 Embedding Strategy
1. Build artifact emitted to `static/reel_maker/assets/`.
2. Add new template `templates/reel_maker.html`:
   ```html
   {% extends "base.html" %}
   {% block content %}
   <div id="reel-maker-root"></div>
   {% endblock %}
   {% block extra_js %}
   <script type="module" src="{{ url_for('static', filename='reel_maker/assets/main.js') }}"></script>
   {% endblock %}
   ```
3. New route in `app.py`:
   ```python
   @app.route('/reel-maker')
   @login_required
   def reel_maker():
       return render_template('reel_maker.html', title='Reel Maker')
   ```

### 7.3 Build & Dev Workflow
- Add `frontend/reel-maker/package.json` with scripts:
  ```json
  {
    "scripts": {
      "dev": "vite",
      "build": "vite build --outDir ../../static/reel_maker"
    }
  }
  ```
- Update `start_local.sh`:
  1. Detect Node availability; warn if missing.
  2. Run `npm install` in `frontend/reel-maker` if `node_modules` absent.
  3. Execute `npm run build` before launching Flask to ensure assets are current.
  4. Optional: accept `--watch-frontend` flag to run `npm run dev` in background for hot reload (documented but not default).
- Production deploy: Add Cloud Build step invoking `npm ci && npm run build` before Flask image build.

## 8. Video Generation Flow (Server Perspective)
1. **POST `/api/reel/projects/<id>/generate`** receives prompts JSON from React, validates shape, enforces ≤50 prompts, orientation consistency, etc.
2. Build Veo request with defaults:
   - `duration_seconds = 8`
   - `model = "veo-3.0-fast-generate-001"`
   - `compression_quality = "optimized"`
   - `generate_audio = true`
   - `aspect_ratio` derived from orientation.
3. Invoke `veo_video_service.start_generation` with `storage_uri` computed from GCS layout.
4. Publish SSE updates for UI (queued → generating → completed/error per prompt).
5. Update Firestore doc `status` to `generating` and override `promptList`.
6. Upon completion, push clip filenames extracted from GCS URIs into Firestore, set `status = "ready"` or `"error"` with details.
7. Return summary payload to frontend (job ID, clip count, message).

**Note**: Since Veo writes directly to GCS, ensure service account used by backend has `storage.objects.get` and `storage.objects.list` on relevant prefix. Validate bucket CORS/ACL to prevent public exposure.

## 9. Video Stitching Workflow
1. UI exposes Stitch button once `clipFilenames.length >= 2`.
2. **POST `/api/reel/projects/<id>/stitch`** enqueues background job.
3. Backend steps:
   - Fetch project doc and verify ownership.
   - Download clips sequentially (consider parallel for >5 clips) to ephemeral workspace.
   - Normalize orientation/codec using FFmpeg (force `-vf scale` as needed, re-encode with `h264` + AAC) to avoid muxing errors.
   - Concatenate using FFmpeg `concat` demuxer: `ffmpeg -f concat -safe 0 -i list.txt -c:v libx264 -c:a aac output.mp4`.
   - Upload to `stitched/` folder, update Firestore `stitchedFilename` + `updatedAt`.
   - Emit SSE progress events (downloading clips, stitching, uploading, complete) for visual feedback.
4. Clean up temp files regardless of success (finally block).
5. Error path writes `status = "error"` + `errorInfo`, surfaces message in UI.

## 10. Security & Access Control
- **Authentication**: Reuse `@login_required` decorator.
- **Authorization**: Service layer ensures `project.userId == session['user_id']` before serving metadata or files.
- **GCS Access**: Client never receives bucket path. For playback, backend proxy route (`/api/reel/projects/<id>/clips/<filename>`) downloads clip into streaming response (or generates signed URL with 5 min expiry) after verifying ownership.
- **CSRF**: All POST/PUT/DELETE routes decorated with `@csrf_protect`. React API helper attaches token from meta tag.
- **Rate Limiting**: Consider reusing `services.rate_limiter` to prevent excessive video generation or stitching.
- **Logging**: Log user ID, project ID, job IDs for traceability (avoid logging full prompts unless necessary for debugging). Redact PII in production logs.

## 11. Error Handling & Observability
- Standardize backend error format: `{ "success": false, "error": { "code": "VEO_POLICY", "message": "..." } }`.
- Map Veo API policy errors to user-friendly descriptions in React UI.
- Firestore: store last error message and timestamp for each project to aid support.
- Monitoring: Extend existing logging to Google Cloud Logging; add log entry when generation/stitch starts, completes, fails.
- Optional future: push status updates to Slack/GCP alerts if repeated failures occur.

## 12. Testing Strategy
- **Unit tests**
  - Firestore service mocks verifying CRUD + ownership.
  - GCS service path construction + stubbed signed URL generation.
  - Stitching service using small sample clips stored under `tests/data/` (skip if ffmpeg missing, mark xfail).
- **Integration tests**
  - Flask test client hitting `/api/reel/projects` endpoints with mocked Firestore and Veo service responses.
  - SSE stream smoke test verifying event order for generation job.
- **Frontend tests**
  - React Testing Library for component rendering and prompt validation.
  - Cypress (optional) for end-to-end flow (login stubbed) after initial MVP.

## 13. Deployment & DevOps Considerations
- Update `cloudbuild.yaml` to run `npm ci && npm run build` inside `frontend/reel-maker` before Docker build.
- Ensure container image includes compiled React bundle under `/app/static/reel_maker`.
- Document local workflow:
  ```bash
  ./start_local.sh            # builds React + runs Flask
  npm --prefix frontend/reel-maker run dev   # optional separate terminal for hot reload
  ```
- Add README section describing Reel Maker setup & environment variables (GCS bucket, etc.).

## 14. Risks & Mitigations
| Risk | Mitigation |
| --- | --- |
| Large video downloads during stitching overwhelm server memory | Stream downloads to disk, enforce max clip duration/count per project. |
| FFmpeg not installed in environment | Add dependency instructions; bundle static ffmpeg binary in Docker image. |
| Storage growth in GCS | Implement lifecycle rules to auto-delete raw clips older than N days or add cleanup endpoint. |
| Vite build failures on CI | Pin Node version (e.g., 20.x) via `.nvmrc` / Cloud Build step; cache `node_modules` where possible. |
| SSE connection drops | Handle reconnect logic in React; backend supports idempotent status fetch fallback via REST. |

## 15. Incremental Delivery Plan
1. **Phase 1 – Foundations**
   - Create Firestore schema + backend CRUD endpoints.
   - Build React project shell + embed into Flask route.
   - Display project list with create/delete.
2. **Phase 2 – Generation MVP**
   - Hook generation endpoint to Veo with defaults.
   - Store prompts + clip metadata; render clip list (mock data until GCS ready).
3. **Phase 3 – GCS Integration**
   - Configure storage URIs, backend streaming endpoint, real asset playback.
4. **Phase 4 – Stitching & Polish**
   - Add stitching service, SSE progress, error reporting.
   - Update profile buttons, homepage tile, documentation.
5. **Phase 5 – Observability & Cleanup**
   - Logs, metrics, cleanup scripts, automated tests.

---

### Open Questions / Follow-ups
- Confirm target GCS bucket name & IAM role for video storage (service account needs write + list + get).
- Decide retention policy for raw clips vs stitched reels.
- Validate ffmpeg availability on production container (may require Dockerfile updates).

This plan provides the blueprint for implementing the Reel Maker experience using a React frontend embedded within the existing Flask application, while ensuring secure asset handling and scalable backend workflows.
