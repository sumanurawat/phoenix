import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { TokenBalanceProvider } from './contexts/TokenBalanceContext';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { ExplorePage } from './pages/ExplorePage';
import { ProfilePage } from './pages/ProfilePage';
import { CreatePage } from './pages/CreatePage';
import { TokensPage } from './pages/TokensPage';
import { TransactionsPage } from './pages/TransactionsPage';
import { DemoPage } from './pages/DemoPage';
import { SettingsPage } from './pages/SettingsPage';
import { OAuthCallbackPage } from './pages/OAuthCallbackPage';
import { UsernameSetupPage } from './pages/UsernameSetupPage';
import { PurchaseSuccessPage } from './pages/PurchaseSuccessPage';

function App() {
  const { loading } = useAuth();

  // Show loading spinner while checking auth
  if (loading) {
    return (
      <div className="min-h-screen bg-momo-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-momo-purple"></div>
      </div>
    );
  }

  return (
    <TokenBalanceProvider>
      <BrowserRouter>
        <Routes>
        {/* Landing page - shows different content based on auth status */}
        <Route path="/" element={<LandingPage />} />

        {/* Auth routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
        <Route path="/username-setup" element={<UsernameSetupPage />} />

        {/* Public routes (accessible to everyone) */}
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/demo" element={<DemoPage />} />

        {/* Protected routes (require authentication) */}
        <Route path="/create" element={<CreatePage />} />
        <Route path="/profile/:username" element={<ProfilePage />} />
        <Route path="/tokens" element={<TokensPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/purchase-success" element={<PurchaseSuccessPage />} />

        {/* Instagram-style profile URLs: friedmomo.com/username
            This catch-all route must be LAST - it only matches if no other route does.
            Profiles are public and shareable via direct username links. */}
        <Route path="/:username" element={<ProfilePage />} />
        </Routes>
      </BrowserRouter>
    </TokenBalanceProvider>
  );
}

export default App;
