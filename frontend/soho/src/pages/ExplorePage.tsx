import { useState, useEffect } from 'react';
import { Layout } from '../components/layout/Layout';
import { PostCard } from '../components/feed/PostCard';
import { PostCardSkeleton } from '../components/common/PostCardSkeleton';
import { CreationModal } from '../components/modals/CreationModal';
import type { Creation } from '../types/creation';
import { api, endpoints } from '../services/api';
import { normalizeCreation } from '../utils/creationMapper';

export const ExplorePage = () => {
  const [creations, setCreations] = useState<Creation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCreation, setSelectedCreation] = useState<Creation | null>(null);

  useEffect(() => {
    const fetchCreations = async () => {
      try {
        const response = await api.get(endpoints.explore, {
          params: { limit: 20 }
        });
        const fetched = Array.isArray(response.data?.creations)
          ? response.data.creations.map((creation: Record<string, unknown>) => normalizeCreation(creation))
          : [];

        setCreations(fetched);
      } catch (err) {
        console.error('Failed to fetch creations:', err);
        setError('Failed to load creations');
      } finally {
        setLoading(false);
      }
    };

    fetchCreations();
  }, []);

  return (
    <Layout>
      <div className="max-w-lg mx-auto px-4 py-8 space-y-6">
        {/* Page Title */}
        <div className="text-center">
          <h1 className="text-3xl font-bold">Explore</h1>
          <p className="text-momo-gray-400 mt-2">
            Discover amazing creations from the community
          </p>
        </div>

        {/* Loading State */}
        {loading && (
          <>
            <PostCardSkeleton />
            <PostCardSkeleton />
            <PostCardSkeleton />
          </>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-momo-red/10 border border-momo-red/20 rounded-lg p-4 text-center">
            <p className="text-momo-red font-semibold">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-3 px-4 py-2 bg-momo-red text-white rounded-lg hover:bg-momo-red/80 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && creations.length === 0 && (
          <div className="text-center py-16">
            <svg className="w-20 h-20 mx-auto text-momo-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <p className="text-momo-gray-400 text-lg mb-2">
              No creations yet
            </p>
            <p className="text-momo-gray-500 text-sm">
              Be the first to create something amazing!
            </p>
          </div>
        )}

        {/* Posts Grid */}
        {!loading && !error && creations.length > 0 && (
          <>
            {creations.map(creation => (
              <PostCard
                key={creation.id}
                creation={creation}
                onOpenModal={setSelectedCreation}
              />
            ))}
          </>
        )}
      </div>

      {/* Creation Modal */}
      {selectedCreation && (
        <CreationModal
          creation={selectedCreation}
          isOpen={!!selectedCreation}
          onClose={() => setSelectedCreation(null)}
        />
      )}
    </Layout>
  );
};
