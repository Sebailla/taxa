/**
 * Public barrel for the `taxonomy` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/taxonomy` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below
 * (`presentation`, `application`, `domain`, `infrastructure`) are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * PR 5a.1 (Phase 5 capability port, slice 1) ships:
 *   - domain types + source-aware parent-chain walker
 *   - typed fetch* helpers + `NetworkError`
 *   - framework-free application view-model surface
 *
 * The React hook + presentation components land with PR 5a.2/5a.3.
 */

export type {
  BreadcrumbSegment,
  Rank,
  Taxon,
  TaxonRecord,
  TreeSource,
} from "./domain/taxon";

export {
  RANK_ORDER,
  compareRanks,
  isValidRank,
  isValidTaxon,
  isValidTreeSource,
  parentIdOf,
  walkParentChain,
} from "./domain/taxon";

export {
  NetworkError,
  defaultFetch,
  fetchChildren,
  fetchDomains,
  fetchTaxon,
  type FetchLike,
} from "./infrastructure";

export {
  buildBreadcrumb,
  loadTaxonTree,
  type BreadcrumbViewModel,
  type TaxonTreeNode,
} from "./application";