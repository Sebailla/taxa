"use client";

/**
 * Explorer — top-level client island for the Browser-tab file
 * explorer (ODD-MIGRATE-003 / W6.1).
 *
 * Client component (boundary declared at the top of the file).
 * Owns the lifecycle of the typed ExplorerState shape
 * (`tree-load status`, `expanded set`, `selected path`,
 * `open file`, `viewer tab`). Renders the recursive `FileTree`
 * on the left and the `Viewer` on the right. The two
 * children are pure projections: Explorer wires their
 * callbacks + props, FileTree + Viewer emit JSX.
 *
 * W6.1 contract:
 *  - Initial tree load/retry/empty/error (the mount fires
 *    `fetchFiles` on first render, paints a quiet skeleton
 *    while loading, surfaces a `role="alert"` retry card on
 *    failure, paints the empty-state card on `exists: false`).
 *  - Typed state and tab behavior (the active-tab state is
 *    owned at the Explorer level and threaded into the Viewer
 *    via props; the Viewer's tab buttons dispatch back through
 *    `onTabChange`).
 *  - No search, no splitter, no materialization, no browser-
 *    state expansion, no legacy mutation, no cutover.
 *
 * Architectural note — the parent Server Component
 * (`src/app/explorer/page.tsx`) cannot pass repository
 * functions to a Client Component (a Server Component can only
 * pass serializable props across the boundary). The Explorer
 * client island therefore constructs/uses the W3 adapter
 * through the public `@taxa/research` barrel with the same-
 * origin base URL the parent Server Component passes through
 * the `apiOrigin` prop. The test harness injects a custom
 * `fetch` through the same `apiOrigin` + `fetchFiles` barrel
 * surface so the mount can be exercised in isolation.
 *
 * spec.md rule 4: presentation depends on the public barrel +
 * domain. Every import is anchored at `@taxa/research`.
 */

import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  ExplorerErrorBoundary,
  FileTree,
  Viewer,
  fetchFiles,
  createInitialViewerState,
  toggleExpansion,
  castFileFormat,
  type ExplorerLoadStatus,
  type ViewerState,
  type ExplorerFileNode,
  type ExplorerTree,
  type ViewerTab,
} from "@taxa/research";

/** Props for the Explorer client island. The parent Server
 *  Component (`src/app/explorer/page.tsx`) passes only the
 *  serializable `apiOrigin` string — a Server Component
 *  cannot pass repository functions to a Client Component,
 *  so the W3 adapter is constructed here through the public
 *  barrel with the same-origin base URL. Tests inject a
 *  custom `fetch` through the same barrel surface inside
 *  client/test boundaries only (per the W6.1 contract). */
export interface ExplorerProps {
  readonly apiOrigin: string;
}

/** Public top-level Explorer component. Renders the two-pane
 *  layout (recursive tree on the left, viewer on the right)
 *  inside a typed error boundary. The state + lifecycle
 *  ownership lives at this level so the children stay pure
 *  projections. */
