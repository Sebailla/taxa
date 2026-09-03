import type { Metadata, Viewport } from "next";
import { Raleway } from "next/font/google";

import { AppShell } from "@taxa/app-shell";

import "./globals.css";

/**
 * Root layout for the App Router static export (PR 3b + PR 3c-a + PR 4b).
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
 * PR 4b (hydration guard + AppShell integration seam) closes the second
 * dependency-defect fix: the AppShell lives in
 * ``src/modules/app-shell/presentation/AppShell.tsx`` (owned by PR 4b),
 * and this layout is where it gets composed into the App Router host.
 * The AppShell reads the typed ``@taxa/browser-state`` store behind the
 * ``useMounted()`` flag so SSR + initial CSR emit byte-identical markup
 * and React's hydration guard never trips.
 *
 * Chain-topology guard (PR 4b relaxation): this file NOW imports
 *   - ``@taxa/app-shell``        (owned by PR 4b — same PR)
 * The ``@taxa/browser-state`` import is transitive (AppShell -> typed
 * store), not direct, so the chain topology stays intact.
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
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}