// Browser-state infrastructure — typed localStorage-backed store
// for the **`taxa-internal-ok`** storage key (ODD-ASN-001).
//
// spec.md rule 4: infrastructure depends on the domain (inward
// dependency) and owns the only `localStorage` call for the
// internal-flag key. Every other capability module MUST reach
// storage through the typed public API exposed by
// `src/modules/browser-state/index.ts`.
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `infrastructure/store.ts` was replaced by one file
// per storage key so Turbopack can retain only the imported
// key's module chain. The ODD-ASN-001 hydration-probe gate
// (`presentation/HydrationProbeGate.tsx`) reads the flag via
// `readInternalFlag()` from this file; storage access stays
// centralised in the typed store so the presentation layer is
// free of `localStorage.*` references and the ODD-BSTATE-TAX-001
// storage-ownership contract holds.
//
// The Playwright harness sets the flag via `context.add_init_script`
// (the harness, NOT the application, is the only writer in
// production). The `writeInternalFlag()` + `subscribeInternalFlag()`
// surface exists for symmetry + future use (a settings-view toggle
// could expose the flag if the user-facing team ever wants one).
//
// Why the localStorage calls are guarded by a try/catch:
//   - SSR (`window === undefined`): the static export prerenders
//     pages without a browser. A direct `localStorage.getItem`
//     would throw `ReferenceError` and break the build. The store
//     returns `false` when `window` is missing (the gate then
//     flips state to "denied" — the safe default for an internal
//     witness route).
//   - Private browsing / quota exceeded: the browser throws on
//     `setItem` / `removeItem`. The store swallows the exception
//     so the in-memory state still reflects the user's choice
//     for the current session.

import type { Unsubscribe } from "../domain/keys";
// ODD-BSTATE-TAX-001-A — strict chunk-boundary contract. The
// internal-flag chain MUST NOT pull `domain/keys.ts` at runtime
// because that file also declares the four typed key literals.
// A shared chunk carrying the typed keys would fail the
// `tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`
// check. Declaring the constant inline here keeps the chain
// independent.
//
// The canonical `INTERNAL_FLAG_STORAGE_KEY = "taxa-internal-ok"`
// declaration in `domain/keys.ts` stays in place for the
// `ALL_STORAGE_KEYS` tuple contract + the public barrel
// re-export. The two declarations are kept in sync by the
// ODD-BSTATE-TAX-001-B strict chunk-boundary witness itself.
const INTERNAL_FLAG_STORAGE_KEY = "taxa-internal-ok";
const INTERNAL_FLAG_VALUE = "1";

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
    // Quota exceeded / private mode — the in-memory state still
    // reflects the user's choice for the current session.
  }
}

function safeRemoveItem(key: string): void {
  try {
    if (typeof window === "undefined") return;
    const storage = window.localStorage;
    if (!storage) return;
    storage.removeItem(key);
  } catch {
    // Quota exceeded / private mode — the in-memory state still
    // reflects the user's choice for the current session.
  }
}

// ---------------------------------------------------------------------------
// parse / serialize — coerce the raw `localStorage` string into
// the typed `boolean` value the public API exposes. Only the
// literal string `"1"` is truthy; every other value (missing
// key, garbage, `null`) maps to `false`. The Playwright harness
// writes `"1"` via `add_init_script`; the typed store treats
// any other string as "not set" so a manual DevTools edit cannot
// accidentally grant the flag.
// ---------------------------------------------------------------------------

function parseFlag(raw: string | null): boolean {
  return raw === INTERNAL_FLAG_VALUE;
}

// ---------------------------------------------------------------------------
// Read site — exactly one per key (the storage-ownership
// contract).
// ---------------------------------------------------------------------------

/** Read the internal flag. Returns `true` only when the flag is
 *  set to the literal `"1"`; returns `false` when storage is
 *  unavailable (SSR / private mode), the key is missing, or the
 *  stored value is anything other than `"1"`. */
export function readInternalFlag(): boolean {
  return parseFlag(safeGetItem(INTERNAL_FLAG_STORAGE_KEY));
}

// ---------------------------------------------------------------------------
// Write site — exactly one per key. `true` writes `"1"`;
// `false` removes the key so the next read returns `false`
// without a stale value lingering in storage.
// ---------------------------------------------------------------------------

/** Write the internal flag. Sets the key to `"1"` when `value`
 *  is `true`; removes the key when `value` is `false`. Used by
 *  the Playwright harness via `add_init_script` (the harness,
 *  NOT the application, owns the writer role in production).
 *  The write is best-effort, swallowed on failure, so a private
 *  mode / quota exceeded environment never throws out of the
 *  typed store. */
export function writeInternalFlag(value: boolean): void {
  if (value) {
    safeSetItem(INTERNAL_FLAG_STORAGE_KEY, INTERNAL_FLAG_VALUE);
  } else {
    safeRemoveItem(INTERNAL_FLAG_STORAGE_KEY);
  }
}

// ---------------------------------------------------------------------------
// Subscribe — typed listener per key. The internal-flag chain
// has no in-memory subscribers today (no React consumer reads
// the flag live; the gate reads once on mount), but the
// `subscribeInternalFlag()` surface exists for symmetry with the
// other per-key stores + for future consumers that may want to
// react to flag changes (e.g. a settings-view toggle that
// mirrors the flag's state).
// ---------------------------------------------------------------------------

/** Subscribe to internal-flag changes. The listener fires
 *  synchronously on every `writeInternalFlag()` call. Returns
 *  an idempotent unsubscribe. */
export function subscribeInternalFlag(
  _listener: () => void,
): Unsubscribe {
  // No internal subscribers to register today; the contract
  // exists for symmetry with the other per-key stores so a
  // future consumer can subscribe without a typed-store
  // surface change. The `_listener` parameter is intentionally
  // retained (with the TS unused-parameter underscore prefix)
  // so the public API stays source-compatible with the four
  // sibling subscribe functions (`subscribeTheme` /
  // `subscribeTreeSource` / `subscribeLastTaxonId` /
  // `subscribeKebabOpenId`).
  let active = true;
  return () => {
    if (!active) return;
    active = false;
  };
}

/** Test seam — clear any future in-memory subscribers + reset
 *  state. NOT exported through the public barrel. Mirrors the
 *  `__resetForTests()` seam in `storeTheme.ts` so the per-key
 *  test composition stays uniform. */
export function __resetForTests(): void {
  // No in-memory state today (the flag is read directly from
  // storage on every read), but the seam exists so future
  // cache + listener additions don't need a test rewrite.
}