/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            maxWidth: 'none',
            color: '#e2e8f0',
            a: { color: '#60a5fa' },
            strong: { color: '#f1f5f9' },
            h2: { color: '#f1f5f9' },
            h3: { color: '#f1f5f9' },
            code: { color: '#a78bfa' },
            blockquote: { color: '#94a3b8' },
          },
        },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
