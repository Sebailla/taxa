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
 * `web/file_explorer.js` byte-for-byte):
 *  - Filter mode: hide non-match rows + auto-expand every
 *    folder on the ancestor chain. The DOM mutation runs
 *    in a `useEffect` keyed on the typed `searchAnnotation`
 *    prop — the React tree itself never re-renders on a
 *    keystroke (mirrors the legacy
 *    `render-time toggle, not re-mount` strategy).
 *  - Highlight mode: paint every matching row with the
 *    `.search-match` class. The class toggle is idempotent
 *    so a fast-typing user never sees stale matches; the
 *    `aria-expanded` + chevron state is NEVER touched in
 *    highlight mode so the user's manual expand/collapse
 *    choices survive (the legacy
 *    `applyHighlightToTree` contract preserved verbatim).
 *  - `filter + hideEmpty + zero matches`: paint the exact
 *    `No matches.` card inside the tree pane (reuses the
 *    `.fex-empty-state` chrome).
 *  - Clear / empty annotation: restore the tree — every
 *    wrap un-hidden, every `.search-match` class removed,
 *    the `No matches.` placeholder cleared.
 *
 * The DOM mutations stay inside a `useEffect` so React's
 * render cycle stays deterministic. The annotation is
 * computed by the parent `Explorer.tsx` via the pure
 * kernel helper `annotateMatches(tree, query)`; this
 * component receives the annotation as a typed prop and
 * applies it via DOM lookup (mirrors the legacy's
 * `applySearchToTree(host, annotation)` /
 * `applyHighlightToTree(host, annotation)` shape).
 *
 * spec.md rule 4: presentation depends on the public barrel +
 * domain. The component imports through `@taxa/research`
 * (the public barrel) only — no deep imports into the
 * application / domain / infrastructure layers.
 */

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import type {
  ExplorerTreeNode,
  ExplorerFolderNode,
  ExplorerFileNode,
  ExplorerTree,
  SearchAnnotation,
} from "@taxa/research";

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

/** Build the folder row element. Single-click selects the
 *  folder (highlights the row, mirrors the legacy `selectFolder`
 *  shape — folders do not open any file, the legacy selection
 *  is highlight-only). The chevron click toggles expansion.
 *  The row carries `role="button"` + `tabindex="0"` so a
 *  keyboard user can select the folder without a mouse.
 *  `aria-expanded` reflects the expansion state verbatim. */
function renderFolderRow(
  folder: ExplorerFolderNode,
  depth: number,
  isExpanded: boolean,
  isSelected: boolean,
  onToggleExpand: (path: string) => void,
  onSelectFolder: (path: string) => void,
  childRows: ReactNode,
): ReactNode {
  const folderPath = folder.path || "";
  const chevron = isExpanded ? "keyboard_arrow_down" : "keyboard_arrow_right";
  const folderIcon = isExpanded ? "folder" : "folder_open";
  const rowClass = `fex-row folder${isSelected ? " selected" : ""}`;
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
 *  `web/file_explorer.js::renderFileRow` shape verbatim. */
function renderFileRow(
  file: ExplorerFileNode,
  depth: number,
  isSelected: boolean,
  onSelectFile: (file: ExplorerFileNode) => void,
  onOpenFile: (file: ExplorerFileNode) => void,
): ReactNode {
  const filePath = file.path || "";
  const rowClass = `fex-row file${isSelected ? " selected" : ""}`;
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
 *  DOM-only toggle and keeps the React tree small). */
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
): ReactNode {
  const out: ReactNode[] = [];
  for (const child of folder.children) {
    if (child.type === "folder") {
      const childIsExpanded = expanded.has(child.path || "");
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
          ),
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
        ),
      );
    }
  }
  return out;
}

/** CSS.escape polyfill — mirrors the legacy
 *  `web/file_explorer.js::cssEscape` shape verbatim so
 *  paths with spaces, accents, quotes, or brackets round-trip
 *  through `querySelector('[data-folder-path="..."]')`
 *  without DOM errors. Falls back to a character-level escape
 *  when `CSS.escape` isn't available (older browsers).
 *  Internal to this module — not exported. */
