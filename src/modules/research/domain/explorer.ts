// Research domain — canonical pure-typed contract for the Browser-tab
// file explorer. W1 of the complete-frontend-migration
// (`odd/tasks/complete-frontend-migration.md::ODD-MIGRATE-002`).
//
// spec.md rule 4: domain stays free of presentation, application,
// browser, HTTP, framework, or infrastructure. This file is purely
// TypeScript types + one pure factory function — no React, no Next,
// no FastAPI, no fetch, no localStorage, no document, no window, no
// process. Every later explorer work unit (W2 ports, W3 search, W4
// renderers, W5/W6 React mount) builds on this surface without
// modifying it.
//
// The shape mirrors `web/state.js::state.explorer` and
// `web/state.js::initialExplorerShape()` byte-for-byte so the React
// cutover can read/write the same fields under the same types — no
// coercion, no surprise renames, no silent drops. The legacy
// `web/file_explorer.js::openFile` tab strip (Raw / Table / Tree) and
// the `web/state.js::state.explorer.search` semantics (mode
// "filter" / "highlight", hideEmpty boolean) survive the migration
// as typed literals instead of free-form strings.
//
// ODD-MIGRATE-002 W1 contract (verbatim from the work-unit file):
//
//   "Introduce only the pure typed Research domain contract needed by
//    later explorer work: canonical ExplorerState, ViewerTab,
//    FileFormat, SearchState and initial state creation, matching
//    documented legacy semantics (query: "", filter mode, hide-empty
//    true; viewer tabs Raw/Table/Tree). Keep it framework- and
//    I/O-free. Do not add API ports, renderers, React components,
//    browser-state keys, CSS, or integration imports."
//
// That contract is the file's only job. Future work units extend it
// (e.g. W2 ports) but never reshape it: dropping a field or
// changing a literal would silently regress every consumer that
// reads the typed surface.
//
// ODD-MIGRATE-002 W1 source-of-truth mapping:
//
//   Field             Legacy oracle                              File
//   ----------------  ----------------------------------------- ----------------------------
//   rootTaxonId       web/state.js::state.explorer.rootTaxonId   ExplorerState.rootTaxonId
//   tree              web/state.js::state.explorer.tree         ExplorerState.tree (ExplorerTree)
//   openFilePath      web/state.js::state.explorer.openFilePath ExplorerState.openFilePath
//   openFileFormat    web/state.js::state.explorer.openFileFormat
//                                                            ExplorerState.openFileFormat (FileFormat)
//   viewerTab         web/state.js::state.explorer.viewerTab   ExplorerState.viewerTab (ViewerTab)
//   search.query      web/state.js::state.explorer.search.query
//                                                            SearchState.query
//   search.mode       web/state.js::state.explorer.search.mode
//                                                            SearchState.mode
//   search.hideEmpty  web/state.js::state.explorer.search.hideEmpty
//                                                            SearchState.hideEmpty

/** Viewer tab literal — the three tabs the legacy
 *  `web/file_explorer.js::openFile` tab strip wires up in that exact
 *  order. The literal is closed: the legacy strip exposes no fourth
 *  tab, and `openspec/specs/research/spec.md` "Multi-format file
 *  viewer" + "Table viewer tab" + "Tree viewer tab" requirements
 *  enumerate exactly these three. A future PR that adds a fourth
 *  tab is a spec change and must extend this union in lock-step
 *  with the tab strip + the spec table.
 *
 *  Case-sensitive `"Raw"` — the legacy button text capitalises only
 *  the first letter (`web/file_explorer.js` paints `el("button", …,
 *  "Raw")` etc.). Coercing to lowercase would silently mismatch the
 *  React cutover's tab buttons. */
export type ViewerTab = "Raw" | "Table" | "Tree";

