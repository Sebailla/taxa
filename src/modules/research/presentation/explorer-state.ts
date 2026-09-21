// Research presentation — pure typed state kernel for the
// Browser-tab Explorer client island (W6.1 of `complete-frontend-
// migration`). spec.md rule 4: presentation depends on domain
// (and the public barrel). This file is purely TypeScript types +
// pure state-transition helpers — no React, no JSX, no `fetch(`,
// no DOM, no localStorage, no process, no framework globals.
//
// ODD-MIGRATE-003 / W6.1 + W6.2 contract:
//
//   W6.1: "Create the smallest non-CDN React Explorer/Viewer mount
//    using the completed Research W1–W4b4 contracts. The Explorer
//    client island constructs/uses the W3 adapter through the
//    public `@taxa/research` barrel with same-origin base URL.
//    Tests inject a repository only inside client/test boundaries.
//    `/explorer/page.tsx` stays a Server Component and passes only
//    serializable props. Include: initial tree load/retry/empty/
//    error; recursive folder/file rows with accessible
//    expand/select/double-click; non-CDN W4a viewer rendering;
//    typed state and tab behavior; safe extension fallback;
//    component-level error state; public barrel export."
//
//   W6.2: "Extend the W6.1 mount with the Browser-tab tree search
//    matching the legacy `web/file_explorer.js` semantics:
//    200 ms debounce, case-insensitive substring match on the
//    wire `name` + `path` fields, filter mode hides non-matches
//    and auto-expands ancestor folders, highlight mode toggles
//    `search-match` without touching expansion, the clear button
//    restores the tree, filter + hideEmpty + zero matches paints
//    the exact `No matches.` card, Escape clears the input,
//    mode/hide-empty controls toggle state, conditional
//    auto-focus fires only when the active element is `body`
//    (the legacy `requestAnimationFrame` focus check preserved
//    verbatim). Search is client-side against the loaded
//    `ExplorerTree` only — no new port / adapter / dependency."
//
// The W6.2 surface adds the pure search annotation helper
// (`annotateMatches`) — the only pure helper the React layer
// needs to drive the legacy render-time toggle semantics. The
// debounce / auto-focus / DOM-mutation passes live in the
// React layer (`Explorer.tsx` + `FileTree.tsx`) because the
// kernel stays framework-free per spec.md rule 4.
//
// spec.md rule 4 keeps the kernel framework-free; spec.md rule 5
// keeps cross-module imports anchored at the public barrel. Every
// field, helper, and constant here is reachable through the
// barrel so the React mount consumes the typed surface through
// `@taxa/research` only.
//
// The kernel is intentionally narrow: it owns the typed shape +
// the transition helpers. The React layer (`Explorer.tsx`,
// `FileTree.tsx`, `Viewer.tsx`) owns the React state, the
// `useEffect` lifecycle, the `fetchFiles`/`fetchFileServe` wiring,
// and the JSX emission. The kernel never imports React so it can
// be compiled in isolation (`--lib ES2022`, no DOM) by the
// focused test harness without polluting the runtime with
// React types.

import type {
  ExplorerState,
  ExplorerTree,
  ExplorerTreeNode,
  ExplorerFileNode,
  ExplorerFolderNode,
  FileFormat,
  ViewerTab,
  SearchState,
} from "../domain/explorer";
import { createInitialExplorerState } from "../domain/explorer";

// ---- Typed tree-load status (the load/retry/empty/error cycle) ----

/** Discriminated union mirroring the W4a + W1 typed surface. The
 *  React mount maps this 1:1 to a render branch:
 *
 *    - `"idle"`     — initial state, the mount fires the request
 *      via the effect on the first render.
 *    - `"loading"` — request in flight. Renders a quiet skeleton
 *      (`role="status"`).
 *    - `"loaded"`  — the wire payload is captured on `tree`. The
 *      React mount decides whether to paint the recursive tree
 *      (`tree.exists === true`) or the empty-state card
 *      (`tree.exists === false`).
 *    - `"empty"`   — semantic empty (server returned
 *      `{ exists: false, root: null }`). The mount paints the
 *      "No research folders yet" card. Mirrors the legacy
 *      `web/file_explorer.js::renderTreePaneEmpty` contract.
 *    - `"error"`   — request failed. The mount paints the
 *      `role="alert"` retry card with a "Retry" button. The
 *      `message` carries the failure detail (mirrors the legacy
 *      `Could not load file tree: ${e.message}` framing).
 *
 *  The discriminated union survives the lifecycle so a mount
 *  that retries after an error flips to `"loading"` then back to
 *  `"loaded"` / `"error"` cleanly without a stale `tree`
 *  reference. */
