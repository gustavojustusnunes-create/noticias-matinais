/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          base: '#0B0F14',
          surface: '#131B26',
          card: '#131B26',
          elevated: '#1A2433',
        },
        border: {
          subtle: 'rgba(255, 255, 255, 0.08)',
          glow: 'rgba(37, 99, 235, 0.25)',
        },
        accent: {
          cobalt: '#2563EB',
          emerald: '#10B981',
          gold: '#EAB308',
          ruby: '#EF4444',
          purple: '#8B5CF6',
        }
      },
      fontFamily: {
        serif: ['Newsreader', 'Playfair Display', 'Georgia', 'serif'],
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
