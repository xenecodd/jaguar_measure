/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './public/index.html',
    './src/components/**/*.{js,jsx,ts,tsx}',
    './src/styles/**/*.css'
  ],
  theme: {
    extend: {
      colors: {
        'jaguar-blue': '#007bff',
        'jaguar-gray': '#6c757d',
        'jaguar-green': '#28a745',
        'jaguar-red': '#dc3545',
        // Yeni navbar renkleri
        'navbar-bg': '#1a2b3c',
        'navbar-text': '#f4f4f4',
        'navbar-hover': '#2c3e50',
        'navbar-accent': '#db4d34'
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'custom': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      }
    },
  },
  plugins: [],
}
