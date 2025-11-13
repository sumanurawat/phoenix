# SOHO UI Implementation Plan
## React + Vite + Tailwind CSS

**Date:** November 11, 2025
**Status:** Ready for Implementation
**Timeline:** 2-3 days (focused development)

---

## Project Structure

```
frontend/soho/
├── public/
│   └── soho-logo.svg
├── src/
│   ├── assets/
│   │   └── icons/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Avatar.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── Spinner.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Layout.tsx
│   │   │   └── Navigation.tsx
│   │   ├── feed/
│   │   │   ├── PostCard.tsx
│   │   │   ├── PostCardSkeleton.tsx
│   │   │   └── InfiniteScroll.tsx
│   │   ├── profile/
│   │   │   ├── ProfileHeader.tsx
│   │   │   ├── CreationGrid.tsx
│   │   │   └── GridItem.tsx
│   │   ├── creation/
│   │   │   ├── CreationModal.tsx
│   │   │   ├── CommentList.tsx
│   │   │   ├── CommentItem.tsx
│   │   │   └── CommentInput.tsx
│   │   ├── tokens/
│   │   │   ├── TokenBalance.tsx
│   │   │   ├── TokenPackageCard.tsx
│   │   │   └── TransactionItem.tsx
│   │   └── create/
│   │       ├── PromptInput.tsx
│   │       ├── MediaTypeSelector.tsx
│   │       └── GenerationSettings.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useTokenBalance.ts
│   │   ├── useInfiniteScroll.ts
│   │   └── useApi.ts
│   ├── pages/
│   │   ├── ExplorePage.tsx
│   │   ├── ProfilePage.tsx
│   │   ├── CreatePage.tsx
│   │   ├── TransactionsPage.tsx
│   │   └── BuyTokensPage.tsx
│   ├── services/
│   │   ├── api.ts
│   │   └── auth.ts
│   ├── types/
│   │   ├── user.ts
│   │   ├── creation.ts
│   │   ├── comment.ts
│   │   └── token.ts
│   ├── utils/
│   │   ├── formatters.ts
│   │   └── validators.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## Phase 1: Project Setup (30 minutes)

### Step 1.1: Initialize Vite + React + TypeScript

```bash
cd ~/Documents/github/phoenix/frontend
npm create vite@latest soho -- --template react-ts
cd soho
npm install
```

### Step 1.2: Install Dependencies

```bash
# Core dependencies
npm install react-router-dom

# UI & Styling
npm install tailwindcss postcss autoprefixer
npm install @headlessui/react @heroicons/react
npm install clsx tailwind-merge

# Utilities
npm install axios date-fns
npm install react-intersection-observer
npm install framer-motion

# Dev dependencies
npm install -D @types/node
```

### Step 1.3: Configure Tailwind CSS

**tailwind.config.js:**
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        soho: {
          black: '#0A0A0A',
          gray: {
            900: '#121212',
            800: '#1E1E1E',
            700: '#2A2A2A',
            600: '#3F3F3F',
            500: '#737373',
            400: '#A3A3A3',
          },
          white: '#FAFAFA',
          purple: '#8B5CF6',
          blue: '#3B82F6',
          green: '#10B981',
          red: '#EF4444',
          gold: '#F59E0B',
          like: '#FF3B5C',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['SF Mono', 'Consolas', 'monospace'],
      },
      animation: {
        'in': 'fadeIn 200ms ease-out',
        'out': 'fadeOut 150ms ease-in',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
      },
    },
  },
  plugins: [],
}
```

### Step 1.4: Environment Variables

**.env.example:**
```env
VITE_API_BASE_URL=http://localhost:8080
VITE_APP_NAME=SOHO
```

**.env:**
```env
VITE_API_BASE_URL=http://localhost:8080
VITE_APP_NAME=SOHO
```

---

## Phase 2: Core Infrastructure (1 hour)

### Step 2.1: API Service

**src/services/api.ts:**
```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Important for session cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const endpoints = {
  // Feed
  explore: '/api/feed/explore',

  // Users
  me: '/api/users/me',
  user: (username: string) => `/api/users/${username}`,
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
```

