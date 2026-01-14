import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

/**
 * OAuth Callback Handler
 *
 * After Google OAuth completes, the backend redirects here.
 * The session cookie is already set by the backend - we just need to verify it works.
 */
export const OAuthCallbackPage = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState('');
  const [statusMessage, setStatusMessage] = useState('Please wait while we verify your session');

  useEffect(() => {
    const handleOAuthCallback = async () => {
      // The backend has already set the session cookie via the OAuth flow
      // We just need to verify it's working by calling /api/users/me
      try {
        setStatusMessage('Verifying your session...');

        const verifyResponse = await api.get('/api/users/me', {
          timeout: 10000
        });

        if (verifyResponse.status === 200) {
          console.log('Session verified successfully');
          setStatus('success');

          // Check if user needs to set up username
          const userData = verifyResponse.data?.user;
          const needsUsername = !userData?.username || userData.username.trim() === '';

          if (needsUsername) {
            setStatusMessage('Welcome! Setting up your profile...');
            setTimeout(() => {
              window.location.href = '/username-setup';
            }, 300);
          } else {
            setStatusMessage('Success! Redirecting...');
            setTimeout(() => {
              window.location.href = '/explore';
            }, 300);
          }
          return;
        }
      } catch (err: any) {
        console.error('OAuth callback verification error:', err);

        // Session verification failed
        setStatus('error');
        const errorMsg = err.response?.status === 401
          ? 'Session not established. Please try logging in again.'
          : err.response?.data?.error || 'Authentication verification failed';
        setError(errorMsg);
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    handleOAuthCallback();
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-momo-black via-momo-purple/20 to-momo-black flex items-center justify-center px-4">
      <div className="text-center">
        {status === 'processing' && (
          <>
            <div className="mb-6">
              <svg
                className="animate-spin h-12 w-12 text-momo-purple mx-auto"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-momo-white mb-2">
              Completing Sign In...
            </h2>
            <p className="text-momo-gray-400">
              {statusMessage}
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="mb-6">
              <svg
                className="h-12 w-12 text-green-500 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-momo-white mb-2">
              Success!
            </h2>
            <p className="text-momo-gray-400">Redirecting you now...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="mb-6">
              <svg
                className="h-12 w-12 text-red-500 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-momo-white mb-2">
              Authentication Failed
            </h2>
            <p className="text-red-400 mb-4">{error}</p>
            <p className="text-momo-gray-400">Redirecting to login...</p>
          </>
        )}
      </div>
    </div>
  );
};
