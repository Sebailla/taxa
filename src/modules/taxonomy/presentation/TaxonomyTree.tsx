"use client";

/**
 * TaxonomyTree — visible taxonomy tree (ODD-VTREE-002 / ODD-NTP-002 /
 * ODD-NTP-003).
 *
 * Client island. Fetches root domains on mount through the canonical
 * `fetchDomains` helper from `@taxa/taxonomy`, renders collapsed root
 * rows, and lazily loads children through `fetchChildren`. Pure
 * tree-state transitions go through the `tree-state.ts` helpers.
 *
 * ODD-NTP-002 — native source parity:
 *   - The legacy native tree exposes three independent source views
 *     (CoL / WoRMS / Freshwater) with a segmented control inside the
 *     tree surface. The React tree mirrors that contract: a compact
 *     selector renders inside the tree section, CoL starts active,
 *     WoRMS always appears, Freshwater appears only when the fetched
 *     root payload contains at least one row with a non-null
 *     `freshwater_id`.
 *   - Source filtering happens client-side against the already-fetched
 *     raw root response (FastAPI `/api/domains` currently ignores the
 *     `source` query parameter; ODD-NTP-001 documents the contract).
 *     The raw root cache survives a source switch so the user sees
 *     an instant roots re-display, not a refetch.
 *   - Child requests go through canonical
 *     `fetchChildren(id, { source: activeSource })` and apply the same
 *     `sourceMatches` predicate before attachment. Foreign rows from
 *     a previous source's hierarchy never enter the visible child
 *     list.
 *   - A source switch clears every source-bound piece of state
 *     (roots, child cache, expanded set, load status, showAll,
 *     per-row error) before re-displaying the new source's roots.
 *     The raw root cache SURVIVES the switch (the canonical fetch
 *     happens once on mount; `loadRoots` has no `activeSource`
 *     dependency so a source switch never issues a second
 *     `/api/domains` request). `nodes` also survives the reset (the
 *     projection carries every FastAPI field) so a later source
 *     switch can re-render cached rows without a re-fetch.
 *   - The selector does NOT introduce native selection/focus/detail
 *     state (that lands in ODD-NTP-005). It only adds the three
 *     source affordances plus the focused styling needed to mirror
 *     the native control's placement + active affordance.
 *
 * ODD-NTP-003 — native structural parity:
 *   - Each taxon renders as a real block row (not a `display: contents`
 *     grid placeholder) so the depth indent applies to the WHOLE
 *     identity + disclosure block. The native indent is 24px per
 *     depth level; the React port mirrors `TreeRow.ROW_INDENT_PX`
 *     byte-for-byte so the staircase stays in lock-step with the
 *     legacy `web/tree.js::renderNodeRow` oracle.
 *   - Loaded children are grouped by native rank tier
 *     (`groupChildrenByRank`) and rendered with native tier
 *     headers — one header per rank group with `count > 1`, sitting
 *     at depth+1, with a "Load N more" affordance that calls
 *     `toggleShowAll(state, parentId, rank)`. The PAGE_SIZE=5
 *     staircase matches the legacy `web/state.js::PAGE_SIZE` constant.
 *   - Source-specific auto-unroll: when `activeSource === "worms"` or
 *     `"freshwater"`, expanding a node adds `${parentId}::${rank}`
 *     to `showAll` for every child rank so the user sees the full
 *     subtree on a single click. CoL view keeps the PAGE_SIZE
 *     staircase. Mirrors `web/nav.js::toggleExpand`.
 *   - Native collapse-all control clears both the expanded set AND
 *     every `showAll` flag, returning the tree to a flat
 *     roots-only view. Mirrors `web/nav.js::collapseAll`.
 *   - Leaf disclosure: species / subspecies rows render with a `•`
 *     glyph (no chevron), are `disabled`, and stamp
 *     `data-action="select"` for the future ODD-NTP-005 selection
 *     handler. Higher ranks render with ▾/▸ and stamp
 *     `data-action="toggle-expand"`. Mirrors `web/tree.js::isLeaf`
 *     + the `chevronFor` / `data-action` contract.
 *
 * Base URL comes from `process.env.NEXT_PUBLIC_TAXA_API_ORIGIN`
 * (inlined at build time). The variable is unset for production
 * static exports — requests stay relative/same-origin so the future
 * FastAPI `out/` mount can serve `/api/domains` from the same origin.
 * Local development overrides the env var via `pnpm run dev:local`
 * (see `package.json`).
 *
 * Accessibility:
 *   - initial loading → `role="status"`
 *   - initial error → `role="alert"` with a "Retry" button
 *   - empty roots → quiet "No domains returned" copy
 *   - per-row child-load error → inline `role="alert"` with retry
 *   - source selector → `role="group"` with `aria-pressed` on each
 *     button (matches the legacy `web/nav.js::tree-source toggle`
 *     a11y contract)
 *   - tier header "Load N more" → `role="button"` with `aria-label`
 *     describing how many more rows will appear
 *   - collapse-all control → `disabled` + `aria-disabled` when no
 *     expansion exists; otherwise carries the
 *     `Collapse all expanded nodes` affordance label
 *
 * spec.md rule 4: presentation → taxonomy module. The recursive
 * row flattening lives here so the `.taxa-tree` block layout can
 * stack each row + its tier headers + its visible children as a
 * vertical sequence at the right depth.
 */
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  fetchChildren,
  fetchDomains,
} from "@taxa/taxonomy";
import type { TaxonomySource } from "@taxa/taxonomy";
import type { Rank, Taxon } from "../domain/taxon";
import {
  EMPTY_TREE_STATE,
  attachChildrenForSource,
  autoUnrollForSource,
  availableSourcesFor,
  childIds,
  clearExpansion,
  expandedTierCount,
  groupChildrenByRank,
  isExpanded,
  loadStatus,
  resetSourceState,
  setLoadStatus,
  setShowAll,
  sourceMatches,
  toggleExpand,
  withRootsForSource,
} from "./tree-state";
import type {
  NodeLoadStatus,
  RankGroup,
  TreeSource,
  TreeState,
} from "./tree-state";
import TreeRow from "./TreeRow";

