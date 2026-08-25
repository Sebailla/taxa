# File Explorer & Viewer — Proposal

> **Source**: Engram observation `sdd/file-explorer/proposal` (id 4221). Full original content reconstructed verbatim.

Replace the dormant **Browser** tab in the header with a two-pane file
explorer that opens the materialized research folder for the currently
selected taxon and renders any supported file inline. The visual
language matches the Stitch `File Explorer & Viewer` screen, and the
file source is the existing `./Research/{taxon_path}/...` tree already
produced by the `materialize` feature — no new on-disk layout, no new
taxonomy schema, no duplication of the path-sanitization logic.

## Scope

- Two-column layout: left `w-72` recursive folder tree, right
  multi-format viewer with `Raw` / `Table` / `Tree` tabs.
- File source: `./Research/{sanitized_root_to_taxon_path}/...`,
  computed by reusing `_build_segments()` and `_sanitize_segment()`
  from `api/server.py`.
- Supported file formats (all 9):
  - `pdf` — rendered via `<iframe>` or native `<embed>`.
  - `html` — rendered via `<iframe sandbox>`.
  - `txt`, `md` — rendered as fenced `<pre>` text (UTF-8 assumed).
  - `doc`, `docx` — `mammoth.js` (CDN) → HTML for `.docx`,
    plain-text fallback for legacy `.doc`.
  - `xls`, `xlsx` — `SheetJS` (CDN) → HTML table in the right pane.
  - `epub` — `epub.js` (CDN) → paginated viewer.
- Double-click on a file row → load + render in the right pane.
  Single-click → select (highlight) without opening.
- Single-click on a folder row → expand / collapse its children.
- Selection state (left highlight) and open file state persist while
  staying on the Browser tab; clearing the taxon clears both.
- Header, footer, and the rest of the app remain untouched.
- Activates via the existing **Browser** tab in `<header>` (currently a
  placeholder). If `state.selected` is null, show a non-blocking
  placeholder ("Select a taxon to browse its files").
- New `GET /api/taxon/{id}/files` endpoint returns the directory tree
  rooted at the taxon's research folder (JSON, lazy-loaded children).
- New `GET /api/files/{rel_path:path}` endpoint streams a single file
  with a `Content-Type` matched by extension and `Content-Disposition:
  inline` so `<iframe>`/`<embed>` can consume it directly.
  *(Note: shipped as taxon-scoped `GET /api/taxon/{id}/files/serve?path=<rel>` per spec — see design §3 / archive-report for reconciliation.)*
- Strict-TDD tests for both endpoints under
  `tests/test_api_file_explorer.py`.

## Out of scope

- File **upload**, **edit**, **rename**, **move**, or **delete**.
- **Drag-and-drop** of files (local or into the tree).
- **Mobile / responsive** layout (desktop-first; below `lg` we keep the
  current single-column placeholder, not this explorer).
- **Download** / **share** / **more_vert** actions in the breadcrumb
  bar — buttons render with hover affordance, but no functionality.
- **Search / filter** inside the explorer tree.
- **Multi-select** of files or folders.
- **Syntax highlighting** inside `Table` and `Tree` tabs (the JSON
  viewer with macOS chrome + line numbers ships; full Prism-style
  highlighting is later refinement).
- **Persistence** of "last opened file" across reloads.
- Changes to `./Research/` layout, materialize behavior, or the
  taxonomy schema.
- New dependencies in `requirements.txt` — libraries are CDN-loaded on
  the client only.

## Affected areas

| File | What changes |
| --- | --- |
| `api/server.py` | Add `GET /api/taxon/{id}/files` (recursive tree JSON, reusing `_build_segments()` + `_sanitize_segment()`); add `GET /api/files/{rel_path:path}` (file streaming with content-type sniffing + traversal guard). |
| `web/index.html` | Add `<script>` tags for `mammoth.js`, `SheetJS`, `epub.js` from a pinned CDN URL. No new CSS. |
| `web/file_explorer.js` *(new)* | Owns left tree render, right viewer render, double-click / single-click handlers, tab switching, format dispatch (pdf/epub/docx/xls/...). |
| `web/nav.js` | When the user clicks the `Browser` header tab, mount `file_explorer` into `<main>` instead of the current placeholder. Pass `state.selected` as the root taxon. |
| `web/app.js` | Export the mount/clear hooks the new module needs; no other changes. |
| `web/state.js` | Add `state.explorer = { rootTaxonId, tree, openFilePath, openFileFormat, viewerTab }`. |
| `tests/test_api_file_explorer.py` *(new)* | FastAPI `TestClient` tests for both endpoints: happy path, path traversal (`../`), unknown taxon, unsupported extension, missing file, large file (range/streaming). |
| `openspec/CHANGELOG.md` | One line under the unreleased section noting the new endpoints. |

## Acceptance criteria

1. Clicking **Browser** in the header while `state.selected !== null`
   renders the explorer with the left column rooted at the selected
   taxon's research folder.
