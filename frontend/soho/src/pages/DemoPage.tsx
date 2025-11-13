import { Layout } from '../components/layout/Layout';

export const DemoPage = () => {
  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Hero Section */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent">
            Welcome to Momo
          </h1>
          <p className="text-xl text-momo-gray-400">
            A beautiful, Jony Ive-inspired social media platform
          </p>
        </div>

        {/* Design System Showcase */}
        <div className="bg-momo-gray-800 rounded-xl p-6 space-y-6">
          <h2 className="text-2xl font-semibold">Design System Preview</h2>

          {/* Colors */}
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-momo-gray-400">Color Palette</h3>
            <div className="grid grid-cols-4 gap-3">
              <div className="space-y-2">
                <div className="h-16 bg-momo-purple rounded-lg"></div>
                <p className="text-xs text-center">Purple</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 bg-momo-blue rounded-lg"></div>
                <p className="text-xs text-center">Blue</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 bg-momo-gold rounded-lg"></div>
                <p className="text-xs text-center">Gold</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 bg-momo-like rounded-lg"></div>
                <p className="text-xs text-center">Like</p>
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-momo-gray-400">Buttons</h3>
            <div className="flex gap-3 flex-wrap">
              <button className="bg-momo-purple hover:bg-momo-purple/80 text-white font-semibold px-6 py-3 rounded-lg transition-all duration-150 active:scale-95 shadow-md hover:shadow-lg">
                Primary Button
              </button>
              <button className="bg-momo-gray-700 hover:bg-momo-gray-600 text-white font-medium px-4 py-2 rounded-lg transition-all duration-150">
                Secondary
              </button>
              <button className="p-2 rounded-full hover:bg-momo-gray-700 transition-colors duration-150">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Sample Post Card */}
        <div className="bg-momo-gray-800 rounded-xl overflow-hidden shadow-lg">
          <div className="flex items-center gap-3 p-4">
            <div className="w-10 h-10 rounded-full bg-momo-purple flex items-center justify-center">
              <span className="text-sm font-semibold">JI</span>
            </div>
            <span className="font-semibold">@jonyive</span>
          </div>

          <div className="relative bg-black aspect-square">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center space-y-2">
                <svg className="w-20 h-20 mx-auto text-momo-gray-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
                </svg>
                <p className="text-momo-gray-500 text-sm">Sample Creation</p>
              </div>
            </div>
          </div>

          <div className="p-4 space-y-3">
            <div className="flex items-center gap-4">
              <button className="flex items-center gap-2 group">
                <svg className="w-7 h-7 text-momo-white group-hover:text-momo-like transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <span className="text-sm font-semibold">42</span>
              </button>

              <button className="flex items-center gap-2 group">
                <svg className="w-7 h-7 text-momo-white group-hover:text-momo-blue transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="text-sm font-semibold">12</span>
              </button>
            </div>

            <p className="text-sm">
              <span className="font-semibold">@jonyive</span>{' '}
              <span className="text-momo-gray-400">
                Simplicity is the ultimate sophistication. ✨
              </span>
            </p>
          </div>
        </div>

        {/* Typography Samples */}
        <div className="bg-momo-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-2xl font-semibold">Typography</h2>
          <div className="space-y-2">
            <p className="text-xs text-momo-gray-400">12px - Timestamps</p>
            <p className="text-sm text-momo-gray-400">14px - Captions</p>
            <p className="text-base">16px - Body Text</p>
            <p className="text-lg font-semibold">18px - Usernames</p>
            <p className="text-xl font-semibold">20px - Section Headers</p>
            <p className="text-2xl font-bold">24px - Page Titles</p>
          </div>
        </div>

        {/* Status Indicator */}
        <div className="bg-momo-green/10 border border-momo-green/20 rounded-lg p-4 flex items-start gap-3">
          <svg className="w-6 h-6 text-momo-green flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
          <div>
            <p className="font-semibold text-momo-green">Momo is Running!</p>
            <p className="text-sm text-momo-gray-400 mt-1">
              Your development environment is set up correctly. Backend on port 8080, Frontend on port 5173.
            </p>
          </div>
        </div>

        {/* Next Steps */}
        <div className="bg-momo-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-2xl font-semibold">Next Steps</h2>
          <ul className="space-y-2 text-momo-gray-400">
            <li className="flex items-start gap-2">
              <span className="text-momo-purple mt-1">→</span>
              <span>Build TypeScript types for API integration</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-momo-purple mt-1">→</span>
              <span>Create Explore page with infinite scroll</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-momo-purple mt-1">→</span>
              <span>Implement Profile page with grid layout</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-momo-purple mt-1">→</span>
              <span>Build Creation modal with comments</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-momo-purple mt-1">→</span>
              <span>Add Token management pages</span>
            </li>
          </ul>
        </div>
      </div>
    </Layout>
  );
};
