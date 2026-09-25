"use client";

// Browser-state application — React adapter for the typed
// explorer-state store (`taxa.fex.explorerState`).
//
// ODD-BSTATE-TAX-001-A — per-key module split. The previous
// monolithic `application/useBrowserStateKey.ts` is replaced by
// one hook file per storage key. `useExplorerState` imports
// ONLY from `infrastructure/storeExplorerState.ts`, NOT from
// the sibling stores (theme / tree-source / last-taxon-id /
// kebab-open-id / internal-flag). Turbopack retention relies on
// this isolation — any cross-key import would silently
// re-bundle the forbidden localStorage key literals into the
// chunk that ships this hook.
//
// ODD-BSTATE-EXPLORER-PERSIST — the EXPLORER-PERSIST
// architecture correction extends the per-key family by one
// entry (`useExplorerState`). The hook is the React adapter
// for the typed explorer-state store; the Browser-tab Explorer
// mount reads the value through `useSyncExternalStore`. Its
// server + hydration snapshots are `null`; after hydration, the
// store exposes the persisted value or its canonical empty
// `PersistedExplorerState` default.
//
// Hydration contract (browser-state-hydration spec §"Hydration
// guard against server / client mismatch"):
//   - The server + hydration renders both use the `null` value
//     returned by `getServerSnapshot`, so a browser-stored value
//     cannot create a server/client markup mismatch.
//   - After hydration, the per-key store hydrates from storage
//     when React reads the snapshot/subscribes. Missing or invalid
//     data resolves to the canonical empty record; valid data is
//     surfaced on the follow-up render.
//
// Consumers MUST import through the public barrel
// (`src/modules/browser-state/index.ts`) — direct imports into
// this file are blocked by
// `.eslintrc.cjs::no-restricted-imports`.

import { useCallback, useSyncExternalStore } from "react";
import {
  readExplorerState,
  writeExplorerState,
  subscribeExplorerState,
} from "../infrastructure/storeExplorerState";
import type { PersistedExplorerState } from "../domain/explorer-state";

// ---------------------------------------------------------------------------
// useExplorerState — `[value, setValue]` tuple for the persisted
// explorer-state record.
//   - `value` is the typed `PersistedExplorerState`, or `null`
//     for the server + hydration snapshot. Missing, invalid, or
//     unavailable browser storage resolves to the canonical empty
//     record after hydration.
//   - `setValue` is a stable callback that mirrors
//     `writeExplorerState`. The matching server + hydration
//     snapshots prevent a stored value from changing the initial
//     render; the post-hydration snapshot surfaces the user's
//     persisted working set.
// ---------------------------------------------------------------------------
export function useExplorerState(): [
  PersistedExplorerState | null,
  (next: PersistedExplorerState) => void,
] {
  const value = useSyncExternalStore<PersistedExplorerState | null>(
    subscribeExplorerState,
    readExplorerState,
    () => null,
  );
  // `getServerSnapshot` returns `null` on the server and during
  // hydration, so both renders match without reading browser
  // storage. After hydration, `readExplorerState` and the store
  // subscription hydrate the cache; missing or invalid data is
  // represented by the canonical empty record.
  const setValue = useCallback(
    (next: PersistedExplorerState) => writeExplorerState(next),
    [],
  );
  return [value, setValue];
}