type RootStatus = "idle" | "loading" | "loaded" | "error" | "empty";

interface RootState {
  readonly status: RootStatus;
  readonly message: string | null;
}

interface RawRoots {
  /** The canonical fetched root payload, unfiltered. Preserved across
   *  source switches so flipping between CoL / WoRMS / Freshwater does
   *  not refetch `/api/domains`. Mirrors the legacy
   *  `web/state.js::roots` cache shape. */
  readonly taxa: readonly Taxon[];
}

/** Inlined at build time by Next.js. Empty string keeps requests
 *  relative (same-origin) so the future FastAPI static mount can
 *  serve `/api/domains` from the same origin as `out/index.html`. */
const TAXA_API_ORIGIN: string =
  process.env.NEXT_PUBLIC_TAXA_API_ORIGIN ?? "";

const DEFAULT_SOURCE: TreeSource = "col";

function messageFor(err: unknown, prefix: string): string {
  const detail = err instanceof Error ? err.message : String(err);
  return `${prefix}: ${detail}`;
}

function rankPluralFor(rank: Rank): string {
  const irregular: Partial<Record<Rank, string>> = {
    phylum: "phyla",
    class: "classes",
    family: "families",
    genus: "genera",
    variety: "varieties",
    subphylum: "subphyla",
    subclass: "subclasses",
    subfamily: "subfamilies",
    subgenus: "subgenera",
    suborder: "suborders",
    subkingdom: "subkingdoms",
    subvariety: "subvarieties",
  };
  if (irregular[rank]) return irregular[rank]!;
  const label = rank.charAt(0).toUpperCase() + rank.slice(1);
  return `${label}s`;
}

