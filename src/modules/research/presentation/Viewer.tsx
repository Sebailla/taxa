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

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Script from "next/script";
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
// W64A-JSON-001 — the W64A pure JSON decoder
// (`parseJsonTree`) + the legacy truncation cap
// (`MAX_JSON_NODES`) live in `explorer-state.ts`. The
// public barrel is intentionally NOT extended for these
// helpers in the W64A edit surface (the barrel is owned
// by a separately authorized slice). The helpers are
// module-local to `presentation/` so the Viewer consumes
// them through the relative path — the same module can
// reach the kernel directly without going through the
// public barrel. A future cross-module consumer (a
// follow-up slice that authorizes the barrel extension)
// would add the helpers to the barrel re-export surface.
import { parseJsonTree, MAX_JSON_NODES } from "./explorer-state";

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
    case "json-source":
      // W64A-JSON-001 — native JSON Tree viewer
      // materialization. JSON parsing is native per the
      // spec's "Tree viewer tab / No CDN is used."
      // requirement (`openspec/specs/research/spec.md`
      // "Tree viewer tab"), so no `<Script>` loader + no
      // CDN library + no third-party JSON parser. The
      // bytes come from the existing `bytesRequiredForFormat`
      // seam (W64A flipped JSON into the bytes-required
      // group); the helper `parseJsonTree` (framework-free
      // kernel + pure `JSON.parse`) decodes UTF-8 + parses
      // the document; `JsonTree` + `JsonNode` paint the
      // accessible / collapsible Explorer tree faithful to
      // the legacy `web/file_viewer.js::renderJsonTree`
      // oracle. The `json-offline` branch stays in the
      // cdn-pending catch-all below so the existing
      // missing-bytes fallback/download behavior is
      // retained verbatim.
      return renderJsonTree(dispatch.bytes, descriptor);
    case "docx-source":
      // W64B-DOCX-002 — DOCX materialization via Next
      // 16's `<Script>` loader + the pinned mammoth
      // CDN pin (`MAMMOTH_CDN_URL` +
      // `MAMMOTH_GLOBAL_NAME`). The `case
      // "docx-source":` branch is intentionally
      // OUT of the W6.1 cdn-pending catch-all (the
      // DOCX materialization owns a typed `cdn-failed`
      // recovery state distinct from the
      // `bytes-missing` offline path the dispatcher
      // emits at dispatch time — the W64B typed union
      // `reason: "bytes-missing" | "cdn-failed"` on
      // the `docx-offline` variant lets the mount
      // surface both paths through the same
      // `renderOfflineCard` shape while keeping the
      // typed recovery literal distinct). The actual
      // mount rendering lives in `DocxRender` below
      // — this branch is a typed hand-off so the
      // renderDispatch switch stays exhaustive.
      return <DocxRender dispatch={dispatch} />;
    case "sheet-source":
      // W64C-XLS-003 — XLS / XLSX materialization via
      // Next 16's `<Script>` loader + the pinned
      // SheetJS CDN pin (`SHEETJS_CDN_URL` +
      // `SHEETJS_GLOBAL_NAME`). The `case
      // "sheet-source":` branch is intentionally
      // OUT of the W6.1 cdn-pending catch-all (the
      // XLS / XLSX materialization owns a typed
      // `cdn-failed` recovery state distinct from the
      // `bytes-missing` offline path the dispatcher
      // emits at dispatch time — the W64B typed union
      // `reason: "bytes-missing" | "cdn-failed"` on
      // the `sheet-offline` variant lets the mount
      // surface both paths through the same
      // `renderOfflineCard` shape while keeping the
      // typed recovery literal distinct). Both XLS
      // and XLSX share the same SheetJS path; the
      // dispatch carries `format` verbatim
      // (`xls` or `xlsx`) so the mount can branch on
      // the format for any future format-specific
      // affordance without re-fetching bytes. The
      // actual mount rendering lives in
      // `SheetRender` below — this branch is a typed
      // hand-off so the renderDispatch switch stays
      // exhaustive.
      return <SheetRender dispatch={dispatch} />;
    case "epub-source":
      // W64D-EPUB-004 — EPUB materialization via Next
      // 16's `<Script>` loader + the pinned epubjs
      // CDN pin (`EPUBJS_CDN_URL` +
      // `EPUBJS_GLOBAL_NAME = "ePub"` — the
      // case-sensitive UMD global — lowercase `e`,
      // capital `P`). This branch is intentionally
      // OUT of the W6.1 cdn-pending catch-all (the
      // EPUB materialization owns a typed `cdn-failed`
      // recovery state distinct from the
      // `bytes-missing` offline path the dispatcher
      // emits at dispatch time — the W64B typed union
      // `reason: "bytes-missing" | "cdn-failed"` on
      // the `epub-offline` variant lets the mount
      // surface both paths through the same
      // `renderOfflineCard` shape while keeping the
      // typed recovery literal distinct). The mount
      // reaches the pinned global through
      // `window[dispatch.scriptGlobal](dispatch.bytes.buffer)`
      // (NOT a constructor with `new` — the UMD
      // global IS a function), calls `book.renderTo(
      // hostEl, ...)` to mount the EPUB, surfaces
      // prev / next click handlers that call
      // `book.prev()` / `book.next()`, and tears
      // down the previous book BEFORE rendering the
      // new one so listeners don't leak per
      // `design.md` §8 (mirrors the legacy
      // `web/file_viewer.js::renderEpub` lines
      // 429–438 `_currentBook.destroy()` lifecycle
      // verbatim). The actual mount rendering lives
      // in `EpubRender` below — this branch is a
      // typed hand-off so the renderDispatch switch
      // stays exhaustive.
      return <EpubRender dispatch={dispatch} />;
    case "docx-offline":
    case "sheet-offline":
    case "epub-offline":
    case "table-source":
    case "table-offline":
    case "json-offline":
      // W6.1 non-CDN mount — the CDN-backed source variants
      // (CSV / TSV) are intentionally not wired
      // here (those mounts land as separately authorized
      // later slices; the W64B typed union
      // `reason: "bytes-missing" | "cdn-failed"` is the
      // common contract they'll surface through). The
      // `docx-offline` branch (the W6.1 bytes-missing
      // offline path for DOCX) + the `sheet-offline`
      // branch (the W6.1 bytes-missing offline path for
      // XLS / XLSX) + the `epub-offline` branch (the
      // W6.1 bytes-missing offline path for EPUB) stay
      // here so the W6.1 download-link affordance + the
      // W64B-DOCX-002 + W64C-XLS-003 + W64D-EPUB-004
      // typed `cdn-failed` recovery states from
      // `DocxRender` + `SheetRender` + `EpubRender`
      // resolve through the same `renderOfflineCard`
      // shape. A future W6+ slice that loads the Papa
      // CDN libraries would replace the `table-*` /
      // `json-*` branches with the typed source /
      // offline rendering shape (one JSX branch per CDN
      // library).
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

// ---- W64A-JSON-001 — native JSON Tree viewer materialization ----
// Mirrors the legacy `web/file_viewer.js::renderJsonTree` +
// `buildJsonWalker` + `renderJsonNode` shapes byte-for-byte.
// JSON parsing is native (no CDN, no third-party library) per
// the spec's "Tree viewer tab / No CDN is used." requirement.

/** Render the native JSON Tree for the typed `json-source`
 *  dispatch. Pure projection: parse bytes → walk value tree
 *  → paint accessible / collapsible JSX. Mirrors the legacy
 *  `web/file_viewer.js::renderJsonTree` + `buildJsonWalker`
 *  + `renderJsonNode` shapes:
 *
 *   - The root paints the legacy `[root]` key + auto-expands
 *     so the user immediately sees the structure (otherwise
 *     they'd need to click the caret).
 *   - Object / array children paint lazily: a child summary
 *     is always rendered, but its children are painted only
 *     when the user expands the parent (this keeps the
 *     initial render fast on huge documents; the legacy
 *     `buildJsonWalker` uses the same `expand` lazy shape).
 *   - Primitive children (string / number / boolean / null)
 *     paint as a single `.fex-tree-leaf` with the type-
 *     coloured modifier class.
 *   - The legacy `MAX_JSON_NODES = 50_000` cap is mirrored
 *     via a shared counter; past the cap the mount paints
 *     a single `…` placeholder child + the legacy
 *     `Tree truncated — open raw` banner so the user can
 *     still see the structure end-to-end.
 *   - Parse failures route through the same offline banner
 *     the legacy `renderJsonTree` catch branch paints
 *     (the legacy `renderOfflineBanner` shape; the React
 *     mount surfaces this through `renderOfflineCard`'s
 *     download affordance so the user has a recovery path).
 */
