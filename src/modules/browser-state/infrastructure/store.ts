// Browser-state infrastructure — typed `localStorage`-backed store.
//
// spec.md rule 4: infrastructure depends on the domain (inward
// dependency) and owns the only `localStorage` calls in the entire
// project. Every other capability module (`taxonomy`, `research`,
// `app-shell`, `design-system`) MUST reach storage through the
// typed public API exposed by `src/modules/browser-state/index.ts`.
//
// Why every `localStorage` call is guarded by a try/catch:
//   - SSR (`window === undefined`): the static export prerenders
//     pages without a browser. A direct `localStorage.getItem`
//     would throw `ReferenceError` and break the build. The store
//     returns the typed default when `window` is missing.
//   - Private browsing / quota exceeded: the browser throws on
//     `setItem` / `removeItem`. The store swallows the exception
//     so the in-memory state still updates and the UI reflects the
//     user's choice for the current session; the next page reload
//     returns to the typed default (the persistent write failed,
//     but the application kept running).
//
// The four read / four write / four subscribe / four reset sites
// are pinned by `tests/test_browser_state_keys.py`. Any future PR
// that adds a fifth key must extend `ALL_STORAGE_KEYS` (declared in
// `domain/keys.ts`), add a fifth read + write + subscribe triple
// here, and extend the spec table — the source-level
// storage-ownership test catches the regression before review.

import {
  DEFAULT_THEME,
  DEFAULT_TREE_SOURCE,
  DEFAULT_LAST_TAXON_ID,
  DEFAULT_KEBAB_OPEN_ID,
} from "../domain/defaults";
import {
  THEME_STORAGE_KEY,
  TREE_SOURCE_STORAGE_KEY,
  LAST_TAXON_ID_STORAGE_KEY,
  KEBAB_OPEN_ID_STORAGE_KEY,
  type Listener,
  type Unsubscribe,
  type Theme,
  type TreeSource,
} from "../domain/keys";

// ---------------------------------------------------------------------------
// safeStorage helpers — wrap the three `localStorage` primitives in
// a try/catch so storage failures (private mode, quota, SSR) never
// propagate out of the typed store. The four read sites and four
// write sites route through `safeGetItem` + `safeSetItem`; the
// reset affordance routes its own try/catch (the storage-ownership
// grep test expects one explicit `localStorage.removeItem` call
// per typed key).
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
    // session. The next page reload returns to the typed default.
  }
}

// ---------------------------------------------------------------------------
// parse / serialize — coerce the raw `localStorage` string into the
// typed value the public API exposes. Garbage values fall back to
// the typed default so a legacy write or a manual DevTools edit
// cannot corrupt the application state.
// ---------------------------------------------------------------------------

function parseTheme(raw: string | null): Theme {
  return raw === "dark" ? "dark" : "light";
}

function serializeTheme(value: Theme): string {
  return value === "dark" ? "dark" : "light";
}

function parseTreeSource(raw: string | null): TreeSource {
  if (raw === "worms" || raw === "freshwater") return raw;
  return "col";
}

function serializeTreeSource(value: TreeSource): string {
  if (value === "worms" || value === "freshwater") return value;
  return "col";
}

function parseNumberOrNull(raw: string | null): number | null {
  if (raw === null || raw === "") return null;
  const n = Number(raw);
  return Number.isInteger(n) ? n : null;
}

function serializeNumberOrNull(value: number | null): string {
  return value === null ? "" : String(value);
}

// ---------------------------------------------------------------------------
// In-memory cache + per-key subscriber sets.
//
// The cache mirrors what `localStorage` last returned (or the typed
// default if storage is unavailable). Every read / write / subscribe
// / reset path goes through `ensureHydrated` so the cache is
// populated lazily — exactly once per page load — and the typed
// default is what SSR + the first client render return.
//
// Subscribers fire synchronously on every mutation regardless of
// whether the persistent write succeeded. That keeps the React tree
// in sync with the in-memory state even when storage is unavailable.
// ---------------------------------------------------------------------------

