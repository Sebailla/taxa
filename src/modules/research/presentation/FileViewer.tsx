"use client";

// FileViewer — the right pane of the research explorer. Owns the
// no-file empty state (when `file` is null), the meta strip
// (`FORMAT | SIZE | ENCODING`), the Raw / Table / Tree tab strip,
// the CDN-failure banner, AND the per-format renderer dispatcher
// (PR 5c). The viewer is mounted by `FileExplorer` inside the
// `.file-viewer-pane` (now also `.fex-viewer-pane` for back-compat
// with the legacy e2e selector contract) selector; the no-file
// empty state lives HERE so the left tree pane doesn't have to
// render an empty viewer.
//
// The viewer hook (`useFileViewer`, 5b.2) owns the CDN script-load
// lifecycle and the serve URL builder. The component composes
// `MetaStrip`, `RawTableTreeTabs`, and `Banners` so each piece can be
// reused independently in app-shell (PR 5b.9 refactor).
//
// PR 5c — per-format renderer
// ============================
// The component now dispatches on the typed `descriptor.format`
// (5b.2 contract) to render the file body inside the
// `fex-snippet-body` host. Coverage:
//   pdf, html, htm    -> <iframe>  (sandboxed for html/htm)
//   txt, md, json     -> <pre>     (fetch + useEffect paint)
//   csv, tsv          -> <iframe>  (Raw tab; Table tab reads Papa)
//   image, svg        -> <img>     (svg: inline + <script> scrub)
//   video             -> <video controls preload="metadata">
//   docx, xls, xlsx, epub -> offline banner w/ download link (Raw)
//   doc, unknown      -> empty state w/ download link (Raw)
//
// The renderer rides the already-shipped 5b.2 typed
// `resolveViewerDescriptor` (no local RENDERERS table) and the
// `useFileViewer` hook (no local CDN cache). No application /
// domain / infrastructure layer changes.

import { useEffect, useState } from "react";
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

// ---- Per-format renderer helpers (file-private) --------------------
//
// Each helper paints into the `host` element via React JSX so React
// owns the lifecycle (no manual DOM mutation, no leaked event
// listeners). Text fetchers (txt / md / json) use a small `useEffect`
// pattern to populate the `<pre>` body on mount / serve-URL change.

// text-only renderer — fetch + paint inside a fenced <pre>. Used for
// txt, md, json (the legacy `renderAsPre` shape).
function TextBody({
  url, label, extension,
}: {
  readonly url: string;
  readonly label: string;
  readonly extension: string;
}): ReactElement {
  const [body, setBody] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    setBody("");
    setError(null);
    void (async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) {
          throw new Error(`${res.status} ${res.statusText}`);
        }
        const text = await res.text();
        if (!cancelled) setBody(text);
      } catch (cause) {
        if (!cancelled) {
          setError(
            cause instanceof Error ? cause.message : String(cause),
          );
        }
      }
    })();
    return () => { cancelled = true; };
  }, [url]);
  if (error !== null) {
    return (
      <div className="fex-banner" role="alert">
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 20 }}
          aria-hidden="true"
        >error</span>
        <span>{`Failed to load ${label}: ${error}`}</span>
      </div>
    );
  }
  return (
    <pre
      className="font-mono-data whitespace-pre-wrap break-words p-4"
      data-viewer-text-format={extension}
    >
      {body}
    </pre>
  );
}

// iframe renderer — used by pdf, html, htm, csv, tsv (Raw tab).
// `sandbox` flag flips on for the HTML family to neutralize the
// same-origin XSS surface (matches legacy `renderHtml`).
function IframeBody({
  url, format, sandbox, title,
}: {
  readonly url: string;
  readonly format: string;
  readonly sandbox: boolean;
  readonly title: string;
}): ReactElement {
  const className = sandbox
    ? "w-full h-full min-h-[480px] bg-white"
    : "w-full h-full min-h-[480px] bg-surface";
  // Sandbox attribute on the iframe: the bare string `""` is the
  // strongest sandbox (no allow-* tokens), which is exactly what
  // the legacy contract wanted for HTML files served from disk.
  // The PDF iframe also stamps `type="application/pdf"` (MIME hint
  // for browsers to render inline vs. download). React's
  // `IframeHTMLAttributes` does not declare `type` — the spread
  // bypasses the type check via `any`.
  const iframeExtraProps = format === "pdf"
    ? ({ type: "application/pdf" } as Record<string, string>)
    : ({} as Record<string, string>);
  return (
    <iframe
      {...iframeExtraProps}
      src={url}
      title={title}
      sandbox={sandbox ? "" : undefined}
      className={className}
      data-viewer-iframe-format={format}
    />
  );
}

