"use client";

/**
 * Single-screen client entry for the App Router static export
 * (PR 3b + PR 4b + PR 5a.2 + PR 5a.3 + PR 5a.4 + PR 5c.1b-A).
 *
 * Renders the taxonomy tree + breadcrumb + detail-panel trio
 * inside the ``<main>`` slot that ``<AppShell>`` (PR 4b.2) emits.
 * ``useTaxonTree`` (PR 5a.2) owns the network boundary; ``Tree`` /
 * ``Breadcrumb`` / ``DetailPanel`` (PR 5a.3) consume the hook state
 * and stay in lock-step via ``setSelectedId``.
 *
 * PR 5a.4 wires the per-row ``Kebab`` (real menu with ``Search
 * online``) back to ``DetailPanel`` via the ``forceOpenSearch``
 * counter prop. Every time the user clicks ``Search online`` in any
 * kebab menu, this page bumps the counter; ``DetailPanel`` watches
 * the counter and snaps the active tab to ``Search`` even for
 * top-level taxa whose default would otherwise be ``Overview``.
 *
 * PR 5c.1b-A wires the tree-source toggle: this page reads the
 * current `treeSource` from the SINGLE typed store AppShell owns
 * (via `useBrowserStateStore` + `useSyncExternalStore`) and flows it
 * into `useTaxonTree` so a user-driven `setTreeSource` click
 * re-fetches the taxonomy tree. The page NEVER constructs a parallel
 * store — the AppShell is the sole `createBrowserStateStore()` call
 * site in the codebase.
 *
 * Chain-topology guard: this file MUST NOT directly import
 * ``./globals.css`` (owned by PR 3c; layout imports it once).
 */
import { useCallback, useState, useSyncExternalStore } from "react";

import {
  Breadcrumb,
  DetailPanel,
  Kebab,
  Tree,
  useTaxonTree,
} from "@taxa/taxonomy";

import { useBrowserStateStore } from "@taxa/app-shell";

export default function Page(): React.ReactElement {
  // PR 5c.1b-A — read the typed store from the AppShell-exposed context.
  // Before mount the store is `null`; we fall through to `"col"` (the
  // typed default) so SSR + initial CSR render byte-identical markup.
  const store = useBrowserStateStore();

  // Subscribe to the current `treeSource` value via `useSyncExternalStore`
  // so a user click on the header `tree-source-toggle` re-fetches the
  // taxonomy tree with the new source.
  const treeSource: import("@taxa/taxonomy").TreeSource = useSyncExternalStore(
    store ? store.subscribe : () => () => undefined,
    () => (store ? store.getTreeSource() : "col"),
    () => "col",
  );

  const treeState = useTaxonTree({ baseUrl: "", source: treeSource });
  // Counter — bumped every time a kebab's `Search online` fires.
  // DetailPanel watches this and snaps to the Search tab on each
  // increment (bumping the counter — not a boolean toggle — lets the
  // same tab be re-forced after the user has navigated away).
  const [forceOpenSearch, setForceOpenSearch] = useState<number>(0);
  const recordsById = new Map(treeState.records.map((r) => [r.id, r]));
  const selected = treeState.selectedId !== null
    ? recordsById.get(treeState.selectedId) ?? null
    : null;

  const onSearchOnline = useCallback((taxonId: number): void => {
    // Select the taxon first so the panel has a subject, then bump
    // the counter so DetailPanel's effect snaps the tab to Search.
    treeState.setSelectedId(taxonId);
    setForceOpenSearch((n) => n + 1);
  }, [treeState]);

  return (
    <>
      <h1>taxa</h1>
      <Breadcrumb viewModel={treeState.breadcrumb}
                  onSelect={treeState.setSelectedId} />
      <Tree root={treeState.tree}
            selectedId={treeState.selectedId}
            onSelect={treeState.setSelectedId}
            onSearchOnline={onSearchOnline} />
      <Kebab taxonId={selected?.id ?? 0}
             onSearchOnline={onSearchOnline} />
      <DetailPanel selected={selected}
                   forceOpenSearch={forceOpenSearch} />
    </>
  );
}