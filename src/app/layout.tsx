import type { Metadata, Viewport } from "next";
import { Raleway } from "next/font/google";
// ODD-MIGRATE-007-DOM-006 — marker #5 (`#version-banner`). The legacy
// `web/index.html` mount shipped `<div id="version-banner" hidden>` with
// `#version-banner-actual` + `#version-banner-expected` spans that JS
// populates from `/api/health`. The React root layout mirrors the
// server-rendered DOM contract via Next 16's `<Script>` component (see
// `node_modules/next/dist/docs/01-app/03-api-reference/02-components/script.md`)
// — the banner host renders statically in the SSR markup, and a tiny
// inline `<Script strategy="afterInteractive">` fetches `/api/health`
// after hydration, writes the schema-version literals into the two
// spans, and flips `hidden={false}` when the DB schema is older than
// the API's expected version. The layout stays a server component;
// the inline script is the only client-side touchpoint.
import Script from "next/script";

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
   <body>
    {/*
     * G4 candidate probe marker — approved issue #245.
     * The capture producer pins `data-testid="g4-probe-marker"` in
     * `tests/fixtures/g4/corpus/manifest.json` and looks it up via the
     * literal DOM marker gate before the runner fires. The element is
     * fully static, hydration-safe (string literal test-id, no
     * expressions, no handlers, no text content), hidden via the
     * HTML5 `hidden` attribute (which sets `display: none` AND removes
     * the element from the accessibility tree), and uses a
     * non-focusable `<span>` with no `tabIndex` so it cannot shift
     * tab order. Adding it here does not import owners of later PRs
     * (`@taxa/app-shell`, `@taxa/browser-state`) — the chain-topology
     * guard in `tests/test_app_shell_render.py` stays green.
     */}
    <span hidden data-testid="g4-probe-marker" />
    {/*
     * ODD-MIGRATE-007-DOM-006 — marker #5 (`#version-banner`). The
     * banner host renders statically in the SSR markup so the legacy
     * Playwright probe finds `#version-banner` byte-for-byte. The
     * spans start with the literal `?` placeholder (matching the
     * legacy `web/index.html` cascade); the inline `<Script>` below
     * fetches `/api/health` after hydration, writes the actual /
     * expected schema-version literals into the spans, and flips
     * `hidden={false}` when the DB schema is older than the API's
     * expected version. The banner stays hidden when the schema is
     * current (the canonical "no-op" path).
     */}
    <div
      id="version-banner"
      hidden
      role="status"
      aria-live="polite"
      data-version-banner=""
      data-version-banner-actual=""
      data-version-banner-expected=""
    >
      <span id="version-banner-actual">?</span>
      <span id="version-banner-expected">?</span>
    </div>
    <Script id="version-banner-loader" strategy="afterInteractive">
      {`fetch('/api/health').then(function(r){return r.json()}).then(function(d){var b=document.getElementById('version-banner');var a=document.getElementById('version-banner-actual');var e=document.getElementById('version-banner-expected');if(a){a.textContent=String(d.db_schema_version);}if(e){e.textContent=String(d.expected_schema_version);}if(b&&d.db_schema_version<d.expected_schema_version){b.hidden=false;b.setAttribute('data-version-banner-actual',String(d.db_schema_version));b.setAttribute('data-version-banner-expected',String(d.expected_schema_version));}}).catch(function(){});`}
    </Script>
    {children}
   </body>
  </html>
 );
}
