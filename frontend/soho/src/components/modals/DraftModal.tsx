import { useState, useEffect } from 'react';
import type { Creation } from '../../types/creation';
import { api, endpoints } from '../../services/api';

interface DraftModalProps {
  creation: Creation;
  isOpen: boolean;
  onClose: () => void;
  onPublished?: () => void;
}

export const DraftModal = ({ creation, isOpen, onClose, onPublished }: DraftModalProps) => {
  const [caption, setCaption] = useState(creation.caption || '');
  const [publishing, setPublishing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setCaption(creation.caption || '');
      setError(null);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, creation.caption]);

  if (!isOpen) return null;

  const isDraft = creation.status === 'draft';
  const isPending = creation.status === 'pending' || creation.status === 'processing';
  const isFailed = creation.status === 'failed';

  const handlePublish = async () => {
    if (!isDraft) return;

    try {
      setPublishing(true);
      setError(null);

      await api.post(endpoints.publish(creation.id), {
        caption: caption.trim() || undefined,
      });

      onPublished?.();
      onClose();
    } catch (err: any) {
      console.error('Failed to publish:', err);
      setError(err.response?.data?.error || 'Failed to publish. Please try again.');
    } finally {
      setPublishing(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this draft?')) return;

    try {
      setDeleting(true);
      setError(null);

      await api.delete(endpoints.deleteCreation(creation.id));

      onPublished?.(); // Refresh the list
      onClose();
    } catch (err: any) {
      console.error('Failed to delete:', err);
      setError(err.response?.data?.error || 'Failed to delete. Please try again.');
    } finally {
      setDeleting(false);
    }
  };

  const getStatusDisplay = () => {
    switch (creation.status) {
      case 'pending':
        return { text: 'Pending - Waiting to generate', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', color: 'text-yellow-400' };
      case 'processing':
        return { text: `Processing - Generating ${creation.mediaType}...`, bg: 'bg-blue-500/10', border: 'border-blue-500/30', color: 'text-blue-400' };
      case 'draft':
        return { text: 'Ready to publish!', bg: 'bg-green-500/10', border: 'border-green-500/30', color: 'text-green-400' };
      case 'failed':
        return { text: 'Generation failed', bg: 'bg-red-500/10', border: 'border-red-500/30', color: 'text-red-400' };
      default:
        return { text: 'Unknown status', bg: 'bg-gray-500/10', border: 'border-gray-500/30', color: 'text-gray-400' };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div 
        className="bg-momo-gray-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center rounded-full bg-momo-gray-700 hover:bg-momo-gray-600 transition-colors"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="p-6 space-y-6">
          {/* Status Banner */}
          <div className={`${statusDisplay.bg} ${statusDisplay.border} border rounded-xl p-4 flex items-center gap-3`}>
            {isPending && (
              <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-current"></div>
            )}
            {isDraft && <span className="text-2xl">✅</span>}
            {isFailed && <span className="text-2xl">❌</span>}
            <span className={`font-semibold ${statusDisplay.color}`}>{statusDisplay.text}</span>
          </div>

          {/* Media Preview */}
          {creation.mediaUrl && (
            <div className="rounded-xl overflow-hidden bg-black">
              {creation.mediaType === 'video' ? (
                <video
                  src={creation.mediaUrl}
                  poster={creation.thumbnailUrl}
                  controls
                  className="w-full max-h-[60vh] object-contain"
                />
              ) : (
                <img
                  src={creation.mediaUrl}
                  alt="Draft preview"
                  className="w-full max-h-[60vh] object-contain"
                />
              )}
            </div>
          )}

          {/* Prompt Display */}
          <div>
            <label className="block text-sm font-semibold text-momo-gray-400 mb-2">
              Prompt
            </label>
            <div className="bg-momo-gray-700 rounded-lg p-4 text-sm text-momo-gray-300">
              {creation.prompt}
            </div>
          </div>

          {/* Caption Editor (only for ready drafts) */}
          {isDraft && (
            <div>
              <label htmlFor="caption" className="block text-sm font-semibold text-momo-gray-400 mb-2">
                Caption (Optional)
              </label>
              <textarea
                id="caption"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                rows={3}
                placeholder="Add a caption for your creation..."
                className="w-full bg-momo-gray-700 text-momo-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-momo-purple resize-none"
              />
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Metadata */}
          <div className="flex items-center gap-4 text-xs text-momo-gray-500">
            <span className="flex items-center gap-1">
              {creation.mediaType === 'video' ? '🎬' : '🖼️'} {creation.mediaType}
            </span>
            {creation.aspectRatio && (
              <span>{creation.aspectRatio}</span>
            )}
            {creation.mediaType === 'video' && creation.duration && (
              <span>{creation.duration}s</span>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            {isDraft && (
              <>
                <button
                  onClick={handlePublish}
                  disabled={publishing}
                  className="flex-1 bg-momo-purple hover:bg-momo-purple/80 disabled:bg-momo-gray-700 disabled:text-momo-gray-500 text-white py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                >
                  {publishing ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white"></div>
                      <span>Publishing...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Publish</span>
                    </>
                  )}
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting || publishing}
                  className="px-6 py-3 bg-momo-gray-700 hover:bg-red-500/20 hover:text-red-400 text-momo-gray-300 rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {deleting ? 'Deleting...' : 'Delete'}
                </button>
              </>
            )}

            {(isPending || isFailed) && (
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
              >
                {deleting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-current"></div>
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    <span>Delete Draft</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
