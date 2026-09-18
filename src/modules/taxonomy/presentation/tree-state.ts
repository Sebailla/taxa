// Taxonomy presentation — pure tree-state helper (ODD-VTREE-001).
// Manages roots, expanded-node ids, child attachment, per-node
// load status, and the active source filter (ODD-NTP-002). The
// React `TaxonomyTree` component (ODD-VTREE-002 / ODD-NTP-002)
// consumes this helper directly. spec.md rule 4: depends on the
// internal domain only — no React, no Next, no HTTP, no DOM, no fetch.
//
// ODD-NTP-002 — native source parity:
//   - The legacy tree exposed three independent source views (CoL,
//     WoRMS, Freshwater) with three distinct roots, parent chains,
//     and per-source filtering. The React tree must mirror that
//     contract through the same `TaxonomySource` qualifier the
//     infrastructure helper already exposes (ODD-NTP-001).
//   - The source union is re-declared here on purpose — tree-state
//     stays framework-free and may not import from the sibling
//     infrastructure layer (spec.md rule 4 + the ESLint
//     `no-restricted-imports` guard). The literal value set is
//     identical to the one in the infrastructure helper so
//     dispatching is value-equal even though the type lives in two
//     layers. A future consolidation lands via the application port
//     when source-aware services start consuming tree-state.
//   - `sourceMatches` is the pure predicate: CoL keeps `coldp_id`
//     rows; WoRMS keeps `worms_id` rows; Freshwater keeps
//     `freshwater_id` rows. Source membership is a per-taxon
//     nullability check — never a coerced "fill in zeros" rule —
//     so a CoL-only row stays out of the WoRMS view, a WoRMS-only
//     row stays out of CoL, and the isolated freshwater overlay
//     never bleeds into either.
//   - `withRootsForSource` is the roots merge + filter pipeline:
//     it inserts every root into the `nodes` map (so the cache
//     survives a future source switch) but exposes ONLY the ids
//     that pass the active source predicate. Foreign ids are
//     preserved on `nodes` so a later source switch can re-surface
//     them without a re-fetch.
//   - `filterChildrenForSource` applies the same predicate to
//     fetched children before they hit `attachChildren`. The
//     attached ids stay coherent with the source the user asked
//     for; stale rows from a previous source (or the same fetch but
//     a different column) never surface in the visible tree.
//   - `resetSourceState` clears every source-bound piece of state
//     (roots, expanded set, child cache, load status, any root-row
//     error preserved on `root.message` upstream) before the new
//     source's roots paint. The native parity oracle (legacy
//     `web/nav.js::tree-source toggle`) does the same on every
//     switch so the user never sees CoL rows under WoRMS, an
//     expanded node that no longer exists, or a half-attached
//     child set with a `loaded` status. `nodes` survives the
//     reset so the next `fetchChildren` round trip can re-use the
//     already-fetched taxon's projection (the projection carries
//     every FastAPI field; see ODD-NTP-001 wire → domain).

import type { Taxon } from "../domain/taxon";

/** Per-node load lifecycle. `idle` is the default for ids the helper
 *  has not observed. */
export type NodeLoadStatus = "idle" | "loading" | "loaded" | "error";

/** Active source qualifier for the visible tree. Mirrors
 *  `TaxonomySource` (`infrastructure/api.ts`) — re-declared here so
 *  the presentation helper stays free of any infrastructure
 *  dependency (spec.md rule 4 + ESLint `no-restricted-imports`).
 *  Value set MUST stay byte-identical to the infrastructure type;
 *  ODD-NTP-002 reuses the exact literal sequence to preserve the
 *  native order in the segmented control. */
export type TreeSource = "col" | "worms" | "freshwater";

/** Immutable tree state. All fields are readonly; mutators return a
 *  fresh instance. Children are keyed by `Taxon.id`. The `nodes`
 *  map survives every source-bound reset (the projection preserves
 *  every FastAPI field, including source identifiers, so a later
 *  source switch can re-render cached rows without a re-fetch). */
export interface TreeState {
  readonly nodes: ReadonlyMap<number, Taxon>;
  readonly rootIds: readonly number[];
  readonly childIdsByParent: ReadonlyMap<number, readonly number[]>;
  readonly expandedIds: ReadonlySet<number>;
  readonly loadStatus: ReadonlyMap<number, NodeLoadStatus>;
}

function makeEmptyState(): TreeState {
  return {
    nodes: new Map<number, Taxon>(),
    rootIds: [],
    childIdsByParent: new Map<number, readonly number[]>(),
    expandedIds: new Set<number>(),
    loadStatus: new Map<number, NodeLoadStatus>(),
  };
}

