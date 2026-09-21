// Research application — pure viewer-dispatch contract for the Browser-tab
// file viewer. W4a + W4b1 + W4b2 of ODD-MIGRATE-002 (`odd/tasks/complete-
// frontend-migration.md::ODD-MIGRATE-002 / W4a + W4b1 + W4b2`).
//
// spec.md rule 4: application depends on domain ONLY. This file is
// purely TypeScript types + pure helper functions + one pure
// dispatcher — no React, no Next, no FastAPI, no `fetch(`, no
// `DOMParser`, no `localStorage`, no `document`, no `window`, no
// `process`. The contract mirrors the legacy `web/file_viewer.js`
// format dispatcher (the `RENDERERS` map + `render()` entry point)
// for the eight no-CDN families the W4a slice owns:
//
//   - PDF (legacy `renderPdf` → `<iframe type="application/pdf">`)
//   - HTML / HTM (legacy `renderHtml` → sandboxed `<iframe>`)
//   - TXT (legacy `renderText` → `renderAsPre` → fenced `<pre>`)
//   - MD (legacy `renderMd` → `renderAsPre` → fenced `<pre>` — W4a
//     PRESERVES the legacy Markdown-as-text behavior; the spec's
//     "Markdown rendering" scenario with marked.js CDN is deferred
//     to a separately authorized later slice per the W4a split)
//   - DOC (legacy `renderUnsupported` with the spec's "Legacy .doc
//     cannot be rendered inline." message — DOC has no inline
//     renderer; the download link is the recovery path)
//   - JPG / JPEG / PNG / GIF / WEBP / BMP (legacy `renderImage` →
//     `<img>` with a 50 MB advisory banner for big files)
//   - SVG (legacy `renderSvg` → fetch + DOMParser + strip
//     `<script>` + strip `on*=` event-handler attributes — W4a
//     replicates the legacy XSS scrub as a pure string-level
//     sanitizer so the contract stays DOMParser-free)
//   - MP4 / WEBM / OGV (legacy `renderVideo` → `<video controls
//     preload="metadata">`)
//   - "other" (legacy `renderUnsupported` with the spec's
//     "Format .xyz not supported in viewer." message + download
//     link)
//   - Table / Tree tab on a file whose format has no W4a Table/Tree
//     renderer (legacy `handleTabClick` branches on the
//     `${tab} view not available for .${ext} files — use Raw.`
//     message — W4a preserves that wording verbatim so the React
//     mount's empty-state card matches the legacy oracle)
//
// W4b1 (DOCX) and W4b2 (XLS / XLSX) of ODD-MIGRATE-002 add two
// CDN-dependent families to the dispatcher — both follow the same
// typed source / offline pattern.
//
// DOCX (W4b1): the dispatcher emits a typed `docx-source` outcome
// that carries the descriptor + bytes + pinned mammoth CDN URL +
// global name so a future React mount (W6+) can load the legacy-
// pinned mammoth library via Next 16's `<Script>` component
// (`node_modules/next/dist/docs/01-app/03-api-reference/02-
// components/script.md`), call `window.mammoth.convertToHtml(
// {arrayBuffer})`, and inject the resulting HTML via
// `Range.createContextualFragment` (mirrors the legacy
// `web/file_viewer.js::renderDocx` shape — mammoth already strips
// `<script>` + event handlers per `design.md` §8). When bytes
// are missing the dispatcher emits a typed `docx-offline` branch
// carrying the download link + pinned CDN URL + global name +
// reason, so the mount paints the same legacy "Viewer offline —
// raw download available" banner (`web/file_viewer.js::
// renderOfflineBanner`) verbatim.
//
// XLS / XLSX (W4b2): the dispatcher emits a typed `sheet-source`
// outcome that carries the descriptor + bytes + pinned SheetJS
// CDN URL + global name so the future React mount (W6+) can load
// the legacy-pinned SheetJS library via the same Next 16 `<Script
// src={scriptUrl} strategy="afterInteractive" onLoad={convert}
// onError={...}>` shape, then call `window[scriptGlobal].read(
// data, { type: "array" })` to parse the workbook and `window
// [scriptGlobal].utils.sheet_to_html(sheet)` to emit the HTML
// table (mirrors the legacy `web/file_viewer.js::renderSheet`
// shape verbatim — SheetJS already emits plain `<table>` markup
// without `<script>` or event handlers per `design.md` §8).
// When bytes are missing the dispatcher emits a typed
// `sheet-offline` branch carrying the download link + pinned
// SheetJS CDN URL + global name + reason, so the mount paints
// the same legacy "Viewer offline" banner verbatim.
//
// Both DOCX (W4b1) and XLS / XLSX (W4b2) application-layer slices
// stay framework-free, browser-free, and CDN-loader-free — mammoth
// and SheetJS are NOT imported or loaded here; the dispatcher
// only emits the typed source descriptor for the mount to
// consume.
//
// W4b3 explicitly defers to W4b4:
//   - CSV / TSV (legacy `renderTable` via Papa Parse CDN),
//   - JSON (legacy `renderJsonTree` — no CDN but still deferred per
//     the W4b split),
//   - Markdown-as-HTML (legacy would call marked.js CDN).
//
// Until those land, the dispatcher returns the `unsupported` or
// `tab-not-applicable` branches for those format/tab combinations —
// mirroring the legacy "Format .xyz not supported in viewer." and
// "Table/Tree view not available for this format" fallbacks so the
// React mount paints the same download-link / empty-state card.
//
// EPUB (W4b3) and the legacy EPUB renderer lifecycle are
// modeled only as the future-mount handoff: the dispatcher
// emits the typed source descriptor (descriptor + bytes +
// pinned epubjs CDN URL + global name) on Raw, the typed
// offline descriptor on Raw when bytes are missing, and
// `tab-not-applicable` on Table / Tree (the EPUB widget has
// no Table or Tree renderer). The future React mount (W6+)
// owns the actual `<Script>` load + `ePub(bytes.buffer)`
// mount + prev/next navigation + `_currentBook.destroy()`
// teardown — none of which the application layer touches.
//
// URL derivation: every URL the dispatcher emits is sourced from the
// explicit `ViewerFileDescriptor.url` input field. The contract does
// NOT import the W3 `fetchFileServe` infrastructure adapter
// (`src/modules/research/infrastructure/api.ts`) and never reads
// bytes by fetching — the bytes are injected as `Uint8Array | null`
// on the dispatch input, and the future W6 React mount reads them
// through the W3 adapter separately and threads them in. Mirrors
// the layered architecture (spec.md rule 4 — application depends on
// domain ONLY) and the W4a split directive ("derive URLs from
// explicit typed input rather than importing W3 implementation").
// The W4b1 contract follows the same rule: the mammoth CDN URL +
// global name are pinned constants on the typed source outcome
// — the dispatcher does NOT load the script, fetch the URL, or
// invoke `convertToHtml`.

import type { FileFormat, ViewerTab } from "../domain/explorer";

/** 50 MB advisory threshold — mirrors the legacy
 *  `web/file_viewer.js::IMAGE_BIG_FILE_BYTES`. Decoding 50 MP
 *  photos or RAW-like inputs freezes the tab — a soft warning is
 *  the proportional response. A future PR that bumps the
 *  threshold must update this constant AND the focused test that
 *  pins it (`tests/test_research_renderers.py::
 *  test_renderers_image_big_file_bytes_constant`). */
export const IMAGE_BIG_FILE_BYTES: number = 50 * 1024 * 1024;

/** W4a W4a-specific message wording for the "Table/Tree view not
 *  available for this format — use Raw." branch. The literal
 *  matches the legacy `web/file_explorer.js::handleTabClick`
 *  wording `${tab} view not available for .${ext} files — use
 *  Raw.` so the React mount's empty-state card matches the
 *  legacy oracle byte-for-byte. The dispatcher prefixes this
 *  with the active tab name and the file's extension at call
 *  time (the prefix is intentionally NOT exported as a separate
 *  constant — the contract commits to the WHOLE message shape,
 *  not a half-message prefix). */
export const TAB_NOT_APPLICABLE_SUFFIX: string =
  "files — use Raw.";

