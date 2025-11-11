import { Link } from 'react-router-dom';
import { User } from '../types';

interface HeaderProps {
  user: User | null;
}

export function Header({ user }: HeaderProps) {
  return (
    <header className="bg-gray-900 border-b border-gray-700 sticky top-0 z-50">
      <div className="flex justify-between items-center px-4 py-3 max-w-7xl mx-auto">
        {/* Left Side - Brand */}
        <div className="flex-shrink-0">
          <Link to="/soho/explore" className="text-2xl font-bold text-white hover:text-gray-200 transition-colors">
            Soho
          </Link>
        </div>

        {/* Middle - Navigation */}
        <nav className="flex items-center gap-6">
          <Link 
            to="/soho/explore" 
            className="text-gray-300 hover:text-white transition-colors flex items-center gap-2"
            title="Explore"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span className="hidden sm:inline">Explore</span>
          </Link>
          
          <Link 
            to="/create" 
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-full w-10 h-10 flex items-center justify-center transition-colors"
            title="Create"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </Link>
        </nav>

        {/* Right Side - User Actions */}
        <div className="flex items-center gap-4">
          {user && (
            <>
              {/* Token Balance */}
              <div className="flex items-center gap-2 bg-dark-card px-3 py-2 rounded-lg border border-dark-border">
                <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd" />
                </svg>
                <span className="text-sm font-semibold text-white">{user.tokenBalance.toLocaleString()}</span>
              </div>

              {/* Profile Link */}
              {user.username && (
                <Link 
                  to={`/soho/profile/${user.username}`}
                  className="flex items-center gap-2 hover:opacity-80 transition-opacity"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-semibold text-sm">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                </Link>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  );
}
