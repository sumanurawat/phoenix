import unittest
from unittest.mock import patch, MagicMock
from flask import session, url_for
from app import create_app # Import create_app from your main app file

class TestAuthRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for simpler testing if forms are involved
        self.app.config['SERVER_NAME'] = 'localhost.localdomain' # Required for url_for to work with _external=True or without app_context
        self.client = self.app.test_client()

        # Establish an application context before running the tests.
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('services.auth_service.AuthService.login_email_password')
    def test_login_redirects_to_profile(self, mock_login_email_password):
        # Mock the auth_service call to simulate successful login
        mock_login_email_password.return_value = {
            'idToken': 'test_id_token',
            'email': 'test@example.com',
            'localId': 'test_user_id'
        }

        with self.client:
            response = self.client.post('/login', data={
                'email': 'test@example.com',
                'password': 'password'
            }, follow_redirects=False) # Important: Don't follow redirects yet to check the first redirect location

            # Check that it redirects
            self.assertEqual(response.status_code, 302)
            # Check that the redirection location is the profile page
            # Ensure the profile URL is correctly generated
            expected_redirect_url = url_for('auth.profile', _external=False)
            self.assertEqual(response.location, expected_redirect_url)

            # Now test with follow_redirects=True to ensure the profile page loads
            response_followed = self.client.post('/login', data={
                'email': 'test@example.com',
                'password': 'password'
            }, follow_redirects=True)
            self.assertEqual(response_followed.status_code, 200)
            # You might want to check for some content on the profile page
            self.assertIn(b'Profile', response_followed.data) # Assuming 'Profile' is in the title or body

    @patch('services.auth_service.AuthService.signup_email_password')
    def test_signup_redirects_to_profile(self, mock_signup_email_password):
        # Mock the auth_service call to simulate successful signup
        mock_signup_email_password.return_value = {
            'idToken': 'test_id_token',
            'email': 'newuser@example.com',
            'localId': 'new_user_id'
        }

        with self.client:
            response = self.client.post('/signup', data={
                'email': 'newuser@example.com',
                'password': 'newpassword'
            }, follow_redirects=False)

            self.assertEqual(response.status_code, 302)
            expected_redirect_url = url_for('auth.profile', _external=False)
            self.assertEqual(response.location, expected_redirect_url)

            # Test with follow_redirects=True
            response_followed = self.client.post('/signup', data={
                'email': 'newuser@example.com',
                'password': 'newpassword'
            }, follow_redirects=True)
            self.assertEqual(response_followed.status_code, 200)
            self.assertIn(b'Profile', response_followed.data)

if __name__ == '__main__':
    unittest.main()
