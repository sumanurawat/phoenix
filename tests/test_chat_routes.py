import unittest
from unittest.mock import patch
from flask import session, url_for, jsonify # Import jsonify for chat route responses
from app import create_app # Import create_app from your main app file

class TestChatRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SERVER_NAME'] = 'localhost.localdomain'
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def _login_user(self):
        # Helper function to simulate a logged-in user
        with self.client.session_transaction() as sess:
            sess['id_token'] = 'test_id_token'
            sess['user_id'] = 'test_user_id'
            sess['user_email'] = 'test@example.com'

    def test_chat_message_requires_login(self):
        with self.client:
            response = self.client.post('/api/chat/message', json={'message': 'Hello'}, follow_redirects=False)
            self.assertEqual(response.status_code, 302) # Should redirect to login
            self.assertTrue(response.location.startswith(url_for('auth.login', _external=False)))

            self._login_user()
            # Mock the chat_service to avoid its internal logic, focus on route access
            with patch('api.chat_routes.chat_service') as mock_chat_service:
                # Configure the mock to return what the route expects
                mock_chat_service.start_new_chat.return_value = {'history': [], 'model_info': 'test_model'}
                mock_chat_service.process_user_message.return_value = {'history': [{'user': 'Hello', 'bot': 'Hi'}], 'model_info': 'test_model'}
                response_authed = self.client.post('/api/chat/message', json={'message': 'Hello'})
                self.assertEqual(response_authed.status_code, 200)
                # Check if the response is JSON as expected
                self.assertTrue(response_authed.is_json)
                self.assertIn('chat', response_authed.get_json())


    def test_upload_document_requires_login(self):
        with self.client:
            with open(__file__, 'rb') as f:
                response = self.client.post('/api/chat/upload-document', content_type='multipart/form-data', data={'document': (f, 'test.txt')}, follow_redirects=False) # Using __file__ as a dummy file
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.startswith(url_for('auth.login', _external=False)))

            self._login_user()
            with patch('api.chat_routes.chat_service'), patch('api.chat_routes.document_service') as mock_doc_service:
                mock_doc_service.is_supported_filetype.return_value = True
                mock_doc_service.process_document.return_value = {'id': 'doc1', 'original_filename': 'test.txt', 'text_preview': 'preview'}
                response_authed = self.client.post('/api/chat/upload-document', content_type='multipart/form-data', data={'document': (open(__file__, 'rb'), 'test.txt')})
                self.assertEqual(response_authed.status_code, 200)
                self.assertTrue(response_authed.is_json)
                self.assertIn('success', response_authed.get_json())

    def test_clear_chat_requires_login(self):
        with self.client:
            response = self.client.post('/api/chat/clear', follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.startswith(url_for('auth.login', _external=False)))

            self._login_user()
            with patch('api.chat_routes.chat_service') as mock_chat_service:
                mock_chat_service.clear_chat_history.return_value = {'history': [], 'model_info': 'test_model'}
                mock_chat_service.start_new_chat.return_value = {'history': [], 'model_info': 'test_model'} # If chat not in session
                response_authed = self.client.post('/api/chat/clear')
                self.assertEqual(response_authed.status_code, 200)
                self.assertTrue(response_authed.is_json)
                self.assertIn('chat', response_authed.get_json())

    def test_get_models_requires_login(self):
        with self.client:
            response = self.client.get('/api/chat/models', follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.startswith(url_for('auth.login', _external=False)))

            self._login_user()
            with patch('api.chat_routes.chat_service') as mock_chat_service:
                 # Ensure session["chat"]["model_info"] path exists
                mock_chat_service.start_new_chat.return_value = {'model_info': 'test_model_data'}
                response_authed = self.client.get('/api/chat/models')
                self.assertEqual(response_authed.status_code, 200)
                self.assertTrue(response_authed.is_json)
                self.assertIn('model_info', response_authed.get_json())

if __name__ == '__main__':
    unittest.main()
