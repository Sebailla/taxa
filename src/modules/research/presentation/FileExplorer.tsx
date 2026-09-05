"use client";

// FileExplorer — the top-level research presentation shell. Two-pane
// layout (left recursive tree + right viewer) mounted for a non-null
// `taxonId`. The explorer SELF-MOUNTS via the `useFileExplorer` hook
// (5b.2) — the parent (app-shell, PR 5b.4) never pre-fetches.
//
// Realm mapping: folder rows dispatch via the domain
// `realmForFolderPath(path)` helper (5b.4 — was deferred in 5b.3).
// File rows do NOT receive a realm attribute (5b.4 user-decision #3
// — folder rows only).
//
// No Search / Folder tab wiring — strictly the research presentation
// surface. No app-shell integration, no CSS changes, no new
// dependencies.

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactElement } from "react";

import {
  DEBOUNCE_MS,
  annotateExplorerMatches,
  realmForFolderPath,
  useFileExplorer,
  type ExplorerSearchState,
  type ExplorerViewerTab,
  type ViewerFile,
  type WireFileNode,
} from "@taxa/research";

import { FileViewer } from "./FileViewer";

// ---- Tree-row view model ---------------------------------------------------
// `WireFileNode` carries `name` + `path` + `children` (folder) or
// `extension` + `size` (file). The presentation layer doesn't reshape
// it — it's the application hook that hands us this surface verbatim.

interface FolderRowProps {
  readonly node: WireFileNode & { type: "folder" };
  readonly depth: number;
  readonly matches: ReadonlySet<string>;
  readonly selectedFolderPath: string | null;
  readonly onSelectFolder: (path: string) => void;
}

function FolderRow({
  node, depth, matches, selectedFolderPath, onSelectFolder,
}: FolderRowProps): ReactElement {
  const isSelected = node.path === selectedFolderPath;
  return (
    <>
      <div
        className={`fex-row folder${isSelected ? " selected" : ""}`}
        data-folder-path={node.path}
        data-realm={realmForFolderPath(node.path)}
        data-row-wrap="folder"
        role="button"
        tabIndex={0}
        aria-expanded="true"
        aria-selected={isSelected}
        style={{ paddingLeft: 4 + depth * 12 }}
        onClick={() => onSelectFolder(node.path)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelectFolder(node.path);
          }
        }}
      >
        <span className="fex-icon material-symbols-outlined" aria-hidden="true">
          folder
        </span>
        <span className="fex-label">{node.name || "/"}</span>
      </div>
      <div
        className="fex-children"
        data-folder-children-of={node.path}
        style={{ marginLeft: 14, paddingLeft: 8 }}
      >
        {node.children.map((child) => (
          <TreeRow
            key={child.path}
            node={child}
            depth={depth + 1}
            matches={matches}
            selectedFolderPath={selectedFolderPath}
            onSelectFolder={onSelectFolder}
          />
        ))}
      </div>
    </>
  );
}

interface FileRowProps {
  readonly node: WireFileNode & { type: "file" };
  readonly depth: number;
  readonly matches: ReadonlySet<string>;
  readonly selectedFilePath: string | null;
  readonly onSelectFile: (node: WireFileNode & { type: "file" }) => void;
}

function FileRow({
  node, depth, matches, selectedFilePath, onSelectFile,
}: FileRowProps): ReactElement {
  const isMatch = matches.has(node.path);
  const isSelected = node.path === selectedFilePath;
  return (
    <div
      className={`fex-row file${isSelected ? " selected" : ""}${isMatch ? " search-match" : ""}`}
      data-file-path={node.path}
      data-row-wrap="file"
      role="button"
      tabIndex={0}
      aria-selected={isSelected}
      style={{ paddingLeft: 4 + depth * 12 }}
      onClick={() => onSelectFile(node)}
    >
      <span className="fex-icon material-symbols-outlined" aria-hidden="true">
        draft
      </span>
      <span className="fex-label">{node.name}</span>
    </div>
  );
}

type TreeRowVariant =
  | (WireFileNode & { type: "folder" })
  | (WireFileNode & { type: "file" });

interface TreeRowProps {
  readonly node: TreeRowVariant;
  readonly depth: number;
  readonly matches: ReadonlySet<string>;
  readonly selectedFolderPath: string | null;
  readonly selectedFilePath: string | null;
  readonly onSelectFolder: (path: string) => void;
  readonly onSelectFile: (node: WireFileNode & { type: "file" }) => void;
}

function TreeRow(props: TreeRowProps): ReactElement {
  if (props.node.type === "folder") {
    return (
      <FolderRow
        node={props.node}
        depth={props.depth}
        matches={props.matches}
        selectedFolderPath={props.selectedFolderPath}
        onSelectFolder={props.onSelectFolder}
      />
    );
  }
  return (
    <FileRow
      node={props.node}
      depth={props.depth}
      matches={props.matches}
      selectedFilePath={props.selectedFilePath}
      onSelectFile={props.onSelectFile}
    />
  );
}

