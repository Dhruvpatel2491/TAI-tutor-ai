/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // Primary teal palette
        primary: {
          DEFAULT: '#53A2A7',
          hover: '#30838c',
          light: 'rgba(83, 162, 167, 0.3)',
          dark: '#30838C',
        },
        // Accent colors
        accent: {
          olive: '#A6BB95',
          'olive-light': 'rgba(166, 187, 149, 0.3)',
          sand: '#DECC9E',
          'sand-light': 'rgba(213, 191, 133, 0.3)',
          'sand-dark': '#9C7F35',
        },
        // Background colors
        surface: {
          page: '#F7F7F6',
          primary: '#FFFFFF',
          secondary: '#FBFAF6',
          tertiary: '#decc9e',
        },
        // Text colors
        text: {
          primary: '#0F1724',
          secondary: '#6B7280',
          muted: '#9CA3AF',
          inverse: '#FFFFFF',
        },
        // Border
        border: {
          DEFAULT: '#E8E9EB',
          hover: '#D1D5DB',
        },
      },
      borderRadius: {
        'xl': '16px',
        '2xl': '24px',
      },
      boxShadow: {
        'soft': '0 8px 22px rgba(15, 23, 36, 0.06)',
        'float': '0 8px 30px rgba(15, 23, 36, 0.12)',
        'card': '0 4px 12px rgba(83, 162, 167, 0.15)',
        'card-hover': '0 12px 24px rgba(83, 162, 167, 0.2)',
      },
    },
  },
  plugins: [],
}
