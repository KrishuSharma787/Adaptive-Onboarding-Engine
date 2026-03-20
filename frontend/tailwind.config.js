/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"DM Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        midnight: '#0a0e1a',
        surface: '#111827',
        'surface-2': '#1a2332',
        'surface-3': '#243044',
        accent: '#06d6a0',
        'accent-dim': '#059669',
        warning: '#fbbf24',
        danger: '#ef4444',
        info: '#38bdf8',
      }
    },
  },
  plugins: [],
}