let themeCache: Theme = DEFAULT_THEME;
let treeSourceCache: TreeSource = DEFAULT_TREE_SOURCE;
let lastTaxonIdCache: number | null = DEFAULT_LAST_TAXON_ID;
let kebabOpenIdCache: number | null = DEFAULT_KEBAB_OPEN_ID;

const themeListeners = new Set<Listener<Theme>>();
const treeSourceListeners = new Set<Listener<TreeSource>>();
const lastTaxonIdListeners = new Set<Listener<number | null>>();
const kebabOpenIdListeners = new Set<Listener<number | null>>();

let hydrated = false;

function hydrateFromStorage(): void {
  // Hydration order matches the cache declaration order so the
  // first paint is reproducible across builds. Each read goes
  // through `safeGetItem` so an unavailable storage layer returns
  // `null` → parsed → typed default.
  themeCache = parseTheme(safeGetItem(THEME_STORAGE_KEY));
  treeSourceCache = parseTreeSource(safeGetItem(TREE_SOURCE_STORAGE_KEY));
  lastTaxonIdCache = parseNumberOrNull(safeGetItem(LAST_TAXON_ID_STORAGE_KEY));
  kebabOpenIdCache = parseNumberOrNull(safeGetItem(KEBAB_OPEN_ID_STORAGE_KEY));
}

function ensureHydrated(): void {
  if (hydrated) return;
  hydrateFromStorage();
  hydrated = true;
}

/** Test seam — clear the in-memory cache + the hydrated flag so a
 *  test can simulate a fresh page load. NOT exported through the
 *  public barrel. */
export function __resetForTests(): void {
  themeCache = DEFAULT_THEME;
  treeSourceCache = DEFAULT_TREE_SOURCE;
  lastTaxonIdCache = DEFAULT_LAST_TAXON_ID;
  kebabOpenIdCache = DEFAULT_KEBAB_OPEN_ID;
  themeListeners.clear();
  treeSourceListeners.clear();
  lastTaxonIdListeners.clear();
  kebabOpenIdListeners.clear();
  hydrated = false;
}

// ---------------------------------------------------------------------------
// Read sites — exactly one per key (the storage-ownership contract).
// ---------------------------------------------------------------------------

/** Read the active theme. Returns the typed default when storage is
 *  unavailable (SSR / private mode) or the stored value is garbage. */
export function readTheme(): Theme {
  ensureHydrated();
  return themeCache;
}

/** Read the active tree-source. Returns the typed default when
 *  storage is unavailable or the stored value is garbage. */
export function readTreeSource(): TreeSource {
  ensureHydrated();
  return treeSourceCache;
}

/** Read the last focused taxon id. Returns `null` when storage is
 *  unavailable, no id is stored, or the stored value is garbage. */
export function readLastTaxonId(): number | null {
  ensureHydrated();
  return lastTaxonIdCache;
}

/** Read the kebab-open taxon id. Returns `null` when storage is
 *  unavailable, no id is stored, or the stored value is garbage. */
export function readKebabOpenId(): number | null {
  ensureHydrated();
  return kebabOpenIdCache;
}

// ---------------------------------------------------------------------------
// Write sites — exactly one per key. Subscribers fire synchronously
// on every mutation, regardless of whether the persistent write
// succeeded.
// ---------------------------------------------------------------------------

/** Write the active theme. Updates the in-memory cache + the
 *  `localStorage` entry (best-effort, swallowed on failure) +
 *  fires every theme subscriber synchronously. */
export function writeTheme(next: Theme): void {
  ensureHydrated();
  themeCache = next;
  safeSetItem(THEME_STORAGE_KEY, serializeTheme(next));
  for (const listener of themeListeners) listener(next);
}

/** Write the active tree-source. Updates the in-memory cache +
 *  `localStorage` + fires every tree-source subscriber. */
export function writeTreeSource(next: TreeSource): void {
  ensureHydrated();
  treeSourceCache = next;
  safeSetItem(TREE_SOURCE_STORAGE_KEY, serializeTreeSource(next));
  for (const listener of treeSourceListeners) listener(next);
}

/** Write the last focused taxon id. Updates the in-memory cache +
 *  `localStorage` + fires every last-taxon-id subscriber. */
