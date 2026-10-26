/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Figtree", "ui-sans-serif", "system-ui", "sans-serif"] },
      colors: {
        pine: { DEFAULT: "#1B4D43", dark: "#123830", soft: "#DCE9E5" },
        mist: "#EEF3F2",
        ink: "#1E2B28",
        amber: { vet: "#F2B544" },
      },
    },
  },
  plugins: [],
};