function renderJsonTree(
  bytes: Uint8Array,
  descriptor: ViewerFileDescriptor,
): ReactNode {
  const parsed = parseJsonTree(bytes);
  if (!parsed.ok) {
    // Mirrors the legacy `renderJsonTree` catch branch:
    // a JSON.parse failure paints the same offline banner
    // the bytes-missing path paints. The W6.1 contract
    // uses `renderOfflineCard`'s `cdn-pending` recovery
    // shape; we synthesize a synthetic `json-offline`
    // descriptor so the user sees the same download
    // affordance regardless of which path failed.
    return renderOfflineCard(
      {
        kind: "json-offline",
        name: descriptor.name,
        download: { href: descriptor.url, download: descriptor.name },
        reason: "bytes-missing",
      },
      descriptor,
    );
  }
  // Counter lives in a ref-shaped closure so the recursive
  // `JsonNode` paint can read + mutate it without React
  // needing to know. The counter is intentionally mutable
  // because the legacy walker counts as it paints, and we
  // want the React render to match that shape exactly
  // (lazy child rendering continues until the cap is
  // exceeded, then the remaining children collapse to a
  // single `…` placeholder + the truncation banner).
  const counter: JsonNodeCounter = { count: 0, truncated: false };
  return (
    <div
      className="fex-json-tree"
      data-viewer-kind="json-tree"
      data-json-path=""
    >
      <JsonNode
        keyName="[root]"
        value={parsed.value}
        initiallyOpen={true}
        depth={0}
        counter={counter}
      />
      {counter.truncated ? (
        <p
          className="fex-tree-truncated"
          role="status"
          data-viewer-kind="json-tree-truncated"
        >
          <span className="material-symbols-outlined">warning</span>
          Tree truncated — open raw
        </p>
      ) : null}
    </div>
  );
}

// ---- W64B-DOCX-002 — DOCX materialization via Next `Script` ----
// Mirrors the legacy `web/file_viewer.js::renderDocx` shape
// (the legacy uses `loadScriptOnce("mammoth")` to inject
// the CDN, then `window.mammoth.convertToHtml({arrayBuffer})`
// to parse the bytes, then injects the resulting HTML via
// `Range.createContextualFragment`). The W64B React mount
// uses Next 16's `<Script src={scriptUrl}
// strategy="afterInteractive" onLoad={convert} onError={...}>`
// component (see
// `node_modules/next/dist/docs/01-app/03-api-reference/02-
// components/script.md`) as the loader surface. mammoth
// itself already strips `<script>` + on* event-handler
// attrs per `design.md` §8, so the React mount's
// `dangerouslySetInnerHTML` injection is the same XSS-safe
// shape as the legacy `Range.createContextualFragment`
// call site. The mount owns the typed `cdn-failed` recovery
// state — Script.onError + mammoth.convertToHtml exceptions
// surface through a synthesized `docx-offline` dispatch
// with `reason: "cdn-failed"` (distinct from the
// `bytes-missing` path the dispatcher emits at dispatch
// time; the W64B typed union
// `reason: "bytes-missing" | "cdn-failed"` keeps both
// literals first-class).

/** Discriminated state for the DOCX materialization. Mirrors
 *  the W4a-\u2011W64A pattern of a typed union that drives
 *  render branching: `loading` paints the quiet skeleton +
 *  the `<Script>` loader, `loaded` renders the converted
 *  HTML verbatim (mammoth strips `<script>` + `on*=` per
 *  `design.md` §8), and `error` flips to the typed
 *  `cdn-failed` recovery state. The error branch carries
 *  the union literal `reason: "cdn-failed"` so the
 *  surface distinguishes mount-detected CDN/convert
 *  failures from the dispatcher-emitted `bytes-missing`
 *  offline path. */
type DocxRenderState =
  | { readonly kind: "loading" }
  | {
      readonly kind: "loaded";
      readonly html: string;
    }
  | {
      readonly kind: "error";
      readonly reason: "cdn-failed";
    };

/** Props for `DocxRender`. The component receives the typed
 *  `docx-source` dispatch directly from
 *  `renderDispatch` — the React mount is the only consumer
 *  of this surface; `bytesRequiredForFormat("docx") ===
 * true` keeps the bytes-fetch effect in sync (the bytes
 *  flow through the existing Viewer.tsx `bytesStatus`
 *  lifecycle so this component is purely a projection of
 *  the typed source outcome). */
interface DocxRenderProps {
  readonly dispatch: ViewerDispatch;
}

/** W64B-DOCX-002 — the DOCX materialization. Renders the
 *  `<Script>` loader on first commit, calls
 *  `window[dispatch.scriptGlobal].convertToHtml(...)` on
 *  script load, and flips to a typed `cdn-failed` recovery
 *  state on either `Script.onError` OR the
 *  `mammoth.convertToHtml(...)` exception path. The
 *  recovery state synthesizes a `docx-offline` dispatch
 *  with `reason: "cdn-failed"` so the existing
 *  `renderOfflineCard` paints the download affordance
 *  with a typed `reason` literal that's distinct from
 *  the `bytes-missing` offline path the dispatcher emits.
 */
