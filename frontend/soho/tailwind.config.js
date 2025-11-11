/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark mode color palette inspired by Instagram/X
        dark: {
          bg: '#000000',
          surface: '#0a0a0a',
          card: '#1a1a1a',
          border: '#262626',
          hover: '#1e1e1e',
        }
      }
    },
  },
  plugins: [],
}
