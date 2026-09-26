"use client";

/**
 * FileTree — recursive folder/file rows for the Browser-tab
 * Explorer client island (ODD-MIGRATE-003 / W6.1 + W6.2).
 *
 * Client component (boundary declared at the top of the file).
 * Renders the recursive tree fetched by `Explorer.tsx`'s mount
 * effect. Folders render with a chevron + icon + accessible
 * `aria-expanded`; files render with a description icon + the
 * basename + a `role="button"` affordance for keyboard select /
 * double-click open. Selection lives in DOM-only via
 * `data-folder-path` / `data-file-path` (mirrors the legacy
 * `web/file_explorer.js::selectFolder` / `selectFile` shape) so
 * single-click highlighting is a classList toggle, not a
 * re-render.
 *
 * W6.1 contract:
 *  - Recursive folder/file rows with accessible expand/select/
 *    double-click.
 *  - No search, no splitter, no materialization, no CDN viewers,
 *    no browser-state expansion.
 *  - Folders start collapsed (the W6.1 mount defaults to a
 *    quiet collapsed tree; the legacy default-everything-
 *    expanded shape is deferred to a future UX slice so the
 *    deep-tree recursion stays readable in W6.1).
 *
 * W6.2 contract (extends W6.1 with the Browser-tab tree
 * search semantics mirroring the legacy
 * `web/file_explorer.js` byte-for-byte). The refactor is
 * **render-puro**: visibility, expansion, and the
 * `.search-match` paint are derived at render time from
 * the typed `(tree, expanded, searchAnnotation, searchMode,
 * searchHideEmpty)` props — there is no post-render
 * `useEffect`, no `querySelector` lookup, and no DOM
 * mutation. The user-visible contract (data attributes,
 * ARIA, classes, behavior) stays byte-for-byte identical
 * to the legacy mutation-driven mount; only *how* the
 * contract is *applied* changes:
 *  - Filter mode: rows whose path is not in the
 *    `matches ∪ ancestors` set are SKIPPED in the
 *    recursive walker (no DOM element is rendered for
 *    them); every folder on the ancestor chain is added
 *    to the derived `expandedSet` so it renders expanded
 *    on the next commit. The `aria-expanded` + chevron +
 *    folder-icon state flips naturally because the row
 *    receives `isExpanded` from the derived set.
 *  - Highlight mode: every matching row receives the
 *    `search-match` class at render time; the derived
 *    `expandedSet` is the unchanged user-controlled set
 *    so `aria-expanded` + chevron state are NEVER touched
 *    (the legacy `Highlight mode keeps expand/collapse
 *    state` contract preserved verbatim).
 *  - `filter + hideEmpty + zero matches`: paint the exact
 *    `No matches.` card inside the tree pane (reuses the
 *    `.fex-empty-state` chrome).
 *  - Clear / empty annotation: the walker derives from
 *    `searchAnnotation === null` so every row is visible
 *    and no row carries `search-match` — the React render
 *    is the single source of truth, no separate "restore"
 *    pass is needed.
 *
 * The annotation is computed by the parent `Explorer.tsx`
 * via the pure kernel helper `annotateMatches(tree, query)`;
 * this component receives the annotation as a typed prop
 * and renders the derived view. Three pure helpers
 * (`deriveExpandedSet`, `isRowVisible`, `rowHasMatchClass`)
 * own the derivation — the component itself only wires
 * them into the recursive walker.
 *
 * spec.md rule 4: presentation depends on the public barrel +
 * domain. The component imports through `@taxa/research`
 * (the public barrel) only — no deep imports into the
 * application / domain / infrastructure layers.
 */

import { useCallback, useState, type ReactNode } from "react";
import type {
  ExplorerTreeNode,
  ExplorerFolderNode,
  ExplorerFileNode,
  ExplorerTree,
  SearchAnnotation,
} from "@taxa/research";
import { EmptyState } from "@taxa/design-system";

/** Props for the recursive `FileTree` component. The mount owns
 *  the expanded-set state (passed in via `expanded` /
 *  `onToggleExpand`) so the React state lives at one place;
 *  `FileTree` is a stateless recursive renderer.
 *
 *  W6.2 adds the search surface:
 *   - `searchAnnotation` — the typed `{matches, ancestors}`
 *     payload from the kernel's `annotateMatches()`. `null`
 *     means "no active query" (the tree renders untouched).
 *   - `searchMode` — `"filter"` (legacy render-time toggle:
 *     hide non-matches + auto-expand ancestors) vs
 *     `"highlight"` (paint `search-match`, never touch
 *     expansion).
 *   - `searchHideEmpty` — filter-only flag (the
 *     legacy `hideEmpty` toggle). Highlight mode ignores
 *     the flag for the visible paint but the React state
 *     still owns the value so a pre-toggle before
 *     switching to filter survives. */
