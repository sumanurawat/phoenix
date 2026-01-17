import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { useTokenBalance } from '../hooks/useTokenBalance';
import { useAuth } from '../hooks/useAuth';
import { api, endpoints } from '../services/api';

const extractUsername = (payload: unknown): string | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  const source = (payload as { user?: Record<string, unknown> }).user ?? payload;
  if (!source || typeof source !== 'object') {
    return null;
  }

  const raw = source as Record<string, unknown>;
  const username = raw.username;

  if (typeof username === 'string' && username.trim()) {
    return username.trim();
  }

  return null;
};

type MediaType = 'image' | 'video';

export const CreatePage = () => {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const { balance, refreshBalance, deductTokens } = useTokenBalance();
  const [prompt, setPrompt] = useState('');
  const [mediaType, setMediaType] = useState<MediaType>('image');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const COSTS = {
    image: 1,
    video: 50,
  };

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login', { state: { from: '/create' } });
    }
  }, [authLoading, user, navigate]);

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

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    const cost = mediaType === 'video' ? COSTS.video : COSTS.image;
    if (balance < cost) {
      setError(`Insufficient tokens. You need ${cost} tokens to generate a ${mediaType}.`);
      return;
    }

    try {
      setGenerating(true);
      setError(null);

      // Optimistic update: deduct tokens immediately for responsive UI
      deductTokens(cost);

      await api.post(endpoints.creations, {
        prompt: prompt.trim(),
        type: mediaType,
      });

      // Sync with server to get exact balance (in case of any discrepancy)
      refreshBalance();

      // Navigate to profile drafts tab to see the creation
      let targetUsername = user?.username;

      if (!targetUsername) {
        try {
          const selfResponse = await api.get(endpoints.me);
          const resolvedUsername = extractUsername(selfResponse.data);
          if (resolvedUsername) {
            targetUsername = resolvedUsername;
          }
        } catch (profileError) {
          if (import.meta.env.DEV) {
            console.warn('Unable to resolve username for navigation:', profileError);
          }
        }
      }

      if (targetUsername) {
        navigate(`/profile/${targetUsername}?tab=drafts`);
      } else {
        navigate('/settings?focus=username');
      }
    } catch (err: any) {
      console.error('Failed to create:', err);
      setError(err.response?.data?.error || 'Failed to start generation. Please try again.');
      // Restore correct balance from server since optimistic update was wrong
      refreshBalance();
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold">Create</h1>
          <p className="text-momo-gray-400 mt-2">
            Bring your imagination to life with AI
          </p>
        </div>

        {/* Token Balance Display */}
        <div className="bg-momo-gray-800 rounded-xl p-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <svg className="w-6 h-6 text-momo-gold" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
              <path d="M12 8.5l-3 3 3 3 3-3-3-3z" opacity="0.7"/>
            </svg>
            <span className="text-2xl font-bold text-momo-white">{balance}</span>
          </div>
          <p className="text-sm text-momo-gray-400">Available Tokens</p>
          <button
            onClick={() => navigate('/tokens')}
            className="mt-3 text-momo-purple hover:text-momo-purple/80 text-sm font-semibold"
          >
            Buy More Tokens →
          </button>
        </div>

        {/* Creation Form */}
        <div className="bg-momo-gray-800 rounded-xl p-6 space-y-6">
          {/* Media Type Selection */}
          <div>
            <label className="block text-sm font-semibold mb-3">Media Type</label>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setMediaType('image')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  mediaType === 'image'
                    ? 'border-momo-purple bg-momo-purple/10'
                    : 'border-momo-gray-700 hover:border-momo-gray-600'
                }`}
              >
                <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <div className="font-semibold">Image</div>
                <div className="text-xs text-momo-gray-400 mt-1">{COSTS.image} tokens</div>
              </button>

              <button
                onClick={() => setMediaType('video')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  mediaType === 'video'
                    ? 'border-momo-purple bg-momo-purple/10'
                    : 'border-momo-gray-700 hover:border-momo-gray-600'
                }`}
              >
                <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <div className="font-semibold">Video</div>
                <div className="text-xs text-momo-gray-400 mt-1">{COSTS.video} tokens</div>
              </button>
            </div>
          </div>

          {/* Prompt Input */}
          <div>
            <label className="block text-sm font-semibold mb-3">
              Prompt
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={
                mediaType === 'image'
                  ? 'A serene mountain landscape at sunset with vibrant colors...'
                  : 'A camera flying through a futuristic city at night...'
              }
              rows={4}
              className="w-full bg-momo-gray-700 text-momo-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-momo-purple resize-none"
              disabled={generating}
            />
            <p className="text-xs text-momo-gray-500 mt-2">
              Describe what you want to create. Be specific and descriptive for best results.
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-momo-red/10 border border-momo-red/20 rounded-lg p-3">
              <p className="text-momo-red text-sm">{error}</p>
            </div>
          )}

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={generating || !prompt.trim()}
            className="w-full py-4 bg-momo-purple hover:bg-momo-purple/80 disabled:bg-momo-gray-700 disabled:text-momo-gray-500 text-white rounded-lg font-bold text-lg transition-colors flex items-center justify-center gap-3"
          >
            {generating ? (
              <>
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Generating...</span>
              </>
            ) : (
              <>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>Generate {mediaType === 'video' ? 'Video' : 'Image'}</span>
              </>
            )}
          </button>
        </div>

        {/* Info Card */}
        <div className="bg-momo-blue/10 border border-momo-blue/20 rounded-xl p-6">
          <div className="flex gap-3">
            <svg className="w-6 h-6 text-momo-blue flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm space-y-2">
              <p className="font-semibold text-momo-blue">How it works</p>
              <ul className="text-momo-gray-300 space-y-1 list-disc list-inside">
                <li>Your creation will be saved as a draft</li>
                <li>Generation typically takes 1-3 minutes</li>
                <li>You can publish it from your profile once ready</li>
                <li>Tokens are deducted when generation starts</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};
