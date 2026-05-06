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
          DEFAULT: '#0d0d12',
          panel: '#11142a',
          panelAlt: '#1a1d3d',
          elev: '#11142a',
          card: '#11142a',
        },
        ink: {
          DEFAULT: '#f4f4ec',
          dim: '#9a9aab',
          mute: '#5a5a6b',
        },
        accent: {
          run: '#5cd86c',
          strength: '#e8a23a',
          rest: '#5b8cff',
          danger: '#e84a4a',
          hi: '#f7d51d',
        },
        line: '#000000',
      },
      fontFamily: {
        pixel: ['PressStart2P'],
        body: ['VT323'],
      },
    },
  },
  plugins: [],
};