2. Clicking **Browser** with `state.selected === null` renders a
   placeholder ("Select a taxon to browse its files") and makes no API
   calls.
3. The left tree is recursive: clicking a folder toggles its children,
   a vertical guide line connects siblings, and the open path stays
   expanded while the user navigates.
4. Selecting a folder paints `bg-primary/5` + `border-l-2 border-primary`
   - `folder_open` icon; selecting a file paints
   `bg-primary-fixed text-on-primary-fixed rounded-r-md`.
5. Single-click on a file **only** highlights it; **no** network
   request, **no** viewer update.
6. Double-click on a `.pdf`, `.html`, `.epub`, `.txt`, `.md`, `.doc`,
   `.docx`, `.xls`, or `.xlsx` file loads it into the right viewer
   via `GET /api/files/...` and renders it in the matching format.
7. The right viewer shows `Raw` / `Table` / `Tree` tabs and a meta
   strip (`FORMAT | SIZE | ENCODING`); the active tab uses
   `bg-surface-container-lowest shadow-sm`, inactive tabs are flat.
8. JSON / text files render inside the framed `pre` panel with macOS
   window dots (red, amber, green) and a `Copy snippet` affordance on
   the panel header.
9. `GET /api/taxon/{id}/files` returns 404 when the taxon has no
   materialized folder on disk; the frontend shows an empty-state
   message ("No files yet — materialize this taxon to create its
   folder.").
10. `GET /api/files/{rel_path:path}` returns 404 for any path that
    escapes the taxon's sanitized root, including `..`, absolute paths,
    and symlinks that resolve outside the root.
11. `GET /api/files/{rel_path:path}` returns `Content-Type` matched by
    extension (`application/pdf`, `text/html`, `text/markdown`, etc.)
    and `Content-Disposition: inline` so embedded viewers do not
    trigger downloads.
12. The existing test suite stays green: `make test` reports
    `63 + N passed, 8 skipped` (no regressions in `tests/` or
    `etl/tests/`).
13. The new tests cover at minimum: tree endpoint happy-path, tree
    endpoint 404 (no folder), file endpoint happy-path for one
    extension per supported format, path traversal blocked, unknown
    taxon 404, unsupported extension 415.

## Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Path traversal via crafted `rel_path` (`../`, encoded slashes, symlinks). | Compute the resolved absolute path, then assert `RESEARCH_DIR` is its strict parent. Reject otherwise with 400. |
| Large files exhaust memory in the streaming endpoint. | Stream with `FileResponse` from FastAPI / Starlette (chunked, no full read into memory). Add a max-size guard (e.g. 100 MB) → 413 above the cap. |
| CDN libraries fail to load (offline, blocked, CDN down). | Render a fallback banner ("Viewer offline — raw download unavailable") and keep the tree interactive. No crash, no silent corruption. |
| DOCX / XLS / EPUB rendering produces inconsistent output across browsers. | Pin a single version per library; document the pinned URL in `web/index.html` as a code comment; smoke-test on the same browser Chromium ships. |
| Tree expansion triggers N+1 API calls on deep folders. | Server returns the full subtree for a taxon in one response (recursive walk; depth cap mirrors `_MAX_PARENT_DEPTH`); no lazy children on disk. |
| The `Browser` tab previously had no behavior; users may not expect it to mount a new module. | Mount only on click; show the placeholder when no taxon is selected so the first interaction is explainable. |
| Strict-TDD requires failing tests first; new ES module needs no test framework. | Backend tests cover both endpoints under `tests/`. Frontend behavior is verified manually + via the existing `make smoke` API smoke (extend with one explorer endpoint). No new JS test runner. |

## Rollback plan

Revert the change at the commit boundary: drop the two new endpoints
from `api/server.py`, delete `web/file_explorer.js`, restore the
`<main>` placeholder branch in `web/nav.js`, remove the three CDN
`<script>` tags from `web/index.html`, and delete
`tests/test_api_file_explorer.py`. Because the explorer only mounts
when the user explicitly clicks the **Browser** tab, no prior
workflow is altered and no data is mutated on disk. A `git revert` of
the merge commit is sufficient.

## Success criteria

- A user selects any materialized taxon, clicks **Browser**, and
  within ~200 ms sees the folder tree rooted at that taxon's
  research folder.
- Double-clicking any of the nine supported file types renders
  readable content inline; double-clicking an unsupported type shows
  a "format not supported in viewer" toast and offers a download
  link.
- Selecting a taxon whose research folder does not exist yet shows
  the empty-state message and does not raise a console error.
- `make test` is green; `make smoke` continues to pass against the
  live API on port 8765.

## Open questions

None. All product decisions are resolved by the orchestrator
(taxonomic tree reuses `_build_segments()`; formats pinned to
`pdf, epub, html, doc, docx, md, xls, txt`; libraries pinned via CDN;
visual target is the Stitch `File Explorer & Viewer` screen; trigger
is the existing **Browser** header tab).