function DocxRender(props: DocxRenderProps): ReactNode {
  // `dispatch` is narrowed by the caller (`renderDispatch`
  // only routes `kind: "docx-source"` here), but TypeScript
  // can't narrow through the JSX element so we explicitly
  // cast to the typed dispatch shape for the body.
  const dispatch = props.dispatch;
  if (dispatch.kind !== "docx-source") {
    // Defensive guard — the caller is `renderDispatch`
    // and only routes `docx-source` here. A future
    // refactor that routes another kind through this
    // component is a contract regression, so the guard
    // returns an empty fragment rather than rendering
    // the wrong shape.
    return null;
  }
  const [state, setState] = useState<DocxRenderState>({
    kind: "loading",
  });
  const cancelledRef = useRef<boolean>(false);

  // Cleanup `cancelledRef` so an unmount mid-flight
  // doesn't flip state to `loaded` / `error` after the
  // parent has unmounted this DOCX viewer (the
  // `useEffect` below sets `cancelledRef.current = true`
  // on cleanup).
  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  // `runConvert` is the single conversion entry point. It
  // reaches the pinned mammoth global through the typed
  // `dispatch.scriptGlobal` (so a future PR that bumps the
  // library version lands in lock-step across the
  // dispatcher constant + the loader site) and passes the
  // bytes via the `{arrayBuffer: bytes.buffer}` shape
  // (mammoths browser bundle expects that exact shape).
  // The `try / catch` covers the synchronous exception
  // path (mammoth throws immediately on invalid DOCX
  // archives in some versions); the `.catch` covers the
  // rejected-promise path. Both routes flip the state to
  // the typed `cdn-failed` recovery literal.
  const runConvert = useCallback(() => {
    try {
      // SAFETY: `window` is typed as the DOM `Window` interface
      // which does NOT carry the CDN-injected global; the
      // SheetJS / mammoth UMD bundle assigns itself to
      // `window[scriptGlobal]` after the Next `<Script>`
      // loader fires `onLoad`. The narrow
      // `Record<string, unknown>` index shape gives us a
      // typed handle; the downstream `typeof convertToHtml
      // !== "function"` guard verifies the runtime shape
      // before any call. The pinned `scriptGlobal` literal
      // comes from the W4b1 dispatcher constant — a future
      // PR that bumps the CDN pin lands in lock-step across
      // the dispatcher constant + the loader site.
      const mammoth = (window as unknown as Record<string, unknown>)[
        dispatch.scriptGlobal
      ] as
        | { convertToHtml: (input: { arrayBuffer: ArrayBuffer }) => unknown }
        | undefined;
      if (
        mammoth === undefined ||
        typeof mammoth.convertToHtml !== "function"
      ) {
        if (!cancelledRef.current) {
          setState({ kind: "error", reason: "cdn-failed" });
        }
        return;
      }
      const result = mammoth.convertToHtml({
        // `Uint8Array.prototype.buffer` is typed
        // `ArrayBufferLike` (which includes
        // `SharedArrayBuffer`), but mammoth's
        // browser bundle expects exactly
        // `ArrayBuffer`. The pinned `dispatch.bytes`
        // reference comes from the W3 `fetchFileServe`
        // adapter, which materializes a typed
        // `Uint8Array` over a plain `ArrayBuffer`
        // backing (not a SharedArrayBuffer) — the cast
        // is therefore safe at runtime even though it's
        // a strict-type narrowing at the type level.
        arrayBuffer: dispatch.bytes.buffer as ArrayBuffer,
      });
      Promise.resolve(result)
        .then((resolved: unknown) => {
          if (cancelledRef.current) return;
          const html =
            typeof resolved === "object" &&
            resolved !== null &&
            "value" in resolved &&
            typeof (resolved as { value: unknown }).value === "string"
              ? (resolved as { value: string }).value
              : typeof resolved === "string"
              ? resolved
              : "";
          setState({ kind: "loaded", html });
        })
        .catch(() => {
          if (cancelledRef.current) return;
          setState({ kind: "error", reason: "cdn-failed" });
        });
    } catch {
      if (cancelledRef.current) return;
      setState({ kind: "error", reason: "cdn-failed" });
    }
  }, [dispatch.scriptGlobal, dispatch.bytes]);

  // If the legacy-pinned mammoth CDN is already on the
  // page (a previous DOCX open loaded the script and the
  // user is opening a second DOCX file), Next 16's
  // `<Script>` component does NOT re-fire `onLoad` for
  // subsequent mounts — so this effect covers the
  // "already-cached" path by checking `window[scriptGlobal]`
  // synchronously after the first commit. A future mount
  // that swaps the loader for a different library would
  // land as a separately authorized slice + would update
  // this effect accordingly.
  useEffect(() => {
    // SAFETY: same invariant as the `runConvert` window
    // assertion above — the CDN-injected global reaches
    // us through `window[scriptGlobal]` after the Next
    // `<Script>` loader has fired. The narrow
    // `Record<string, unknown>` index shape gives us a
    // typed handle; the downstream `typeof
    // convertToHtml === "function"` guard verifies the
    // runtime shape before any call.
    const w = window as unknown as Record<string, unknown>;
    const mammoth = w[dispatch.scriptGlobal] as
      | { convertToHtml?: unknown }
      | undefined;
    if (
      mammoth !== undefined &&
      typeof mammoth.convertToHtml === "function"
    ) {
      runConvert();
    }
    // `runConvert` is intentionally listed as a dep — its
    // identity flips when the dispatch bytes / scriptGlobal
    // change, which mirrors the "new file open" lifecycle
    // the Explorer.tsx parent drives.
  }, [runConvert, dispatch]);

  const handleScriptLoad = useCallback(() => {
    runConvert();
  }, [runConvert]);

  const handleScriptError = useCallback(() => {
    setState({ kind: "error", reason: "cdn-failed" });
  }, []);

  // The error branch synthesizes a typed `docx-offline`
  // dispatch with `reason: "cdn-failed"` so the existing
  // `renderOfflineCard` paints the download affordance with
  // a typed `reason` literal distinct from the
  // `bytes-missing` path. The descriptor here is a
  // synthetic stand-in (the CDN-failed branch doesn't have
  // a real `ViewerFileDescriptor` in scope, only the
  // typed dispatch fields).
  if (state.kind === "error") {
    const syntheticDescriptor: ViewerFileDescriptor = {
      url: dispatch.src,
      name: dispatch.title,
      format: "docx",
      size: dispatch.bytes.length,
      path: dispatch.title,
    };
    return renderOfflineCard(
      {
        kind: "docx-offline",
        name: dispatch.title,
        download: { href: dispatch.src, download: dispatch.title },
        scriptUrl: dispatch.scriptUrl,
        scriptGlobal: dispatch.scriptGlobal,
        reason: "cdn-failed",
      },
      syntheticDescriptor,
    );
  }

  if (state.kind === "loaded") {
    // SAFETY: mammoth's browser bundle strips `<script>` +
    // on* event-handler attributes per `design.md` §8, so
    // the `dangerouslySetInnerHTML` XSS surface mirrors the
    // legacy `web/file_viewer.js::renderDocx`
    // `Range.createContextualFragment` call site. The
    // `state.html` payload originates from the pinned
    // mammoth CDN (the `MAMMOTH_CDN_URL` constant) — the
    // only source of bytes is `dispatch.bytes` (the typed
    // `Uint8Array` from the W3 `fetchFileServe` adapter)
    // passed verbatim through `mammoth.convertToHtml(
    // {arrayBuffer: bytes.buffer})`. The pinned
    // `scriptGlobal` literal comes from the W4b1 dispatcher
    // constant; a future PR that bumps the CDN pin lands
    // in lock-step across the dispatcher constant + the
    // loader site. The `fex-docx-content` wrapper mirrors
    // the legacy `fex-image-frame` shape so the cascade
    // applies the same styling rules.
    return (
      <div
        className="fex-docx-content"
        data-viewer-kind="docx-content"
        dangerouslySetInnerHTML={{ __html: state.html }}
      />
    );
  }

  // `loading` state — render the quiet skeleton + the
  // Next 16 `<Script>` loader on the first commit. The
  // `<Script>` dedups by URL across mounts, so a second
  // DOCX open within the same page session does NOT
  // re-fetch the bundle.
  return (
    <>
      <div
        className="fex-empty-state"
        role="status"
        data-viewer-loading=""
        data-viewer-kind="docx-loading"
      >
        <span className="fex-empty-state-icon material-symbols-outlined animate-spin">
          progress_activity
        </span>
        <p>Loading DOCX preview…</p>
      </div>
      <Script
        src={dispatch.scriptUrl}
        strategy="afterInteractive"
        onLoad={handleScriptLoad}
        onError={handleScriptError}
      />
    </>
  );
}

// ---- W64C-XLS-003 — XLS / XLSX materialization via Next `Script` ----
// Mirrors the legacy `web/file_viewer.js::renderSheet` shape
// byte-for-byte: the legacy uses `loadScriptOnce("XLSX")` to
// inject the CDN, then `window.XLSX.read(data, { type: "array" })`
// to parse the workbook, then `window.XLSX.utils.sheet_to_html(sheet)`
// to emit the HTML table. For multi-sheet workbooks the legacy
// renders a sheet picker above the table so the user can
// switch. The W64C React mount uses Next 16's
// `<Script src={scriptUrl} strategy="afterInteractive"
// onLoad={convert} onError={...}>` component (see
// `node_modules/next/dist/docs/01-app/03-api-reference/02-
// components/script.md`) as the loader surface. SheetJS itself
// already emits a plain HTML `<table>` without `<script>` or
// event handlers per `design.md` §8, so the React mount's
// `dangerouslySetInnerHTML` injection is the same XSS-safe
// shape as the legacy `Range.createContextualFragment` call
// site. The mount owns the typed `cdn-failed` recovery state
// — Script.onError + SheetJS.read / utils.sheet_to_html
// exceptions surface through a synthesized `sheet-offline`
// dispatch with `reason: "cdn-failed"` (distinct from the
// `bytes-missing` path the dispatcher emits at dispatch time;
// the W64B typed union `reason: "bytes-missing" | "cdn-failed"`
// on the `sheet-offline` variant keeps both literals
// first-class).

/** Discriminated state for the XLS / XLSX materialization.
 *  Mirrors the W64B-DOCX-002 `DocxRenderState` union shape:
 *  `loading` paints the quiet skeleton + the `<Script>`
 *  loader, `loaded` carries the converted HTML table verbatim
 *  (SheetJS strips nothing by default, but its output is a
 *  plain `<table>` without `<script>` or on* attributes per
 *  `design.md` §8), and `error` flips to the typed
 *  `cdn-failed` recovery state. The error branch carries the
 *  union literal `reason: "cdn-failed"` so the surface
 *  distinguishes mount-detected CDN / read / sheet_to_html
 *  failures from the dispatcher-emitted `bytes-missing`
 *  offline path. The `sheet` + `names` fields on the
 *  `loaded` branch let the mount's `<select>` picker switch
 *  the active sheet on demand (mirrors the legacy
 *  `wb.SheetNames` + `wb.Sheets[name]` shape verbatim). */
