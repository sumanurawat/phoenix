"""
Fix duplicate username bug - Clean up sumanurawat12/sumanurawat123 issue.

This script:
1. Investigates the current state
2. Removes the incorrect username claim
3. Restores the correct username
"""
import firebase_admin
from firebase_admin import credentials, firestore
import sys

# Initialize Firebase
try:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized")
except Exception as e:
    print(f"❌ Error initializing Firebase: {e}")
    sys.exit(1)

db = firestore.client()

def investigate_user_state():
    """Check the current state of the username claims."""
    print("\n" + "="*60)
    print("INVESTIGATION: Current State")
    print("="*60)

    # Check sumanurawat12
    username12_ref = db.collection('usernames').document('sumanurawat12')
    username12_doc = username12_ref.get()

    print(f"\n1. Checking 'usernames/sumanurawat12':")
    if username12_doc.exists:
        data = username12_doc.to_dict()
        print(f"   ✅ EXISTS - Points to userId: {data.get('userId')}")
        print(f"   Claimed at: {data.get('claimedAt')}")
    else:
        print(f"   ❌ DOES NOT EXIST")

    # Check sumanurawat123
    username123_ref = db.collection('usernames').document('sumanurawat123')
    username123_doc = username123_ref.get()

    print(f"\n2. Checking 'usernames/sumanurawat123':")
    if username123_doc.exists:
        data = username123_doc.to_dict()
        print(f"   ✅ EXISTS - Points to userId: {data.get('userId')}")
        print(f"   Claimed at: {data.get('claimedAt')}")
        user_id_123 = data.get('userId')
    else:
        print(f"   ❌ DOES NOT EXIST")
        user_id_123 = None

    # If we have a user_id, check the users collection
    if username12_doc.exists and username123_doc.exists:
        user_id_12 = username12_doc.to_dict().get('userId')
        user_id_123 = username123_doc.to_dict().get('userId')

        print(f"\n3. Comparing user IDs:")
        print(f"   sumanurawat12 → {user_id_12}")
        print(f"   sumanurawat123 → {user_id_123}")

        if user_id_12 == user_id_123:
            print(f"   ⚠️  DUPLICATE: Both usernames point to the SAME user!")

            # Check the user document
            user_ref = db.collection('users').document(user_id_12)
            user_doc = user_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                print(f"\n4. Checking user document:")
                print(f"   Current username in profile: {user_data.get('username')}")
                print(f"   Email: {user_data.get('email')}")
                print(f"   usernameLower: {user_data.get('usernameLower')}")

                return {
                    'user_id': user_id_12,
                    'current_username': user_data.get('username'),
                    'username_lower': user_data.get('usernameLower'),
                    'has_duplicate': True
                }
        else:
            print(f"   ✅ Different users (no duplicate)")
            return {'has_duplicate': False}

    return None

def fix_duplicate_username(user_id, desired_username='sumanurawat12'):
    """
    Fix the duplicate username issue.

    Args:
        user_id: The Firebase user ID
        desired_username: The username to restore (default: sumanurawat12)
    """
    print("\n" + "="*60)
    print(f"FIX: Restoring username '{desired_username}'")
    print("="*60)

    desired_lower = desired_username.lower()

    # Start a batch operation
    batch = db.batch()

    # 1. Delete the wrong username claim (sumanurawat123)
    if desired_lower == 'sumanurawat12':
        wrong_username_ref = db.collection('usernames').document('sumanurawat123')
        batch.delete(wrong_username_ref)
        print(f"\n1. ✅ Queued deletion of 'usernames/sumanurawat123'")

    # 2. Ensure correct username claim exists
    correct_username_ref = db.collection('usernames').document(desired_lower)
    batch.set(correct_username_ref, {
        'userId': user_id,
        'claimedAt': firestore.SERVER_TIMESTAMP
    })
    print(f"2. ✅ Queued creation/update of 'usernames/{desired_lower}'")

    # 3. Update user document with correct username
    user_ref = db.collection('users').document(user_id)
    batch.update(user_ref, {
        'username': desired_username,
        'usernameLower': desired_lower,
        'updatedAt': firestore.SERVER_TIMESTAMP
    })
    print(f"3. ✅ Queued update of user document with username '{desired_username}'")

    # Commit the batch
    try:
        batch.commit()
        print(f"\n✅ SUCCESS: All changes committed!")
        print(f"   - Removed: sumanurawat123")
        print(f"   - Restored: {desired_username}")
        print(f"   - User {user_id} now has single username: {desired_username}")
    except Exception as e:
        print(f"\n❌ ERROR during commit: {e}")
        return False

    return True

def verify_fix():
    """Verify the fix was applied correctly."""
    print("\n" + "="*60)
    print("VERIFICATION: Post-Fix State")
    print("="*60)

    # Check sumanurawat12
    username12_ref = db.collection('usernames').document('sumanurawat12')
    username12_doc = username12_ref.get()

    print(f"\n1. 'usernames/sumanurawat12':")
    if username12_doc.exists:
        data = username12_doc.to_dict()
        print(f"   ✅ EXISTS - Points to userId: {data.get('userId')}")
    else:
        print(f"   ❌ DOES NOT EXIST (ERROR!)")

    # Check sumanurawat123 (should be gone)
    username123_ref = db.collection('usernames').document('sumanurawat123')
    username123_doc = username123_ref.get()

    print(f"\n2. 'usernames/sumanurawat123':")
    if username123_doc.exists:
        print(f"   ❌ STILL EXISTS (Fix failed!)")
    else:
        print(f"   ✅ DELETED (as expected)")

if __name__ == '__main__':
    print("\n🔧 USERNAME DUPLICATE FIX TOOL")
    print("="*60)

    # Step 1: Investigate
    state = investigate_user_state()

    if not state:
        print("\n⚠️  Could not determine current state. Exiting.")
        sys.exit(1)

    if not state.get('has_duplicate'):
        print("\n✅ No duplicate found. Nothing to fix!")
        sys.exit(0)

    # Step 2: Confirm with user
    print("\n" + "="*60)
    print("PROPOSED FIX:")
    print("="*60)
    print(f"  1. Delete 'usernames/sumanurawat123' claim")
    print(f"  2. Keep/restore 'usernames/sumanurawat12' claim")
    print(f"  3. Update user profile to show 'sumanurawat12'")
    print(f"\n  User ID: {state['user_id']}")

    response = input("\n⚠️  Proceed with fix? (yes/no): ").strip().lower()

    if response != 'yes':
        print("\n❌ Fix cancelled by user.")
        sys.exit(0)

    # Step 3: Apply fix
    success = fix_duplicate_username(
        user_id=state['user_id'],
        desired_username='sumanurawat12'
    )

    if success:
        # Step 4: Verify
        verify_fix()
        print("\n" + "="*60)
        print("✅ FIX COMPLETE!")
        print("="*60)
        print("\n📋 Next steps:")
        print("  1. The username 'sumanurawat123' is now available for others")
        print("  2. Your profile should show 'sumanurawat12'")
        print("  3. Both /soho/sumanurawat12 and your profile should work")
        print("  4. Test by visiting: http://localhost:8080/soho/sumanurawat12")
    else:
        print("\n❌ Fix failed. Check error messages above.")
        sys.exit(1)