export interface FileTreeProps {
  readonly tree: ExplorerTree;
  readonly expanded: ReadonlySet<string>;
  readonly selectedPath: string | null;
  readonly onToggleExpand: (folderPath: string) => void;
  readonly onSelectFile: (file: ExplorerFileNode) => void;
  readonly onOpenFile: (file: ExplorerFileNode) => void;
  readonly searchAnnotation: SearchAnnotation | null;
  readonly searchMode: "filter" | "highlight";
  readonly searchHideEmpty: boolean;
}

/** Map a W1 `FileFormat` to a Material Symbols icon name. Mirrors
 *  the legacy `web/file_explorer.js::iconForExt(ext)` mapping
 *  byte-for-byte so the React tree row tells the user what
 *  viewer will open on double-click. The list is intentionally
 *  exhaustive against the W1 `FileFormat` union (a future PR
 *  that adds an extension lands a new branch here so the typed
 *  surface stays honest at the boundary). The "other" fallback
 *  uses the `draft` glyph to mirror the legacy's generic
 *  description icon. */
function iconForExt(ext: string): string {
  switch (ext.toLowerCase()) {
    case "pdf":
      return "picture_as_pdf";
    case "epub":
      return "menu_book";
    case "html":
    case "htm":
      return "html";
    case "md":
      return "article";
    case "txt":
      return "description";
    case "doc":
    case "docx":
      return "article";
    case "xls":
    case "xlsx":
      return "table_chart";
    case "csv":
    case "tsv":
      return "table_chart";
    case "json":
      return "data_object";
    case "jpg":
    case "jpeg":
    case "png":
    case "gif":
    case "webp":
    case "bmp":
    case "svg":
      return "image";
    case "mp4":
    case "webm":
    case "ogv":
      return "videocam";
    case "zip":
    case "exe":
      return "draft";
    default:
      return "draft";
  }
}

/** Format a byte count using the legacy's `formatBytes` rules
 *  (B / KB / MB / GB with one decimal of precision). Pure
 *  helper — never called with `null` (the W1 wire projection
 *  carries `size: number` for every file node). */
function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/** Internal — derive the expanded set the recursive walker
 *  reads at render time. Pure function: same inputs always
 *  produce the same output.
 *   - When `searchAnnotation === null` (no active query) the
 *     user-controlled `expanded` set is returned unchanged.
 *   - When `searchMode === "highlight"` the user-controlled
 *     `expanded` set is returned unchanged — highlight mode
 *     never auto-expands (the legacy `Highlight mode keeps
 *     expand/collapse state` contract).
 *   - When `searchMode === "filter"` the derived set is
 *     `expanded ∪ searchAnnotation.ancestors` — every
 *     folder on the ancestor chain auto-expands so a
 *     collapsed chain never hides a match. The new set is
 *     a fresh `Set` so the parent's read-only contract
 *     stays honest (the union is a derived view, never a
 *     mutation of the caller's set). */
function deriveExpandedSet(
  expanded: ReadonlySet<string>,
  searchAnnotation: SearchAnnotation | null,
  searchMode: "filter" | "highlight",
): ReadonlySet<string> {
  if (searchAnnotation === null || searchMode === "highlight") {
    return expanded;
  }
  const next = new Set<string>(expanded);
  for (const ancestor of searchAnnotation.ancestors) {
    next.add(ancestor);
  }
  return next;
}

/** Internal — decide whether a row should render at all. Pure
 *  function. The walker SKIPS children whose path is not
 *  visible so the filter pass is a render-time conditional
 *  (the equivalent of the legacy `style.display = "none"`
 *  toggle, without touching the DOM).
 *   - When `searchAnnotation === null` every row is visible.
 *   - When `searchMode === "highlight"` every row is visible
 *     (highlight only paints a class, never hides).
 *   - When `searchMode === "filter"` a row is visible iff
 *     its path is in `matches ∪ ancestors`. */
