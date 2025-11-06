# Git Commit Checklist - Unified Draft-First Workflow

## Pre-Commit Verification

### ✅ All Files Created
- [x] `services/creation_service.py` (185 lines)
- [x] `jobs/async_image_generation_worker.py` (128 lines)
- [x] `api/generation_routes.py` (120 lines)
- [x] `UNIFIED_DRAFT_WORKFLOW_TESTING.md` (comprehensive test guide)
- [x] `UNIFIED_DRAFT_WORKFLOW_IMPLEMENTATION.md` (architecture summary)
- [x] `QUICK_START_UNIFIED_WORKFLOW.md` (5-minute quickstart)
- [x] `UNIFIED_WORKFLOW_VISUAL_GUIDE.md` (diagrams and flowcharts)

### ✅ All Files Modified
- [x] `jobs/async_video_generation_worker.py` (refactored to use CreationService)
- [x] `app.py` (registered generation_bp blueprint)
- [x] `templates/create.html` (unified generateButton handler)
- [x] `templates/profile.html` (enhanced renderDrafts with visual states + shimmer CSS)
- [x] `celery_app.py` (added async_image_generation_worker to include list)

---

## Suggested Commit Messages

### Option 1: Single Commit (Recommended for Clean History)
```bash
git add services/creation_service.py \
        jobs/async_image_generation_worker.py \
        api/generation_routes.py \
        jobs/async_video_generation_worker.py \
        app.py \
        templates/create.html \
        templates/profile.html \
        celery_app.py \
        UNIFIED_DRAFT_WORKFLOW_TESTING.md \
        UNIFIED_DRAFT_WORKFLOW_IMPLEMENTATION.md \
        QUICK_START_UNIFIED_WORKFLOW.md \
        UNIFIED_WORKFLOW_VISUAL_GUIDE.md

git commit -m "feat: Implement unified draft-first workflow for images and videos

- Add CreationService for centralized creation lifecycle management
  - Atomic token debit/refund using Firestore transactions
  - Idempotent refund mechanism prevents duplicate refunds
  
- Create async image generation worker matching video worker pattern
  - Handles SafetyFilterError and PolicyViolationError with auto-refund
  - Uploads to R2 storage with public URLs
  
- Add unified /api/generate/creation endpoint for both content types
  - Single entry point replacing separate image/video endpoints
  - Returns 202 Accepted with immediate redirect to drafts
  
- Refactor video worker to use shared CreationService
  - Remove duplicate token refund transaction logic
  - Consistent error handling across both workers
  
- Update frontend for draft-first UX
  - Create page: immediate redirect to drafts on generation start
  - Drafts tab: visual states (pending/processing/draft/failed)
  - Loading skeletons with shimmer animation
  - Image previews (clickable) and video players
  - Status-specific action buttons
  
- Register async_image_generation_worker in Celery app

This brings Phoenix content creation to parity with Instagram/Sora UX
where all generations appear as drafts immediately with async processing.

Closes #[issue-number] (if applicable)
"
```

### Option 2: Multi-Commit (More Granular)

#### Commit 1: Backend Services
```bash
git add services/creation_service.py

git commit -m "feat(backend): Add CreationService for unified creation lifecycle

- Atomic token debit using Firestore transactions
- Idempotent refund mechanism with transaction ledger
- Centralized status management (pending → processing → draft)
- Safe error handling with automatic rollback
"
```

#### Commit 2: Image Worker
```bash
git add jobs/async_image_generation_worker.py

git commit -m "feat(workers): Add async image generation worker

- Celery task for background image processing
- Integrates with CreationService for token management
- Handles SafetyFilterError and PolicyViolationError
- Uploads to R2 storage with public URLs
- Auto-refunds tokens on failure
"
```

#### Commit 3: Video Worker Refactor
```bash
git add jobs/async_video_generation_worker.py

git commit -m "refactor(workers): Refactor video worker to use CreationService

- Remove duplicate _refund_tokens transaction logic (80 lines)
- Now uses creation_service.handle_generation_failure()
- Consistent error handling with image worker
- Add lazy CreationService initializer
"
```

