import { useState, useEffect } from 'react';
import { api, endpoints } from '../services/api';
import type { User } from '../types/user';

const mapUser = (payload: unknown): User | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  const raw = (payload as { user?: Record<string, unknown> }).user ?? payload;

  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const data = raw as Record<string, unknown>;
  const uid = data.firebase_uid ?? data.uid;

  // User must have a uid to be considered authenticated
  if (typeof uid !== 'string' || !uid) {
    return null;
  }

  const username = typeof data.username === 'string' && data.username.trim() !== ''
    ? data.username
    : undefined;

  return {
    uid,
    username,
    needsUsername: !username,  // Flag for users who need to set up username
    displayName: typeof data.displayName === 'string' ? data.displayName : undefined,
    bio: typeof data.bio === 'string' ? data.bio : undefined,
    profileImageUrl: typeof data.profileImageUrl === 'string' ? data.profileImageUrl : undefined,
    tokenBalance: typeof data.tokenBalance === 'number' ? data.tokenBalance : 0,
    totalTokensEarned: typeof data.totalTokensEarned === 'number' ? data.totalTokensEarned : 0,
    totalTokensPurchased: typeof data.totalTokensPurchased === 'number' ? data.totalTokensPurchased : 0,
  };
};

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const fetchUser = async () => {
      try {
        const response = await api.get(endpoints.me);
        const mappedUser = mapUser(response.data);

        if (isMounted) {
          setUser(mappedUser);
        }
      } catch (error) {
        if (isMounted) {
          setUser(null);
        }
        if (import.meta.env.DEV) {
          console.error('Failed to fetch user:', error);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchUser();

    return () => {
      isMounted = false;
    };
  }, []);

  return { user, loading };
};