function isRowVisible(
  path: string,
  searchAnnotation: SearchAnnotation | null,
  searchMode: "filter" | "highlight",
): boolean {
  if (searchAnnotation === null) return true;
  if (searchMode === "highlight") return true;
  return (
    searchAnnotation.matches.has(path) ||
    searchAnnotation.ancestors.has(path)
  );
}

/** Internal — decide whether a row should carry the
 *  `search-match` class at render time. Pure function.
 *   - When `searchAnnotation === null` no row carries the
 *     class (the legacy `restoreTree()` un-paint).
 *   - When `searchMode === "highlight"` rows whose path is
 *     in `matches` carry the class.
 *   - When `searchMode === "filter"` NO row carries the
 *     class — filter mode hides non-matches via the
 *     render-time conditional in `isRowVisible`, the class
 *     is highlight-only.
 *  The class is computed at render time so the render
 *  itself is the single source of truth — there is no
 *  post-render pass that toggles it. */
function rowHasMatchClass(
  path: string,
  searchAnnotation: SearchAnnotation | null,
  searchMode: "filter" | "highlight",
): boolean {
  if (searchAnnotation === null) return false;
  if (searchMode === "highlight") {
    return searchAnnotation.matches.has(path);
  }
  return false;
}

/** Build the folder row element. Single-click selects the
 *  folder (highlights the row, mirrors the legacy `selectFolder`
 *  shape — folders do not open any file, the legacy selection
 *  is highlight-only). The chevron click toggles expansion.
 *  The row carries `role="button"` + `tabindex="0"` so a
 *  keyboard user can select the folder without a mouse.
 *  `aria-expanded` reflects the expansion state verbatim.
 *
 *  Render-puro contract: `isExpanded` is derived from the
 *  walker-supplied `expandedSet` (which has already merged
 *  the filter-mode ancestor chain), and `rowClass` includes
 *  the `search-match` class when the highlight pass paints
 *  this row. There is no post-render DOM mutation. */
function renderFolderRow(
  folder: ExplorerFolderNode,
  depth: number,
  isExpanded: boolean,
  isSelected: boolean,
  onToggleExpand: (path: string) => void,
  onSelectFolder: (path: string) => void,
  childRows: ReactNode,
  searchAnnotation: SearchAnnotation | null,
  searchMode: "filter" | "highlight",
): ReactNode {
  const folderPath = folder.path || "";
  const chevron = isExpanded ? "keyboard_arrow_down" : "keyboard_arrow_right";
  const folderIcon = isExpanded ? "folder_open" : "folder";
  const hasMatch = rowHasMatchClass(folderPath, searchAnnotation, searchMode);
  const rowClass =
    `fex-row folder` +
    (isSelected ? " selected" : "") +
    (hasMatch ? " search-match" : "");
  return (
    <div data-row-wrap="folder" className="fex-row-wrap" key={`folder:${folderPath}`}>
      <div
        className={rowClass}
        data-folder-path={folderPath}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded ? "true" : "false"}
        aria-label={`Folder ${folder.name}, ${folder.children.length} items`}
        style={{ paddingLeft: `${4 + depth * 12}px` }}
        onClick={() => onSelectFolder(folderPath)}
        onKeyDown={(ev) => {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            onSelectFolder(folderPath);
            return;
          }
          if (ev.key === "ArrowRight" && !isExpanded) {
            ev.preventDefault();
            onToggleExpand(folderPath);
            return;
          }
          if (ev.key === "ArrowLeft" && isExpanded) {
            ev.preventDefault();
            onToggleExpand(folderPath);
          }
        }}
      >
        <span
          className="fex-icon material-symbols-outlined"
          data-folder-toggle=""
          onClick={(ev) => {
            ev.stopPropagation();
            onToggleExpand(folderPath);
          }}
        >
          {chevron}
        </span>
        <span
          className="fex-icon material-symbols-outlined"
          onClick={(ev) => {
            ev.stopPropagation();
            onToggleExpand(folderPath);
          }}
        >
          {folderIcon}
        </span>
        <span className="fex-label">{folder.name}</span>
      </div>
      {isExpanded ? (
        <div
          className="fex-children"
          data-folder-children-of={folderPath}
        >
          {childRows}
        </div>
      ) : null}
    </div>
  );
}

/** Build the file row element. Single-click selects the file
 *  (highlights the row only — no network), double-click opens
 *  the file in the right viewer. Mirrors the legacy
 *  `web/file_explorer.js::renderFileRow` shape verbatim.
 *
 *  Render-puro contract: `rowClass` includes the
 *  `search-match` class when the highlight pass paints
 *  this row. There is no post-render DOM mutation. */
