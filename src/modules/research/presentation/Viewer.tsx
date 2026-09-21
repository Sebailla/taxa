"use client";

/**
 * Viewer — non-CDN W4a viewer rendering for the Browser-tab
 * Explorer client island (ODD-MIGRATE-003 / W6.1).
 *
 * Client component (boundary declared at the top of the file).
 * Receives the open file + active tab from `Explorer.tsx` and
 * renders the matching JSX branch by calling
 * `dispatchViewer({file, tab, bytes})` and switching on the
 * typed `ViewerDispatch` outcome. The component owns the
 * fetch-bytes lifecycle (when the format requires them —
 * TXT / MD / SVG) so `Explorer.tsx` stays a thin orchestrator.
 *
 * W6.1 contract — non-CDN rendering only. The dispatcher's
 * W4b1–W4b4 source variants (`docx-source`, `sheet-source`,
 * `epub-source`, `table-source`, `json-source`) carry bytes +
 * pinned CDN URLs; W6.1 does not wire the CDN scripts, so
 * the mount surfaces those source variants as a download-link
 * recovery card (functionally equivalent to the matching
 * offline variant — the user can still get the raw file
 * even though the inline preview is not available). A future
 * W6+ slice would extend the typed predicate to load the CDN
 * libraries via Next 16's `<Script>` component and re-render
 * the inline preview.
 *
 * The component also owns the W4a tab-not-applicable message
 * rendering: when the active tab is "Table" / "Tree" for a
 * format that has no W4a renderer, the dispatcher returns
 * `tab-not-applicable` and the mount paints the legacy
 * `"${tab} view not available for .${ext} files — use Raw."`
 * message verbatim. The W4b4 canonical exceptions
 * (Table on CSV / TSV, Tree on JSON) surface through the
 * typed source / offline branches, which the W6.1 mount
 * renders as a download-link card (per the W6.1 non-CDN
 * scope).
 *
 * spec.md rule 4: presentation depends on the public barrel +
 * domain. The component imports through `@taxa/research`
 * (the public barrel) only — no deep imports into the
 * application / domain / infrastructure layers.
 */

import { useEffect, useState, type ReactNode } from "react";
import {
  dispatchViewer,
  fetchFileServe,
  type ViewerDispatch,
  type ViewerFileDescriptor,
  type FileFormat,
  type ViewerTab,
  bytesRequiredForFormat,
  buildServeUrl,
} from "@taxa/research";

/** Props for the `Viewer` component. The Explorer mount owns
 *  the active-tab state and the open-file state; this
 *  component renders the JSX branch + owns the bytes-fetch
 *  lifecycle. The component is intentionally a pure
 *  projection: no internal state for which-tab-is-active
 *  (the parent owns it) so the React render cycle stays
 *  deterministic. */
export interface ViewerProps {
  readonly apiOrigin: string;
  readonly openFilePath: string | null;
  readonly openFileFormat: FileFormat | null;
  readonly tab: ViewerTab;
  readonly onTabChange: (tab: ViewerTab) => void;
}

/** Typed fetch status for the bytes lifecycle. Mirrors the
 *  ExplorerLoadStatus shape (idle / loading / loaded / error)
 *  but scoped to a single file's bytes — the bytes are
 *  cached for the lifetime of the component mount, then
 *  garbage-collected when the parent unmounts the Viewer. */
type BytesStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | { readonly kind: "loaded"; readonly bytes: Uint8Array }
  | { readonly kind: "error"; readonly message: string };

function createInitialBytesStatus(): BytesStatus {
  return { kind: "idle" };
}

function buildDescriptor(
  apiOrigin: string,
  filePath: string,
  fileFormat: FileFormat,
): ViewerFileDescriptor {
  // Extract the basename from the relative path so the
  // `name` field carries the wire `name` verbatim when
  // available. The ViewerFileDescriptor's `name` field is
  // used for the `<iframe title>` / `<img alt>` / download
  // `download` attribute; the basename is the legacy
  // observable shape.
  const basename = filePath.split("/").pop() ?? filePath;
  return {
    url: buildServeUrl(apiOrigin, filePath),
    name: basename,
    format: fileFormat,
    size: 0,
    path: filePath,
  };
}

