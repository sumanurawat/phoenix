import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { useTokenBalance } from '../hooks/useTokenBalance';
import { useAuth } from '../hooks/useAuth';
import type { TokenPackage } from '../types/token';
import { api, endpoints } from '../services/api';

export const TokensPage = () => {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const { balance, loading: balanceLoading } = useTokenBalance();
  const [packages, setPackages] = useState<TokenPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purchasing, setPurchasing] = useState<string | null>(null);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login', { state: { from: '/tokens' } });
    }
  }, [authLoading, user, navigate]);

  useEffect(() => {
    // Only fetch packages if user is authenticated
    if (user) {
      fetchPackages();
    }
  }, [user]);

  const fetchPackages = async () => {
    try {
      const response = await api.get(endpoints.packages);
      setPackages(response.data.packages || []);
    } catch (err) {
      console.error('Failed to fetch packages:', err);
      setError('Failed to load token packages');
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async (pkg: TokenPackage) => {
    try {
      setPurchasing(pkg.id);
      const response = await api.post(endpoints.checkout, {
        package: pkg.id,
      });

      // Redirect to Stripe checkout
      window.location.href = response.data.url;
    } catch (err: any) {
      console.error('Failed to create checkout:', err);
      alert(err.response?.data?.error || 'Failed to start checkout process');
      setPurchasing(null);
    }
  };

  // Show loading while checking auth
  if (authLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-momo-purple"></div>
        </div>
      </Layout>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!user) {
    return null;
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold">Token Balance</h1>
          <p className="text-momo-gray-400 mt-2">
            Buy tokens to create amazing AI-generated content
          </p>
        </div>

        {/* Current Balance */}
        <div className="bg-gradient-to-br from-momo-purple to-momo-blue rounded-xl p-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <svg className="w-10 h-10 text-momo-gold" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
              <path d="M12 8.5l-3 3 3 3 3-3-3-3z" opacity="0.7"/>
            </svg>
            <span className="text-5xl font-bold text-white">
              {balanceLoading ? '...' : balance}
            </span>
          </div>
          <p className="text-white/80 text-lg">Available Tokens</p>
        </div>

        {/* Token Usage Info */}
        <div className="bg-momo-gray-800 rounded-xl p-6">
          <h2 className="text-xl font-bold mb-4">Token Usage</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-momo-purple/20 flex items-center justify-center">
                <svg className="w-6 h-6 text-momo-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="font-semibold">Image Generation</p>
                <p className="text-momo-gray-400 text-sm">1 token per image</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-momo-blue/20 flex items-center justify-center">
                <svg className="w-6 h-6 text-momo-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="font-semibold">Video Generation</p>
                <p className="text-momo-gray-400 text-sm">50 tokens per video</p>
              </div>
            </div>
          </div>
        </div>

        {/* Token Packages */}
        <div>
          <h2 className="text-2xl font-bold mb-6">Buy Tokens</h2>

          {/* Loading State */}
          {loading && (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="bg-momo-gray-800 rounded-xl p-6 animate-pulse flex items-center justify-between">
                  <div className="flex-1 space-y-3">
                    <div className="h-6 bg-momo-gray-700 rounded w-1/4"></div>
                    <div className="h-8 bg-momo-gray-700 rounded w-1/3"></div>
                    <div className="h-4 bg-momo-gray-700 rounded w-1/2"></div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="h-10 bg-momo-gray-700 rounded w-20"></div>
                    <div className="h-10 bg-momo-gray-700 rounded w-24"></div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="bg-momo-red/10 border border-momo-red/20 rounded-lg p-4 text-center">
              <p className="text-momo-red font-semibold">{error}</p>
            </div>
          )}

          {/* Packages List */}
          {!loading && !error && (
            <div className="space-y-4">
              {packages.map((pkg) => (
                <div
                  key={pkg.id}
                  className={`bg-momo-gray-800 rounded-xl p-6 border-2 transition-all flex items-center justify-between ${
                    pkg.badge
                      ? 'border-momo-gold shadow-lg shadow-momo-gold/20'
                      : 'border-momo-gray-700'
                  }`}
                >
                  {/* Left Side: Package Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-bold">{pkg.name}</h3>
                      {pkg.badge && (
                        <span className="bg-momo-gold text-momo-black text-xs font-bold px-2 py-1 rounded-full">
                          {pkg.badge}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-baseline gap-3 mb-2">
                      <span className="text-3xl font-bold text-momo-gold">{pkg.tokens}</span>
                      <span className="text-momo-gray-400">tokens</span>
                      {pkg.bonus > 0 && (
                        <span className="text-sm text-momo-gold">
                          (+{pkg.bonus} bonus!)
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-4 text-sm text-momo-gray-400">
                      <span>~{pkg.tokens} images</span>
                      <span>•</span>
                      <span>~{Math.floor(pkg.tokens / 50)} videos</span>
                    </div>
                  </div>

                  {/* Right Side: Price & Button */}
                  <div className="flex items-center gap-6">
                    <div className="text-3xl font-bold text-white">
                      ${pkg.price.toFixed(0)}
                    </div>

                    <button
                      onClick={() => handlePurchase(pkg)}
                      disabled={purchasing === pkg.id}
                      className="px-6 py-3 bg-momo-purple hover:bg-momo-purple/80 disabled:bg-momo-gray-700 disabled:text-momo-gray-500 text-white rounded-lg font-semibold transition-colors whitespace-nowrap"
                    >
                      {purchasing === pkg.id ? 'Processing...' : 'Buy Now'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Info Section */}
        <div className="bg-momo-blue/10 border border-momo-blue/20 rounded-xl p-6">
          <div className="flex gap-3">
            <svg className="w-6 h-6 text-momo-blue flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm space-y-2">
              <p className="font-semibold text-momo-blue">Payment Information</p>
              <ul className="text-momo-gray-300 space-y-1 list-disc list-inside">
                <li>Secure payment powered by Stripe</li>
                <li>Tokens are added to your account instantly</li>
                <li>Tokens never expire</li>
                <li>All purchases are non-refundable</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};