// image renderer — <img> for raster formats + inline SVG with
// <script> scrub for SVG (XSS defense; matches legacy `renderSvg`).
function ImageBody({
  url, name, format,
}: {
  readonly url: string;
  readonly name: string;
  readonly format: string;
}): ReactElement {
  // SVG path: fetch + parse + scrub. Raster path: <img> native decoder.
  if (format === "svg") {
    return <SvgBody url={url} name={name} />;
  }
  return (
    <div className="fex-image-frame">
      <img
        src={url}
        alt={name}
        title={name}
        className="fex-image"
        loading="lazy"
        decoding="async"
        data-viewer-image-format={format}
      />
    </div>
  );
}

// Inline SVG with XSS scrub. Fetches the body, parses via DOMParser
// in `image/svg+xml` mode, drops every <script> and every `on*`
// attribute, then mounts the cleaned <svg> inside the frame.
function SvgBody({
  url, name,
}: {
  readonly url: string;
  readonly name: string;
}): ReactElement {
  const [svg, setSvg] = useState<ReactElement | null>(null);
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const text = await res.text();
        const doc = new DOMParser().parseFromString(text, "image/svg+xml");
        const el = doc.documentElement;
        if (!el || el.nodeName.toLowerCase() !== "svg") {
          throw new Error("Document is not a valid SVG");
        }
        // Strip <script> elements — primary XSS vector for inline SVG.
        el.querySelectorAll("script").forEach((n) => n.remove());
        // Strip every on* attribute (onload / onclick / onerror / ...).
        const walker = doc.createTreeWalker(el, NodeFilter.SHOW_ELEMENT);
        let node: Node | null = walker.currentNode;
        while (node !== null) {
          for (const attr of [...(node as Element).attributes]) {
            if (/^on/i.test(attr.name)) {
              (node as Element).removeAttribute(attr.name);
            }
          }
          node = walker.nextNode();
        }
        // Pin to the frame box (object-contain semantics) and
        // preserve the aspect ratio when the source didn't declare one.
        el.setAttribute("class", "fex-image");
        if (!el.getAttribute("preserveAspectRatio")) {
          el.setAttribute("preserveAspectRatio", "xMidYMid meet");
        }
        if (!cancelled) {
          // Use dangerouslySetInnerHTML — the SVG has been scrubbed
          // above (<script> + on* attrs removed) so this is safe.
          const html = new XMLSerializer().serializeToString(el);
          setSvg(
            <div
              className="fex-image-frame"
              data-viewer-image-format="svg"
              dangerouslySetInnerHTML={{ __html: html }}
            />,
          );
        }
      } catch {
        if (!cancelled) {
          // Render the generic image error card (download link).
          setSvg(
            <div className="fex-empty-state" data-viewer-image-error="">
              <span
                className="fex-empty-state-icon material-symbols-outlined"
                aria-hidden="true"
              >broken_image</span>
              <p className="font-semibold text-on-surface">
                {`Could not decode ${name}`}
              </p>
              <a
                href={url}
                download={name}
                className="fex-snippet-btn mt-2"
              >Download file</a>
            </div>,
          );
        }
      }
    })();
    return () => { cancelled = true; };
  }, [url, name]);
  return svg ?? (
    <div className="fex-empty-state" role="status" aria-live="polite">
      <span className="fex-empty-state-icon material-symbols-outlined animate-spin"
            aria-hidden="true">progress_activity</span>
      <p>{"Loading image\u2026"}</p>
    </div>
  );
}

// video renderer — <video controls preload="metadata">. No autoplay.
function VideoBody({
  url, name,
}: {
  readonly url: string;
  readonly name: string;
}): ReactElement {
  return (
    <div className="fex-video-frame">
      <video
        src={url}
        title={name}
        className="fex-video-el"
        controls
        preload="metadata"
        data-viewer-video-format="video"
      />
    </div>
  );
}