/** W4b1 — pinned mammoth CDN URL. Mirrors `web/file_viewer.js::
 *  CDN_URLS.mammoth` and the matching `<script>` tag in
 *  `web/index.html` (whose comment block calls the URL "Pinned
 *  URL: do not unpin."). The URL is part of the W4b1 typed
 *  source outcome so the future React mount (W6+) can load the
 *  CDN idempotently via Next 16's `<Script src={scriptUrl}
 *  strategy="afterInteractive" onLoad={convert} onError={...}>`
 *  (see `node_modules/next/dist/docs/01-app/03-api-reference/02-
 *  components/script.md`). The application layer does NOT load
 *  the script — it only pins the URL on the typed source
 *  descriptor so the mount knows what to inject. A future PR
 *  that bumps mammoth's version MUST update this constant AND
 *  the matching `web/index.html` <script> tag AND the focused
 *  test that pins the literal — bumping the URL without updating
 *  the legacy `<script>` tag would silently diverge the React
 *  + legacy paths. */
export const MAMMOTH_CDN_URL: string =
  "https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js";

/** W4b1 — pinned window-global name mammoth assigns itself once
 *  the CDN script loads. Mirrors the `web/file_viewer.js::
 *  CDN_URLS.mammoth` map key and the legacy `window.mammoth.
 *  convertToHtml(...)` call site in `web/file_viewer.js::
 *  renderDocx`. The global name is part of the W4b1 typed source
 *  outcome so the future React mount can read the global verbatim
 *  (via `window[scriptGlobal].convertToHtml({arrayBuffer:
 *  bytes.buffer})`) without hardcoding the string. A future PR
 *  that bumps mammoth (or that swaps the library for a different
 *  DOCX renderer that exposes a different global) MUST update
 *  this constant in lock-step with `MAMMOTH_CDN_URL`. */
export const MAMMOTH_GLOBAL_NAME: string = "mammoth";

/** W4b2 — pinned SheetJS CDN URL. Mirrors `web/file_viewer.js::
 *  CDN_URLS.XLSX` and the matching `<script>` tag in
 *  `web/index.html` (whose comment block calls the URL "Pinned
 *  URL: do not unpin." — the SheetJS Community edition is served
 *  under the Apache 2.0 license; the Pro edition is a different
 *  URL). The URL is part of the W4b2 typed source outcome so the
 *  future React mount (W6+) can load the CDN idempotently via
 *  Next 16's `<Script src={scriptUrl} strategy="afterInteractive"
 *  onLoad={convert} onError={...}>` (see `node_modules/next/dist/
 *  docs/01-app/03-api-reference/02-components/script.md`). The
 *  application layer does NOT load the script — it only pins the
 *  URL on the typed source descriptor so the mount knows what
 *  to inject. A future PR that bumps SheetJS's version MUST
 *  update this constant AND the matching `web/index.html`
 *  <script> tag AND the focused test that pins the literal —
 *  bumping the URL without updating the legacy `<script>` tag
 *  would silently diverge the React + legacy paths. */
export const SHEETJS_CDN_URL: string =
  "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js";

/** W4b2 — pinned window-global name SheetJS assigns itself once
 *  the CDN script loads. Mirrors the `web/file_viewer.js::
 *  CDN_URLS.XLSX` map key and the legacy `window.XLSX.read(...)`
 *  + `window.XLSX.utils.sheet_to_html(...)` call sites in
 *  `web/file_viewer.js::renderSheet`. The global name is part
 *  of the W4b2 typed source outcome so the future React mount
 *  can read the global verbatim (via
 *  `window[scriptGlobal].read(bytes, { type: "array" })` then
 *  `window[scriptGlobal].utils.sheet_to_html(sheet)`) without
 *  hardcoding the string. A future PR that bumps SheetJS (or
 *  that swaps the library for a different spreadsheet renderer
 *  that exposes a different global) MUST update this constant
 *  in lock-step with `SHEETJS_CDN_URL`. */
export const SHEETJS_GLOBAL_NAME: string = "XLSX";

/** W4b3 — pinned epubjs CDN URL. Mirrors `web/file_viewer.js::
 *  CDN_URLS.ePub` and the matching `<script>` tag in
 *  `web/index.html` (whose comment block calls the URL "Pinned
 *  URL: do not unpin."). The URL is part of the W4b3 typed
 *  source outcome so the future React mount (W6+) can load
 *  the CDN idempotently via Next 16's `<Script src={scriptUrl}
 *  strategy="afterInteractive" onLoad={mount} onError={...}>`
 *  (see `node_modules/next/dist/docs/01-app/03-api-reference/
 *  02-components/script.md`). The application layer does NOT
 *  load the script — it only pins the URL on the typed source
 *  descriptor so the mount knows what to inject. A future PR
 *  that bumps epubjs's version MUST update this constant AND
 *  the matching `web/index.html` <script> tag AND the focused
 *  test that pins the literal — bumping the URL without
 *  updating the legacy `<script>` tag would silently diverge
 *  the React + legacy paths. */
export const EPUBJS_CDN_URL: string =
  "https://cdn.jsdelivr.net/npm/epubjs@0.3.93/dist/epub.min.js";

/** W4b3 — pinned window-global name epubjs assigns itself once
 *  the CDN script loads. Mirrors the `web/file_viewer.js::
 *  CDN_URLS.ePub` map key (literal `"ePub"`, capital `P` — the
 *  epubjs UMD bundle assigns itself to `window.ePub`, not
 *  `window.EPUBJS` or `window.epub`) and the legacy
 *  `window.ePub(arrayBuffer)` call site in
 *  `web/file_viewer.js::renderEpub`. The global name is part
 *  of the W4b3 typed source outcome so the future React mount
 *  can read the global verbatim (via
 *  `window[scriptGlobal](bytes.buffer)`) without hardcoding
 *  the string. A future PR that bumps epubjs (or that swaps
 *  the library for a different EPUB renderer that exposes a
 *  different global) MUST update this constant in lock-step
 *  with `EPUBJS_CDN_URL`. */
export const EPUBJS_GLOBAL_NAME: string = "ePub";

/** Input file descriptor for the viewer-dispatch contract.
 *  Mirrors the legacy `web/file_viewer.js::render(host, file)`
 *  `file` shape verbatim — the future W6 React mount builds a
 *  `ViewerFileDescriptor` from the W1 `ExplorerFileNode` + the
 *  W3 `fetchFileServe` URL + the W3 served filename:
 *
 *  - `url` — the W3 `/api/files/serve?path=<encoded>` URL (already
 *    encoded — `web/file_explorer.js::serveUrl(relativePath)`
 *    URL-encodes verbatim; the dispatcher never re-encodes).
 *  - `name` — the file's basename. Used for the `<iframe title>`,
 *    `<img alt>`, `<video title>`, the download `download`
 *    attribute, and the spec's "Legacy .doc cannot be rendered
 *    inline." message framing.
 *  - `format` — the W1 `FileFormat` literal (pdf, html, htm, txt,
 *    md, doc, jpg, jpeg, png, gif, webp, bmp, svg, mp4, webm, ogv,
 *    or "other"). The W6 mount casts the wire `extension` string
 *    to `FileFormat` once before constructing the descriptor (the
 *    cast returns "other" for unknown extensions like "zip" — the
 *    W1 union's `"other"` literal is the typed fallback).
 *  - `size` — the wire byte count (`ExplorerFileNode.size`). Used
 *    for the legacy 50 MB image advisory banner.
 *  - `path` — the file's path relative to the research root (the
 *    W1 `ExplorerFileNode.path` field, e.g.
 *    `"Animalia/Chordata/Mammalia.pdf"` or `"foo.zip"`). Used
 *    ONLY to derive the extension label for the
 *    `"Format .{ext} not supported in viewer."` message when
 *    `format === "other"` (the W1 `"other"` literal carries no
 *    extension information — the descriptor's `path` field
 *    carries the wire basename verbatim, so the dispatcher can
 *    re-extract the extension at the message site).
 *
 *  Every field is `readonly` so a future React mount cannot
 *  accidentally mutate the input between dispatch and the
 *  renderer's JSX emission (mirrors the W1 readonly contract on
 *  `ExplorerState.openFilePath` / `openFileFormat` — `tests/
 *  test_research_domain.py::test_domain_file_explorer_state_
 *  fields_are_readonly`). The dispatcher treats the descriptor
 *  as immutable — the same input yields the same dispatch
 *  outcome on every call (the focused runtime harness exercises
 *  this end-to-end). */
export interface ViewerFileDescriptor {
  readonly url: string;
  readonly name: string;
  readonly format: FileFormat;
  readonly size: number;
  readonly path: string;
}

/** Typed link descriptor — the dispatch contract surfaces
 *  download-link affordances (`<a href download>`) as a typed
 *  `{ href, download }` pair so the future React mount reads the
 *  two attributes without parsing a free-form string. Mirrors
 *  the legacy `renderOfflineBanner` + `renderUnsupported`
 *  download-link shape verbatim — `href` is the W3 serve URL,
 *  `download` is the file basename (which triggers the browser's
 *  save-as dialog with the suggested filename). */
