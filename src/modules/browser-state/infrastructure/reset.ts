// Browser-state infrastructure — aggregate `reset()`.
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `infrastructure/store.ts` was replaced by one file
// per storage key. The aggregate `reset()` affordance is the
// ONE module that crosses key boundaries: it must clear every
// key to its typed default AND remove every matching
// `localStorage` entry. It lives in its own file under
// `infrastructure/` so it can import all four sibling stores
// without the main route's bundle needing to follow.
//
// The main route MUST NOT import `reset`. The strict chunk-
// boundary contract (ODD-BSTATE-TAX-001-B) requires the main
// route's bundle to carry ONLY the typed-source chain; importing
// `reset` would pull the sibling stores (theme / last-taxon-id /
// kebab-open-id) into the same chunk and the forbidden localStorage
// key literals would re-appear alongside `taxa.tree.source`.
//
// Spec.md rule 5: cross-module consumers MUST import the reset
// affordance through the public barrel
// (`src/modules/browser-state/index.ts`); deep paths into the
// layer folders are blocked by `.eslintrc.cjs::no-restricted-imports`.
//
// Storage-isolation regression guard:
//   - Exactly four explicit `localStorage.removeItem` sites
//     (one per typed key) MUST stay in this file. The
//     `tests/test_browser_state_keys.py::test_browser_state_module_has_reset_remove_item_sites`
//     count assertion guards the contract: a future refactor
//     that consolidates the four sites into a loop would drop a
//     key without breaking the spec table, and the test catches
//     it before review.

import {
  DEFAULT_THEME,
  DEFAULT_TREE_SOURCE,
  DEFAULT_LAST_TAXON_ID,
  DEFAULT_KEBAB_OPEN_ID,
} from "../domain/defaults";
// ODD-BSTATE-TAX-001-A — strict chunk-boundary contract. The
// reset aggregate MUST declare each key constant inline so the
// sibling store chains stay independent of `domain/keys.ts` at
// runtime. The canonical declarations in `domain/keys.ts` stay
// in place for the spec table preservation test + the public
// barrel re-export — the two declarations are kept in sync by
// the ODD-BSTATE-TAX-001-B strict chunk-boundary witness
// itself (if any drift appears, the build would either embed a
// forbidden literal in an unrelated chunk or miss the
// permitted one).
const THEME_STORAGE_KEY = "taxa.settings.theme";
const TREE_SOURCE_STORAGE_KEY = "taxa.tree.source";
const LAST_TAXON_ID_STORAGE_KEY = "taxa.tree.lastTaxonId";
const KEBAB_OPEN_ID_STORAGE_KEY = "taxa.tree.kebabOpenId";

// ---------------------------------------------------------------------------
// Per-key subscribers — captured at module-load time. Each per-key
// store owns its own `List<Listener>`; we import the per-key stores
// here so we can fan the reset out across the four caches.
//
// Why the stores are imported (not the cached values themselves):
// the per-key stores fire listeners on every mutation; we want
// `reset()` to behave the same way it did in the monolithic
// version — fire every per-key subscriber synchronously with the
// new default so the React tree re-renders in one frame. Importing
// the singleton stores keeps the listener sets accessible to the
// aggregate without losing the per-key separation.
// ---------------------------------------------------------------------------
import {
  subscribeTheme as _subscribeTheme,
  writeTheme as _writeTheme,
} from "./storeTheme";
import {
  subscribeTreeSource as _subscribeTreeSource,
  writeTreeSource as _writeTreeSource,
} from "./storeTreeSource";
import {
  subscribeLastTaxonId as _subscribeLastTaxonId,
  writeLastTaxonId as _writeLastTaxonId,
} from "./storeLastTaxonId";
import {
  subscribeKebabOpenId as _subscribeKebabOpenId,
  writeKebabOpenId as _writeKebabOpenId,
} from "./storeKebabOpenId";

/** Reset every key to its typed default. Removes every matching
 *  `localStorage` entry (best-effort, swallowed on failure) and
 *  fires every subscriber. Used by the settings-view reset
 *  affordance; consumers MUST NOT call this directly without
 *  user intent — the typed defaults are a one-shot, deliberate
 *  state transition.
 *
 *  The aggregate fire-and-remove path uses each per-key store's
 *  own `write*` (updates the in-memory cache + fires its
 *  subscribers + persists the default) so the per-key store
 *  stays the single source of truth for every cache mutation.
 *  The explicit `localStorage.removeItem` sites below are the
 *  persistence-remove belt: every key is removed from
 *  `localStorage` verbatim so the next page load starts from
 *  the typed default instead of re-reading the previous value.
 */
export function reset(): void {
  // 1) In-memory reset + subscriber fan-out — route through each
  //    per-key store's writer so its cache + subscribers update
  //    in lock-step.
  _writeTheme(DEFAULT_THEME);
  _writeTreeSource(DEFAULT_TREE_SOURCE);
  _writeLastTaxonId(DEFAULT_LAST_TAXON_ID);
  _writeKebabOpenId(DEFAULT_KEBAB_OPEN_ID);

  // 2) Persistence remove — four explicit `localStorage.removeItem`
  //    sites, one per typed key. Inlined (instead of a
  //    `safeRemoveItem` loop) so the storage-ownership grep test
  //    counts exactly four `localStorage.removeItem` occurrences.
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.removeItem(THEME_STORAGE_KEY);
      window.localStorage.removeItem(TREE_SOURCE_STORAGE_KEY);
      window.localStorage.removeItem(LAST_TAXON_ID_STORAGE_KEY);
      window.localStorage.removeItem(KEBAB_OPEN_ID_STORAGE_KEY);
    }
  } catch {
    // Quota exceeded / private mode — the in-memory cache still
    // resets so the UI updates for the current session.
  }
}

// Re-export the subscribe shims so the per-key tests can build a
// listener fan-out without importing each per-key store directly.
// NOT re-exported through the public barrel — these are the
// aggregate-only escape hatch.
export {
  _subscribeTheme as subscribeTheme,
  _subscribeTreeSource as subscribeTreeSource,
  _subscribeLastTaxonId as subscribeLastTaxonId,
  _subscribeKebabOpenId as subscribeKebabOpenId,
};
