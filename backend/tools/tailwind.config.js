/**
 * Tailwind build config — used by tools/build-tailwind.sh
 *
 * The app no longer loads cdn.tailwindcss.com (a 398 KB JIT compiler that ran
 * in the browser on every page load). Instead app/static/assets/css/tailwind.css
 * is pre-built here and shipped as a normal stylesheet (49 KB, 9 KB gzipped).
 *
 * IMPORTANT: utility classes are discovered by scanning the files listed in
 * `content`. If you add a new Tailwind class anywhere in the HTML or JS,
 * re-run tools/build-tailwind.sh or that class will have no CSS rule.
 */
module.exports = {
  content: [
    '../app/static/**/*.html',
    '../app/static/assets/js/**/*.js'
  ],
  darkMode: 'class',
  theme: { extend: {} },
  corePlugins: { preflight: true },
  plugins: []
};