export interface ViewerLink {
  readonly href: string;
  readonly download: string;
}

/** Image advisory descriptor — the legacy `renderImage`
 *  paints a yellow `fex-image-advisory` banner above the `<img>`
 *  when the file size exceeds `IMAGE_BIG_FILE_BYTES`. W4a
 *  surfaces this as a typed `{ message }` object so the React
 *  mount can paint the same banner with the same wording. The
 *  message is pre-computed (formatted via `formatSize`) so the
 *  React mount doesn't need to ship its own size-formatter
 *  helper — the dispatch contract owns the legacy's
 *  `formatSize` rounding rules (B / KB / MB / GB). */
export interface ViewerImageAdvisory {
  readonly message: string;
}

/** The pure viewer-dispatch outcome. A discriminated union over
 *  `kind` so the future React mount dispatches on `kind` (no
 *  manual field-comparison tree) and so a future PR that adds
 *  a new variant breaks every consumer's switch exhaustiveness
 *  check at the TypeScript compile gate (the focused project-
 *  wide strict typecheck catches missing cases before they
 *  reach review).
 *
 *  The variants mirror the legacy `renderX(target, file)`
 *  functions verbatim:
 *
 *  - `"pdf-iframe"`     — `renderPdf`'s `<iframe
 *    type="application/pdf">` + the inline `<a download>`
 *    fallback. The `fallback` link mirrors the legacy "If the
 *    PDF does not render, download the file directly."
 *    recovery path.
 *  - `"html-iframe"`    — `renderHtml`'s sandboxed `<iframe>`.
 *    `sandbox: ""` (empty string) matches the legacy — the
 *    spec's "HTML rendering" scenario requires NO
 *    `allow-same-origin` (same-origin XSS surface is noted in
 *    `design.md` §8). The dispatch contract pins this so a
 *    future PR can't accidentally widen the sandbox to
 *    `allow-same-origin`.
 *  - `"text-pre"`       — `renderAsPre`'s fenced `<pre>` for
 *    `.txt` and `.md` files. W4a PRESERVES the legacy
 *    Markdown-as-text behavior (the spec's "Markdown
 *    rendering" scenario with marked.js CDN is deferred to a
 *    separately authorized later slice). `body` is the UTF-8
 *    decoded text content (already converted from the injected
 *    `Uint8Array` bytes).
 *  - `"image"`          — `renderImage`'s `<img>` + optional
 *    50 MB advisory banner. `advisory` is `null` when the
 *    file is under the threshold and the typed
 *    `{ message }` object when above.
 *  - `"image-error"`    — `renderImageError`'s decode-failure
 *    card. The SVG and video renderers fall back to this when
 *    the bytes fail to decode / the SVG isn't valid — the
 *    future React mount decides WHEN to call (e.g. on
 *    `<video error>` event or after `sanitizeSvgMarkup`
 *    returns ""), and the dispatcher surfaces the same typed
 *    error shape regardless of the failure source. The
 *    contract pins the `name` + `download` pair so the React
 *    mount reads the legacy "Could not decode X" framing
 *    without re-implementing it.
 *  - `"svg-sanitized"`  — `renderSvg`'s XSS-scrubbed inline
 *    SVG. `svg` is the cleaned markup (no `<script>`, no
 *    `on*=` event handlers). `className` is the legacy
 *    `"fex-image"` (the React mount passes it through to
 *    `<svg class>`). `preserveAspectRatio` defaults to
 *    `"xMidYMid meet"` to mirror the legacy
 *    `setAttribute("preserveAspectRatio", "xMidYMid meet")`
 *    fallback when the source SVG omits it.
 *  - `"video"`          — `renderVideo`'s `<video controls
 *    preload="metadata">`. `controls: true` and `preload:
 *    "metadata"` are pinned so a future PR that flips them
 *    (e.g. adds autoplay) breaks the focused test.
 *  - `"unsupported"`    — `renderUnsupported`'s
 *    "Format .xyz not supported in viewer." (or "Legacy .doc
 *    cannot be rendered inline.") message + download link.
 *    Covers BOTH the legacy "unknown extension" path (e.g.
 *    `.zip`, `.exe`) AND the still-W4b+-deferred formats
 *    (CSV, TSV, JSON) until W4b4 extends the
 *    dispatcher. DOCX (W4b1) + XLS / XLSX (W4b2) + EPUB
 *    (W4b3) are no longer part of this deferred set — they
 *    own explicit `case "docx":`, `case "xls":`,
 *    `case "xlsx":`, and `case "epub":` arms that emit the
 *    typed `docx-source` / `docx-offline` /
 *    `sheet-source` / `sheet-offline` / `epub-source` /
 *    `epub-offline` variants.
 *  - `"tab-not-applicable"` — the legacy
 *    `handleTabClick`'s `${tab} view not available for .${ext}
 *    files — use Raw.` message for any file on the Table or
 *    Tree tab when no W4a Table/Tree renderer exists for the
 *    format. W4a defers ALL Table/Tree renderers to W4b+, so
 *    every file on Table/Tree tabs hits this branch. The
 *    message preserves the legacy wording verbatim — the
 *    spec's "Table/Tree view not available for this format —
 *    use Raw." scenario is satisfied by the dynamic `${tab}
 *    view not available for .${ext} files — use Raw.`
 *    message (the literal `"Table/Tree"` static text in the
 *    spec is a shorthand description; the legacy observable
 *    behavior is the dynamic version, and W4a preserves the
 *    observable behavior).
 *  - `"docx-source"`    — W4b1 DOCX source descriptor. The
 *    dispatcher emits this typed outcome when `format ===
 *    "docx"` + `tab === "Raw"` + `bytes !== null`. The future
 *    React mount (W6+) consumes it: load the legacy-pinned
 *    mammoth CDN via Next 16's `<Script src={scriptUrl}
 *    strategy="afterInteractive" onLoad={convert} onError=
 *    {...}>` (see `node_modules/next/dist/docs/01-app/03-api-
 *    reference/02-components/script.md`), then call
 *    `window[scriptGlobal].convertToHtml({arrayBuffer:
 *    bytes.buffer})`, then inject the resulting HTML via
 *    `Range.createContextualFragment` (mirrors the legacy
 *    `web/file_viewer.js::renderDocx` shape — mammoth
 *    already strips `<script>` + event handlers per
 *    `design.md` §8). Fields:
 *      - `src`         — descriptor URL (download link +
 *        raw-fetch fallback). Sourced from
 *        `ViewerFileDescriptor.url` verbatim.
 *      - `title`       — file basename for the meta strip /
 *        `<iframe title>` / open-in-new-tab gesture. Sourced
 *        from `ViewerFileDescriptor.name`.
 *      - `bytes`       — the SAME `Uint8Array` reference as
 *        the input `bytes` field (the dispatcher passes by
 *        reference, NOT by copy — `mammoth.convertToHtml`
 *        reads the bytes at call time, so a copy would cost
 *        an allocation and gain nothing). The mount treats
 *        the bytes as read-only or copies before mutation
 *        (Uint8Array is a view on a backing ArrayBuffer —
 *        any mutation is visible through the dispatched
 *        reference).
 *      - `scriptUrl`   — pinned mammoth CDN URL
 *        (`MAMMOTH_CDN_URL`). The mount injects this with
 *        Next 16's `<Script>` component so the legacy +
 *        React paths share the exact same CDN URL.
 *      - `scriptGlobal` — window-global name
 *        (`MAMMOTH_GLOBAL_NAME` = `"mammoth"`). The mount
 *        calls `window[scriptGlobal].convertToHtml(...)`
 *        via the pinned global so a future PR that bumps
 *        the library doesn't silently break the conversion
 *        site.
 *  - `"docx-offline"`   — W4b1 DOCX offline fallback. The
 *    dispatcher emits this typed outcome when `format ===
 *    "docx"` + `tab === "Raw"` + `bytes === null`. Mirrors
 *    the legacy `web/file_viewer.js::renderOfflineBanner`
 *    shape so the future React mount paints the same
 *    "Viewer offline — raw download available for X"
 *    banner with a download affordance. Fields:
 *      - `name`        — file basename. Sourced from
 *        `ViewerFileDescriptor.name`.
 *      - `download`    — typed `ViewerLink` (the W4a
 *        pattern). `href` is `ViewerFileDescriptor.url`;
 *        `download` is `ViewerFileDescriptor.name`. Mirrors
 *        the legacy offline banner's `<a href download>`.
 *      - `scriptUrl`   — pinned mammoth CDN URL
 *        (`MAMMOTH_CDN_URL`). The mount needs the URL to
 *        retry the loader or surface a "try again"
 *        affordance after the offline banner renders.
 *      - `scriptGlobal` — window-global name
 *        (`MAMMOTH_GLOBAL_NAME`).
 *      - `reason`      — typed literal `"bytes-missing"`.
 *        The dispatcher can only detect the bytes-missing
 *        offline path at dispatch time (the dispatcher
 *        does not fetch the URL, load the CDN, or call
 *        `convertToHtml`). CDN-load failures and
 *        conversion failures are MOUNT responsibilities
 *        and surface as additional typed branches in a
 *        future iteration (W4b+ ADR).
 *    The `"docx-offline"` branch does NOT carry a free-form
 *    `message` string — the mount paints the offline
 *    wording verbatim from the typed descriptor (kind +
 *    name + download), not from a pre-formatted message
 *    field. Mirrors the W4a `image-error` shape, which
 *    also omits a `message` string so the mount owns the
 *    wording.
 *  - `"sheet-source"`   — W4b2 XLS / XLSX source descriptor.
 *    The dispatcher emits this typed outcome when `format
 *    === "xls" || format === "xlsx"` + `tab === "Raw"` +
 *    `bytes !== null`. The future React mount (W6+)
 *    consumes it: load the legacy-pinned SheetJS CDN via
 *    Next 16's `<Script src={scriptUrl} strategy=
 *    "afterInteractive" onLoad={convert} onError={...}>`
 *    (see `node_modules/next/dist/docs/01-app/03-api-
 *    reference/02-components/script.md`), then call
 *    `window[scriptGlobal].read(bytes, { type: "array"
 *    })` to parse the workbook, then call `window
 *    [scriptGlobal].utils.sheet_to_html(sheet)` to emit
 *    the HTML table, then inject the HTML via
 *    `Range.createContextualFragment` (mirrors the legacy
 *    `web/file_viewer.js::renderSheet` shape — SheetJS
 *    already emits plain `<table>` markup without `<script>`
 *    or event handlers per `design.md` §8). Both XLS and
 *    XLSX dispatch through the same SheetJS path; the
 *    `format` field carries the extension verbatim so the
 *    mount can branch on XLS vs XLSX for format-specific
 *    affordances if needed (SheetJS itself does not
 *    distinguish them at the read site — the same `read`
 *    + `sheet_to_html` call sites handle both). Fields:
 *      - `src`         — descriptor URL (download link +
 *        raw-fetch fallback). Sourced from
 *        `ViewerFileDescriptor.url` verbatim.
 *      - `title`       — file basename for the meta strip
 *        / `<iframe title>` / open-in-new-tab gesture.
 *        Sourced from `ViewerFileDescriptor.name`.
 *      - `bytes`       — the SAME `Uint8Array` reference
 *        as the input `bytes` field (the dispatcher
 *        passes by reference, NOT by copy — `XLSX.read`
 *        reads the bytes at call time, so a copy would
 *        cost an allocation and gain nothing). The mount
 *        treats the bytes as read-only or copies before
 *        mutation. The `Uint8Array` reference contract
 *        is pinned by `tests/test_research_renderers.py::
 *        test_compiled_renderers_passes_runtime_contract`
 *        steps 45-46 (XLS/XLSX mirror the W4b1 DOCX
 *        bytes-reference contract from steps 36-37).
 *      - `scriptUrl`   — pinned SheetJS CDN URL
 *        (`SHEETJS_CDN_URL`). The mount injects this
 *        with Next 16's `<Script>` component so the
 *        legacy + React paths share the exact same CDN
 *        URL.
 *      - `scriptGlobal` — window-global name
 *        (`SHEETJS_GLOBAL_NAME` = `"XLSX"`). The mount
 *        calls `window[scriptGlobal].read(...)` +
 *        `window[scriptGlobal].utils.sheet_to_html(...)`
 *        via the pinned global so a future PR that bumps
 *        the library doesn't silently break the
 *        conversion site.
 *  - `"sheet-offline"`  — W4b2 XLS / XLSX offline
 *    fallback. The dispatcher emits this typed outcome
 *    when `format === "xls" || format === "xlsx"` + `tab
 *    === "Raw"` + `bytes === null`. Mirrors the legacy
 *    `web/file_viewer.js::renderOfflineBanner` shape so
 *    the future React mount paints the same "Viewer
 *    offline — raw download available for X" banner with
 *    a download affordance. Fields:
 *      - `name`        — file basename. Sourced from
 *        `ViewerFileDescriptor.name`.
 *      - `download`    — typed `ViewerLink` (the W4a
 *        pattern). `href` is `ViewerFileDescriptor.url`;
 *        `download` is `ViewerFileDescriptor.name`.
 *        Mirrors the legacy offline banner's `<a href
 *        download>`.
 *      - `scriptUrl`   — pinned SheetJS CDN URL
 *        (`SHEETJS_CDN_URL`). The mount needs the URL to
 *        retry the loader or surface a "try again"
 *        affordance after the offline banner renders.
 *      - `scriptGlobal` — window-global name
 *        (`SHEETJS_GLOBAL_NAME`).
 *      - `reason`      — typed literal `"bytes-missing"`.
 *        The dispatcher can only detect the bytes-missing
 *        offline path at dispatch time (the dispatcher
 *        does not fetch the URL, load the CDN, or call
 *        `XLSX.read`). CDN-load failures and
 *        conversion failures are MOUNT responsibilities
 *        and surface as additional typed branches in a
 *        future iteration (W4b+ ADR).
 *    The `"sheet-offline"` branch does NOT carry a free-
 *    form `message` string — mirrors the W4b1
 *    `docx-offline` shape (mount paints the offline
 *    wording verbatim from the typed descriptor, not from
 *    a pre-formatted message field).
 *  - `"epub-source"`    — W4b3 EPUB source descriptor. The
 *    dispatcher emits this typed outcome when `format ===
 *    "epub"` + `tab === "Raw"` + `bytes !== null`. The future
 *    React mount (W6+) consumes it: load the legacy-pinned
 *    epubjs CDN via Next 16's `<Script src={scriptUrl}
 *    strategy="afterInteractive" onLoad={mount} onError=
 *    {...}>` (see `node_modules/next/dist/docs/01-app/03-api-
 *    reference/02-components/script.md`), then call
 *    `window[scriptGlobal](bytes.buffer)` to construct the
 *    book, then `book.renderTo(hostEl, { width: "100%",
 *    height: "100%" })` to mount it, then attach prev / next
 *    click handlers to `book.prev()` / `book.next()`, then
 *    store the book in a module-scoped `_currentBook` slot
 *    so the NEXT open's mount can call `_currentBook.
 *    destroy()` first (mirrors the legacy lifecycle in
 *    `web/file_viewer.js::renderEpub` verbatim — the legacy
 *    tears down the previous book before mounting the new
 *    one so listeners don't leak). Fields:
 *      - `src`         — descriptor URL (download link +
 *        raw-fetch fallback). Sourced from
 *        `ViewerFileDescriptor.url` verbatim.
 *      - `title`       — file basename for the meta strip
 *        / open-in-new-tab gesture. Sourced from
 *        `ViewerFileDescriptor.name`.
 *      - `bytes`       — the SAME `Uint8Array` reference
 *        as the input `bytes` field (the dispatcher
 *        passes by reference, NOT by copy — `ePub(arrayBuffer)`
 *        reads the bytes at call time, so a copy would cost
 *        an allocation and gain nothing). The mount treats
 *        the bytes as read-only or copies before mutation
 *        (Uint8Array is a view on a backing ArrayBuffer —
 *        any mutation is visible through the dispatched
 *        reference). The `Uint8Array` reference contract
 *        mirrors the W4b1 DOCX + W4b2 XLS / XLSX contract.
 *      - `scriptUrl`   — pinned epubjs CDN URL
 *        (`EPUBJS_CDN_URL`). The mount injects this with
 *        Next 16's `<Script>` component so the legacy +
 *        React paths share the exact same CDN URL.
 *      - `scriptGlobal` — window-global name
 *        (`EPUBJS_GLOBAL_NAME` = `"ePub"`). The mount calls
 *        `window[scriptGlobal](bytes.buffer)` via the pinned
 *        global so a future PR that bumps the library doesn't
 *        silently break the construction site.
 *  - `"epub-offline"`   — W4b3 EPUB offline fallback. The
 *    dispatcher emits this typed outcome when `format ===
 *    "epub"` + `tab === "Raw"` + `bytes === null`. Mirrors
 *    the legacy `web/file_viewer.js::renderOfflineBanner`
 *    shape so the future React mount paints the same "Viewer
 *    offline — raw download available for X" banner with a
 *    download affordance. Fields:
 *      - `name`        — file basename. Sourced from
 *        `ViewerFileDescriptor.name`.
 *      - `download`    — typed `ViewerLink` (the W4a
 *        pattern). `href` is `ViewerFileDescriptor.url`;
 *        `download` is `ViewerFileDescriptor.name`. Mirrors
 *        the legacy offline banner's `<a href download>`.
 *      - `scriptUrl`   — pinned epubjs CDN URL
 *        (`EPUBJS_CDN_URL`). The mount needs the URL to
 *        retry the loader or surface a "try again"
 *        affordance after the offline banner renders.
 *      - `scriptGlobal` — window-global name
 *        (`EPUBJS_GLOBAL_NAME`).
 *      - `reason`      — typed literal `"bytes-missing"`.
 *        The dispatcher can only detect the bytes-missing
 *        offline path at dispatch time (the dispatcher
 *        does not fetch the URL, load the CDN, or call
 *        `ePub(arrayBuffer)`). CDN-load failures and
 *        construction failures are MOUNT responsibilities
 *        and surface as additional typed branches in a
 *        future iteration (W4b+ ADR). epubjs renders fail
 *        silently if the bytes aren't a valid EPUB archive
 *        — the mount owns the validate-and-recover path
 *        (mirrors the legacy `renderEpub` catch branch
 *        that paints the offline banner when the
 *        `ePub(arrayBuffer)` call throws).
 *    The `"epub-offline"` branch does NOT carry a free-form
 *    `message` string — mirrors the W4b1 DOCX + W4b2 XLS /
 *    XLSX offline shapes (mount paints the offline wording
 *    verbatim from the typed descriptor, not from a pre-
 *    formatted message field).
 *  - `"tab-not-applicable"` stays the only Table / Tree
 *    outcome for EPUB. EPUB has NO Table renderer (no
 *    spreadsheet shape) and NO Tree renderer (epubjs
 *    renders an EPUB as a paged book, not a hierarchical
 *    outline — the future mount's EPUB viewer is the
 *    W4b3 source / offline surface itself, scoped to Raw).
 *    The Table/Tree branch at the top of the dispatcher
 *    short-circuits before the format switch so EPUB on
 *    Table/Tree hits `tab-not-applicable` with the legacy
 *    `${tab} view not available for .${ext} files — use Raw.`
 *    message. A future mount that wants a Table or Tree
 *    renderer for EPUB would land as a separately authorized
 *    follow-up slice. */
