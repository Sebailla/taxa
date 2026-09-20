"use client";

// Browser-state application — React adapter for the typed
// kebab-open-id store (`taxa.tree.kebabOpenId`).
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `application/useBrowserStateKey.ts` is replaced by
// one hook file per storage key. `useKebabOpenId` imports only
// from `infrastructure/storeKebabOpenId.ts`, NOT from the
// sibling stores (theme / tree-source / last-taxon-id). Turbopack
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
//     (`null` — no kebab menu open on first paint; the kebab
//     closes on every reload by design).
//   - After mount, `useSyncExternalStore` invokes
//     `subscribeKebabOpenId` which triggers the lazy
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
import { DEFAULT_KEBAB_OPEN_ID } from "../domain/defaults";
import {
  readKebabOpenId,
  writeKebabOpenId,
  subscribeKebabOpenId,
} from "../infrastructure/storeKebabOpenId";

// ---------------------------------------------------------------------------
// useKebabOpenId — `[value, setValue]` tuple for the kebab-open
// taxon id. `null` is a valid value (no kebab menu open).
//   - SSR + first client render returns `DEFAULT_KEBAB_OPEN_ID`
//     (`null`).
//   - `setValue` is a stable callback that mirrors
//     `writeKebabOpenId`.
// ---------------------------------------------------------------------------
export function useKebabOpenId(): [
  number | null,
  (next: number | null) => void,
] {
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
