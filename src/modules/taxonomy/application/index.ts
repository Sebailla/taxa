// Application-layer re-export surface for the taxonomy module (PR 5a.1).
// The presentation layer imports view models and (in 5a.2) the React
// hook exclusively from this barrel.

export {
  buildBreadcrumb,
  loadTaxonTree,
  type BreadcrumbViewModel,
  type TaxonTreeNode,
} from "./useTaxonTree";