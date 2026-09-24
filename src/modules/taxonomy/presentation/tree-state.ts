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

import type { Rank, Taxon } from "../domain/taxon";
import { compareRanks } from "../domain/taxon";

/** ODD-NTP-003 — page size for native tier grouping. Mirrors the
 *  legacy `web/state.js::PAGE_SIZE` constant. Each `(parentId,
 *  rank)` group shows up to this many children before a "Load N
 *  more" / "Load all" affordance appears. Native ordering:
 *  PAGE_SIZE children render in insertion order, then a single
 *  "Load N more" button on the tier header reveals every
 *  remaining child at once. */
export const PAGE_SIZE = 5;

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
 *  source switch can re-render cached rows without a re-fetch).
 *
 *  ODD-NTP-003 — `showAll` mirrors the legacy
 *  `web/state.js::showAll` set: keys are `"${parentId}::${rank}"`
 *  and presence means the corresponding tier group is fully
 *  unrolled (no PAGE_SIZE staircase). The collapse-all control and
 *  the source switch both clear `showAll` so the tree rebuilds
 *  from a blank slate, exactly as the legacy nav.js reset did. */
export interface TreeState {
  readonly nodes: ReadonlyMap<number, Taxon>;
  readonly rootIds: readonly number[];
  readonly childIdsByParent: ReadonlyMap<number, readonly number[]>;
  readonly expandedIds: ReadonlySet<number>;
  readonly loadStatus: ReadonlyMap<number, NodeLoadStatus>;
  readonly showAll: ReadonlySet<string>;
}

