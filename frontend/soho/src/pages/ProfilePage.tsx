import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { PostCard } from '../components/feed/PostCard';
import { DraftCard } from '../components/feed/DraftCard';
import { PostCardSkeleton } from '../components/common/PostCardSkeleton';
import { CreationModal } from '../components/modals/CreationModal';
import { DraftModal } from '../components/modals/DraftModal';
import type { Creation } from '../types/creation';
import { api, endpoints } from '../services/api';
import { normalizeCreation } from '../utils/creationMapper';

type ProfileSummary = {
  username: string;
  displayName?: string;
  bio?: string;
  profileImageUrl?: string;
  totalTokensEarned: number;
  tokenBalance?: number;
  totalTokensPurchased?: number;
};

export const ProfilePage = () => {
  const { username: routeUsername } = useParams<{ username?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const profileUsername = routeUsername && routeUsername !== 'undefined'
    ? routeUsername.trim()
    : null;
  const isUsernameMissing = !routeUsername || routeUsername === 'undefined';
  const [profile, setProfile] = useState<ProfileSummary | null>(null);
  const [creations, setCreations] = useState<Creation[]>([]);
  const [activeTab, setActiveTab] = useState<'published' | 'drafts'>('published');
  const [isOwnProfile, setIsOwnProfile] = useState(false);
  const [profileLoading, setProfileLoading] = useState(true);
  const [creationsLoading, setCreationsLoading] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [creationsError, setCreationsError] = useState<string | null>(null);
  const [selectedCreation, setSelectedCreation] = useState<Creation | null>(null);
  const [refreshCounter, setRefreshCounter] = useState(0);

  // Sync activeTab with URL query parameter
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab');
    if (tabFromUrl === 'drafts' && isOwnProfile) {
      setActiveTab('drafts');
    } else if (tabFromUrl === 'published' || !tabFromUrl) {
      setActiveTab('published');
    }
  }, [searchParams, isOwnProfile]);

  useEffect(() => {
    if (!isOwnProfile && activeTab === 'drafts') {
      setActiveTab('published');
    }
  }, [isOwnProfile, activeTab]);

  useEffect(() => {
    let isMounted = true;

    const fetchProfile = async () => {
      if (!profileUsername) {
        if (isMounted) {
          setProfile(null);
          setIsOwnProfile(false);
          setProfileError(
            isUsernameMissing ? 'Sign in to view your profile.' : 'Profile not found.'
          );
          setProfileLoading(false);
        }
        return;
      }

      try {
        setProfileLoading(true);
        setProfileError(null);

        const response = await api.get(endpoints.userProfile(profileUsername));
        const payload = response.data;

        if (!payload?.success || !payload.user) {
          throw new Error('Profile not found');
        }

        let tokenBalance: number | undefined;
        let totalTokensPurchased: number | undefined;

        if (payload.isOwnProfile) {
          try {
            const meResponse = await api.get(endpoints.me);
            const privateUser = meResponse.data?.user ?? meResponse.data;

            if (privateUser && typeof privateUser === 'object') {
              const record = privateUser as Record<string, unknown>;
              tokenBalance = typeof record.tokenBalance === 'number' ? record.tokenBalance : undefined;
              totalTokensPurchased = typeof record.totalTokensPurchased === 'number' ? record.totalTokensPurchased : undefined;
            }
          } catch (privateError) {
            if (import.meta.env.DEV) {
              console.warn('Failed to fetch private profile data:', privateError);
            }
          }
        }

        if (!isMounted) {
          return;
        }

        const publicRecord = payload.user as Record<string, unknown>;

        setProfile({
          username: typeof publicRecord.username === 'string' ? publicRecord.username : profileUsername,
          displayName: typeof publicRecord.displayName === 'string' ? publicRecord.displayName : undefined,
          bio: typeof publicRecord.bio === 'string' ? publicRecord.bio : undefined,
          profileImageUrl: typeof publicRecord.profileImageUrl === 'string' ? publicRecord.profileImageUrl : undefined,
          totalTokensEarned: typeof publicRecord.totalTokensEarned === 'number' ? publicRecord.totalTokensEarned : 0,
          tokenBalance,
          totalTokensPurchased,
        });
        setIsOwnProfile(Boolean(payload.isOwnProfile));
      } catch (err) {
        if (!isMounted) {
          return;
        }

        setProfile(null);
        setIsOwnProfile(false);
        setProfileError('Profile not found');

        if (import.meta.env.DEV) {
          console.error('Failed to fetch profile:', err);
        }
      } finally {
        if (isMounted) {
          setProfileLoading(false);
        }
      }
    };

    fetchProfile();

    return () => {
      isMounted = false;
    };
  }, [profileUsername, isUsernameMissing]);

  useEffect(() => {
    let isMounted = true;

    const fetchCreations = async () => {
      if (!profileUsername) {
        if (isMounted) {
          setCreations([]);
          setCreationsError(isUsernameMissing ? null : 'Profile not found.');
          setCreationsLoading(false);
        }
        return;
      }

      if (activeTab === 'drafts' && (profileLoading || !isOwnProfile)) {
        if (isMounted) {
          setCreations([]);
          setCreationsError(
            isOwnProfile ? null : 'Drafts are only visible to the creator.'
          );
          setCreationsLoading(false);
        }
        return;
      }

      try {
        setCreationsLoading(true);
        setCreationsError(null);

        if (activeTab === 'drafts') {
          // Get all non-published creations (pending, processing, draft, failed)
          const response = await api.get(endpoints.drafts);
          const list = Array.isArray(response.data?.creations)
            ? response.data.creations.map((item: Record<string, unknown>) =>
                normalizeCreation(item, { fallbackUsername: profile?.username ?? profileUsername })
              )
            : [];

          if (isMounted) {
            setCreations(list);
          }
          return;
        }

        const response = await api.get(endpoints.userCreations(profileUsername));
        const list = Array.isArray(response.data?.creations)
          ? response.data.creations.map((item: Record<string, unknown>) =>
              normalizeCreation(item, { fallbackUsername: profile?.username ?? profileUsername })
            )
          : [];

        if (isMounted) {
          setCreations(list);
        }
      } catch (err) {
        if (!isMounted) {
          return;
        }

        setCreations([]);
        setCreationsError('Failed to load creations');

        if (import.meta.env.DEV) {
          console.error('Failed to fetch profile creations:', err);
        }
      } finally {
        if (isMounted) {
          setCreationsLoading(false);
        }
      }
    };

    fetchCreations();

    return () => {
      isMounted = false;
    };
  }, [profileUsername, activeTab, isOwnProfile, profileLoading, profile?.username, isUsernameMissing, refreshCounter]);

  const creationsLabel = activeTab === 'drafts' ? 'drafts' : 'creations';
  const creationsCount = creationsLoading ? '…' : creations.length;
  const tokensLabel = isOwnProfile ? 'tokens' : 'tokens earned';
  const tokensValue = isOwnProfile
    ? profile?.tokenBalance ?? '—'
    : profile?.totalTokensEarned ?? 0;

  if (isUsernameMissing) {
    return (
      <Layout>
        <div className="max-w-md mx-auto px-4 py-16 text-center space-y-4">
          <h1 className="text-2xl font-bold">Sign in to view your profile</h1>
          <p className="text-momo-gray-400">
            Create an account or log in to personalize your experience and manage your creations.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="px-6 py-3 bg-momo-purple hover:bg-momo-purple/80 text-white font-semibold rounded-lg transition-colors"
          >
            Sign in
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Profile Header */}
        {profileLoading ? (
          <div className="animate-pulse space-y-4">
            <div className="flex items-center gap-6">
              <div className="w-24 h-24 rounded-full bg-momo-gray-700" />
              <div className="space-y-2 flex-1">
                <div className="h-6 bg-momo-gray-700 rounded w-48" />
                <div className="h-4 bg-momo-gray-700 rounded w-32" />
              </div>
            </div>
          </div>
        ) : profile ? (
          <div className="flex items-start gap-6">
            {/* Avatar */}
            <div className="w-24 h-24 rounded-full bg-momo-purple flex items-center justify-center text-3xl font-bold text-white">
              {profile.profileImageUrl ? (
                <img
                  src={profile.profileImageUrl}
                  alt={profile.username}
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                profile.username.charAt(0).toUpperCase()
              )}
            </div>

            {/* User Info */}
            <div className="flex-1 space-y-3">
              <div>
                <h1 className="text-2xl font-bold">@{profile.username}</h1>
                {profile.displayName && (
                  <p className="text-momo-gray-400 mt-1">{profile.displayName}</p>
                )}
              </div>

              {profile.bio && (
                <p className="text-momo-gray-300">{profile.bio}</p>
              )}

              {/* Stats */}
              <div className="flex items-center gap-6 text-sm">
                <div>
                  <span className="font-bold text-momo-white">{creationsCount}</span>
                  <span className="text-momo-gray-400 ml-1">{creationsLabel}</span>
                </div>
                <div>
                  <span className="font-bold text-momo-white">{tokensValue}</span>
                  <span className="text-momo-gray-400 ml-1">{tokensLabel}</span>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {/* Error States */}
        {profileError && !profileLoading && (
          <div className="bg-momo-red/10 border border-momo-red/20 rounded-lg p-4 text-center">
            <p className="text-momo-red font-semibold">{profileError}</p>
          </div>
        )}

        {creationsError && !creationsLoading && (
          <div className="bg-momo-red/10 border border-momo-red/20 rounded-lg p-4 text-center">
            <p className="text-momo-red font-semibold">{creationsError}</p>
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-momo-gray-700">
          <div className="flex gap-8">
            <button
              className={`pb-3 px-1 border-b-2 transition-colors ${
                activeTab === 'published'
                  ? 'border-momo-purple text-momo-white'
                  : 'border-transparent text-momo-gray-400 hover:text-momo-white'
              }`}
              onClick={() => setActiveTab('published')}
            >
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
                <span className="font-semibold">Published</span>
              </div>
            </button>

            {isOwnProfile && (
              <button
                className={`pb-3 px-1 border-b-2 transition-colors ${
                  activeTab === 'drafts'
                    ? 'border-momo-purple text-momo-white'
                    : 'border-transparent text-momo-gray-400 hover:text-momo-white'
                }`}
                onClick={() => setActiveTab('drafts')}
              >
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="font-semibold">Drafts</span>
                </div>
              </button>
            )}
          </div>
        </div>

        {/* Loading State */}
        {creationsLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <PostCardSkeleton />
            <PostCardSkeleton />
            <PostCardSkeleton />
            <PostCardSkeleton />
          </div>
        )}

        {/* Empty State */}
        {!creationsLoading && !creationsError && creations.length === 0 && (
          <div className="text-center py-16">
            <svg className="w-20 h-20 mx-auto text-momo-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="text-momo-gray-400 text-lg mb-2">
              No {activeTab === 'published' ? 'published creations' : 'drafts'} yet
            </p>
            <p className="text-momo-gray-500 text-sm">
              {activeTab === 'published'
                ? 'Create something and publish it to see it here'
                : 'Your draft creations will appear here'}
            </p>
          </div>
        )}

        {/* Creations Grid */}
        {!creationsLoading && !creationsError && creations.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {creations.map((creation) => (
              activeTab === 'drafts' ? (
                <DraftCard
                  key={creation.id}
                  creation={creation}
                  onOpenModal={setSelectedCreation}
                />
              ) : (
                <PostCard
                  key={creation.id}
                  creation={creation}
                  onOpenModal={setSelectedCreation}
                />
              )
            ))}
          </div>
        )}
      </div>

            {/* Creation/Draft Modal */}
      {selectedCreation && (
        activeTab === 'drafts' ? (
          <DraftModal
            creation={selectedCreation}
            isOpen={!!selectedCreation}
            onClose={() => setSelectedCreation(null)}
            onPublished={() => {
              setSelectedCreation(null);
              setRefreshCounter((value) => value + 1);
            }}
          />
        ) : (
          <CreationModal
            creation={selectedCreation}
            isOpen={!!selectedCreation}
            onClose={() => setSelectedCreation(null)}
          />
        )
      )}
    </Layout>
  );
};
