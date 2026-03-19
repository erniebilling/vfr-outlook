/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // VFR score colors
        vfr: '#22c55e',      // green-500
        mvfr: '#84cc16',     // lime-500
        marginal: '#eab308', // yellow-500
        poor: '#f97316',     // orange-500
        ifr: '#ef4444',      // red-500
      },
    },
  },
  plugins: [],
}
