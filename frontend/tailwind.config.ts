import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/data/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        line: "#d7e2ef",
        panel: "#f7fbff",
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#1677ff",
          600: "#0b63e5",
          700: "#064eb8"
        },
        teal: {
          50: "#ecfdf8",
          500: "#13a897",
          700: "#0b7f75"
        }
      },
      boxShadow: {
        soft: "0 10px 28px rgba(15, 23, 42, 0.08)",
        card: "0 1px 0 rgba(15, 23, 42, 0.04), 0 10px 30px rgba(15, 23, 42, 0.07)"
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans TC", "Segoe UI", "Arial", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
