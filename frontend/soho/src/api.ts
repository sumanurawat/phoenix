import { User, FeedResponse, UserProfileResponse, CommentsResponse } from './types';

const BASE_URL = '/api';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

// User API
export const userAPI = {
  getCurrentUser: () => fetchAPI<{ success: boolean; user: User }>('/users/me'),
  
  getUserByUsername: (username: string) => 
    fetchAPI<UserProfileResponse>(`/users/${username}`),
  
  getUserCreations: (username: string, limit = 20, cursor?: string) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append('cursor', cursor);
    return fetchAPI<UserProfileResponse>(`/users/${username}/creations?${params}`);
  },
};

// Feed API
export const feedAPI = {
  getExploreFeed: (limit = 20, cursor?: string) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append('cursor', cursor);
    return fetchAPI<FeedResponse>(`/feed/explore?${params}`);
  },
  
  updateCaption: (creationId: string, caption: string) =>
    fetchAPI(`/creations/${creationId}/caption`, {
      method: 'PATCH',
      body: JSON.stringify({ caption }),
    }),
  
  getComments: (creationId: string, limit = 20, startAfter?: string) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (startAfter) params.append('startAfter', startAfter);
    return fetchAPI<CommentsResponse>(`/creations/${creationId}/comments?${params}`);
  },
  
  addComment: (creationId: string, commentText: string) =>
    fetchAPI<{ success: boolean; comment: any }>(`/creations/${creationId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ commentText }),
    }),
};
