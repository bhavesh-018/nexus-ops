/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0b0d11",
        surface: "#11141b",
        panel: "#171b24",
        border: "#252b36"
      }
    }
  },
  plugins: []
};
