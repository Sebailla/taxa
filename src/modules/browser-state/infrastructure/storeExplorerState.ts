// Browser-state infrastructure — typed localStorage-backed store
// for the **`taxa.fex.explorerState`** storage key
// (ODD-BSTATE-EXPLORER-PERSIST — EXPLORER-PERSIST architecture
// correction).
//
// spec.md rule 4: infrastructure depends on the domain (inward
// dependency) and owns the only `localStorage` call for the
// explorer-state key. Every other capability module MUST reach
// storage through the typed public API exposed by
// `src/modules/browser-state/index.ts`.
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `infrastructure/store.ts` is replaced by one file
// per storage key. The EXPLORER-PERSIST architecture correction
// extends the per-key family by one entry (`storeExplorerState.ts`)
// so the Browser-tab Explorer working-set persistence follows the
// canonical typed-chain pattern.
//
// The store stores the persisted record as a JSON string (the
// versioned envelope produced by the Research-side
// `serializeExplorerState` helper). The Research-side
// `parseExplorerState` helper reads + validates the envelope so
// the typed shape stays the canonical Research-domain concept;
// this file just owns the typed `string | null` `localStorage`
// round-trip.
//
// Why this chain declares its key inline: the canonical
// declaration in `domain/keys.ts` keeps the spec-table
// preservation test green + the public barrel re-export
// happy. The per-file rationale mirrors the four sibling
// stores (`storeTheme` / `storeTreeSource` / etc.) — declaring
// the constant inline keeps the explorer-state chain
// independent of `domain/keys.ts` at runtime, so Turbopack
// retention isolates the chain from the four sibling key
// literals. A regression that drifts the local constant away
// from the canonical value trips the
// `test_explorer_state_store_declares_inline_storage_key` pin
// below.
//
// Why the localStorage calls are guarded by a try/catch:
//   - SSR (`window === undefined`): the static export prerenders
//     pages without a browser. A direct `localStorage.getItem`
//     would throw `ReferenceError` and break the build. The store
//     returns `null` (read) / no-op (write) when `window` is
//     missing — the Explorer mount then starts from the empty
//     default + the React layer renders the fresh working set.
//   - Private browsing / quota exceeded: the browser throws on
//     `setItem` / `removeItem`. The store swallows the exception
//     so the in-memory state still reflects the user's choice
//     for the current session.

import {
  EXPLORER_STATE_STORAGE_VERSION,
  createEmptyPersistedExplorerState,
} from "../domain/explorer-state";
import type { PersistedExplorerState } from "../domain/explorer-state";
import { DEFAULT_EXPLORER_STATE } from "../domain/defaults";
import type { Listener, Unsubscribe } from "../domain/keys";

// ODD-BSTATE-TAX-001-A — strict chunk-boundary contract. The
// explorer-state chain MUST NOT pull `domain/keys.ts` at
// runtime because that file also declares the four sibling key
// literals. A shared chunk carrying the four sibling keys PLUS
// the explorer-state key would fail the strict chunk-boundary
// witness on the explorer route's chunk. Declaring the constant
// inline here keeps the chain independent.
//
// The canonical declaration in `domain/keys.ts` stays in place
// for the spec-table preservation test + the public barrel
// re-export. The two declarations are kept in sync by the
// `test_explorer_state_store_declares_inline_storage_key` source-
// level guard in `tests/test_browser_state_keys.py`.
const EXPLORER_STATE_STORAGE_KEY = "taxa.fex.explorerState";

// ---------------------------------------------------------------------------
// safeStorage helpers — wrap the three `localStorage` primitives
// in a try/catch so storage failures (private mode, quota, SSR)
// never propagate out of the typed store. The read site routes
// through `safeGetItem`; the write site routes through
// `safeSetItem`; the reset site routes through `safeRemoveItem`.
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

function safeRemoveItem(key: string): void {
  try {
    if (typeof window === "undefined") return;
    const storage = window.localStorage;
    if (!storage) return;
    storage.removeItem(key);
  } catch {
    // Quota exceeded / private mode — the in-memory cache still
    // resets, so the UI reflects the change for the current
    // session.
  }
}

// ---------------------------------------------------------------------------
// serialize / parse — the EXPLORER-PERSIST envelope. The chain
// stores the persisted record as a JSON string; the typed
// `PersistedExplorerState` round-trip goes through this file
// so the storage layer owns the version / write-bound /
// read-validate checks at the boundary (instead of relying on
// the Research-side `parseExplorerState` to silently discard
// malformed records at every read).
//
// The parser is conservative: a future / unknown version,
// out-of-bounds length, missing field, or wrong-typed field
// returns `null` so the React mount treats the failure as
// "no persisted state, start fresh". A non-empty `value`
// argument that is not a JSON object also returns `null`.
// ---------------------------------------------------------------------------

