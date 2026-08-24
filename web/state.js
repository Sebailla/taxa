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
};

export { API, PAGE_SIZE, state };
