/**
 * Public barrel for the `research` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/research` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * PR 2a (Phase 2 scaffold work unit) ships an empty barrel — the real
 * exports land with the PR 5 capability port (tasks 5.4–5.6):
 *   - `domain/viewer.ts`           → ViewerTab, FileFormat, viewer types
 *   - `infrastructure/api.ts`      → fetchFiles, fetchFileServe
 *   - `infrastructure/search-engines.js` → relocated web/search_urls.js
 *                                       (AC-21 contract preserved)
 *   - `application/useExplorer`, `application/useViewer`
 *   - `presentation/{Explorer,Viewer}/` React components
 *
 * An empty barrel is intentionally a no-op re-export so this file is
 * a valid TypeScript module and `tsc --noEmit` accepts it.
 */
export * from "./domain";
export * from "./infrastructure";
