import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

/**
 * OAuth Callback Handler
 *
 * After Google OAuth completes, the backend redirects here with:
 * - token: Firebase ID token
 * - user_id: Firebase user ID
 *
 * This page exchanges these for a backend session cookie.
 */
export const OAuthCallbackPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState('');

  useEffect(() => {
    const handleOAuthCallback = async () => {
      const token = searchParams.get('token');
      const userId = searchParams.get('user_id');

      if (!token || !userId) {
        setStatus('error');
        setError('Missing authentication credentials');
        setTimeout(() => navigate('/login'), 2000);
        return;
      }

      try {
        // Exchange token for session cookie
        const response = await api.post('/api/auth/exchange-token', {
          token,
          user_id: userId
        });

        if (response.data.success) {
          setStatus('success');
          // Redirect to explore or intended destination
          setTimeout(() => {
            navigate('/explore');
          }, 500);
        } else {
          throw new Error('Failed to establish session');
        }
      } catch (err: any) {
        console.error('OAuth callback error:', err);
        setStatus('error');
        setError(err.response?.data?.error || 'Authentication failed');
        setTimeout(() => navigate('/login'), 2000);
      }
    };

    handleOAuthCallback();
  }, [searchParams, navigate]);

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
              Please wait while we set up your session
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