export function writeLastTaxonId(next: number | null): void {
  ensureHydrated();
  lastTaxonIdCache = next;
  safeSetItem(LAST_TAXON_ID_STORAGE_KEY, serializeNumberOrNull(next));
  for (const listener of lastTaxonIdListeners) listener(next);
}

/** Write the kebab-open taxon id. Updates the in-memory cache +
 *  `localStorage` + fires every kebab-open-id subscriber. */
export function writeKebabOpenId(next: number | null): void {
  ensureHydrated();
  kebabOpenIdCache = next;
  safeSetItem(KEBAB_OPEN_ID_STORAGE_KEY, serializeNumberOrNull(next));
  for (const listener of kebabOpenIdListeners) listener(next);
}

// ---------------------------------------------------------------------------
// Subscribe — typed listeners per key. Returns an idempotent
// unsubscribe handle; calling it twice is a no-op (subsequent
// subscriptions stay valid).
// ---------------------------------------------------------------------------

/** Subscribe to theme changes. The listener fires synchronously on
 *  every `writeTheme` call. Returns an idempotent unsubscribe. */
export function subscribeTheme(listener: Listener<Theme>): Unsubscribe {
  ensureHydrated();
  themeListeners.add(listener);
  let active = true;
  return () => {
    if (!active) return;
    active = false;
    themeListeners.delete(listener);
  };
}

/** Subscribe to tree-source changes. The listener fires
 *  synchronously on every `writeTreeSource` call. Returns an
 *  idempotent unsubscribe. */
export function subscribeTreeSource(
  listener: Listener<TreeSource>,
): Unsubscribe {
  ensureHydrated();
  treeSourceListeners.add(listener);
  let active = true;
  return () => {
    if (!active) return;
    active = false;
    treeSourceListeners.delete(listener);
  };
}

/** Subscribe to last-taxon-id changes. Returns an idempotent
 *  unsubscribe. */
export function subscribeLastTaxonId(
  listener: Listener<number | null>,
): Unsubscribe {
  ensureHydrated();
  lastTaxonIdListeners.add(listener);
  let active = true;
  return () => {
    if (!active) return;
    active = false;
    lastTaxonIdListeners.delete(listener);
  };
}

/** Subscribe to kebab-open-id changes. Returns an idempotent
 *  unsubscribe. */
export function subscribeKebabOpenId(
  listener: Listener<number | null>,
): Unsubscribe {
  ensureHydrated();
  kebabOpenIdListeners.add(listener);
  let active = true;
  return () => {
    if (!active) return;
    active = false;
    kebabOpenIdListeners.delete(listener);
  };
}

// ---------------------------------------------------------------------------
// reset — clears every key to its typed default AND removes the
// matching `localStorage` entries. Subscribers fire synchronously
// with the new default values so the UI updates in one render.
// ---------------------------------------------------------------------------

/** Reset every key to its typed default. Removes every matching
 *  `localStorage` entry (best-effort, swallowed on failure) and
 *  fires every subscriber. Used by the settings-view reset
 *  affordance; consumers MUST NOT call this directly without user
 *  intent — the typed defaults are a one-shot, deliberate state
 *  transition. */
export function reset(): void {
  ensureHydrated();
  themeCache = DEFAULT_THEME;
  treeSourceCache = DEFAULT_TREE_SOURCE;
  lastTaxonIdCache = DEFAULT_LAST_TAXON_ID;
  kebabOpenIdCache = DEFAULT_KEBAB_OPEN_ID;
  // Four explicit removeItem sites — one per typed key. Inlined
  // (instead of a `safeRemoveItem` loop) so the storage-ownership
  // grep test counts exactly four `localStorage.removeItem`
  // occurrences and a future PR cannot silently drop a key from
  // the reset path without breaking the test.
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
  for (const listener of themeListeners) listener(DEFAULT_THEME);
  for (const listener of treeSourceListeners) listener(DEFAULT_TREE_SOURCE);
  for (const listener of lastTaxonIdListeners) listener(DEFAULT_LAST_TAXON_ID);
  for (const listener of kebabOpenIdListeners) listener(DEFAULT_KEBAB_OPEN_ID);
}