### Step 2.2: TypeScript Types

**src/types/creation.ts:**
```typescript
export interface Creation {
  id: string;
  userId: string;
  username: string;
  mediaType: 'image' | 'video';
  mediaUrl: string;
  thumbnailUrl?: string;
  prompt: string;
  caption?: string;
  status: 'pending' | 'processing' | 'draft' | 'published' | 'failed';
  aspectRatio?: string;
  duration?: number;
  likeCount: number;
  commentCount: number;
  isLiked?: boolean;
  createdAt: number;
  publishedAt?: number;
}

export interface Comment {
  id: string;
  userId: string;
  username: string;
  text: string;
  createdAt: number;
}
```

**src/types/user.ts:**
```typescript
export interface User {
  uid: string;
  username: string;
  displayName?: string;
  bio?: string;
  profileImageUrl?: string;
  tokenBalance: number;
  totalTokensEarned: number;
  totalTokensPurchased: number;
}
```

**src/types/token.ts:**
```typescript
export interface TokenPackage {
  id: string;
  name: string;
  tokens: number;
  price: number;
  priceId: string;
  bonusPercent: number;
}

export interface Transaction {
  id: string;
  type: 'purchase' | 'generation_spend' | 'generation_refund';
  amount: number;
  description: string;
  createdAt: number;
}
```

### Step 2.3: Custom Hooks

**src/hooks/useAuth.ts:**
```typescript
import { useState, useEffect } from 'react';
import { api, endpoints } from '../services/api';
import { User } from '../types/user';

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await api.get(endpoints.me);
        setUser(response.data);
      } catch (error) {
        console.error('Failed to fetch user:', error);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  return { user, loading };
};
```

**src/hooks/useTokenBalance.ts:**
```typescript
import { useState, useEffect } from 'react';
import { api, endpoints } from '../services/api';

export const useTokenBalance = () => {
  const [balance, setBalance] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  const fetchBalance = async () => {
    try {
      const response = await api.get(endpoints.tokenBalance);
      setBalance(response.data.balance);
    } catch (error) {
      console.error('Failed to fetch token balance:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBalance();
  }, []);

  const refreshBalance = () => {
    setLoading(true);
    fetchBalance();
  };

  return { balance, loading, refreshBalance };
};
```

---

## Phase 3: Layout Components (1 hour)

### Step 3.1: Header Component

**src/components/layout/Header.tsx:**
```typescript
import { Link } from 'react-router-dom';
import {
  HomeIcon,
  PlusCircleIcon,
  UserCircleIcon,
  ReceiptPercentIcon
} from '@heroicons/react/24/outline';
import { TokenBalance } from '../tokens/TokenBalance';
import { useAuth } from '../../hooks/useAuth';

export const Header = () => {
  const { user } = useAuth();

  return (
    <header className="sticky top-0 z-50 bg-soho-gray-900/80 backdrop-blur-xl border-b border-soho-gray-700">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/soho/explore" className="text-2xl font-bold text-soho-white">
          SOHO
        </Link>

        {/* Navigation */}
        <nav className="flex items-center gap-6">
          <Link
            to="/soho/explore"
            className="p-2 rounded-lg hover:bg-soho-gray-800 transition-colors"
            title="Explore"
          >
            <HomeIcon className="w-6 h-6 text-soho-white" />
          </Link>

          <Link
            to="/soho/create"
            className="p-2 rounded-lg hover:bg-soho-gray-800 transition-colors"
            title="Create"
          >
            <PlusCircleIcon className="w-7 h-7 text-soho-purple" />
          </Link>
        </nav>

        {/* User Actions */}
        <div className="flex items-center gap-4">
          <TokenBalance />

          <Link
            to="/soho/transactions"
            className="p-2 rounded-lg hover:bg-soho-gray-800 transition-colors"
            title="Transactions"
          >
            <ReceiptPercentIcon className="w-6 h-6 text-soho-white" />
          </Link>

          {user && (
            <Link
              to={`/soho/${user.username}`}
              className="w-8 h-8 rounded-full bg-soho-purple flex items-center justify-center hover:ring-2 hover:ring-soho-purple/50 transition-all"
            >
              {user.profileImageUrl ? (
                <img
                  src={user.profileImageUrl}
                  alt={user.username}
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                <span className="text-sm font-semibold text-white">
                  {user.username[0].toUpperCase()}
                </span>
              )}
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
```

