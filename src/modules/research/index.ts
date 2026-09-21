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
 *
 * ODD-MIGRATE-002 W3: re-export the typed HTTP adapter + the
 * `ExplorerApiError` named error class + the `FetchOptions` transport
 * surface so cross-module consumers (W6 React mount, integration tests)
 * reach the W3 contract through the barrel — spec.md rule 5. The
 * application port (`ExplorerRepository`, `EXPLORER_PORT_NAME`,
 * `ExplorerFileServeRequest`, `ExplorerFileServeResult`) is re-exported
 * too so W6+ consumers can wire the typed surface through one barrel
 * import. The domain types are already reachable through the W1
 * barrel work; future work units (W4 renderers, W5 search) will
 * extend the barrel without restructuring this surface.
 *
 * ODD-MIGRATE-002 W4a: re-export the pure viewer-dispatch contract —
 * `dispatchViewer` + `sanitizeSvgMarkup` + the `ViewerDispatch` /
 * `ViewerDispatchInput` / `ViewerFileDescriptor` / `ViewerLink` /
 * `ViewerImageAdvisory` types + the `IMAGE_BIG_FILE_BYTES` and
 * `TAB_NOT_APPLICABLE_SUFFIX` constants — so cross-module consumers
 * (W6 React mount, integration tests) reach the W4a contract through
 * the barrel. The contract covers the eight no-CDN families (PDF,
 * HTML/HTM, TXT, MD-as-text, DOC fallback, JPG/JPEG/PNG/GIF/WEBP/
 * BMP, SVG with XSS scrub, MP4/WEBM/OGV) + the "other" extension
 * fallback + the Table/Tree tab-not-applicable feedback. CDN-dependent
 * families (DOCX, XLS/XLSX, EPUB, CSV/TSV, JSON) and Markdown-as-HTML
 * stay deferred to W4b+; the dispatcher falls through to
 * `unsupported` / `tab-not-applicable` for those combinations until
 * the later slices extend the contract.
 *
 * ODD-MIGRATE-002 W4b1: re-export the pinned mammoth CDN URL +
 * window-global name — `MAMMOTH_CDN_URL` + `MAMMOTH_GLOBAL_NAME`
 * — so cross-module consumers (W6 React mount) reach the typed
 * DOCX source descriptor's CDN pin through the barrel. The W4b1
 * contract adds `docx-source` and `docx-offline` variants to the
 * existing `ViewerDispatch` discriminated union (no new top-level
 * type); React consumers read the variants via the same
 * `ViewerDispatch` import. The dispatcher does NOT import or load
 * mammoth — the application layer stays framework-free,
 * browser-free, and CDN-loader-free. Future W4b2–W4b4 slices follow
 * the same pattern: add variants to `ViewerDispatch`, not new
 * top-level types.
 *
 * ODD-MIGRATE-002 W4b2: re-export the pinned SheetJS CDN URL +
 * window-global name — `SHEETJS_CDN_URL` + `SHEETJS_GLOBAL_NAME`
 * — so cross-module consumers (W6 React mount) reach the typed
 * XLS / XLSX source descriptor's CDN pin through the barrel. The
 * W4b2 contract adds `sheet-source` and `sheet-offline` variants
 * to the existing `ViewerDispatch` discriminated union (no new
 * top-level type); React consumers read the variants via the same
 * `ViewerDispatch` import. The dispatcher does NOT import or load
 * SheetJS — the application layer stays framework-free,
 * browser-free, and CDN-loader-free. Future W4b3 (EPUB) slices
 * follow the same pattern: add variants to `ViewerDispatch`, not
 * new top-level types.
 *
 * ODD-MIGRATE-002 W4b3: re-export the pinned epubjs CDN URL +
 * window-global name — `EPUBJS_CDN_URL` + `EPUBJS_GLOBAL_NAME`
 * — so cross-module consumers (W6 React mount) reach the typed
 * EPUB source descriptor's CDN pin through the barrel. The W4b3
 * contract adds `epub-source` and `epub-offline` variants to the
 * existing `ViewerDispatch` discriminated union (no new top-level
 * type); React consumers read the variants via the same
 * `ViewerDispatch` import. The dispatcher does NOT import or load
 * epubjs — the application layer stays framework-free,
 * browser-free, and CDN-loader-free. The future mount owns the
 * full EPUB render lifecycle: `<Script>` load +
 * `ePub(bytes.buffer)` construction + `book.renderTo(...)` mount
 * + prev / next click handlers + module-scoped
 * `_currentBook.destroy()` teardown on the NEXT open.
 *
 * ODD-MIGRATE-002 W4b4: re-export the pinned Papa Parse CDN URL
 * + window-global name — `PAPA_CDN_URL` + `PAPA_GLOBAL_NAME`
 * — so cross-module consumers (W6 React mount) reach the typed
 * CSV / TSV source descriptor's CDN pin through the barrel. The
 * W4b4 contract adds four new variants to the existing
 * `ViewerDispatch` discriminated union (no new top-level type):
 * `table-source` (CSV / TSV + Table + bytes), `table-offline`
 * (CSV / TSV + Table + bytes=null), `json-source` (JSON + Tree +
 * bytes — NO CDN metadata, JSON parsing is native), and
 * `json-offline` (JSON + Tree + bytes=null — NO CDN metadata).
 * React consumers read the variants via the same `ViewerDispatch`
 * import. The W4b4 contract closes the W4 split by adding the
 * canonical exceptions to the Table / Tree tab gate: (Table,
 * csv), (Table, tsv), (Tree, json). CSV / TSV / JSON on Raw
 * stay on the existing W4a `unsupported` fallback / download
 * per the user decision (Raw uses the existing fallback/download
 * behavior). The dispatcher does NOT import or load Papa Parse,
 * does NOT call `JSON.parse`, does NOT touch the DOM — the
 * application layer stays framework-free, browser-free, and
 * CDN-loader-free. Parsing, JSON truncation, Papa script
 * loading, and all DOM / React / Next rendering remain the future
 * React mount's responsibility.
 */