function renderFileRow(
  file: ExplorerFileNode,
  depth: number,
  isSelected: boolean,
  onSelectFile: (file: ExplorerFileNode) => void,
  onOpenFile: (file: ExplorerFileNode) => void,
  searchAnnotation: SearchAnnotation | null,
  searchMode: "filter" | "highlight",
): ReactNode {
  const filePath = file.path || "";
  const hasMatch = rowHasMatchClass(filePath, searchAnnotation, searchMode);
  const rowClass =
    `fex-row file` +
    (isSelected ? " selected" : "") +
    (hasMatch ? " search-match" : "");
  const size = formatBytes(file.size);
  return (
    <div data-row-wrap="file" className="fex-row-wrap" key={`file:${filePath}`}>
      <div
        className={rowClass}
        data-file-path={filePath}
        role="button"
        tabIndex={0}
        aria-label={`File ${file.name}`}
        style={{ paddingLeft: `${4 + depth * 12}px` }}
        onClick={(ev) => {
          // The legacy filter checks `e.detail >= 2` so a
          // double-click's first click doesn't fire as a
          // select. The React equivalent uses a small
          // `details` heuristic — `>= 2` is the canonical
          // double-click threshold across browsers.
          if (ev.detail >= 2) return;
          onSelectFile(file);
        }}
        onDoubleClick={() => onOpenFile(file)}
        onKeyDown={(ev) => {
          if (ev.key === "Enter") {
            ev.preventDefault();
            onOpenFile(file);
            return;
          }
          if (ev.key === " ") {
            ev.preventDefault();
            onSelectFile(file);
          }
        }}
      >
        <span className="fex-icon material-symbols-outlined">
          {iconForExt(file.extension)}
        </span>
        <span className="fex-label">{file.name}</span>
        {size ? <span className="fex-meta">{size}</span> : null}
      </div>
    </div>
  );
}

/** Render the children of a folder row, recursively. Folders
 *  that are expanded render their children; collapsed folders
 *  skip the recursion (the legacy `display: none` toggle lives
 *  in `renderFolderRow`'s conditional render — no DOM is
 *  rendered for collapsed subtrees, which matches the legacy
 *  DOM-only toggle and keeps the React tree small).
 *
 *  Render-puro contract:
 *   - `expanded` is the walker-supplied DERIVED set (already
 *     `expanded ∪ ancestors` for filter mode). The walker
 *     reads from this set so `aria-expanded` + chevron +
 *     folder-icon flip naturally on the next commit.
 *   - Children whose path is not visible in the current
 *     `(searchAnnotation, searchMode)` triple are SKIPPED
 *     in the recursive walk (no DOM element is rendered for
 *     them). This replaces the legacy
 *     `style.display = "none"` pass with a render-time
 *     conditional — the React tree is the single source of
 *     truth.
 *   - `searchAnnotation` + `searchMode` are threaded into
 *     every row renderer + every recursive call so the
 *     highlight pass can paint `search-match` on the same
 *     pass. */
function renderChildren(
  folder: ExplorerFolderNode,
  depth: number,
  expanded: ReadonlySet<string>,
  selectedPath: string | null,
  selectedFolderPath: string | null,
  onToggleExpand: (folderPath: string) => void,
  onSelectFolder: (folderPath: string) => void,
  onSelectFile: (file: ExplorerFileNode) => void,
  onOpenFile: (file: ExplorerFileNode) => void,
  searchAnnotation: SearchAnnotation | null,
  searchMode: "filter" | "highlight",
): ReactNode {
  const out: ReactNode[] = [];
  for (const child of folder.children) {
    const childPath = child.path || "";
    // Render-puro filter pass — skip children whose path is
    // not visible in the current `(annotation, mode)` triple.
    // Highlight mode always renders every child; filter mode
    // hides non-matches via the walker, not via DOM mutation.
    if (!isRowVisible(childPath, searchAnnotation, searchMode)) {
      continue;
    }
    if (child.type === "folder") {
      const childIsExpanded = expanded.has(childPath);
      const childIsSelected = selectedFolderPath === child.path;
      out.push(
        renderFolderRow(
          child,
          depth,
          childIsExpanded,
          childIsSelected,
          onToggleExpand,
          // Folders are highlight-only on single-click. The
          // legacy `selectFolder(folderPath)` is the same
          // shape; the row's `onClick` is wired to
          // `onSelectFolder` (NOT `onToggleExpand`) so a
          // single-click selects/highlights without
          // expanding. The chevron + ArrowRight/ArrowLeft
          // still drive expansion.
          onSelectFolder,
          renderChildren(
            child,
            depth + 1,
            expanded,
            selectedPath,
            selectedFolderPath,
            onToggleExpand,
            onSelectFolder,
            onSelectFile,
            onOpenFile,
            searchAnnotation,
            searchMode,
          ),
          searchAnnotation,
          searchMode,
        ),
      );
    } else {
      const childIsSelected = selectedPath === (child.path || "");
      out.push(
        renderFileRow(
          child,
          depth,
          childIsSelected,
          onSelectFile,
          onOpenFile,
          searchAnnotation,
          searchMode,
        ),
      );
    }
  }
  return out;
}

