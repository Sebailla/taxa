// Single shared state object for the whole frontend. Direct mutation is
// allowed — every existing call site reads/writes these fields. No setters,
// no getters, no event bus. Keep this file tiny.

const API = ""; // same-origin (served by FastAPI)
const PAGE_SIZE = 5; // children per tier group before "Load all"

const state = {
  roots: [], // top-level domains returned by /api/domains (CoL only)
  expanded: new Set(), // ids whose direct children are shown
  showAll: new Set(), // "${parentId}::${rank}" — tier groups fully unrolled
  selected: null, // species/subspecies id for the detail panel + URL
  focused: null, // current "position" in the tree (drives the breadcrumb)
  cache: new Map(), // id → { taxon, children: Taxon[] | null }
  extantOnly: true,
  treeSource: "col", // "col" | "worms" — header toggle filter (default CoL)

  // Search
  searchOpen: false,
  searchResults: [],
  searchTimer: null,

  // Detail panel
  detail: null,
  detailOpen: true,
  detailLoading: false,
  // activeTab[taxonId] = tab key. The Búsquedas tab is the default on a
  // fresh selection; explicit tab clicks persist so reopening the same
  // taxon remembers which tab was active.
  activeTab: {},

  // Materialize indicator. Set of taxon ids whose root→taxon folder
  // has been confirmed to exist on disk during THIS session. The set
  // starts empty and grows when the user confirms a materialize modal
  // (the server response includes the new ids, which the modal
  // callback merges here). Children of a confirmed taxon are also
  // marked by the tree's render() so the indicator propagates to the
  // visible sub-tree without needing a fresh backend call per child.
  // The set is session-scoped — a full page reload re-derives the
  // flag from the backend's per-child `research_path_exists` on the
  // next /api/taxon/{id}/children round trip.
  materialized: new Set(),

  // File explorer (Browser tab). Owns the recursive tree fetched via
  // GET /api/taxon/{id}/files plus the currently-opened file + format
  // + viewer-tab state. Selection state (which file/folder row is
  // highlighted in the left tree) lives in DOM-only via data-file-path
  // / data-folder-path attributes — keeping re-renders cheap.
  //
  //   rootTaxonId    number | null   — taxon the tree is rooted at
  //   tree           object | null   — full response from GET /files
  //   openFilePath   string | null   — relative path inside the tree
  //   openFileFormat string | null   — extension of the open file (e.g. "pdf")
  //   viewerTab      "Raw" | "Table" | "Tree" — active right-pane tab
  //
  // Cleared by clearFileExplorer() in nav.js when the user leaves the
  // Browser tab, and reset to its initial shape by file_explorer.js
  // mount(null). See design.md §4 for the full shape rationale.
  explorer: {
    rootTaxonId: null,
    tree: null,
    openFilePath: null,
    openFileFormat: null,
    viewerTab: "Raw",
  },
};

// Exported so other modules (specifically nav.js's clearFileExplorer)
// can reset state.explorer to its initial shape without duplicating
// the literal. Keep in sync with the `explorer` field above.
export function initialExplorerShape() {
  return {
    rootTaxonId: null,
    tree: null,
    openFilePath: null,
    openFileFormat: null,
    viewerTab: "Raw",
  };
}

export { API, PAGE_SIZE, state };
