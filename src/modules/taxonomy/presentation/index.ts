// Presentation-layer barrel for the taxonomy module (PR 5a.2 + 5a.3).
// 5a.3 EXTENDS the surface with `DetailPanel` + `OverviewTab` + the
// local `TabStrip` primitive plus inert `SearchTabStub` / `FolderTabStub`
// (real bodies land in PR 5b; force-Search wiring lands in PR 5a.4).
export { Breadcrumb, type BreadcrumbProps } from "./Breadcrumb";
export { DetailPanel, type DetailPanelProps } from "./DetailPanel";
export { FolderTabStub, type FolderTabStubProps } from "./FolderTabStub";
export { KebabStub, type KebabStubProps } from "./KebabStub";
export { OverviewTab, type OverviewTabProps } from "./OverviewTab";
export { SearchTabStub, type SearchTabStubProps } from "./SearchTabStub";
export { TabStrip, type TabDefinition, type TabStripProps } from "./TabStrip";
export {
  TaxonDetailPlaceholder, type TaxonDetailPlaceholderProps,
} from "./TaxonDetailPlaceholder";
export { Tree, type TreeProps } from "./Tree";