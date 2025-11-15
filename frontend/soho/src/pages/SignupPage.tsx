import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

export const SignupPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setInfo('');

    // Validation
    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);

    try {
      // Get CSRF token first
      const csrfResponse = await axios.get(`${API_BASE_URL}/api/csrf-token`, {
        withCredentials: true
      });
      const csrfToken = csrfResponse.data.csrf_token;

      // Submit signup form
      const formData = new FormData();
      formData.append('email', email);
      formData.append('password', password);
      formData.append('csrf_token', csrfToken);

      const response = await axios.post(`${API_BASE_URL}/signup`, formData, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json', // Request JSON response
        },
      });

      // Success - redirect to next URL or home
      if (response.data.success) {
        const nextUrl = searchParams.get('next') || '/explore';
        window.location.href = nextUrl; // Full page reload to establish session
      }
    } catch (err: any) {
      setLoading(false);
      
      // Check if it's an "email exists" error
      const errorMsg = err.response?.data?.error || err.message || '';
      
      if (errorMsg.includes('EMAIL_EXISTS') || errorMsg.includes('already registered')) {
        setInfo('This email is already registered. Please sign in instead.');
        // Redirect to login after 2 seconds
        setTimeout(() => {
          const nextParam = searchParams.get('next');
          navigate(`/login${nextParam ? `?next=${nextParam}` : ''}`);
        }, 2000);
      } else if (errorMsg.includes('WEAK_PASSWORD')) {
        setError('Password should be at least 6 characters.');
      } else if (errorMsg.includes('INVALID_EMAIL')) {
        setError('Please enter a valid email address.');
      } else {
        setError('Signup failed. Please try again.');
      }
    }
  };

  const handleGoogleSignup = () => {
    // Use relative URL so it goes through friedmomo.com (proxied to backend via Firebase Hosting rewrites)
    const callbackUrl = window.location.origin + '/oauth/callback';
    window.location.href = `/login/google?next=${encodeURIComponent(callbackUrl)}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-momo-black via-momo-purple/20 to-momo-black flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo and Header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-block">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent mb-2">
              MOMO
            </h1>
          </Link>
          <h2 className="text-2xl font-semibold text-momo-white mb-2">Join Momo</h2>
          <p className="text-momo-gray-300">Create your account to start generating with Momo</p>
        </div>

        {/* Signup Card */}
        <div className="bg-momo-gray-800/50 backdrop-blur-xl rounded-2xl border border-momo-gray-700 p-8">
          {info && (
            <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/50 rounded-lg text-blue-400 text-sm">
              <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {info}
            </div>
          )}

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
              <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-momo-gray-300 mb-2">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-momo-gray-900 border border-momo-gray-600 rounded-lg text-momo-white placeholder-momo-gray-500 focus:outline-none focus:ring-2 focus:ring-momo-purple focus:border-transparent"
                placeholder="you@example.com"
                required
                disabled={loading}
              />
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-momo-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-momo-gray-900 border border-momo-gray-600 rounded-lg text-momo-white placeholder-momo-gray-500 focus:outline-none focus:ring-2 focus:ring-momo-purple focus:border-transparent"
                  placeholder="At least 6 characters"
                  required
                  minLength={6}
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-momo-gray-400 hover:text-momo-white"
                >
                  {showPassword ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Confirm Password Field */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-momo-gray-300 mb-2">
                Confirm Password
              </label>
              <input
                type={showPassword ? 'text' : 'password'}
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 bg-momo-gray-900 border border-momo-gray-600 rounded-lg text-momo-white placeholder-momo-gray-500 focus:outline-none focus:ring-2 focus:ring-momo-purple focus:border-transparent"
                placeholder="Re-enter your password"
                required
                disabled={loading}
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full px-6 py-3 bg-gradient-to-r from-momo-purple to-momo-blue rounded-lg font-semibold text-white hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating account...
                </span>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-momo-gray-600"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-momo-gray-800/50 text-momo-gray-400">or</span>
            </div>
          </div>

          {/* Google Signup */}
          <button
            onClick={handleGoogleSignup}
            className="w-full px-6 py-3 bg-white hover:bg-gray-100 text-gray-900 rounded-lg font-semibold transition flex items-center justify-center gap-3"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          {/* Login Link */}
          <div className="mt-6 text-center text-sm text-momo-gray-400">
            Already have an account?{' '}
            <Link
              to={`/login${searchParams.get('next') ? `?next=${searchParams.get('next')}` : ''}`}
              className="text-momo-purple hover:text-momo-blue transition font-semibold"
            >
              Sign in
            </Link>
          </div>

          {/* Back to Home */}
          <div className="mt-4 text-center">
            <Link to="/" className="text-sm text-momo-gray-500 hover:text-momo-gray-300 transition">
              ← Back to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
