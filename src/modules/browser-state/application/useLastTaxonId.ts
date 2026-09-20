"use client";

// Browser-state application — React adapter for the typed
// last-taxon-id store (`taxa.tree.lastTaxonId`).
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `application/useBrowserStateKey.ts` is replaced by
// one hook file per storage key. `useLastTaxonId` imports only
// from `infrastructure/storeLastTaxonId.ts`, NOT from the
// sibling stores (theme / tree-source / kebab-open-id). Turbopack
// retention relies on this isolation — any cross-key import
// would silently re-bundle the forbidden localStorage key
// literals into the chunk that ships this hook.
//
// The hook stays out of scope until its consumer slice ships;
// the strict chunk-boundary contract
// (ODD-BSTATE-TAX-001-B) requires the chain to never reach the
// main route's bundle.
//
// Hydration contract (browser-state-hydration spec §"Hydration
// guard against server / client mismatch"):
//   - SSR + the first client render return the typed default
//     (`null` — no taxon focused on first paint).
//   - After mount, `useSyncExternalStore` invokes
//     `subscribeLastTaxonId` which triggers the lazy
//     `hydrateFromStorage` call inside the infrastructure store.
//     The cache then mirrors `localStorage`, `getSnapshot`
//     returns the stored value, and React commits the follow-up
//     render.
//   - React's hydration guard never trips: the server snapshot
//     and the first client render are byte-equal (both are
//     `null`).
//
// Consumers MUST import through the public barrel
// (`src/modules/browser-state/index.ts`) — direct imports into
// this file are blocked by
// `.eslintrc.cjs::no-restricted-imports`.

import { useCallback, useSyncExternalStore } from "react";
import { DEFAULT_LAST_TAXON_ID } from "../domain/defaults";
import {
  readLastTaxonId,
  writeLastTaxonId,
  subscribeLastTaxonId,
} from "../infrastructure/storeLastTaxonId";

// ---------------------------------------------------------------------------
// useLastTaxonId — `[value, setValue]` tuple for the last focused
// taxon id. `null` is a valid value (no taxon focused).
//   - SSR + first client render returns `DEFAULT_LAST_TAXON_ID`
//     (`null`).
//   - `setValue` is a stable callback that mirrors `writeLastTaxonId`.
// ---------------------------------------------------------------------------
export function useLastTaxonId(): [
  number | null,
  (next: number | null) => void,
] {
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
