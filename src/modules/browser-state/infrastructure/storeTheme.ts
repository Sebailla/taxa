// Browser-state infrastructure — typed localStorage-backed store
// for the **`taxa.settings.theme`** storage key.
//
// spec.md rule 4: infrastructure depends on the domain (inward
// dependency) and owns the only `localStorage` call for the theme
// key. Every other capability module MUST reach storage through
// the typed public API exposed by `src/modules/browser-state/index.ts`.
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `infrastructure/store.ts` was replaced by one file
// per storage key so Turbopack can retain only the imported key's
// module chain. The main route imports `useTreeSource`, so the
// tree-source chain stays while the theme / last-taxon-id /
// kebab-open-id chains are dropped.
//
// Why the localStorage calls are guarded by a try/catch:
//   - SSR (`window === undefined`): the static export prerenders
//     pages without a browser. A direct `localStorage.getItem`
//     would throw `ReferenceError` and break the build. The store
//     returns the typed default when `window` is missing.
//   - Private browsing / quota exceeded: the browser throws on
//     `setItem` / `removeItem`. The store swallows the exception
//     so the in-memory state still updates and the UI reflects
//     the user's choice for the current session.

import {
  DEFAULT_THEME,
} from "../domain/defaults";
// ODD-BSTATE-TAX-001-A — strict chunk-boundary contract. The
// theme chain MUST NOT pull `domain/keys.ts` at runtime because
// that file also declares the three sibling key literals. A
// shared chunk carrying all four literals would fail the
// `tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`
// check. Declaring the constant inline here keeps the chain
// independent.
//
// The canonical `THEME_STORAGE_KEY = "taxa.settings.theme"`
// declaration in `domain/keys.ts` stays in place for the spec
// table preservation test
// (`tests/test_browser_state_keys.py::test_keys_file_declares_four_storage_key_literals`)
// + the public barrel re-export.
const THEME_STORAGE_KEY = "taxa.settings.theme";
import type { Listener, Unsubscribe, Theme } from "../domain/keys";

// ---------------------------------------------------------------------------
// safeStorage helpers — wrap the two `localStorage` primitives in a
// try/catch so storage failures (private mode, quota, SSR) never
// propagate out of the typed store. The read site routes through
// `safeGetItem`; the write site routes through `safeSetItem`.
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
// the typed `Theme` value the public API exposes. Garbage values
// fall back to the typed default so a legacy write or a manual
// DevTools edit cannot corrupt the application state.
// ---------------------------------------------------------------------------

function parseTheme(raw: string | null): Theme {
  return raw === "dark" ? "dark" : "light";
}

function serializeTheme(value: Theme): string {
  return value === "dark" ? "dark" : "light";
}

// ---------------------------------------------------------------------------
// In-memory cache + per-key subscriber sets.
//
// The cache mirrors what `localStorage` last returned (or the
// typed default if storage is unavailable). Every read / write /
// subscribe path goes through `ensureHydrated` so the cache is
// populated lazily — exactly once per page load — and the typed
// default is what SSR + the first client render return.
//
// Subscribers fire synchronously on every mutation regardless
// of whether the persistent write succeeded. That keeps the
// React tree in sync with the in-memory state even when storage
// is unavailable.
// ---------------------------------------------------------------------------

let cache: Theme = DEFAULT_THEME;
const listeners = new Set<Listener<Theme>>();

let hydrated = false;

function hydrateFromStorage(): void {
  cache = parseTheme(safeGetItem(THEME_STORAGE_KEY));
}

function ensureHydrated(): void {
  if (hydrated) return;
  hydrateFromStorage();
  hydrated = true;
}

/** Test seam — clear the in-memory cache + the hydrated flag
 *  so a test can simulate a fresh page load. NOT exported
 *  through the public barrel. */
export function __resetForTests(): void {
  cache = DEFAULT_THEME;
  listeners.clear();
  hydrated = false;
}

// ---------------------------------------------------------------------------
// Read site — exactly one per key (the storage-ownership
// contract). The four-key count lives in
// `tests/test_browser_state_keys.py::test_browser_state_module_has_exactly_four_read_sites`.
// ---------------------------------------------------------------------------

/** Read the active theme. Returns the typed default when storage
 *  is unavailable (SSR / private mode) or the stored value is
 *  garbage. */
export function readTheme(): Theme {
  ensureHydrated();
  return cache;
}

// ---------------------------------------------------------------------------
// Write site — exactly one per key. Subscribers fire
// synchronously on every mutation, regardless of whether the
// persistent write succeeded.
// ---------------------------------------------------------------------------

/** Write the active theme. Updates the in-memory cache + the
 *  `localStorage` entry (best-effort, swallowed on failure) +
 *  fires every theme subscriber synchronously. */
export function writeTheme(next: Theme): void {
  ensureHydrated();
  cache = next;
  safeSetItem(THEME_STORAGE_KEY, serializeTheme(next));
  for (const listener of listeners) listener(next);
}

// ---------------------------------------------------------------------------
// Subscribe — typed listener per key. Returns an idempotent
// unsubscribe handle; calling it twice is a no-op (subsequent
// subscriptions stay valid).
// ---------------------------------------------------------------------------

/** Subscribe to theme changes. The listener fires synchronously
 *  on every `writeTheme` call. Returns an idempotent
 *  unsubscribe. */
export function subscribeTheme(listener: Listener<Theme>): Unsubscribe {
  ensureHydrated();
  listeners.add(listener);
  let active = true;
  return () => {
    if (!active) return;
    active = false;
    listeners.delete(listener);
  };
}