export default function Explorer(props: ExplorerProps): ReactNode {
  const { apiOrigin } = props;
  // The typed load status (idle / loading / loaded / empty /
  // error) drives the left-pane render branch. The status
  // carries the wire `tree` payload verbatim when the request
  // succeeds, so the typed surface flows through the mount
  // without coercion.
  const [loadStatus, setLoadStatus] = useState<ExplorerLoadStatus>(
    { kind: "idle" },
  );
  // The expanded-folders set (mirrors the legacy `expanded`
  // Set). Initial state is empty — folders start collapsed in
  // the W6.1 mount (the legacy default-everything-expanded
  // shape is deferred to a future UX slice per the W6.1
  // contract). The `useState` initialiser is a fresh Set per
  // mount, never a shared reference.
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  // The selected path drives the file-row highlighting +
  // the right-pane viewer mount. `null` = no file selected.
  // The selected path is set on single-click (`selectFile`)
  // AND on double-click (`openFile`); double-click is a
  // superset of single-click (mirrors the legacy
  // `selectFile` → `openFile` ordering).
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  // The viewer state owns the active tab + the open file
  // shape. The mount keeps the typed view-model here so the
  // Viewer's bytes-fetch lifecycle + the typed dispatch
  // transition live in one place.
  const [viewerState, setViewerState] = useState<ViewerState>(
    createInitialViewerState,
  );

  /** Memoised tree loader. Fires `fetchFiles` through the
   *  public barrel with the same-origin base URL. The mount
   *  invokes this on first render (via the effect below) and
   *  on every retry click. The callback is stable across
   *  renders (`useCallback` with `[apiOrigin]` deps) so the
   *  effect's identity stays stable. */
  const loadTree = useCallback(async (): Promise<void> => {
    setLoadStatus({ kind: "loading" });
    try {
      const tree = await fetchFiles({ baseUrl: apiOrigin });
      // The wire payload's `exists` flag drives the
      // empty-state branch. Mirrors the FastAPI contract
      // (200 with `{ exists: false, root: null,
      // filesystem_path }` when the research root is
      // missing). The W1 `ExplorerTree` typed shape carries
      // the flag verbatim.
      if (!tree.exists) {
        setLoadStatus({ kind: "empty", tree });
        return;
      }
      setLoadStatus({ kind: "loaded", tree });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setLoadStatus({ kind: "error", message });
    }
  }, [apiOrigin]);

  // First-render effect — fires the initial tree fetch.
  // The dependency is `loadTree` (the stable callback) so
  // the effect runs once per mount + once per `apiOrigin`
  // change (a future Server Component that passed a
  // different origin would re-fetch). The cleanup is a
  // no-op (the fetch is in-flight cancellation is handled
  // by the AbortController inside `fetchFiles` when the
  // caller passes one — the W6.1 mount does not thread an
  // AbortController because the mount's lifetime matches
  // the route's lifetime).
  useEffect(() => {
    void loadTree();
  }, [loadTree]);

  /** Memoised folder toggle. The set transition goes through
   *  the pure `toggleExpansion` helper from the typed state
   *  kernel so React's render cycle stays deterministic. */
  const handleToggleExpand = useCallback((folderPath: string): void => {
    setExpanded((prev) => toggleExpansion(prev, folderPath));
  }, []);

  /** Memoised file select. Mirrors the legacy
   *  `web/file_explorer.js::selectFile` shape: single-click
   *  sets the selected path + highlights the row. The
   *  viewer-side state is NOT changed here (the legacy
   *  spec: single-click = highlight only; double-click =
   *  open). */
  const handleSelectFile = useCallback((file: ExplorerFileNode): void => {
    setSelectedPath(file.path);
  }, []);

  /** Memoised file open. Mirrors the legacy
   *  `web/file_explorer.js::openFile` shape: double-click
   *  updates the viewer-side `openFilePath` +
   *  `openFileFormat` and triggers the right-pane render.
   *  The viewer tab stays at its current value (the legacy
   *  default is "Raw"). */
  const handleOpenFile = useCallback((file: ExplorerFileNode): void => {
    setSelectedPath(file.path);
    setViewerState((prev) => ({
      ...prev,
      openFilePath: file.path,
      openFileFormat: castFileFormat(file.extension),
    }));
  }, []);

  /** Memoised tab change. The tab is owned at the Explorer
   *  level so the Viewer's tab buttons dispatch back through
   *  `onTabChange`. The viewer-state's `dispatch` field is
   *  reset to `null` so the Viewer recomputes on the next
   *  render (the `dispatch` is a derived value, not a
   *  stored one — re-running `dispatchViewer` on the next
   *  render is the canonical pattern). */
  const handleTabChange = useCallback((tab: ViewerTab): void => {
    setViewerState((prev) => ({ ...prev, tab, dispatch: null }));
  }, []);

  // Render the left pane based on the load status. The
  // status map is 1:1 with the discriminated union's
  // branches — every branch returns the same typed JSX
  // shape so React's reconciliation stays simple.
  const renderTreePane = (): ReactNode => {
    switch (loadStatus.kind) {
      case "idle":
      case "loading":
        return (
          <div className="fex-empty-state" role="status" data-tree-loading="">
            <span className="fex-empty-state-icon material-symbols-outlined animate-spin">
              progress_activity
            </span>
            <p>Loading…</p>
          </div>
        );
      case "empty":
        return renderEmptyPane(loadStatus.tree);
      case "error":
        return renderErrorPane(loadStatus.message);
      case "loaded":
        return (
          <FileTree
            tree={loadStatus.tree}
            expanded={expanded}
            selectedPath={selectedPath}
            onToggleExpand={handleToggleExpand}
            onSelectFile={handleSelectFile}
            onOpenFile={handleOpenFile}
          />
        );
    }
  };

  return (
    <ExplorerErrorBoundary>
      <div className="fex-shell flex flex-row gap-0" data-explorer-root="">
        <div className="fex-tree-pane flex flex-col" data-explorer-tree-pane="">
          <div className="fex-tree-header">
            <h2>Research</h2>
          </div>
          {renderTreePane()}
        </div>
        <div className="fex-viewer-pane flex-1" data-explorer-viewer-pane="">
          <Viewer
            apiOrigin={apiOrigin}
            openFilePath={viewerState.openFilePath}
            openFileFormat={viewerState.openFileFormat}
            tab={viewerState.tab}
            onTabChange={handleTabChange}
          />
        </div>
      </div>
    </ExplorerErrorBoundary>
  );
}

/** Render the empty-state card when the server returns
 *  `exists: false`. Mirrors the legacy
 *  `web/file_explorer.js::renderTreePaneEmpty` shape — same
 *  Material Symbols icon + copy ("No research folders yet —
 *  materialize a taxon to populate the tree."). */
function renderEmptyPane(tree: ExplorerTree): ReactNode {
  return (
    <div className="fex-empty-state" role="status" data-tree-empty="">
      <span className="fex-empty-state-icon material-symbols-outlined">
        folder_off
      </span>
      <p>No research folders yet — materialize a taxon to populate the tree.</p>
      <p className="text-on-surface-variant text-body-sm">
        {tree.filesystem_path || ""}
      </p>
    </div>
  );
}

/** Render the error-state card with a Retry button. Mirrors
 *  the legacy `web/file_explorer.js::mount()` catch branch —
 *  the `role="alert"` + Retry button. The retry callback
 *  re-fires the loader through the parent's effect chain;
 *  a future slice could thread the loader through a context
 *  provider so this retry button can call it directly. The
 *  W6.1 non-CDN scope keeps the retry shape simple — a
 *  page reload restores the mount from a clean state. */
function renderErrorPane(message: string): ReactNode {
  const handleRetry = (): void => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
    void message;
  };
  return (
    <div className="fex-empty-state" role="alert" data-tree-error="">
      <span className="fex-empty-state-icon material-symbols-outlined">
        error
      </span>
      <p className="font-semibold text-on-surface">
        Could not load file tree
      </p>
      <p className="text-on-surface-variant text-body-sm">{message}</p>
      <button
        type="button"
        className="fex-snippet-btn mt-2"
        onClick={handleRetry}
        aria-label="Retry loading the file tree"
      >
        Retry
      </button>
    </div>
  );
}
