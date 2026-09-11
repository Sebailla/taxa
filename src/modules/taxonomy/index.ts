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
 * adapter re-export. Subsequent PR 5 slices add:
 *   - `application/useTaxonTree`, `application/useDetail`
 *   - `presentation/{Tree,DetailPanel,Breadcrumb}/` React components
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
