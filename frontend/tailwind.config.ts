import type { Config } from "tailwindcss";

// Colores como variables CSS (ver app/globals.css) para que el modo oscuro
// cambie todo desde un solo lugar.
const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: v("canvas"),
        surface: v("surface"),
        sunken: v("sunken"),
        ink: v("ink"),
        muted: v("muted"),
        line: v("line"),
        deep: v("deep"),
        field: v("field"),
        "field-ink": v("field-ink"),
        leaf: v("leaf"),
        warn: v("warn"),
        "warn-bg": v("warn-bg"),
        "warn-ink": v("warn-ink"),
        crit: v("crit"),
        "crit-bg": v("crit-bg"),
        info: v("info"),
        "info-bg": v("info-bg"),
        tag: v("tag"),
      },
      fontFamily: {
        display: ['"Bricolage Grotesque Variable"', "system-ui", "sans-serif"],
        sans: ['"Public Sans Variable"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      borderRadius: { tag: "6px" },
    },
  },
  plugins: [],
} satisfies Config;
