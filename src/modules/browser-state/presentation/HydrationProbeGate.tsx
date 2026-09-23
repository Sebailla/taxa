"use client";

/**
 * HydrationProbeGate — production guard for the isolated
 * `/hydration-probe` route (ODD-ASN-001).
 *
 * The static export ships the probe's HTML to every visitor
 * because ``next build`` pre-renders the route during the
 * static-export pass. A client-only guard is the only way to
 * keep the Playwright witness contract (`out/hydration-probe.html`
 * still carries the probe body so the existing hydration
 * assertions in `tests/test_hydration_console.py` continue to
 * hold) AND close direct-URL exposure from non-test visitors.
 *
 * Behaviour:
 *   - Initial state is ``"pending"`` so SSR + the first client
 *     render agree byte-for-byte — the static HTML witness
 *     contract is preserved (the probe body ships in the
 *     document markup).
 *   - After mount, a `useEffect` reads the internal flag via
 *     `readInternalFlag()` from the typed browser-state store
 *     (`@taxa/browser-state`). The literal string ``"1"`` flips
 *     state to ``"allowed"``; any other value, a missing key,
 *     OR a thrown `localStorage` access (private browsing,
 *     blocked storage, etc.) flips state to ``"denied"``.
 *     Storage access is centralised in the typed store so the
 *     presentation layer stays free of `localStorage.*`
 *     references (the ODD-BSTATE-TAX-001 storage-ownership
 *     contract).
 *   - ``"allowed"`` and ``"pending"`` both render ``<>{children}</>``
 *     — the probe body ships untouched so the witness contract
 *     holds for the Playwright harness (which seeds the flag via
 *     `context.add_init_script` before navigation).
 *   - ``"denied"`` renders a quiet fallback that explains the
 *     route is an internal witness, carries the canonical
 *     "Internal witness — not part of the product." heading,
 *     and links to the three product surfaces
 *     (Classification / Browser / Help) so a real visitor has a
 *     path forward.
 *
 * Spec.md rule 5: this component is exported through the public
 * ``@taxa/browser-state`` barrel so the dedicated
 * `src/app/hydration-probe/layout.tsx` can mount it via
 * `import { HydrationProbeGate } from "@taxa/browser-state";`
 * without deep-importing the presentation layer. The flag read
 * goes through the same public barrel
 * (`import { readInternalFlag } from "@taxa/browser-state";`)
 * so the storage-ownership contract holds end-to-end.
 */
import { useEffect, useState, type ReactElement, type ReactNode } from "react";
import { readInternalFlag } from "@taxa/browser-state";

type GateState = "pending" | "allowed" | "denied";

export interface HydrationProbeGateProps {
  readonly children: ReactNode;
}

export default function HydrationProbeGate({
  children,
}: HydrationProbeGateProps): ReactElement {
  const [state, setState] = useState<GateState>("pending");

  useEffect(() => {
    setState(readInternalFlag() ? "allowed" : "denied");
  }, []);

  if (state === "denied") {
    return (
      <main
        data-hydration-probe-gate="denied"
        style={{
          minHeight: "100vh",
          padding: "48px 24px",
          background: "var(--surface, #ffffff)",
          color: "var(--on-surface, #1a1a1a)",
          fontFamily: "'Raleway', system-ui, sans-serif",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: "16px",
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: "1.5rem",
            fontWeight: 600,
            color: "var(--on-surface, #1a1a1a)",
          }}
        >
          Internal witness — not part of the product.
        </h1>
        <p
          style={{
            margin: 0,
            maxWidth: "60ch",
            color: "var(--on-surface-variant, #555555)",
            lineHeight: 1.5,
          }}
        >
          This route exists for the test suite to witness the static-export
          hydration contract in headless Chromium. It is not a product
          surface and will not be wired into the live navigation.
        </p>
        <p
          style={{
            margin: "8px 0 0 0",
            color: "var(--on-surface-variant, #555555)",
          }}
        >
          Pick a destination:
        </p>
        <ul
          style={{
            margin: 0,
            padding: 0,
            listStyle: "none",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <li>
            <a
              href="/"
              style={{
                color: "var(--primary, #2563eb)",
                textDecoration: "underline",
              }}
            >
              Classification
            </a>
          </li>
          <li>
            <a
              href="/explorer"
              style={{
                color: "var(--primary, #2563eb)",
                textDecoration: "underline",
              }}
            >
              Browser
            </a>
          </li>
          <li>
            <a
              href="/help"
              style={{
                color: "var(--primary, #2563eb)",
                textDecoration: "underline",
              }}
            >
              Help
            </a>
          </li>
        </ul>
      </main>
    );
  }

  return <>{children}</>;
}
