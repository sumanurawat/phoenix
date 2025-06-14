# tests/test_deeplink_service.py
import unittest
from unittest.mock import patch, MagicMock

# Import the functions to be tested
# Assuming services are accessible like this. Adjust if your structure is different.
# If 'services' is not directly in PYTHONPATH for tests, this might need adjustment (e.g. sys.path manipulation or relative imports)
# For now, we assume the standard structure where the root of the project is in PYTHONPATH.
from services.deeplink_service import (
    generate_short_code,
    create_short_link,
    get_original_url,
    increment_click_count,
    get_links_for_user,
    SHORTENED_LINKS_COLLECTION # Ensure this is imported if used directly in tests
)
# Mock firestore at the module level for some functions if it's imported there directly
# For deeplink_service, firestore is imported within each function, so patching at function call time is appropriate.

class TestDeeplinkService(unittest.TestCase):

    @patch('services.deeplink_service.firestore.client')
    @patch('services.deeplink_service.uuid.uuid4') # Patch uuid.uuid4
    def test_generate_short_code_unique(self, mock_uuid, mock_firestore_client):
        # Mock Firestore responses to simulate uniqueness checks
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db

        mock_collection_ref = MagicMock()
        mock_db.collection.return_value = mock_collection_ref

        # Simulate document 'get' results: first exists, second doesn't
        mock_doc_exists = MagicMock()
        mock_doc_exists.exists = True

        mock_doc_not_exists = MagicMock()
        mock_doc_not_exists.exists = False

        # Side effect for document().get()
        # The first time generate_short_code calls doc.exists, it will be True (collision)
        # The second time, it will be False (unique)
        mock_document_ref = MagicMock()
        mock_collection_ref.document.return_value = mock_document_ref
        mock_document_ref.get.side_effect = [mock_doc_exists, mock_doc_not_exists]

        # Configure mock_uuid to return different values on subsequent calls if needed,
        # or ensure the logic being tested handles collisions correctly with same mocked hex.
        # Here, uuid is called, then its .hex attribute is accessed.
        mock_uuid.return_value.hex = 'abcdef123456' # First attempt (collides)
        # If the loop runs again, uuid.uuid4() is called again.
        # To make it generate a different code for the second attempt:
        mock_uuid_instance_1 = MagicMock()
        mock_uuid_instance_1.hex = 'abcdef123456' # Collides

        mock_uuid_instance_2 = MagicMock()
        mock_uuid_instance_2.hex = '123456abcdef' # Unique

        mock_uuid.side_effect = [mock_uuid_instance_1, mock_uuid_instance_2]

        short_code = generate_short_code()

        self.assertEqual(short_code, '123456') # Second attempt, first 6 chars
        self.assertEqual(mock_document_ref.get.call_count, 2)
        # Check that it tried to create a document with the first hex, then the second
        mock_collection_ref.document.assert_any_call('abcdef')
        mock_collection_ref.document.assert_any_call('123456')


    @patch('services.deeplink_service.firestore.client')
    @patch('services.deeplink_service.generate_short_code') # Mock internal call
    def test_create_short_link(self, mock_generate_short_code, mock_firestore_client):
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db
        mock_collection_ref = MagicMock()
        mock_db.collection.return_value = mock_collection_ref
        mock_document_ref = MagicMock()
        mock_collection_ref.document.return_value = mock_document_ref

        mock_generate_short_code.return_value = "testcd"

        original_url = "https://example.com/test"
        user_id = "user123"
        user_email = "user@example.com"

        # Need to mock firestore.SERVER_TIMESTAMP as it's used directly
        with patch('services.deeplink_service.firestore.SERVER_TIMESTAMP', 'SERVER_TIMESTAMP_MOCK'):
            short_code = create_short_link(original_url, user_id, user_email)

            self.assertEqual(short_code, "testcd")
            mock_db.collection.assert_called_once_with(SHORTENED_LINKS_COLLECTION)
            mock_collection_ref.document.assert_called_once_with("testcd")

            # Check that set was called with the correct data structure
            args, kwargs = mock_document_ref.set.call_args
            self.assertEqual(args[0]['original_url'], original_url)
            self.assertEqual(args[0]['user_id'], user_id)
            self.assertEqual(args[0]['user_email'], user_email)
            self.assertEqual(args[0]['click_count'], 0)
            self.assertEqual(args[0]['created_at'], 'SERVER_TIMESTAMP_MOCK')


    @patch('services.deeplink_service.firestore.client')
    def test_get_original_url_found(self, mock_firestore_client):
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db
        mock_collection_ref = MagicMock()
        mock_db.collection.return_value = mock_collection_ref
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {'original_url': 'https://example.com'}
        mock_collection_ref.document.return_value.get.return_value = mock_doc_snapshot

        url = get_original_url("testcd")
        self.assertEqual(url, "https://example.com")
        mock_collection_ref.document.assert_called_once_with("testcd")


    @patch('services.deeplink_service.firestore.client')
    def test_get_original_url_not_found(self, mock_firestore_client):
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db
        mock_collection_ref = MagicMock()
        mock_db.collection.return_value = mock_collection_ref
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False
        mock_collection_ref.document.return_value.get.return_value = mock_doc_snapshot

        url = get_original_url("unknown")
        self.assertIsNone(url)


    @patch('services.deeplink_service.firestore.client')
    @patch('services.deeplink_service.firestore.Increment') # Mock the Increment class
    def test_increment_click_count_success(self, mock_increment, mock_firestore_client):
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_ref.get.return_value = mock_doc_snapshot

        mock_increment_instance = MagicMock() # This is what firestore.Increment(1) returns
        mock_increment.return_value = mock_increment_instance

        result = increment_click_count("testcd")

        self.assertTrue(result)
        mock_doc_ref.update.assert_called_once_with({'click_count': mock_increment_instance})
        mock_increment.assert_called_once_with(1)


    @patch('services.deeplink_service.firestore.client')
    def test_increment_click_count_not_found(self, mock_firestore_client):
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False
        mock_doc_ref.get.return_value = mock_doc_snapshot

        result = increment_click_count("testcd_notfound") # Use a different code for clarity
        self.assertFalse(result)
        mock_doc_ref.update.assert_not_called()


    @patch('services.deeplink_service.firestore.client')
    def test_get_links_for_user(self, mock_firestore_client):
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db

        mock_query_obj = MagicMock() # This is what order_by returns
        mock_db.collection.return_value.where.return_value.order_by.return_value = mock_query_obj

        # Simulate documents returned by stream()
        doc1_data = {'original_url': 'url1', 'user_id': 'user123', 'click_count': 1, 'created_at': 'ts1'}
        doc1 = MagicMock()
        doc1.id = "code1"
        doc1.to_dict.return_value = doc1_data

        doc2_data = {'original_url': 'url2', 'user_id': 'user123', 'click_count': 5, 'created_at': 'ts2'}
        doc2 = MagicMock()
        doc2.id = "code2"
        doc2.to_dict.return_value = doc2_data

        mock_query_obj.stream.return_value = [doc1, doc2]

        # Mock firestore.Query.DESCENDING
        # This is a class attribute, so patch it where it's defined if possible,
        # or ensure its value is correctly used if it's just a constant.
        # Assuming it's used as a constant from `google.cloud.firestore.Query`
        # If it's `from firebase_admin import firestore` then `firestore.Query.DESCENDING`
        with patch('services.deeplink_service.firestore.Query') as mock_firestore_query_class:
            mock_firestore_query_class.DESCENDING = "DESC_MOCK" # Mock the constant value

            links = get_links_for_user("user123")

            self.assertEqual(len(links), 2)
            self.assertEqual(links[0]['short_code'], "code1")
            self.assertEqual(links[0]['original_url'], "url1")
            self.assertEqual(links[1]['short_code'], "code2")
            self.assertEqual(links[1]['original_url'], "url2")

            mock_db.collection.assert_called_with(SHORTENED_LINKS_COLLECTION)
            mock_db.collection.return_value.where.assert_called_with('user_id', '==', 'user123')
            mock_db.collection.return_value.where.return_value.order_by.assert_called_with('created_at', direction="DESC_MOCK")


if __name__ == '__main__':
    # This allows running the tests directly from the command line: python tests/test_deeplink_service.py
    # For more complex setups, a test runner like pytest or nose2 might be used.
    # You might need to adjust PYTHONPATH if services module is not found:
    # Example: PYTHONPATH=. python tests/test_deeplink_service.py
    unittest.main()