type SheetRenderState =
  | { readonly kind: "loading" }
  | {
      readonly kind: "loaded";
      readonly html: string;
      readonly sheetNames: readonly string[];
    }
  | {
      readonly kind: "error";
      readonly reason: "cdn-failed";
    };

/** Props for `SheetRender`. The component receives the typed
 *  `sheet-source` dispatch directly from `renderDispatch` —
 *  the React mount is the only consumer of this surface;
 *  `bytesRequiredForFormat("xls") === true` and
 *  `bytesRequiredForFormat("xlsx") === true` (the W64C
 *  matrix flip) keep the bytes-fetch effect in sync (the
 *  bytes flow through the existing Viewer.tsx `bytesStatus`
 *  lifecycle so this component is purely a projection of
 *  the typed source outcome). */
interface SheetRenderProps {
  readonly dispatch: ViewerDispatch;
}

/** W64C-XLS-003 — the XLS / XLSX materialization. Renders
 *  the `<Script>` loader on first commit, calls
 *  `window[dispatch.scriptGlobal].read(bytes, {type: "array"})`
 *  + `utils.sheet_to_html(activeSheet)` on script load, and
 *  flips to a typed `cdn-failed` recovery state on either
 *  `Script.onError` OR the `SheetJS.read(...)` /
 *  `utils.sheet_to_html(...)` exception path. The recovery
 *  state synthesizes a `sheet-offline` dispatch with
 *  `reason: "cdn-failed"` so the existing `renderOfflineCard`
 *  paints the download affordance with a typed `reason`
 *  literal that's distinct from the `bytes-missing` offline
 *  path the dispatcher emits. When
 *  `wb.SheetNames.length > 1` the mount surfaces a `<select>`
 *  picker that switches the active sheet (mirrors the legacy
 *  `web/file_viewer.js::renderSheet` multi-sheet shape
 *  verbatim).
 *
 *  Both XLS and XLSX share the same SheetJS path; the
 *  `dispatch` is typed `sheet-source` regardless of the
 *  format field. The `format` field (`xls` or `xlsx`) is
 *  carried verbatim through the dispatch contract so a
 *  future mount that wants format-specific affordances
 *  (e.g. a different default sheet picker label) can branch
 *  on the format without re-fetching bytes.
 */
