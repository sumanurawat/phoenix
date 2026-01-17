import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { api, endpoints } from '../services/api';

export const SettingsPage = () => {
  const navigate = useNavigate();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') {
      setDeleteError('Please type DELETE to confirm');
      return;
    }

    try {
      setIsDeleting(true);
      setDeleteError(null);

      const response = await api.delete(endpoints.me);

      if (response.data.success) {
        // Redirect to home page after successful deletion
        navigate('/', { replace: true });
      } else {
        setDeleteError(response.data.error || 'Failed to delete account');
      }
    } catch (err: any) {
      console.error('Account deletion failed:', err);
      setDeleteError(
        err.response?.data?.error || 'An error occurred while deleting your account'
      );
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="min-h-screen bg-momo-gray-950 text-momo-white">
      <Header />
      <main className="max-w-3xl mx-auto px-4 py-12 space-y-8">
        <section>
          <h1 className="text-3xl font-bold">Account Settings</h1>
          <p className="mt-2 text-momo-gray-300">
            Manage your profile and security preferences. We will continue to add more controls over time.
          </p>
        </section>

        <section className="bg-momo-gray-900 border border-momo-gray-800 rounded-xl p-6 space-y-4">
          <header>
            <h2 className="text-xl font-semibold">Profile</h2>
            <p className="text-sm text-momo-gray-400">
              Updates you make here keep your profile in sync across the platform.
            </p>
          </header>
          <div className="rounded-lg border border-dashed border-momo-gray-700 p-6 text-momo-gray-400">
            Profile editing is coming soon. For now, visit your profile to make changes.
          </div>
        </section>

        <section className="bg-momo-gray-900 border border-momo-gray-800 rounded-xl p-6 space-y-4">
          <header>
            <h2 className="text-xl font-semibold">Security</h2>
            <p className="text-sm text-momo-gray-400">
              Keep your account safe with reliable authentication options.
            </p>
          </header>
          <div className="rounded-lg border border-dashed border-momo-gray-700 p-6 text-momo-gray-400">
            Additional security controls will appear here once multi-factor authentication is available.
          </div>
        </section>

        {/* Danger Zone */}
        <section className="bg-momo-red/5 border border-momo-red/30 rounded-xl p-6 space-y-4">
          <header>
            <h2 className="text-xl font-semibold text-momo-red">Danger Zone</h2>
            <p className="text-sm text-momo-gray-400">
              Irreversible actions that will permanently affect your account.
            </p>
          </header>

          <div className="flex items-center justify-between p-4 bg-momo-gray-900 rounded-lg">
            <div>
              <p className="font-medium">Delete Account</p>
              <p className="text-sm text-momo-gray-400">
                Permanently delete your account and all associated data.
              </p>
            </div>
            <button
              onClick={() => setShowDeleteModal(true)}
              className="px-4 py-2 bg-momo-red/20 text-momo-red border border-momo-red/30 rounded-lg hover:bg-momo-red/30 transition-colors font-medium"
            >
              Delete Account
            </button>
          </div>
        </section>
      </main>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
          <div className="bg-momo-gray-900 border border-momo-gray-700 rounded-2xl max-w-md w-full p-6 space-y-6">
            {/* Header */}
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-momo-red/20 flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-momo-red"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-momo-red">Delete Account?</h3>
              <p className="mt-2 text-momo-gray-400 text-sm">
                This action is <span className="text-momo-red font-semibold">permanent</span> and cannot be undone.
              </p>
            </div>

            {/* Warning list */}
            <div className="bg-momo-gray-800 rounded-lg p-4 space-y-2 text-sm">
              <p className="font-medium text-momo-gray-200">This will permanently delete:</p>
              <ul className="space-y-1 text-momo-gray-400">
                <li className="flex items-center gap-2">
                  <span className="text-momo-red">-</span>
                  Your profile and all account data
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-momo-red">-</span>
                  All your generated images and videos
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-momo-red">-</span>
                  Your transaction history
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-momo-red">-</span>
                  Any remaining token balance
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-momo-red">-</span>
                  Your username (it will become available to others)
                </li>
              </ul>
            </div>

            {/* Confirmation input */}
            <div>
              <label className="block text-sm font-medium text-momo-gray-300 mb-2">
                Type <span className="text-momo-red font-bold">DELETE</span> to confirm
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => {
                  setDeleteConfirmText(e.target.value);
                  setDeleteError(null);
                }}
                placeholder="DELETE"
                className="w-full bg-momo-gray-800 border border-momo-gray-700 rounded-lg px-4 py-3 text-momo-white placeholder-momo-gray-500 focus:outline-none focus:ring-2 focus:ring-momo-red/50"
                disabled={isDeleting}
              />
              {deleteError && (
                <p className="mt-2 text-sm text-momo-red">{deleteError}</p>
              )}
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteConfirmText('');
                  setDeleteError(null);
                }}
                disabled={isDeleting}
                className="flex-1 px-4 py-3 bg-momo-gray-800 text-momo-white rounded-lg hover:bg-momo-gray-700 transition-colors font-medium disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={isDeleting || deleteConfirmText !== 'DELETE'}
                className="flex-1 px-4 py-3 bg-momo-red text-white rounded-lg hover:bg-momo-red/80 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <svg
                      className="animate-spin h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Deleting...
                  </>
                ) : (
                  'Delete Forever'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
