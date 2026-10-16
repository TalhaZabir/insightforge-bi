/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 950: "#0A1628", 900: "#0F1F3A", 800: "#1A2F52" },
        teal: { 500: "#14B8A6", 600: "#0D9488" }
      }
    }
  },
  plugins: []
};