function cssEscape(s: string): string {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(s);
  }
  return String(s).replace(/(["\\\]])/g, "\\$1");
}

/** Internal: apply the filter-mode search annotation to the
 *  rendered tree DOM. Mirrors the legacy
 *  `web/file_explorer.js::applySearchToTree(host, annotation)`
 *  byte-for-byte: expand every folder on the ancestor chain
 *  (flipping `aria-expanded` + chevron + folder icon); then
 *  hide every wrap whose path is not in `matches` or
 *  `ancestors`. The wrap selector (`[data-row-wrap]`) avoids
 *  the parent-might-be-shared trap where a file row's parent
 *  is the shared children container. Never touches `.selected`
 *  or any `.search-match` class so prior selection survives
 *  every keystroke. */
function applyFilterMutation(
  rootEl: HTMLElement,
  annotation: SearchAnnotation,
): void {
  const { matches, ancestors } = annotation;
  // First, expand every folder on the ancestor chain.
  for (const folderPath of ancestors) {
    const row = rootEl.querySelector(
      `[data-folder-path="${cssEscape(folderPath)}"]`,
    );
    if (!(row instanceof HTMLElement)) continue;
    const wrap = row.closest("[data-row-wrap]");
    if (!(wrap instanceof HTMLElement)) continue;
    const childrenContainer = wrap.querySelector(
      `[data-folder-children-of="${cssEscape(folderPath)}"]`,
    );
    if (childrenContainer instanceof HTMLElement) {
      childrenContainer.style.display = "";
    }
    if (row.getAttribute("aria-expanded") !== "true") {
      row.setAttribute("aria-expanded", "true");
      const chevron = row.querySelector("[data-folder-toggle]");
      if (chevron !== null) chevron.textContent = "keyboard_arrow_down";
      const icon = row.querySelector(".fex-icon");
      if (icon !== null) icon.textContent = "folder";
    }
  }
  // Then hide every wrap whose path is not in the visible set.
  const wraps = rootEl.querySelectorAll("[data-row-wrap]");
  wraps.forEach((wrap) => {
    if (!(wrap instanceof HTMLElement)) return;
    const row = wrap.querySelector(".fex-row");
    if (!(row instanceof HTMLElement)) return;
    const isFolder = row.classList.contains("folder");
    const path = isFolder
      ? row.dataset.folderPath || ""
      : row.dataset.filePath || "";
    if (matches.has(path) || ancestors.has(path)) {
      wrap.style.display = "";
    } else {
      wrap.style.display = "none";
    }
  });
}

/** Internal: apply the highlight-mode search annotation to the
 *  rendered tree DOM. Mirrors the legacy
 *  `web/file_explorer.js::applyHighlightToTree(host, annotation)`
 *  byte-for-byte: idempotently add `.search-match` to every
 *  matching row + remove the class from every non-match. Never
 *  touches `aria-expanded`, the chevron glyph, or the children
 *  container's display — the user's manual expand/collapse
 *  choices survive every keystroke (the legacy
 *  `Highlight mode keeps expand/collapse state` contract). */
function applyHighlightMutation(
  rootEl: HTMLElement,
  annotation: SearchAnnotation,
): void {
  const { matches } = annotation;
  const rows = rootEl.querySelectorAll(".fex-row");
  rows.forEach((row) => {
    if (!(row instanceof HTMLElement)) return;
    const isFolder = row.classList.contains("folder");
    const path = isFolder
      ? row.dataset.folderPath || ""
      : row.dataset.filePath || "";
    if (matches.has(path)) {
      row.classList.add("search-match");
    } else {
      row.classList.remove("search-match");
    }
  });
}

/** Internal: restore the rendered tree to its pre-search state.
 *  Mirrors the legacy
 *  `web/file_explorer.js::restoreTree()` shape: un-hide every
 *  row wrap, remove every `.search-match` class, and clear
 *  the `No matches.` placeholder if it was up. Does NOT
 *  touch `aria-expanded` / chevron / folder icon — those are
 *  the user's domain in the absence of a search query. */
function restoreTreeMutation(rootEl: HTMLElement): void {
  rootEl.querySelectorAll("[data-row-wrap]").forEach((wrap) => {
    if (wrap instanceof HTMLElement) wrap.style.display = "";
  });
  rootEl.querySelectorAll(".fex-row").forEach((row) => {
    if (row instanceof HTMLElement) row.classList.remove("search-match");
  });
  hideSearchEmptyMutation(rootEl);
}

/** Internal: paint the `No matches.` placeholder inside the
 *  tree pane when filter mode + active query + zero matches +
 *  hideEmpty are all true. Mirrors the legacy
 *  `web/file_explorer.js::showSearchEmpty(pane)` shape
 *  byte-for-byte: appends a `.fex-search-empty` block with
 *  the `search_off` Material Symbols icon + the exact
 *  `No matches.` text, stamped with `data-search-empty` so
 *  a future restore pass can find + remove it. Idempotent —
 *  a no-op when the placeholder is already up. */
function showSearchEmptyMutation(rootEl: HTMLElement): void {
  rootEl.classList.add("fex-search-empty-active");
  if (rootEl.querySelector("[data-search-empty]") !== null) return;
  const empty = document.createElement("div");
  empty.className = "fex-empty-state fex-search-empty";
  empty.setAttribute("data-search-empty", "");
  const icon = document.createElement("span");
  icon.className = "fex-empty-state-icon";
  icon.textContent = "search_off";
  const p = document.createElement("p");
  p.textContent = "No matches.";
  empty.append(icon, p);
  rootEl.append(empty);
}

/** Internal: hide + remove the `No matches.` placeholder if
 *  it was up. Mirrors the legacy
 *  `web/file_explorer.js::hideSearchEmpty(pane)` shape
 *  verbatim. Idempotent — a no-op when the placeholder
 *  isn't on the DOM. */
function hideSearchEmptyMutation(rootEl: HTMLElement): void {
  rootEl.classList.remove("fex-search-empty-active");
  const empty = rootEl.querySelector("[data-search-empty]");
  if (empty !== null) empty.remove();
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
  // Ref to the rendered tree's wrapping element — the
  // search `useEffect` below applies the legacy
  // `render-time toggle, not re-mount` mutations against
  // this root (the same `_currentHost.querySelector(
  // ".fex-tree-pane")` lookup the legacy
  // `applySearchToTree(host, annotation)` performs).
  // Mounted in `useEffect` so the first render commits
  // before the DOM lookup fires.
  const treeRootRef = useRef<HTMLDivElement | null>(null);
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
  // Search `useEffect` — applies the legacy `render-time
  // toggle, not re-mount` semantics on every annotation
  // flip. The effect:
  //   - When `searchAnnotation === null`, restores the
  //     tree (un-hides every wrap, removes every
  //     `.search-match` class, clears the `No matches.`
  //     placeholder).
  //   - When `searchMode === "filter"`, applies the filter
  //     pass: hide non-matches, auto-expand ancestors, and
  //     paint `No matches.` when `searchHideEmpty` is true
  //     and `matches.size === 0`. The `No matches.` card
  //     fires ONLY in filter mode + hideEmpty on (the
  //     legacy `filter + hideEmpty + no matches` triple).
  //   - When `searchMode === "highlight"`, applies the
  //     highlight pass: toggle `.search-match` on rows
  //     whose path is in `matches`. Never touches
  //     expansion (the legacy
  //     `Highlight mode keeps expand/collapse state`
  //     contract). `searchHideEmpty` is a no-op in
  //     highlight mode.
  // The effect runs after the render commits (the legacy
  // `useEffect` dependency array includes the rendered
  // tree's DOM so React's commit phase has already painted
  // the rows). The effect is stable across renders —
  // only the (annotation, mode, hideEmpty) identity
  // triggers a re-run, so a fast-typing user never blocks
  // on a stale mutation pass.
  useEffect(() => {
    const rootEl = treeRootRef.current;
    if (rootEl === null) return;
    if (searchAnnotation === null) {
      restoreTreeMutation(rootEl);
      return;
    }
    if (searchMode === "filter") {
      applyFilterMutation(rootEl, searchAnnotation);
      if (
        searchHideEmpty &&
        searchAnnotation.matches.size === 0
      ) {
        showSearchEmptyMutation(rootEl);
      } else {
        hideSearchEmptyMutation(rootEl);
      }
    } else {
      applyHighlightMutation(rootEl, searchAnnotation);
      hideSearchEmptyMutation(rootEl);
    }
  }, [searchAnnotation, searchMode, searchHideEmpty]);
  if (root === null) {
    return null;
  }
  return (
    <div
      ref={treeRootRef}
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
        expanded,
        selectedPath,
        internalSelectedFolder,
        onToggleExpand,
        handleSelectFolder,
        onSelectFile,
        onOpenFile,
      )}
    </div>
  );
}