function makeEmptyState(): TreeState {
  return {
    nodes: new Map<number, Taxon>(),
    rootIds: [],
    childIdsByParent: new Map<number, readonly number[]>(),
    expandedIds: new Set<number>(),
    loadStatus: new Map<number, NodeLoadStatus>(),
    showAll: new Set<string>(),
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
    showAll: state.showAll,
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
    showAll: state.showAll,
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

/** ODD-JKNAV-001 — flat list of visible taxon ids in render
 *  order. The walker recurses through `rootIds` then each
 *  parent's `childIdsByParent`, descending only into ids that
 *  are in `expandedIds` (so a collapsed subtree contributes
 *  only its root row, matching what the user sees on screen).
 *  Pure helper — no React, no DOM, no refs. The j/k keyboard
 *  handler in TaxonomyTree.tsx uses this to compute the next /
 *  previous row when the user presses `j` or `k`. */
export function flattenVisibleRows(state: TreeState): readonly number[] {
  const out: number[] = [];
  const visit = (parentId: number | null): void => {
    const ids =
      parentId === null
        ? state.rootIds
        : (state.childIdsByParent.get(parentId) ?? []);
    for (const id of ids) {
      if (!state.nodes.has(id)) continue;
      out.push(id);
      if (state.expandedIds.has(id)) visit(id);
    }
  };
  visit(null);
  return out;
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

/** ODD-NTP-003 — a single `(parentId, rank)` tier slice as it should
 *  be rendered. Mirrors the legacy `web/tree.js::renderTierHeader`
 *  contract: the tier shows `visibleIds` (capped at PAGE_SIZE when
 *  `showAll` is absent) plus a "Load N more" affordance when
 *  `remaining > 0`. Children WITHIN a group preserve their fetched
 *  insertion order so the source predicate never reshuffles rows the
 *  legacy tree would render sequentially. Groups are sorted by
 *  `compareRanks` (broadest-first) so the legacy order survives the
 *  React port. */
export interface RankGroup {
  readonly rank: Rank;
  readonly count: number;
  readonly visibleIds: readonly number[];
  readonly remaining: number;
  readonly fullyShown: boolean;
}

/** ODD-NTP-003 — pure source-aware group + paginate pipeline.
 *  Reads `state.childIdsByParent.get(parentId)` and applies, in order:
 *    1. `sourceMatches` filter (foreign-source rows from a mixed
 *       payload never enter the visible tier list)
 *    2. rank grouping (children WITHIN a group keep insertion order;
 *       GROUPS sort by `compareRanks`)
 *    3. PAGE_SIZE staircase (cap at PAGE_SIZE unless `showAll`
 *       contains `"${parentId}::${rank}"`)
 *  An empty child bucket (no children cached for the parent, or no
 *  matching-source children) yields an empty groups list — callers
 *  can skip the tier-header slot. Matches the legacy
 *  `web/tree.js::renderNode` flow bit-for-bit so the React tree's
 *  visible tiers match the legacy oracle on CoL / WoRMS /
 *  Freshwater and across source switches. */
export function groupChildrenByRank(
  state: TreeState,
  parentId: number,
  source: TreeSource,
): readonly RankGroup[] {
  const childIdList = state.childIdsByParent.get(parentId);
  if (!childIdList || childIdList.length === 0) return [];
  // Source-filter + group by rank in a single pass so the foreign-
  // source rows never enter the bucket and the rank-order list
  // stays canonical.
  const bucket = new Map<Rank, number[]>();
  for (const id of childIdList) {
    const child = state.nodes.get(id);
    if (!child) continue;
    if (!sourceMatches(child, source)) continue;
    let ids = bucket.get(child.rank);
    if (!ids) {
      ids = [];
      bucket.set(child.rank, ids);
    }
    ids.push(id);
  }
  // Sort groups by canonical rank breadth (broadest-first). Groups
  // with the same rank are already insertion-stable (the iteration
  // walks the child list in source-order).
  const sortedGroups = [...bucket.entries()].sort(
    ([aRank], [bRank]) => compareRanks(aRank, bRank),
  );
  const groups: RankGroup[] = [];
  for (const [rank, ids] of sortedGroups) {
    const fullyShown = state.showAll.has(`${parentId}::${rank}`);
    const visibleIds = fullyShown ? ids : ids.slice(0, PAGE_SIZE);
    groups.push({
      rank,
      count: ids.length,
      visibleIds,
      remaining: Math.max(0, ids.length - visibleIds.length),
      fullyShown,
    });
  }
  return groups;
}

/** ODD-NTP-003 — set the `showAll` flag for `(parentId, rank)`.
 *  `enabled=true` adds the key; `enabled=false` removes it.
 *  Idempotent — no-op when the flag already matches the requested
 *  state (the returned instance is reference-equal to `state` so
 *  React skips the render). Mirrors the legacy
 *  `web/nav.js::load-all` / `web/nav.js::collapseAll` actions. */
export function setShowAll(
  state: TreeState,
  parentId: number,
  rank: Rank,
  enabled: boolean,
): TreeState {
  const key = `${parentId}::${rank}`;
  const has = state.showAll.has(key);
  if (has === enabled) return state;
  const next = new Set(state.showAll);
  if (enabled) next.add(key);
  else next.delete(key);
  return { ...state, showAll: next };
}

/** ODD-NTP-003 — toggle the `showAll` flag for `(parentId, rank)`.
 *  Mirrors the legacy "Load N more" → "Load all" one-click
 *  unroll. */
export function toggleShowAll(
  state: TreeState,
  parentId: number,
  rank: Rank,
): TreeState {
  return setShowAll(state, parentId, rank, !state.showAll.has(`${parentId}::${rank}`));
}

/** ODD-NTP-003 — read the `showAll` flag for `(parentId, rank)`. */
export function isShowAll(
  state: TreeState,
  parentId: number,
  rank: Rank,
): boolean {
  return state.showAll.has(`${parentId}::${rank}`);
}

/** ODD-NTP-003 — clear every `showAll` entry without touching the
 *  expanded set. Used by the collapse-all control when the user
 *  wants to flatten just the tier pagination while keeping the
 *  expansion tree visible (rare; the canonical "collapse all"
 *  control uses `clearExpansion` instead). */
export function clearShowAll(state: TreeState): TreeState {
  if (state.showAll.size === 0) return state;
  return { ...state, showAll: new Set<string>() };
}

/** ODD-NTP-003 — native "Collapse all" semantics: clear both the
 *  expanded set AND every `showAll` flag so the tree returns to a
 *  flat roots-only view. Mirrors the legacy
 *  `web/nav.js::collapseAll` function byte-for-byte (the legacy
 *  early-return when both sets are empty is preserved by
 *  `clearShowAll`'s identity-equal no-op). */
export function clearExpansion(state: TreeState): TreeState {
  if (state.expandedIds.size === 0 && state.showAll.size === 0) return state;
  return {
    nodes: state.nodes,
    rootIds: state.rootIds,
    childIdsByParent: state.childIdsByParent,
    expandedIds: new Set<number>(),
    loadStatus: state.loadStatus,
    showAll: new Set<string>(),
  };
}

/** ODD-NTP-003 — native source-specific auto-unroll. When a node is
 *  expanded under the WoRMS or Freshwater source, every tier of
 *  that node is added to `showAll` so a single expansion reveals
 *  the full subtree — Biota → Animalia → phylum → class → ... →
 *  species without the user hitting "Load N more" at every level.
 *  CoL view keeps the PAGE_SIZE=5 staircase to stay snappy. The
 *  legacy `web/nav.js::toggleExpand` runs the same predicate after
 *  every successful `loadChildren(id)` call. The helper is a
 *  no-op when the source is CoL or when the parent has no
 *  matching-source children. */
export function autoUnrollForSource(
  state: TreeState,
  parentId: number,
  source: TreeSource,
): TreeState {
  if (source !== "worms" && source !== "freshwater") return state;
  const childIdList = state.childIdsByParent.get(parentId);
  if (!childIdList || childIdList.length === 0) return state;
  // `state.showAll` is typed `ReadonlySet<string>` (the public contract
  // for `TreeState`); copy-on-mutate must rebuild the set as a
  // mutable `Set<string>` so `.add(...)` is callable. The reference-
  // equality shortcut above (no-op when nothing changes) keeps the
  // common path allocation-free.
  let next: Set<string> = new Set(state.showAll);
  let mutated = next.size !== state.showAll.size;
  if (!mutated) {
    for (const id of childIdList) {
      const child = state.nodes.get(id);
      if (!child) continue;
      if (!sourceMatches(child, source)) continue;
      const key = `${parentId}::${child.rank}`;
      if (!next.has(key)) {
        mutated = true;
        break;
      }
    }
  }
  if (!mutated) return state;
  // Reset and re-add — cheaper than rebuilding a second map when
  // most tiers are already in `showAll`.
  if (next.size !== state.showAll.size) {
    next = new Set(state.showAll);
  }
  for (const id of childIdList) {
    const child = state.nodes.get(id);
    if (!child) continue;
    if (!sourceMatches(child, source)) continue;
    const key = `${parentId}::${child.rank}`;
    next.add(key);
  }
  return { ...state, showAll: next };
}

/** ODD-NTP-003 — read every tier key currently expanded for a
 *  parent. Used by the collapse-all control's tooltip / a11y
 *  affordance ("you have 3 tiers expanded"). Mirrors the legacy
 *  `state.expanded.size + state.showAll.size` heuristic. */
export function expandedTierCount(state: TreeState): number {
  return state.expandedIds.size + state.showAll.size;
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
 *    - showAll → cleared (ODD-NTP-003 — every tier key
 *      `"${parentId}::${rank}"` from the previous source may not
 *      even exist under the new one; the auto-unroll that follows
 *      rebuilds the set on the first WoRMS / Freshwater expand)
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
    showAll: new Set<string>(),
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

/** ODD-NTP-003 — leaf predicate. Matches the legacy
 *  `web/tree.js::isLeaf` (rank === "species" || rank ===
 *  "subspecies"). Leaves are disclosed by a `•` glyph (no chevron),
 *  carry no children, and clicking them dispatches the "select"
 *  data-action (selection lands in ODD-NTP-005; the contract here
 *  is only the rank classification). Re-exported here so the
 *  React component does not need to import `Rank` directly. */
export function isLeafRank(rank: Rank): boolean {
  return rank === "species" || rank === "subspecies";
}