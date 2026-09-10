/**
 * Safe platform-storage access layer (PR 4a).
 *
 * The store (sibling file `store.ts`) is the only module that calls
 * `getItem(` or `setItem(`. This file isolates platform-detection and
 * JSON try/catch helpers so the store never repeats them. Zero
 * `getItem(` / `setItem(` call sites live here — those are concentrated
 * in store.ts so the 4 + 4 count enforced by
 * `tests/test_browser_state_keys.py` is single-sourced.
 */

/** Returns the platform storage object if available, else `null`.
 *  Returns null in SSR (Node), in private-browsing (Safari), or when
 *  the global is absent. */
export function getBrowserStorage(): Storage | null {
  if (typeof globalThis === "undefined") return null;
  try {
    const candidate = (globalThis as { localStorage?: Storage }).localStorage;
    return candidate ?? null;
  } catch {
    return null;
  }
}

/** Parses `raw` as JSON and validates via the type guard; falls back to
 *  `fallback` on missing input, parse failure, or guard rejection. */
export function tryJsonParse<T>(
  raw: string | null,
  fallback: T,
  isValid: (value: unknown) => value is T,
): T {
  if (raw === null) return fallback;
  try {
    const parsed: unknown = JSON.parse(raw);
    return isValid(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

/** Best-effort `JSON.stringify` that returns `null` on serialization
 *  failure (cycles, BigInt, etc.). store.ts treats `null` as "skip
 *  the write" so a thrown stringify never reaches the wire. */
export function tryJsonStringify(value: unknown): string | null {
  try {
    return JSON.stringify(value);
  } catch {
    return null;
  }
}
