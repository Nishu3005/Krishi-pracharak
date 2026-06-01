import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(42 45% 98%)",
        foreground: "hsl(153 20% 16%)",
        card: "hsl(0 0% 100%)",
        border: "hsl(120 12% 84%)",
        muted: "hsl(90 20% 94%)",
        primary: {
          DEFAULT: "hsl(149 48% 26%)",
          foreground: "hsl(0 0% 100%)"
        },
        secondary: {
          DEFAULT: "hsl(35 70% 86%)",
          foreground: "hsl(23 39% 22%)"
        },
        accent: {
          DEFAULT: "hsl(84 40% 72%)",
          foreground: "hsl(149 48% 18%)"
        },
        ring: "hsl(149 48% 30%)"
      },
      boxShadow: {
        soft: "0 16px 40px -20px rgba(39, 76, 52, 0.25)"
      },
      fontFamily: {
        sans: ["Trebuchet MS", "Segoe UI", "Tahoma", "sans-serif"],
        serif: ["Georgia", "Palatino Linotype", "serif"]
      }
    }
  },
  plugins: []
};

export default config;
