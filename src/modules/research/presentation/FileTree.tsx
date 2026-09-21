"use client";

/**
 * FileTree — recursive folder/file rows for the Browser-tab
 * Explorer client island (ODD-MIGRATE-003 / W6.1).
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
} from "@taxa/research";

/** Props for the recursive `FileTree` component. The mount owns
 *  the expanded-set state (passed in via `expanded` /
 *  `onToggleExpand`) so the React state lives at one place;
 *  `FileTree` is a stateless recursive renderer. */
export interface FileTreeProps {
  readonly tree: ExplorerTree;
  readonly expanded: ReadonlySet<string>;
  readonly selectedPath: string | null;
  readonly onToggleExpand: (folderPath: string) => void;
  readonly onSelectFile: (file: ExplorerFileNode) => void;
  readonly onOpenFile: (file: ExplorerFileNode) => void;
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

/** Top-level recursive tree. Renders the root node and recurses
 *  through `renderChildren`. The root starts collapsed in the
 *  W6.1 mount (the legacy default-everything-expanded shape
 *  is deferred to a future UX slice — see the module-level
 *  contract note above). */
export default function FileTree(props: FileTreeProps): ReactNode {
  const { tree, expanded, selectedPath, onToggleExpand, onSelectFile, onOpenFile } = props;
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
  if (root === null) {
    return null;
  }
  return renderChildren(
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
