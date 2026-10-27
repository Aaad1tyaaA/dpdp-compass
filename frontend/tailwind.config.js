import animate from "tailwindcss-animate"
import typography from "@tailwindcss/typography"

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: { center: true, padding: "1rem", screens: { "2xl": "1152px" } },
    extend: {
      // Nothing smaller than ~14px at the 18px root: xs and sm are raised for older readers.
      fontSize: { xs: ["0.8125rem", { lineHeight: "1.25rem" }], sm: ["0.875rem", { lineHeight: "1.4rem" }] },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        success: { DEFAULT: "hsl(var(--success))", foreground: "hsl(var(--success-foreground))" },
        warning: { DEFAULT: "hsl(var(--warning))", foreground: "hsl(var(--warning-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        saffron: "hsl(var(--signal))",
        signal: { DEFAULT: "hsl(var(--signal))", foreground: "hsl(var(--signal-foreground))" },
        marker: "hsl(var(--marker))",
      },
      fontFamily: {
        sans: ["Atkinson Hyperlegible", "ui-sans-serif", "system-ui", "Segoe UI", "Nirmala UI", "sans-serif"],
        mono: ["ui-monospace", "Consolas", "monospace"],
        display: ["Atkinson Hyperlegible", "ui-sans-serif", "sans-serif"],
      },
      // Gently rounded corners everywhere; full circles stay circles.
      borderRadius: { DEFAULT: "var(--radius)", sm: "var(--radius)", md: "var(--radius)", lg: "var(--radius)", xl: "var(--radius)", "2xl": "var(--radius)", "3xl": "var(--radius)" },
      boxShadow: {
        soft: "0 1px 2px 0 rgb(0 0 0 / 0.06)",
        lift: "0 2px 8px -2px rgb(0 0 0 / 0.12)",
        glow: "none",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        caret: { "0%, 100%": { opacity: "1" }, "50%": { opacity: "0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.22s cubic-bezier(0.32, 0.72, 0, 1)",
        "accordion-up": "accordion-up 0.18s cubic-bezier(0.32, 0.72, 0, 1)",
        caret: "caret 1s step-end infinite",
      },
    },
  },
  plugins: [animate, typography],
}
