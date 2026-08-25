# Changelog

All notable changes to **taxa** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and entries are grouped
by the SDD change that introduced them.

## Unreleased

### Added — File Explorer (Browser tab)

The **Browser** header tab now mounts a two-pane file explorer for the
selected taxon's materialized research folder. The change ships in two
PRs:

- **PR 1 — Backend** (merged as #25): two new endpoints exposed by
  `api/server.py`:
  - `GET /api/taxon/{taxon_id}/files` — recursive tree JSON of the
    taxon's `./Research/<sanitized-root-to-taxon>/…` folder. Returns
    `exists: false` with `root: null` when the folder isn't materialized
    (200, not 404 — distinguishes "taxon doesn't exist" from "folder
    not yet on disk").
  - `GET /api/taxon/{taxon_id}/files/serve?path=<rel>` — streams a single
    file with a `Content-Type` matched per extension (PDF, EPUB, HTML,
    MD, TXT, DOC, DOCX, XLS, XLSX, with `application/octet-stream` as
    the unsupported fallback). `Content-Disposition: inline` so embedded
    viewers consume the body directly. Path traversal (`..`, absolute
    paths, symlink escapes) is rejected with HTTP 400 *before* any byte
    is read. Files larger than the 100 MB streaming cap return HTTP
    413. The OpenAPI smoke (`make smoke`) was extended to assert both
    new routes are present in the schema.

- **PR 2 — Frontend** (this branch): the Browser tab integration that
  consumes the two endpoints:
  - `state.explorer` (new field in `web/state.js`) tracks the recursive
    tree, the currently-opened file path + format, and the active
    Raw / Table / Tree viewer tab.
  - `web/nav.js` exports `mountFileExplorer(rootTaxonId)` and
    `clearFileExplorer()`. The header nav links (Browser / Classification
    / Settings) carry `data-action="nav-tab"` + `data-path="<tab>"`; the
    click delegation in `nav.js` routes each click to the matching mount
    or restore.
  - `web/file_explorer.js` (new) — recursive tree rendering on the
    left, file viewer on the right, with single-click (highlight only)
    and double-click (open in viewer) semantics. Folder expand/collapse
    is per-folder via a chevron button; selection lives in DOM via
    `data-file-path` / `data-folder-path` attributes. AbortController
    drops in-flight fetches when the user leaves the Browser tab.
  - `web/file_viewer.js` (new) — format dispatcher. One renderer per
    supported format: `renderPdf` (iframe), `renderHtml` (sandboxed
    iframe), `renderText` / `renderMd` (fenced `<pre>`), `renderDocx`
    (mammoth.js), `renderSheet` (SheetJS, with a sheet picker for
    multi-sheet workbooks), `renderEpub` (epubjs, with prev/next page
    controls), and `renderUnsupported` (download link fallback for
    `.doc`, `.zip`, etc.). CDN libraries load lazily via
    `loadScriptOnce(name, src)` so users who never open a `.docx` /
    `.xlsx` / `.epub` don't pay the ~600 KB download cost.
  - `web/index.html` adds three `<script>` tags with **pinned** CDN
    URLs (mammoth.js@1.8.0, xlsx@0.18.5, epubjs@0.3.93) plus an inline
    reproducibility comment next to each tag. Also adds `.fex-*` CSS
    classes for the meta strip, tab strip, snippet frame, two-pane
    shell, and selection / hover styles.
  - Empty states — three distinct messages:
    - `state.selected === null` → "Select a taxon to browse its files."
      (no API call, no listeners).
    - `exists: false` from the tree endpoint → "No files yet —
      materialize this taxon to create its folder." (in the right
      viewer pane).
    - Tree loaded but no file opened → "Double-click a file in the
      tree to open it here." (in the right viewer pane).

### Security notes

- The same-origin path-safety guarantees on `/files/serve` (rejection
  of `..`, absolute paths, and symlink escapes via `Path.resolve()` +
  `is_relative_to`) protect against an attacker crafting a URL to
  read arbitrary files on the server.
- `renderHtml` uses `sandbox=""` (no `allow-same-origin`) on its
  iframe so a same-origin HTML file can't reach the parent page's
  cookies / DOM. See `file_viewer.js:renderHtml`.
- `mammoth.js` strips `<script>` and event handlers from its
  `convertToHtml` output (documented in the library), bounding the
  same-origin XSS surface for `.docx` rendering.
- The `renderPdf` iframe is type-only (`type="application/pdf"`); no
  script injection possible.
