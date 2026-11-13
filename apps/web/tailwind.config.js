/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Kabuk + Inbox: değerler src/styles/tokens.css'tedir (tek kaynak)
        os: {
          bg: 'var(--bg)', nav: 'var(--nav)', panel: 'var(--panel)', raised: 'var(--raised)',
          line: 'var(--line)', line2: 'var(--line-strong)',
          text: 'var(--text)', text2: 'var(--text-2)', muted: 'var(--muted)', faint: 'var(--faint)',
          accent: 'var(--accent)', onaccent: 'var(--on-accent)', ok: 'var(--ok)',
          urgentbg: 'var(--urgent-bg)', urgentfg: 'var(--urgent-fg)',
          inbg: 'var(--in-bg)', inline: 'var(--in-line)',
          outbg: 'var(--out-bg)', outline: 'var(--out-line)', outtext: 'var(--out-text)',
        },
        brand: {
          50: '#fefce8',
          100: '#fef9c3',
          400: '#facc15',
          500: '#eab308',
          600: '#ca8a04',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
