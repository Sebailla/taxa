"use client";

/**
 * TaxonomyTree — visible taxonomy tree (ODD-VTREE-002).
 *
 * Client island. Fetches root domains on mount through the canonical
 * `fetchDomains` helper from `@taxa/taxonomy`, renders collapsed root
 * rows, and lazily loads children through `fetchChildren`. Pure
 * tree-state transitions go through the `tree-state.ts` helpers.
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
 *
 * spec.md rule 4: presentation → taxonomy module. The recursive
 * row flattening lives here so the `.taxa-tree` CSS grid can
 * auto-flow each row's four cells as direct grid items
 * (the `.tree-row { display: contents }` cascade).
 */
import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  fetchChildren,
  fetchDomains,
} from "@taxa/taxonomy";
import {
  EMPTY_TREE_STATE,
  attachChildren,
  childIds,
  isExpanded,
  loadStatus,
  setLoadStatus,
  toggleExpand,
  withRoots,
} from "./tree-state";
import type { NodeLoadStatus, TreeState } from "./tree-state";
import TreeRow from "./TreeRow";

type RootStatus = "idle" | "loading" | "loaded" | "error" | "empty";

interface RootState {
  readonly status: RootStatus;
  readonly message: string | null;
}

/** Inlined at build time by Next.js. Empty string keeps requests
 *  relative (same-origin) so the future FastAPI static mount can
 *  serve `/api/domains` from the same origin as `out/index.html`. */
const TAXA_API_ORIGIN: string =
  process.env.NEXT_PUBLIC_TAXA_API_ORIGIN ?? "";

function messageFor(err: unknown, prefix: string): string {
  const detail = err instanceof Error ? err.message : String(err);
  return `${prefix}: ${detail}`;
}

export default function TaxonomyTree(): React.ReactElement {
  const [state, setState] = useState<TreeState>(EMPTY_TREE_STATE);
  const [root, setRoot] = useState<RootState>({
    status: "idle",
    message: null,
  });

  const loadRoots = useCallback(async () => {
    setRoot({ status: "loading", message: null });
    try {
      const roots = await fetchDomains({ baseUrl: TAXA_API_ORIGIN });
      if (roots.length === 0) {
        setState(EMPTY_TREE_STATE);
        setRoot({ status: "empty", message: null });
      } else {
        setState((prev) => withRoots(prev, roots));
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

  const loadChildren = useCallback(async (id: number) => {
    setState((prev) => setLoadStatus(prev, id, "loading"));
    try {
      const kids = await fetchChildren(id, { baseUrl: TAXA_API_ORIGIN });
      setState((prev) => attachChildren(prev, id, kids));
    } catch (err) {
      setState((s) => setLoadStatus(s, id, "error"));
      setRoot(() => ({
        status: "loaded",
        message: messageFor(err, `Could not load children of taxon ${id}`),
      }));
    }
  }, []);

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
      {root.status === "loaded" && state.rootIds.length === 0 && (
        <p
          role="status"
          className="px-2 py-6 text-center text-on-surface-variant"
          style={{ gridColumn: "1 / -1" }}
        >
          No taxonomy domains returned by the API.
        </p>
      )}
      {(root.status === "loaded" || root.status === "idle") &&
        state.rootIds.length > 0 &&
        renderRows(state, null, 0)}
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