/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // SOC-themed colors
        'soc-primary': '#0ea5e9',
        'soc-secondary': '#8b5cf6',
        'soc-danger': '#ef4444',
        'soc-warning': '#f59e0b',
        'soc-success': '#10b981',
        'soc-bg': '#0f172a',
        'soc-card': '#1e293b',
      },
    },
  },
  plugins: [],
}
