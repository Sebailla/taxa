// Browser-state domain — typed defaults for the four storage keys.
//
// spec.md rule 4: domain stays free of presentation, application,
// browser, HTTP, framework, or infrastructure. Defaults are
// PURELY TypeScript constants so the SSR snapshot (`useSyncExternalStore`'s
// `getServerSnapshot`) and the first client render BEFORE the
// store rehydrates from `localStorage` both return the SAME typed
// default — the React hydration guard never trips on a stored
// value.
//
// The defaults mirror the `browser-state-hydration` spec table:
//   - theme         → "light"
//   - tree-source   → "col"
//   - last-taxon-id → null
//   - kebab-open-id → null
//
// A future PR that changes a default must update both the spec
// table AND the legacy `web/state.js::initialState` value; the
// two are wired through the migration's parity contract.

import type { Theme, TreeSource } from "./keys";

/** Theme default — `light` (the spec table). */
export const DEFAULT_THEME: Theme = "light";

/** Tree-source default — `col` (the spec table; the legacy
 *  `web/app.js::boot` picks CoL as the source unless the
 *  `?source=worms` query param is present). */
export const DEFAULT_TREE_SOURCE: TreeSource = "col";

/** Last-taxon-id default — `null` (no taxon focused on first
 *  paint; the URL is updated to `?taxon=<id>` after rehydration
 *  only if a stored id exists). */
export const DEFAULT_LAST_TAXON_ID: number | null = null;

/** Kebab-open-id default — `null` (no kebab menu open on first
 *  paint; the kebab closes on every reload by design). */
export const DEFAULT_KEBAB_OPEN_ID: number | null = null;