function renderDispatch(
  dispatch: ViewerDispatch,
  descriptor: ViewerFileDescriptor,
): ReactNode {
  switch (dispatch.kind) {
    case "pdf-iframe":
      return (
        <div className="flex flex-col gap-2">
          <iframe
            src={dispatch.src}
            title={dispatch.title}
            className="w-full min-h-[480px] bg-surface"
            data-viewer-kind="pdf-iframe"
          />
          <p className="p-4 text-on-surface-variant text-body-sm">
            If the PDF does not render,{" "}
            <a
              href={dispatch.fallback.href}
              download={dispatch.fallback.download}
              className="text-primary underline"
            >
              download the file
            </a>{" "}
            directly.
          </p>
        </div>
      );
    case "html-iframe":
      return (
        <iframe
          src={dispatch.src}
          title={dispatch.title}
          // Empty sandbox (NO `allow-same-origin`) — mirrors
          // the W4a contract (`web/file_viewer.js::renderHtml`
          // also passes `sandbox: ""`).
          sandbox=""
          className="w-full min-h-[480px] bg-white"
          data-viewer-kind="html-iframe"
        />
      );
    case "text-pre":
      return (
        <pre
          className="font-mono-data whitespace-pre-wrap break-words p-4 text-on-surface"
          data-viewer-kind="text-pre"
        >
          {dispatch.body}
        </pre>
      );
    case "image":
      return (
        <div className="fex-image-frame flex flex-col gap-2">
          {dispatch.advisory !== null ? (
            <div
              className="fex-image-advisory"
              role="status"
              data-viewer-kind="image-advisory"
            >
              <span className="material-symbols-outlined">warning</span>
              {dispatch.advisory.message}
            </div>
          ) : null}
          <img
            src={dispatch.src}
            alt={dispatch.alt}
            title={dispatch.title}
            className="fex-image"
            loading="lazy"
            decoding="async"
            data-viewer-kind="image"
          />
        </div>
      );
    case "image-error":
      return (
        <div
          className="fex-empty-state"
          role="alert"
          data-viewer-kind="image-error"
        >
          <span className="fex-empty-state-icon material-symbols-outlined">
            broken_image
          </span>
          <p className="font-semibold text-on-surface">
            Could not decode {dispatch.name}
          </p>
          <a
            href={dispatch.download.href}
            download={dispatch.download.download}
            className="fex-snippet-btn mt-2"
          >
            Download file
          </a>
        </div>
      );
    case "svg-sanitized": {
      // The dispatcher returns the XSS-scrubbed SVG markup
      // verbatim; the React mount injects it through
      // `dangerouslySetInnerHTML`. The W4a scrub has already
      // stripped `<script>` (paired + self-closing, case-
      // insensitive) AND `on*=` event-handler attributes (case-
      // insensitive — see `sanitizeSvgMarkup` in
      // `application/renderers.ts`), so the inline surface is
      // the same XSS-safe shape as the legacy
      // `web/file_viewer.js::renderSvg` path. The W4a scrub is
      // the XSS guard — the React mount does not add its own.
      // We pass the scrubbed string through a `div` wrapper
      // (matching the legacy `fex-image-frame` shape) so the
      // CSS sizing rules still apply. The lint advisory about
      // `dangerouslySetInnerHTML` XSS surface is intentional:
      // the W4a scrub is the typed hand-off, and the mount
      // trusts it byte-for-byte.
      return (
        <div
          className="fex-image-frame"
          data-viewer-kind="svg-sanitized"
          dangerouslySetInnerHTML={{ __html: dispatch.svg }}
        />
      );
    }
    case "video":
      return (
        <div className="fex-video-frame">
          <video
            src={dispatch.src}
            title={dispatch.title}
            className="fex-video-el"
            controls
            preload="metadata"
            data-viewer-kind="video"
          />
        </div>
      );
    case "unsupported":
      return (
        <div
          className="fex-empty-state"
          role="status"
          data-viewer-kind="unsupported"
        >
          <span className="fex-empty-state-icon material-symbols-outlined">
            description
          </span>
          <p className="font-semibold text-on-surface">{dispatch.message}</p>
          <a
            href={dispatch.download.href}
            download={dispatch.download.download}
            className="fex-snippet-btn mt-2"
          >
            Download file
          </a>
        </div>
      );
    case "tab-not-applicable":
      return (
        <div
          className="fex-empty-state"
          role="status"
          data-viewer-kind="tab-not-applicable"
        >
          <span className="fex-empty-state-icon material-symbols-outlined">
            info
          </span>
          <p className="font-semibold text-on-surface">{dispatch.message}</p>
        </div>
      );
    case "docx-source":
    case "docx-offline":
    case "sheet-source":
    case "sheet-offline":
    case "epub-source":
    case "epub-offline":
    case "table-source":
    case "table-offline":
    case "json-source":
    case "json-offline":
      // W6.1 non-CDN mount — the CDN-backed source variants
      // are intentionally not wired here (the mount is
      // non-CDN per the W6.1 contract). The download link
      // gives the user a recovery path so they can still get
      // the raw file even though the inline preview is not
      // available. A future W6+ slice that loads the CDN
      // libraries via Next 16's `<Script>` component would
      // replace this branch with the typed source / offline
      // rendering shape (one JSX branch per CDN library).
      return renderOfflineCard(dispatch, descriptor);
  }
}

