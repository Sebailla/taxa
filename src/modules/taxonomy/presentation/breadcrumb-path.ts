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
// ODD-NTP-005 — native source-aware ancestor reconstruction:
//   - CoL uses `Taxon.parent_id` (the global backbone). Each cached
//     taxon exposes its CoL parent on the wire, so the walker simply
//     resolves the next hop by reading the field and looking up the
//     targeted taxon in the cache.
//   - Freshwater uses `Taxon.freshwater_parent_id`. The freshwater
//     rows are isolated from CoL/WoRMS (a Freshwater taxon's
//     `parent_id` points at the CoL backbone, not at the Freshwater
//     root), so the walker must dispatch on the active source to pick
//     the right field.
//   - WoRMS reconstructs ancestry from attached source-tree edges.
//     The FastAPI wire does NOT expose `worms_parent_id` (see the
//     domain-level note in `../domain/taxon.ts`), so the React
//     projection cannot carry the column. Instead, the walker
//     derives a reverse index from the cached `childIdsByParent`
//     map — every `(parent, child)` attachment the tree has
//     attached under the WoRMS source is a source-safe edge, and
//     the walker walks back through those edges. This guarantees
//     only source-matching ancestors participate (CoL rows that
//     happen to share ids with WoRMS rows cannot back-walk through
//     a WoRMS view).
//   - `walkBreadcrumbForSource` is the TreeState-aware walker the
//     React `Breadcrumb` component consumes. It dispatches on the
//     active source and applies the source-safe parent resolver
//     internally. `walkBreadcrumbPath` (the resolver-parameterised
//     version) stays for tests + future application-layer
//     composition that already has the parent resolver at hand.
//
// spec.md rule 4: this helper depends on `Taxon` + `Rank` from the
// internal domain (`../domain/taxon.js`) only. No React, no Next, no
// HTTP, no DOM, no framework imports. Pure: no I/O, no async, no state
// mutation.

import type { Rank, Taxon } from "../domain/taxon";

/** Hard cap on parent-chain hops. Mirrors the legacy `let safety = 30`. */
export const BREADCRUMB_MAX_HOPS = 30;

/** Source qualifier for the parent chain. Mirrors `SourceFilter` from
 *  `../application/ports.js` but re-declared here so the presentation
 *  layer does not import from a sibling layer (spec.md rule 4).
 *  Value set MUST stay byte-identical to the infrastructure type. */
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

/** Minimal source-aware TreeState shape the breadcrumb walker needs.
 *  Decouples this helper from `tree-state.ts` (which would create a
 *  sibling-import cycle from `tree-state.ts` -> `breadcrumb-path.ts`
 *  in a future composition). Mirrors the public fields of
 *  `TreeState` used by `walkBreadcrumbForSource`. */
export interface BreadcrumbTreeState {
  readonly nodes: ReadonlyMap<number, Taxon>;
  readonly childIdsByParent: ReadonlyMap<number, readonly number[]>;
}

/** ODD-NTP-005 — derive the source-safe WoRMS parent reverse index
 *  from `TreeState.childIdsByParent`. For every cached
 *  `(parentId, children)` attachment, every child whose `worms_id`
 *  is not null is recorded as having `parentId` as its WoRMS
 *  parent. Children that don't pass `sourceMatches(child, "worms")`
 *  are excluded, so the resulting map can ONLY walk back through
 *  WoRMS-passing ancestors. This is the bridge the legacy
 *  `web/breadcrumb.js::parentIdOf` would need if the wire shape
 *  actually exposed `worms_parent_id` — but the FastAPI wire does
 *  not, so we derive the same relationship from the cached
 *  source-safe edges.
 *
 *  - Multiple cached parents could in principle claim the same
 *    child (a taxon should not normally appear twice under
 *    different parents, but a stale cache from a pre-source-switch
 *    projection might). The reverse index records the FIRST
 *    source-safe attachment and ignores subsequent ones — the
 *    resulting ancestor chain is therefore deterministic.
 *  - The function is pure: it returns a fresh `Map` instance on
 *    every call. Callers that cache the result (e.g. the React
 *    component, which already memoises via the `state` reference
 *    identity) re-derive on every state change.
 *  - Empty map when no WoRMS-passing parent/child edges are
 *    cached — the breadcrumb walker handles this case by
 *    truncating the chain at the focused taxon (single-segment
 *    path). */