/** Top-level recursive tree. Renders the root node and recurses
 *  through `renderChildren`. The root starts collapsed in the
 *  W6.1 mount (the legacy default-everything-expanded shape
 *  is deferred to a future UX slice — see the module-level
 *  contract note above). */
export default function FileTree(props: FileTreeProps): ReactNode {
  const {
    tree,
    expanded,
    selectedPath,
    onToggleExpand,
    onSelectFile,
    onOpenFile,
    searchAnnotation,
    searchMode,
    searchHideEmpty,
  } = props;
  // Internal folder-selection highlight state. The Explorer
  // prop `selectedPath` is reserved for file selection (single-
  // click on a file selects; the Viewer mounts on double-click).
  // Folders are highlight-only on single-click — the legacy
  // `web/file_explorer.js::selectFolder` shape toggled a CSS
  // class and never opened any file. The mount tracks folder
  // highlight in local state so a single-click on the folder
  // row selects (highlights) without expanding — the contract
  // the row's docblock already pins. The W6.1 `FileTreeProps`
  // surface stays unchanged: a future UX slice that wires
  // folder-open-on-double-click would land an explicit
  // `onSelectFolder` prop here and replace this internal state
  // with a controlled callback so the Explorer can observe
  // folder selection in its lifecycle.
  const [internalSelectedFolder, setInternalSelectedFolder] =
    useState<string | null>(null);
  const handleSelectFolder = useCallback((folderPath: string): void => {
    setInternalSelectedFolder(folderPath);
  }, []);
  const root = tree.root;
  // ODD-EXP-PHASE2-004 — the search empty state now renders
  // through the JSX `<EmptyState>` primitive below instead
  // of the legacy imperative `showSearchEmptyMutation`
  // helper. The boolean `showSearchEmpty` is the typed
  // handle the JSX uses to conditionally render the
  // primitive vs the recursive tree. The boolean is
  // derived at render time (no `useEffect`, no DOM
  // mutation) so the empty card flips synchronously with
  // the `(annotation, mode, hideEmpty)` props.
  const showSearchEmpty =
    searchAnnotation !== null &&
    searchMode === "filter" &&
    searchHideEmpty &&
    searchAnnotation.matches.size === 0;
  // Render-puro expansion derivation — the recursive walker
  // reads from `derivedExpanded` instead of the raw `expanded`
  // prop. The helper folds the filter-mode ancestor chain into
  // a fresh `Set` so the user's read-only `expanded` prop
  // stays untouched. Highlight mode returns `expanded`
  // unchanged; `searchAnnotation === null` returns `expanded`
  // unchanged. The fresh set is created on every render — the
  // walker is cheap (collapsed folders skip their subtree) so
  // the cost is bounded.
  const derivedExpanded = deriveExpandedSet(
    expanded,
    searchAnnotation,
    searchMode,
  );
  // ODD-EXP-PHASE2-004 — the `filter + hideEmpty + zero
  // matches` triple now renders the `<EmptyState>` JSX
  // primitive (the `data-search-empty` wrapper carries
  // the data attribute the test harness asserts; the
  // EmptyState primitive owns the icon + title + size
  // contract). When `showSearchEmpty` is true, the
  // recursive tree is NOT rendered (the EmptyState
  // replaces it), so the render-puro derivation above is
  // unused for that branch.
  if (showSearchEmpty) {
    return (
      <div data-search-empty="" className="fex-tree-root">
        <EmptyState
          icon={
            <span aria-hidden="true" className="material-symbols-outlined">
              search_off
            </span>
          }
          title="No matches."
          size="sm"
        />
      </div>
    );
  }
  if (root === null) {
    return null;
  }
  return (
    <div
      data-tree-root=""
      className="fex-tree-root"
    >
      {renderChildren(
        {
          name: root.name,
          path: root.path,
          type: "folder",
          children: root.type === "folder" ? root.children : [root],
        },
        0,
        derivedExpanded,
        selectedPath,
        internalSelectedFolder,
        onToggleExpand,
        handleSelectFolder,
        onSelectFile,
        onOpenFile,
        searchAnnotation,
        searchMode,
      )}
    </div>
  );
}