### Step 3.2: Layout Component

**src/components/layout/Layout.tsx:**
```typescript
import { ReactNode } from 'react';
import { Header } from './Header';

interface LayoutProps {
  children: ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="min-h-screen bg-soho-gray-900 text-soho-white">
      <Header />
      <main className="pb-12">
        {children}
      </main>
    </div>
  );
};
```

---

## Phase 4: Feed Components (2 hours)

### Step 4.1: PostCard Component

**src/components/feed/PostCard.tsx:**
```typescript
import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  HeartIcon,
  ChatBubbleOvalLeftIcon
} from '@heroicons/react/24/outline';
import { HeartIcon as HeartSolidIcon } from '@heroicons/react/24/solid';
import { Creation } from '../../types/creation';
import { api, endpoints } from '../../services/api';

interface PostCardProps {
  creation: Creation;
  onOpenModal: (creation: Creation) => void;
}

export const PostCard = ({ creation, onOpenModal }: PostCardProps) => {
  const [isLiked, setIsLiked] = useState(creation.isLiked || false);
  const [likeCount, setLikeCount] = useState(creation.likeCount);

  const handleLike = async () => {
    const previousState = { isLiked, likeCount };

    // Optimistic update
    setIsLiked(!isLiked);
    setLikeCount(isLiked ? likeCount - 1 : likeCount + 1);

    try {
      if (isLiked) {
        await api.delete(endpoints.unlike(creation.id));
      } else {
        await api.post(endpoints.like(creation.id));
      }
    } catch (error) {
      // Rollback on error
      setIsLiked(previousState.isLiked);
      setLikeCount(previousState.likeCount);
      console.error('Failed to toggle like:', error);
    }
  };

  return (
    <article className="bg-soho-gray-800 rounded-xl overflow-hidden shadow-lg">
      {/* Header */}
      <div className="flex items-center gap-3 p-4">
        <Link
          to={`/soho/${creation.username}`}
          className="w-10 h-10 rounded-full bg-soho-purple flex items-center justify-center"
        >
          <span className="text-sm font-semibold">
            {creation.username[0].toUpperCase()}
          </span>
        </Link>
        <Link
          to={`/soho/${creation.username}`}
          className="font-semibold hover:underline"
        >
          @{creation.username}
        </Link>
      </div>

      {/* Media */}
      <div
        className="relative bg-black cursor-pointer"
        onClick={() => onOpenModal(creation)}
      >
        {creation.mediaType === 'video' ? (
          <video
            src={creation.mediaUrl}
            poster={creation.thumbnailUrl}
            className="w-full aspect-square object-cover"
            autoPlay
            muted
            loop
            playsInline
          />
        ) : (
          <img
            src={creation.mediaUrl}
            alt={creation.caption || creation.prompt}
            className="w-full aspect-square object-cover"
          />
        )}

        {creation.duration && (
          <div className="absolute bottom-2 right-2 bg-black/75 text-white text-xs px-2 py-1 rounded">
            {Math.floor(creation.duration)}s
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-4">
          <button
            onClick={handleLike}
            className="flex items-center gap-2 group"
          >
            {isLiked ? (
              <HeartSolidIcon className="w-7 h-7 text-soho-like" />
            ) : (
              <HeartIcon className="w-7 h-7 text-soho-white group-hover:text-soho-like transition-colors" />
            )}
            <span className="text-sm font-semibold">{likeCount}</span>
          </button>

          <button
            onClick={() => onOpenModal(creation)}
            className="flex items-center gap-2 group"
          >
            <ChatBubbleOvalLeftIcon className="w-7 h-7 text-soho-white group-hover:text-soho-blue transition-colors" />
            <span className="text-sm font-semibold">{creation.commentCount}</span>
          </button>
        </div>

        {/* Caption */}
        {creation.caption && (
          <p className="text-sm">
            <Link to={`/soho/${creation.username}`} className="font-semibold">
              @{creation.username}
            </Link>{' '}
            <span className="text-soho-gray-400">{creation.caption}</span>
          </p>
        )}

        {/* View comments */}
        {creation.commentCount > 0 && (
          <button
            onClick={() => onOpenModal(creation)}
            className="text-sm text-soho-gray-400 hover:text-soho-white transition-colors"
          >
            View all {creation.commentCount} comments
          </button>
        )}
      </div>
    </article>
  );
};
```

