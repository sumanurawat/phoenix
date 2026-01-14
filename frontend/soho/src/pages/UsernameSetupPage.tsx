import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';

export const UsernameSetupPage = () => {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Redirect if not authenticated or already has username
  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        navigate('/login');
      } else if (user.username && !user.needsUsername) {
        navigate('/explore');
      }
    }
  }, [user, authLoading, navigate]);

  // Debounced username availability check
  useEffect(() => {
    if (!username || username.length < 3) {
      setAvailable(null);
      setError('');
      return;
    }

    // Basic validation
    if (!/^[a-zA-Z0-9][a-zA-Z0-9._]*$/.test(username)) {
      setError('Username must start with a letter or number');
      setAvailable(false);
      return;
    }

    if (username.length > 20) {
      setError('Username must be 20 characters or less');
      setAvailable(false);
      return;
    }

    const timer = setTimeout(async () => {
      setChecking(true);
      setError('');
      try {
        const response = await api.get(`/api/users/check-username?username=${encodeURIComponent(username)}`);
        setAvailable(response.data.available);
        if (!response.data.available) {
          setError(response.data.message || 'Username is not available');
        }
      } catch (err: any) {
        setError('Failed to check availability');
        setAvailable(null);
      } finally {
        setChecking(false);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [username]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!username || username.length < 3 || !available) {
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const response = await api.post('/api/users/set-username', { username });

      if (response.data.success) {
        // Force a page reload to refresh auth state
        window.location.href = '/explore';
      } else {
        setError(response.data.error || 'Failed to set username');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Failed to set username. Please try again.';
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-momo-black via-momo-purple/20 to-momo-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-momo-purple"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-momo-black via-momo-purple/20 to-momo-black flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent mb-2">
            Welcome to Momo!
          </h1>
          <p className="text-momo-gray-300">Choose a unique username to get started</p>
        </div>

        {/* Card */}
        <div className="bg-momo-gray-800/50 backdrop-blur-xl rounded-2xl border border-momo-gray-700 p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Username Input */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-momo-gray-300 mb-2">
                Username
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-momo-gray-500">@</span>
                <input
                  type="text"
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9._]/g, ''))}
                  className="w-full pl-8 pr-10 py-3 bg-momo-gray-900 border border-momo-gray-600 rounded-lg text-momo-white placeholder-momo-gray-500 focus:outline-none focus:ring-2 focus:ring-momo-purple focus:border-transparent"
                  placeholder="yourname"
                  maxLength={20}
                  autoFocus
                  disabled={submitting}
                />
                {/* Status indicator */}
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {checking && (
                    <svg className="animate-spin h-5 w-5 text-momo-gray-400" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  {!checking && available === true && (
                    <svg className="h-5 w-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                  {!checking && available === false && (
                    <svg className="h-5 w-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                </div>
              </div>

              {/* Helper text */}
              <p className="mt-2 text-xs text-momo-gray-500">
                3-20 characters. Letters, numbers, dots, and underscores only.
              </p>

              {/* Error message */}
              {error && (
                <p className="mt-2 text-sm text-red-400">{error}</p>
              )}

              {/* Success message */}
              {available && !error && username.length >= 3 && (
                <p className="mt-2 text-sm text-green-400">Username is available!</p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={!username || username.length < 3 || !available || submitting}
              className="w-full px-6 py-3 bg-gradient-to-r from-momo-purple to-momo-blue rounded-lg font-semibold text-white hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Setting up...
                </span>
              ) : (
                'Continue'
              )}
            </button>
          </form>

          {/* Info */}
          <div className="mt-6 pt-6 border-t border-momo-gray-700">
            <p className="text-xs text-momo-gray-500 text-center">
              Your username is how others will find and mention you on Momo.
              You can change it later in settings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
