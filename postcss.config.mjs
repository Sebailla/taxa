/**
 * Root PostCSS config for the Next.js + Tailwind 4 build pipeline (PR 5.5).
 *
 * Registered plugin:
 *   - ``@tailwindcss/postcss`` — the official Tailwind 4 PostCSS plugin.
 *     It resolves the ``@import "tailwindcss";`` directive in
 *     ``src/app/globals.css``, expands the ``@theme { … }`` block into
 *     a corresponding ``:root, :host { … }`` declaration under
 *     ``@layer theme``, and emits the Tailwind 4 preflight + utility
 *     class surface for every utility referenced from the React source.
 *     Before PR 5.5 this config was absent — Turbopack's default
 *     PostCSS pipeline silently left the ``@import "tailwindcss";``
 *     directive unresolved, the ``@theme`` block was passed through as
 *     a literal at-rule (the browser silently drops it because
 *     ``@theme`` is not a real CSS at-rule), and the entire
 *     ``var(--token)`` cascade resolved to ``unset`` at runtime.
 *
 * No Tailwind 3-era plugins are registered — the PR 5.5 contract bans
 * every legacy Tailwind 3 plugin (the legacy ``web/index.css``
 * pipeline was retired by PR 3d; ``make css`` is now a successful
 * no-op that defers to ``next build``). See
 * ``openspec/changes/complete-taxa-frontend-migration/design.md`` §5.5.
 */
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
