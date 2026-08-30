// Disposable G2 candidate workspace — see
// openspec/changes/migrate-nextjs-tailwind4/design.md §3.3.2.1.
// Self-contained build root. Does NOT wire FastAPI, web/, CI, root
// package.json, Makefile, or extension/manifest.json. Does NOT select
// Approach A / B / C. Does NOT select static export globally.

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: false,
};

export default nextConfig;
