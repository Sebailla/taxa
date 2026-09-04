// Infrastructure barrel (5b.1). Consumers import from `@taxa/research`.
export {
  NetworkError, defaultFetch, fetchFiles, fetchServe,
  loadScriptOnce, CDN_LIBRARIES, CDN_URLS, type FetchLike,
} from "./api";
export { SEARCH_ENGINES, CATEGORIES } from "./search-engines.js";
