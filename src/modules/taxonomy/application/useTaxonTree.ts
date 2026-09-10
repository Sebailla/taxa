// View-model surface for the taxonomy module (PR 5a.1).
//
// This layer is intentionally framework-free: no React, no DOM, no
// fetch. The functions below take pre-loaded `TaxonRecord` collections
// and project them into presentation-ready view models. The actual
// network call is owned by the infrastructure layer and is expected to
// be resolved by the React hook in PR 5a.2 before this surface is
// called.

import {
  type BreadcrumbSegment,
  type Rank,
  type TaxonRecord,
  type TreeSource,
  parentIdOf,
  walkParentChain,
} from "../domain/taxon";

/** Presentation-ready tree node. Immutable so React's reference-equality
  *  memoisation in 5a.2 can short-circuit subtree re-renders. */
export interface TaxonTreeNode {
  readonly id: number;
  readonly name: string;
  readonly rank: Rank;
  readonly children: readonly TaxonTreeNode[];
}

/** Presentation-ready breadcrumb. A single ordered list of segments
  *  plus the `source` so the renderer can pick the right link route
  *  per source. */
export interface BreadcrumbViewModel {
  readonly source: TreeSource;
  readonly segments: readonly BreadcrumbSegment[];
}

/** Build a `TaxonTreeNode` view model for `rootId` by walking every
  *  record whose `source`-scoped parent pointer resolves to a node in
  *  the current subtree. Returns `null` when `rootId` is absent from
  *  `records` so callers can distinguish "not loaded" from "loaded,
  *  empty subtree". */
export function loadTaxonTree(
  records: readonly TaxonRecord[],
  rootId: number,
  source: TreeSource,
): TaxonTreeNode | null {
  const byId = new Map<number, TaxonRecord>();
  for (const record of records) byId.set(record.id, record);
  const root = byId.get(rootId);
  if (!root) return null;
  return buildNode(root, source, byId);
}

function buildNode(
  record: TaxonRecord,
  source: TreeSource,
  byId: ReadonlyMap<number, TaxonRecord>,
): TaxonTreeNode {
  const children: TaxonTreeNode[] = [];
  for (const candidate of byId.values()) {
    if (candidate.id !== record.id && parentIdOf(candidate, source) === record.id) {
      children.push(buildNode(candidate, source, byId));
    }
  }
  return {
    id: record.id,
    name: record.scientific_name,
    rank: record.rank,
    children,
  };
}

/** Project the `source`-scoped parent chain of `id` into a flat
 *  breadcrumb list. Order is root-first so the renderer can drop the
 *  array into a horizontal flex row without reversing it. */
export function buildBreadcrumb(
  records: readonly TaxonRecord[],
  id: number,
  source: TreeSource,
): BreadcrumbViewModel {
  const byId = new Map<number, TaxonRecord>();
  for (const record of records) byId.set(record.id, record);
  const chain = walkParentChain(id, source, byId);
  const segments: BreadcrumbSegment[] = chain.map((record) => ({
    id: record.id,
    name: record.scientific_name,
    rank: record.rank,
  }));
  return { source, segments };
}