### Step 4.2: Explore Page

**src/pages/ExplorePage.tsx:**
```typescript
import { useState, useEffect } from 'react';
import { useInView } from 'react-intersection-observer';
import { Layout } from '../components/layout/Layout';
import { PostCard } from '../components/feed/PostCard';
import { PostCardSkeleton } from '../components/feed/PostCardSkeleton';
import { CreationModal } from '../components/creation/CreationModal';
import { Creation } from '../types/creation';
import { api, endpoints } from '../services/api';

export const ExplorePage = () => {
  const [creations, setCreations] = useState<Creation[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [cursor, setCursor] = useState<string | null>(null);
  const [selectedCreation, setSelectedCreation] = useState<Creation | null>(null);

  const { ref, inView } = useInView();

  const fetchCreations = async (nextCursor?: string | null) => {
    try {
      const params = new URLSearchParams();
      params.append('limit', '10');
      if (nextCursor) params.append('cursor', nextCursor);

      const response = await api.get(`${endpoints.explore}?${params}`);
      const newCreations = response.data.creations || [];

      setCreations(prev => nextCursor ? [...prev, ...newCreations] : newCreations);
      setCursor(response.data.nextCursor || null);
      setHasMore(!!response.data.nextCursor);
    } catch (error) {
      console.error('Failed to fetch creations:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCreations();
  }, []);

  useEffect(() => {
    if (inView && hasMore && !loading) {
      setLoading(true);
      fetchCreations(cursor);
    }
  }, [inView]);

  return (
    <Layout>
      <div className="max-w-lg mx-auto px-4 py-8 space-y-6">
        {loading && creations.length === 0 ? (
          <>
            <PostCardSkeleton />
            <PostCardSkeleton />
            <PostCardSkeleton />
          </>
        ) : creations.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-soho-gray-400 text-lg">
              No creations yet. Be the first to create!
            </p>
          </div>
        ) : (
          <>
            {creations.map(creation => (
              <PostCard
                key={creation.id}
                creation={creation}
                onOpenModal={setSelectedCreation}
              />
            ))}

            {hasMore && (
              <div ref={ref} className="py-4">
                <PostCardSkeleton />
              </div>
            )}
          </>
        )}
      </div>

      {selectedCreation && (
        <CreationModal
          creation={selectedCreation}
          onClose={() => setSelectedCreation(null)}
        />
      )}
    </Layout>
  );
};
```

---

## Phase 5: Token Components (1 hour)

### Step 5.1: TokenBalance Widget

**src/components/tokens/TokenBalance.tsx:**
```typescript
import { Link } from 'react-router-dom';
import { useTokenBalance } from '../../hooks/useTokenBalance';
import { SparklesIcon } from '@heroicons/react/24/solid';

export const TokenBalance = () => {
  const { balance, loading } = useTokenBalance();

  return (
    <Link
      to="/soho/tokens/buy"
      className="flex items-center gap-2 px-3 py-2 bg-soho-gray-800 hover:bg-soho-gray-700 rounded-lg transition-colors"
    >
      <SparklesIcon className="w-5 h-5 text-soho-gold" />
      <span className="font-semibold text-soho-white">
        {loading ? '...' : balance}
      </span>
    </Link>
  );
};
```

---

## Next Steps

Continue with:
1. Profile page implementation
2. Creation modal with comments
3. Create page with generation controls
4. Transaction history page
5. Buy tokens page
6. Testing and polish

This plan provides a solid foundation for building a world-class UI that honors Jony Ive's design principles while meeting all functional requirements.