export function deriveWoRMSEdges(
  state: BreadcrumbTreeState,
): ReadonlyMap<number, number> {
  const childToParent = new Map<number, number>();
  for (const [parentId, childIds] of state.childIdsByParent.entries()) {
    const parent = state.nodes.get(parentId);
    if (!parent || parent.worms_id === null) continue;
    for (const childId of childIds) {
      if (childToParent.has(childId)) continue;
      const child = state.nodes.get(childId);
      if (!child || child.worms_id === null) continue;
      childToParent.set(childId, parentId);
    }
  }
  return childToParent;
}

/** ODD-NTP-005 — TreeState-aware parent-chain walker. Picks the
 *  right source-safe resolver internally so the React component
 *  can dispatch on the active source without threading a closure
 *  through the helpers. See the file header for the per-source
 *  contract:
 *    - CoL: parent(X) = X.parent_id (must be a cached CoL taxon).
 *    - Freshwater: parent(X) = X.freshwater_parent_id (must be a
 *      cached Freshwater taxon).
 *    - WoRMS: parent(X) = the closest cached WoRMS ancestor
 *      (`deriveWoRMSEdges(state).get(X.id)`). When the focused
 *      taxon has never been expanded as a child of any WoRMS
 *      parent (the chain has not been walked), the resolver
 *      returns `null` and the breadcrumb truncates at the
 *      focused taxon — the same behaviour the legacy oracle has
 *      for a taxon's first visit.
 *
 *  Cycle safety: the walker applies the 30-hop cap
 *  (`BREADCRUMB_MAX_HOPS`) so a corrupted cache cannot spin
 *  forever. The cap mirrors the legacy `let safety = 30`.
 *
 *  Source isolation: CoL ↔ WoRMS ↔ Freshwater parents NEVER
 *  cross. A WoRMS-only child whose CoL `parent_id` points at a
 *  CoL backbone row resolves to `null` under CoL when the parent
 *  is not cached (the walker stops at the focused taxon); under
 *  WoRMS the same child's WoRMS parent is read from the derived
 *  edge map, which never records a non-WoRMS-passing parent.
 */
export function walkBreadcrumbForSource(
  focusedId: number | null,
  source: BreadcrumbSource,
  state: BreadcrumbTreeState,
): readonly BreadcrumbSegment[] {
  if (focusedId === null) return [];
  const cache = state.nodes;
  const wormsEdges = source === "worms" ? deriveWoRMSEdges(state) : null;
  const parentIdOf: ParentIdResolver = (taxon, src) => {
    if (src === "freshwater") {
      const id = taxon.freshwater_parent_id;
      if (id === null) return null;
      // Source-isolation guard: a Freshwater ancestor must itself
      // pass the Freshwater predicate (otherwise the chain has
      // already crossed into CoL/WoRMS territory and the walker
      // must stop).
      const candidate = cache.get(id);
      if (!candidate || candidate.freshwater_id === null) return null;
      return id;
    }
    if (src === "worms") {
      // WoRMS ancestry is reconstructed from attached tree edges
      // (the FastAPI wire does not expose `worms_parent_id`).
      // The edge map records only WoRMS-passing parents, so the
      // back-walk is source-safe by construction.
      return wormsEdges ? (wormsEdges.get(taxon.id) ?? null) : null;
    }
    // CoL: `Taxon.parent_id`. Source-isolation guard: a CoL
    // ancestor must itself pass the CoL predicate (otherwise
    // the chain has already crossed into WoRMS / Freshwater
    // territory via `parent_id IS NULL` rows that nevertheless
    // have a CoL parent through a sibling projection).
    const id = taxon.parent_id;
    if (id === null) return null;
    const candidate = cache.get(id);
    if (!candidate || candidate.coldp_id === null) return null;
    return id;
  };
  return walkBreadcrumbPath(focusedId, source, cache, parentIdOf);
}
