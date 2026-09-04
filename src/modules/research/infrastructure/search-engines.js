// Re-export the canonical AC-21 search-engine catalog from
// src/data/search-engines.js so consumers can `import { ... } from
// "@taxa/research"` without reaching into src/data/.

export { SEARCH_ENGINES, CATEGORIES } from "../../../data/search-engines.js";
