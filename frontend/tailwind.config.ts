import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        call: "#16a34a",
        put: "#dc2626",
        wait: "#eab308",
        panel: "#0f1115",
        panelBorder: "#1f232b",
      },
    },
  },
  plugins: [],
};
export default config;
