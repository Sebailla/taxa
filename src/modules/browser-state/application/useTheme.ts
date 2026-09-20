"use client";

// Browser-state application — React adapter for the typed theme
// store (`taxa.settings.theme`).
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `application/useBrowserStateKey.ts` is replaced by
// one hook file per storage key. `useTheme` imports only from
// `infrastructure/storeTheme.ts`, NOT from the sibling stores
// (tree-source / last-taxon-id / kebab-open-id). Turbopack
// retention relies on this isolation — any cross-key import
// would silently re-bundle the forbidden localStorage key
// literals into the chunk that ships this hook.
//
// Hydration contract (browser-state-hydration spec §"Hydration
// guard against server / client mismatch"):
//   - SSR + the first client render return the typed default
//     (`useSyncExternalStore`'s `getServerSnapshot` is the typed
//     default; the in-memory cache is initialised with the same
//     default so the client's `getSnapshot` returns the same value
//     until `useSyncExternalStore` fires the first `subscribe`
//     callback after mount).
//   - After mount, `useSyncExternalStore` invokes `subscribeTheme`
//     which triggers the lazy `hydrateFromStorage` call inside
//     the infrastructure store. The cache then mirrors
//     `localStorage`, `getSnapshot` returns the stored value, and
//     React commits the follow-up render with the rehydrated
//     state.
//   - React's hydration guard never trips: the server snapshot
//     and the first client render are byte-equal (both are the
//     typed default).
//
// Consumers MUST import through the public barrel
// (`src/modules/browser-state/index.ts`) — direct imports into
// this file are blocked by
// `.eslintrc.cjs::no-restricted-imports`.

import { useCallback, useSyncExternalStore } from "react";
import { DEFAULT_THEME } from "../domain/defaults";
import {
  readTheme,
  writeTheme,
  subscribeTheme,
} from "../infrastructure/storeTheme";
import type { Theme } from "../domain/keys";

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