export type ViewerDispatch =
  | {
      readonly kind: "pdf-iframe";
      readonly src: string;
      readonly title: string;
      readonly fallback: ViewerLink;
    }
  | {
      readonly kind: "html-iframe";
      readonly src: string;
      readonly sandbox: "";
      readonly title: string;
    }
  | {
      readonly kind: "text-pre";
      readonly body: string;
    }
  | {
      readonly kind: "image";
      readonly src: string;
      readonly alt: string;
      readonly title: string;
      readonly advisory: ViewerImageAdvisory | null;
    }
  | {
      readonly kind: "image-error";
      readonly name: string;
      readonly download: ViewerLink;
    }
  | {
      readonly kind: "svg-sanitized";
      readonly svg: string;
      readonly className: string;
      readonly preserveAspectRatio: string;
    }
  | {
      readonly kind: "video";
      readonly src: string;
      readonly title: string;
      readonly controls: true;
      readonly preload: "metadata";
    }
  | {
      readonly kind: "unsupported";
      readonly message: string;
      readonly download: ViewerLink;
    }
  | {
      readonly kind: "docx-source";
      readonly src: string;
      readonly title: string;
      readonly bytes: Uint8Array;
      readonly scriptUrl: string;
      readonly scriptGlobal: string;
    }
  | {
      readonly kind: "docx-offline";
      readonly name: string;
      readonly download: ViewerLink;
      readonly scriptUrl: string;
      readonly scriptGlobal: string;
      readonly reason: "bytes-missing";
    }
  | {
      readonly kind: "sheet-source";
      readonly src: string;
      readonly title: string;
      readonly bytes: Uint8Array;
      readonly scriptUrl: string;
      readonly scriptGlobal: string;
    }
  | {
      readonly kind: "sheet-offline";
      readonly name: string;
      readonly download: ViewerLink;
      readonly scriptUrl: string;
      readonly scriptGlobal: string;
      readonly reason: "bytes-missing";
    }
  | {
      readonly kind: "epub-source";
      readonly src: string;
      readonly title: string;
      readonly bytes: Uint8Array;
      readonly scriptUrl: string;
      readonly scriptGlobal: string;
    }
  | {
      readonly kind: "epub-offline";
      readonly name: string;
      readonly download: ViewerLink;
      readonly scriptUrl: string;
      readonly scriptGlobal: string;
      readonly reason: "bytes-missing";
    }
  | {
      readonly kind: "tab-not-applicable";
      readonly message: string;
    };

