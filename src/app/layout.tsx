import type { Metadata, Viewport } from "next";
import { Raleway } from "next/font/google";

import "./globals.css";

/**
 * Root layout for the App Router static export (PR 3b + PR 3c-a).
 *
 * Self-contained minimum that satisfies the G2 markup contract (design.md
 * §3.3.2.1): ``<html lang="en">``, the responsive viewport meta, and the
 * Raleway ``<link rel="preload">`` emitted by ``next/font/google``.
 *
 * PR 3c-a (tokens / base / dark mode) closes the dependency-defect-fix seam
 * by adding the ``import "./globals.css"`` line: PR 3b originally imported
 * this file, but globals.css did not exist yet (PR 3c-a ships it). The
 * Tailwind 4 ``@import "tailwindcss"`` directives now flow into the Next.js
 * build, and the @theme + @layer base tokens cascade through `next build`'s
 * generated CSS chunk.
 *
 * Chain-topology guard: this file MUST NOT import
 *   - ``@taxa/app-shell``        (owned by PR 4b)
 *   - ``@taxa/browser-state``    (owned by PR 4a)
 * Doing so would invert the chain's dependency order. Subsequent PRs extend
 * the shell — they do not pre-empt the bootstrap.
 */
const raleway = Raleway({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
  variable: "--font-raleway",
});

export const metadata: Metadata = {
  title: "taxa",
  description:
    "Local Catalogue of Life + WoRMS marine overlay powering a research web.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <html lang="en" className={raleway.variable}>
      <body>{children}</body>
    </html>
  );
}