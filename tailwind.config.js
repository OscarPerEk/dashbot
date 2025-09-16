/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./dashbot/templates/**/*.html",
  ],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
}


