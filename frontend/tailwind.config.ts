import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172321",
        muted: "#73817d",
        canvas: "#f4f6f3",
        forest: "#1d5448",
        mint: "#dceee6",
        line: "#e5eae6",
        amber: "#b97927",
        rose: "#a84d4d",
      },
      boxShadow: {
        soft: "0 8px 30px rgba(23, 35, 33, .05)",
      },
      fontFamily: {
        sans: ["Arial", "Helvetica", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