export default function TaxonomyTree(): React.ReactElement {
  const [activeSource, setActiveSource] = useState<TreeSource>(DEFAULT_SOURCE);
  const [rawRoots, setRawRoots] = useState<RawRoots | null>(null);
  const [state, setState] = useState<TreeState>(EMPTY_TREE_STATE);
  const [root, setRoot] = useState<RootState>({
    status: "idle",
    message: null,
  });

  // `loadRoots` fetches `/api/domains` ONCE on mount. It deliberately
  // does NOT close over `activeSource` — the source filter is applied
  // by the `rawRoots + activeSource` effect below, which is the sole
  // source-filter application point. Closing over `activeSource` here
  // would put `loadRoots` in the effect's dep array and trigger a
  // second `/api/domains` round trip on every source switch.
  const loadRoots = useCallback(async () => {
    setRoot({ status: "loading", message: null });
    try {
      const taxa = await fetchDomains({ baseUrl: TAXA_API_ORIGIN });
      if (taxa.length === 0) {
        setRawRoots(null);
        setState(EMPTY_TREE_STATE);
        setRoot({ status: "empty", message: null });
      } else {
        // Store the unfiltered payload; the active-source effect
        // below projects it through `withRootsForSource` next.
        setRawRoots({ taxa });
        setRoot({ status: "loaded", message: null });
      }
    } catch (err) {
      setRoot({
        status: "error",
        message: messageFor(err, "Could not load taxonomy domains"),
      });
    }
  }, []);

  useEffect(() => {
    void loadRoots();
  }, [loadRoots]);

  /** Apply the active source to the raw root payload. Fires when
   *  (a) `rawRoots` first becomes non-null after a successful fetch,
   *  or (b) `activeSource` changes mid-session (the user clicked a
   *  different source button). Resetting `state` to
   *  `resetSourceState(prev)` (which clears expanded, child cache,
   *  load status, showAll, rootIds, preserves nodes) before
   *  re-applying the filter guarantees a clean source-bound state
   *  every time — same contract as the legacy
   *  `web/nav.js::tree-source toggle`. `rawRoots` itself is
   *  preserved across source switches (no refetch). */
  useEffect(() => {
    if (!rawRoots) return;
    setState((prev) =>
      withRootsForSource(resetSourceState(prev), rawRoots.taxa, activeSource),
    );
  }, [activeSource, rawRoots]);

  // Apply the active-source predicate BEFORE the visible child list
  // is built — foreign-source rows from the fetched payload (e.g.
  // WoRMS-only rows landing under a CoL parent's response, or vice
  // versa) never enter `childIdsByParent`. `attachChildrenForSource`
  // is the single entry point that combines
  // `filterChildrenForSource` + `attachChildren`.
  //
  // ODD-NTP-003: after a successful attach, if the parent is expanded
  // and the active source is WoRMS / Freshwater, run the
  // source-specific auto-unroll so a single expansion reveals the full
  // subtree (Biota → Animalia → phylum → class → ... → species). CoL
  // view keeps the PAGE_SIZE staircase to stay snappy. Mirrors the
  // legacy `web/nav.js::toggleExpand` predicate.
  const loadChildren = useCallback(
    async (id: number) => {
      setState((prev) => setLoadStatus(prev, id, "loading"));
      try {
        const kids = await fetchChildren(id, {
          baseUrl: TAXA_API_ORIGIN,
          source: activeSource as TaxonomySource,
        });
        setState((prev) => {
          const attached = attachChildrenForSource(
            prev, id, kids, activeSource,
          );
          if (isExpanded(attached, id) &&
              (activeSource === "worms" || activeSource === "freshwater")) {
            return autoUnrollForSource(attached, id, activeSource);
          }
          return attached;
        });
      } catch (err) {
        setState((s) => setLoadStatus(s, id, "error"));
        setRoot(() => ({
          status: "loaded",
          message: messageFor(err, `Could not load children of taxon ${id}`),
        }));
      }
    },
    [activeSource],
  );

  const handleToggle = useCallback(
    (id: number) => {
      const wasExpanded = isExpanded(state, id);
      const knownChildren = childIds(state, id);
      if (wasExpanded) {
        setState((prev) => {
          const collapsed = toggleExpand(prev, id);
          // Toggling a node closed should also clear its tier-level
          // showAll entries so a subsequent re-expand starts fresh
          // (otherwise the auto-unroll would re-fire and the user
          // would see every WoRMS / Freshwater tier expanded
          // again on a single click). Mirrors the legacy
          // `collapseAll` semantic at the per-node level.
          return collapseNodeTiers(collapsed, id);
        });
      } else {
        setState((prev) => toggleExpand(prev, id));
        if (knownChildren.length === 0) {
          void loadChildren(id);
        } else {
          // Children already cached — apply auto-unroll synchronously
          // so the WoRMS / Freshwater view reveals its full subtree
          // without waiting for the next render cycle to refresh.
          setState((prev) => autoUnrollForSource(prev, id, activeSource));
        }
      }
    },
    [state, activeSource, loadChildren],
  );

  const handleRetryChild = useCallback(
    (id: number) => {
      void loadChildren(id);
    },
    [loadChildren],
  );

  const handleSourceChange = useCallback((next: TreeSource) => {
    if (next === activeSource) return;
    // Mirrors the legacy `web/nav.js::tree-source toggle` reset:
    // clear every source-bound React state (root ids, child cache,
    // expanded set, load status, showAll, per-row error) so the
    // next effect re-applies `withRootsForSource` against a blank
    // slate. The raw root cache SURVIVES the switch — `loadRoots`
    // already ran once on mount, and `setActiveSource(next)`
    // triggers the `rawRoots + activeSource` effect to re-project
    // the cached payload without a second `/api/domains` round
    // trip. `nodes` is also preserved by `resetSourceState` so
    // cached rows are reachable on the next switch without a
    // refetch.
    setState((prev) => resetSourceState(prev));
    setRoot((prev) => ({ status: prev.status, message: null }));
    setActiveSource(next);
  }, [activeSource]);

  const handleLoadMore = useCallback(
    (parentId: number, rank: Rank) => {
      setState((prev) => setShowAll(prev, parentId, rank, true));
    },
    [],
  );

  const handleCollapseAll = useCallback(() => {
    setState((prev) => clearExpansion(prev));
  }, []);

  /** Source selector metadata. Recomputed only when the raw root
   *  payload changes — the `useMemo` keeps the segmented control
   *  static across the per-row state churn. Freshwater appears
   *  only when `hasFreshwaterRoot(rawRoots.taxa)` is true. */
  const availableSources = useMemo<readonly TreeSource[]>(() => {
    if (!rawRoots) return ["col", "worms"];
    return availableSourcesFor(rawRoots.taxa);
  }, [rawRoots]);

  /** Collapse-all affordance state. The button is `disabled` when
   *  no expansion exists, mirroring the legacy
   *  `web/nav.js::renderCollapseAllButton` opacity/cursor heuristic
   *  so the visual affordance matches the legacy oracle on all
   *  three sources. */
  const collapseAllEnabled = expandedTierCount(state) > 0;

  const renderSourceSelector = (): ReactNode => {
    const selectorLabel = "Tree data source";
    return (
      <div
        className="tree-source-toggle"
        role="group"
        aria-label={selectorLabel}
        data-tree-source-toggle=""
        data-active-source={activeSource}
        style={{ gridColumn: "1 / -1" }}
      >
        {availableSources.map((src) => {
          const active = src === activeSource;
          const label =
            src === "col" ? "CoL" : src === "worms" ? "WoRMS" : "Freshwater";
          return (
            <button
              key={src}
              type="button"
              className={`tree-source-btn${active ? " active" : ""}`}
              data-tree-source={src}
              aria-pressed={active ? "true" : "false"}
              onClick={() => handleSourceChange(src)}
            >
              {label}
            </button>
          );
        })}
      </div>
    );
  };

  /** ODD-NTP-003 — native collapse-all control. Mirrors the legacy
   *  `#collapse-all` button's contract: clears both the expanded
   *  set and every `showAll` flag so the tree returns to a flat
   *  roots-only view. Disabled when no expansion exists. The
   *  visual treatment (`opacity-40 disabled:cursor-not-allowed`)
   *  mirrors the legacy cascade. */
  const renderCollapseAllInline = (): ReactNode => (
    <div
      className="tree-collapse-all"
      data-collapse-all=""
    >
      <button
        id="collapse-all"
        type="button"
        className={`collapse-all-btn flex items-center gap-1 text-body-sm px-3 py-1.5 rounded-lg border border-outline-variant bg-surface transition-colors ${
          collapseAllEnabled
            ? "text-on-surface hover:bg-surface-container-low"
            : "opacity-40 cursor-not-allowed"
        }`}
        onClick={handleCollapseAll}
        disabled={!collapseAllEnabled}
        aria-disabled={!collapseAllEnabled}
        title="Collapse all expanded nodes"
        data-action="collapse-all"
      >
        <span aria-hidden="true" className="text-[18px] select-none">⊟</span>
        <span>Collapse all</span>
      </button>
    </div>
  );

  /** ODD-NTP-003 — per-row status affordance. Mirrors the TreeRow
   *  disclosure's loading + error affordances so the layout stays
   *  deterministic (the row stays focused on its own disclosure
   *  contract; loading + error states render as indented
   *  siblings). The indent uses `depth * 24 + 16` to match the
   *  TreeRow block-layout contract. */
  const renderRowStatus = (
    tree: TreeState,
    id: number,
    depth: number,
  ): ReactNode => {
    const status: NodeLoadStatus = loadStatus(tree, id);
    const taxon = tree.nodes.get(id);
    if (!taxon) return null;
    const paddingLeft = 16 + (depth + 1) * 24;
    if (status === "loading") {
      return (
        <p
          role="status"
          className="px-4 py-2 text-sm text-on-surface-variant"
          style={{ paddingLeft: `${paddingLeft}px` }}
          data-row-status="loading"
          data-row-status-for={id}
        >
          Loading children…
        </p>
      );
    }
    if (status === "error") {
      return (
        <div
          role="alert"
          className="flex items-center gap-3 px-4 py-2 text-sm"
          style={{ paddingLeft: `${paddingLeft}px` }}
          data-row-status="error"
          data-row-status-for={id}
        >
          <span className="text-on-surface">Could not load children.</span>
          <button
            type="button"
            className="rounded-md border border-outline-variant bg-surface px-2 py-1 text-xs font-medium text-on-surface hover:bg-surface-container-low"
            onClick={() => handleRetryChild(id)}
          >
            Retry
          </button>
        </div>
      );
    }
    return null;
  };

  /** ODD-NTP-003 — native tier header. Sits at `depth+1` so it
   *  shares the same indent as its children, mirroring the legacy
   *  `web/tree.js::renderTierHeader` cascade byte-for-byte. The
   *  "Load N more" affordance calls `handleLoadMore` which marks
   *  the tier's `${parentId}::${rank}` key in `showAll` — the
   *  subsequent render expands every child of that rank group. */
  const renderTierHeader = (
    parentId: number,
    group: RankGroup,
    depth: number,
  ): ReactNode | null => {
    if (group.count <= 1) return null;
    const indentPx = (depth + 1) * 24;
    return (
      <div
        className="tier-header"
        data-tier-header=""
        data-tier-parent={parentId}
        data-tier-rank={group.rank}
        data-tier-count={group.count}
        style={{ marginLeft: `${indentPx}px` }}
      >
        <h2 className="flex items-center gap-2 font-semibold text-base text-on-surface tracking-wide">
          <span aria-hidden="true" className="text-[20px] text-on-surface-variant">▾</span>
          {rankPluralFor(group.rank)} ({group.count})
        </h2>
        {group.remaining > 0 ? (
          <button
            type="button"
            className="load-all"
            data-action="load-all"
            data-parent-id={parentId}
            data-rank={group.rank}
            data-remaining={group.remaining}
            onClick={() => handleLoadMore(parentId, group.rank)}
            aria-label={`Load ${group.remaining} more ${rankPluralFor(group.rank)}`}
          >
            Load {group.remaining} more
          </button>
        ) : null}
      </div>
    );
  };

  /** ODD-NTP-003 — recursive native tree renderer. Walks the
   *  `(parentId, depth)` axis; for each taxon it renders the row
   *  block, then (if expanded) the tier groups for the parent's
   *  cached children. Tier headers sit at depth+1; their visible
   *  children sit at depth+1 and recurse into their own tier
   *  groups at depth+2. Per-row loading + error affordances
   *  render after the row at the same depth so the user always
   *  sees the disclosure state immediately under the row. */
  const renderRows = (
    tree: TreeState,
    parentId: number | null,
    depth: number,
  ): ReactNode => {
    const ids =
      parentId === null
        ? tree.rootIds
        : (tree.childIdsByParent.get(parentId) ?? []);
    const items: ReactNode[] = [];
    for (const id of ids) {
      const taxon = tree.nodes.get(id);
      if (!taxon) continue;
      const expanded = isExpanded(tree, id);
      const status: NodeLoadStatus = loadStatus(tree, id);
      items.push(
        <Fragment key={id}>
          <TreeRow
            taxon={taxon}
            depth={depth}
            state={tree}
            onToggle={handleToggle}
          />
          {expanded && status === "loading" ? renderRowStatus(tree, id, depth) : null}
          {expanded && status === "error" ? renderRowStatus(tree, id, depth) : null}
          {expanded ? renderTiers(tree, id, depth) : null}
        </Fragment>,
      );
    }
    return <>{items}</>;
  };

  /** ODD-NTP-003 — tier-group renderer. Replaces the previous
   *  flat-sibling recursion with a grouped view: one tier
   *  header per `count > 1` rank group, then the visible children
   *  for that group (each recursing into its own tier groups).
   *  Source filtering + PAGE_SIZE staircase + showAll are all
   *  applied inside `groupChildrenByRank`, so this view is a
   *  pure projection. */
  const renderTiers = (
    tree: TreeState,
    parentId: number,
    depth: number,
  ): ReactNode => {
    const groups = groupChildrenByRank(tree, parentId, activeSource);
    if (groups.length === 0) return null;
    const items: ReactNode[] = [];
    for (const group of groups) {
      const header = renderTierHeader(parentId, group, depth);
      if (header) items.push(header);
      for (const childId of group.visibleIds) {
        const child = tree.nodes.get(childId);
        if (!child) continue;
        const expanded = isExpanded(tree, childId);
        const status: NodeLoadStatus = loadStatus(tree, childId);
        items.push(
          <Fragment key={childId}>
            <TreeRow
              taxon={child}
              depth={depth + 1}
              state={tree}
              onToggle={handleToggle}
            />
            {expanded && status === "loading" ? renderRowStatus(tree, childId, depth + 1) : null}
            {expanded && status === "error" ? renderRowStatus(tree, childId, depth + 1) : null}
            {expanded ? renderTiers(tree, childId, depth + 1) : null}
          </Fragment>,
        );
      }
    }
    return <>{items}</>;
  };

  return (
    <section aria-label="Taxonomic tree" className="taxa-tree">
      {(root.status === "idle" || root.status === "loading") && (
        <p
          role="status"
          className="px-2 py-6 text-center text-on-surface-variant"
          style={{ gridColumn: "1 / -1" }}
        >
          Loading domains…
        </p>
      )}
      {root.status === "error" && (
        <div
          role="alert"
          className="flex flex-col items-center gap-3 px-2 py-6"
          style={{ gridColumn: "1 / -1" }}
        >
          <p className="text-on-surface">Could not load taxonomy domains.</p>
          {root.message && (
            <p className="text-sm text-on-surface-variant">{root.message}</p>
          )}
          <button
            type="button"
            className="rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-sm font-medium text-on-surface hover:bg-surface-container-low"
            onClick={() => void loadRoots()}
          >
            Retry
          </button>
        </div>
      )}
      {root.status === "empty" && (
        <p
          role="status"
          className="px-2 py-6 text-center text-on-surface-variant"
          style={{ gridColumn: "1 / -1" }}
        >
          No taxonomy domains returned by the API.
        </p>
      )}
      {(root.status === "loaded" || root.status === "idle") &&
        state.rootIds.length > 0 && (
          <>
            <div className="tree-source-toggle-wrapper">
              {renderSourceSelector()}
              {renderCollapseAllInline()}
            </div>
            {renderRows(state, null, 0)}
          </>
        )}
      {root.status === "loaded" && root.message && (
        <p
          role="alert"
          className="mt-2 rounded-md border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface-variant"
          style={{ gridColumn: "1 / -1" }}
        >
          {root.message}
        </p>
      )}
    </section>
  );
}

