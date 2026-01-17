# AI Agent Instructions for Friedmomo/Phoenix Codebase

> **For all AI assistants (Claude, GPT, Copilot, Cursor, etc.)**

This document contains critical guidelines for any AI agent working on this codebase.
**Read this file before making changes to ensure consistency and completeness.**

---

## Critical: Account Deletion & Artifact Cleanup

### The Golden Rule

> **Every feature that creates user data MUST have a corresponding cleanup in the account deletion service.**

When you add any new feature that:
- Creates Firestore documents/collections with user data
- Stores files in cloud storage (R2, GCS)
- Creates records in external services (Stripe, etc.)
- Adds subcollections to existing documents

**You MUST also update:**
1. `services/account_deletion_service.py` - Add deletion logic
2. `scripts/delete_account.py` - Update preview counts (if applicable)

### Current Artifact Registry

The account deletion service (`services/account_deletion_service.py`) handles these artifacts:

#### Firestore Collections (User-Specific)
| Collection | User ID Field | Description |
|------------|---------------|-------------|
| `users` | document ID | Main user profile |
| `usernames` | `userId` | Username claims (released on deletion) |
| `creations` | `userId` | Images/videos with `comments` subcollection |
| `transactions` | `userId` | Financial ledger |
| `user_subscriptions` | `firebase_uid` | Stripe subscription records |
| `user_usage` | `firebase_uid` | Daily usage tracking |
| `user_social_accounts` | `user_id` | Connected social media |
| `social_posts` | `user_id` | Synced social posts |
| `oauth_states` | `user_id` | OAuth temporary tokens |
| `cache_sessions` | `data.user_id` | Flask session cache |
| `security_alerts` | `user_id` | Rate limit events |
| `image_generations` | `user_id` | Legacy image history |

#### External Storage
| Service | Path Pattern | Description |
|---------|--------------|-------------|
| Cloudflare R2 | `{user_id}/{creation_id}/*` | Media files (images/videos) |

#### External APIs
| Service | Identifier | Description |
|---------|------------|-------------|
| Stripe | `stripe_customer_id` | Customer record (cascades to subscriptions) |
| Firebase Auth | `user_id` (UID) | Auth identity (frees email for reuse) |

### How to Add a New Feature with User Data

1. **Create the feature** with appropriate user_id field
2. **Update account_deletion_service.py:**
   ```python
   # Add a new step in delete_account() method:
   # ---------------------------------------------------------------------
   # STEP X: Delete [your_collection] records
   # ---------------------------------------------------------------------
   try:
       count = self._delete_collection_by_user_id(
           'your_collection', 'user_id', user_id
       )
       cleanup_summary['firestore']['your_collection'] = count
       logger.info(f"✅ Deleted {count} [description] records")
   except Exception as e:
       errors.append(f"Failed to delete [your_collection]: {e}")
       logger.error(f"❌ Error deleting [your_collection]: {e}")
   ```

3. **Update the docstring** at the top of account_deletion_service.py
4. **Update this file** (CLAUDE.md) with the new collection

### Deletion Service Design Principles

- **Modular**: Each artifact type has its own cleanup function
- **Idempotent**: Safe to run multiple times
- **Fail-safe**: Continues cleanup even if individual steps fail
- **Auditable**: Comprehensive logging for debugging and compliance
- **Complete**: Deletes EVERYTHING - no orphaned data

---

## Architecture Overview

### Tech Stack
- **Backend**: Flask (Python 3.11+)
- **Database**: Firestore
- **Storage**: Cloudflare R2 (S3-compatible)
- **Auth**: Firebase Auth + Flask sessions
- **Payments**: Stripe
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Deployment**: Google Cloud Run

### Key Directories
```
phoenix/
├── api/                    # Flask API routes (blueprints)
├── services/               # Business logic services
├── jobs/                   # Cloud Run background jobs
├── frontend/soho/          # React frontend (Momo)
├── scripts/                # Admin/maintenance scripts
├── config/                 # Configuration files
└── middleware/             # Flask middleware
```

### Service Naming Conventions
- Services use snake_case: `account_deletion_service.py`
- Classes use PascalCase: `AccountDeletionService`
- User ID field names: `userId` (camelCase in JS) or `user_id` (snake_case in Python)

---

## Code Quality Standards

### Python
- Use type hints
- Add docstrings to all public methods
- Use logging (not print statements)
- Handle exceptions gracefully
- Follow existing patterns in the codebase

### TypeScript/React
- Use functional components with hooks
- Type all props and state
- Use the existing design system (momo-* color classes)
- Handle loading and error states

### Commits
- Use conventional commit messages
- Include `Co-Authored-By:` trailer when AI-assisted (with appropriate AI name)

---

## Testing Checklist

Before submitting changes:
- [ ] Python syntax check: `python3 -m py_compile <file>`
- [ ] Frontend build: `cd frontend/soho && npm run build`
- [ ] If adding user data: Updated account deletion service
- [ ] If adding API endpoint: Added proper auth decorators

---

## Common Patterns

### Adding a New Firestore Collection

1. Create the service in `services/`
2. Add API routes in `api/`
3. **Add deletion logic to `services/account_deletion_service.py`**
4. Update this CLAUDE.md file

### Adding Cloud Storage

1. Use R2 with user_id prefix: `{user_id}/{resource_id}/{filename}`
2. Store the URL in Firestore document
3. **Add R2 cleanup to account deletion service**

### Adding External Service Integration

1. Store credentials/IDs in user document
2. **Add API call to delete external record in account deletion**

---

## Reference

For questions about this codebase, check:
- Existing service implementations for patterns
- This `AGENTS.md` for guidelines
- `services/account_deletion_service.py` for data model reference