/** Dispatch input — wraps the file descriptor + the active
 *  viewer tab + the injected bytes. The contract takes the
 *  bytes through the input (NOT through a fetch call) so the
 *  dispatcher stays framework-free and so the future React
 *  mount can read bytes through the W3 adapter once and
 *  thread them through the dispatch without the dispatcher
 *  importing W3 (mirrors the layered architecture + the W4a
 *  split directive).
 *
 *  `bytes` is nullable because not every W4a family needs
 *  bytes: PDF / HTML / image / video pass the URL straight
 *  through to the renderer, TXT / MD / SVG need the UTF-8
 *  decoded body / XSS-scrubbed markup. When a renderer that
 *  needs bytes receives `bytes: null`, the dispatcher falls
 *  back to `image-error` (SVG) or `unsupported` with a
 *  parse-error message (TXT / MD) — mirroring the legacy
 *  `try / catch` fallbacks in `renderSvg` + `renderAsPre`.
 *  A future W6 mount that forgets to thread bytes would
 *  surface the typed fallback branch instead of crashing —
 *  same defensive shape as the W3 adapter's `ExplorerApiError`
 *  (mirrors `tests/test_research_infra.py::
 *  test_compiled_infra_passes_runtime_contract` steps 4 + 8). */
export interface ViewerDispatchInput {
  readonly file: ViewerFileDescriptor;
  readonly tab: ViewerTab;
  readonly bytes: Uint8Array | null;
}

/** Strip `<script>…</script>` blocks AND `on*=` event-handler
 *  attributes from an SVG markup string. Pure string-level
 *  regex — no `DOMParser`, no `document.createTreeWalker`, no
 *  browser APIs. Replicates the legacy
 *  `web/file_viewer.js::renderSvg` XSS scrub verbatim:
 *
 *  1. Validate the markup starts with `<svg` (case-insensitive).
 *     Anything else returns `""` so the dispatcher's SVG branch
 *     falls back to `image-error` (mirrors the legacy
 *     `throw new Error("Document is not a valid SVG")` path).
 *  2. Strip every `<script>` element — both PAIRED
 *     (`<script …>…</script>`) AND SELF-CLOSING
 *     (`<script src="…" />`, `<script src="…"/>`) shapes,
 *     case-insensitively. The legacy oracle calls
 *     `svg.querySelectorAll("script").forEach((n) =>
 *     n.remove())`; the DOM query returns BOTH shapes (paired
 *     + self-closing) inherently, and the browser's SVG
 *     parser is case-insensitive on tag names, so `<SCRIPT>`,
 *     `<Script>`, `<script src="…"/>` all reach the same
 *     removal path. The regex form mirrors the legacy with
 *     two non-overlapping case-insensitive patterns (paired
 *     first, then self-closing). A `<script>` inside an HTML
 *     comment is not a real script element, and SVGs that
 *     include literal `<script>` blocks as text content are
 *     not XSS-relevant — they'd need to be unescaped into
 *     elements first, which the browser's HTML parser
 *     refuses to do inside an `<svg>` root.
 *  3. Strip every `on*=` event-handler attribute (e.g.
 *     `onclick`, `onload`, `ONCLICK`, `OnMouseover`,
 *     `onLoad`). The legacy oracle walks every element and
 *     drops attributes whose name starts with `"on"`
 *     regardless of case; the regex form mirrors the legacy
 *     exactly with the `/gi` flag — it strips
 *     `on[a-z]+ = "value"` / `='value'` / `=value` (no
 *     quotes) and tolerates arbitrary whitespace before the
 *     attribute. Non-event attributes (`href`, `class`,
 *     `viewBox`, `xmlns`, etc.) are preserved verbatim.
 *
 *  Pure function — same input string yields the same output on
 *  every call. The focused runtime harness exercises the
 *  document-valid path, the script-removal path, the
 *  event-handler-removal path, the document-invalid path, and
 *  the multi-block / multi-attribute stress paths so a future
 *  PR that loosens the scrub trips a focused test before
 *  review.
 *
 *  Note: this is a SHAPE-equivalent scrub, not a security-grade
 *  SVG sanitizer. The legacy oracle uses the same
 *  `<script>` + `on*=` approach and ships as the Browser tab's
 *  XSS defense. A future work unit that swaps in a
 *  security-grade sanitizer (DOMPurify, parse5, etc.) would
 *  land as a separately authorized slice — for now W4a
 *  preserves the legacy scrub verbatim so the React cutover
 *  reaches feature parity before hardening. */
