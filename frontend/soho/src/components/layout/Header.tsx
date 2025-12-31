import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useTokenBalance } from '../../hooks/useTokenBalance';

export const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading: authLoading } = useAuth();
  const { balance, loading: balanceLoading } = useTokenBalance();
  const isAuthenticated = Boolean(user?.username);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  const navigateAndCloseMenu = (path: string) => {
    setIsMenuOpen(false);
    navigate(path);
  };

  const handleLogout = () => {
    // Use same-origin for logout (works with Firebase Hosting proxy)
    const returnUrl = `${window.location.origin}/`; // Go to React landing page after logout
    window.location.href = `/logout?redirect=momo&redirect_url=${encodeURIComponent(returnUrl)}`;
  };

  return (
    <header className="sticky top-0 z-50 bg-momo-gray-900/80 backdrop-blur-xl border-b border-momo-gray-700">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-8">
          <button
            className="cursor-pointer hover:opacity-80 transition"
            onClick={() => navigate('/')}
            title="Go to home"
          >
            <img
              src="/fried_momo_text.png"
              alt="Fried Momo"
              className="h-10 w-auto mix-blend-screen"
            />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-6">
          <button
            className={`p-2 rounded-lg transition-colors ${
              location.pathname === '/explore'
                ? 'bg-momo-gray-800 text-momo-purple'
                : 'hover:bg-momo-gray-800 text-momo-white'
            }`}
            title="Explore"
            onClick={() => navigate('/explore')}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          </button>

          <button
            className={`p-2 rounded-lg transition-colors ${
              location.pathname === '/create'
                ? 'bg-momo-gray-800'
                : 'hover:bg-momo-gray-800'
            }`}
            title="Create"
            onClick={() => navigate('/create')}
          >
            <svg className="w-7 h-7 text-momo-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>

          <button
            className={`p-2 rounded-lg transition-colors ${
              location.pathname.startsWith('/profile')
                ? 'bg-momo-gray-800 text-momo-purple'
                : 'hover:bg-momo-gray-800 text-momo-white'
            } ${!isAuthenticated && 'opacity-50 cursor-default'}`}
            title={isAuthenticated ? 'Profile' : 'Sign in to view profile'}
            onClick={() => isAuthenticated && user?.username && navigate(`/profile/${user.username}`)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </button>
        </nav>

        {/* User Actions */}
        <div className="flex items-center gap-4">
          {/* Token Balance */}
          <div
            className={`flex items-center gap-2 px-3 py-2 bg-momo-gray-800 rounded-lg transition-colors ${
              user ? 'hover:bg-momo-gray-700 cursor-pointer' : 'opacity-50 cursor-default'
            }`}
            title={user ? 'Token Balance' : 'Sign in to view token balance'}
            onClick={() => user && navigate('/tokens')}
          >
            <svg className="w-5 h-5 text-momo-gold" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
              <path d="M12 8.5l-3 3 3 3 3-3-3-3z" opacity="0.7"/>
            </svg>
            <span className="font-semibold text-momo-white">
              {balanceLoading ? '...' : user ? balance : '—'}
            </span>
          </div>

          {/* Transactions */}
          <button
            className={`p-2 rounded-lg transition-colors ${
              isAuthenticated ? 'hover:bg-momo-gray-800' : 'opacity-50 cursor-default'
            }`}
            title={isAuthenticated ? 'Transactions' : 'Sign in to view transactions'}
            onClick={() => isAuthenticated && navigate('/transactions')}
          >
            <svg className="w-6 h-6 text-momo-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </button>

          {/* Profile Avatar / Username */}
          {isAuthenticated && user ? (
            <div className="relative" ref={menuRef}>
              <button
                className="h-8 px-3 rounded-full bg-momo-purple flex items-center justify-center gap-2 hover:ring-2 hover:ring-momo-purple/50 transition-all"
                title={`@${user.username}`}
                onClick={() => setIsMenuOpen((prev) => !prev)}
                aria-haspopup="menu"
                aria-expanded={isMenuOpen}
              >
                {user.profileImageUrl && (
                  <img
                    src={user.profileImageUrl}
                    alt={user.username}
                    className="w-6 h-6 rounded-full object-cover"
                  />
                )}
                <span className="text-sm font-semibold text-white">
                  {user.username}
                </span>
              </button>

              {isMenuOpen && (
                <div className="absolute right-0 mt-3 w-56 rounded-xl bg-momo-gray-900 border border-momo-gray-700 shadow-xl overflow-hidden" role="menu">
                  <div className="px-4 py-3 border-b border-momo-gray-800">
                    <p className="text-xs text-momo-gray-400">Signed in as</p>
                    <p className="text-sm font-semibold text-momo-white truncate">@{user.username}</p>
                  </div>

                  <div className="py-1">
                    <button
                      className="w-full px-4 py-2 text-left text-sm text-momo-white hover:bg-momo-gray-800"
                      onClick={() => navigateAndCloseMenu(`/profile/${user.username}`)}
                      role="menuitem"
                    >
                      Profile
                    </button>
                    <button
                      className="w-full px-4 py-2 text-left text-sm text-momo-white hover:bg-momo-gray-800"
                      onClick={() => navigateAndCloseMenu('/tokens')}
                      role="menuitem"
                    >
                      Tokens
                    </button>
                    <button
                      className="w-full px-4 py-2 text-left text-sm text-momo-white hover:bg-momo-gray-800"
                      onClick={() => navigateAndCloseMenu('/transactions')}
                      role="menuitem"
                    >
                      Transactions
                    </button>
                    <button
                      className="w-full px-4 py-2 text-left text-sm text-momo-white hover:bg-momo-gray-800"
                      onClick={() => navigateAndCloseMenu('/settings')}
                      role="menuitem"
                    >
                      Settings
                    </button>
                  </div>

                  <div className="border-t border-momo-gray-800">
                    <button
                      className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-momo-gray-800"
                      onClick={handleLogout}
                      role="menuitem"
                    >
                      Sign out
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <button
              className="px-4 py-2 rounded-lg bg-momo-purple hover:bg-momo-purple/80 text-white font-semibold transition-colors"
              onClick={() => navigate('/login')}
              disabled={authLoading}
            >
              {authLoading ? 'Loading…' : 'Sign in'}
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
