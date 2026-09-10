"use client";

// File-explorer application surface (PR 5b.2). Pure view-model
// helpers + React hook adapter (network boundary). The Explorer
// search contract and DEBOUNCE_MS anchor are declared here so 5b.3
// can consume them without re-inventing either.

import { useEffect, useState } from "react";

import {
  isValidFilesEnvelope,
  type FileFormat,
  type WireFileNode,
} from "../domain/research-file";
import { fetchFiles, type FetchLike } from "../infrastructure/api";

// ---- Persisted Explorer search contract (5b.2 anchor) ------------

/** spec.md §Tree search debounce — 200 ms. Pinned so 5b.3 cannot drift. */
export const DEBOUNCE_MS = 200;

export type ExplorerSearchMode = "filter" | "highlight";
export type ExplorerViewerTab = "Raw" | "Table" | "Tree";

/** Mirrors `web/state.js::initialExplorerShape().search`. */
export interface ExplorerSearchState {
  readonly query: string;
  readonly mode: ExplorerSearchMode;
  readonly hideEmpty: boolean;
}

/** The `state.explorer.*` slice. */
export interface ExplorerState {
  readonly search: ExplorerSearchState;
  readonly openFilePath: string | null;
  readonly openFileFormat: FileFormat | null;
  readonly viewerTab: ExplorerViewerTab;
}

/** Initial Explorer search state — byte-for-byte compatible with the
 *  legacy `web/state.js::initialExplorerShape().search` literal. */
export function initialExplorerSearchState(): ExplorerSearchState {
  return { query: "", mode: "filter", hideEmpty: true };
}

/** Initial full Explorer state. */
export function initialExplorerState(): ExplorerState {
  return {
    search: initialExplorerSearchState(),
    openFilePath: null,
    openFileFormat: null,
    viewerTab: "Raw",
  };
}

export function isExplorerSearchMode(v: unknown): v is ExplorerSearchMode {
  return v === "filter" || v === "highlight";
}

export function isExplorerViewerTab(v: unknown): v is ExplorerViewerTab {
  return v === "Raw" || v === "Table" || v === "Tree";
}

export function isExplorerSearchState(v: unknown): v is ExplorerSearchState {
  if (typeof v !== "object" || v === null) return false;
  const o = v as Record<string, unknown>;
  return typeof o.query === "string"
    && isExplorerSearchMode(o.mode)
    && typeof o.hideEmpty === "boolean";
}

// ---- Pure tree-annotation view model ------------------------------

/** Presentation-ready projection of a `FilesEnvelope`. Returns `null`
 *  when the envelope is invalid so callers can distinguish "not loaded"
 *  from "loaded, empty corpus". */
export interface ExplorerTreeViewModel {
  readonly exists: boolean;
  readonly taxonId: number;
  readonly taxonName: string;
  readonly taxonPath: string;
  readonly filesystemPath: string;
  readonly subpath: string | null;
  readonly root: WireFileNode | null;
}

export function projectExplorerTree(envelope: unknown): ExplorerTreeViewModel | null {
  if (!isValidFilesEnvelope(envelope)) return null;
  return {
    exists: envelope.exists,
    taxonId: envelope.taxon_id,
    taxonName: envelope.taxon_name,
    taxonPath: envelope.taxon_path,
    filesystemPath: envelope.filesystem_path,
    subpath: envelope.subpath,
    root: envelope.root,
  };
}

/** Returns { matches, ancestors } for query against the tree.
 *    matches   — every node whose name OR path contains query
 *                (case-insensitive substring).
 *    ancestors — every folder that contains at least one matching
 *                descendant (transitive).
 *  Framework-free port of `web/file_explorer.js::_annotateMatches`. */
export function annotateExplorerMatches(
  root: WireFileNode | null,
  query: string,
): { matches: ReadonlySet<string>; ancestors: ReadonlySet<string> } {
  const matches = new Set<string>();
  const ancestors = new Set<string>();
  if (!root || !query) return { matches, ancestors };
  const needle = query.toLowerCase();
  const stack: WireFileNode[] = [root];
  while (stack.length) {
    const node = stack.pop();
    if (!node) continue;
    const path = node.path || "";
    const name = node.name || "";
    if (
      path.toLowerCase().includes(needle) ||
      name.toLowerCase().includes(needle)
    ) {
      matches.add(path);
    }
    if (node.type === "folder" && Array.isArray(node.children)) {
      for (const c of node.children) stack.push(c);
    }
  }
  const visit = (node: WireFileNode): boolean => {
    const path = node.path || "";
    if (matches.has(path)) return true;
    if (node.type !== "folder" || !Array.isArray(node.children)) return false;
    let childHasMatch = false;
    for (const c of node.children) if (visit(c)) childHasMatch = true;
    if (childHasMatch) ancestors.add(path);
    return childHasMatch;
  };
  visit(root);
  return { matches, ancestors };
}

// ---- React hook adapter (network boundary) ------------------------

export interface UseFileExplorerOptions {
  readonly baseUrl: string;
  readonly taxonId: number | null;
  readonly fetchFn?: FetchLike;
}

export interface FileExplorerHookState {
  readonly tree: ExplorerTreeViewModel | null;
  readonly state: ExplorerState;
  readonly loading: boolean;
  readonly error: Error | null;
  readonly setSearch: (next: ExplorerSearchState) => void;
  readonly openFile: (path: string | null, format: FileFormat | null) => void;
  readonly setViewerTab: (tab: ExplorerViewerTab) => void;
  readonly resetState: () => void;
}

/** React adapter — owns the network boundary. Loads
 *  `${baseUrl}/api/taxon/${taxonId}/files` on mount and on taxonId
 *  change; resets Explorer state on every taxon switch
 *  (spec.md §State Changes). */
export function useFileExplorer(
  options: UseFileExplorerOptions,
): FileExplorerHookState {
  const { baseUrl, taxonId, fetchFn } = options;
  const [tree, setTree] = useState<ExplorerTreeViewModel | null>(null);
  const [state, setState] = useState<ExplorerState>(() => initialExplorerState());
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (taxonId === null) {
      setTree(null); setLoading(false); setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true); setError(null);
    void (async () => {
      try {
        const env = await fetchFiles(baseUrl, taxonId, fetchFn);
        if (cancelled) return;
        setTree(projectExplorerTree(env));
        setLoading(false);
      } catch (cause) {
        if (cancelled) return;
        setError(cause instanceof Error ? cause : new Error(String(cause)));
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [baseUrl, taxonId, fetchFn]);

  // Explorer state reset on taxon switch (spec.md §State Changes).
  useEffect(() => { setState(initialExplorerState()); }, [taxonId]);

  return {
    tree,
    state,
    loading,
    error,
    setSearch: (next) => setState((p) => ({ ...p, search: next })),
    openFile: (path, format) =>
      setState((p) => ({ ...p, openFilePath: path, openFileFormat: format })),
    setViewerTab: (tab) => setState((p) => ({ ...p, viewerTab: tab })),
    resetState: () => setState(initialExplorerState()),
  };
}