export function sanitizeSvgMarkup(svgText: string): string {
  const trimmed = svgText.trim();
  // 1. Document-validity guard — anything that doesn't start
  //    with `<svg` (case-insensitive, with optional whitespace
  //    + a `>` or another character) is not a valid SVG root
  //    and returns "" so the dispatcher's SVG branch falls back
  //    to `image-error`. Mirrors the legacy
  //    `if (!svg || svg.nodeName.toLowerCase() !== "svg") throw`
  //    guard.
  if (!/^<svg(\s|>|\/)/i.test(trimmed)) return "";
  // 2. Strip `<script>` elements — both PAIRED (`<script …>…</script>`)
  //    AND SELF-CLOSING (`<script src="…" />`, `<script src="…"/>`)
  //    shapes, case-insensitively. The legacy oracle calls
  //    `svg.querySelectorAll("script").forEach((n) =>
  //    n.remove())`; the DOM query returns BOTH shapes (paired +
  //    self-closing) and the browser's SVG parser is case-
  //    insensitive on tag names. The regex form mirrors the legacy
  //    with two non-overlapping case-insensitive patterns (paired
  //    first, then self-closing; the paired regex is non-greedy on
  //    the inner `[\s\S]*?` so back-to-back scripts each match
  //    their own close-tag, and the self-closing regex uses a
  //    non-greedy attribute walk so the `/>` lands at the actual
  //    close — tolerates both `<script/>` and `<script … />`).
  const withoutPairedScripts = trimmed.replace(
    /<script\b[^>]*>[\s\S]*?<\/script\s*>/gi,
    "",
  );
  const withoutScripts = withoutPairedScripts.replace(
    /<script\b[^>]*?\/\s*>/gi,
    "",
  );
  // 3. Strip `on*=` event-handler attributes (case-insensitive —
  //    e.g. `ONCLICK`, `OnClick`, `onMouseover`). The `/gi` flag
  //    handles the case-insensitive match; otherwise this step
  //    tolerates double-quoted / single-quoted / unquoted values
  //    and any amount of whitespace between the previous tag char
  //    and the attribute name.
  const withoutOnAttrs = withoutScripts.replace(
    /\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*)/gi,
    "",
  );
  return withoutOnAttrs;
}

/** Format a byte count as the legacy `formatSize` helper does —
 *  B / KB / MB / GB with one decimal of precision. Used by the
 *  image advisory message so the React mount doesn't need to
 *  ship its own size-formatter helper. Pure function; never
 *  called with `null` (the `ViewerFileDescriptor.size` field is
 *  `number`, defaulted to `0` by the W1 wire projection). */
function formatSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/** Build the optional `ViewerImageAdvisory` for a file of the
 *  given size. Returns `null` under the threshold so the React
 *  mount doesn't paint a banner for normal-sized images.
 *  Mirrors the legacy `renderImage`'s `big = (file.size || 0) >
 *  IMAGE_BIG_FILE_BYTES` check. */
function buildImageAdvisory(size: number): ViewerImageAdvisory | null {
  if (!Number.isFinite(size) || size <= IMAGE_BIG_FILE_BYTES) return null;
  return { message: `Large image (${formatSize(size)}) — decoding may be slow.` };
}

/** Build the `image-error` dispatch — used by the SVG branch on
 *  parse failure AND by the SVG branch when bytes are missing.
 *  The future React mount emits the same typed error card
 *  regardless of which failure surfaced (decode failure, fetch
 *  failure, parse failure), so the message stays consistent
 *  with the legacy `renderImageError` oracle. */
function buildImageError(file: ViewerFileDescriptor): ViewerDispatch {
  return {
    kind: "image-error",
    name: file.name,
    download: { href: file.url, download: file.name },
  };
}

/** Build the `docx-offline` dispatch — used by the W4b1 DOCX
 *  branch when the input bytes are missing. Mirrors the legacy
 *  `web/file_viewer.js::renderOfflineBanner` recovery path:
 *  the future React mount paints the same "Viewer offline —
 *  raw download available for X" banner with a download
 *  affordance. The branch carries the pinned mammoth CDN URL
 *  + global name so the mount can retry the loader or surface
 *  a "try again" affordance after the offline banner renders.
 *  The typed `reason: "bytes-missing"` literal documents the
 *  specific offline path the dispatcher detected — the only
 *  offline path the dispatcher can detect at dispatch time
 *  (CDN-load + convertToHtml failures happen at the mount and
 *  are not part of this contract). */
function buildDocxOffline(file: ViewerFileDescriptor): ViewerDispatch {
  return {
    kind: "docx-offline",
    name: file.name,
    download: { href: file.url, download: file.name },
    scriptUrl: MAMMOTH_CDN_URL,
    scriptGlobal: MAMMOTH_GLOBAL_NAME,
    reason: "bytes-missing",
  };
}

/** Build the `sheet-offline` dispatch — used by the W4b2 XLS /
 *  XLSX branch when the input bytes are missing. Mirrors the
 *  W4b1 `buildDocxOffline` helper verbatim: the future React
 *  mount paints the same legacy "Viewer offline — raw download
 *  available for X" banner (`web/file_viewer.js::
 *  renderOfflineBanner`) with a download affordance. The
 *  branch carries the pinned SheetJS CDN URL + global name so
 *  the mount can retry the loader or surface a "try again"
 *  affordance after the offline banner renders. The typed
 *  `reason: "bytes-missing"` literal documents the specific
 *  offline path the dispatcher detected — the only offline
 *  path the dispatcher can detect at dispatch time (CDN-load
 *  + `XLSX.read` + `sheet_to_html` failures happen at the
 *  mount and are not part of this contract). */
function buildSheetOffline(file: ViewerFileDescriptor): ViewerDispatch {
  return {
    kind: "sheet-offline",
    name: file.name,
    download: { href: file.url, download: file.name },
    scriptUrl: SHEETJS_CDN_URL,
    scriptGlobal: SHEETJS_GLOBAL_NAME,
    reason: "bytes-missing",
  };
}

/** Build the `epub-offline` dispatch — used by the W4b3 EPUB
 *  branch when the input bytes are missing. Mirrors the W4b1
 *  `buildDocxOffline` + W4b2 `buildSheetOffline` helpers
 *  verbatim: the future React mount paints the same legacy
 *  "Viewer offline — raw download available for X" banner
 *  (`web/file_viewer.js::renderOfflineBanner`) with a
 *  download affordance. The branch carries the pinned
 *  epubjs CDN URL + global name so the mount can retry the
 *  loader or surface a "try again" affordance after the
 *  offline banner renders. The typed `reason: "bytes-missing"`
 *  literal documents the specific offline path the dispatcher
 *  detected — the only offline path the dispatcher can detect
 *  at dispatch time (CDN-load + `ePub(arrayBuffer)`
 *  construction failures happen at the mount and are not
 *  part of this contract; the legacy `renderEpub` catch
 *  branch paints the same banner when the `ePub(arrayBuffer)`
 *  call throws on invalid EPUB archives). */
function buildEpubOffline(file: ViewerFileDescriptor): ViewerDispatch {
  return {
    kind: "epub-offline",
    name: file.name,
    download: { href: file.url, download: file.name },
    scriptUrl: EPUBJS_CDN_URL,
    scriptGlobal: EPUBJS_GLOBAL_NAME,
    reason: "bytes-missing",
  };
}

/** Build the `unsupported` dispatch — used by the DOC branch
 *  (with the spec's "Legacy .doc cannot be rendered inline."
 *  message), the "other" branch (with the wire-extension
 *  message), and the still-W4b+-deferred format default
 *  branch (with the format-literal message). The message text
 *  is the dispatcher's responsibility — the React mount emits
 *  it verbatim via `<p>`. */
function renderUnsupported(
  file: ViewerFileDescriptor,
  message: string,
): ViewerDispatch {
  return {
    kind: "unsupported",
    message,
    download: { href: file.url, download: file.name },
  };
}

