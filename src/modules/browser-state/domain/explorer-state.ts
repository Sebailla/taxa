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
 *  coercing a future shape). Pinned to `1` for the
 *  initial release; bump + add a guard on subsequent
 *  releases.
 *
 *  Lives here (NOT in `infrastructure/storeExplorerState.ts`)
 *  so the canonical version literal stays reachable through
 *  the typed hand-off surface. The browser-state chain is the
 *  single source of truth for the EXPLORER-PERSIST contract;
 *  the research-side helper module (`src/modules/research/
 *  presentation/explorer-storage.ts`) declares a LOCAL
 *  MIRROR of this constant + the four bound caps + the
 *  storage key literal so the pure parse / serialize /
 *  validate helpers compile in isolation (the focused
 *  runtime harness does not depend on the
 *  `@taxa/browser-state` path-alias resolution). The mirror
 *  is kept in lock-step with this canonical declaration by
 *  the source-level parity test
 *  (`tests/test_research_explorer_mount.py::
 *  test_w6_4_storage_version_matches_canonical_browser_state_literal`),
 *  not by a re-export — the pure-helper mirror is
 *  intentionally a SOURCE-LEVEL copy so a future PR that
 *  converts the mirror to a deep import can replace the
 *  test with a typing assertion. The test-time parity
 *  guard catches every drift at review time so the focused
 *  runtime harness stays focused on the runtime contract. */
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
// ODD-BSTATE-EXPLORER-PERSIST-BOUNDS — canonical cap constants.
//
// The persistence-boundary regression suite pins these four
// values byte-for-byte against the pure Research-side helper
// (`src/modules/research/presentation/explorer-storage.ts`).
// The helper is the read-only reference; the per-key store
// (`infrastructure/storeExplorerState.ts`) is the real
// read/write boundary that enforces the caps. The values
// are kept in sync so a stale / malformed / oversized record
// hydrates to the canonical empty default and an out-of-bound
// write is rejected at the boundary without calling
// `localStorage.setItem`.
// ---------------------------------------------------------------------------

/** Hard byte cap on the serialized record. A pathological
 *  user (a deeply nested tree path that exceeds the cap)
 *  is rejected at the boundary instead of silently bloating
 *  `localStorage`. The cap is a sane `localStorage` value
 *  (≤ 1 MiB) so the persisted record stays well under
 *  every browser's practical per-origin quota. 64 KiB
 *  leaves headroom for future PRs without overflowing the
 *  quota. The parser fires the check BEFORE `JSON.parse`
 *  with the conservative `raw.length * 3` wire-byte
 *  estimate (a UTF-16 code unit is exactly 2 bytes; the
 *  multiplier 3 covers the worst case of multibyte UTF-8
 *  expansion). */
export const MAX_EXPLORER_STATE_BYTES = 65536;

/** Hard cap on the number of expanded folder paths in
 *  the persisted record. A pathological user (a session
 *  that expanded every folder in a 10k-folder tree) is
 *  rejected at the boundary instead of silently bloating
 *  `localStorage`. The cap is well above a realistic
 *  user's working set (typical session < 100 expanded
 *  folders). */
export const MAX_EXPANDED_PATHS = 1000;

/** Hard cap on the search-query string length. The legacy
 *  search input accepts arbitrary strings; the cap is a
 *  defensive bound on the persisted record so a
 *  pathological user (a 1 MiB paste) is rejected at the
 *  boundary instead of silently bloating `localStorage`.
 *  256 chars is well above a realistic search query. */
export const MAX_QUERY_LENGTH = 256;

/** Hard cap on the selected-path string length AND on
 *  every individual expanded-path entry. Tree paths are
 *  bounded by FastAPI's `_walk_tree` depth cap; the cap is
 *  a defensive bound on the persisted record so a
 *  pathological payload is rejected at the boundary
 *  instead of silently bloating `localStorage`. 1024 chars
 *  is well above a realistic tree path. The same constant
 *  guards both the `selectedPath` field and each entry in
 *  `expandedPaths` so a single 1025-char path cannot
 *  sneak through the count check on the array. */
export const MAX_SELECTED_PATH_LENGTH = 1024;

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