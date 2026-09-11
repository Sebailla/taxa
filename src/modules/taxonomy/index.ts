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
  TaxonomyApiError,
} from "./infrastructure/api.js";
export type {
  FetchOptions,
  FetchChildrenOptions,
} from "./infrastructure/api.js";

// Application layer — typed port + readonly view-models.
export type { SourceFilter, TaxonomyRepository } from "./application/ports.js";
export { TAXONOMY_PORT_NAME } from "./application/ports.js";
export type {
  TaxonNodeViewModel,
  TaxonTreeViewModel,
  TaxonBreadcrumbSegment,
  TaxonDetailViewModel,
} from "./application/view-models.js";
export { buildTaxonTree, buildTaxonDetail } from "./application/view-models.js";

// Presentation layer — pure parent-chain walker. Consumers receive
// `walkBreadcrumbPath` so they can pre-compute the focused-taxon's
// ancestor chain outside the React tree (tests, server-side snapshots,
// view-model builders). The React `Breadcrumb` component lands in PR
// 5c slice 2 and will be re-exported here once it ships.
export { walkBreadcrumbPath } from "./presentation/breadcrumb-path.js";
export type {
  BreadcrumbSegment,
  BreadcrumbSource,
  ParentIdResolver,
} from "./presentation/breadcrumb-path.js";
export { BREADCRUMB_MAX_HOPS } from "./presentation/breadcrumb-path.js";
