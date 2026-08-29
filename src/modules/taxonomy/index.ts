/**
 * Public barrel for the `taxonomy` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/taxonomy` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below
 * (`presentation`, `application`, `domain`, `infrastructure`) are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * PR 2a (Phase 2 scaffold work unit) ships an empty barrel — the real
 * exports land with the PR 5 capability port (tasks 5.1–5.3):
 *   - `domain/taxon.ts`        → plain TS types + invariants
 *   - `infrastructure/api.ts`   → `fetchTaxon`, `fetchChildren`
 *   - `application/useTaxonTree`, `application/useDetail`
 *   - `presentation/{Tree,DetailPanel,Breadcrumb}/` React components
 *
 * An empty barrel is intentionally a no-op re-export so this file is
 * a valid TypeScript module and `tsc --noEmit` accepts it.
 */
export {};