/** Decode the file's bytes as UTF-8 text. Returns the decoded
 *  string regardless of byte validity (`fatal: false`) — the
 *  legacy `renderAsPre` paints whatever the browser hands back,
 *  including replacement characters for invalid sequences.
 *  `TextDecoder` is part of ES2022 (Node 18+ + every modern
 *  browser), so no polyfill is needed. */
function decodeUtf8(bytes: Uint8Array): string {
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

/** Decode `bytes` as UTF-8 and emit the `text-pre` dispatch —
 *  or fall back to `unsupported` with a parse-error framing
 *  when bytes are missing (mirrors the legacy
 *  `renderAsPre` catch branch). */
function decodeTextPre(
  file: ViewerFileDescriptor,
  bytes: Uint8Array | null,
): ViewerDispatch {
  if (bytes === null) {
    return renderUnsupported(
      file,
      `Failed to load ${file.format} — bytes not available.`,
    );
  }
  return { kind: "text-pre", body: decodeUtf8(bytes) };
}

/** Extract the file's lowercase extension from its wire
 *  `path` field. Used only by the `"other"` branch (the W1
 *  `FileFormat` literal `"other"` carries no extension
 *  information — the W6 mount stores the wire extension on
 *  `ExplorerFileNode.extension`, but the dispatcher reads
 *  from the descriptor's `path` field because the
 *  descriptor's `format` is already typed `"other"` and the
 *  raw extension string is needed for the message text).
 *
 *  Returns `""` when the basename has no `.` separator or the
 *  separator is at the boundary (leading-dot or trailing-dot
 *  hidden files) — the legacy's `Format .{ext || "?"}`
 *  fallback handles both cases. */
function extensionFromPath(path: string): string {
  const basename = path.split("/").pop() ?? "";
  const dot = basename.lastIndexOf(".");
  if (dot <= 0 || dot >= basename.length - 1) return "";
  return basename.slice(dot + 1).toLowerCase();
}

/** Pure viewer dispatcher — converts a typed
 *  `ViewerDispatchInput` into a typed `ViewerDispatch`
 *  outcome. The W4a contract covers the eight no-CDN
 *  families (PDF, HTML/HTM, TXT, MD, DOC, JPG/JPEG/PNG/GIF/
 *  WEBP/BMP, SVG, MP4/WEBM/OGV) plus the "other" fallback
 *  plus the Table/Tree tab-not-applicable feedback. The
 *  W4b1 + W4b2 + W4b3 contracts extend the dispatcher
 *  with three CDN-dependent families: DOCX (W4b1, pinned
 *  mammoth CDN), XLS / XLSX (W4b2, pinned SheetJS CDN),
 *  and EPUB (W4b3, pinned epubjs CDN) — all three emit
 *  typed source / offline outcomes that carry the
 *  descriptor + bytes + pinned CDN URL + global name so
 *  a future React mount (W6+) can load the libraries and
 *  construct / convert / render the bytes. CDN-dependent
 *  families still deferred: CSV / TSV (W4b4, Papa Parse),
 *  JSON (W4b4, native), and Markdown-as-HTML
 *  (separately authorized). The dispatcher returns the
 *  `unsupported` or `tab-not-applicable` branches for
 *  those combinations until the later slices extend the
 *  contract.
 *
 *  Same input always yields the same output (the function
 *  is deterministic and pure — no `Date.now()`, no
 *  `Math.random()`, no side effects on `input`). The focused
 *  runtime harness exercises the dispatcher end-to-end on
 *  every W4a-supported format, on every W4b1 DOCX branch,
 *  on every W4b2 XLS / XLSX branch, on every W4b3 EPUB
 *  branch, and on every W4b4+ deferred format so the
 *  contract stays honest at the boundary. */
export function dispatchViewer(input: ViewerDispatchInput): ViewerDispatch {
  const { file, tab, bytes } = input;

  // Tab gate — Table / Tree tabs have NO W4a renderer. W4a
  // defers the Table renderer (CSV/TSV via Papa Parse CDN)
  // and the Tree renderer (JSON) to W4b+. Until those land,
  // every file on Table / Tree surfaces the legacy
  // `${tab} view not available for .${ext} files — use Raw.`
  // message verbatim so the React mount's empty-state card
  // matches the oracle byte-for-byte. W4b+ extends this
  // branch by adding Table-on-csv/tsv and Tree-on-json cases
  // that return their respective CDN-dependent dispatches.
  if (tab === "Table" || tab === "Tree") {
    const extLabel =
      file.format === "other" ? extensionFromPath(file.path) || "?" : file.format;
    return {
      kind: "tab-not-applicable",
      message: `${tab} view not available for .${extLabel} ${TAB_NOT_APPLICABLE_SUFFIX}`,
    };
  }

  // Raw tab — dispatch by format. The W4a families are
  // enumerated explicitly; the W4a-deferred formats fall
  // through to the default arm with the legacy "Format .xyz
  // not supported in viewer." message + download link so the
  // React mount paints the same empty-state card until W4b+
  // extends the dispatcher.
  switch (file.format) {
    case "pdf":
      return {
        kind: "pdf-iframe",
        src: file.url,
        title: file.name,
        fallback: { href: file.url, download: file.name },
      };
    case "html":
    case "htm":
      return {
        kind: "html-iframe",
        src: file.url,
        sandbox: "",
        title: file.name,
      };
    case "txt":
    case "md":
      // W4a preserves the legacy Markdown-as-text behavior —
      // `.md` files render inside the same fenced `<pre>` as
      // `.txt`. The spec's "Markdown rendering" scenario
      // (HTML via marked.js CDN) is deferred to a separately
      // authorized later slice per the W4a split. Mirrors
      // `web/file_viewer.js::renderMd` which delegates to
      // `renderAsPre` verbatim.
      return decodeTextPre(file, bytes);
    case "doc":
      // Legacy DOC has no inline renderer — the download link
      // is the recovery path. The message text matches the
      // spec's "Legacy .doc fallback" scenario verbatim.
      return renderUnsupported(file, "Legacy .doc cannot be rendered inline.");
    case "jpg":
    case "jpeg":
    case "png":
    case "gif":
    case "webp":
    case "bmp":
      return {
        kind: "image",
        src: file.url,
        alt: file.name,
        title: file.name,
        advisory: buildImageAdvisory(file.size),
      };
    case "svg":
      // SVG needs the bytes (to scrub `<script>` + `on*=`
      // attrs). When bytes are missing the dispatcher falls
      // back to `image-error` — mirrors the legacy
      // `renderSvg`'s catch branch.
      if (bytes === null) return buildImageError(file);
      {
        const text = decodeUtf8(bytes);
        const sanitized = sanitizeSvgMarkup(text);
        if (!sanitized) return buildImageError(file);
        return {
          kind: "svg-sanitized",
          svg: sanitized,
          className: "fex-image",
          preserveAspectRatio: "xMidYMid meet",
        };
      }
    case "mp4":
    case "webm":
    case "ogv":
      return {
        kind: "video",
        src: file.url,
        title: file.name,
        controls: true,
        preload: "metadata",
      };
    case "docx":
      // W4b1 — DOCX source descriptor. The dispatcher emits
      // a typed `docx-source` outcome carrying the
      // descriptor + bytes + pinned mammoth CDN URL +
      // global name so the future React mount (W6+) can
      // load the legacy-pinned mammoth library via Next 16's
      // `<Script src={scriptUrl} strategy="afterInteractive"
      // onLoad={convert} onError={...}>` and call
      // `window[scriptGlobal].convertToHtml({arrayBuffer:
      // bytes.buffer})`. The application layer does NOT
      // load mammoth, fetch the URL, or invoke
      // `convertToHtml` — it only emits the typed source
      // descriptor for the mount to consume.
      //
      // Bytes-missing fallback: when `bytes === null` the
      // dispatcher emits `docx-offline` (typed `name` +
      // `download` + `scriptUrl` + `scriptGlobal` +
      // `reason: "bytes-missing"`) so the future mount
      // paints the same legacy "Viewer offline — raw
      // download available for X" banner (`web/file_viewer.
      // js::renderOfflineBanner`) verbatim. Mirrors the
      // W4a SVG / TXT bytes-missing fallbacks (the
      // dispatcher detects the failure at dispatch time;
      // CDN-load + convertToHtml failures happen at the
      // mount and are not part of this contract).
      if (bytes === null) return buildDocxOffline(file);
      return {
        kind: "docx-source",
        src: file.url,
        title: file.name,
        // Pass-by-reference: the future mount reads the
        // bytes at mount time and feeds them straight to
        // `window.mammoth.convertToHtml`. Copying the bytes
        // at dispatch time would cost a Uint8Array
        // allocation per dispatch and gain nothing (the
        // mount doesn't mutate the bytes). The future mount
        // is responsible for treating the bytes as
        // read-only or copying before mutation. The
        // `Uint8Array` reference contract is pinned by
        // `tests/test_research_renderers.py::test_compiled_
        // renderers_passes_runtime_contract` step 36-37.
        bytes,
        scriptUrl: MAMMOTH_CDN_URL,
        scriptGlobal: MAMMOTH_GLOBAL_NAME,
      };
    case "xls":
    case "xlsx":
      // W4b2 — XLS / XLSX source descriptor. Both XLS
      // and XLSX dispatch through the same SheetJS path
      // (SheetJS does not branch on the XLS vs XLSX
      // extension at the read site — the same `read` +
      // `sheet_to_html` call sites handle both). The
      // `format` field carries the extension verbatim so
      // the mount can branch on XLS vs XLSX for format-
      // specific affordances if needed (e.g. legacy
      // export warnings, OOXML vs BIFF messages).
      // The dispatcher emits a typed `sheet-source`
      // outcome carrying the descriptor + bytes + pinned
      // SheetJS CDN URL + global name so the future
      // React mount (W6+) can load the legacy-pinned
      // SheetJS library via Next 16's `<Script src=
      // {scriptUrl} strategy="afterInteractive"
      // onLoad={convert} onError={...}>` and call
      // `window[scriptGlobal].read(bytes, { type:
      // "array" })` to parse the workbook, then
      // `window[scriptGlobal].utils.sheet_to_html(sheet)`
      // to emit the HTML table. The application layer
      // does NOT load SheetJS, fetch the URL, or invoke
      // `read` / `sheet_to_html` — it only emits the
      // typed source descriptor for the mount to
      // consume.
      //
      // Bytes-missing fallback: when `bytes === null`
      // the dispatcher emits `sheet-offline` (typed
      // `name` + `download` + `scriptUrl` +
      // `scriptGlobal` + `reason: "bytes-missing"`) so
      // the future mount paints the same legacy
      // "Viewer offline — raw download available for
      // X" banner (`web/file_viewer.js::
      // renderOfflineBanner`) verbatim. Mirrors the
      // W4a SVG / TXT + W4b1 DOCX bytes-missing
      // fallbacks.
      //
      // Table/Tree gate: XLS / XLSX have NO Table /
      // Tree renderer in this contract (SheetJS emits
      // HTML tables, not a dedicated spreadsheet widget).
      // The Table/Tree branch at the top of the
      // dispatcher short-circuits before the format
      // switch so XLS / XLSX on Table/Tree tabs hits
      // `tab-not-applicable` with the legacy
      // `${tab} view not available for .${ext} files
      // — use Raw.` message. The future mount can
      // override this branch with a SheetJS-backed
      // Table renderer as a separately authorized
      // follow-up slice.
      if (bytes === null) return buildSheetOffline(file);
      return {
        kind: "sheet-source",
        src: file.url,
        title: file.name,
        // Pass-by-reference: the future mount reads
        // the bytes at mount time and feeds them
        // straight to `window.XLSX.read(bytes, { type:
        // "array" })`. Copying the bytes at dispatch
        // time would cost a Uint8Array allocation per
        // dispatch and gain nothing (the mount doesn't
        // mutate the bytes). The future mount is
        // responsible for treating the bytes as
        // read-only or copying before mutation. The
        // `Uint8Array` reference contract mirrors the
        // W4b1 DOCX bytes-reference contract (pinned by
        // `tests/test_research_renderers.py::
        // test_compiled_renderers_passes_runtime_
        // contract` steps 45-46).
        bytes,
        scriptUrl: SHEETJS_CDN_URL,
        scriptGlobal: SHEETJS_GLOBAL_NAME,
      };
    case "epub":
      // W4b3 — EPUB source descriptor. The dispatcher
      // emits a typed `epub-source` outcome carrying the
      // descriptor + bytes + pinned epubjs CDN URL +
      // global name so the future React mount (W6+)
      // can load the legacy-pinned epubjs library via
      // Next 16's `<Script src={scriptUrl} strategy=
      // "afterInteractive" onLoad={mount} onError=
      // {...}>` (see `node_modules/next/dist/docs/
      // 01-app/03-api-reference/02-components/script.md`)
      // and call `window[scriptGlobal](bytes.buffer)`
      // to construct the book. The application layer
      // does NOT load epubjs, fetch the URL, construct
      // the book, or invoke `renderTo` / `prev` / `next` /
      // `destroy` — it only emits the typed source
      // descriptor for the mount to consume. The mount
      // owns the full EPUB render lifecycle (book
      // construction + `book.renderTo(hostEl, ...)` +
      // prev / next click handlers + module-scoped
      // `_currentBook.destroy()` teardown on the NEXT
      // open so listeners don't leak — mirrors the
      // legacy `web/file_viewer.js::renderEpub`
      // verbatim).
      //
      // Bytes-missing fallback: when `bytes === null`
      // the dispatcher emits `epub-offline` (typed
      // `name` + `download` + `scriptUrl` +
      // `scriptGlobal` + `reason: "bytes-missing"`) so
      // the future mount paints the same legacy
      // "Viewer offline — raw download available for
      // X" banner (`web/file_viewer.js::
      // renderOfflineBanner`) verbatim. Mirrors the
      // W4a SVG / TXT + W4b1 DOCX + W4b2 XLS / XLSX
      // bytes-missing fallbacks.
      //
      // Table / Tree gate: EPUB has NO Table / Tree
      // renderer in this contract (epubjs renders an
      // EPUB as a paged book, not a Table widget or a
      // Tree widget — the future mount's EPUB viewer
      // is the W4b3 source / offline surface itself,
      // scoped to Raw). The Table / Tree branch at
      // the top of the dispatcher short-circuits
      // before the format switch so EPUB on Table /
      // Tree tabs hits `tab-not-applicable` with the
      // legacy `${tab} view not available for .${ext}
      // files — use Raw.` message. The future mount
      // can override this branch with a Table / Tree
      // renderer for EPUB as a separately authorized
      // follow-up slice.
      if (bytes === null) return buildEpubOffline(file);
      return {
        kind: "epub-source",
        src: file.url,
        title: file.name,
        // Pass-by-reference: the future mount reads
        // the bytes at mount time and feeds them
        // straight to `window.ePub(bytes.buffer)`.
        // Copying the bytes at dispatch time would
        // cost a Uint8Array allocation per dispatch
        // and gain nothing (the mount doesn't mutate
        // the bytes). The future mount is responsible
        // for treating the bytes as read-only or
        // copying before mutation. The `Uint8Array`
        // reference contract mirrors the W4b1 DOCX +
        // W4b2 XLS / XLSX bytes-reference contracts
        // (pinned by `tests/test_research_renderers.
        // py::test_compiled_renderers_passes_runtime_
        // contract` steps 36-37 + 45-46 + the new
        // W4b3 EPUB steps 56-57).
        bytes,
        scriptUrl: EPUBJS_CDN_URL,
        scriptGlobal: EPUBJS_GLOBAL_NAME,
      };
    case "other":
      // Unknown extensions (e.g. .zip, .exe) — the message
      // uses the wire extension from the descriptor's `path`
      // field. Mirrors the legacy
      // `Format .${ext || "?"} not supported in viewer.`
      // fallback.
      return renderUnsupported(
        file,
        `Format .${extensionFromPath(file.path) || "?"} not supported in viewer.`,
      );
    default:
      // Still-W4b+-deferred formats: CSV, TSV,
      // JSON. These require CDN-dependent or
      // native renderers (Papa Parse, native JSON
      // tree) and land in separately authorized
      // W4b+ slices. DOCX is OWNED by W4b1 (the
      // explicit `case "docx":` arm above) and is
      // no longer part of this deferred set; XLS /
      // XLSX are OWNED by W4b2 (the explicit
      // `case "xls":` + `case "xlsx":` arm above)
      // and are also no longer part of this
      // deferred set; EPUB is OWNED by W4b3 (the
      // explicit `case "epub":` arm above) and is
      // no longer part of this deferred set. The
      // default arm returns the `unsupported`
      // branch with the format-literal message so
      // the React mount paints the same
      // download-link card as the legacy
      // `renderUnsupported` oracle. W4b4 replaces
      // this arm by adding explicit `case "csv":`,
      // `case "tsv":`, `case "json":` arms above
      // it.
      return renderUnsupported(
        file,
        `Format .${file.format} not supported in viewer.`,
      );
  }
}
