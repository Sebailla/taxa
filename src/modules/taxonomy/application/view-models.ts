// Taxonomy application — pure readonly view-model types + builders.
// spec.md rule 4: domain ONLY; no framework, no HTTP, no DOM.

import type { Rank, Taxon } from "../domain/taxon.js";
import { compareRanks, isValidTaxon, RANK_ORDER } from "../domain/taxon.js";

/** Plain-data, immutable tree node. Children sorted by taxonomic
 *  breadth (kingdom → subspecies) then case-insensitive name. */
export interface TaxonNodeViewModel {
  readonly taxon: Taxon;
  readonly children: readonly TaxonNodeViewModel[];
  readonly depth: number;
  readonly isLeaf: boolean;
  readonly childCount: number;
  readonly descendantCount: number;
}

/** Forest of taxonomies. Empty forest is the valid empty-state. */
export interface TaxonTreeViewModel {
  readonly roots: readonly TaxonNodeViewModel[];
  readonly totalNodeCount: number;
}

/** Breadcrumb segment — focused taxon's ancestor chain, oldest first. */
export interface TaxonBreadcrumbSegment {
  readonly id: number;
  readonly name: string;
  readonly rank: Rank;
}

/** Detail panel view-model — focused taxon + breadcrumb + summary. */
export interface TaxonDetailViewModel {
  readonly taxon: Taxon;
  readonly breadcrumb: readonly TaxonBreadcrumbSegment[];
  readonly childCount: number;
  readonly descendantCount: number;
  readonly hasChildren: boolean;
  readonly rankIndex: number;
}

/** Broader ranks first, then case-insensitive name. */
function compareByRankThenName(a: Taxon, b: Taxon): number {
  const r = compareRanks(a.rank, b.rank);
  if (r !== 0) return r;
  const an = a.name.toLowerCase();
  const bn = b.name.toLowerCase();
  if (an < bn) return -1;
  if (an > bn) return 1;
  return 0;
}

/** Build a tree view-model from a flat list of `Taxon` records.
 *  Walks `parent_id` deterministically:
 *    - Roots: `parent_id === null` OR points outside the loaded set.
 *    - Cycles: a record on the DFS stack renders as a leaf.
 *    - Children sort by rank breadth, then case-insensitive name.
 *  Pure: no I/O, no HTTP, no React. */
export function buildTaxonTree(
  flatTaxa: readonly Taxon[],
  options: { readonly rootIds?: readonly number[] } = {},
): TaxonTreeViewModel {
  // Defensive filter — a stray invalid record must not poison the forest.
  const valid = flatTaxa.filter(isValidTaxon);
  const byId = new Map<number, Taxon>();
  for (const t of valid) byId.set(t.id, t);

  // Bucket taxa by effective parent. Orphan (parent_id outside the
  // loaded set) folds into the null bucket.
  const childrenOf = new Map<number | null, Taxon[]>();
  for (const t of valid) {
    const parentKey: number | null =
      t.parent_id !== null && byId.has(t.parent_id) ? t.parent_id : null;
    const bucket = childrenOf.get(parentKey);
    if (bucket) bucket.push(t);
    else childrenOf.set(parentKey, [t]);
  }
  for (const bucket of childrenOf.values()) bucket.sort(compareByRankThenName);

  let roots: Taxon[];
  if (options.rootIds && options.rootIds.length > 0) {
    roots = [];
    for (const id of options.rootIds) {
      const t = byId.get(id);
      if (t !== undefined) roots.push(t);
    }
  } else {
    roots = childrenOf.get(null) ?? [];
  }

  // Cycle-safe DFS.
  const onStack = new Set<number>();
  function build(taxon: Taxon, depth: number): TaxonNodeViewModel {
    if (onStack.has(taxon.id)) {
      // Cycle break: emit a leaf so the taxon still renders.
      onStack.delete(taxon.id);
      return {
        taxon, children: [], depth,
        isLeaf: true, childCount: 0, descendantCount: 0,
      };
    }
    onStack.add(taxon.id);
    const kids = childrenOf.get(taxon.id) ?? [];
    const childNodes: TaxonNodeViewModel[] = [];
    for (const k of kids) childNodes.push(build(k, depth + 1));
    onStack.delete(taxon.id);
    let descendantCount = childNodes.length;
    for (const n of childNodes) descendantCount += n.descendantCount;
    return {
      taxon, children: childNodes, depth,
      isLeaf: childNodes.length === 0,
      childCount: childNodes.length,
      descendantCount,
    };
  }

  const rootNodes = roots.map((r) => build(r, 0));
  rootNodes.sort((a, b) => compareByRankThenName(a.taxon, b.taxon));

  let totalNodeCount = 0;
  for (const n of rootNodes) totalNodeCount += 1 + n.descendantCount;

  return { roots: rootNodes, totalNodeCount };
}

/** Build a detail view-model from the focused taxon + ancestor chain
 *  + child count + (optional) flattened subtree. Pure: no I/O.
 *  Raises a plain `Error` if any input fails `isValidTaxon`. */
export function buildTaxonDetail(args: {
  readonly taxon: Taxon;
  readonly ancestors: readonly Taxon[];
  readonly childCount: number;
  readonly allDescendants?: readonly Taxon[];
}): TaxonDetailViewModel {
  const { taxon, ancestors, childCount, allDescendants } = args;
  if (!isValidTaxon(taxon)) {
    throw new Error("buildTaxonDetail: focused taxon failed isValidTaxon validation");
  }
  for (let i = 0; i < ancestors.length; i++) {
    if (!isValidTaxon(ancestors[i]!)) {
      throw new Error("buildTaxonDetail: ancestor[" + i + "] failed isValidTaxon validation");
    }
  }
  const breadcrumb: TaxonBreadcrumbSegment[] = [];
  for (const a of ancestors) breadcrumb.push({ id: a.id, name: a.name, rank: a.rank });
  breadcrumb.push({ id: taxon.id, name: taxon.name, rank: taxon.rank });
  const descendantCount = allDescendants ? allDescendants.length : 0;
  return {
    taxon, breadcrumb, childCount, descendantCount,
    hasChildren: childCount > 0,
    rankIndex: RANK_ORDER.indexOf(taxon.rank),
  };
}
