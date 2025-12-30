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
        // Semantic text colors
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },
        // Theme colors (aliased to dark.* for backward compatibility)
        dark: {
          bg: 'var(--bg-primary)',
          'bg-secondary': 'var(--bg-secondary)',
          surface: 'var(--bg-surface)',
          'surface-elevated': 'var(--bg-surface-elevated)',
          border: 'var(--border-color)',
          'border-light': 'var(--border-light)',
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
