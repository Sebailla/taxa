// PostCSS configuration for the Next.js 16 + Tailwind CSS v4 pipeline
// (ODD-TW-001 / `odd/tasks/repair-tailwind-next-pipeline.md`).
//
// The bundled Next 16 CSS guide at
// `node_modules/next/dist/docs/01-app/01-getting-started/11-css.md` requires
// the official `@tailwindcss/postcss` plugin and a single v4-only toolchain.
// The previous v3 plugin chain (`tailwindcss` + `autoprefixer`) was deleted
// alongside `tailwind.config.js` because v4 reads its configuration from
// `@theme` / `@source` directives in `src/app/globals.css`.
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
