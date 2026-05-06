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
          DEFAULT: '#0e1320',
          panel: '#1a1f33',
          panelAlt: '#222a44',
          elev: '#1a1f33',
          card: '#1a1f33',
        },
        ink: {
          DEFAULT: '#e8e8d8',
          dim: '#8b9bb3',
          mute: '#5a6478',
        },
        accent: {
          run: '#22d36a',
          cyan: '#7ec8c8',
          strength: '#e8593a',
          purple: '#7c5cd8',
          rest: '#5b8cff',
          danger: '#e84a4a',
          hi: '#f7d51d',
        },
        line: {
          DEFAULT: '#2a3045',
          hard: '#000000',
        },
      },
      fontFamily: {
        pixel: ['PressStart2P'],
        body: ['VT323'],
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '8px',
        xl: '10px',
      },
    },
  },
  plugins: [],
};
