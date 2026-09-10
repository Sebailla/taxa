// Application-layer re-export surface for the taxonomy module
// (PR 5a.1 + 5a.2). The presentation layer imports view models and
// (in 5a.2) the React hook exclusively from this barrel. The hook
// lives in its own file (`useTaxonTreeHook.ts`) so the framework-
// free view-model surface in `useTaxonTree.ts` stays byte-identical
// with PR 5a.1 — the predecessor foundation test enforces this.

export {
  buildBreadcrumb,
  loadTaxonTree,
  type BreadcrumbViewModel,
  type TaxonTreeNode,
} from "./useTaxonTree";

export {
  useTaxonTree,
  type TaxonTreeHookState,
  type UseTaxonTreeOptions,
} from "./useTaxonTreeHook";