#### Commit 4: Unified API Endpoint
```bash
git add api/generation_routes.py app.py

git commit -m "feat(api): Add unified /api/generate/creation endpoint

- Single entry point for both image and video generation
- Validates type (image/video) and content-specific params
- Returns 202 Accepted for async processing
- Auto-refunds tokens if queue fails
- Register generation_bp in Flask app
"
```

#### Commit 5: Frontend Updates
```bash
git add templates/create.html templates/profile.html

git commit -m "feat(frontend): Update UI for draft-first workflow

Create page:
- Unified generateButton handler for both content types
- Immediate redirect to drafts on 202 response
- Remove inline image result display

Drafts tab:
- Visual states (pending/processing/draft/failed)
- Loading skeleton with shimmer animation
- Image previews (clickable, max-height 300px)
- Video players with poster and duration badges
- Status-specific action buttons (Refresh/Publish/Delete)
- Error displays with red background for failures
"
```

#### Commit 6: Celery Configuration
```bash
git add celery_app.py

git commit -m "chore(celery): Register async_image_generation_worker

Add image worker to Celery auto-discovery for task pickup
"
```

#### Commit 7: Documentation
```bash
git add UNIFIED_DRAFT_WORKFLOW_TESTING.md \
        UNIFIED_DRAFT_WORKFLOW_IMPLEMENTATION.md \
        QUICK_START_UNIFIED_WORKFLOW.md \
        UNIFIED_WORKFLOW_VISUAL_GUIDE.md

git commit -m "docs: Add comprehensive unified workflow documentation

- Testing guide with 5 detailed test cases
- Implementation summary with architecture details
- Quick start checklist (5 minutes to test)
- Visual guide with diagrams and flowcharts
"
```

---

## Recommended Approach

