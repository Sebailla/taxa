// Infrastructure barrel (5b.1 + 5b.4 addendum). Consumers import
// from `@taxa/research`. PR 5b.4 ADDS the materialize-preview + folder
// creation typed fetch helpers (no removal / reorder of predecessors).

export {
  NetworkError, defaultFetch, fetchFiles, fetchServe,
  loadScriptOnce, CDN_LIBRARIES, CDN_URLS, type FetchLike,
  fetchMaterializePreview, createMaterializeFolder,
  type MaterializePreviewEnvelope,
} from "./api";
export { SEARCH_ENGINES, CATEGORIES } from "./search-engines.js";
