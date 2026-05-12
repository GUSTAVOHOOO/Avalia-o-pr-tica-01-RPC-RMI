import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        surface: {
          bg: '#0f1117',
          card: '#1a1d27',
        },
        accent: '#6366f1',
        destructive: '#ef4444',
        success: '#22c55e',
      },
    },
  },
  plugins: [],
} satisfies Config
