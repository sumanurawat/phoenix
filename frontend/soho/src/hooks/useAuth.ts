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
  const username = data.username;

  if (typeof username !== 'string' || username.trim() === '') {
    return null;
  }

  const uid = data.firebase_uid ?? data.uid;

  return {
    uid: typeof uid === 'string' && uid ? uid : username,
    username,
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
