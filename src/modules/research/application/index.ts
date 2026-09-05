// Application-layer re-export surface for the research module
// (PR 5b.2). Mirrors `src/modules/taxonomy/application/index.ts`:
// presentation consumers import view models + hook adapters
// exclusively from this barrel.

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
