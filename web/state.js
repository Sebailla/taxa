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
};

export { API, PAGE_SIZE, state };