/** File format identifier — the lowercase file extension (without
 *  the leading dot) the legacy `state.explorer.openFileFormat`
 *  carries. The closed union names every extension the legacy
 *  `web/file_viewer.js` renderer table dispatches on plus a
 *  fallback for the "Format .xyz not supported in viewer" contract:
 *
 *    - Document renderer family (`renderPdf`, `renderEpub`)
 *    - Plain / marked-up text family (`renderHtml`, `renderTxt`,
 *      `renderMarkdown`)
 *    - Legacy MS Word + OOXML family (`renderDoc`, `renderDocx`,
 *      `renderLegacyDoc`)
 *    - Spreadsheet family (`renderXls`, `renderXlsx`)
 *    - Tabular data (`renderTable` for .csv / .tsv)
 *    - JSON (`renderTree` for .json)
 *    - Image family (`renderImage`)
 *    - Video family (`renderVideo`)
 *    - The string literal `"other"` covers the fallback / unknown
 *      extension path (legacy `renderUnsupported`)
 *
 *  The union is intentionally closed: the legacy renderers
 *  dispatch a tree-shaped switch, so an unknown extension lands on
 *  the `other` arm and paints the unsupported-format message +
 *  download link. A future PR that adds an extension must extend
 *  this union AND the renderer's dispatch in lock-step.
 *
 *  Why the union is wider than the nine "supported" extensions the
 *  spec table enumerates: the legacy `state.explorer.openFileFormat`
 *  still carries e.g. `.zip` after a user double-clicks an
 *  unsupported file (the open-file handler records the format
 *  before dispatching the renderer). The union reflects what the
 *  legacy state can hold, not what the renderers can paint. */
export type FileFormat =
  // Document renderer family.
  | "pdf"
  | "epub"
  // Plain / marked-up text family.
  | "html"
  | "htm"
  | "md"
  | "txt"
  // Legacy MS Word + OOXML family.
  | "doc"
  | "docx"
  // Spreadsheet family.
  | "xls"
  | "xlsx"
  // Tabular data (Table tab renderer).
  | "csv"
  | "tsv"
  // JSON (Tree tab renderer).
  | "json"
  // Image family.
  | "jpg"
  | "jpeg"
  | "png"
  | "gif"
  | "webp"
  | "bmp"
  | "svg"
  // Video family.
  | "mp4"
  | "webm"
  | "ogv"
  // Fallback for unknown / unsupported extensions (legacy
  // `renderUnsupported` — keeps the typed surface honest when the
  // user double-clicks a `.zip` or `.exe`).
  | "other";

/** Search state — the legacy `web/state.js::state.explorer.search`
 *  shape, typed verbatim so the React tree-search behaviour
 *  (`openspec/specs/research/spec.md` "Tree search") can read/write
 *  the same fields without coercion.
 *
 *    - `query`     string — debounced input value, `""` when idle.
 *      The 200 ms debounce lives in the wiring layer (W3 search),
 *      NOT in this contract — the domain is pure.
 *    - `mode`      `"filter" | "highlight"` — filter hides
 *      non-matches (default); highlight paints matches. See
 *      `web/file_explorer.js::runSearch` for the dispatch.
 *    - `hideEmpty` boolean — filter-only: hide folders with no
 *      descendant matches. Default `true`. Highlight mode
 *      ignores the flag (the contract keeps it on the state so a
 *      pre-toggle before switching to filter survives).
 *
 *  Session-scoped only — intentionally NOT in `localStorage`. The
 *  research folders may contain sensitive taxon names, and the tree
 *  itself is re-fetched on reload, so a stale query against a
 *  missing tree would produce a confusing empty result. The
 *  `localStorage` taxonomy lives in `@taxa/browser-state`; the
 *  Research module deliberately has no browser-state keys (W1
 *  contract — "Do not add … browser-state keys").
 */
export interface SearchState {
  readonly query: string;
  readonly mode: "filter" | "highlight";
  readonly hideEmpty: boolean;
}

/** Folder node in the research tree (mirrors
 *  `api/server.py::_walk_tree` folder branch). Folders start
 *  expanded in the legacy `web/file_explorer.js::renderFolderRow`
 *  — `aria-expanded="true"` is the legacy default — but the DOM
 *  state is the consumer's responsibility; this contract only
 *  names the typed shape.
 *
 *  `children` is recursive — the FastAPI tree JSON inlines the
 *  full subtree in one response (no lazy children, no N+1 round
 *  trips — see `openspec/specs/research/spec.md` "Recursive
 *  directory listing endpoint"). The shape is therefore an
 *  unfolded recursive type, not a "load children on demand"
 *  reference. */
export interface ExplorerFolderNode {
  readonly name: string;
  readonly path: string;
  readonly type: "folder";
  readonly children: readonly ExplorerTreeNode[];
}

/** File node in the research tree (mirrors
 *  `api/server.py::_walk_tree` file branch). `size` is the wire
 *  byte count (Python `Path.stat().st_size`); `modified` is the
 *  ISO timestamp the wire emits (`datetime.fromtimestamp(st_mtime)
 *  .isoformat(timespec="seconds")`). Both are typed as `number` /
 *  `string` to mirror the wire — no coercion, no Date wrapper.
 *
 *  `extension` is the lowercase extension without the leading dot
 *  (e.g. `"pdf"`, `"epub"`, `"csv"`) — same shape the legacy
 *  `state.explorer.openFileFormat` reads. A `FileFormat` cast
 *  happens at the rendering boundary (W4 / W6), NOT here, so the
 *  typed contract accepts any string the wire can carry (a wire
 *  `null` projects as `null` — coercing to `"other"` would
 *  silently swallow missing fields). */