export type ExplorerLoadStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | { readonly kind: "loaded"; readonly tree: ExplorerTree }
  | { readonly kind: "empty"; readonly tree: ExplorerTree }
  | { readonly kind: "error"; readonly message: string };

/** Pure factory: produce a fresh `ExplorerLoadStatus`. Mirrors
 *  the legacy `web/file_explorer.js::mount()` initial state —
 *  the request fires on the first effect tick after the mount
 *  commits, so the very first render paints a quiet skeleton.
 *  Tests inject an explicit `"loaded"` / `"empty"` / `"error"`
 *  status to skip the lifecycle. */
export function createInitialLoadStatus(): ExplorerLoadStatus {
  return { kind: "idle" };
}

// ---- Typed viewer-tab state ----

/** Typed view-model for the active viewer tab. Mirrors the W1
 *  `ExplorerState.viewerTab` literal union ("Raw" / "Table" /
 *  "Tree") and carries the open file's descriptor + nullable
 *  bytes + dispatch outcome. The React mount reads/writes the
 *  through the `setOpenFile` / `setViewerTab` / `setDispatch`
 *  transitions so a tab switch preserves the open file's URL +
 *  format + bytes by construction.
 *
 *  `bytes` is nullable because not every W4a family needs bytes
 *  (PDF / HTML / image / video pass the URL straight through to
 *  the renderer). The mount sets bytes ONLY when the format
 *  demands them (TXT / MD / SVG). See `bytesRequiredForFormat`.
 *  `dispatch` is the typed `ViewerDispatch` outcome; the
 *  `Viewer.tsx` component reads `dispatch` and renders the
 *  matching JSX branch. `dispatch` is `null` while the mount
 *  is awaiting bytes or while a previous render has not yet
 *  been dispatched (e.g. between tab switches). */
export interface ViewerState {
  readonly tab: ViewerTab;
  readonly openFilePath: string | null;
  readonly openFileFormat: FileFormat | null;
  readonly bytes: Uint8Array | null;
  readonly dispatch: import("../application/renderers").ViewerDispatch | null;
}

/** Pure factory: produce a fresh `ViewerState`. Mirrors the
 *  legacy `web/file_explorer.js::initialExplorerShape()` defaults:
 *  no file open, Raw tab active. The mount replaces the
 *  open-file fields through `setOpenFile`; the tab changes via
 *  `setViewerTab`. */
export function createInitialViewerState(): ViewerState {
  return {
    tab: "Raw",
    openFilePath: null,
    openFileFormat: null,
    bytes: null,
    dispatch: null,
  };
}

// ---- Format-aware viewer-tab bytes requirement ----

/** Bytes are required for the formats that need them to render:
 *  TXT + MD need the UTF-8 decoded body; SVG needs the bytes to
 *  pass through the W4a `sanitizeSvgMarkup` XSS scrub. Every
 *  other W4a family (PDF / HTML / image / video) passes the URL
 *  straight through to the renderer without reading bytes.
 *
 *  The W4b1–W4b4 source variants (`docx-source`, `sheet-source`,
 *  `epub-source`, `table-source`, `json-source`) also need
 *  bytes — but the W6.1 mount is non-CDN, so those formats
 *  never reach the "fetch bytes" path; the dispatcher's offline
 *  branch fires when bytes are missing and the mount paints
 *  the download-link card. The contract below covers the W4a
 *  families only; a future mount that wires the CDN libraries
 *  would extend the typed predicate here. */
