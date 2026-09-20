// Browser-state domain — typed `localStorage` keys + listener type.
//
// spec.md rule 4: domain stays free of presentation, application,
// browser, HTTP, framework, or infrastructure. This file is PURELY
// TypeScript identifiers + the listener/unsubscribe types — no
// `localStorage` access, no React, no Node process. The
// infrastructure layer (`infrastructure/store.ts`) owns the actual
// `getItem` / `setItem` / `removeItem` calls so storage failures
// (private mode / quota exceeded) stay isolated from the consumer
// API and the typed defaults stay reachable when `window` is
// unavailable (SSR / build-time prerender).
//
// The four keys pin the `browser-state-hydration` spec table
// verbatim. Renaming any of them is a wire contract change — the
// legacy `web/state.js` consumers hard-code the same literals, so
// a refactor here must migrate every consumer in lock-step.

/** Theme literal — `light` / `dark`. Mirrors the spec table. */
export type Theme = "light" | "dark";

/** Active tree-source literal — `col` / `worms` / `freshwater`.
 *  Mirrors the spec table (the legacy `web/tree.js::treeSource`
 *  enum re-declared here so the browser-state domain stays free of
 *  any taxonomy dependency). */
export type TreeSource = "col" | "worms" | "freshwater";

/** localStorage key for the active theme. */
export const THEME_STORAGE_KEY = "taxa.settings.theme" as const;

/** localStorage key for the active tree-source. */
export const TREE_SOURCE_STORAGE_KEY = "taxa.tree.source" as const;

/** localStorage key for the last selected taxon id. */
export const LAST_TAXON_ID_STORAGE_KEY = "taxa.tree.lastTaxonId" as const;

/** localStorage key for the kebab-menu open taxon id. */
export const KEBAB_OPEN_ID_STORAGE_KEY = "taxa.tree.kebabOpenId" as const;

/** Canonical ordered list of every storage key the typed store
 *  owns. The `reset()` affordance iterates this list; the
 *  `subscribe` dispatch table uses it to validate the key at
 *  compile time. A future PR that adds a fifth key must extend
 *  this tuple + the spec table in lock-step. */
export const ALL_STORAGE_KEYS = [
  THEME_STORAGE_KEY,
  TREE_SOURCE_STORAGE_KEY,
  LAST_TAXON_ID_STORAGE_KEY,
  KEBAB_OPEN_ID_STORAGE_KEY,
] as const;

/** Union of every storage key literal. */
export type StorageKey = typeof ALL_STORAGE_KEYS[number];

/** Generic listener contract — `useSyncExternalStore` /
 *  `subscribe()` callers pass a typed callback that fires
 *  synchronously on every store mutation. The store delivers the
 *  new typed value, never the raw string. */
export type Listener<T> = (value: T) => void;

/** Unsubscriber returned by `subscribe*()`. Idempotent — calling
 *  the same unsubscribe twice is a no-op (subsequent subscriptions
 *  are also valid). */
export type Unsubscribe = () => void;
