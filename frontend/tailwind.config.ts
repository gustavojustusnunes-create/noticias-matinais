import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0fdf9",
          100: "#ccfbef",
          200: "#99f6e0",
          300: "#5eead1",
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0d9488",
          700: "#0a5c5a",
          800: "#115e59",
          900: "#134e4a",
          950: "#042f2e",
        },
        paper: {
          light: "#FBFBFA",
          sand: "#F4F1EA",
          border: "#E7E4DC",
        },
        obsidian: {
          base: "#0A0A0C",
          surface: "#121215",
          border: "#1E1E24",
          muted: "#27272A",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
      },
      animation: {
        "marquee": "marquee 35s linear infinite",
        "marquee-reverse": "marquee-reverse 35s linear infinite",
        "pulse-slow": "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "shine": "shine 2s linear infinite",
      },
      keyframes: {
        marquee: {
          "0%": { transform: "translateX(0%)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "marquee-reverse": {
          "0%": { transform: "translateX(-50%)" },
          "100%": { transform: "translateX(0%)" },
        },
        shine: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
