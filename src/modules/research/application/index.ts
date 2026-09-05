// Application-layer re-export surface for the research module
// (PR 5b.2 + 5b.4 addendum). Mirrors `src/modules/taxonomy/application/index.ts`:
// presentation consumers import view models + hook adapters
// exclusively from this barrel.
//
// 5b.4 ADDS the `useMaterializePreview` hook surface (decision #2 +
// decision #5). The hook is reached via `@taxa/research` (public barrel).

export {
  DEBOUNCE_MS,
  annotateExplorerMatches,
  initialExplorerSearchState,
  initialExplorerState,
  isExplorerSearchMode,
  isExplorerSearchState,
  isExplorerViewerTab,
  projectExplorerTree,
  useFileExplorer,
  type ExplorerSearchMode,
  type ExplorerSearchState,
  type ExplorerState,
  type ExplorerTreeViewModel,
  type ExplorerViewerTab,
  type FileExplorerHookState,
  type UseFileExplorerOptions,
} from "./useFileExplorer";

export {
  formatSize,
  resolveViewerDescriptor,
  useFileViewer,
  type CdnLibrary,
  type FileViewerHookState,
  type FormatDescriptor,
  type UseFileViewerOptions,
  type ViewerFile,
} from "./useFileViewer";

export {
  useMaterializePreview,
  projectMaterializePreview,
  isMaterializeStatus,
  NetworkError,
  type FolderCreateInput,
  type MaterializePreviewHookState,
  type MaterializePreviewViewModel,
  type MaterializeStatus,
  type UseMaterializePreviewOptions,
} from "./useMaterializePreview";