export interface ExplorerFileNode {
  readonly name: string;
  readonly path: string;
  readonly type: "file";
  readonly extension: string;
  readonly size: number;
  readonly modified: string;
}

/** Recursive tree node — discriminated union over the `type`
 *  field. Mirrors the FastAPI `_walk_tree` shape exactly (folder
 *  vs file). `ExplorerFolderNode` and `ExplorerFileNode` are
 *  externally distinguishable by `type`, so a React reducer /
 *  switch can dispatch on the discriminator without an extra
 *  guard. */
export type ExplorerTreeNode = ExplorerFolderNode | ExplorerFileNode;

/** Research tree payload — the JSON body of
 *  `GET /api/files` and `GET /api/taxon/{id}/files`. Mirrors the
 *  server's response verbatim:
 *
 *    - `exists` — `true` when the research root is a directory on
 *      disk, `false` otherwise (the server returns 200 with
 *      `exists: false` rather than 404 so the frontend can render
 *      the empty-state without an error branch).
 *    - `root` — the recursive tree, `null` when `exists` is
 *      `false`.
 *    - `filesystem_path` — the server-resolved absolute path of
 *      the research root on disk. Surfaces as `string` (the
 *      server always populates it; consumers may treat it as
 *      informational).
 *
 *  The contract is the wire shape — no derived fields, no
 *  convenience projections. Coercion / derivation belongs to the
 *  infra layer (W2 ports) so the domain stays framework-free. */
export interface ExplorerTree {
  readonly exists: boolean;
  readonly root: ExplorerTreeNode | null;
  readonly filesystem_path: string;
}

/** Explorer state — the legacy `web/state.js::state.explorer`
 *  shape, typed so the React cutover can read/write the same
 *  fields without runtime coercion. Every field mirrors the
 *  legacy contract verbatim:
 *
 *    - `rootTaxonId` — the taxon the explorer is rooted at. Kept
 *      around for future "highlight this taxon's folder"
 *      affordances; the Browser tab itself always fetches the
 *      global Research tree via `GET /api/files` regardless of
 *      the selected taxon (see `web/file_explorer.js::mount`).
 *    - `tree` — the fetched tree payload (or `null` until the
 *      mount fires the request).
 *    - `openFilePath` — the relative path of the open file (or
 *      `null` when no file is open).
 *    - `openFileFormat` — the open file's extension (or `null`
 *      when no file is open).
 *    - `viewerTab` — the active viewer tab (Raw / Table / Tree).
 *    - `search` — the tree-search state.
 *
 *  The interface is the W1 contract: every field is `readonly`
 *  so a future reducer / store can rely on immutable updates
 *  (W6 React mount). Mutation belongs to the application layer
 *  (W2 ports / store), NOT here — the domain stays pure. */
export interface ExplorerState {
  readonly rootTaxonId: number | null;
  readonly tree: ExplorerTree | null;
  readonly openFilePath: string | null;
  readonly openFileFormat: FileFormat | null;
  readonly viewerTab: ViewerTab;
  readonly search: SearchState;
}

/** Factory: produce a fresh W1-initial ExplorerState.
 *
 *  The returned object mirrors `web/state.js::initialExplorerShape()`
 *  byte-for-byte — every resetable field starts at `null`, viewerTab
 *  defaults to `"Raw"`, search defaults to
 *  `{ query: "", mode: "filter", hideEmpty: true }`. The legacy
 *  `web/file_explorer.js::mount()` consumes this shape to reset
 *  state on every remount; W6's React mount MUST produce the
 *  exact same fresh state so a React-driven remount matches the
 *  legacy oracle to the byte.
 *
 *  Each call returns a NEW object (no shared references) so
 *  mutating one initial state never bleeds into a sibling — the
 *  legacy `initialExplorerShape()` returns a fresh literal on
 *  every call. The runtime contract is verified by
 *  `tests/test_research_domain.py::test_compiled_module_passes_runtime_contract`. */
export function createInitialExplorerState(): ExplorerState {
  return {
    rootTaxonId: null,
    tree: null,
    openFilePath: null,
    openFileFormat: null,
    viewerTab: "Raw",
    search: {
      query: "",
      mode: "filter",
      hideEmpty: true,
    },
  };
}