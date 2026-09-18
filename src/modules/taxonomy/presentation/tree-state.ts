// Taxonomy presentation — pure tree-state helper (ODD-VTREE-001).
// Manages roots, expanded-node ids, child attachment, and per-node
// load status. The React `TaxonomyTree` component (ODD-VTREE-002)
// consumes this helper directly. spec.md rule 4: depends on the
// internal domain only — no React, no Next, no HTTP, no DOM, no fetch.

import type { Taxon } from "../domain/taxon";

/** Per-node load lifecycle. `idle` is the default for ids the helper
 *  has not observed. */
export type NodeLoadStatus = "idle" | "loading" | "loaded" | "error";

/** Immutable tree state. All fields are readonly; mutators return a
 *  fresh instance. Children are keyed by `Taxon.id`. */
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