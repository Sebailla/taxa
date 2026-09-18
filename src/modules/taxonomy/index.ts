/**
 * Public barrel for the `taxonomy` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/taxonomy` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below
 * (`presentation`, `application`, `domain`, `infrastructure`) are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * PR 5a (Phase 5 infrastructure work unit) ships the typed HTTP
 * adapter re-export. PR 5b adds the application port + readonly
 * view-models. PR 5c slice 1 adds the pure `walkBreadcrumbPath`
 * helper. PR 5c slice 2 adds the `Breadcrumb` presentation React
 * component. Subsequent PR 5 slices add the remaining presentation
 * components.
 *
 * The `infrastructure` layer's error type is re-exported too so
 * consumers can `instanceof`-narrow without a deep import.
 */
export {
  fetchTaxon,
  fetchChildren,
  fetchDomains,
  TaxonomyApiError,
} from "./infrastructure/api";
export type {
  FetchOptions,
  FetchChildrenOptions,
  FetchDomainsOptions,
  TaxonomySource,
} from "./infrastructure/api";

// Application layer — typed port + readonly view-models.
export type { SourceFilter, TaxonomyRepository } from "./application/ports";
export { TAXONOMY_PORT_NAME } from "./application/ports";
export type {
  TaxonNodeViewModel,
  TaxonTreeViewModel,
  TaxonBreadcrumbSegment,
  TaxonDetailViewModel,
} from "./application/view-models";
export { buildTaxonTree, buildTaxonDetail } from "./application/view-models";

// Presentation layer — pure parent-chain walker. Consumers receive
// `walkBreadcrumbPath` so they can pre-compute the focused-taxon's
// ancestor chain outside the React tree (tests, server-side snapshots,
// view-model builders). The React `Breadcrumb` component lands in PR
// 5c slice 2 and will be re-exported here once it ships.
export { walkBreadcrumbPath } from "./presentation/breadcrumb-path";
export type {
  BreadcrumbSegment,
  BreadcrumbSource,
  ParentIdResolver,
} from "./presentation/breadcrumb-path";
export { BREADCRUMB_MAX_HOPS } from "./presentation/breadcrumb-path";

// ODD-VTREE-001 — pure tree-state kernel for the visible taxonomy
// tree. The React `TaxonomyTree` component (ODD-VTREE-002) consumes
// this helper directly; everything here is framework-free.
export {
  EMPTY_TREE_STATE,
  withRoots,
  childIds,
  isExpanded,
  expand,
  collapse,
  toggleExpand,
  attachChildren,
  setLoadStatus,
  loadStatus,
} from "./presentation/tree-state";
export type {
  TreeState,
  NodeLoadStatus,
} from "./presentation/tree-state";

// ODD-VTREE-002 — visible taxonomy tree (client island). Re-exported
// here so cross-module consumers (`src/app/page.tsx`) can mount the
// tree without a deep import. `TreeRow` stays internal to the
// presentation folder — it is not part of the public barrel.
export { default as TaxonomyTree } from "./presentation/TaxonomyTree";
