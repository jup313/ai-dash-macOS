/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        dash: {
          bg: "#0f1117",
          surface: "#1a1d27",
          border: "#2a2d3a",
          accent: "#6366f1",
          "accent-hover": "#818cf8",
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#ef4444",
          muted: "#6b7280",
          text: "#e5e7eb",
          "text-dim": "#9ca3af",
        },
      },
    },
  },
  plugins: [],
};
