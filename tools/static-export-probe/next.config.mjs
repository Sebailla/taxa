// Disposable static-export probe — see tools/static-export-probe/DESIGN.md.
// `output: 'export'` produces a fully static `out/`. `generateBuildId` is a
// deterministic function of the exact pinned tuple so capture.mjs can
// verify the build emitted the same buildId across runs.

import { createHash } from "node:crypto";

const PINNED_TUPLE = "next@16.3.3|react@19.2.8|react-dom@19.2.8";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
  generateBuildId: () => createHash("sha256").update(PINNED_TUPLE).digest("hex").slice(0, 16),
};

export default nextConfig;