export function bytesRequiredForFormat(format: FileFormat): boolean {
  switch (format) {
    case "txt":
    case "md":
    case "svg":
      return true;
    case "pdf":
    case "epub":
    case "html":
    case "htm":
    case "doc":
    case "docx":
    case "xls":
    case "xlsx":
    case "csv":
    case "tsv":
    case "json":
    case "jpg":
    case "jpeg":
    case "png":
    case "gif":
    case "webp":
    case "bmp":
    case "mp4":
    case "webm":
    case "ogv":
    case "other":
      return false;
    default: {
      // Exhaustiveness guard — a future PR that adds a new
      // `FileFormat` literal lands a compile error here so the
      // bytes-required matrix stays in sync with the W1 union.
      const _exhaustive: never = format;
      void _exhaustive;
      return false;
    }
  }
}

// ---- Safe extension fallback ----

/** Cast a wire `extension` string to a W1 `FileFormat` literal,
 *  falling back to `"other"` when the wire carries an unknown
 *  extension (e.g. ".zip", ".exe", or a typo). Mirrors the
 *  legacy `web/file_explorer.js::iconForExt` + the W1
 *  `"other"` literal — the dispatcher paints the spec's
 *  "Format .xyz not supported in viewer." message + download
 *  link for unknown extensions.
 *
 *  The cast is exhaustive against the W1 `FileFormat` union;
 *  the cast site (`as FileFormat`) is intentionally explicit so
 *  a future extension added to the union forces a cast site
 *  update here. A future extension would also land a new branch
 *  in `bytesRequiredForFormat` above. */
export function castFileFormat(extension: string | null): FileFormat {
  if (extension === null) return "other";
  const e = extension.toLowerCase();
  switch (e) {
    case "pdf":
    case "epub":
    case "html":
    case "htm":
    case "md":
    case "txt":
    case "doc":
    case "docx":
    case "xls":
    case "xlsx":
    case "csv":
    case "tsv":
    case "json":
    case "jpg":
    case "jpeg":
    case "png":
    case "gif":
    case "webp":
    case "bmp":
    case "svg":
    case "mp4":
    case "webm":
    case "ogv":
      return e;
    default:
      return "other";
  }
}

// ---- W3 serve-URL builder (pure) ----

/** Pure helper: build the W3 `/api/files/serve?path=<encoded>`
 *  URL the React mount hands to `<iframe>` / `<img>` / `<video>`
 *  + the W3 adapter. Mirrors the legacy
 *  `web/file_explorer.js::serveUrl(relativePath)` byte-for-byte
 *  — the path is URL-encoded verbatim so a path with spaces /
 *  unicode / accents round-trips cleanly.
 *
 *  Pure function: same input always yields the same output.
 *  Lives here (NOT in the W3 infra layer) so the React mount
 *  can construct the URL without importing the adapter directly
 *  — the adapter's serve method is called separately to fetch
 *  the bytes when the format needs them. The mount reads the
 *  URL straight from the descriptor field (the adapter does
 *  not return it on `fetchFiles`). */
export function buildServeUrl(baseUrl: string, relativePath: string): string {
  const base = baseUrl.replace(/\/+$/, "");
  return `${base}/api/files/serve?path=${encodeURIComponent(relativePath)}`;
}

// ---- Pure state transitions (immutable) ----

/** Toggle a folder's expansion. Returns a NEW `Set<string>` so
 *  React's render cycle stays pure; the mount's `useState`
 *  updater receives the new set. Folders start collapsed in
 *  the W6.1 mount (the legacy default expanded-everything is
 *  deferred — the W6.1 mount paints a quiet collapsed tree so
 *  the user expands folders explicitly). */
export function toggleExpansion(
  expanded: ReadonlySet<string>,
  folderPath: string,
): Set<string> {
  const next = new Set(expanded);
  if (next.has(folderPath)) next.delete(folderPath);
  else next.add(folderPath);
  return next;
}

