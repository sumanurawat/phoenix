import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Header } from '../components/layout/Header';

export const LandingPage = () => {
  const navigate = useNavigate();
  const { user, loading } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const isAuthenticated = Boolean(user?.username);

  // If user is authenticated, use the standard Header component
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-momo-black via-momo-purple/20 to-momo-black flex items-center justify-center">
        <div className="text-momo-white text-xl">Loading...</div>
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-momo-black via-momo-purple/20 to-momo-black text-momo-white">
        <Header />
        
        {/* Hero Section for Logged-in Users */}
        <section className="pt-32 pb-20 px-4">
          <div className="max-w-7xl mx-auto text-center">
            <div className="inline-block mb-4 px-4 py-2 bg-momo-purple/20 rounded-full border border-momo-purple/30">
              <span className="text-momo-purple text-sm">Welcome back, @{user?.username}!</span>
            </div>

            <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight text-white">
              Ready to Create
              <br />
              <span className="bg-gradient-to-r from-momo-purple via-momo-blue to-momo-purple bg-clip-text text-transparent">
                Something Amazing?
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-momo-gray-300 mb-12 max-w-3xl mx-auto">
              Your AI creative studio awaits. Generate stunning images and videos with the power of prompts.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <button
                onClick={() => navigate('/create')}
                className="group px-8 py-4 bg-gradient-to-r from-momo-purple to-momo-blue rounded-lg text-lg font-semibold hover:opacity-90 transition flex items-center gap-2"
              >
                <span>Start Creating</span>
                <svg className="w-5 h-5 group-hover:translate-x-1 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
              <button
                onClick={() => navigate(`/profile/${user?.username}`)}
                className="px-8 py-4 border-2 border-momo-purple rounded-lg text-lg font-semibold hover:bg-momo-purple/10 transition"
              >
                View Your Profile
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-20 max-w-4xl mx-auto">
              <div className="p-6 bg-momo-gray-800/50 backdrop-blur rounded-xl border border-momo-gray-700">
                <div className="text-4xl font-bold text-momo-purple mb-2">AI-Powered</div>
                <div className="text-momo-gray-300">Image & Video Generation</div>
              </div>
              <div className="p-6 bg-momo-gray-800/50 backdrop-blur rounded-xl border border-momo-gray-700">
                <div className="text-4xl font-bold text-momo-blue mb-2">Token-Based</div>
                <div className="text-momo-gray-300">Fair & Transparent Pricing</div>
              </div>
              <div className="p-6 bg-momo-gray-800/50 backdrop-blur rounded-xl border border-momo-gray-700">
                <div className="text-4xl font-bold text-momo-purple mb-2">Community</div>
                <div className="text-momo-gray-300">Share & Discover</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  // Logged-out view with custom navigation
  return (
    <div className="min-h-screen bg-gradient-to-br from-momo-black via-momo-purple/20 to-momo-black text-momo-white">
      {/* Navigation */}
      <nav className="fixed w-full bg-momo-gray-900/80 backdrop-blur-xl z-50 border-b border-momo-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <button
              onClick={() => navigate('/')}
              className="hover:opacity-80 transition"
            >
              <span className="text-2xl font-bold bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent">
                fried momo
              </span>
            </button>

            {/* Desktop Menu */}
            <div className="hidden md:flex items-center gap-8">
              <a href="#vision" className="hover:text-momo-purple transition">Vision</a>
              <a href="#features" className="hover:text-momo-purple transition">Features</a>
              <a href="#founder" className="hover:text-momo-purple transition">About</a>
              <button
                onClick={() => navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`)}
                className="px-4 py-2 text-momo-purple border border-momo-purple rounded-lg hover:bg-momo-purple hover:text-white transition"
              >
                Sign In
              </button>
              <button
                onClick={() => navigate(`/signup?next=${encodeURIComponent(window.location.pathname)}`)}
                className="px-4 py-2 bg-gradient-to-r from-momo-purple to-momo-blue rounded-lg hover:opacity-90 transition"
              >
                Get Started
              </button>
            </div>

            {/* Mobile menu button */}
            <button
              className="md:hidden"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden bg-momo-gray-900 border-t border-momo-gray-700">
            <div className="px-4 py-4 space-y-3">
              <a href="#vision" className="block hover:text-momo-purple">Vision</a>
              <a href="#features" className="block hover:text-momo-purple">Features</a>
              <a href="#founder" className="block hover:text-momo-purple">About</a>
              <button
                onClick={() => navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`)}
                className="w-full px-4 py-2 text-momo-purple border border-momo-purple rounded-lg"
              >
                Sign In
              </button>
              <button
                onClick={() => navigate(`/signup?next=${encodeURIComponent(window.location.pathname)}`)}
                className="w-full px-4 py-2 bg-gradient-to-r from-momo-purple to-momo-blue rounded-lg"
              >
                Get Started
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-block mb-4 px-4 py-2 bg-momo-purple/20 rounded-full border border-momo-purple/30">
            <span className="text-momo-purple text-sm">The Prompt Economy is Here</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight text-white">
            The Future of Work
            <br />
            <span className="bg-gradient-to-r from-momo-purple via-momo-blue to-momo-purple bg-clip-text text-transparent">
              is Prompts
            </span>
          </h1>

          <p className="text-xl md:text-2xl text-momo-gray-300 mb-12 max-w-3xl mx-auto">
            Master the art of AI collaboration. Build your prompt arsenal.
            Thrive in the new creative economy.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <button
              onClick={() => navigate('/signup')}
              className="group px-8 py-4 bg-gradient-to-r from-momo-purple to-momo-blue rounded-lg text-lg font-semibold hover:opacity-90 transition flex items-center gap-2"
            >
              <span>Get Started Free</span>
              <svg className="w-5 h-5 group-hover:translate-x-1 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
            <button
              onClick={() => navigate('/explore')}
              className="px-8 py-4 border-2 border-momo-purple rounded-lg text-lg font-semibold hover:bg-momo-purple/10 transition"
            >
              Explore Creations
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-20 max-w-4xl mx-auto">
            <div className="p-6 bg-momo-gray-800/50 backdrop-blur rounded-xl border border-momo-gray-700">
              <div className="text-4xl font-bold text-momo-purple mb-2">AI-Powered</div>
              <div className="text-momo-gray-300">Image & Video Generation</div>
            </div>
            <div className="p-6 bg-momo-gray-800/50 backdrop-blur rounded-xl border border-momo-gray-700">
              <div className="text-4xl font-bold text-momo-blue mb-2">Token-Based</div>
              <div className="text-momo-gray-300">Fair & Transparent Pricing</div>
            </div>
            <div className="p-6 bg-momo-gray-800/50 backdrop-blur rounded-xl border border-momo-gray-700">
              <div className="text-4xl font-bold text-momo-purple mb-2">Community</div>
              <div className="text-momo-gray-300">Share & Discover</div>
            </div>
          </div>
        </div>
      </section>

      {/* Founder's Note Section */}
      <section id="founder" className="py-20 px-4 bg-momo-gray-900/50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-4 text-white">From the Founder</h2>
            <div className="w-20 h-1 bg-gradient-to-r from-momo-purple to-momo-blue mx-auto"></div>
          </div>

          <div className="bg-momo-gray-800/50 backdrop-blur rounded-2xl p-8 md:p-12 border border-momo-gray-700">
            <h3 className="text-3xl font-bold mb-6 text-momo-purple">The Quiet Revolution</h3>

            <div className="space-y-4 text-lg text-momo-gray-300 leading-relaxed">
              <p>
                Something remarkable is happening right now. We're standing at the edge of a transformation
                that will redefine what it means to work, create, and build.
              </p>

              <p>
                AI can already code your app, edit your video, design your course, and generate your content.
                Soon—maybe sooner than we think—these systems will be so powerful they'll create ten versions
                of anything you imagine, and you'll simply choose the one you love.
              </p>

              <p className="text-xl font-semibold text-momo-white">
                But we're not there yet.
              </p>

              <p>
                Right now, in this unique moment, there's a skill that separates dreamers from builders:
                <span className="text-momo-purple font-semibold"> the ability to speak to AI</span>.
                The right prompt is the difference between mediocre and magical. Between generic and genius.
                Between "that's interesting" and "that's exactly what I needed."
              </p>

              <p>
                This is the creative economy for the AI era. A place where your vision becomes reality.
                Where specificity wins. Where knowing <em>how</em> to ask is as valuable as knowing <em>what</em> to ask.
              </p>

              <p className="text-xl font-semibold text-momo-purple">
                We're building Momo because we see what's coming—and we want you ready for it.
              </p>

              <p className="text-xl">
                Welcome to where it's happening.
              </p>
            </div>

            <div className="mt-8 pt-8 border-t border-momo-gray-700">
              <p className="text-momo-gray-400">— Sumanu, Founder</p>
            </div>
          </div>
        </div>
      </section>

      {/* Vision Section */}
      <section id="vision" className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4 text-white">The Vision</h2>
            <div className="w-20 h-1 bg-gradient-to-r from-momo-purple to-momo-blue mx-auto"></div>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Today's Reality */}
            <div className="p-8 bg-gradient-to-br from-momo-gray-800/50 to-momo-purple/10 backdrop-blur rounded-2xl border border-momo-gray-700">
              <div className="inline-block p-3 bg-momo-purple/20 rounded-lg mb-4">
                <svg className="w-8 h-8 text-momo-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold mb-6 text-momo-purple">Today's Reality</h3>
              <ul className="space-y-3 text-momo-gray-300">
                <li className="flex items-start gap-3">
                  <div className="w-1.5 h-1.5 bg-momo-purple rounded-full mt-2"></div>
                  <span>AI generates stunning images and videos on command</span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-1.5 h-1.5 bg-momo-purple rounded-full mt-2"></div>
                  <span>Creators share and monetize their AI art</span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-1.5 h-1.5 bg-momo-purple rounded-full mt-2"></div>
                  <span>Communities form around AI creativity</span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-1.5 h-1.5 bg-momo-purple rounded-full mt-2"></div>
                  <span>But only if you know how to guide them</span>
                </li>
              </ul>
            </div>

            {/* Tomorrow's Promise */}
            <div className="p-8 bg-gradient-to-br from-momo-gray-800/50 to-momo-blue/10 backdrop-blur rounded-2xl border border-momo-gray-700">
              <div className="inline-block p-3 bg-momo-blue/20 rounded-lg mb-4">
                <svg className="w-8 h-8 text-momo-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold mb-6 text-momo-blue">Tomorrow's Promise</h3>
              <p className="text-momo-gray-300 leading-relaxed">
                We're racing toward a future where AI creation is instant and limitless. Where your imagination
                is the only boundary. Where technology democratizes creativity.
                <br /><br />
                <span className="text-momo-white font-semibold">
                  Until then, your edge is mastering the art of AI collaboration. Momo is where you learn,
                  create, and thrive.
                </span>
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 bg-momo-gray-900/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4 text-white">Why Momo</h2>
            <div className="w-20 h-1 bg-gradient-to-r from-momo-purple to-momo-blue mx-auto"></div>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-8 bg-momo-gray-800/50 backdrop-blur rounded-2xl border border-momo-gray-700 hover:border-momo-purple transition group">
              <div className="inline-block p-4 bg-momo-purple/20 rounded-xl mb-6 group-hover:scale-110 transition">
                <svg className="w-10 h-10 text-momo-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold mb-4">🎨 Create Anything</h3>
              <p className="text-momo-gray-300">
                Generate stunning images and videos with AI. Your imagination becomes reality with
                powerful generation tools.
              </p>
            </div>

            <div className="p-8 bg-momo-gray-800/50 backdrop-blur rounded-2xl border border-momo-gray-700 hover:border-momo-blue transition group">
              <div className="inline-block p-4 bg-momo-blue/20 rounded-xl mb-6 group-hover:scale-110 transition">
                <svg className="w-10 h-10 text-momo-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold mb-4">🤝 Join Community</h3>
              <p className="text-momo-gray-300">
                Share your creations, discover others' work, and connect with fellow AI artists in
                a vibrant community.
              </p>
            </div>

            <div className="p-8 bg-momo-gray-800/50 backdrop-blur rounded-2xl border border-momo-gray-700 hover:border-momo-purple transition group">
              <div className="inline-block p-4 bg-momo-purple/20 rounded-xl mb-6 group-hover:scale-110 transition">
                <svg className="w-10 h-10 text-momo-purple" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
                  <path d="M12 8.5l-3 3 3 3 3-3-3-3z" opacity="0.7"/>
                </svg>
              </div>
              <h3 className="text-2xl font-bold mb-4">💎 Own Your Work</h3>
              <p className="text-momo-gray-300">
                Fair token-based system. Create drafts, refine your art, and publish when ready.
                You control everything.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-bold mb-6 text-white">
            Ready to Start Creating?
          </h2>
          <p className="text-xl text-momo-gray-300 mb-10">
            Join Momo today. Get 10 free tokens to start generating your first AI masterpieces.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate('/signup')}
              className="group px-10 py-5 bg-gradient-to-r from-momo-purple to-momo-blue rounded-lg text-xl font-semibold hover:opacity-90 transition flex items-center justify-center gap-2"
            >
              <span>Create Your Account</span>
              <svg className="w-6 h-6 group-hover:translate-x-1 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
            <button
              onClick={() => navigate('/explore')}
              className="px-10 py-5 border-2 border-momo-purple rounded-lg text-xl font-semibold hover:bg-momo-purple/10 transition"
            >
              Explore the Platform
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 border-t border-momo-gray-700 bg-momo-gray-900/80">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <span className="text-xl font-bold bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent">
                fried momo
              </span>
            </div>

            <div className="text-momo-gray-400 text-center md:text-left mb-4 md:mb-0">
              <p className="italic">Where the creative economy lives.</p>
            </div>

            <div className="flex gap-6 text-momo-gray-400">
              <a href="#" className="hover:text-momo-purple transition">Privacy</a>
              <a href="#" className="hover:text-momo-purple transition">Terms</a>
              <a href="#" className="hover:text-momo-purple transition">Contact</a>
            </div>
          </div>

          <div className="text-center text-momo-gray-500 text-sm mt-8">
            © 2025 Momo. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};