/** ODD-NTP-003 — clear the showAll entries keyed to a collapsing
 *  node so a later re-expand starts from the PAGE_SIZE staircase.
 *  Mirrors the legacy `web/nav.js::collapseAll` semantics scoped
 *  to one node (the legacy code did this globally; the React
 *  per-node toggle is a stricter contract because WoRMS /
 *  Freshwater auto-unroll would otherwise re-fire on the next
 *  expand). */
function collapseNodeTiers(state: TreeState, parentId: number): TreeState {
  const prefix = `${parentId}::`;
  let next: Set<string> = new Set(state.showAll);
  let mutated = next.size !== state.showAll.size;
  if (!mutated) {
    for (const key of state.showAll) {
      if (key.startsWith(prefix)) {
        mutated = true;
        break;
      }
    }
  }
  if (!mutated) return state;
  // Reset to a fresh mutable copy before applying the deletes
  // (state.showAll is ReadonlySet<string>; the Set constructor
  // accepts it for an immutable initial copy, then `delete` is
  // callable on the mutable `Set<string>` local).
  if (next.size !== state.showAll.size) {
    next = new Set(state.showAll);
  }
  for (const key of state.showAll) {
    if (key.startsWith(prefix)) {
      next.delete(key);
    }
  }
  return { ...state, showAll: next };
}

// Re-export `sourceMatches` so consumers using the React tree can
// compose the same predicate without a deep import. The barrel
// (index.ts) is the public API; this internal re-export just keeps
// the source-affordance slot in `TreeRow` free to filter rows in a
// later PR (ODD-NTP-004).
export { sourceMatches };