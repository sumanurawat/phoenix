import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ExplorePage } from './pages/ExplorePage';
import { ProfilePage } from './pages/ProfilePage';
import { userAPI } from './api';
import { User } from './types';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const response = await userAPI.getCurrentUser();
        if (response.success) {
          setUser(response.user);
        }
      } catch (err) {
        console.error('Failed to load user:', err);
        // User is not authenticated - that's okay for public pages
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <Router>
      <Layout user={user}>
        <Routes>
          <Route path="/soho/explore" element={<ExplorePage />} />
          <Route path="/soho/profile/:username" element={<ProfilePage />} />
          <Route path="/soho" element={<Navigate to="/soho/explore" replace />} />
          <Route path="*" element={<Navigate to="/soho/explore" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
