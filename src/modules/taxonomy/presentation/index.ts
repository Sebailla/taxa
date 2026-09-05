// Presentation-layer barrel for the taxonomy module
// (PR 5a.2 + 5a.3 + 5a.4).
//
// 5a.4 EXTENDS the surface with the real `Kebab` (per-row menu
// with `Search online`) + `useKebab` (local open/close state hook).
// `KebabStub` (5a.2 inert glyph) stays exported for backward
// compatibility with anything that still references it; the page
// mounts the real `Kebab` exclusively. Real Search/Folder bodies
// land in PR 5b.
export { Breadcrumb, type BreadcrumbProps } from "./Breadcrumb";
export { DetailPanel, type DetailPanelProps } from "./DetailPanel";
export { FolderTabStub, type FolderTabStubProps } from "./FolderTabStub";
export { Kebab, type KebabProps } from "./Kebab";
export { KebabStub, type KebabStubProps } from "./KebabStub";
export { OverviewTab, type OverviewTabProps } from "./OverviewTab";
export { SearchTabStub, type SearchTabStubProps } from "./SearchTabStub";
export { TabStrip, type TabDefinition, type TabStripProps } from "./TabStrip";
export {
  TaxonDetailPlaceholder, type TaxonDetailPlaceholderProps,
} from "./TaxonDetailPlaceholder";
export { Tree, type TreeProps } from "./Tree";
export { useKebab, type UseKebabResult } from "./useKebab";