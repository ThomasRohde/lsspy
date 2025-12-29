/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Lodestar brand colors
        lodestar: {
          blue: '#3B82F6',
          'blue-light': '#60A5FA',
          'blue-dark': '#2563EB',
        },
        // Status colors
        status: {
          success: '#22C55E',
          info: '#3B82F6',
          warning: '#EAB308',
          error: '#EF4444',
          neutral: '#6B7280',
        },
        // Dark theme colors
        dark: {
          bg: '#0f172a',
          'bg-secondary': '#0c1322',
          surface: '#1e293b',
          'surface-elevated': '#273549',
          border: '#334155',
          'border-light': '#475569',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'monospace'],
      },
      fontSize: {
        'xxs': '0.625rem',
      },
    },
  },
  plugins: [],
}
