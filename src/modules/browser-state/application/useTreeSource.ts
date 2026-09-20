"use client";

// Browser-state application — React adapter for the typed
// tree-source store (`taxa.tree.source`).
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `application/useBrowserStateKey.ts` is replaced by
// one hook file per storage key. `useTreeSource` imports only
// from `infrastructure/storeTreeSource.ts`, NOT from the sibling
// stores (theme / last-taxon-id / kebab-open-id). Turbopack
// retention relies on this isolation — any cross-key import
// would silently re-bundle the forbidden localStorage key
// literals into the chunk that ships this hook.
//
// This is the FIRST production consumer of the typed store in
// the main route (ODD-BSTATE-TAX-001): `TaxonomyTree` reads +
// writes the active source through `useTreeSource()`. The
// hook returns the typed default `"col"` on SSR + the first
// client render (so React's hydration guard never trips on a
// stored value) and the stored value on the post-mount render.
//
// Hydration contract (browser-state-hydration spec §"Hydration
// guard against server / client mismatch"):
//   - SSR + the first client render return the typed default
//     (`useSyncExternalStore`'s `getServerSnapshot` is the typed
//     default; the in-memory cache is initialised with the same
//     default so the client's `getSnapshot` returns the same value
//     until `useSyncExternalStore` fires the first `subscribe`
//     callback after mount).
//   - After mount, `useSyncExternalStore` invokes
//     `subscribeTreeSource` which triggers the lazy
//     `hydrateFromStorage` call inside the infrastructure store.
//     The cache then mirrors `localStorage`, `getSnapshot` returns
//     the stored value, and React commits the follow-up render.
//   - React's hydration guard never trips: the server snapshot
//     and the first client render are byte-equal (both are the
//     typed default `"col"`).
//
// Consumers MUST import through the public barrel
// (`src/modules/browser-state/index.ts`) — direct imports into
// this file are blocked by
// `.eslintrc.cjs::no-restricted-imports`.

import { useCallback, useSyncExternalStore } from "react";
import { DEFAULT_TREE_SOURCE } from "../domain/defaults";
import {
  readTreeSource,
  writeTreeSource,
  subscribeTreeSource,
} from "../infrastructure/storeTreeSource";
import type { TreeSource } from "../domain/keys";

// ---------------------------------------------------------------------------
// useTreeSource — `[value, setValue]` tuple for the active tree-source.
//   - `value` is the typed `TreeSource` (`"col" | "worms" | "freshwater"`).
//   - `setValue` is a stable callback that mirrors `writeTreeSource`.
//   - SSR + first client render returns `DEFAULT_TREE_SOURCE`
//     (`"col"`); the post-mount render surfaces the stored value
//     so the user-picked source persists across reload.
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
