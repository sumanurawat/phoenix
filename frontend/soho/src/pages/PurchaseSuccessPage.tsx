import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { useTokenBalance } from '../hooks/useTokenBalance';
import { useAuth } from '../hooks/useAuth';

export const PurchaseSuccessPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const { balance, loading: balanceLoading, refreshBalance } = useTokenBalance();
  const [countdown, setCountdown] = useState(5);

  const sessionId = searchParams.get('session_id');

  // Refresh token balance when page loads
  useEffect(() => {
    if (user && sessionId) {
      // Refresh balance after a short delay to ensure webhook has processed
      const timer = setTimeout(() => {
        refreshBalance();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [user, sessionId, refreshBalance]);

  // Countdown and redirect
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      navigate('/create');
    }
  }, [countdown, navigate]);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login');
    }
  }, [authLoading, user, navigate]);

  if (authLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-momo-purple"></div>
        </div>
      </Layout>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        {/* Success Icon */}
        <div className="mb-8">
          <div className="w-24 h-24 mx-auto bg-green-500/20 rounded-full flex items-center justify-center">
            <svg className="w-12 h-12 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>

        {/* Success Message */}
        <h1 className="text-3xl font-bold text-white mb-4">
          Purchase Successful!
        </h1>
        <p className="text-momo-gray-400 text-lg mb-8">
          Thank you for your purchase. Your tokens have been added to your account.
        </p>

        {/* Token Balance */}
        <div className="bg-gradient-to-br from-momo-purple to-momo-blue rounded-xl p-8 mb-8">
          <div className="flex items-center justify-center gap-3 mb-2">
            <svg className="w-10 h-10 text-momo-gold" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
              <path d="M12 8.5l-3 3 3 3 3-3-3-3z" opacity="0.7"/>
            </svg>
            <span className="text-5xl font-bold text-white">
              {balanceLoading ? '...' : balance}
            </span>
          </div>
          <p className="text-white/80 text-lg">Your Token Balance</p>
        </div>

        {/* Auto-redirect notice */}
        <p className="text-momo-gray-500 mb-6">
          Redirecting to create page in {countdown} seconds...
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            to="/create"
            className="px-8 py-3 bg-momo-purple hover:bg-momo-purple/80 text-white rounded-lg font-semibold transition-colors"
          >
            Start Creating
          </Link>
          <Link
            to="/tokens"
            className="px-8 py-3 bg-momo-gray-800 hover:bg-momo-gray-700 text-white rounded-lg font-semibold transition-colors"
          >
            Buy More Tokens
          </Link>
        </div>

        {/* Transaction Info */}
        {sessionId && (
          <div className="mt-8 p-4 bg-momo-gray-800/50 rounded-lg">
            <p className="text-xs text-momo-gray-500">
              Transaction ID: {sessionId.slice(0, 20)}...
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};
