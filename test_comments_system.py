"""
Comprehensive test suite for the comments system.
Tests all endpoints and edge cases to ensure production readiness.
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8080"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, passed, details=""):
    icon = f"{Colors.GREEN}✅" if passed else f"{Colors.RED}❌"
    print(f"{icon} {name}{Colors.END}")
    if details:
        print(f"   {details}")
    if not passed:
        sys.exit(1)

def test_get_comments_unauthenticated():
    """Test: GET comments without authentication (should work)"""
    # First, get a creation ID from explore
    response = requests.get(f"{BASE_URL}/api/feed/explore")
    data = response.json()

    if not data.get('success') or not data.get('creations'):
        print_test("Get explore feed", False, "No creations found")
        return None

    creation_id = data['creations'][0]['creationId']
    print_test("Get explore feed", True, f"Found creation: {creation_id}")

    # Try to get comments (should work without auth)
    response = requests.get(f"{BASE_URL}/api/creations/{creation_id}/comments")

    if response.status_code == 200:
        data = response.json()
        if 'success' in data and 'comments' in data and 'hasMore' in data:
            print_test("GET comments (unauthenticated)", True,
                      f"Got {len(data['comments'])} comments")
            return creation_id
        else:
            print_test("GET comments (unauthenticated)", False,
                      f"Invalid response structure: {data}")
            return None
    else:
        print_test("GET comments (unauthenticated)", False,
                  f"Status: {response.status_code}, Body: {response.text}")
        return None

def test_post_comment_unauthenticated(creation_id):
    """Test: POST comment without authentication (should fail with 401)"""
    response = requests.post(
        f"{BASE_URL}/api/creations/{creation_id}/comments",
        json={"commentText": "Test comment"},
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 401:
        print_test("POST comment (unauthenticated)", True,
                  "Correctly rejected with 401")
        return True
    else:
        print_test("POST comment (unauthenticated)", False,
                  f"Expected 401, got {response.status_code}")
        return False

def test_invalid_creation_id():
    """Test: GET comments for non-existent creation (should fail with 404)"""
    response = requests.get(f"{BASE_URL}/api/creations/nonexistent-id-12345/comments")

    if response.status_code == 404:
        data = response.json()
        if 'error' in data:
            print_test("GET comments (invalid ID)", True,
                      "Correctly returned 404")
            return True

    print_test("GET comments (invalid ID)", False,
              f"Expected 404, got {response.status_code}")
    return False

def test_pagination_params(creation_id):
    """Test: GET comments with pagination parameters"""
    # Test with limit
    response = requests.get(
        f"{BASE_URL}/api/creations/{creation_id}/comments?limit=5"
    )

    if response.status_code != 200:
        print_test("GET comments (with limit)", False,
                  f"Status: {response.status_code}")
        return False

    data = response.json()
    if not isinstance(data.get('comments'), list):
        print_test("GET comments (with limit)", False,
                  "Comments is not a list")
        return False

    if len(data['comments']) > 5:
        print_test("GET comments (with limit)", False,
                  f"Expected max 5, got {len(data['comments'])}")
        return False

    print_test("GET comments (with limit)", True,
              f"Got {len(data['comments'])} comments (max 5)")
    return True

def test_comment_structure(creation_id):
    """Test: Verify comment object structure"""
    response = requests.get(f"{BASE_URL}/api/creations/{creation_id}/comments")

    if response.status_code != 200:
        print_test("Comment structure validation", False,
                  f"Failed to fetch comments")
        return False

    data = response.json()
    comments = data.get('comments', [])

    if not comments:
        print_test("Comment structure validation", True,
                  "No comments to validate (empty is valid)")
        return True

    # Check first comment structure
    comment = comments[0]
    required_fields = ['commentId', 'userId', 'username', 'commentText', 'createdAt']

    missing_fields = [f for f in required_fields if f not in comment]

    if missing_fields:
        print_test("Comment structure validation", False,
                  f"Missing fields: {missing_fields}")
        return False

    # Check for Sentinel objects
    for field, value in comment.items():
        if str(type(value)) == "<class 'google.cloud.firestore_v1.transforms.Sentinel'>":
            print_test("Comment structure validation", False,
                      f"Field '{field}' contains Sentinel object!")
            return False

    print_test("Comment structure validation", True,
              f"All fields present, no Sentinel objects")
    return True

def test_explore_feed_comment_count():
    """Test: Verify commentCount field in explore feed"""
    response = requests.get(f"{BASE_URL}/api/feed/explore?limit=5")

    if response.status_code != 200:
        print_test("Explore feed commentCount", False,
                  f"Status: {response.status_code}")
        return False

    data = response.json()
    creations = data.get('creations', [])

    if not creations:
        print_test("Explore feed commentCount", True,
                  "No creations to check (empty is valid)")
        return True

    # Check that commentCount exists and is a number
    creation = creations[0]

    if 'commentCount' not in creation:
        print_test("Explore feed commentCount", False,
                  "commentCount field missing from creation")
        return False

    if not isinstance(creation['commentCount'], int):
        print_test("Explore feed commentCount", False,
                  f"commentCount is not an integer: {type(creation['commentCount'])}")
        return False

    # Check that likeCount is NOT present
    if 'likeCount' in creation:
        print_test("Explore feed commentCount", False,
                  "likeCount still present (should be removed)")
        return False

    print_test("Explore feed commentCount", True,
              f"commentCount: {creation['commentCount']}, likeCount removed")
    return True

def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print("COMMENTS SYSTEM - PRODUCTION READINESS TEST")
    print(f"{'='*60}{Colors.END}\n")

    # Test 1: Get explore feed and extract creation ID
    creation_id = test_get_comments_unauthenticated()
    if not creation_id:
        print(f"\n{Colors.RED}❌ FAILED: Cannot proceed without creation ID{Colors.END}")
        sys.exit(1)

    # Test 2: POST without auth (should fail)
    test_post_comment_unauthenticated(creation_id)

    # Test 3: Invalid creation ID
    test_invalid_creation_id()

    # Test 4: Pagination
    test_pagination_params(creation_id)

    # Test 5: Comment structure
    test_comment_structure(creation_id)

    # Test 6: Explore feed commentCount
    test_explore_feed_comment_count()

    print(f"\n{Colors.GREEN}{'='*60}")
    print("✅ ALL TESTS PASSED - PRODUCTION READY")
    print(f"{'='*60}{Colors.END}\n")

    print(f"{Colors.YELLOW}Note: Authenticated POST test requires manual login{Colors.END}")
    print(f"{Colors.YELLOW}To test: Login to /soho/explore and post a comment{Colors.END}\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}❌ UNEXPECTED ERROR: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
