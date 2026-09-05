"use client";

// FileViewer — the right pane of the research explorer. Owns the
// no-file empty state (when `file` is null), the meta strip
// (`FORMAT | SIZE | ENCODING`), the Raw / Table / Tree tab strip,
// and the CDN-failure banner. The viewer is mounted by `FileExplorer`
// inside the `.file-viewer-pane` selector; the no-file empty state
// lives HERE so the left tree pane doesn't have to render an empty
// viewer.
//
// The viewer hook (`useFileViewer`, 5b.2) owns the CDN script-load
// lifecycle and the serve URL builder. The component composes
// `MetaStrip`, `RawTableTreeTabs`, and `Banners` so each piece can be
// reused independently in app-shell (PR 5b.9 refactor).
//
// No Search / Folder / app-shell integration in 5b.3.

import type { ReactElement } from "react";

import {
  resolveViewerDescriptor,
  useFileViewer,
  type ViewerFile,
} from "@taxa/research";

import { Banners } from "./Banners";
import { MetaStrip } from "./MetaStrip";
import { RawTableTreeTabs } from "./RawTableTreeTabs";

export interface FileViewerProps {
  /** Active file descriptor (the explorer feeds this on open). When
   *  null the viewer paints its no-file empty state. */
  readonly file: ViewerFile | null;
  /** Base URL for the serve endpoint (`${baseUrl}/api/taxon/{id}/files/serve`). */
  readonly baseUrl: string;
  /** Active taxon id, used to build the serve URL. */
  readonly taxonId: number;
  /** Active viewer tab (Raw / Table / Tree) — controlled by the parent
   *  hook so the explorer state is the single source of truth. */
  readonly viewerTab: "Raw" | "Table" | "Tree";
  /** Called when the user picks a different viewer tab. */
  readonly onSelectTab: (tab: "Raw" | "Table" | "Tree") => void;
}

export function FileViewer({
  file, baseUrl, taxonId, viewerTab, onSelectTab,
}: FileViewerProps): ReactElement {
  // useFileViewer is the single source of truth for descriptor, serveUrl,
  // cdnReady, cdnError. When `file` is null the hook returns a fully
  // idle state — descriptor null, serveUrl null, cdnReady true.
  const { descriptor, serveUrl, cdnReady, cdnError } = useFileViewer({
    baseUrl, taxonId, file,
  });

  if (file === null || descriptor === null) {
    return (
      <div className="file-viewer-pane" data-viewer-empty="">
        <div className="fex-empty-state" role="status" aria-live="polite">
          <span className="fex-empty-state-icon material-symbols-outlined"
                aria-hidden="true">description</span>
          <p>Select a file to preview.</p>
        </div>
      </div>
    );
  }

  const showCdnBanner = cdnError !== null || (descriptor.cdnLibrary !== null && !cdnReady);

  return (
    <div className="file-viewer-pane" data-viewer-pane=""
         data-viewer-format={descriptor.format}
         data-cdn-library={descriptor.cdnLibrary ?? ""}
         data-cdn-ready={cdnReady ? "true" : "false"}>
      <Banners show={showCdnBanner} fileName={file.name} />
      <MetaStrip format={file.extension} size={file.size} />
      <RawTableTreeTabs active={viewerTab} onSelect={onSelectTab} />
      <div className="fex-snippet-frame">
        <div className="fex-snippet-title">
          <span className="fex-snippet-dots" aria-hidden="true">
            <span className="dot-r" />
            <span className="dot-y" />
            <span className="dot-g" />
          </span>
          <span>{file.name}</span>
        </div>
        <div id="fex-snippet-body" className="fex-snippet-body"
             data-viewer-body="" data-serve-url={serveUrl ?? ""}>
          {/* PR 5c will paint the per-format renderer into this host
              element (matched by the data-viewer-body attribute). For
              now we expose the host so the explorer shell has a stable
              shape for the refactor. */}
        </div>
      </div>
    </div>
  );
}
