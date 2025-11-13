import { Header } from '../components/layout/Header';

export const SettingsPage = () => {
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
      </main>
    </div>
  );
};
