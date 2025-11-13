import type { Creation } from '../../types/creation';

interface DraftCardProps {
  creation: Creation;
  onOpenModal?: (creation: Creation) => void;
}

export const DraftCard = ({ creation, onOpenModal }: DraftCardProps) => {
  const getStatusDisplay = () => {
    switch (creation.status) {
      case 'pending':
        return {
          badge: 'Pending',
          icon: '⏳',
          bg: 'bg-yellow-500/20',
          border: 'border-yellow-500/40',
          text: 'text-yellow-400',
        };
      case 'processing':
        return {
          badge: 'Processing',
          icon: '⚙️',
          bg: 'bg-blue-500/20',
          border: 'border-blue-500/40',
          text: 'text-blue-400',
        };
      case 'draft':
        return {
          badge: 'Ready',
          icon: '✅',
          bg: 'bg-green-500/20',
          border: 'border-green-500/40',
          text: 'text-green-400',
        };
      case 'failed':
        return {
          badge: 'Failed',
          icon: '❌',
          bg: 'bg-red-500/20',
          border: 'border-red-500/40',
          text: 'text-red-400',
        };
      default:
        return {
          badge: 'Unknown',
          icon: '❓',
          bg: 'bg-gray-500/20',
          border: 'border-gray-500/40',
          text: 'text-gray-400',
        };
    }
  };

  const status = getStatusDisplay();
  const isGenerating = creation.status === 'pending' || creation.status === 'processing';

  return (
    <article
      className="bg-momo-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition-shadow cursor-pointer"
      onClick={() => onOpenModal?.(creation)}
    >
      {/* Header */}
      <div className="flex items-center gap-3 p-4">
        <div className="w-10 h-10 rounded-full bg-momo-purple flex items-center justify-center">
          <span className="text-sm font-semibold">
            {creation.username[0].toUpperCase()}
          </span>
        </div>
        <span className="font-semibold">@{creation.username}</span>
      </div>

      {/* Media or Loading State */}
      <div className="relative bg-black aspect-square">
        {isGenerating ? (
          // Loading state with shimmer
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-r from-momo-gray-700 via-momo-gray-600 to-momo-gray-700 bg-[length:200%_100%] animate-shimmer">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-momo-purple mx-auto mb-3"></div>
              <div className="text-sm text-momo-gray-400">
                {creation.status === 'processing' ? 'Processing...' : 'Pending...'}
              </div>
            </div>
          </div>
        ) : creation.status === 'failed' ? (
          // Error state
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-red-900/20 to-red-800/10">
            <div className="text-center p-4">
              <div className="text-5xl mb-3">❌</div>
              <div className="text-sm font-semibold text-red-400">Generation Failed</div>
            </div>
          </div>
        ) : creation.mediaUrl ? (
          // Show media thumbnail
          creation.mediaType === 'video' ? (
            <video
              src={creation.mediaUrl}
              poster={creation.thumbnailUrl}
              className="w-full h-full object-cover"
              muted
              preload="metadata"
            />
          ) : (
            <img
              src={creation.mediaUrl}
              alt="Draft"
              className="w-full h-full object-cover"
            />
          )
        ) : null}

        {/* Status Badge */}
        <div className={`absolute top-3 left-3 ${status.bg} ${status.border} border backdrop-blur-sm px-3 py-1.5 rounded-lg flex items-center gap-2`}>
          <span className="text-base">{status.icon}</span>
          <span className={`text-xs font-semibold ${status.text}`}>{status.badge}</span>
        </div>

        {/* Duration badge for videos */}
        {creation.duration && creation.mediaUrl && (
          <div className="absolute bottom-2 right-2 bg-black/75 text-white text-xs px-2 py-1 rounded">
            {Math.floor(creation.duration)}s
          </div>
        )}
      </div>

      {/* Footer - Only show for ready drafts */}
      {creation.status === 'draft' && (
        <div className="p-4">
          <p className="text-sm text-momo-gray-400 line-clamp-2">
            {creation.caption || 'No caption yet - click to add one and publish'}
          </p>
        </div>
      )}
    </article>
  );
};
