"""Auto-fix duplicate username bug (no prompts)."""
import firebase_admin
from firebase_admin import credentials, firestore
import sys

# Initialize Firebase
try:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized\n")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

db = firestore.client()

print("🔧 FIXING USERNAME DUPLICATE...")
print("="*60)

# Check current state
print("\n📊 Current state:")
username12_doc = db.collection('usernames').document('sumanurawat12').get()
username123_doc = db.collection('usernames').document('sumanurawat123').get()

if username12_doc.exists and username123_doc.exists:
    user_id_12 = username12_doc.to_dict().get('userId')
    user_id_123 = username123_doc.to_dict().get('userId')

    print(f"  sumanurawat12 → {user_id_12}")
    print(f"  sumanurawat123 → {user_id_123}")

    if user_id_12 == user_id_123:
        print(f"  ⚠️  DUPLICATE CONFIRMED\n")

        # Apply fix
        print("🔧 Applying fix...")
        batch = db.batch()

        # Delete sumanurawat123
        batch.delete(db.collection('usernames').document('sumanurawat123'))

        # Update user document
        batch.update(db.collection('users').document(user_id_12), {
            'username': 'sumanurawat12',
            'usernameLower': 'sumanurawat12',
            'updatedAt': firestore.SERVER_TIMESTAMP
        })

        batch.commit()

        print("  ✅ Deleted: usernames/sumanurawat123")
        print("  ✅ Updated: user profile to 'sumanurawat12'")

        # Verify
        print("\n📋 Verification:")
        if not db.collection('usernames').document('sumanurawat123').get().exists:
            print("  ✅ sumanurawat123 removed")
        if db.collection('usernames').document('sumanurawat12').get().exists:
            print("  ✅ sumanurawat12 retained")

        user_doc = db.collection('users').document(user_id_12).get()
        if user_doc.exists:
            username = user_doc.to_dict().get('username')
            print(f"  ✅ User profile shows: {username}")

        print("\n" + "="*60)
        print("✅ FIX COMPLETE!")
        print("="*60)
        print("\nYour username is now: sumanurawat12")
        print("sumanurawat123 is available for others to claim")
    else:
        print("✅ No duplicate (different users)")
else:
    print("⚠️  One or both usernames don't exist")