/** Empty state — start here before the first `fetchDomains` resolves. */
export const EMPTY_TREE_STATE: TreeState = Object.freeze(makeEmptyState());

/** Replace the root-id list. Merges `roots` into `nodes`. */
export function withRoots(
  state: TreeState,
  roots: readonly Taxon[],
): TreeState {
  const nodes = new Map(state.nodes);
  const rootIds: number[] = [];
  for (const t of roots) {
    nodes.set(t.id, t);
    rootIds.push(t.id);
  }
  return {
    nodes, rootIds,
    childIdsByParent: state.childIdsByParent,
    expandedIds: state.expandedIds,
    loadStatus: state.loadStatus,
  };
}

/** ODD-NTP-002 — source-aware roots merge. Inserts every fetched
 *  root into the `nodes` cache (so a later source switch can
 *  re-surface cached rows without a re-fetch) and exposes ONLY
 *  the ids that pass `sourceMatches(taxon, source)` on
 *  `state.rootIds`. Foreign rows are kept on `nodes` but hidden
 *  from the visible roots list until the user picks the matching
 *  source. Order preserves the canonical fetch sequence so the
 *  rendered roots stay stable across filter passes. */
export function withRootsForSource(
  state: TreeState,
  roots: readonly Taxon[],
  source: TreeSource,
): TreeState {
  const nodes = new Map(state.nodes);
  const rootIds: number[] = [];
  for (const t of roots) {
    nodes.set(t.id, t);
    if (sourceMatches(t, source)) rootIds.push(t.id);
  }
  return {
    nodes, rootIds,
    childIdsByParent: state.childIdsByParent,
    expandedIds: state.expandedIds,
    loadStatus: state.loadStatus,
  };
}

/** Children of `parentId`, in insertion order; `[]` when absent. */
export function childIds(state: TreeState, parentId: number): readonly number[] {
  return state.childIdsByParent.get(parentId) ?? [];
}

/** True iff `id` is in the expanded set. */
export function isExpanded(state: TreeState, id: number): boolean {
  return state.expandedIds.has(id);
}

/** Mark `id` as expanded. Idempotent. */
export function expand(state: TreeState, id: number): TreeState {
  if (state.expandedIds.has(id)) return state;
  const expanded = new Set(state.expandedIds);
  expanded.add(id);
  return { ...state, expandedIds: expanded };
}

/** Mark `id` as collapsed. Idempotent. */
export function collapse(state: TreeState, id: number): TreeState {
  if (!state.expandedIds.has(id)) return state;
  const expanded = new Set(state.expandedIds);
  expanded.delete(id);
  return { ...state, expandedIds: expanded };
}

/** Flip the expansion flag for `id`. */
export function toggleExpand(state: TreeState, id: number): TreeState {
  return state.expandedIds.has(id) ? collapse(state, id) : expand(state, id);
}

/** Attach children to `parentId`. Duplicate ids collapse to the first
 *  occurrence (preserving insertion order); already-attached ids are
 *  not re-attached. The parent's load status transitions to `loaded`
 *  (the caller signals request start via `setLoadStatus("loading")`
 *  and failure via `setLoadStatus("error")`). */
export function attachChildren(
  state: TreeState,
  parentId: number,
  children: readonly Taxon[],
): TreeState {
  const nodes = new Map(state.nodes);
  const existing = state.childIdsByParent.get(parentId) ?? [];
  const seen = new Set(existing);
  const merged: number[] = [...existing];
  for (const c of children) {
    nodes.set(c.id, c);
    if (!seen.has(c.id)) {
      seen.add(c.id);
      merged.push(c.id);
    }
  }
  const childIdsByParent = new Map(state.childIdsByParent);
  childIdsByParent.set(parentId, merged);
  const loadStatus = new Map(state.loadStatus);
  loadStatus.set(parentId, "loaded");
  return { ...state, nodes, childIdsByParent, loadStatus };
}

/** ODD-NTP-002 — source-aware child attachment. Applies the
 *  `sourceMatches` predicate to the fetched payload before
 *  `attachChildren`, so foreign-source rows (e.g. WoRMS-only rows
 *  landing under a CoL parent's response) never enter the visible
 *  child list. The parent still transitions to `loaded` so the load
 *  status tracks the request lifecycle, and the merged ids remain
 *  insertion-stable (matching the legacy `web/api.js::loadChildren`
 *  contract). */
export function attachChildrenForSource(
  state: TreeState,
  parentId: number,
  children: readonly Taxon[],
  source: TreeSource,
): TreeState {
  return attachChildren(state, parentId, filterChildrenForSource(children, source));
}

