# Firestore Index Setup Instructions

## Context
The Phoenix app needs a composite index for the `creations` collection to efficiently query and sort user drafts/posts.

## Option 1: One-Click Index Creation (FASTEST - 2 minutes)

**Instructions for AI Browser Agent:**

1. **Navigate to the auto-generated URL:**
   ```
   https://console.firebase.google.com/v1/r/project/phoenix-project-386/firestore/indexes?create_composite=ClVwcm9qZWN0cy9waG9lbml4LXByb2plY3QtMzg2L2RhdGFiYXNlcy8oZGVmYXVsdCkvY29sbGVjdGlvbkdyb3Vwcy9jcmVhdGlvbnMvaW5kZXhlcy9fEAEaCgoGdXNlcklkEAEaDQoJY3JlYXRlZEF0EAIaDAoIX19uYW1lX18QAg
   ```

2. **You should see a pre-filled form with:**
   - Collection: `creations`
   - Fields to index:
     - `userId` (Ascending)
     - `createdAt` (Descending)
     - `__name__` (Descending)

3. **Click the "Create Index" button** (usually a blue/purple button)

4. **Wait for index to build** (~2-5 minutes)
   - Status will change from "Building" to "Enabled"
   - You'll see a green checkmark when ready

5. **Refresh the Phoenix app** - queries will now be faster

---

## Option 2: Manual Index Creation via Firebase Console

**Instructions for AI Browser Agent:**

1. **Navigate to Firebase Console:**
   ```
   https://console.firebase.google.com/project/phoenix-project-386/firestore/indexes
   ```

2. **Click "Create Index" or "Add Index" button**

3. **Fill in the form:**
   - **Collection ID:** `creations`
   - **Fields to index:** (Click "Add field" for each)
     1. Field path: `userId`, Order: `Ascending`
     2. Field path: `createdAt`, Order: `Descending`
   - **Query scope:** `Collection`

4. **Click "Create" button**

5. **Wait 2-5 minutes** for index to build

6. **Verify** the index shows "Enabled" status (green)

---

## Option 3: Deploy via Firebase CLI (For Developers)

We already have a `firestore.indexes.json` file. Add this index to it:

```json
{
  "indexes": [
    {
      "collectionGroup": "creations",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "userId",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "createdAt",
          "order": "DESCENDING"
        }
      ]
    }
  ]
}
```

Then run:
```bash
firebase deploy --only firestore:indexes
```

---

## Why This Index is Optional Right Now

✅ **Current Status:** The app works WITHOUT the index
- We sort creations in Python after fetching from Firestore
- Performance is acceptable for <1000 creations per user

❌ **Future Need:** The index becomes critical when:
- Users have 100+ drafts/posts (sorting 100 items in Python is slow)
- Multiple users querying simultaneously (Firestore query without index is expensive)
- You want to enable pagination (skip/offset requires ordered queries)

---

## Verification Steps

After creating the index:

1. **Check index status** in Firebase Console
   - Should show "Enabled" with green checkmark

2. **Test in Phoenix app:**
   - Go to profile → Drafts tab
   - Should load instantly (no delay)
   - Check browser DevTools → Network tab
   - `/api/generate/drafts` should return in <100ms

3. **Check server logs** (should NOT see this warning):
   ```
   Could not order by createdAt: [error]
   ```

---

## Current Implementation Note

The app currently uses **Python-based sorting** as a fallback:
- File: `api/generation_routes.py`
- Line: ~265
- Code: `creations.sort(key=lambda x: x.get('createdAt', 0), reverse=True)`

This works but is slower than Firestore-native ordering with an index.
