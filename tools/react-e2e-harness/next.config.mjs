/**
 * Next.js configuration for the React E2E harness (PR 5c.2-B.1a).
 *
 * Mirrors the G2 static-export contract (design.md §3.3.2.1 / root
 * `next.config.mjs`):
 *   - `output: "export"`           — Next 16 static export required so the
 *                                     harness produces an `out/` directory the
 *                                     future capture driver can mount.
 *   - `images.unoptimized: true`   — static export cannot run the image
 *                                     optimisation server; disabling it is a
 *                                     hard requirement of `output: 'export'`.
 *   - `trailingSlash: false`       — matches the G2 contract.
 *   - `reactStrictMode: true`      — surface lifecycle / effect bugs during
 *                                     development.
 *
 * The harness deliberately does NOT add `transpilePackages`. The
 * `@taxa/*` aliases resolve to local source files under `../../src/modules/`
 * via `tsconfig.json::paths`; Next.js's bundler reads those paths directly.
 *
 * No app-shell integration, no FastAPI hooks, no production globals,
 * no `webpack` overrides — the harness is intentionally minimal.
 */
const nextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
  trailingSlash: false,
  reactStrictMode: true,
};

export default nextConfig;
