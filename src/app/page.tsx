"use client";

/**
 * Single-screen client entry for the App Router static export
 * (PR 3b + PR 4b + PR 5a.2 + PR 5a.3).
 *
 * Renders the taxonomy tree + breadcrumb + detail-panel trio
 * inside the ``<main>`` slot that ``<AppShell>`` (PR 4b.2) emits.
 * ``useTaxonTree`` (PR 5a.2) owns the network boundary; ``Tree`` /
 * ``Breadcrumb`` / ``DetailPanel`` (PR 5a.3) consume the hook state
 * and stay in lock-step via ``setSelectedId``. ``KebabStub`` is a
 * no-op until 5a.4 (force-Search).
 *
 * Chain-topology guard: this file MUST NOT directly import
 * ``@taxa/app-shell`` (composed by layout.tsx),
 * ``@taxa/browser-state`` (transitive via the AppShell), or
 * ``./globals.css`` (owned by PR 3c; layout imports it once).
 */
import {
  Breadcrumb,
  DetailPanel,
  KebabStub,
  Tree,
  useTaxonTree,
} from "@taxa/taxonomy";

export default function Page(): React.ReactElement {
  const treeState = useTaxonTree({ baseUrl: "", source: "col" });
  const recordsById = new Map(treeState.records.map((r) => [r.id, r]));
  const selected = treeState.selectedId !== null
    ? recordsById.get(treeState.selectedId) ?? null
    : null;
  return (
    <>
      <h1>taxa</h1>
      <Breadcrumb viewModel={treeState.breadcrumb}
                  onSelect={treeState.setSelectedId} />
      <Tree root={treeState.tree}
            selectedId={treeState.selectedId}
            onSelect={treeState.setSelectedId} />
      <KebabStub taxonId={selected?.id ?? 0} />
      <DetailPanel selected={selected} />
    </>
  );
}