// Download-fallback renderer — used by `doc` / `unknown` (and the
// CDN-backed formats as the Raw tab placeholder when the CDN is
// offline). Mirrors the legacy `renderUnsupported` /
// `renderOfflineBanner` shapes.
function DownloadFallbackBody({
  url, name, message,
}: {
  readonly url: string;
  readonly name: string;
  readonly message: string;
}): ReactElement {
  return (
    <div
      className="fex-empty-state"
      data-viewer-download-fallback=""
      data-viewer-download-name={name}
    >
      <span
        className="fex-empty-state-icon material-symbols-outlined"
        aria-hidden="true"
      >description</span>
      <p className="font-semibold text-on-surface">{message}</p>
      <p className="text-on-surface-variant text-body-sm">
        {"Raw download available."}
      </p>
      <a
        href={url}
        download={name}
        className="fex-snippet-btn mt-2"
      >{"Download file"}</a>
    </div>
  );
}

// ---- Per-format dispatcher ----------------------------------------
// Dispatches on `descriptor.format` (typed 5b.2 contract). Each
// branch mounts the matching body component inside the snippet frame.

export function FileViewer({
  file, baseUrl, taxonId, viewerTab, onSelectTab,
}: FileViewerProps): ReactElement {
  // useFileViewer is the single source of truth for descriptor, serveUrl,
  // cdnReady, cdnError. When `file` is null the hook returns a fully
  // idle state — descriptor null, serveUrl null, cdnReady true.
  const { serveUrl, cdnReady, cdnError } = useFileViewer({
    baseUrl, taxonId, file,
  });
  // Resolve the typed descriptor via the 5b.2 dispatcher — the hook
  // uses the same helper internally; computing it here directly pins
  // the contract (the renderer dispatches on the same shape the helper
  // emits) and avoids relying on the hook's wrapper.
  const descriptor = file !== null ? resolveViewerDescriptor(file) : null;

  if (file === null || descriptor === null) {
    return (
      <div className="file-viewer-pane fex-viewer-pane" data-viewer-empty="">
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
    <div className="file-viewer-pane fex-viewer-pane" data-viewer-pane=""
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
          <FormatBody
            format={descriptor.format}
            serveUrl={serveUrl}
            fileName={file.name}
          />
        </div>
      </div>
    </div>
  );
}

// ---- FormatBody — per-format dispatcher ----------------------------
// Reads `descriptor.format` (typed 5b.2 contract). Branches cover
// every format `resolveViewerDescriptor` may emit. The Raw-tab
// placeholder for CDN-backed formats (docx / xls / xlsx / epub) is
// the download-fallback (the Banners component surfaces the offline
// message; the fallback here keeps the user pointed at the raw file).

function FormatBody({
  format, serveUrl, fileName,
}: {
  readonly format: string;
  readonly serveUrl: string | null;
  readonly fileName: string;
}): ReactElement {
  // serveUrl is null only when the file is null (the early return
  // above already filtered that), so we can safely default to "".
  const url = serveUrl ?? "";

  switch (format) {
    case "pdf":
      return (
        <IframeBody
          url={url}
          format="pdf"
          sandbox={false}
          title={fileName}
        />
      );
    case "html":
    case "htm":
      return (
        <IframeBody
          url={url}
          format="html"
          sandbox={true}
          title={fileName}
        />
      );
    case "txt":
      return <TextBody url={url} label="text" extension="txt" />;
    case "md":
      return <TextBody url={url} label="markdown" extension="md" />;
    case "json":
      return <TextBody url={url} label="json" extension="json" />;
    case "csv":
    case "tsv":
      // Raw tab: iframe pointing at the served bytes. The Table tab
      // is the parsed Papa Parse view (a future PR).
      return (
        <IframeBody
          url={url}
          format={format}
          sandbox={false}
          title={fileName}
        />
      );
    case "image":
      return <ImageBody url={url} name={fileName} format="image" />;
    case "video":
      return <VideoBody url={url} name={fileName} />;
    case "docx":
    case "xls":
    case "xlsx":
    case "epub":
      // Raw tab fallback when CDN is offline / not loaded. The
      // Banners component already paints the offline status; the
      // body points the user at the raw download.
      return (
        <DownloadFallbackBody
          url={url}
          name={fileName}
          message={`No inline preview for ${format.toUpperCase()}.`}
        />
      );
    case "doc":
    case "unknown":
    default:
      return (
        <DownloadFallbackBody
          url={url}
          name={fileName}
          message={
            format === "doc"
              ? "DOC (legacy) has no inline preview."
              : "No inline preview is available for this format."
          }
        />
      );
  }
}
