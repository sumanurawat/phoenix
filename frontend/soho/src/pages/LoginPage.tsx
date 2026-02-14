import { Link } from 'react-router-dom';

export const LoginPage = () => {
  const handleGoogleLogin = () => {
    // In development, go directly to backend; in production, use relative URL (Firebase proxy)
    const isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const backendUrl = isDev ? 'http://localhost:8080' : '';
    const callbackUrl = window.location.origin + '/oauth/callback';
    window.location.href = `${backendUrl}/login/google?next=${encodeURIComponent(callbackUrl)}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-momo-black via-momo-purple/20 to-momo-black flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo and Header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex flex-col items-center">
            <img src="/logo.png" alt="Fried Momo" className="w-16 h-16 mb-2" />
            <h1 className="text-4xl font-bold bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent mb-2">
              MOMO
            </h1>
          </Link>
          <h2 className="text-2xl font-semibold text-momo-white mb-2">Welcome Back</h2>
          <p className="text-momo-gray-300">Sign in to continue creating with Momo</p>
        </div>

        {/* Login Card */}
        <div className="bg-momo-gray-800/50 backdrop-blur-xl rounded-2xl border border-momo-gray-700 p-8">
          {/* Google Login */}
          <button
            onClick={handleGoogleLogin}
            className="w-full px-6 py-3 bg-white hover:bg-gray-100 text-gray-900 rounded-lg font-semibold transition flex items-center justify-center gap-3"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </button>

          {/* Sign Up Link */}
          <div className="mt-6 text-center text-sm text-momo-gray-400">
            Don't have an account?{' '}
            <Link
              to="/signup"
              className="text-momo-purple hover:text-momo-blue transition font-semibold"
            >
              Sign up
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