/** Internal: render the children of a synthetic root folder
 *  (the explorer tree's root is an `ExplorerFolderNode`; the
 *  top-level component wraps it in a synthetic folder so the
 *  recursion stays consistent). The exported function above is
 *  the public surface; the synthetic-root wrap is private to
 *  this module.
 *
 *  Render-puro contract: threads `searchAnnotation` +
 *  `searchMode` into the recursion. Visibility is decided
 *  via `isRowVisible` (skip the child) and the
 *  `search-match` class is computed at render time in the
 *  row renderers. */
function renderChildrenShim(
  node: ExplorerTreeNode,
  depth: number,
  expanded: ReadonlySet<string>,
  selectedPath: string | null,
  selectedFolderPath: string | null,
  onToggleExpand: (folderPath: string) => void,
  onSelectFolder: (folderPath: string) => void,
  onSelectFile: (file: ExplorerFileNode) => void,
  onOpenFile: (file: ExplorerFileNode) => void,
  searchAnnotation: SearchAnnotation | null,
  searchMode: "filter" | "highlight",
): ReactNode {
  if (node.type === "file") {
    const filePath = node.path || "";
    if (!isRowVisible(filePath, searchAnnotation, searchMode)) {
      return null;
    }
    return renderFileRow(
      node,
      depth,
      selectedPath === (node.path || ""),
      onSelectFile,
      onOpenFile,
      searchAnnotation,
      searchMode,
    );
  }
  const folder = node;
  const folderPath = folder.path || "";
  if (!isRowVisible(folderPath, searchAnnotation, searchMode)) {
    return null;
  }
  const isExpanded = expanded.has(folderPath);
  const isSelected = selectedFolderPath === folder.path;
  const childRows = node.children.map((child: ExplorerTreeNode) =>
    renderChildrenShim(
      child,
      depth + 1,
      expanded,
      selectedPath,
      selectedFolderPath,
      onToggleExpand,
      onSelectFolder,
      onSelectFile,
      onOpenFile,
      searchAnnotation,
      searchMode,
    ),
  );
  return renderFolderRow(
    folder,
    depth,
    isExpanded,
    isSelected,
    onToggleExpand,
    // The synthetic root + every nested folder row passes
    // `onSelectFolder` (NOT `onToggleExpand`) to the
    // row's select slot. The legacy `selectFolder` shape
    // toggled a CSS class and never opened any file; the
    // chevron + ArrowRight/ArrowLeft still drive expansion.
    onSelectFolder,
    childRows,
    searchAnnotation,
    searchMode,
  );
}

/** Public renderer — wraps the recursive walk with the typed
 *  `ExplorerTree` shape. The actual default export above is
 *  the canonical entry point; this function exists so tests
 *  can exercise the recursive walker with explicit
 *  `(tree, depth, ...)` arguments without a React render
 *  harness.
 *
 *  Render-puro contract: callers pass `(searchAnnotation,
 *  searchMode)` so the walker derives visibility + the
 *  `search-match` class at render time. The exported
 *  function deliberately has no `useEffect` and never
 *  mutates the DOM. */
export function renderFileTree(
  tree: ExplorerTree,
  expanded: ReadonlySet<string>,
  selectedPath: string | null,
  selectedFolderPath: string | null,
  onToggleExpand: (folderPath: string) => void,
  onSelectFolder: (folderPath: string) => void,
  onSelectFile: (file: ExplorerFileNode) => void,
  onOpenFile: (file: ExplorerFileNode) => void,
  searchAnnotation: SearchAnnotation | null,
  searchMode: "filter" | "highlight",
): ReactNode {
  const root = tree.root;
  if (root === null) return null;
  return renderChildrenShim(
    root,
    0,
    expanded,
    selectedPath,
    selectedFolderPath,
    onToggleExpand,
    onSelectFolder,
    onSelectFile,
    onOpenFile,
    searchAnnotation,
    searchMode,
  );
}
