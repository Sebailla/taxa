/**
 * Dedicated hydration-probe route.
 *
 * ODD-BSTATE-PW-001 — the isolated witness route for the typed
 * browser-state hooks. Mounts the `<HydrationProbe />` presentation
 * component directly so the static export carries the probe at
 * `out/hydration-probe.html`, reachable through an isolated static
 * HTTP server.
 *
 * Spec.md rule 5 — the probe is consumed through the public browser-
 * state barrel so this file stays free of deep imports into the
 * presentation / application / domain / infrastructure layers of
 * `browser-state`. The barrel exposes the typed surface only; the
 * probe is the single presentation component the barrel re-exports
 * and exists exclusively for this witness.
 *
 * Boundary guarantee: this route is the ONLY route under `src/app/`
 * that mounts browser-state consumers. The main index route
 * (`src/app/page.tsx`) stays free of `@taxa/browser-state` so the
 * static chunks the main route loads remain browser-state free —
 * `tests/test_app_shell_render.py::test_out_index_html_chunks_reference_no_browser_state`
 * pins the contract.
 */
import { HydrationProbe } from "@taxa/browser-state";

export default function HydrationProbePage(): React.ReactElement {
  return <HydrationProbe />;
}
