/**
 * Next.js configuration for the App Router static export (PR 3b).
 *
 * Pins the G2 contract (design.md §3.3.2.1):
 *   - ``output: "export"``           — Next 16 static export required for the
 *                                       FastAPI ``StaticFiles(html=True)`` mount
 *                                       to serve ``out/index.html``.
 *   - ``images.unoptimized: true``   — static export cannot run the image
 *                                       optimisation server; disabling it is
 *                                       a hard requirement of ``output: 'export'``.
 *   - ``trailingSlash: false``       — matches the G2 contract; the FastAPI
 *                                       mount treats ``out/index.html`` as
 *                                       the SPA entry without a redirect.
 *   - ``reactStrictMode: true``      — surface lifecycle / effect bugs during
 *                                       development; static export keeps the
 *                                       setting for parity with the predecessor.
 *
 * Tailwind 4 (PR 3c), the typed-store hydration guard (PR 4a/4b), and the
 * capability ports (PR 5a/5b/5c) extend this config in their own sub-PRs;
 * none of them land in PR 3b.
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