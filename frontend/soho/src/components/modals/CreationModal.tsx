import { useState, useEffect, useRef, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Creation, Comment } from '../../types/creation';
import { useAuth } from '../../hooks/useAuth';
import { api, endpoints } from '../../services/api';

interface CreationModalProps {
  creation: Creation;
  isOpen: boolean;
  onClose: () => void;
}

export const CreationModal = ({ creation, isOpen, onClose }: CreationModalProps) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentText, setCommentText] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const commentInputRef = useRef<HTMLInputElement>(null);

  const normalizeComment = (comment: any): Comment => {
    if (!comment) {
      return {
        id: `${Date.now()}`,
        userId: '',
        username: 'unknown',
        text: '',
        createdAt: Date.now()
      };
    }

    const toMillis = (value: any): number => {
      if (!value) return Date.now();
      if (typeof value === 'number') return value;
      if (typeof value === 'string') {
        const parsed = Date.parse(value);
        return Number.isNaN(parsed) ? Date.now() : parsed;
      }
      if (typeof value === 'object') {
        if (typeof value.seconds === 'number') {
          const nanos = typeof value.nanoseconds === 'number' ? value.nanoseconds : 0;
          return value.seconds * 1000 + Math.floor(nanos / 1_000_000);
        }
        if (typeof value._seconds === 'number') {
          const nanos = typeof value._nanoseconds === 'number' ? value._nanoseconds : 0;
          return value._seconds * 1000 + Math.floor(nanos / 1_000_000);
        }
      }
      return Date.now();
    };

    const createdAt = toMillis(comment.createdAt);

    return {
      id: comment.commentId ?? comment.id ?? `${comment.userId || 'comment'}-${createdAt}`,
      userId: comment.userId ?? '',
      username: comment.username ?? 'unknown',
      text: comment.commentText ?? comment.text ?? '',
      createdAt,
      avatarUrl: comment.avatarUrl ?? ''
    };
  };

  useEffect(() => {
    if (isOpen) {
      fetchComments();
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  const fetchComments = async () => {
    try {
      setLoading(true);
      const response = await api.get(endpoints.comments(creation.id));
      const mapped = (response.data.comments || []).map(normalizeComment);
      setComments(mapped);
    } catch (error) {
      console.error('Failed to fetch comments:', error);
    } finally {
      setLoading(false);
    }
  };

  const goToProfile = (username: string | undefined | null) => {
    if (!username) return;
    onClose();
    navigate(`/profile/${username}`);
  };

  const handleSubmitComment = async (e: FormEvent) => {
    e.preventDefault();
    if (!commentText.trim() || submitting) return;

    try {
      setSubmitting(true);
      const response = await api.post(endpoints.postComment(creation.id), {
        commentText: commentText.trim()
      });

      // Add new comment to the list
      const newComment = normalizeComment(response.data.comment);
      setComments(prev => [newComment, ...prev]);
      setCommentText('');
      commentInputRef.current?.focus();
    } catch (error) {
      console.error('Failed to post comment:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const formatTimestamp = (timestamp: number) => {
    const safeTimestamp = Number.isFinite(timestamp) ? timestamp : Date.now();
    const now = Date.now();
    const diff = now - safeTimestamp;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-6xl h-[90vh] bg-momo-gray-900 rounded-xl overflow-hidden shadow-2xl flex"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          className="absolute top-4 right-4 z-10 p-2 bg-momo-gray-800/80 hover:bg-momo-gray-700 rounded-full transition-colors"
          onClick={onClose}
        >
          <svg className="w-6 h-6 text-momo-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Media Section */}
        <div className="flex-1 bg-black flex items-center justify-center">
          {creation.mediaType === 'video' ? (
            <video
              src={creation.mediaUrl}
              poster={creation.thumbnailUrl}
              className="max-h-full max-w-full"
              controls
              autoPlay
              loop
            />
          ) : (
            <img
              src={creation.mediaUrl}
              alt={creation.caption || creation.prompt}
              className="max-h-full max-w-full object-contain"
            />
          )}
        </div>

        {/* Details Section */}
        <div className="w-96 flex flex-col bg-momo-gray-900 border-l border-momo-gray-700">
          {/* Header */}
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              goToProfile(creation.username);
            }}
            className="flex items-center gap-3 p-4 border-b border-momo-gray-700 text-left hover:bg-momo-gray-800/60 transition-colors"
          >
            <div className="w-10 h-10 rounded-full bg-momo-purple flex items-center justify-center">
              <span className="text-sm font-semibold">
                {creation.username[0].toUpperCase()}
              </span>
            </div>
            <div>
              <p className="font-semibold">@{creation.username}</p>
              <p className="text-xs text-momo-gray-400">
                {formatTimestamp(creation.publishedAt || creation.createdAt)}
              </p>
            </div>
          </button>

          {/* Caption */}
          {creation.caption && (
            <div className="px-4 pb-4 border-b border-momo-gray-700">
              <p className="text-sm text-momo-gray-300">{creation.caption}</p>
            </div>
          )}

          {/* Comments List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="flex gap-3 animate-pulse">
                    <div className="w-8 h-8 rounded-full bg-momo-gray-700"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-3 bg-momo-gray-700 rounded w-24"></div>
                      <div className="h-3 bg-momo-gray-700 rounded w-full"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : comments.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-momo-gray-400 text-sm">No comments yet</p>
                <p className="text-momo-gray-500 text-xs mt-1">Be the first to comment</p>
              </div>
            ) : (
              comments.map(comment => {
                const initial = comment.username ? comment.username[0]?.toUpperCase() : '?';
                return (
                  <div key={comment.id} className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-momo-purple flex items-center justify-center flex-shrink-0 overflow-hidden">
                      {comment.avatarUrl ? (
                        <img
                          src={comment.avatarUrl}
                          alt={comment.username || 'User avatar'}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <span className="text-xs font-semibold">{initial}</span>
                      )}
                    </div>
                  <div className="flex-1">
                    <p className="text-sm">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          goToProfile(comment.username);
                        }}
                        className="font-semibold text-left hover:text-momo-purple transition-colors"
                      >
                        @{comment.username}
                      </button>{' '}
                      <span className="text-momo-gray-300">{comment.text}</span>
                    </p>
                    <p className="text-xs text-momo-gray-500 mt-1">
                      {formatTimestamp(comment.createdAt)}
                    </p>
                  </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Actions Bar */}
          <div className="p-4 border-t border-momo-gray-700 space-y-3">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <svg className="w-7 h-7 text-momo-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="text-sm font-semibold">{comments.length}</span>
              </div>
            </div>

            {/* Comment Input */}
            {user && (
              <form onSubmit={handleSubmitComment} className="flex gap-2">
                <input
                  ref={commentInputRef}
                  type="text"
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Add a comment..."
                  className="flex-1 bg-momo-gray-800 text-momo-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-momo-purple"
                  disabled={submitting}
                />
                <button
                  type="submit"
                  disabled={!commentText.trim() || submitting}
                  className="px-4 py-2 bg-momo-purple hover:bg-momo-purple/80 disabled:bg-momo-gray-700 disabled:text-momo-gray-500 text-white rounded-lg font-semibold text-sm transition-colors"
                >
                  {submitting ? 'Posting...' : 'Post'}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