export {
  fetchFiles,
  fetchFileServe,
  ExplorerApiError,
} from "./infrastructure/api";
export type { FetchOptions } from "./infrastructure/api";
export type {
  ExplorerRepository,
  ExplorerFileServeRequest,
  ExplorerFileServeResult,
} from "./application/ports";
export { EXPLORER_PORT_NAME } from "./application/ports";
export {
  dispatchViewer,
  sanitizeSvgMarkup,
  IMAGE_BIG_FILE_BYTES,
  TAB_NOT_APPLICABLE_SUFFIX,
  MAMMOTH_CDN_URL,
  MAMMOTH_GLOBAL_NAME,
  SHEETJS_CDN_URL,
  SHEETJS_GLOBAL_NAME,
  EPUBJS_CDN_URL,
  EPUBJS_GLOBAL_NAME,
  PAPA_CDN_URL,
  PAPA_GLOBAL_NAME,
} from "./application/renderers";
export type {
  ViewerDispatch,
  ViewerDispatchInput,
  ViewerFileDescriptor,
  ViewerLink,
  ViewerImageAdvisory,
  TableDelimiter,
} from "./application/renderers";

// ODD-MIGRATE-002 W1 — re-export the W1 domain types so
// cross-module consumers (the W6 React mount + integration
// tests) reach the typed shape through the barrel —
// spec.md rule 5. The domain folder stays private (deep
// imports are blocked by `.eslintrc.cjs::no-restricted-
// imports`); every consumer of `ExplorerTree`,
// `ExplorerTreeNode`, `ExplorerFolderNode`,
// `ExplorerFileNode`, `ViewerTab`, `FileFormat`, or
// `SearchState` reaches the typed surface through one
// barrel import. The W1 `createInitialExplorerState`
// factory is also re-exported so the W6 mount's initial
// state matches the legacy `web/state.js::initialExplorerShape()`
// oracle byte-for-byte.
//
// ODD-MIGRATE-003 W6.1 — the W6.1 mount reads every
// domain type + the W1 initial-state factory + the
// `ViewerTab` + `FileFormat` literals through the
// barrel only. The barrel is the single typed hand-off
// surface between the presentation layer and the rest
// of the capability module. A future PR that re-exports
// a new domain type (e.g. a Search-state discriminator
// the W6.2 search slice owns) extends this list without
// restructuring the consumer contract.
export type {
  ExplorerTree,
  ExplorerTreeNode,
  ExplorerFolderNode,
  ExplorerFileNode,
  ViewerTab,
  FileFormat,
  SearchState,
  ExplorerState,
} from "./domain/explorer";
export { createInitialExplorerState } from "./domain/explorer";

// ODD-MIGRATE-003 W6.1 — re-export the pure state kernel
// (`explorer-state.ts`) so the React mount consumes the
// typed state transitions through the barrel. The kernel
// owns the typed `ExplorerLoadStatus` discriminated union
// (idle / loading / loaded / empty / error) + the typed
// `ViewerState` view-model + the `bytesRequiredForFormat`
// predicate + the `castFileFormat` safe-extension fallback
// + the `buildServeUrl` W3 URL builder + the recursive
// `enumerateFiles` walker + the pure `toggleExpansion` /
// `withExpanded` set transitions. Every helper is pure —
// the React mount wires the helpers into `useState` /
// `useEffect` calls without re-implementing the typed
// surface. The kernel is framework-free (no React, no
// Next, no DOM, no fetch) so a future presentation-only
// slice can import it through the barrel and compile it
// in isolation under `--lib ES2022`. The presentation
// React components (`Explorer.tsx`, `Viewer.tsx`,
// `FileTree.tsx`) are re-exported below as the W6.1
// client island surface.
export {
  createInitialLoadStatus,
  createInitialViewerState,
  bytesRequiredForFormat,
  castFileFormat,
  buildServeUrl,
  enumerateFiles,
  toggleExpansion,
  withExpanded,
} from "./presentation/explorer-state";
export type {
  ExplorerLoadStatus,
  ViewerState,
} from "./presentation/explorer-state";
export { default as Explorer } from "./presentation/Explorer";
export { default as Viewer } from "./presentation/Viewer";
export { default as FileTree } from "./presentation/FileTree";
export { default as ExplorerErrorBoundary } from "./presentation/ExplorerErrorBoundary";
