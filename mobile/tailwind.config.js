/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './App.tsx',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#0b0b0d',
          elev: '#16161a',
          card: '#1c1c22',
        },
        ink: {
          DEFAULT: '#f5f5f7',
          dim: '#a1a1aa',
          mute: '#6b7280',
        },
        accent: {
          run: '#34d399',
          strength: '#f59e0b',
          rest: '#60a5fa',
          danger: '#ef4444',
        },
        line: '#2a2a31',
      },
      fontFamily: {
        sans: ['System'],
      },
    },
  },
  plugins: [],
};
