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
  avatarUrl?: string;
}
