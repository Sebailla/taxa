/**
 * Layout for the dedicated `/hydration-probe` route.
 *
 * ODD-ASN-001 — production isolation for the Playwright
 * witness. Two layers of defence:
 *
 * 1. **Search-engine exposure (server-rendered)** — the
 *    `metadata` export ships `<meta name="robots"
 *    content="noindex,nofollow">` in the static HTML, so the
 *    well-behaved crawlers skip the route without rendering it.
 *    Next.js's App Router auto-injects the meta tag from the
 *    `metadata` object; the route's static HTML now carries the
 *    noindex/nofollow pair at build time.
 *
 * 2. **Direct-URL exposure (client-rendered)** — the
 *    `<HydrationProbeGate />` client component wraps the route
 *    body. After mount, the gate reads
 *    `localStorage.taxa-internal-ok`; without the literal value
 *    ``"1"`` it replaces the probe body with a quiet fallback
 *    ("Internal witness — not part of the product.") and a link
 *    list to the canonical destinations. The Playwright
 *    harness seeds the flag via `context.add_init_script`
 *    BEFORE navigation, so the witness contract
 *    (`tests/test_hydration_console.py::test_hydration_probe_gate_allows_with_flag`
 *    + the static-HTML defaults witness
 *    `test_probe_static_html_uses_typed_defaults`) still holds
 *    for the test pipeline.
 *
 * Spec.md rule 5 — the gate is imported through the public
 * ``@taxa/browser-state`` barrel so this file does not deep-link
 * into the presentation layer.
 */
import type { ReactElement, ReactNode } from "react";
import type { Metadata } from "next";
import { HydrationProbeGate } from "@taxa/browser-state";

export const metadata: Metadata = {
  title: "Browser-state hydration probe",
  robots: {
    index: false,
    follow: false,
  },
};

export default function HydrationProbeLayout({
  children,
}: {
  readonly children: ReactNode;
}): ReactElement {
  return <HydrationProbeGate>{children}</HydrationProbeGate>;
}
