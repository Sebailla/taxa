// Taxonomy presentation — pure `walkBreadcrumbPath` helper (PR 5c slice 1).
//
// The React `Breadcrumb` component lives in a later PR (5c slice 2). This
// file ships only the pure parent-chain walker so consumers can pre-compute
// the focused-taxon's ancestor chain outside the React tree (tests,
// server-side snapshots, view-model builders). The walker dispatches on
// the active source via a caller-supplied resolver — the canonical
// domain `Taxon` only carries `parent_id`, so source-specific parents
// (WoRMS / freshwater) come from the application layer as `parentIdOf`.
//
// spec.md rule 4: this helper depends on `Taxon` + `Rank` from the
// internal domain (`../domain/taxon.js`) only. No React, no Next, no
// HTTP, no DOM, no framework imports. Pure: no I/O, no async, no state
// mutation.

import type { Rank, Taxon } from "../domain/taxon.js";

/** Hard cap on parent-chain hops. Mirrors the legacy `let safety = 30`. */
export const BREADCRUMB_MAX_HOPS = 30;

/** Source qualifier for the parent chain. Mirrors `SourceFilter` from
 *  `../application/ports.js` but re-declared here so the presentation
 *  layer does not import from a sibling layer (spec.md rule 4). */
export type BreadcrumbSource = "col" | "worms" | "freshwater";

/** A single breadcrumb segment — focused taxon's ancestor chain,
 *  oldest first. Matches the legacy DOM's `pathSegments` array shape. */
export interface BreadcrumbSegment {
  readonly id: number;
  readonly name: string;
  readonly rank: Rank;
}

/** Resolves a `Taxon` to its parent id under the active source. The
 *  application layer composes this function (CoL reads `Taxon.parent_id`;
 *  WoRMS / freshwater read source-specific parents from per-source DTOs).
 *  The walker is source-agnostic; the source parameter is threaded
 *  through so the resolver can dispatch without the caller closing over it. */
export type ParentIdResolver = (
  taxon: Taxon,
  source: BreadcrumbSource,
) => number | null;

/** Pure, deterministic parent-chain walker. Empty for null focus or any
 *  id absent from the cache. Bounded at `BREADCRUMB_MAX_HOPS` hops. The
 *  walker does NOT throw on missing ancestors; it truncates. */
export function walkBreadcrumbPath(
  focusedId: number | null,
  source: BreadcrumbSource,
  cache: ReadonlyMap<number, Taxon>,
  parentIdOf: ParentIdResolver,
): readonly BreadcrumbSegment[] {
  if (focusedId === null) return [];
  const segments: BreadcrumbSegment[] = [];
  let currentId: number | null = focusedId;
  let safety = BREADCRUMB_MAX_HOPS;
  while (currentId !== null && safety-- > 0) {
    const node = cache.get(currentId);
    if (!node) break;
    segments.unshift({ id: currentId, name: node.name, rank: node.rank });
    currentId = parentIdOf(node, source);
  }
  return segments;
}