// ---- Empty-state helpers --------------------------------------------------

function TreeEmptyState({ message }: { readonly message: string }): ReactElement {
  return (
    <div className="fex-empty-state" role="status" aria-live="polite">
      <span className="fex-empty-state-icon material-symbols-outlined"
            aria-hidden="true">folder_off</span>
      <p>{message}</p>
    </div>
  );
}

function TreeLoadingState(): ReactElement {
  return (
    <div className="fex-empty-state" role="status" aria-live="polite">
      <span className="fex-empty-state-icon material-symbols-outlined animate-spin"
            aria-hidden="true">progress_activity</span>
      <p>Loading research tree…</p>
    </div>
  );
}

const NO_CORPUS_MESSAGE =
  "No research folders yet — materialize a taxon to populate the tree.";

// ---- FileExplorer shell --------------------------------------------------

export interface FileExplorerProps {
  /** Selected taxon (the explorer is mounted when this is non-null).
   *  When null the explorer renders its no-taxon placeholder without
   *  firing any network request. */
  readonly taxonId: number | null;
  /** Base URL for the files endpoint (`${baseUrl}/api/taxon/{id}/files`). */
  readonly baseUrl: string;
  /** Override the fetch function (tests / SSR). Optional. */
  readonly fetchFn?: (input: string, init?: {
    method?: string;
    headers?: Record<string, string>;
  }) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;
}

// Locate a wire file node by path via an iterative walk so deep trees
// don't blow the JS call stack.
function findFileNode(root: WireFileNode, path: string): WireFileNode | null {
  const stack: WireFileNode[] = [root];
  while (stack.length) {
    const node = stack.pop();
    if (!node) continue;
    if (node.type === "file" && node.path === path) return node;
    if (node.type === "folder") {
      for (const c of node.children) stack.push(c);
    }
  }
  return null;
}

