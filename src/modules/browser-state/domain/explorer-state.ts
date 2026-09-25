// Browser-state domain — typed `PersistedExplorerState` shape
// for the EXPLORER-PERSIST Browser-tab Explorer working-set
// persistence chain.
//
// spec.md rule 4: domain stays free of presentation, application,
// browser, HTTP, framework, or infrastructure. This file is
// purely TypeScript identifiers + the typed shape — no
// `localStorage` access, no React, no Node process. The
// infrastructure layer (`infrastructure/storeExplorerState.ts`)
// owns the actual `getItem` / `setItem` / `removeItem` calls so
// storage failures (private mode / quota exceeded) stay isolated
// from the consumer API and the typed default stays reachable
// when `window` is unavailable (SSR / build-time prerender).
//
// ODD-BSTATE-EXPLORER-PERSIST — the EXPLORER-PERSIST
// architecture correction moves the Browser-tab Explorer
// working-set persistence behind the canonical per-key
// browser-state store (`infrastructure/storeExplorerState.ts`).
// The previous design owned the raw `taxa.fex.explorerState`
// localStorage key inside `src/modules/research/presentation/explorer-storage.ts`;
// the correction routes every localStorage I/O through this
// chain so the Research module is free of `localStorage.*`
// references (the architecture guard at
// `tests/test_browser_state_keys.py::test_other_module_does_not_touch_localstorage[research]`
// now passes without a research-side carveout).
//
// The shape mirrors the working set the React Explorer mount
// restores on mount (search query + selected path + expanded
// folder paths). Every field is `readonly` so a future reducer
// / store can rely on immutable updates; mutation belongs to
// the application layer (`application/useExplorerState.ts`),
// NOT here. The shape is intentionally NARROWER than the
// full `ExplorerState` (the viewer tab, the open file, the
// search mode + hideEmpty are session-only — they're either
// ephemeral viewer state or mode toggles that should not
// survive a reload).

import type { Listener, Unsubscribe } from "./keys";

/** Version literal carried in the persisted record. The
 *  serializer writes the version; the parser reads +
 *  validates it; a future PR that bumps the version gets
 *  a clean discard path (`parseExplorerState` returns
 *  `null` for unknown versions instead of silently
 *  coercing a future shape). Pinned to `1 for the
 *  initial release; bump + add a guard on subsequent
 *  releases.
 *
 *  Lives here (NOT in `infrastructure/storeExplorerState.ts`)
 *  so the canonical version literal stays reachable through
 *  the typed hand-off surface. The browser-state chain is the
 *  single source of truth for the EXPLORER-PERSIST contract;
 *  the research-side module re-exports it from this file so
 *  the public barrels stay in sync without a future drift. */
export const EXPLORER_STATE_STORAGE_VERSION = 1;

/** The pure typed shape of the persisted record. Mirrors
 *  the React state we persist (search query + selected
 *  path + expanded paths). Every field is `readonly` so a
 *  future consumer cannot mutate the parsed record by
 *  accident. The shape is framework-free + I/O-free; the
 *  storage helpers (`readExplorerState` /
 *  `writeExplorerState` / `subscribeExplorerState`) wrap
 *  it. */
export interface PersistedExplorerState {
  readonly version: number;
  readonly query: string;
  readonly selectedPath: string | null;
  readonly expandedPaths: readonly string[];
}

/** Pure factory: produce a fresh, empty
 *  `PersistedExplorerState` with the current
 *  `EXPLORER_STATE_STORAGE_VERSION` literal. Mirrors the
 *  W6.4 `createEmptyPersistedExplorerState` factory — a
 *  stable typed handle for the trivial cases so the
 *  infrastructure store can short-circuit with a fresh
 *  object instead of an inline literal. The
 *  `expandedPaths` array is a fresh per-call allocation
 *  (no shared references) so a future presentation-only
 *  consumer can mutate locally without bleeding into a
 *  sibling. */
export function createEmptyPersistedExplorerState(): PersistedExplorerState {
  return {
    version: EXPLORER_STATE_STORAGE_VERSION,
    query: "",
    selectedPath: null,
    expandedPaths: [],
  };
}

// ---------------------------------------------------------------------------
// Re-export the generic Listener / Unsubscribe aliases so the
// infrastructure store + the application hook can read the typed
// `Listener<PersistedExplorerState>` shape without a deep import
// into `../domain/keys`. The alias surface stays export-only —
// no runtime indirection — so Turbopack's tree-shaking decision
// remains file-bound (a future bundling regression that picks up
// this file would only re-export the alias types, NOT the four
// sibling key literals from `domain/keys.ts`).
// ---------------------------------------------------------------------------
export type { Listener, Unsubscribe };