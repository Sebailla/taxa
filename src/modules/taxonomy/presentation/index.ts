// Presentation-layer barrel for the taxonomy module
// (PR 5a.2 + 5a.3 + 5a.4 + PR 5b.4 promotion cleanup).
//
// 5b.4 removes the obsolete taxonomy TabStrip primitive (promoted to
// the design-system module verbatim) and the inert placeholders for
// the Search/Folder tab bodies (replaced by the real
// SearchTab / FolderTab surfaces from the research module). The
// barrel drops their re-exports so the public surface stays in
// lock-step with the files on disk.
export { Breadcrumb, type BreadcrumbProps } from "./Breadcrumb";
export { DetailPanel, type DetailPanelProps } from "./DetailPanel";
export { Kebab, type KebabProps } from "./Kebab";
export { KebabStub, type KebabStubProps } from "./KebabStub";
export { OverviewTab, type OverviewTabProps } from "./OverviewTab";
export {
  TaxonDetailPlaceholder, type TaxonDetailPlaceholderProps,
} from "./TaxonDetailPlaceholder";
export { Tree, type TreeProps } from "./Tree";
export { useKebab, type UseKebabResult } from "./useKebab";