export function FileExplorer({
  taxonId, baseUrl, fetchFn,
}: FileExplorerProps): ReactElement {
  // The hook is unconditionally declared (rules of hooks); when
  // `taxonId` is null the hook short-circuits to the no-fetch idle
  // surface so the explorer renders its placeholder.
  const hook = useFileExplorer({ baseUrl, taxonId, fetchFn });

  // Local view-state — the search query is debounced via DEBOUNCE_MS
  // so a fast typer only triggers one annotateExplorerMatches pass
  // after they stop. Search mode / hideEmpty live on the hook's
  // persisted state; only the query needs a local mirror (the legacy
  // mirror — the input field shows the user's keystrokes immediately,
  // the hook state updates on the trailing edge).
  const [queryInput, setQueryInput] = useState<string>(
    hook.state.search.query,
  );
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync the input field when the hook's persisted query changes
  // externally (e.g. a taxon switch resets the hook state — the
  // input must clear too).
  useEffect(() => {
    setQueryInput(hook.state.search.query);
  }, [hook.state.search.query]);

  // Debounce the input → hook write. The trailing-edge timer is
  // cancelled on every keystroke + on unmount.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      debounceRef.current = null;
      const next: ExplorerSearchState = {
        ...hook.state.search, query: queryInput,
      };
      hook.setSearch(next);
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [queryInput, hook]);

  // The annotation helper runs only when the debounced query changes
  // (the hook's `search` is the debounced source of truth) — keeps
  // the expensive tree walk off the keystroke path.
  const annotation = useMemo(
    () => annotateExplorerMatches(hook.tree?.root ?? null, hook.state.search.query),
    [hook.tree, hook.state.search.query],
  );

  // No-taxon / loading / error states (self-mount: hook owns the fetch).
  if (taxonId === null) {
    return (
      <div className="research-explorer" data-explorer="idle" data-taxon-id="">
        <div className="file-explorer-pane" data-pane="tree" />
        <div className="file-viewer-pane" data-pane="viewer">
          <TreeEmptyState message={NO_CORPUS_MESSAGE} />
        </div>
      </div>
    );
  }

  if (hook.loading && hook.tree === null) {
    return (
      <div className="research-explorer" data-explorer="loading"
           data-taxon-id={taxonId} aria-busy="true">
        <div className="file-explorer-pane" data-pane="tree">
          <TreeLoadingState />
        </div>
        <div className="file-viewer-pane" data-pane="viewer">
          <div className="fex-empty-state" role="status" aria-live="polite">
            <span className="fex-empty-state-icon material-symbols-outlined animate-spin"
                  aria-hidden="true">progress_activity</span>
            <p>Loading viewer…</p>
          </div>
        </div>
      </div>
    );
  }

  if (hook.error !== null) {
    return (
      <div className="research-explorer" data-explorer="error"
           data-taxon-id={taxonId} role="status" aria-live="assertive">
        <div className="file-explorer-pane" data-pane="tree" />
        <div className="file-viewer-pane" data-pane="viewer">
          <div className="fex-empty-state">
            <span className="fex-empty-state-icon material-symbols-outlined"
                  aria-hidden="true">error</span>
            <p>{`Could not load file tree: ${hook.error.message}`}</p>
          </div>
        </div>
      </div>
    );
  }

  const tree = hook.tree;
  // The hook returns `tree: null` while loading or when the envelope
  // is invalid (the application predicate rejects malformed inputs).
  // For the latter we render the empty-corpus placeholder so the user
  // sees a stable "no corpus" surface instead of a blank pane.
  if (tree === null || !tree.exists || tree.root === null) {
    return (
      <div className="research-explorer" data-explorer="empty" data-taxon-id={taxonId}>
        <div className="file-explorer-pane" data-pane="tree">
          <TreeEmptyState message={NO_CORPUS_MESSAGE} />
        </div>
        <div className="file-viewer-pane" data-pane="viewer">
          <FileViewer
            file={null}
            baseUrl={baseUrl}
            taxonId={taxonId}
            viewerTab={hook.state.viewerTab}
            onSelectTab={hook.setViewerTab}
          />
        </div>
      </div>
    );
  }

  // Selected row paths — `openFilePath` is the file the user
  // double-clicked; the folder is whatever row currently has the
  // `.selected` class. The explorer derives both from the persisted
  // state so the explorer reset on taxon switch (spec.md §State
  // Changes) clears every selection automatically.
  const selectedFilePath = hook.state.openFilePath;
  const openFileNode = selectedFilePath === null
    ? null : findFileNode(tree.root, selectedFilePath);
  const openFile: ViewerFile | null = openFileNode && openFileNode.type === "file"
    ? {
        name: openFileNode.name,
        path: openFileNode.path,
        extension: openFileNode.extension,
        size: openFileNode.size,
      }
    : null;

  const search = hook.state.search;
  const searchMode = search.mode;

  return (
    <div className="research-explorer" data-explorer="ready" data-taxon-id={taxonId}>
      <div className="file-explorer-pane" data-pane="tree">
        <div className="fex-tree-header">
          <h2>Research</h2>
        </div>
        <div className="fex-tree-header-search">
          <div className="fex-search-row">
            <span className="fex-search-icon material-symbols-outlined"
                  aria-hidden="true">search</span>
            <input
              type="text"
              className="fex-search-input"
              placeholder="Search files & folders…"
              autoComplete="off"
              spellCheck={false}
              value={queryInput}
              data-search-input=""
              aria-label="Search files and folders"
              onChange={(e) => setQueryInput(e.target.value)}
            />
          </div>
          <div className="fex-search-toggles">
            <button
              type="button"
              className="fex-snippet-btn fex-search-mode-btn"
              title={
                searchMode === "filter"
                  ? "Filter mode: hiding non-matches. Click to switch to highlight."
                  : "Highlight mode: painting matches. Click to switch to filter."
              }
              aria-label="Toggle search mode"
              aria-pressed={searchMode === "filter"}
              data-search-mode-btn=""
              data-mode={searchMode}
              onClick={() => hook.setSearch({
                ...search,
                mode: searchMode === "filter" ? "highlight" : "filter",
              })}
            >
              <span className="material-symbols-outlined" aria-hidden="true">
                {searchMode === "filter" ? "filter_alt" : "highlight_alt"}
              </span>
              <span>{searchMode === "filter" ? "Filter" : "Highlight"}</span>
            </button>
            <button
              type="button"
              className="fex-snippet-btn fex-search-hide-empty-btn"
              title={
                search.hideEmpty
                  ? "Hide empty folders: ON. Click to show all folders."
                  : "Hide empty folders: OFF. Click to hide folders with no matches."
              }
              aria-label="Toggle hide empty folders"
              aria-pressed={search.hideEmpty}
              data-search-hide-empty-btn=""
              onClick={() => hook.setSearch({
                ...search, hideEmpty: !search.hideEmpty,
              })}
            >
              <span className="material-symbols-outlined" aria-hidden="true">
                visibility_off
              </span>
              Hide empty
            </button>
          </div>
        </div>
        <TreeRow
          node={tree.root}
          depth={0}
          matches={annotation.matches}
          selectedFolderPath={selectedFilePath}
          selectedFilePath={selectedFilePath}
          onSelectFolder={(path) => hook.openFile(path, null)}
          onSelectFile={(node) => hook.openFile(node.path, node.extension)}
        />
      </div>
      <div className="file-viewer-pane" data-pane="viewer">
        <FileViewer
          file={openFile}
          baseUrl={baseUrl}
          taxonId={taxonId}
          viewerTab={hook.state.viewerTab as ExplorerViewerTab}
          onSelectTab={hook.setViewerTab}
        />
      </div>
    </div>
  );
}
