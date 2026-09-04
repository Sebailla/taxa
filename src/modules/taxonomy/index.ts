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
 * PR 5a.2 EXTENDS the public surface with:
 *   - the React adapter hook (`useTaxonTree` + state types)
 *   - the presentation layer (Tree, Breadcrumb, KebabStub,
 *     TaxonDetailPlaceholder)
 *
 * PR 5a.3 EXTENDS the public surface with:
 *   - `DetailPanel` + `OverviewTab` + local `TabStrip`
 *   - inert `SearchTabStub` / `FolderTabStub` (bodies land in 5b)
 *
 * PR 5a.4 EXTENDS the public surface with:
 *   - the real per-row `Kebab` menu (Search online) + `useKebab`
 *     open/close state hook
 *   - the force-Search contract on `DetailPanel` (the kebab's
 *     `Search online` callback forces the Search tab active even
 *     for top-level taxa)
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

export {
  useTaxonTree,
  type TaxonTreeHookState,
  type UseTaxonTreeOptions,
} from "./application";

export {
  Breadcrumb,
  type BreadcrumbProps,
  DetailPanel,
  type DetailPanelProps,
  FolderTabStub,
  type FolderTabStubProps,
  Kebab,
  type KebabProps,
  KebabStub,
  type KebabStubProps,
  OverviewTab,
  type OverviewTabProps,
  SearchTabStub,
  type SearchTabStubProps,
  TabStrip,
  type TabDefinition,
  type TabStripProps,
  TaxonDetailPlaceholder,
  type TaxonDetailPlaceholderProps,
  Tree,
  type TreeProps,
  useKebab,
  type UseKebabResult,
} from "./presentation";