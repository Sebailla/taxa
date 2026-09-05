// Presentation-layer barrel for the research module (PR 5b.3).
//
// Re-exports the FileExplorer / FileViewer shell pair plus the four
// internal pieces (RawTableTreeTabs, MetaStrip, BreadcrumbPanel,
// Banners) so a future app-shell reuse (PR 5b.9) can compose them
// without reaching into the layer. Cross-module consumers MUST import
// via this barrel; deep imports are blocked by the ESLint guard in
// `.eslintrc.cjs` (spec.md rule 5).
//
// `RawTableTreeTabs` stays local to the research module — it is NOT
// promoted to design-system. The barrel re-export is the only
// research-side seam.

export { Banners, type BannersProps } from "./Banners";
export { BreadcrumbPanel, type BreadcrumbPanelProps, type BreadcrumbSegment } from "./BreadcrumbPanel";
export { FileExplorer, type FileExplorerProps } from "./FileExplorer";
export { FileViewer, type FileViewerProps } from "./FileViewer";
export { MetaStrip, type MetaStripProps } from "./MetaStrip";
export { RawTableTreeTabs, type RawTableTreeTabsProps } from "./RawTableTreeTabs";