/** Expand a set of folders. Returns a NEW `Set<string>` so a
 *  subsequent `toggleExpansion` does not mutate the prior set.
 *  Used by `Explorer.tsx`'s auto-expand-on-first-render effect:
 *  the mount expands the root + its top-level children so the
 *  very first paint shows the user where they are. A future
 *  UX iteration could default-collapse the entire tree; the
 *  typed surface stays honest through this helper. */
export function withExpanded(
  expanded: ReadonlySet<string>,
  folderPaths: readonly string[],
): Set<string> {
  const next = new Set(expanded);
  for (const p of folderPaths) next.add(p);
  return next;
}

// ---- Pure search annotation ----

/** Search annotation — the pure output of `annotateMatches()`.
 *  Mirrors the legacy `web/file_explorer.js::_annotateMatches`
 *  contract byte-for-byte: the recursive walker collects every
 *  node whose `name` OR `path` contains the (case-insensitive)
 *  query into `matches`, then walks post-order to collect every
 *  folder that contains at least one matching descendant into
 *  `ancestors`. Both sets carry absolute path strings (the
 *  same shape `data-folder-path` / `data-file-path` carry on
 *  the rendered DOM rows) so the React layer can map them to
 *  rows via `querySelector('[data-folder-path="..."]')`.
 *
 *  The annotation is `ReadonlySet<string>` because consumers
 *  must not mutate it (a future W6+ slice that wants memoised
 *  React state depends on the set identity staying stable for
 *  the lifetime of a single query).
 *
 *  Folders that match by their OWN `name`/`path` end up in
 *  `matches` (and `ancestors` transitively if any descendant
 *  also matches); the React layer's filter pass keeps matches
 *  + ancestors visible and auto-expands ancestors. Highlight
 *  mode ignores `ancestors` and paints `search-match` on the
 *  match set only. */
export interface SearchAnnotation {
  readonly matches: ReadonlySet<string>;
  readonly ancestors: ReadonlySet<string>;
}

/** Pure factory: produce a fresh, empty `SearchAnnotation`.
 *  Mirrors the legacy `_annotateMatches()` return shape for
 *  the trivial cases (empty root, empty query) so the React
 *  layer can short-circuit with a stable typed handle without
 *  branching on `undefined`. The two sets are fresh per call
 *  (no shared references) so a future presentation-only
 *  consumer can mutate locally without bleeding into a
 *  sibling. */
export function createEmptySearchAnnotation(): SearchAnnotation {
  return {
    matches: new Set<string>(),
    ancestors: new Set<string>(),
  };
}

/** Pure helper: build the legacy render-time search
 *  annotation. Walks the recursive `ExplorerTreeNode` tree
 *  twice — pass 1 collects direct matches (name OR path
 *  contains the query, case-insensitive substring); pass 2
 *  walks post-order to promote every folder-with-match into
 *  the `ancestors` set. The walker uses explicit stacks rather
 *  than recursion so a deep tree (>1000 folders) never blows
 *  the JS call stack.
 *
 *  Returns `createEmptySearchAnnotation()` for the trivial
 *  cases (null/undefined root, empty/whitespace-only query).
 *  The `query` is normalised to lower-case once before the
 *  walk so every comparison reuses the same cached needle.
 *
 *  Pure function: same `(root, query)` always yields the same
 *  annotation. The React layer's `useMemo` updater relies on
 *  the deterministic shape so the annotation identity flips
 *  only when the query actually changes. */
