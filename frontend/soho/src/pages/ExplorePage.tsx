import { useState, useEffect, useCallback } from 'react';
import { feedAPI } from '../api';
import { Creation } from '../types';

export function ExplorePage() {
  const [creations, setCreations] = useState<Creation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  const loadFeed = useCallback(async (nextCursor?: string) => {
    try {
      setLoading(true);
      setError(null);
      const response = await feedAPI.getExploreFeed(20, nextCursor || undefined);
      
      if (nextCursor) {
        setCreations(prev => [...prev, ...response.creations]);
      } else {
        setCreations(response.creations);
      }
      
      setCursor(response.nextCursor);
      setHasMore(response.hasMore);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load feed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  return (
    <div className="py-6 px-4">
      <h1 className="text-3xl font-bold text-white mb-6">Explore</h1>
      
      {error && (
        <div className="bg-red-900/20 border border-red-500 text-red-200 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Masonry Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {creations.map((creation) => (
          <div key={creation.creationId} className="bg-dark-card rounded-lg overflow-hidden border border-dark-border hover:border-gray-600 transition-colors">
            {/* Media */}
            <div className="relative aspect-video bg-dark-surface">
              {creation.mediaType === 'video' ? (
                <video 
                  src={creation.mediaUrl} 
                  className="w-full h-full object-cover"
                  controls
                  preload="metadata"
                />
              ) : (
                <img 
                  src={creation.mediaUrl} 
                  alt={creation.caption || 'Creation'}
                  className="w-full h-full object-cover"
                />
              )}
            </div>

            {/* Info */}
            <div className="p-4">
              {/* User info */}
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-semibold text-sm">
                  {creation.username.charAt(0).toUpperCase()}
                </div>
                <a 
                  href={`/soho/profile/${creation.username}`}
                  className="text-sm font-semibold text-white hover:underline"
                >
                  @{creation.username}
                </a>
              </div>

              {/* Caption */}
              {creation.caption && (
                <p className="text-gray-300 text-sm mb-3 line-clamp-2">
                  {creation.caption}
                </p>
              )}

              {/* Engagement Stats */}
              <div className="flex items-center gap-4 text-gray-400 text-sm">
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  {creation.commentCount}
                </span>
                <span className="text-xs text-gray-500">
                  {new Date(creation.publishedAt).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Loading State */}
      {loading && creations.length === 0 && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* Load More */}
      {hasMore && !loading && (
        <div className="flex justify-center mt-8">
          <button
            onClick={() => loadFeed(cursor || undefined)}
            className="btn-primary"
          >
            Load More
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && creations.length === 0 && !error && (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg">No creations yet. Be the first to create!</p>
        </div>
      )}
    </div>
  );
}
