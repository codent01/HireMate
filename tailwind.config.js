/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js"],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
      colors: {
        brand: {
          50: '#fff7ed', 100: '#ffedd5', 200: '#fed7aa',
          300: '#fdba74', 400: '#fb923c', 500: '#f97316',
          600: '#ea580c', 700: '#c2410c', 800: '#9a3412',
          900: '#7c2d12', 950: '#431407',
        },
        surface: {
          50: '#1c1c1e',
          100: '#1a1a1c',
          200: '#28282b',
          300: '#333336',
          400: '#48484a',
          500: '#636366',
          600: '#8e8e93',
          700: '#aeaeb2',
          800: '#d1d1d6',
          900: '#0d0d0f',
          950: '#08080a',
        },
      },
    },
  },
  plugins: [],
}
