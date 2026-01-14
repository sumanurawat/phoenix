import { useNavigate } from 'react-router-dom';
import type { Creation } from '../../types/creation';

interface PostCardProps {
  creation: Creation;
  onOpenModal?: (creation: Creation) => void;
}

/**
 * PostCard - Displays a published creation in the feed
 *
 * Structure:
 * - Header: User avatar + username (clickable → profile)
 * - Media: Video (autoplays muted) or Image
 * - Duration badge: Only shown for videos (bottom-right corner)
 * - Actions: Comment button + count
 * - Caption: Username + caption text
 * - Comments link: Opens modal to view comments
 */
export const PostCard = ({ creation, onOpenModal }: PostCardProps) => {
  const navigate = useNavigate();

  const handleUsernameClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/profile/${creation.username}`);
  };

  return (
    <article className="bg-momo-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition-shadow">
      {/* Header */}
      <div className="flex items-center gap-3 p-4">
        <button
          onClick={handleUsernameClick}
          className="w-10 h-10 rounded-full bg-momo-purple flex items-center justify-center hover:ring-2 hover:ring-momo-purple/50 transition-all"
        >
          <span className="text-sm font-semibold">
            {creation.username[0].toUpperCase()}
          </span>
        </button>
        <button
          onClick={handleUsernameClick}
          className="font-semibold hover:underline text-left hover:text-momo-purple transition-colors"
        >
          @{creation.username}
        </button>
      </div>

      {/* Media */}
      <div
        className="relative bg-black cursor-pointer"
        onClick={() => onOpenModal?.(creation)}
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

        {/* Duration badge - only shown for videos, not images */}
        {creation.mediaType === 'video' && creation.duration && (
          <div className="absolute bottom-2 right-2 bg-black/75 text-white text-xs px-2 py-1 rounded">
            {Math.floor(creation.duration)}s
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-4">
          <button
            onClick={() => onOpenModal?.(creation)}
            className="flex items-center gap-2 group"
          >
            <svg className="w-7 h-7 text-momo-white group-hover:text-momo-blue transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span className="text-sm font-semibold">{creation.commentCount}</span>
          </button>
        </div>

        {/* Caption */}
        {creation.caption && (
          <p className="text-sm">
            <span className="font-semibold">@{creation.username}</span>{' '}
            <span className="text-momo-gray-400">{creation.caption}</span>
          </p>
        )}

        {/* View comments */}
        {creation.commentCount > 0 && (
          <button
            onClick={() => onOpenModal?.(creation)}
            className="text-sm text-momo-gray-400 hover:text-momo-white transition-colors"
          >
            View all {creation.commentCount} comments
          </button>
        )}
      </div>
    </article>
  );
};
