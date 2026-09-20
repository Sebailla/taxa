// Browser-state infrastructure — typed localStorage-backed store
// for the **`taxa.tree.source`** storage key (CoL / WoRMS /
// Freshwater).
//
// spec.md rule 4: infrastructure depends on the domain (inward
// dependency) and owns the only `localStorage` call for the
// tree-source key. Every other capability module MUST reach
// storage through the typed public API exposed by
// `src/modules/browser-state/index.ts`.
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `infrastructure/store.ts` was replaced by one file
// per storage key so Turbopack can retain only the imported key's
// module chain. The main route imports `useTreeSource`, so the
// tree-source chain stays while the theme / last-taxon-id /
// kebab-open-id chains are dropped.
//
// This is the FIRST production consumer of the typed store in
// the main route (ODD-BSTATE-TAX-001) — `TaxonomyTree` reads +
// writes the active source through `useTreeSource()` from this
// file. The retention guarantee relies on this file NOT
// importing the sibling store files (theme / last-taxon-id /
// kebab-open-id); a future PR that pulls them in would silently
// re-bundle the forbidden keys into the main route's chunk.

import {
  DEFAULT_TREE_SOURCE,
} from "../domain/defaults";
// ODD-BSTATE-TAX-001-A — strict chunk-boundary contract. The
// typed-source chain (useTreeSource → storeTreeSource) MUST NOT
// pull `domain/keys.ts` at runtime, because that file also
// declares the three forbidden key literals
// (`taxa.settings.theme`, `taxa.tree.lastTaxonId`,
// `taxa.tree.kebabOpenId`). A shared chunk carrying all four
// literals would fail the
// `tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`
// check. Declaring the constant inline here keeps the typed-
// source chain independent — the chain reaches for one literal
// literal string and never imports the aggregate `keys.ts`.
//
// The canonical `TREE_SOURCE_STORAGE_KEY = "taxa.tree.source"`
// declaration in `domain/keys.ts` stays in place for the spec
// table preservation test
// (`tests/test_browser_state_keys.py::test_keys_file_declares_four_storage_key_literals`)
// + the public barrel re-export. A regression that drifts this
// local constant away from the canonical value trips the
// `test_tree_source_key_matches_domain_keys` pin below.
const TREE_SOURCE_STORAGE_KEY = "taxa.tree.source";
import type { Listener, Unsubscribe, TreeSource } from "../domain/keys";

// ---------------------------------------------------------------------------
// safeStorage helpers — wrap the two `localStorage` primitives in a
// try/catch so storage failures (private mode, quota, SSR) never
// propagate out of the typed store.
// ---------------------------------------------------------------------------

function safeGetItem(key: string): string | null {
  try {
    if (typeof window === "undefined") return null;
    const storage = window.localStorage;
    if (!storage) return null;
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key: string, value: string): void {
  try {
    if (typeof window === "undefined") return;
    const storage = window.localStorage;
    if (!storage) return;
    storage.setItem(key, value);
  } catch {
    // Quota exceeded / private mode — the in-memory cache still
    // updates, so the UI reflects the change for the current
    // session.
  }
}

// ---------------------------------------------------------------------------
// parse / serialize — coerce the raw `localStorage` string into
// the typed `TreeSource` value the public API exposes. Garbage
// values fall back to the typed default so a legacy write or a
// manual DevTools edit cannot corrupt the application state.
// ---------------------------------------------------------------------------

function parseTreeSource(raw: string | null): TreeSource {
  if (raw === "worms" || raw === "freshwater") return raw;
  return "col";
}

function serializeTreeSource(value: TreeSource): string {
  if (value === "worms" || value === "freshwater") return value;
  return "col";
}

// ---------------------------------------------------------------------------
// In-memory cache + per-key subscriber sets. Mirrors the contract
// documented on `storeTheme.ts`; the same hydrate-once semantics
// keep the SSR + first-client-render byte-equal (so React's
// hydration guard never trips on a stored value).
// ---------------------------------------------------------------------------

let cache: TreeSource = DEFAULT_TREE_SOURCE;
const listeners = new Set<Listener<TreeSource>>();

let hydrated = false;

function hydrateFromStorage(): void {
  cache = parseTreeSource(safeGetItem(TREE_SOURCE_STORAGE_KEY));
}

function ensureHydrated(): void {
  if (hydrated) return;
  hydrateFromStorage();
  hydrated = true;
}

/** Test seam — clear the in-memory cache + the hydrated flag. */
export function __resetForTests(): void {
  cache = DEFAULT_TREE_SOURCE;
  listeners.clear();
  hydrated = false;
}

// ---------------------------------------------------------------------------
// Read site — exactly one per key.
// ---------------------------------------------------------------------------

/** Read the active tree-source. Returns the typed default when
 *  storage is unavailable or the stored value is garbage. */
export function readTreeSource(): TreeSource {
  ensureHydrated();
  return cache;
}

// ---------------------------------------------------------------------------
// Write site — exactly one per key.
// ---------------------------------------------------------------------------

/** Write the active tree-source. Updates the in-memory cache +
 *  `localStorage` + fires every tree-source subscriber. */
export function writeTreeSource(next: TreeSource): void {
  ensureHydrated();
  cache = next;
  safeSetItem(TREE_SOURCE_STORAGE_KEY, serializeTreeSource(next));
  for (const listener of listeners) listener(next);
}

// ---------------------------------------------------------------------------
// Subscribe — typed listener per key.
// ---------------------------------------------------------------------------

/** Subscribe to tree-source changes. Returns an idempotent
 *  unsubscribe. */
export function subscribeTreeSource(
  listener: Listener<TreeSource>,
): Unsubscribe {
  ensureHydrated();
  listeners.add(listener);
  let active = true;
  return () => {
    if (!active) return;
    active = false;
    listeners.delete(listener);
  };
}
