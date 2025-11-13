import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Important for session cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// CSRF token management
let csrfToken: string | null = null;

export const getCsrfToken = async (): Promise<string> => {
  if (csrfToken) {
    return csrfToken;
  }
  
  try {
    const response = await axios.get(`${API_BASE_URL}/api/csrf-token`, {
      withCredentials: true,
    });
    csrfToken = response.data.csrf_token;
    if (!csrfToken) {
      throw new Error('CSRF token not received from server');
    }
    return csrfToken;
  } catch (error) {
    console.error('Failed to fetch CSRF token:', error);
    throw error;
  }
};

// Request interceptor to add CSRF token to all POST/PUT/DELETE requests
api.interceptors.request.use(
  async (config) => {
    // Add CSRF token for state-changing requests
    if (config.method && ['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
      const token = await getCsrfToken();
      config.headers['X-CSRF-Token'] = token;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle CSRF token expiration
    if (error.response?.status === 400 && error.response?.data?.error?.includes('CSRF')) {
      console.log('CSRF token expired, fetching new token...');
      csrfToken = null; // Clear cached token
      
      // Retry the request with new token
      const config = error.config;
      if (config && !config._retry) {
        config._retry = true;
        const token = await getCsrfToken();
        config.headers['X-CSRF-Token'] = token;
        return api.request(config);
      }
    }
    
    // For now, just log 401 errors without redirecting
    // The app can handle unauthenticated state gracefully
    if (error.response?.status === 401) {
      console.log('User not authenticated');
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const endpoints = {
  // Auth
  csrfToken: '/api/csrf-token',

  // Feed
  explore: '/api/feed/explore',

  // Users
  me: '/api/users/me',
  userProfile: (username: string) => `/api/users/${username}`,
  userCreations: (username: string) => `/api/users/${username}/creations`,

  // Creations
  creations: '/api/generate/creation',
  drafts: '/api/generate/drafts',
  publish: (id: string) => `/api/generate/creation/${id}/publish`,
  deleteCreation: (id: string) => `/api/generate/creation/${id}`,

  // Likes
  like: (id: string) => `/api/creations/${id}/like`,
  unlike: (id: string) => `/api/creations/${id}/like`,

  // Comments
  comments: (id: string) => `/api/creations/${id}/comments`,
  postComment: (id: string) => `/api/creations/${id}/comments`,

  // Tokens
  tokenBalance: '/api/tokens/balance',
  transactions: '/api/tokens/transactions',
  packages: '/api/tokens/packages',
  checkout: '/api/tokens/create-checkout-session',
};
