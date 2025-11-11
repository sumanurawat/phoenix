// API Types
export interface User {
  firebase_uid: string;
  username: string;
  email?: string;
  displayName?: string;
  bio?: string;
  profileImageUrl?: string;
  tokenBalance: number;
  totalTokensEarned: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface Creation {
  creationId: string;
  userId: string;
  username: string;
  caption?: string;
  prompt?: string;
  mediaUrl: string;
  mediaType: 'video' | 'image';
  aspectRatio: string;
  duration: number;
  commentCount: number;
  publishedAt: string;
}

export interface Comment {
  commentId: string;
  userId: string;
  username: string;
  avatarUrl: string;
  commentText: string;
  createdAt: string;
}

export interface ApiResponse<T> {
  success: boolean;
  error?: string;
  data?: T;
}

export interface FeedResponse {
  success: boolean;
  creations: Creation[];
  nextCursor: string | null;
  hasMore: boolean;
}

export interface UserProfileResponse {
  success: boolean;
  user: {
    username: string;
    displayName?: string;
    bio?: string;
    profileImageUrl?: string;
    totalTokensEarned: number;
  };
  creations: Creation[];
  nextCursor: string | null;
  hasMore: boolean;
  isOwnProfile?: boolean;
}

export interface CommentsResponse {
  success: boolean;
  comments: Comment[];
  hasMore: boolean;
}