/** Internal: render the children of a synthetic root folder
 *  (the explorer tree's root is an `ExplorerFolderNode`; the
 *  top-level component wraps it in a synthetic folder so the
 *  recursion stays consistent). The exported function above is
 *  the public surface; the synthetic-root wrap is private to
 *  this module. */
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
): ReactNode {
  if (node.type === "file") {
    return renderFileRow(
      node,
      depth,
      selectedPath === (node.path || ""),
      onSelectFile,
      onOpenFile,
    );
  }
  const folder = node;
  const isExpanded = expanded.has(folder.path || "");
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
  );
}

/** Public renderer — wraps the recursive walk with the typed
 *  `ExplorerTree` shape. The actual default export above is
 *  the canonical entry point; this function exists so tests
 *  can exercise the recursive walker with explicit
 *  `(tree, depth, ...)` arguments without a React render
 *  harness. */
export function renderFileTree(
  tree: ExplorerTree,
  expanded: ReadonlySet<string>,
  selectedPath: string | null,
  selectedFolderPath: string | null,
  onToggleExpand: (folderPath: string) => void,
  onSelectFolder: (folderPath: string) => void,
  onSelectFile: (file: ExplorerFileNode) => void,
  onOpenFile: (file: ExplorerFileNode) => void,
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
  );
}