/** ODD-NTP-002 — source predicate. Mirrors the legacy
 *  `web/tree.js::matchesTreeSource` contract byte-for-byte so the
 *  React tree presents the same roots + children the legacy tree
 *  would. CoL keeps `coldp_id IS NOT NULL` rows; WoRMS keeps
 *  `worms_id IS NOT NULL` rows; Freshwater keeps
 *  `freshwater_id IS NOT NULL` rows. Nullability check only —
 *  no coercion of missing wire fields to zero / empty string /
 *  another source. */
export function sourceMatches(taxon: Taxon, source: TreeSource): boolean {
  if (source === "col") return taxon.coldp_id !== null;
  if (source === "worms") return taxon.worms_id !== null;
  return taxon.freshwater_id !== null;
}

/** ODD-NTP-002 — pure source filter over a child array. Used by
 *  `attachChildrenForSource` and by tests; preserves the fetched
 *  insertion order so the source predicate doesn't reshuffle rows
 *  the legacy tree would render sequentially. */
export function filterChildrenForSource(
  children: readonly Taxon[],
  source: TreeSource,
): readonly Taxon[] {
  const filtered: Taxon[] = [];
  for (const c of children) {
    if (sourceMatches(c, source)) filtered.push(c);
  }
  return filtered;
}

/** ODD-NTP-002 — does the canonical root payload contain at least
 *  one row that belongs to the Freshwater overlay? Mirrors the
 *  legacy `web/app.js::boot` check that gates the Freshwater
 *  toggle's append on `roots.some(r => r.freshwater_id != null)`.
 *  The Freshwater toggle is conditional on this predicate so the
 *  segmented control only carries three buttons when the overlay
 *  was actually loaded into the database. */
export function hasFreshwaterRoot(roots: readonly Taxon[]): boolean {
  for (const r of roots) {
    if (r.freshwater_id !== null) return true;
  }
  return false;
}

/** ODD-NTP-002 — native source order in the native segmented
 *  control: CoL first, then WoRMS, then Freshwater only if the
 *  fetched root payload carries at least one freshwater row.
 *  Mirrors the legacy HTML order (`CoL` → `WoRMS` → `Freshwater`
 *  appended at boot). Returning a fresh array keeps the helper
 *  pure and lets tests pin the order without stateful mocks. */
export function availableSourcesFor(
  roots: readonly Taxon[],
): readonly TreeSource[] {
  const sources: TreeSource[] = ["col", "worms"];
  if (hasFreshwaterRoot(roots)) sources.push("freshwater");
  return sources;
}

/** ODD-NTP-002 — clear every source-bound piece of state on a
 *  source switch. Mirrors the legacy
 *  `web/nav.js::tree-source toggle` reset:
 *    - root ids → empty (replaced by the next `withRootsForSource`)
 *    - expanded set → cleared (a closed id belongs to the previous
 *      source's hierarchy and may not exist under the new one)
 *    - child cache → cleared (children were loaded with the previous
 *      source's `?source=…` query and must be re-fetched with the
 *      matching source — WoRMS vs CoL vs Freshwater parent chains
 *      are independent)
 *    - load status → cleared (the previous load lifecycle no
 *      longer matches the visible ids; a `loaded` row in WoRMS
 *      view is `idle` again under Freshwater)
 *    - nodes → PRESERVED (the projection carries every FastAPI
 *      field including source identifiers — a later source switch
 *      can re-render cached rows without a re-fetch, and the
 *      `withRootsForSource` call that follows can re-surface
 *      foreign rows that were hidden under the previous filter)
 *  The raw root cache ALSO survives the switch — `loadRoots` runs
 *  once on mount and the React island re-projects the cached
 *  payload through the `rawRoots + activeSource` effect on every
 *  source change, never issuing a second `/api/domains` request.
 *  The caller is responsible only for resetting the upstream
 *  root-row error message + the active source variable (those
 *  live on the React island, not on `TreeState`). */
export function resetSourceState(state: TreeState): TreeState {
  return {
    nodes: state.nodes,
    rootIds: [],
    childIdsByParent: new Map<number, readonly number[]>(),
    expandedIds: new Set<number>(),
    loadStatus: new Map<number, NodeLoadStatus>(),
  };
}

/** Update the load status for `id`. */
export function setLoadStatus(
  state: TreeState,
  id: number,
  status: NodeLoadStatus,
): TreeState {
  const loadStatus = new Map(state.loadStatus);
  loadStatus.set(id, status);
  return { ...state, loadStatus };
}

/** Read the load status for `id`; defaults to `idle`. */
export function loadStatus(state: TreeState, id: number): NodeLoadStatus {
  return state.loadStatus.get(id) ?? "idle";
}