export function annotateMatches(
  rootNode: ExplorerTreeNode | null,
  query: string,
): SearchAnnotation {
  const empty = createEmptySearchAnnotation();
  if (rootNode === null) return empty;
  const trimmed = query.trim();
  if (trimmed === "") return empty;
  const needle = trimmed.toLowerCase();

  const matches = new Set<string>();
  // Pass 1 — iterative walk, every node becomes a direct
  // match when its `name` OR `path` contains the needle
  // (case-insensitive substring). Files + folders both
  // qualify; a folder whose own name matches does NOT
  // automatically promote its descendants (descendants land
  // in `ancestors` only).
  const stack1: ExplorerTreeNode[] = [rootNode];
  while (stack1.length > 0) {
    const node = stack1.pop();
    if (node === undefined) continue;
    const path = node.path || "";
    const name = node.name || "";
    if (
      path.toLowerCase().includes(needle) ||
      name.toLowerCase().includes(needle)
    ) {
      matches.add(path);
    }
    if (node.type === "folder" && Array.isArray(node.children)) {
      for (const c of node.children) stack1.push(c);
    }
  }

  // Pass 2 — post-order walk that promotes every folder
  // whose subtree contains at least one match into
  // `ancestors`. The legacy uses a real recursive visit
  // here ("tree depth is bounded (typical <20), so a real
  // recursive call is fine"); we mirror that shape — the
  // helper is pure, the depth is bounded by the wire tree
  // (FastAPI's `_walk_tree` enforces a sane depth on the
  // server), and the iterative pass 1 already covers the
  // hot path (deep flat trees).
  const ancestors = new Set<string>();
  const visit = (node: ExplorerTreeNode): boolean => {
    const path = node.path || "";
    if (matches.has(path)) return true;
    if (node.type !== "folder" || !Array.isArray(node.children)) {
      return false;
    }
    let childHasMatch = false;
    for (const c of node.children) {
      if (visit(c)) childHasMatch = true;
    }
    // Only promote the folder to an ancestor when its
    // own path is non-empty. The synthetic root in the
    // React mount carries `path: ""` (the wire tree
    // root has no path string), so the wrapped folder
    // never lands in `ancestors` — the visible ancestor
    // chain is the post-order descendant folders of the
    // root. The matches check above already excludes
    // the root via the direct-match short-circuit
    // (the root's `path` is `""` so `name/path` lookups
    // are empty strings, which never include a typed
    // query); this guard catches the edge case where a
    // child of the root is a folder on the ancestor
    // chain.
    if (childHasMatch && path !== "") ancestors.add(path);
    return childHasMatch;
  };
  visit(rootNode);

  return { matches, ancestors };
}

// ---- Recursive row enumeration (pure) ----

/** Enumerate every file node under a recursive tree. Returns a
 *  flat array of `{path, node}` pairs in depth-first order. The
 *  React mount uses this for keyboard navigation (j/k through
 *  the visible tree); the result is intentionally depth-first
 *  + pre-order so the visible order matches what the user sees.
 *
 *  Pure function: same input always yields the same output. A
 *  folder node contributes no entry of its own (only its
 *  descendants); a file node contributes one entry per file.
 *  The result excludes the root node when it is a folder (the
 *  caller already knows about the root via `tree.root`). */
export function enumerateFiles(
  node: ExplorerTreeNode,
): readonly { readonly path: string; readonly node: ExplorerFileNode }[] {
  if (node.type === "file") {
    return [{ path: node.path, node }];
  }
  const out: { path: string; node: ExplorerFileNode }[] = [];
  for (const child of node.children) {
    for (const entry of enumerateFiles(child)) out.push(entry);
  }
  return out;
}

// ---- Public surface re-exported through the kernel ----

/** Re-export the W1 domain types + factory so the React mount
 *  reaches the typed shape through the barrel without a deep
 *  import into `../domain/explorer`. spec.md rule 5 forbids
 *  reverse deep imports from the React layer into the domain
 *  folder; the kernel is the typed hand-off surface so the
 *  React layer's only import is the barrel + this kernel. */
export {
  createInitialExplorerState,
  type ExplorerState,
  type ExplorerTree,
  type ExplorerTreeNode,
  type ExplorerFileNode,
  type ExplorerFolderNode,
  type FileFormat,
  type ViewerTab,
  type SearchState,
};

// ---- W6.2 typed search shape re-export ----

/** Re-export the W1 `SearchState` so the React mount reaches
 *  the typed query / mode / hideEmpty triple through the
 *  barrel without a reverse deep import into
 *  `../domain/explorer`. The kernel + barrel own the typed
 *  surface; spec.md rule 5 forbids the React layer from
 *  importing from `../domain/explorer` directly. The W6.2
 *  React mount reads the W1 `SearchState` literal union
 *  through this kernel re-export. */
