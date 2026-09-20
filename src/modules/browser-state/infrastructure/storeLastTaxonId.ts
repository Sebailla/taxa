// Browser-state infrastructure — typed localStorage-backed store
// for the **`taxa.tree.lastTaxonId`** storage key.
//
// spec.md rule 4: infrastructure depends on the domain (inward
// dependency) and owns the only `localStorage` call for the
// last-taxon-id key. Every other capability module MUST reach
// storage through the typed public API exposed by
// `src/modules/browser-state/index.ts`.
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `infrastructure/store.ts` was replaced by one file
// per storage key. The last-taxon-id hook stays out of scope
// until its consumer slice ships; the strict chunk-boundary
// contract (ODD-BSTATE-TAX-001-B) requires the chain to never
// reach the main route's bundle.
//
// The shared `parseNumberOrNull` + `serializeNumberOrNull`
// helpers LOWER the duplication while staying inside this file
// (a sibling store owns the same helpers — kebab-open-id — and
// duplicates them locally; centralising across keys would put
// a non-storage helper inside `infrastructure/` and couple the
// chains, defeating the strict boundary).

import {
  DEFAULT_LAST_TAXON_ID,
} from "../domain/defaults";
// ODD-BSTATE-TAX-001-A — strict chunk-boundary contract. The
// last-taxon-id chain MUST NOT pull `domain/keys.ts` at runtime
// because that file also declares the three sibling key
// literals. A shared chunk carrying all four literals would
// fail the strict chunk-boundary witness. Declaring the
// constant inline here keeps the chain independent.
//
// The canonical declaration in `domain/keys.ts` stays in place
// for the spec table preservation test + the public barrel
// re-export.
const LAST_TAXON_ID_STORAGE_KEY = "taxa.tree.lastTaxonId";
import type { Listener, Unsubscribe } from "../domain/keys";

// ---------------------------------------------------------------------------
// safeStorage helpers — wrap the two `localStorage` primitives in
// a try/catch so storage failures (private mode, quota, SSR)
// never propagate out of the typed store.
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
// the typed `number | null` value the public API exposes.
// Garbage values (non-integer strings, decimals) fall back to
// `null` so a legacy write or a manual DevTools edit cannot
// corrupt the application state.
// ---------------------------------------------------------------------------

function parseNumberOrNull(raw: string | null): number | null {
  if (raw === null || raw === "") return null;
  const n = Number(raw);
  return Number.isInteger(n) ? n : null;
}

function serializeNumberOrNull(value: number | null): string {
  return value === null ? "" : String(value);
}

// ---------------------------------------------------------------------------
// In-memory cache + subscriber sets. Mirrors the contract
// documented on `storeTheme.ts`.
// ---------------------------------------------------------------------------

let cache: number | null = DEFAULT_LAST_TAXON_ID;
const listeners = new Set<Listener<number | null>>();

let hydrated = false;

function hydrateFromStorage(): void {
  cache = parseNumberOrNull(safeGetItem(LAST_TAXON_ID_STORAGE_KEY));
}

function ensureHydrated(): void {
  if (hydrated) return;
  hydrateFromStorage();
  hydrated = true;
}

/** Test seam — clear the in-memory cache + the hydrated flag. */
export function __resetForTests(): void {
  cache = DEFAULT_LAST_TAXON_ID;
  listeners.clear();
  hydrated = false;
}

// ---------------------------------------------------------------------------
// Read site — exactly one per key.
// ---------------------------------------------------------------------------

/** Read the last focused taxon id. Returns `null` when storage
 *  is unavailable, no id is stored, or the stored value is
 *  garbage. */
export function readLastTaxonId(): number | null {
  ensureHydrated();
  return cache;
}

// ---------------------------------------------------------------------------
// Write site — exactly one per key.
// ---------------------------------------------------------------------------

/** Write the last focused taxon id. Updates the in-memory cache
 *  + `localStorage` + fires every subscriber. */
export function writeLastTaxonId(next: number | null): void {
  ensureHydrated();
  cache = next;
  safeSetItem(LAST_TAXON_ID_STORAGE_KEY, serializeNumberOrNull(next));
  for (const listener of listeners) listener(next);
}

// ---------------------------------------------------------------------------
// Subscribe — typed listener per key.
// ---------------------------------------------------------------------------

/** Subscribe to last-taxon-id changes. Returns an idempotent
 *  unsubscribe. */
export function subscribeLastTaxonId(
  listener: Listener<number | null>,
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