function renderOfflineCard(
  dispatch: ViewerDispatch,
  descriptor: ViewerFileDescriptor,
): ReactNode {
  // The W4b source variants + offline variants carry different
  // download-link shapes: the `*-source` variants expose the
  // raw URL via `src` + `title` (so the mount can wire the
  // CDN load site); the `*-offline` variants expose a typed
  // `ViewerLink` (the W4a offline-banner shape). The W6.1
  // non-CDN mount normalizes both into a single offline
  // banner with a download affordance so the user sees a
  // consistent recovery path regardless of which CDN library
  // would have been loaded.
  let downloadHref = descriptor.url;
  let downloadName = descriptor.name;
  if (
    dispatch.kind === "docx-offline" ||
    dispatch.kind === "sheet-offline" ||
    dispatch.kind === "epub-offline" ||
    dispatch.kind === "table-offline" ||
    dispatch.kind === "json-offline"
  ) {
    downloadHref = dispatch.download.href;
    downloadName = dispatch.download.download;
  } else if (
    dispatch.kind === "docx-source" ||
    dispatch.kind === "sheet-source" ||
    dispatch.kind === "epub-source" ||
    dispatch.kind === "table-source" ||
    dispatch.kind === "json-source"
  ) {
    // The source variants carry the raw serve URL via
    // `src` (the descriptor's URL verbatim) so the user
    // can download the raw file even though the inline
    // preview is not wired in W6.1.
    downloadHref = dispatch.src;
    downloadName = dispatch.title;
  }
  return (
    <div
      className="fex-empty-state"
      role="status"
      data-viewer-kind="cdn-pending"
    >
      <span className="fex-empty-state-icon material-symbols-outlined">
        cloud_off
      </span>
      <p className="font-semibold text-on-surface">
        Inline preview pending — raw download available.
      </p>
      <a
        href={downloadHref}
        download={downloadName}
        className="fex-snippet-btn mt-2"
      >
        Download file
      </a>
    </div>
  );
}

/** Public Viewer component. Owns the bytes-fetch lifecycle
 *  + the dispatch lifecycle. Renders the meta strip + tab
 *  strip + snippet frame around the dispatch outcome. */
