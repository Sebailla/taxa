// Typed fetch re-export surface for the taxonomy module (PR 5a.1).
// The application + presentation layers import the typed fetch
// helpers exclusively from this barrel — never from the implementation
// file — so the implementation can be swapped (real backend, mock,
// fixture) without rippling through call sites.

export {
  NetworkError,
  defaultFetch,
  fetchChildren,
  fetchDomains,
  fetchTaxon,
  type FetchLike,
} from "./api";