"use client";

/**
 * Explorer — top-level client island for the Browser-tab file
 * explorer (ODD-MIGRATE-003 / W6.1 + W6.2).
 *
 * Client component (boundary declared at the top of the file).
 * Owns the lifecycle of the typed ExplorerState shape
 * (`tree-load status`, `expanded set`, `selected path`,
 * `open file`, `viewer tab`, `search query / mode / hide-empty`).
 * Renders the recursive `FileTree` on the left and the
 * `Viewer` on the right. The two children are pure
 * projections: Explorer wires their callbacks + props,
 * FileTree + Viewer emit JSX.
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
 *  - No splitter, no materialization, no browser-state
 *    expansion, no legacy mutation, no cutover.
 *
 * W6.2 contract (Browser-tab tree search, mirrors the
 * legacy `web/file_explorer.js` byte-for-byte):
 *  - 200 ms debounce on the input event (the legacy
 *    `setTimeout(..., 200)` pattern preserved verbatim).
 *  - Case-insensitive substring match on `name` OR `path`.
 *    Computation goes through the pure kernel helper
 *    `annotateMatches(root, query)` so the React layer
 *    never re-implements the recursive walker.
 *  - Filter mode (default): hide non-matches + auto-expand
 *    every ancestor folder. The legacy `render-time
 *    toggle, not re-mount` strategy is preserved — the
 *    React tree itself never re-renders on a keystroke;
 *    a `useEffect` in `FileTree` applies the DOM mutations
 *    keyed on the typed annotation.
 *  - Highlight mode: paint `search-match` on matching rows
 *    without touching expansion. The legacy `Highlight mode
 *    keeps expand/collapse state` contract is preserved
 *    verbatim — `aria-expanded`, the chevron glyph, and
 *    `.fex-children` display are NEVER touched in highlight
 *    mode.
 *  - Clear (button or Escape key) restores the tree
 *    verbatim — un-hides every wrap, removes every
 *    `.search-match` class, clears the `No matches.`
 *    placeholder.
 *  - `filter + hideEmpty + zero matches` paints the EXACT
 *    `No matches.` card inside the tree pane (the
 *    `.fex-search-empty` chrome reuses the existing
 *    `.fex-empty-state` shape with the `search_off`
 *    Material Symbols icon).
 *  - Conditional auto-focus: on every mount, the search
 *    input is focused via `requestAnimationFrame` ONLY
 *    when `document.activeElement === document.body` —
 *    the legacy's IME-safe focus check preserved verbatim
 *    so a mid-composition user never has their keystroke
 *    stolen.
 *  - Mode toggle swaps the icon + `aria-pressed` and
 *    re-applies the current query so the user sees the
 *    mode switch instantly.
 *  - Hide-empty toggle updates state + re-applies the
 *    filter pass (no-op in highlight mode).
 *  - Search is client-side against the loaded
 *    `ExplorerTree` only — no new port, no new adapter,
 *    no new dependency.
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

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  ExplorerErrorBoundary,
  FileTree,
  Viewer,
  fetchFiles,
  createInitialViewerState,
  toggleExpansion,
  castFileFormat,
  annotateMatches,
  type ExplorerLoadStatus,
  type ViewerState,
  type ExplorerFileNode,
  type ExplorerTree,
  type ViewerTab,
  type SearchAnnotation,
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
  // ---- W6.2 search state ----
  // The active query (live, pre-debounce). The
  // `useState` initialiser is `""` so the very first render
  // paints no annotation. The 200 ms debounced value lives
  // in `debouncedQuery` (see the effect below) — the
  // debounced value drives the annotation computation so a
  // fast-typing user only triggers one `annotateMatches`
  // call after they stop typing. Mirrors the legacy
  // `web/file_explorer.js::wireSearch()` `setTimeout(..., 200)`
  // shape verbatim.
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [debouncedQuery, setDebouncedQuery] = useState<string>("");
  // The search mode — `"filter"` (default) hides non-matches
  // and auto-expands ancestors; `"highlight"` paints
  // `search-match` without touching expansion. Mirrors the
  // legacy `web/state.js::initialExplorerShape().search.mode`
  // default (`"filter"`). The state is mirrored in the
  // `aria-pressed` + title attributes of the mode toggle
  // button so the visual stack stays in lock-step.
  const [searchMode, setSearchMode] = useState<"filter" | "highlight">(
    "filter",
  );
  // The hide-empty flag — filter-only. Mirrors the legacy
  // `web/state.js::initialExplorerShape().search.hideEmpty`
  // default (`true`); the toggle button surfaces the flag
  // verbatim via `aria-pressed` + title. The W6.2 React
  // mount owns the state here (no browser-state expansion
  // per the W6.2 contract).
  const [searchHideEmpty, setSearchHideEmpty] = useState<boolean>(true);
  // Ref to the search input element — the conditional
  // auto-focus effect focuses this element via
  // `requestAnimationFrame` ONLY when `document.activeElement
  // === document.body`, matching the legacy
  // `web/file_explorer.js::renderTreeHeader()` focus check
  // verbatim (a mid-IME-composition user never has their
  // keystroke stolen).
  const searchInputRef = useRef<HTMLInputElement | null>(null);

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

  // ---- W6.2 search effects ----
  // 200 ms debounce — mirrors the legacy
  // `web/file_explorer.js::wireSearch()` `setTimeout(..., 200)`
  // pattern verbatim. The previous timer is cancelled on
  // every keystroke so a fast typer only triggers one
  // `setDebouncedQuery` call after they stop. The cleanup
  // function clears the in-flight timer on unmount / query
  // change so a race between a delayed commit and a
  // re-render never fires a stale annotation.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 200);
    return () => {
      clearTimeout(timer);
    };
  }, [searchQuery]);

  // Conditional auto-focus — mirrors the legacy
  // `web/file_explorer.js::renderTreeHeader()` focus check
  // verbatim: deferred via `requestAnimationFrame` so the
  // DOM is committed to the document before `focus()` runs
  // (calling `focus()` synchronously on a freshly appended
  // node is a no-op in some browsers). Skipped when
  // `document.activeElement !== document.body` so a mid-
  // IME-composition user never has their keystroke stolen.
  // `preventScroll: true` keeps the focus from yanking the
  // viewport (matches the legacy `<input focus({ preventScroll:
  // true })>` shape).
  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      if (
        typeof document !== "undefined" &&
        document.activeElement === document.body
      ) {
        searchInputRef.current?.focus({ preventScroll: true });
      }
    });
    return () => {
      cancelAnimationFrame(raf);
    };
  }, []);

  // Pure search annotation — memoised on (debouncedQuery,
  // loadStatus.tree.root). `useMemo` keeps the typed
  // `{matches, ancestors}` shape stable across renders
  // when the inputs don't change, so the `FileTree`
  // `useEffect` doesn't re-fire on every Explorer render.
  // `null` (the typed "no active query" handle) is
  // returned when the tree isn't loaded yet — `FileTree`
  // restores the DOM in that case. The default-mode
  // initial render yields `null` (the W6.2 contract: no
  // annotation until the user types).
  const searchAnnotation: SearchAnnotation | null = useMemo(() => {
    if (loadStatus.kind !== "loaded") return null;
    if (debouncedQuery.trim() === "") return null;
    return annotateMatches(loadStatus.tree.root, debouncedQuery);
  }, [debouncedQuery, loadStatus]);

  // Memoised search-input change. The legacy wires the
  // input via `addEventListener("input", ...)` inside
  // `wireSearch()`; the React equivalent owns the change
  // via a single callback that updates the typed query
  // state. The 200 ms debounce lives in the effect above
  // so every keystroke updates the visible input value
  // instantly (no debounced echo back into the input
  // field — the legacy also does not echo).
  const handleSearchInputChange = useCallback(
    (next: string): void => {
      setSearchQuery(next);
    },
    [],
  );

  // Memoised Escape-clear — mirrors the legacy
  // `web/file_explorer.js::wireSearch()` `keydown` Escape
  // branch: when the input is focused AND the value is
  // non-empty, Escape clears the value + the query
  // WITHOUT losing focus on the input (the React state
  // update re-renders with `value=""`; the input retains
  // focus through the re-render). The `preventDefault`
  // call mirrors the legacy `e.preventDefault()` so any
  // ancestor Escape handler (browser back, etc.) does
  // not also fire.
  //
  // The handler clears BOTH the live `searchQuery` AND
  // the debounced `debouncedQuery` synchronously so the
  // `searchAnnotation` `useMemo` flips to `null` on the
  // next render without waiting for the 200 ms debounce
  // timer to fire. Mirrors the legacy
  // `input.value = ""; runSearch("");` shape byte-for-
  // byte — `runSearch("")` is called synchronously in
  // the same handler, NOT through the input-debounced
  // setTimeout. Typed input keeps the full 200 ms
  // debounce path (the `useEffect` keyed on
  // `[searchQuery]`); only Escape bypasses it.
  const handleSearchKeyDown = useCallback(
    (ev: React.KeyboardEvent<HTMLInputElement>): void => {
      if (ev.key === "Escape" && searchQuery !== "") {
        ev.preventDefault();
        setSearchQuery("");
        setDebouncedQuery("");
      }
    },
    [searchQuery],
  );

  // Memoised clear-button click — mirrors the legacy
  // `web/file_explorer.js::clearSearchInput()` shape
  // verbatim: the legacy reads the input's value off the
  // DOM (via `host.querySelector("[data-search-input]")`)
  // and resets state. The React equivalent reads state
  // directly (`searchQuery === ""`). The button stays
  // visible only when the value is non-empty (the CSS
  // `:not(:placeholder-shown) ~ .fex-search-clear` rule
  // mirrors the legacy shape).
  const handleSearchClear = useCallback((): void => {
    setSearchQuery("");
  }, []);

  // Memoised mode toggle — mirrors the legacy
  // `web/file_explorer.js::toggleSearchMode()` shape
  // verbatim: flip the typed mode, update state, and
  // re-apply the current query so the user sees the
  // effect of the mode switch instantly (the legacy
  // re-calls `runSearch(state.explorer.search.query)`;
  // the React equivalent lets the `useMemo` re-fire on
  // the next render because `debouncedQuery` is unchanged
  // and the FileTree's `useEffect` re-applies the
  // annotation with the new mode).
  const handleSearchToggleMode = useCallback((): void => {
    setSearchMode((prev) => (prev === "filter" ? "highlight" : "filter"));
  }, []);

  // Memoised hide-empty toggle — mirrors the legacy
  // `web/file_explorer.js::toggleHideEmpty()` shape
  // verbatim: flip the typed flag. The legacy re-runs
  // the filter pass when mode === "filter" + query is
  // non-empty; the React equivalent lets the FileTree
  // `useEffect` re-fire because `searchHideEmpty` is in
  // the dependency array (the dependency array carries
  // the same triple the legacy gate checks).
  const handleSearchToggleHideEmpty = useCallback((): void => {
    setSearchHideEmpty((prev) => !prev);
  }, []);

  // Render the search block underneath the tree-header
  // toolbar (the legacy `web/file_explorer.js::renderSearchBlock()`
  // shape). The block is always visible — the user can
  // clear the input at any time, even when the tree is
  // empty / loading / errored. The debounced `useEffect`
  // above + the FileTree `useEffect` together carry the
  // search semantics; this render only owns the input
  // UX surface.
  const renderSearchHeader = (): ReactNode => {
    const modeIcon =
      searchMode === "filter" ? "filter_alt" : "highlight_alt";
    const modeLabel = searchMode === "filter" ? "Filter" : "Highlight";
    const modeTitle =
      searchMode === "filter"
        ? "Filter mode: hiding non-matches. Click to switch to highlight."
        : "Highlight mode: painting matches. Click to switch to filter.";
    const hideEmptyTitle = searchHideEmpty
      ? "Hide empty folders: ON. Click to show all folders."
      : "Hide empty folders: OFF. Click to hide folders with no matches.";
    return (
      <div className="fex-tree-header-search" data-tree-header-search="">
        <div className="fex-search-row">
          <span className="fex-search-icon material-symbols-outlined">
            search
          </span>
          <input
            ref={searchInputRef}
            type="text"
            className="fex-search-input"
            placeholder="Search files & folders…"
            autoComplete="off"
            spellCheck={false}
            value={searchQuery}
            data-search-input=""
            onChange={(ev) => handleSearchInputChange(ev.target.value)}
            onKeyDown={handleSearchKeyDown}
          />
          <button
            type="button"
            className="fex-search-clear"
            title="Clear search"
            aria-label="Clear search"
            data-search-clear=""
            onClick={handleSearchClear}
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        <div className="fex-search-toggles">
          <button
            type="button"
            className="fex-snippet-btn fex-search-mode-btn"
            title={modeTitle}
            aria-label="Toggle search mode"
            aria-pressed={searchMode === "filter" ? "true" : "false"}
            data-search-mode-btn=""
            data-mode={searchMode}
            onClick={handleSearchToggleMode}
          >
            <span
              className="material-symbols-outlined"
              data-search-mode-icon=""
            >
              {modeIcon}
            </span>
            <span data-search-mode-label="">{modeLabel}</span>
          </button>
          <button
            type="button"
            className="fex-snippet-btn fex-search-hide-empty-btn"
            title={hideEmptyTitle}
            aria-label="Toggle hide empty folders"
            aria-pressed={searchHideEmpty ? "true" : "false"}
            data-search-hide-empty-btn=""
            onClick={handleSearchToggleHideEmpty}
          >
            <span className="material-symbols-outlined">visibility_off</span>
            Hide empty
          </button>
        </div>
      </div>
    );
  };

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
            searchAnnotation={searchAnnotation}
            searchMode={searchMode}
            searchHideEmpty={searchHideEmpty}
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
          {renderSearchHeader()}
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
