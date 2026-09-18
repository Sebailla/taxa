"use client";

/**
 * TaxonomyTree — visible taxonomy tree (ODD-VTREE-002 / ODD-NTP-002).
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
 *     (roots, child cache, expanded set, load status, per-row error)
 *     before re-displaying the new source's roots. The raw root
 *     cache SURVIVES the switch (the canonical fetch happens once
 *     on mount; `loadRoots` has no `activeSource` dependency so a
 *     source switch never issues a second `/api/domains` request).
 *     `nodes` also survives the reset (the projection carries every
 *     FastAPI field) so a later source switch can re-render cached
 *     rows without a re-fetch.
 *   - The selector does NOT introduce native selection/focus/detail
 *     state (that lands in ODD-NTP-005). It only adds the three
 *     source affordances plus the focused styling needed to mirror
 *     the native control's placement + active affordance.
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
 *
 * spec.md rule 4: presentation → taxonomy module. The recursive
 * row flattening lives here so the `.taxa-tree` CSS grid can
 * auto-flow each row's four cells as direct grid items
 * (the `.tree-row { display: contents }` cascade).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  fetchChildren,
  fetchDomains,
} from "@taxa/taxonomy";
import type { TaxonomySource } from "@taxa/taxonomy";
import {
  EMPTY_TREE_STATE,
  attachChildrenForSource,
  availableSourcesFor,
  childIds,
  isExpanded,
  loadStatus,
  resetSourceState,
  setLoadStatus,
  sourceMatches,
  toggleExpand,
  withRootsForSource,
} from "./tree-state";
import type {
  NodeLoadStatus,
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
  readonly taxa: readonly import("../domain/taxon").Taxon[];
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
   *  different source button). Resetting `state` to `EMPTY_TREE_STATE`
   *  before re-applying the filter guarantees a clean source-bound
   *  state every time — same contract as the legacy
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
  const loadChildren = useCallback(
    async (id: number) => {
      setState((prev) => setLoadStatus(prev, id, "loading"));
      try {
        const kids = await fetchChildren(id, {
          baseUrl: TAXA_API_ORIGIN,
          source: activeSource as TaxonomySource,
        });
        setState((prev) =>
          attachChildrenForSource(prev, id, kids, activeSource),
        );
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
      setState((prev) => toggleExpand(prev, id));
      if (!wasExpanded && knownChildren.length === 0) {
        void loadChildren(id);
      }
    },
    [state, loadChildren],
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
    // expanded set, load status, per-row error) so the next effect
    // re-applies `withRootsForSource` against a blank slate. The
    // raw root cache SURVIVES the switch — `loadRoots` already ran
    // once on mount, and `setActiveSource(next)` triggers the
    // `rawRoots + activeSource` effect to re-project the cached
    // payload without a second `/api/domains` round trip. `nodes`
    // is also preserved by `resetSourceState` so cached rows are
    // reachable on the next switch without a refetch.
    setState((prev) => resetSourceState(prev));
    setRoot((prev) => ({ status: prev.status, message: null }));
    setActiveSource(next);
  }, [activeSource]);

  /** Source selector metadata. Recomputed only when the raw root
   *  payload changes — the `useMemo` keeps the segmented control
   *  static across the per-row state churn. Freshwater appears
   *  only when `hasFreshwaterRoot(rawRoots.taxa)` is true. */
  const availableSources = useMemo<readonly TreeSource[]>(() => {
    if (!rawRoots) return ["col", "worms"];
    return availableSourcesFor(rawRoots.taxa);
  }, [rawRoots]);

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

  /** Per-row status affordance. Mirrors the TreeRow disclosure's
   *  loading + error affordances so the CSS grid layout stays
   *  deterministic. Rendered as flat siblings of the row by the
   *  parent `.taxa-tree` grid (see `renderRows`). */
  const renderRowStatus = (
    tree: TreeState,
    id: number,
    depth: number,
  ): ReactNode => {
    const status: NodeLoadStatus = loadStatus(tree, id);
    const taxon = tree.nodes.get(id);
    if (!taxon) return null;
    const indent = `calc(${depth * 1.25}rem + 1rem)`;
    if (status === "loading") {
      return (
        <p
          role="status"
          className="px-2 py-2 text-sm text-on-surface-variant"
          style={{ gridColumn: "1 / -1", paddingLeft: indent }}
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
          className="flex items-center gap-3 px-2 py-2 text-sm"
          style={{ gridColumn: "1 / -1", paddingLeft: indent }}
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

  const renderRows = (
    tree: TreeState,
    parentId: number | null,
    depth: number,
  ): ReactNode => {
    const ids = parentId === null ? tree.rootIds : childIds(tree, parentId);
    return ids.map((id) => {
      const taxon = tree.nodes.get(id);
      if (!taxon) return null;
      const expanded = isExpanded(tree, id);
      const status: NodeLoadStatus = loadStatus(tree, id);
      return (
        <div key={id} className="contents">
          <TreeRow
            taxon={taxon}
            depth={depth}
            state={tree}
            onToggle={handleToggle}
          />
          {expanded && status === "loading" ? renderRowStatus(tree, id, depth) : null}
          {expanded && status === "error" ? renderRowStatus(tree, id, depth) : null}
          {expanded ? renderRows(tree, id, depth + 1) : null}
        </div>
      );
    });
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
            {renderSourceSelector()}
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

// Re-export `sourceMatches` so consumers using the React tree can
// compose the same predicate without a deep import. The barrel
// (index.ts) is the public API; this internal re-export just keeps
// the source-affordance slot in `TreeRow` free to filter rows in a
// later PR (ODD-NTP-004).
export { sourceMatches };