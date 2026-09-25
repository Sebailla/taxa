// Browser-state domain — typed defaults for the storage keys.
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
// ODD-BSTATE-EXPLORER-PERSIST — the canonical default family
// grows by one entry after the EXPLORER-PERSIST architecture
// correction. The explorer-state default points at a fresh
// empty `PersistedExplorerState` (the canonical factory from
// `domain/explorer-state.ts`) so the typed surface stays
// framework-free, I/O-free, and consistent across SSR + the
// first client render.
//
// A future PR that changes a default must update both the spec
// table AND the legacy `web/state.js::initialState` value; the
// two are wired through the migration's parity contract.

import type { Theme, TreeSource } from "./keys";
import {
  createEmptyPersistedExplorerState,
  EXPLORER_STATE_STORAGE_VERSION,
} from "./explorer-state";
import type { PersistedExplorerState } from "./explorer-state";

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

/** ODD-BSTATE-EXPLORER-PERSIST — typed explorer-state default.
 *  Points at a fresh empty `PersistedExplorerState` (the
 *  canonical factory from `domain/explorer-state.ts`) so the
 *  SSR + first-render hydration snapshot matches the typed
 *  default without a stored-value race. The factory is
 *  re-exported from this module so the typed surface stays in
 *  one place; the default constant is the typed hand-off the
 *  React layer reads through `useExplorerState` / `readExplorerState`.
 *
 *  The `version` literal is the current
 *  `EXPLORER_STATE_STORAGE_VERSION` so a future PR that bumps
 *  the version does not have to chase the default constant
 *  through `domain/explorer-state.ts`. */
export const DEFAULT_EXPLORER_STATE: PersistedExplorerState = {
  version: EXPLORER_STATE_STORAGE_VERSION,
  query: "",
  selectedPath: null,
  expandedPaths: [],
};

// Re-export the empty-record factory so the typed surface
// stays reachable from this module (the chain's primary
// typed hand-off). NOT re-exported through the public
// barrel (the per-file rationale mirrors the sibling
// stores — cross-key exports would defeat the chunk-boundary
// isolation).
export { createEmptyPersistedExplorerState };
