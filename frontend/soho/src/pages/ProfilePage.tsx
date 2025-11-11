import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { userAPI } from '../api';
import { Creation } from '../types';

export function ProfilePage() {
  const { username } = useParams<{ username: string }>();
  const [user, setUser] = useState<any>(null);
  const [creations, setCreations] = useState<Creation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProfile() {
      if (!username) return;
      
      try {
        setLoading(true);
        setError(null);
        const response = await userAPI.getUserCreations(username);
        setUser(response.user);
        setCreations(response.creations);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    }

    loadProfile();
  }, [username]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-6 px-4">
        <div className="bg-red-900/20 border border-red-500 text-red-200 px-4 py-3 rounded-lg">
          {error}
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="py-6 px-4 text-center">
        <p className="text-gray-400 text-lg">User not found</p>
      </div>
    );
  }

  return (
    <div className="py-6 px-4">
      {/* Profile Header */}
      <div className="bg-dark-card rounded-lg p-6 mb-6 border border-dark-border">
        <div className="flex items-start gap-6">
          {/* Avatar */}
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-3xl flex-shrink-0">
            {user.username.charAt(0).toUpperCase()}
          </div>

          {/* Info */}
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-white mb-1">
              {user.displayName || user.username}
            </h1>
            <p className="text-gray-400 mb-3">@{user.username}</p>
            
            {user.bio && (
              <p className="text-gray-300 mb-4">{user.bio}</p>
            )}

            {/* Stats */}
            <div className="flex gap-6 text-sm">
              <div>
                <span className="font-semibold text-white">{creations.length}</span>
                <span className="text-gray-400 ml-1">Creations</span>
              </div>
              <div>
                <span className="font-semibold text-white">{user.totalTokensEarned?.toLocaleString() || 0}</span>
                <span className="text-gray-400 ml-1">Tokens Earned</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Creations Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {creations.map((creation) => (
          <div key={creation.creationId} className="bg-dark-card rounded-lg overflow-hidden border border-dark-border hover:border-gray-600 transition-colors">
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

            {creation.caption && (
              <div className="p-3">
                <p className="text-gray-300 text-sm line-clamp-2">
                  {creation.caption}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Empty State */}
      {creations.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg">No creations yet</p>
        </div>
      )}
    </div>
  );
}
