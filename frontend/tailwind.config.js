/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
      },
      colors: {
        nexus: {
          bg: "#050813",
          surface: "#0d1117",
          card: "#111827",
          border: "#1f2937",
          accent: "#6366f1",
          "accent-glow": "#818cf8",
          cyan: "#22d3ee",
          emerald: "#10b981",
          amber: "#f59e0b",
          rose: "#f43f5e",
          muted: "#6b7280",
          text: "#f9fafb",
          "text-dim": "#9ca3af",
        },
      },
      backgroundImage: {
        "mesh-gradient":
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.15), transparent)",
        "card-gradient":
          "linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(34,211,238,0.04) 100%)",
        "node-active":
          "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(34,211,238,0.1))",
      },
      boxShadow: {
        "nexus-sm": "0 0 12px rgba(99,102,241,0.15)",
        "nexus-md": "0 0 24px rgba(99,102,241,0.2)",
        "nexus-lg": "0 0 48px rgba(99,102,241,0.25)",
        "nexus-glow": "0 0 60px rgba(99,102,241,0.35)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow": "spin 8s linear infinite",
        float: "float 6s ease-in-out infinite",
        "scan-line": "scan 4s linear infinite",
        "fade-in": "fadeIn 0.5s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