function parseExplorerStateEnvelope(
  raw: string | null,
): PersistedExplorerState | null {
  if (raw === null || raw === "") return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (
    typeof parsed !== "object" ||
    parsed === null ||
    Array.isArray(parsed)
  ) {
    return null;
  }
  const obj = parsed as Record<string, unknown>;
  const version = obj.version;
  if (
    typeof version !== "number" ||
    !Number.isFinite(version) ||
    version > EXPLORER_STATE_STORAGE_VERSION
  ) {
    return null;
  }
  const query = obj.query;
  if (typeof query !== "string") return null;
  const selectedPath = obj.selectedPath;
  if (selectedPath !== null && typeof selectedPath !== "string") {
    return null;
  }
  const expandedPaths = obj.expandedPaths;
  if (!Array.isArray(expandedPaths)) return null;
  for (const entry of expandedPaths) {
    if (typeof entry !== "string") return null;
  }
  return {
    version,
    query,
    selectedPath,
    expandedPaths: expandedPaths.slice(),
  };
}

// ---------------------------------------------------------------------------
// In-memory cache + per-key subscriber sets. Mirrors the
// contract documented on `storeTheme.ts`; the same
// hydrate-once semantics keep the SSR + first-client-render
// byte-equal (so React's hydration guard never trips on a
// stored value).
//
// The cache holds the typed `PersistedExplorerState` shape.
// Before hydration it carries the canonical empty record
// (`createEmptyPersistedExplorerState()` — the typed default
// for SSR + first-client-render). After hydration it
// mirrors the persisted envelope OR the canonical empty
// record (for absent / malformed / future-version / out-of-
// bounds records). This way the cache never returns `null`
// after hydration — the React layer always sees a typed
// `PersistedExplorerState`, never `undefined` / `null`.
// ---------------------------------------------------------------------------

let cache: PersistedExplorerState = createEmptyPersistedExplorerState();
const listeners = new Set<Listener<PersistedExplorerState>>();

let hydrated = false;

function hydrateFromStorage(): void {
  cache = parseExplorerStateEnvelope(
    safeGetItem(EXPLORER_STATE_STORAGE_KEY),
  ) ?? createEmptyPersistedExplorerState();
}

function ensureHydrated(): void {
  if (hydrated) return;
  hydrateFromStorage();
  hydrated = true;
}

/** Test seam — clear the in-memory cache + the hydrated flag +
 *  fire every listener with the empty record so the per-key
 *  reset contract stays symmetric (subscribers see the typed
 *  default on reset). */
export function __resetForTests(): void {
  cache = DEFAULT_EXPLORER_STATE;
  // Notify every subscriber that the value flipped to the
  // empty record so test harnesses can assert the reset path
  // end-to-end.
  for (const listener of listeners) listener(cache);
  listeners.clear();
  hydrated = false;
}

// ---------------------------------------------------------------------------
// Read site — exactly one per key.
// ---------------------------------------------------------------------------

/** Read the persisted explorer state. Returns the typed
 *  `PersistedExplorerState` shape (the persisted envelope OR
 *  the canonical empty record for absent / malformed /
 *  future-version / out-of-bounds records). SSR + the first
 *  client render return the canonical empty record; the
 *  post-mount render surfaces the persisted value. */
export function readExplorerState(): PersistedExplorerState {
  ensureHydrated();
  return cache;
}

// ---------------------------------------------------------------------------
// Write site — exactly one per key.
// ---------------------------------------------------------------------------

/** Write the persisted explorer state. Updates the in-memory
 *  cache + `localStorage` + fires every subscriber. The write
 *  is best-effort, swallowed on failure, so a private mode /
 *  quota exceeded environment never throws out of the typed
 *  store. The store accepts the typed `PersistedExplorerState`
 *  shape so the chain is typed end-to-end. */
export function writeExplorerState(
  next: PersistedExplorerState,
): void {
  ensureHydrated();
  cache = next;
  try {
    safeSetItem(
      EXPLORER_STATE_STORAGE_KEY,
      JSON.stringify(next),
    );
  } catch {
    /* swallow — see safeSetItem */
  }
  for (const listener of listeners) listener(next);
}

/** Remove the persisted explorer state. Updates the
 *  in-memory cache to the canonical empty record + removes
 *  the `localStorage` entry + fires every subscriber with
 *  the empty record. The remove is best-effort, swallowed
 *  on failure, so a private mode / quota exceeded
 *  environment never throws out of the typed store. */
export function clearExplorerState(): void {
  ensureHydrated();
  cache = DEFAULT_EXPLORER_STATE;
  safeRemoveItem(EXPLORER_STATE_STORAGE_KEY);
  for (const listener of listeners) listener(cache);
}

// ---------------------------------------------------------------------------
// Subscribe — typed listener per key.
// ---------------------------------------------------------------------------

/** Subscribe to explorer-state changes. Returns an
 *  idempotent unsubscribe. The listener fires synchronously
 *  on every `writeExplorerState()` / `clearExplorerState()`
 *  call, with the new typed value (the typed `null` on
 *  `clearExplorerState` / `__resetForTests`). */
export function subscribeExplorerState(
  listener: Listener<PersistedExplorerState | null>,
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

// Re-export the empty-record factory so the typed defaults
// route through the canonical domain surface (the same shape
// that powers the in-memory empty-state fallback for SSR +
// the first client render). NOT re-exported through the
// public barrel (the per-file rationale mirrors the sibling
// stores — cross-key exports would defeat the chunk-boundary
// isolation).
export { createEmptyPersistedExplorerState };