export default function Viewer(props: ViewerProps): ReactNode {
  const { apiOrigin, openFilePath, openFileFormat, tab, onTabChange } = props;
  const [bytesStatus, setBytesStatus] = useState<BytesStatus>(
    createInitialBytesStatus,
  );

  // Effect: fetch bytes when the open file or tab changes AND
  // the format requires bytes (TXT / MD / SVG). When bytes
  // are not required, the effect short-circuits and the
  // dispatch fires with `bytes: null`. The bytes are NOT
  // cached across opens — a fresh fetchFileServe runs every
  // time the user opens a file (mirrors the legacy's
  // `renderAsPre` / `renderSvg` per-open fetch).
  useEffect(() => {
    if (openFilePath === null || openFileFormat === null) {
      setBytesStatus({ kind: "idle" });
      return;
    }
    if (!bytesRequiredForFormat(openFileFormat)) {
      setBytesStatus({ kind: "idle" });
      return;
    }
    let cancelled = false;
    setBytesStatus({ kind: "loading" });
    fetchFileServe(
      { path: openFilePath },
      { baseUrl: apiOrigin },
    )
      .then((result) => {
        if (cancelled) return;
        setBytesStatus({ kind: "loaded", bytes: result.content });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : String(err);
        setBytesStatus({ kind: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [openFilePath, openFileFormat, apiOrigin]);

  if (openFilePath === null || openFileFormat === null) {
    return (
      <div
        className="fex-empty-state"
        role="status"
        data-viewer-empty=""
      >
        <span className="fex-empty-state-icon material-symbols-outlined">
          visibility_off
        </span>
        <p className="font-semibold text-on-surface">No file selected</p>
        <p className="text-on-surface-variant text-body-sm">
          Double-click a file in the tree to open it.
        </p>
      </div>
    );
  }

  // Bytes-failed branch — surfaces the error inline so the
  // user sees the failure detail + can retry by re-opening
  // the file (the legacy `renderAsPre` catch branch paints
  // the same shape).
  if (bytesStatus.kind === "error") {
    return (
      <div className="fex-banner" role="alert" data-viewer-bytes-error="">
        <span className="material-symbols-outlined text-[20px]">error</span>
        <span>Failed to load file: {bytesStatus.message}</span>
      </div>
    );
  }

  // Bytes-loading branch — quiet skeleton.
  if (bytesStatus.kind === "loading") {
    return (
      <div className="fex-empty-state" role="status" data-viewer-loading="">
        <span className="fex-empty-state-icon material-symbols-outlined animate-spin">
          progress_activity
        </span>
        <p>Loading file…</p>
      </div>
    );
  }

  // Build the dispatch input. Bytes are passed ONLY when the
  // format requires them and the fetch has completed; every
  // other path passes `null` so the dispatcher falls through
  // to the typed fallback branch (the spec's "Format .xyz
  // not supported in viewer." message + download link for
  // unknown extensions, or the bytes-missing offline branch
  // for CDN-backed formats).
  const descriptor = buildDescriptor(apiOrigin, openFilePath, openFileFormat);
  const bytes =
    bytesRequiredForFormat(openFileFormat) && bytesStatus.kind === "loaded"
      ? bytesStatus.bytes
      : null;
  const dispatch: ViewerDispatch = dispatchViewer({
    file: descriptor,
    tab,
    bytes,
  });

  return (
    <div className="flex flex-col gap-2" data-viewer-root="">
      <div className="fex-meta-strip">
        <span>FORMAT={openFileFormat.toUpperCase()}</span>
        <span className="fex-meta-spacer" />
        <a
          href={descriptor.url}
          target="_blank"
          rel="noreferrer"
          className="fex-snippet-btn"
          aria-label="Open in new tab"
          title="Open in new tab"
        >
          <span className="material-symbols-outlined text-[16px]">
            open_in_new
          </span>
        </a>
      </div>
      <div className="fex-tab-strip" role="tablist">
        {(["Raw", "Table", "Tree"] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t ? "true" : "false"}
            className={tab === t ? "active" : ""}
            data-viewer-tab={t}
            onClick={() => onTabChange(t)}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="fex-snippet-frame">
        <div className="fex-snippet-title">
          <span className="fex-snippet-dots">
            <span className="dot-r" />
            <span className="dot-y" />
            <span className="dot-g" />
          </span>
          <span>{descriptor.name}</span>
        </div>
        <div className="fex-snippet-body" data-viewer-body="">
          {renderDispatch(dispatch, descriptor)}
        </div>
      </div>
    </div>
  );
}