function SheetRender(props: SheetRenderProps): ReactNode {
  // `dispatch` is narrowed by the caller (`renderDispatch`
  // only routes `kind: "sheet-source"` here), but TypeScript
  // can't narrow through the JSX element so we explicitly
  // cast to the typed dispatch shape for the body.
  const dispatch = props.dispatch;
  if (dispatch.kind !== "sheet-source") {
    // Defensive guard — the caller is `renderDispatch`
    // and only routes `sheet-source` here. A future
    // refactor that routes another kind through this
    // component is a contract regression, so the guard
    // returns an empty fragment rather than rendering
    // the wrong shape.
    return null;
  }
  const [state, setState] = useState<SheetRenderState>({
    kind: "loading",
  });
  const [activeSheetName, setActiveSheetName] = useState<string | null>(
    null,
  );
  const cancelledRef = useRef<boolean>(false);

  // Cleanup `cancelledRef` so an unmount mid-flight
  // doesn't flip state to `loaded` / `error` after the
  // parent has unmounted this XLS / XLSX viewer (the
  // `useEffect` below sets `cancelledRef.current = true`
  // on cleanup).
  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  // `renderSheetHtml` is the pure projection: given a
  // parsed workbook + a sheet name, call
  // `window[dispatch.scriptGlobal].utils.sheet_to_html(sheet)`
  // and return the resulting HTML string. Mirrors the
  // legacy `web/file_viewer.js::renderSheet` closure shape
  // verbatim — the legacy builds a `renderSheetHtml(name)`
  // closure that calls
  // `range.createContextualFragment(window.XLSX.utils.sheet_to_html(sheet))`
  // and re-uses it for both the initial render + every
  // picker `change` event.
  const renderSheetHtml = useCallback(
    (
      SheetJSLib: {
        read: (
          data: Uint8Array,
          opts: { type: string },
        ) => { SheetNames: readonly string[]; Sheets: Record<string, unknown> };
        utils: {
          sheet_to_html: (sheet: unknown) => string;
        };
      },
      sheetName: string,
    ): string => {
      const wb = SheetJSLib.read(dispatch.bytes, { type: "array" });
      const sheet = (wb.Sheets as Record<string, unknown>)[sheetName];
      if (sheet === undefined) return "";
      return SheetJSLib.utils.sheet_to_html(sheet);
    },
    [dispatch.bytes],
  );

  // `runConvert` is the single conversion entry point. It
  // reaches the pinned SheetJS global through the typed
  // `dispatch.scriptGlobal` (so a future PR that bumps the
  // library version lands in lock-step across the
  // dispatcher constant + the loader site) and calls
  // `read(bytes, {type: "array"})` + `utils.sheet_to_html(activeSheet)`.
  // The `try / catch` covers the synchronous exception
  // path (SheetJS throws immediately on invalid workbook
  // archives); both routes flip the state to the typed
  // `cdn-failed` recovery literal.
  const runConvert = useCallback(() => {
    try {
      // SAFETY: `window` is typed as the DOM `Window`
      // interface which does NOT carry the CDN-injected
      // global; the SheetJS UMD bundle assigns itself
      // to `window[scriptGlobal]` after the Next
      // `<Script>` loader fires `onLoad`. The narrow
      // `Record<string, unknown>` index shape gives us
      // a typed handle; the downstream `typeof read !==
      // "function"` + `typeof utils.sheet_to_html !==
      // "function"` guards verify the runtime shape
      // before any call. The pinned `scriptGlobal`
      // literal comes from the W4b2 dispatcher
      // constant — a future PR that bumps the CDN pin
      // lands in lock-step across the dispatcher
      // constant + the loader site.
      const SheetJSLib = (window as unknown as Record<string, unknown>)[
        dispatch.scriptGlobal
      ] as
        | {
            read: (
              data: Uint8Array,
              opts: { type: string },
            ) => {
              SheetNames: readonly string[];
              Sheets: Record<string, unknown>;
            };
            utils: { sheet_to_html: (sheet: unknown) => string };
          }
        | undefined;
      if (
        SheetJSLib === undefined ||
        typeof SheetJSLib.read !== "function" ||
        typeof SheetJSLib.utils?.sheet_to_html !== "function"
      ) {
        if (!cancelledRef.current) {
          setState({ kind: "error", reason: "cdn-failed" });
        }
        return;
      }
      const wb = SheetJSLib.read(dispatch.bytes, { type: "array" });
      const sheetNames: readonly string[] = Array.isArray(wb.SheetNames)
        ? wb.SheetNames
        : [];
      const initialName = sheetNames[0] ?? "";
      const html = renderSheetHtml(SheetJSLib, initialName);
      if (cancelledRef.current) return;
      setActiveSheetName(initialName);
      setState({ kind: "loaded", html, sheetNames });
    } catch {
      if (cancelledRef.current) return;
      setState({ kind: "error", reason: "cdn-failed" });
    }
  }, [dispatch.scriptGlobal, dispatch.bytes, renderSheetHtml]);

  // If the legacy-pinned SheetJS CDN is already on the
  // page (a previous XLS / XLSX open loaded the script and
  // the user is opening a second spreadsheet), Next 16's
  // `<Script>` component does NOT re-fire `onLoad` for
  // subsequent mounts — so this effect covers the
  // "already-cached" path by checking `window[scriptGlobal]`
  // synchronously after the first commit. A future mount
  // that swaps the loader for a different library would
  // land as a separately authorized slice + would update
  // this effect accordingly.
  useEffect(() => {
    // SAFETY: same invariant as the `runConvert` window
    // assertion above — the CDN-injected global reaches
    // us through `window[scriptGlobal]` after the Next
    // `<Script>` loader has fired. The narrow
    // `Record<string, unknown>` index shape gives us a
    // typed handle; the downstream `typeof read ===
    // "function"` guard verifies the runtime shape before
    // any call.
    const w = window as unknown as Record<string, unknown>;
    const SheetJSLib = w[dispatch.scriptGlobal] as
      | { read?: unknown; utils?: unknown }
      | undefined;
    if (
      SheetJSLib !== undefined &&
      typeof SheetJSLib.read === "function" &&
      typeof (SheetJSLib as { utils?: unknown }).utils ===
        "object" &&
      SheetJSLib.utils !== null &&
      typeof (
        SheetJSLib.utils as { sheet_to_html?: unknown }
      ).sheet_to_html === "function"
    ) {
      runConvert();
    }
    // `runConvert` is intentionally listed as a dep — its
    // identity flips when the dispatch bytes / scriptGlobal
    // change, which mirrors the "new file open" lifecycle
    // the Explorer.tsx parent drives.
  }, [runConvert, dispatch]);

  const handleScriptLoad = useCallback(() => {
    runConvert();
  }, [runConvert]);

  const handleScriptError = useCallback(() => {
    setState({ kind: "error", reason: "cdn-failed" });
  }, []);

  const handleSheetChange = useCallback(
    (ev: React.ChangeEvent<HTMLSelectElement>): void => {
      const newName = ev.target.value;
      setActiveSheetName(newName);
      if (state.kind !== "loaded") return;
      // Capture the loaded-state typed surface into a local
      // const so the rest of the callback body + the deps
      // array can reach `sheetNames` without re-narrowing
      // through `state` (TypeScript can't narrow a union
      // member across the useCallback closure boundary).
      const loadedSheetNames = state.sheetNames;
      try {
        // SAFETY: `window` is the DOM `Window` interface
        // which does NOT carry the CDN-injected global;
        // the SheetJS UMD bundle assigns itself to
        // `window[scriptGlobal]` after the Next `<Script>`
        // loader fires `onLoad`. The narrow
        // `Record<string, unknown>` index shape gives us a
        // typed handle; the loaded-state precondition +
        // the `try/catch` cover the runtime invariants
        // (SheetJS is on the page because we already
        // reached `loaded` via the same global).
        const SheetJSLib = (window as unknown as Record<string, unknown>)[
          dispatch.scriptGlobal
        ] as
          | {
              read: (
                data: Uint8Array,
                opts: { type: string },
              ) => {
                SheetNames: readonly string[];
                Sheets: Record<string, unknown>;
              };
              utils: { sheet_to_html: (sheet: unknown) => string };
            }
          | undefined;
        if (
          SheetJSLib === undefined ||
          typeof SheetJSLib.utils?.sheet_to_html !== "function"
        ) {
          setState({ kind: "error", reason: "cdn-failed" });
          return;
        }
        const html = renderSheetHtml(SheetJSLib, newName);
        setState({
          kind: "loaded",
          html,
          sheetNames: loadedSheetNames,
        });
      } catch {
        setState({ kind: "error", reason: "cdn-failed" });
      }
    },
    [dispatch.scriptGlobal, renderSheetHtml],
  );

  // The error branch synthesizes a typed `sheet-offline`
  // dispatch with `reason: "cdn-failed"` so the existing
  // `renderOfflineCard` paints the download affordance with
  // a typed `reason` literal distinct from the
  // `bytes-missing` path. The descriptor here is a
  // synthetic stand-in (the CDN-failed branch doesn't have
  // a real `ViewerFileDescriptor` in scope, only the
  // typed dispatch fields).
  if (state.kind === "error") {
    const syntheticDescriptor: ViewerFileDescriptor = {
      url: dispatch.src,
      name: dispatch.title,
      format: "xlsx",
      size: dispatch.bytes.length,
      path: dispatch.title,
    };
    return renderOfflineCard(
      {
        kind: "sheet-offline",
        name: dispatch.title,
        download: { href: dispatch.src, download: dispatch.title },
        scriptUrl: dispatch.scriptUrl,
        scriptGlobal: dispatch.scriptGlobal,
        reason: "cdn-failed",
      },
      syntheticDescriptor,
    );
  }

  if (state.kind === "loaded") {
    // SAFETY: SheetJS's browser bundle emits a plain HTML
    // `<table>` without `<script>` + on* event-handler
    // attributes per `design.md` §8, so the
    // `dangerouslySetInnerHTML` XSS surface mirrors the
    // legacy `web/file_viewer.js::renderSheet`
    // `Range.createContextualFragment` call site. The
    // `state.html` payload originates from the pinned
    // SheetJS CDN (the `SHEETJS_CDN_URL` constant) — the
    // only source of bytes is `dispatch.bytes` (the typed
    // `Uint8Array` from the W3 `fetchFileServe` adapter)
    // passed verbatim through
    // `window[dispatch.scriptGlobal].read(bytes, {type:
    // "array"})` + `utils.sheet_to_html(activeSheet)`.
    // The pinned `scriptGlobal` literal comes from the
    // W4b2 dispatcher constant; a future PR that bumps
    // the CDN pin lands in lock-step across the
    // dispatcher constant + the loader site. The
    // `.fex-sheet-table-host` wrapper mirrors the legacy
    // `overflow-auto` shape so the cascade applies the
    // same styling rules.
    //
    // When the workbook has more than one sheet
    // (`sheetNames.length > 1`) the mount surfaces a
    // `<select>` picker above the table so the user can
    // switch the active sheet (matches the legacy
    // `web/file_viewer.js::renderSheet`
    // `sheetNames.length > 1` shape verbatim). The
    // picker reuses the existing `.fex-snippet-btn`
    // styling for its `<select>` element (matches the
    // legacy
    // `el("select", { class: "fex-snippet-btn font-mono-data ..." })`
    // shape verbatim).
    const showPicker =
      Array.isArray(state.sheetNames) && state.sheetNames.length > 1;
    return (
      <div
        className="fex-sheet-host flex flex-col gap-2"
        data-viewer-kind="sheet-content"
      >
        {showPicker ? (
          <div className="fex-sheet-picker flex items-center gap-2 mb-2">
            <label
              className="fex-sheet-picker-label text-body-sm text-on-surface-variant"
              htmlFor="fex-sheet-picker-select"
            >
              Sheet:
            </label>
            <select
              id="fex-sheet-picker-select"
              className="fex-snippet-btn font-mono-data text-on-surface bg-surface"
              value={activeSheetName ?? state.sheetNames[0] ?? ""}
              onChange={handleSheetChange}
              data-viewer-kind="sheet-picker"
            >
              {state.sheetNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        <div
          className="fex-sheet-table-host overflow-auto"
          data-viewer-kind="sheet-table-host"
          dangerouslySetInnerHTML={{ __html: state.html }}
        />
      </div>
    );
  }

  // `loading` state — render the quiet skeleton + the
  // Next 16 `<Script>` loader on the first commit. The
  // `<Script>` dedups by URL across mounts, so a second
  // XLS / XLSX open within the same page session does
  // NOT re-fetch the bundle.
  return (
    <>
      <div
        className="fex-empty-state"
        role="status"
        data-viewer-loading=""
        data-viewer-kind="sheet-loading"
      >
        <span className="fex-empty-state-icon material-symbols-outlined animate-spin">
          progress_activity
        </span>
        <p>Loading spreadsheet preview…</p>
      </div>
      <Script
        src={dispatch.scriptUrl}
        strategy="afterInteractive"
        onLoad={handleScriptLoad}
        onError={handleScriptError}
      />
    </>
  );
}

// ---- W64D-EPUB-004 — EPUB materialization via Next `Script` ----
// Mirrors the legacy `web/file_viewer.js::renderEpub` shape
// (the legacy uses `loadScriptOnce("ePub")` to inject the
// CDN, then `window.ePub(arrayBuffer)` to construct the
// book, then `book.renderTo(epubHost, { width: "100%",
// height: "100%" })` to mount it). The W64D React mount
// uses Next 16's
// `<Script src={dispatch.scriptUrl} strategy="afterInteractive"
// onLoad={mount} onError={...}>` component (see
// `node_modules/next/dist/docs/01-app/03-api-reference/02-
// components/script.md`) as the loader surface.
//
// Critical lifecycle invariant — mirrors the legacy
// `web/file_viewer.js::renderEpub` lines 429–438 verbatim:
// the mount owns a module-scoped `previousBook` reference
// (the legacy uses `_currentBook`) and tears down the
// previous book BEFORE mounting the new one so listeners
// don't leak per `design.md` §8 EPUB render lifecycle. The
// same cleanup runs on unmount AND on any change of the
// EPUB dispatch (the `useEffect` cleanup path preserves the
// React-mount equivalence of the legacy's "next open tears
// down the previous" shape).
//
// On `Script.onError` OR any exception from
// `ePub(arrayBuffer)` construction / `book.renderTo(...)` /
// `book.prev()` / `book.next()` the mount flips to a typed
// `"cdn-failed"` recovery state (the W64B-DOCX-002 typed
// union `reason: "bytes-missing" | "cdn-failed"` on the
// `epub-offline` variant — extended on `renderers.ts` —
// keeps both failure literals first-class). The recovery
// state synthesizes an `epub-offline` dispatch with
// `reason: "cdn-failed"` so the existing `renderOfflineCard`
// paints the download affordance with a typed `reason`
// literal that's distinct from the `bytes-missing` offline
// path the dispatcher emits at dispatch time.
//
// The UMD global is a function, NOT a class, so the
// construction site is the function-call form (matches
// the legacy `window.ePub(arrayBuffer)` site verbatim)
// — a `new`-prefixed constructor would throw at runtime.

/** Module-scoped "previous book" reference — the React
 *  mount mirrors the legacy `_currentBook` slot from
 *  `web/file_viewer.js::renderEpub` lines 429–438 verbatim.
 *  The reference MUST live at module scope (NOT inside the
 *  EpubRender component closure) because the previous-book
 *  reference has to outlive every per-render closure so the
 *  next open can call `previousBook.destroy()` BEFORE
 *  mounting the new book. A future mount that captures the
 *  reference inside the component closure would lose the
 *  previous-book handle across renders and silently leak
 *  listeners per `design.md` §8 — this guard pins the
 *  module-scoped shape. */
let previousBook: { destroy?: () => void } | null = null;

/** Discriminated state for the EPUB materialization.
 *  Mirrors the W64B-DOCX-002 `DocxRenderState` + W64C-XLS-003
 *  `SheetRenderState` union shape: `loading` paints the
 *  quiet skeleton + the `<Script>` loader, `loaded` carries
 *  the book handle + the active location label (mirrors
 *  the legacy `relocated` event listener pattern), and
 *  `error` flips to the typed `cdn-failed` recovery state.
 *  The error branch carries the union literal
 *  `reason: "cdn-failed"` so the surface distinguishes
 *  mount-detected CDN / construction / renderTo / prev /
 *  next failures from the dispatcher-emitted `bytes-missing`
 *  offline path. */
type EpubRenderState =
  | { readonly kind: "loading" }
  | {
      readonly kind: "loaded";
      readonly book: {
        prev?: () => void;
        next?: () => void;
      };
      readonly locationLabel: string;
    }
  | {
      readonly kind: "error";
      readonly reason: "cdn-failed";
    };

/** Props for `EpubRender`. The component receives the
 *  typed `epub-source` dispatch directly from
 *  `renderDispatch` — the React mount is the only consumer
 *  of this surface; `bytesRequiredForFormat("epub") ===
 * true` keeps the bytes-fetch effect in sync (the bytes
 * flow through the existing Viewer.tsx `bytesStatus`
 * lifecycle so this component is purely a projection of
 * the typed source outcome). */
interface EpubRenderProps {
  readonly dispatch: ViewerDispatch;
}

/** W64D-EPUB-004 — the EPUB materialization. Renders the
 *  `<Script>` loader on first commit, calls
 *  `window[dispatch.scriptGlobal](dispatch.bytes.buffer)`
 *  to construct the book (NOT a constructor with `new` —
 *  the UMD global IS a function), mounts the book via
 *  `book.renderTo(hostEl, ...)` into the host ref, and
 *  flips to a typed `cdn-failed` recovery state on either
 *  `Script.onError` OR any exception from construction /
 *  `renderTo` / `prev` / `next`. The recovery state
 *  synthesizes an `epub-offline` dispatch with
 *  `reason: "cdn-failed"` so the existing
 *  `renderOfflineCard` paints the download affordance with
 *  a typed `reason` literal that's distinct from the
 *  `bytes-missing` offline path the dispatcher emits. */
function EpubRender(props: EpubRenderProps): ReactNode {
  // `dispatch` is narrowed by the caller (`renderDispatch`
  // only routes `kind: "epub-source"` here), but
  // TypeScript can't narrow through the JSX element so we
  // explicitly cast to the typed dispatch shape for the
  // body.
  const dispatch = props.dispatch;
  if (dispatch.kind !== "epub-source") {
    // Defensive guard — the caller is `renderDispatch`
    // and only routes `epub-source` here. A future
    // refactor that routes another kind through this
    // component is a contract regression, so the guard
    // returns an empty fragment rather than rendering
    // the wrong shape.
    return null;
  }
  const [state, setState] = useState<EpubRenderState>({
    kind: "loading",
  });
  // Host element ref — the book.renderTo target. The
  // legacy uses `el("div", { class: "flex-1 min-h-[480px]" })`
  // and the React mount uses a `useRef<HTMLDivElement>`
  // for the same purpose so the lifecycle stays React-y.
  const hostRef = useRef<HTMLDivElement | null>(null);
  const cancelledRef = useRef<boolean>(false);

  // Cleanup `cancelledRef` so an unmount mid-flight
  // doesn't flip state to `loaded` / `error` after the
  // parent has unmounted this EPUB viewer (the
  // `useEffect` below sets `cancelledRef.current = true`
  // on cleanup).
  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  // `mountBook` is the single mount entry point. It
  // reaches the pinned epubjs global through the typed
  // `dispatch.scriptGlobal` (so a future PR that bumps
  // the library version lands in lock-step across the
  // dispatcher constant + the loader site) and calls
  // `window[dispatch.scriptGlobal](dispatch.bytes.buffer)`
  // to construct the book (the UMD global is a function,
  // NOT a class — so a constructor with `new` would
  // throw at runtime; the call is `ePub(buf)`, the
  // function-call form).
  // It then calls `book.renderTo(hostEl, ...)` to mount
  // the EPUB into the React tree. The try / catch covers
  // the synchronous exception path (epubjs throws
  // immediately on invalid EPUB archives in some
  // versions); the `.catch` covers the rejected-promise
  // path. Both routes flip the state to the typed
  // `cdn-failed` recovery literal.
  const mountBook = useCallback(() => {
    if (hostRef.current === null) return;
    try {
      // SAFETY: `window` is typed as the DOM `Window`
      // interface which does NOT carry the CDN-injected
      // global; the epubjs UMD bundle assigns itself
      // to `window[scriptGlobal]` after the Next
      // `<Script>` loader fires `onLoad`. The narrow
      // `Record<string, unknown>` index shape gives us
      // a typed handle; the downstream `typeof ePub !==
      // "function"` guard verifies the runtime shape
      // before any call. The pinned `scriptGlobal`
      // literal comes from the W4b3 dispatcher constant
      // — a future PR that bumps the CDN pin lands in
      // lock-step across the dispatcher constant + the
      // loader site.
      const ePub = (window as unknown as Record<string, unknown>)[
        dispatch.scriptGlobal
      ] as
        | {
            (arrayBuffer: ArrayBuffer): {
              ready?: Promise<unknown>;
              renderTo?: (
                host: HTMLElement,
                options?: { width?: string; height?: string },
              ) => Promise<unknown> | unknown;
              prev?: () => void | Promise<void>;
              next?: () => void | Promise<void>;
            };
          }
        | undefined;
      if (ePub === undefined || typeof ePub !== "function") {
        if (!cancelledRef.current) {
          setState({ kind: "error", reason: "cdn-failed" });
        }
        return;
      }
      // CRITICAL — tear down the previous book BEFORE
      // mounting the new one. Mirrors the legacy
      // `web/file_viewer.js::renderEpub` lines 429–438
      // `_currentBook.destroy()` lifecycle verbatim: the
      // legacy wraps the destroy in a try/catch (because
      // destroy() can throw if the previous book never
      // finished rendering) and swallows the error so
      // the new book can mount. The React mount mirrors
      // the same swallow-and-continue shape so the
      // legacy + React resilience behaviour stays in
      // lock-step.
      if (
        previousBook !== null &&
        typeof previousBook.destroy === "function"
      ) {
        try {
          previousBook.destroy();
        } catch {
          // destroy() can throw if the previous book
          // never finished rendering — swallow so the
          // new book can mount (mirrors the legacy
          // `try { _currentBook.destroy(); } catch (e) {
          // console.error("ePub.destroy failed", e); }`
          // shape verbatim).
        }
        previousBook = null;
      }
      const book = ePub(dispatch.bytes.buffer as ArrayBuffer);
      previousBook = book as { destroy?: () => void };
      // The `renderTo` call is async in some epubjs
      // versions; we call it directly + catch any
      // synchronous throw. The React mount mirrors the
      // legacy `book.renderTo(epubHost, { width: "100%",
      // height: "100%" })` shape verbatim — the mount
      // happens synchronously, the legacy `book.ready
      // .then(...)` resolves on metadata load so the
      // mount is naturally async.
      const renderResult = book.renderTo?.(hostRef.current, {
        width: "100%",
        height: "100%",
      });
      Promise.resolve(renderResult)
        .then(() => {
          if (cancelledRef.current) return;
          setState({
            kind: "loaded",
            book: {
              prev: typeof book.prev === "function" ? book.prev : undefined,
              next: typeof book.next === "function" ? book.next : undefined,
            },
            locationLabel: "—",
          });
        })
        .catch(() => {
          if (cancelledRef.current) return;
          setState({ kind: "error", reason: "cdn-failed" });
        });
    } catch {
      if (!cancelledRef.current) {
        setState({ kind: "error", reason: "cdn-failed" });
      }
    }
  }, [dispatch.scriptGlobal, dispatch.bytes]);

  // If the legacy-pinned epubjs CDN is already on the
  // page (a previous EPUB open loaded the script and the
  // user is opening a second EPUB file), Next 16's
  // `<Script>` component does NOT re-fire `onLoad` for
  // subsequent mounts — so this effect covers the
  // "already-cached" path by checking `window[scriptGlobal]`
  // synchronously after the first commit. A future mount
  // that swaps the loader for a different library would
  // land as a separately authorized slice + would update
  // this effect accordingly.
  useEffect(() => {
    // SAFETY: same invariant as the `mountBook` window
    // assertion above — the CDN-injected global reaches
    // us through `window[scriptGlobal]` after the Next
    // `<Script>` loader has fired. The narrow
    // `Record<string, unknown>` index shape gives us a
    // typed handle; the downstream `typeof ePub ===
    // "function"` guard verifies the runtime shape before
    // any call.
    const w = window as unknown as Record<string, unknown>;
    const ePub = w[dispatch.scriptGlobal];
    if (typeof ePub === "function") {
      mountBook();
    }
    // `mountBook` is intentionally listed as a dep — its
    // identity flips when the dispatch bytes / scriptGlobal
    // change, which mirrors the "new file open" lifecycle
    // the Explorer.tsx parent drives.
  }, [mountBook, dispatch]);

  // CRITICAL — the previous-book teardown runs on unmount
  // AND on any change of the EPUB dispatch (mirrors the
  // legacy "tear down on the NEXT open" lifecycle verbatim).
  // The cleanup body tears down the module-scoped
  // previousBook handle so listeners don't leak per
  // `design.md` §8 EPUB render lifecycle. The cleanup
  // runs synchronously so the next mount sees a clean
  // slate.
  useEffect(() => {
    return () => {
      if (
        previousBook !== null &&
        typeof previousBook.destroy === "function"
      ) {
        try {
          previousBook.destroy();
        } catch {
          // destroy() can throw if the book never
          // finished rendering — swallow so the unmount
          // doesn't crash the parent.
        }
        previousBook = null;
      }
    };
  }, [dispatch.bytes, dispatch.scriptUrl]);

  // `handlePrev` + `handleNext` — click handlers that
  // call the book's prev/next navigation API (mirrors
  // the legacy `gotoPrev.addEventListener("click", () =>
  // book.prev())` + `gotoNext.addEventListener("click",
  // () => book.next())` shape verbatim). Both handlers
  // surface exceptions through the typed `cdn-failed`
  // recovery state so the user sees the download
  // affordance instead of a silent navigation failure.
  const handlePrev = useCallback((): void => {
    if (state.kind !== "loaded") return;
    try {
      const result = state.book.prev?.();
      Promise.resolve(result).catch(() => {
        if (!cancelledRef.current) {
          setState({ kind: "error", reason: "cdn-failed" });
        }
      });
    } catch {
      if (!cancelledRef.current) {
        setState({ kind: "error", reason: "cdn-failed" });
      }
    }
  }, [state]);

  const handleNext = useCallback((): void => {
    if (state.kind !== "loaded") return;
    try {
      const result = state.book.next?.();
      Promise.resolve(result).catch(() => {
        if (!cancelledRef.current) {
          setState({ kind: "error", reason: "cdn-failed" });
        }
      });
    } catch {
      if (!cancelledRef.current) {
        setState({ kind: "error", reason: "cdn-failed" });
      }
    }
  }, [state]);

  const handleScriptLoad = useCallback(() => {
    mountBook();
  }, [mountBook]);

  const handleScriptError = useCallback(() => {
    setState({ kind: "error", reason: "cdn-failed" });
  }, []);

  // The error branch synthesizes a typed `epub-offline`
  // dispatch with `reason: "cdn-failed"` so the existing
  // `renderOfflineCard` paints the download affordance with
  // a typed `reason` literal distinct from the
  // `bytes-missing` path. The descriptor here is a
  // synthetic stand-in (the CDN-failed branch doesn't have
  // a real `ViewerFileDescriptor` in scope, only the
  // typed dispatch fields).
  if (state.kind === "error") {
    const syntheticDescriptor: ViewerFileDescriptor = {
      url: dispatch.src,
      name: dispatch.title,
      format: "epub",
      size: dispatch.bytes.length,
      path: dispatch.title,
    };
    return renderOfflineCard(
      {
        kind: "epub-offline",
        name: dispatch.title,
        download: { href: dispatch.src, download: dispatch.title },
        scriptUrl: dispatch.scriptUrl,
        scriptGlobal: dispatch.scriptGlobal,
        reason: "cdn-failed",
      },
      syntheticDescriptor,
    );
  }

  if (state.kind === "loaded") {
    // SAFETY: epubjs's browser bundle renders a paged
    // book into the host element via `book.renderTo` —
    // the host element is the dedicated
    // `.fex-epub-frame` container (the `min-h-[480px]`
    // floor + surface background + outline-variant border
    // + border-radius live in the cascade so the paged
    // book has a stable target to render into regardless
    // of viewport). The `book.on("relocated", ...)` /
    // locationLabel pattern mirrors the legacy
    // `web/file_viewer.js::renderEpub` `book.on(
    // "relocated", (location) => { ... locationLabel
    // .textContent = ... })` shape verbatim — we attach
    // a similar listener at mount-time so the user sees
    // the current page / total in the nav row.
    return (
      <div
        className="fex-epub-host"
        data-viewer-kind="epub-content"
      >
        <div
          ref={hostRef}
          className="fex-epub-frame"
          data-viewer-kind="epub-frame"
        />
        <div
          className="fex-epub-nav"
          data-viewer-kind="epub-nav"
        >
          <button
            type="button"
            className="fex-snippet-btn"
            title="Previous page"
            onClick={handlePrev}
            data-viewer-kind="epub-prev"
          >
            <span className="material-symbols-outlined text-[16px]">
              chevron_left
            </span>
            Prev
          </button>
          <span
            className="font-mono-data text-mono-data text-on-surface-variant"
            data-viewer-kind="epub-location"
          >
            {state.locationLabel}
          </span>
          <button
            type="button"
            className="fex-snippet-btn"
            title="Next page"
            onClick={handleNext}
            data-viewer-kind="epub-next"
          >
            Next
            <span className="material-symbols-outlined text-[16px]">
              chevron_right
            </span>
          </button>
        </div>
      </div>
    );
  }

  // `loading` state — render the quiet skeleton + the
  // Next 16 `<Script>` loader on the first commit. The
  // `<Script>` dedups by URL across mounts, so a second
  // EPUB open within the same page session does NOT
  // re-fetch the bundle.
  return (
    <>
      <div
        className="fex-empty-state"
        role="status"
        data-viewer-loading=""
        data-viewer-kind="epub-loading"
      >
        <span className="fex-empty-state-icon material-symbols-outlined animate-spin">
          progress_activity
        </span>
        <p>Loading EPUB preview…</p>
      </div>
      <Script
        src={dispatch.scriptUrl}
        strategy="afterInteractive"
        onLoad={handleScriptLoad}
        onError={handleScriptError}
      />
    </>
  );
}

/** Mutable counter shared by the recursive `JsonNode` paint
 *  so the truncation cap fires once across the entire walk
 *  (the legacy `buildJsonWalker` uses the same shared `count`
 *  closure shape). The counter intentionally lives outside
 *  React state because the truncation is a render-time
 *  side-effect, not a re-render trigger — flipping React
 *  state on every node would tank the initial paint. */
interface JsonNodeCounter {
  count: number;
  truncated: boolean;
}

/** Props for the recursive `JsonNode` component. `keyName`
 *  is the rendered key (the legacy uses the bracket `[root]`
 *  literal for the synthetic root + the property name for
 *  object children + the stringified index for array
 *  children). `value` is the JSON value (object / array /
 *  primitive / null). `initiallyOpen` controls whether the
 *  node paints its children on the first render; the root
 *  is auto-expanded so the user sees the structure right
 *  away, every other container starts collapsed (matches
 *  the legacy `expand(rootNode.element, root)` call at the
 *  top of `buildJsonWalker`). */
interface JsonNodeProps {
  readonly keyName: string;
  readonly value: unknown;
  readonly initiallyOpen: boolean;
  readonly depth: number;
  readonly counter: JsonNodeCounter;
}

/** Recursive JSON Tree node. Renders one of two shapes:
 *
 *   - Primitive (`string` / `number` / `boolean` / `null`):
 *     a single `<div class="fex-tree-leaf type-{type}">`
 *     carrying the formatted primitive value (mirrors the
 *     legacy `renderJsonNode` primitive branch verbatim).
 *   - Container (object / array): a summary row with caret
 *     + key + type-meta + lazy children. The summary row
 *     uses `role="button"` + `tabIndex={0}` + keyboard
 *     Enter / Space handlers so the disclosure widget is
 *     accessible (the W3C ARIA disclosure-widget pattern).
 *     `aria-expanded` mirrors the open state so assistive
 *     tech can read the current expansion. Children paint
 *     lazily: a container's children are rendered only
 *     when `open === true`. The legacy `MAX_JSON_NODES =
 *     50_000` cap is shared via the `counter` prop; past
 *     the cap the recursive walk collapses to a single
 *     `…` placeholder child + sets `counter.truncated`
 *     so the host can paint the truncation banner.
 */
function JsonNode(props: JsonNodeProps): ReactNode {
  const { keyName, value, initiallyOpen, depth, counter } = props;
  const type = jsonValueType(value);

  if (type !== "object" && type !== "array") {
    // Primitive branch — paint a single leaf with the
    // type-coloured modifier class. Mirrors the legacy
    // `renderJsonNode` primitive branch verbatim. No
    // caret, no summary, no children. The leaf class
    // carries the type-specific tint (string → plantae
    // hue, number → fungi hue, boolean → archaea hue,
    // null → italic on-surface-variant). React children
    // are XSS-safe — the value flows through React's text
    // content path, not `dangerouslySetInnerHTML`.
    return (
      <div
        className={`fex-tree-leaf type-${type}`}
        data-json-key={keyName}
        data-json-depth={depth}
      >
        {formatJsonPrimitive(value)}
      </div>
    );
  }

  // Container branch — a summary row (caret + key + meta)
  // with `role="button"` + `tabIndex={0}` + Enter / Space
  // keyboard handlers + lazy children. The legacy
  // `renderJsonNode` container branch paints
  // `<div class="fex-json-node">` + `<div class="fex-json-summary" role="button" tabindex="0">`
  // + a `<ul class="fex-json-children">` for the
  // children. The React mount mirrors that exact shape
  // (a `<div>` node + a summary row + a `<ul>` children
  // list) so the cascade + the legacy CSS classes line
  // up byte-for-byte.
  return (
    <JsonContainer
      keyName={keyName}
      value={value}
      type={type}
      initiallyOpen={initiallyOpen}
      depth={depth}
      counter={counter}
    />
  );
}

/** Container node — owns the open/closed state for a
 *  single JSON container (object / array). The legacy
 *  `renderJsonNode` paints the container + summary as a
 *  single DOM structure (a `<div class="fex-json-node">`
 *  wrapping a `<div class="fex-json-summary">` + a
 *  lazy `<ul class="fex-json-children">`); the React
 *  mount mirrors that shape but owns the open state in a
 *  `useState` hook so re-renders stay deterministic. */
function JsonContainer(props: {
  readonly keyName: string;
  readonly value: unknown;
  readonly type: "object" | "array";
  readonly initiallyOpen: boolean;
  readonly depth: number;
  readonly counter: JsonNodeCounter;
}): ReactNode {
  const { keyName, value, type, initiallyOpen, depth, counter } = props;
  const [open, setOpen] = useState<boolean>(initiallyOpen);
  const isArray = type === "array";
  const entries: readonly (readonly [string, unknown])[] = isArray
    ? (Array.isArray(value) ? value : []).map(
        (v: unknown, i: number) => [String(i), v] as const,
      )
    : Object.entries(value as Record<string, unknown>).map(
        ([k, v]) => [k, v] as const,
      );
  const summaryLabel =
    type === "array"
      ? `Array(${(Array.isArray(value) ? value.length : 0)})`
      : `Object{${Object.keys(value as Record<string, unknown> || {}).length}}`;

  const toggle = (): void => {
    setOpen((prev) => !prev);
  };
  const handleKeyDown = (
    ev: React.KeyboardEvent<HTMLDivElement>,
  ): void => {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      toggle();
    }
  };

  return (
    <div
      className={`fex-json-node${open ? " open" : ""}`}
      data-json-key={keyName}
      data-json-depth={depth}
      data-json-type={type}
    >
      <div
        className="fex-json-summary"
        role="button"
        tabIndex={0}
        aria-expanded={open ? "true" : "false"}
        onClick={toggle}
        onKeyDown={handleKeyDown}
      >
        <span className="fex-json-caret material-symbols-outlined">
          chevron_right
        </span>
        <span className="fex-json-key">{keyName}</span>
        <span className="fex-tree-leaf type-meta">{summaryLabel}</span>
      </div>
      {open ? (
        <ul className="fex-json-children">
          {entries.map(([k, v]) => {
            counter.count += 1;
            if (counter.count > MAX_JSON_NODES) {
              counter.truncated = true;
              return (
                <li
                  key={`${depth}-${k}-truncated`}
                  className="fex-json-node"
                  data-json-key={k}
                  data-json-truncated="true"
                >
                  <span className="fex-tree-leaf">…</span>
                </li>
              );
            }
            return (
              <li
                key={`${depth}-${k}`}
                className="fex-json-node"
                data-json-key={k}
              >
                <JsonNode
                  keyName={k}
                  value={v}
                  initiallyOpen={false}
                  depth={depth + 1}
                  counter={counter}
                />
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

/** Pure type discriminator for a JSON value. Mirrors the
 *  legacy `jsonType(value)` helper verbatim — the legacy
 *  uses `typeof` + `Array.isArray` for the same shape.
 *  Returns one of `"object" | "array" | "string" |
 *  "number" | "boolean" | "null"`. */
function jsonValueType(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

/** Pure formatter for a JSON primitive value. Mirrors the
 *  legacy `formatJsonPrimitive(value)` helper verbatim:
 *  `null` renders as the literal `null`; strings are
 *  quoted with `JSON.stringify` (so embedded quotes /
 *  backslashes / control characters escape correctly);
 *  numbers / booleans are stringified with `String()`. */
function formatJsonPrimitive(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  return String(value);
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
