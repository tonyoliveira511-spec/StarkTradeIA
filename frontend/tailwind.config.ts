import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Sinal — tons dessaturados, não neon (evita o clichê "preto + acento vibrante")
        call: "#2F9E68",
        callDim: "#1D6B45",
        put: "#C1443C",
        putDim: "#8A302A",
        wait: "#D9A441",
        waitDim: "#9C7730",
        // Marca — latão, usado com moderação
        brass: "#C9A227",
        brassDim: "#8F7420",
        // Base — carvão quente, não preto puro
        ink: "#14161B",
        panel: "#1C1F26",
        panelRaised: "#22252D",
        panelBorder: "#2A2E38",
        ash: "#8B90A0",
        ashDim: "#5A5F6E",
        paper: "#E9E7E0",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "system-ui", "sans-serif"],
        body: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        data: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