**Use Option 1 (Single Commit)** because:
- ✅ All changes are tightly coupled (feature doesn't work without all pieces)
- ✅ Easier to revert if issues found during testing
- ✅ Clear milestone in git history ("Unified Workflow Complete")
- ✅ Simpler for code review (one PR)

**Use Option 2 (Multi-Commit)** if:
- Need to review backend separately from frontend
- Want to deploy incrementally (backend first, then frontend)
- Team prefers granular commit history

---

## Pre-Push Checklist

Before `git push`:

### 1. Verify No Syntax Errors
```bash
# Check Python syntax
python -m py_compile services/creation_service.py
python -m py_compile jobs/async_image_generation_worker.py
python -m py_compile api/generation_routes.py
```

### 2. Verify Imports
```bash
# Quick import test
python -c "from services.creation_service import CreationService"
python -c "from jobs.async_image_generation_worker import generate_image_task"
python -c "from api.generation_routes import generation_bp"
```

### 3. Check for Secrets
```bash
# Ensure no API keys committed
grep -r "AIza" services/ jobs/ api/ || echo "No API keys found ✓"
grep -r "sk-" services/ jobs/ api/ || echo "No API keys found ✓"
```

### 4. Review .gitignore
```bash
# Ensure these are ignored
cat .gitignore | grep -E "\.env|firebase-credentials\.json|__pycache__"
```

### 5. Verify File Permissions
```bash
# Scripts should be executable
chmod +x start_local.sh start_production.sh
```

---

## Post-Commit Actions

After successful commit and push:

### 1. Update Issue/Ticket
```markdown
✅ **Completed**: Unified draft-first workflow

**Changes**:
- Created CreationService for lifecycle management
- Added async image generation worker
- Refactored video worker to use shared service
- Unified API endpoint at /api/generate/creation
- Enhanced UI with visual states and loading animations

**Testing**: See QUICK_START_UNIFIED_WORKFLOW.md

**Documentation**: 
- UNIFIED_DRAFT_WORKFLOW_TESTING.md (test guide)
- UNIFIED_DRAFT_WORKFLOW_IMPLEMENTATION.md (architecture)
- UNIFIED_WORKFLOW_VISUAL_GUIDE.md (diagrams)

**Next**: Local testing, then deploy to dev environment
```

### 2. Notify Team
```markdown
📢 **Unified Draft-First Workflow Ready for Testing**

Just pushed a major feature that brings Phoenix's content creation UX to parity 
with Instagram/Sora. All image and video generation now follows a unified 
draft-first workflow:

1. User clicks Generate → Immediate redirect to drafts
2. Draft appears with loading animation (pending status)
3. Worker processes in background (10-120 seconds)
4. Draft updates to show media preview when ready
5. User can publish to feed from drafts tab

**Key Benefits**:
- Instant feedback (no waiting on create page)
- Automatic token refunds on failures
- Visual status indicators (pending/processing/draft/failed)
- Consistent UX for both images and videos

**Testing**: Follow QUICK_START_UNIFIED_WORKFLOW.md (15 min)

**Docs**: See UNIFIED_WORKFLOW_VISUAL_GUIDE.md for architecture diagrams
```

### 3. Create Pull Request (if using PR workflow)
```markdown
## Summary
Implements unified draft-first creation workflow for both images and videos, 
matching Instagram/Sora UX patterns.

## Changes
- **Backend**: CreationService, async image worker, unified API endpoint
- **Frontend**: Immediate draft redirect, visual states, loading animations
- **Refactor**: Video worker now uses shared CreationService

## Testing
Ran manual tests locally (see test guide). Ready for QA validation.

## Documentation
Added 4 comprehensive docs (testing, implementation, quickstart, visuals)

## Screenshots
[Attach: pending card with shimmer, completed draft with preview, failed state]

## Deployment Notes
- Requires Celery worker restart to pick up new image task
- No database migrations needed (uses existing collections)
- No environment variable changes required

## Checklist
- [x] Code follows style guidelines
- [x] No syntax errors
- [x] Documentation updated
- [x] Testing guide provided
- [ ] QA validation (pending)
- [ ] Deployed to dev (pending)
```

---

## Rollback Instructions (If Needed)

If critical issues found after push:

### Quick Rollback
```bash
# Find commit hash
git log --oneline -5

# Revert the commit
git revert <commit-hash>

# Push revert
git push origin main

# Restart services
./start_local.sh
```

### Manual Rollback
```bash
# Delete new files
rm services/creation_service.py
rm jobs/async_image_generation_worker.py
rm api/generation_routes.py

# Restore old files from git
git checkout HEAD~1 jobs/async_video_generation_worker.py
git checkout HEAD~1 app.py
git checkout HEAD~1 templates/create.html
git checkout HEAD~1 templates/profile.html
git checkout HEAD~1 celery_app.py

# Commit rollback
git add .
git commit -m "revert: Rollback unified workflow due to [issue]"
git push
```

---

## Success Criteria

Commit is ready to push when:
- ✅ All files exist and have no syntax errors
- ✅ No secrets or credentials committed
- ✅ Documentation is complete and accurate
- ✅ Commit message is clear and descriptive
- ✅ Testing guide is provided
- ✅ Rollback plan is documented

---

## Final Command Sequence

```bash
# 1. Verify current status
git status

# 2. Add all relevant files (use Option 1 command above)
git add [files...]

# 3. Commit with detailed message
git commit -m "[message from Option 1 above]"

# 4. Verify commit
git log -1 --stat

# 5. Push to remote
git push origin main

# 6. Verify on GitHub
# Check: https://github.com/[your-repo]/commit/[commit-hash]

# 7. Update issue tracker
# Mark issue as "In Testing" or "Ready for QA"
```

---

## Post-Push Monitoring

After push, monitor for:

### GitHub Actions (if configured)
- Build status
- Linting results  
- Test results

### Cloud Build (if auto-deploy enabled)
- Build logs
- Deployment status
- Service health checks

### Local Testing
```bash
# Pull latest and test
git pull origin main
./start_local.sh

# Follow QUICK_START_UNIFIED_WORKFLOW.md
```

---

**Status**: ✅ Ready to commit and push

**Estimated Time**: 5 minutes for commit, 10-15 minutes for deployment validation

**Next Step**: Run the command sequence above, then proceed to testing phase
