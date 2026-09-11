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
 * adapter re-export. PR 5b (this slice) adds the application
 * port + readonly view-models. Subsequent PR 5 slices add the
 * presentation React components.
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
