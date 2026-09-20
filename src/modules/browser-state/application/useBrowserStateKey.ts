"use client";

// Browser-state application — React adapter for the typed store.
//
// This hook is the hydration-safe surface the React tree reaches for
// the four typed `localStorage` keys. It is the ONLY application-
// layer file in the browser-state module; the typed-store surface
// (read / write / subscribe / reset) lives in `infrastructure/store.ts`,
// the typed keys + listener types live in `domain/keys.ts`, and the
// typed defaults live in `domain/defaults.ts`.
//
// Hydration contract (browser-state-hydration spec §"Hydration guard
// against server / client mismatch"):
//   - SSR + the first client render return the typed default
//     (`useSyncExternalStore`'s `getServerSnapshot` is the typed
//     default; the in-memory cache is initialised with the same
//     default so the client's `getSnapshot` returns the same value
//     until `useSyncExternalStore` fires the first `subscribe`
//     callback after mount).
//   - After mount, `useSyncExternalStore` invokes `subscribeTheme`
//     (etc.), which triggers the lazy `hydrateFromStorage` call
//     inside the infrastructure store. The cache then mirrors
//     `localStorage`, `getSnapshot` returns the stored value, and
//     React commits the follow-up render with the rehydrated state.
//   - React's hydration guard never trips: the server snapshot and
//     the first client render are byte-equal (both are the typed
//     default).
//
// Consumers MUST import through the public barrel
// (`src/modules/browser-state/index.ts`) — direct imports into this
// file are blocked by `.eslintrc.cjs::no-restricted-imports`.

import { useCallback, useSyncExternalStore } from "react";
import {
  DEFAULT_THEME,
  DEFAULT_TREE_SOURCE,
  DEFAULT_LAST_TAXON_ID,
  DEFAULT_KEBAB_OPEN_ID,
} from "../domain/defaults";
import {
  readTheme,
  writeTheme,
  subscribeTheme,
  readTreeSource,
  writeTreeSource,
  subscribeTreeSource,
  readLastTaxonId,
  writeLastTaxonId,
  subscribeLastTaxonId,
  readKebabOpenId,
  writeKebabOpenId,
  subscribeKebabOpenId,
} from "../infrastructure/store";
import type { Theme, TreeSource } from "../domain/keys";

// ---------------------------------------------------------------------------
// useTheme — `[value, setValue]` tuple for the active theme.
//   - `value` is the typed `Theme` (`"light" | "dark"`).
//   - `setValue` is a stable callback (React identity preserved
//     across renders) that mirrors `writeTheme`.
//   - During SSR + the first client render, `value` is
//     `DEFAULT_THEME` (`"light"`). After mount, `useSyncExternalStore`
//     drives the rehydration + follow-up render.
// ---------------------------------------------------------------------------
export function useTheme(): [Theme, (next: Theme) => void] {
  const value = useSyncExternalStore<Theme>(
    subscribeTheme,
    readTheme,
    () => DEFAULT_THEME,
  );
  const setValue = useCallback((next: Theme) => writeTheme(next), []);
  return [value, setValue];
}

// ---------------------------------------------------------------------------
// useTreeSource — `[value, setValue]` tuple for the active tree-source.
// ---------------------------------------------------------------------------
export function useTreeSource(): [TreeSource, (next: TreeSource) => void] {
  const value = useSyncExternalStore<TreeSource>(
    subscribeTreeSource,
    readTreeSource,
    () => DEFAULT_TREE_SOURCE,
  );
  const setValue = useCallback(
    (next: TreeSource) => writeTreeSource(next),
    [],
  );
  return [value, setValue];
}

// ---------------------------------------------------------------------------
// useLastTaxonId — `[value, setValue]` tuple for the last focused
// taxon id. `null` is a valid value (no taxon focused).
// ---------------------------------------------------------------------------
export function useLastTaxonId(): [number | null, (next: number | null) => void] {
  const value = useSyncExternalStore<number | null>(
    subscribeLastTaxonId,
    readLastTaxonId,
    () => DEFAULT_LAST_TAXON_ID,
  );
  const setValue = useCallback(
    (next: number | null) => writeLastTaxonId(next),
    [],
  );
  return [value, setValue];
}

// ---------------------------------------------------------------------------
// useKebabOpenId — `[value, setValue]` tuple for the kebab-open
// taxon id. `null` is a valid value (no kebab menu open).
// ---------------------------------------------------------------------------
export function useKebabOpenId(): [number | null, (next: number | null) => void] {
  const value = useSyncExternalStore<number | null>(
    subscribeKebabOpenId,
    readKebabOpenId,
    () => DEFAULT_KEBAB_OPEN_ID,
  );
  const setValue = useCallback(
    (next: number | null) => writeKebabOpenId(next),
    [],
  );
  return [value, setValue];
}
