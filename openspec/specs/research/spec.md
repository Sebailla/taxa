# Research Specification

## Purpose

The research subsystem exposes a taxon's materialized on-disk research folder
(`./Research/<sanitized root→taxon>/…`) to the frontend as a recursive
folder tree plus a streaming file endpoint with extension-based content
type sniffing. It lets a user open any of nine supported file formats
(PDF, EPUB, HTML, TXT, MD, DOC, DOCX, XLS, XLSX) inline in a single
right-hand viewer, switch between Raw / Table / Tree tabs for textual
content, and trust the API to reject path traversal and absolute paths
before any byte is read from disk. Path computation reuses
`_build_segments()` + `_sanitize_segment()` from `api/server.py` so the
folder layout is identical to the one `POST /api/taxon/{id}/materialize`
already produces — no new on-disk convention, no new schema, no path
duplication.

## Requirements

### Requirement: Browsable research folder tree per taxon

The system MUST render a recursive folder tree in the left pane of the
existing **Browser** header tab, rooted at the selected taxon's
materialized research folder on disk.

#### Scenario: Selected taxon has a materialized folder

- GIVEN taxon X has been materialized via `POST /api/taxon/{id}/materialize`
- AND the user clicks the **Browser** tab in the header
- WHEN the explorer renders
- THEN the left column (`w-72`) shows the recursive folder tree rooted at `./Research/<sanitized-root-to-X>/`
- AND the right pane shows an empty viewer placeholder
- AND `GET /api/taxon/{id}/files` was fired and returned `exists: true`

#### Scenario: Selected taxon has no materialized folder

- GIVEN taxon X has NOT been materialized
- AND the user clicks the **Browser** tab
- WHEN the explorer renders
- THEN the right viewer shows the empty-state message `"No files yet — materialize this taxon to create its folder."`
- AND `GET /api/taxon/{id}/files` was fired and returned `exists: false`
- AND the left column shows no folder rows (or shows a sibling placeholder)

#### Scenario: No taxon is selected

- GIVEN `state.selected === null`
- AND the user clicks the **Browser** tab
- WHEN the explorer renders
- THEN the explorer shows the placeholder `"Select a taxon to browse its files."`
- AND no API calls are fired
- AND the left column and right viewer both show the same placeholder

### Requirement: Recursive directory listing endpoint

The system MUST expose `GET /api/taxon/{taxon_id}/files` that returns
the full tree rooted at the taxon's research folder in one response
(no lazy children, no N+1 round trips).

#### Scenario: Happy path — materialized taxon with mixed children

- GIVEN taxon X is materialized
- AND `./Research/<sanitized-path>/` exists and contains at least one folder and one file
- WHEN the client calls `GET /api/taxon/{taxon_id}/files`
- THEN the response is 200 with JSON body
  `{ exists, taxon_id, taxon_name, taxon_path, filesystem_path, root: { name, path, type: "folder", children: [...] } }`
- AND each file child carries `{ name, path, type: "file", extension, size, modified }`
- AND each folder child carries `{ name, path, type: "folder", children: [...] }`
- AND at each level folders appear before files, both sorted alphabetically case-insensitive
- AND the recursive walk respects `_MAX_PARENT_DEPTH` (50) — see `api/server.py`

#### Scenario: Taxon does not exist in the database

- GIVEN `taxon_id` has no row in the `taxon` table
- WHEN the client calls `GET /api/taxon/{taxon_id}/files`
- THEN the response is 404 with `detail: "taxon {id} not found"`

#### Scenario: Taxon is not materialized

- GIVEN taxon X exists but `./Research/<sanitized-path>/` does NOT exist on disk
- WHEN the client calls `GET /api/taxon/{taxon_id}/files`
- THEN the response is 200 with `{ exists: false, taxon_id, taxon_name, taxon_path, filesystem_path, root: null }`
- AND the response is **not** 404 — the taxon exists; only the folder is missing

#### Scenario: Synonym taxon resolves through parent chain

- GIVEN taxon X is a synonym with `path = NULL`
- WHEN the client calls `GET /api/taxon/{taxon_id}/files`
- THEN the server reuses `_build_segments()` to walk `parent_id` up to the root
- AND the response `taxon_path` reflects the walked sanitized segments, not `null`

### Requirement: Path-traversal-safe file streaming endpoint

The system MUST expose `GET /api/taxon/{taxon_id}/files/serve?path=<rel>`
that streams a single file with a `Content-Type` matched by extension
and a `Content-Disposition: inline` header so embedded viewers
(`<iframe>`, `<embed>`) consume it directly without triggering a
download.

#### Scenario: Happy path

- GIVEN a file exists at `./Research/<sanitized-path>/<rel>`
- WHEN the client calls `GET /api/taxon/{taxon_id}/files/serve?path=<rel>`
- THEN the response is 200 with the file body
- AND `Content-Type` matches the extension table below
- AND `Content-Disposition: inline; filename="<basename>"`

#### Scenario: Content-Type by extension

| Extension | Content-Type |
| --- | --- |
| pdf | application/pdf |
| epub | application/epub+zip |
| html, htm | text/html |
| md | text/markdown |
| txt | text/plain |
| doc | application/msword |
| docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document |
| xls | application/vnd.ms-excel |
| xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| (any other extension) | application/octet-stream |

#### Scenario: Path traversal blocked (`..`)

- GIVEN the client calls the endpoint with `path="../../etc/passwd"`
- WHEN the server resolves the absolute path
- THEN the response is 400 with `detail: "Path escapes research root"`
- AND no file bytes are returned

#### Scenario: Absolute path blocked

- GIVEN the client calls the endpoint with `path="/etc/passwd"`
- WHEN the server resolves the absolute path
- THEN the response is 400 with `detail: "Path escapes research root"`
- AND no file bytes are returned

#### Scenario: Symlink escape blocked

- GIVEN a symlink inside the taxon's research root resolves to a path outside `./Research/<sanitized-path>/`
- WHEN the server calls `Path.resolve()` on the joined candidate path
- THEN the response is 400 with `detail: "Path escapes research root"`
- AND no file bytes are returned

#### Scenario: File not found inside root

- GIVEN the client calls the endpoint with a path that resolves inside the taxon's research root but does not exist
- WHEN the server checks existence
- THEN the response is 404 with `detail: "File not found"`

#### Scenario: Taxon not materialized

- GIVEN taxon X has no research folder on disk
- WHEN the client calls the endpoint
- THEN the response is 404 with `detail: "Research folder not materialized"`

#### Scenario: File exceeds streaming cap

- GIVEN a candidate file larger than the configured cap (default 100 MB)
- WHEN the server inspects file size before streaming
- THEN the response is 413 with a detail naming the cap and the actual size

#### Scenario: Response is streamed, not buffered

- GIVEN any successful file response
- WHEN the server returns the body
- THEN the response uses `FileResponse` (chunked transfer) so memory usage is bounded
- AND no `Content-Length` is forced for files larger than the cap

### Requirement: Multi-format file viewer

The system MUST render each of the nine supported file types in the
right viewer when the user double-clicks the file, MUST pin a single
CDN URL per library, and MUST dispatch the **Raw / Table / Tree** tab
buttons to the matching renderer for the open file's format (CSV/TSV →
Table, JSON → Tree, everything else → Raw).

#### Scenario: PDF rendering

- GIVEN a `.pdf` file in the tree
- WHEN the user double-clicks it
- THEN the right viewer fetches the file via `GET /api/taxon/{id}/files/serve`
- AND renders it inside an `<iframe>` or `<embed>` tag with the matching `Content-Type`
- AND the meta strip shows `FORMAT=PDF | SIZE=<bytes> | ENCODING=UTF-8`

#### Scenario: HTML rendering

- GIVEN an `.html` or `.htm` file
- WHEN the user double-clicks it
- THEN the viewer renders the file inside a sandboxed `<iframe>` (`sandbox` attribute set, no `allow-same-origin`)
- AND the meta strip shows `FORMAT=HTML`

#### Scenario: Plain-text rendering

- GIVEN a `.txt` file
- WHEN the user double-clicks it
- THEN the viewer fetches the file as `text/plain` via `fetch()`
- AND renders the body inside a fenced `<pre>` block with the project's monospace family (`JetBrains Mono`)
- AND the meta strip shows `FORMAT=TXT`

#### Scenario: Markdown rendering

- GIVEN a `.md` file
- WHEN the user double-clicks it
- THEN the viewer fetches the file as text
- AND renders the markdown as HTML using `marked.min.js` (pinned CDN URL — declared in `web/index.html`)
- AND the meta strip shows `FORMAT=MD`

#### Scenario: DOCX rendering

- GIVEN a `.docx` file
- WHEN the user double-clicks it
- THEN the viewer fetches the file as `ArrayBuffer`
- AND passes it to `mammoth.js` (pinned CDN URL) for conversion to HTML
- AND renders the resulting HTML inside a styled `<article>` in the right viewer
- AND the meta strip shows `FORMAT=DOCX`

#### Scenario: Legacy DOC fallback

- GIVEN a `.doc` file (legacy binary format)
- WHEN the user double-clicks it
- THEN the viewer shows the fallback message `"Legacy .doc cannot be rendered inline. <Download file>"`
- AND the download link is `<a href="<serve-url>" download>`
- AND the meta strip shows `FORMAT=DOC`

#### Scenario: XLS / XLSX rendering

- GIVEN a `.xls` or `.xlsx` file
- WHEN the user double-clicks it
- THEN the viewer fetches the file as `ArrayBuffer`
- AND parses it with `SheetJS` (pinned CDN URL)
- AND renders the first sheet as an HTML table inside the viewer
- AND for multi-sheet workbooks, a sheet picker is rendered above the table so the user can switch sheets
- AND the meta strip shows `FORMAT=XLS` or `FORMAT=XLSX`

#### Scenario: EPUB rendering

- GIVEN a `.epub` file
- WHEN the user double-clicks it
- THEN the viewer fetches the file as `ArrayBuffer`
- AND renders it with `epub.js` (pinned CDN URL)
- AND the viewer shows prev/next page navigation and the current page content
- AND the meta strip shows `FORMAT=EPUB`

#### Scenario: Unsupported format fallback

- GIVEN a file with extension `.zip`, `.exe`, or any extension outside the nine supported formats
- WHEN the user double-clicks it
- THEN the viewer shows the message `"Format not supported in viewer."` with a download link
- AND the underlying API call returns the file with `Content-Type: application/octet-stream`
- AND `Content-Disposition: inline; filename="<basename>"` is still set so the download link works

#### Scenario: CDN failure fallback

- GIVEN any of the pinned CDN libraries fails to load (offline, blocked, CDN down)
- WHEN the user double-clicks a file that requires that library
- THEN the viewer renders a banner `"Viewer offline — raw download unavailable"` and keeps the tree interactive
- AND no uncaught exception is raised; no silent corruption occurs

#### Scenario: Table tab dispatches to Table renderer for CSV

- GIVEN the user has double-clicked `data.csv`
- WHEN they click the **Table** tab button
- THEN the right viewer re-renders the file via the Table renderer (sticky header + scrollable body)
- AND the Table tab is the active tab in the tab strip
- AND the **Tree** tab is NOT auto-activated

#### Scenario: Tree tab dispatches to Tree renderer for JSON

- GIVEN the user has double-clicked `spec.json`
- WHEN they click the **Tree** tab button
- THEN the right viewer re-renders the file via the Tree renderer (collapsible, indented)
- AND the Tree tab is the active tab in the tab strip
- AND the **Table** tab is NOT auto-activated

#### Scenario: Non-tabular file ignores Table/Tree tabs

- GIVEN the user has double-clicked `notes.md`
- WHEN they click the **Table** or **Tree** tab
- THEN the viewer shows the message `"Table/Tree view not available for this format — use Raw."`
- AND no renderer error is thrown

### Requirement: Tree search

The system MUST expose a search input inside the left tree header that
filters or highlights rows by case-insensitive substring match on a row's
`name` or full `path`. The system MUST debounce input by 200 ms and
persist `{ query, mode, hideEmpty }` in `state.explorer.search`.

#### Scenario: Filter mode hides non-matching rows

- GIVEN the tree has 200 files and folders
- WHEN the user types `acr` in the search input
- THEN within 250 ms the tree shows only rows whose path or basename contains `acr` (case-insensitive)
- AND any folder whose subtree contains a match is auto-expanded

#### Scenario: Filter mode + hide-empty shows "No matches."

- GIVEN filter mode is active and `hideEmpty` is on
- WHEN the user types `foo` and no descendant matches exist
- THEN the tree pane shows the message `"No matches."` in place of an empty space

#### Scenario: Highlight mode keeps expand/collapse state

- GIVEN highlight mode is active
- AND the user manually collapsed folder `X` before typing
- WHEN the user types `something` that matches a descendant of `X`
- THEN folder `X` stays collapsed
- AND every matching row is painted with `.fex-row.search-match`

#### Scenario: Clear restores tree without state churn

- GIVEN the search input has an active query
- WHEN the user clicks the "X" clear button (or empties the field)
- THEN the search input becomes empty
- AND the tree restores to its pre-search render
- AND in highlight mode the user's prior expand/collapse state is preserved

#### Scenario: Toggles persist while keeping the query

- GIVEN a query is active in filter mode
- WHEN the user clicks the mode toggle to switch to highlight
- THEN the query text remains
- AND the mode icon flips to highlight
- AND matching rows are painted (not hidden)

### Requirement: Table viewer tab

The system MUST render CSV / TSV files via Papa Parse when the user
clicks the **Table** tab, with a sticky `<thead>` and a horizontally
and vertically scrollable body.

#### Scenario: CSV opens with sticky header

- GIVEN the user has double-clicked `data.csv`
- WHEN they click the **Table** tab
- THEN the first row is rendered as a sticky `<thead>`
- AND subsequent rows scroll horizontally and vertically
- AND the meta strip still shows `FORMAT=CSV | SIZE=<bytes>`

#### Scenario: TSV uses tab delimiter

- GIVEN the user has double-clicked `data.tsv`
- WHEN they click the **Table** tab
- THEN Papa Parse is invoked with `delimiter: "\t"`
- AND cells render without tab artefacts in the cell content

#### Scenario: CDN load failure falls back to Raw

- GIVEN the Papa Parse CDN `<script>` failed to load
- WHEN the user clicks the **Table** tab on a `.csv` file
- THEN the viewer shows the same offline banner already used by other CDN-failure paths
- AND no uncaught exception is raised

### Requirement: Tree viewer tab

The system MUST render JSON files as a collapsible native tree when the
user clicks the **Tree** tab, with 16 px indent per nesting level and
type-coloured leaves. No CDN is used.

#### Scenario: JSON root expands on click

- GIVEN the user has double-clicked `spec.json`
- WHEN they click the **Tree** tab
- THEN the root object appears as a clickable caret node
- AND clicking the caret expands its children with 16 px indent per level

#### Scenario: Leaf values are type-coloured

- GIVEN a JSON object is expanded in the Tree viewer
- WHEN the renderer paints leaves
- THEN strings, numbers, booleans, and `null` each carry a distinct type token from the Tailwind config (no hardcoded hex)
- AND object / array keys render as `<summary>` rows

#### Scenario: Large JSON is truncated with a hint

- GIVEN a JSON file larger than the configured node cap (50 000)
- WHEN the Tree renderer walks the document
- THEN it stops at the cap and shows `"Tree truncated — open raw"`
- AND the Raw tab still renders the full body

### Requirement: Tree interaction semantics

The explorer MUST distinguish single-click (select + highlight) from
double-click (open / expand) consistently across files and folders.

#### Scenario: Single-click on a file

- GIVEN a file row in the left tree
- WHEN the user single-clicks it
- THEN the file row is highlighted with `bg-primary-fixed` + `text-on-primary-fixed` + `rounded-r-md`
- AND no network request fires
- AND the right viewer state is unchanged

#### Scenario: Double-click on a file

- GIVEN a file row is highlighted
- WHEN the user double-clicks it
- THEN the viewer fetches the file via `GET /api/taxon/{id}/files/serve` and renders it in the matching format
- AND the file row remains highlighted
- AND the right viewer state now reflects the opened file

#### Scenario: Single-click on a folder

- GIVEN a folder row in the left tree
- WHEN the user single-clicks it
- THEN the folder row is highlighted with `bg-primary/5` + `border-l-2 border-primary` + `folder_open` icon
- AND the folder toggles its children visibility (expand if collapsed, collapse if expanded)
- AND a vertical guide line (`1px outline-variant/20` width) connects the folder's children visually

#### Scenario: Switching taxon clears the explorer state

- GIVEN the explorer is mounted and showing files for taxon A
- WHEN the user selects taxon B in the taxonomy tree (left panel)
- THEN `state.explorer` is cleared: `rootTaxonId = null`, `tree = null`, `openFilePath = null`, `openFileFormat = null`, `viewerTab = "raw"`
- AND no stale renders fire after the clear
- AND re-opening the **Browser** tab triggers a fresh `GET /api/taxon/{B}/files` request

### Requirement: Header integration

The existing **Browser** tab in `<header>` MUST mount the file explorer
when clicked, and MUST unmount its subscriptions when the user switches
to **Classification** or **Settings**.

#### Scenario: First Browser click with selected taxon

- GIVEN `state.selected !== null`
- AND the explorer has not been mounted yet for this taxon
- WHEN the user clicks the **Browser** tab
- THEN the explorer mounts into `<main>`, replacing any previous content
- AND `GET /api/taxon/{selected}/files` fires
- AND the explorer shows the recursive tree on the left and an empty viewer on the right

#### Scenario: Browser click with no selected taxon

- GIVEN `state.selected === null`
- WHEN the user clicks the **Browser** tab
- THEN the explorer mounts the placeholder view
- AND no API calls fire

#### Scenario: Switching away from Browser

- GIVEN the explorer is mounted and showing files
- WHEN the user clicks **Classification** or **Settings** in the header
- THEN the explorer's pending API subscriptions / listeners are cleared (no stale renders fire later)
- AND the explorer state persists in `state.explorer` so re-opening the **Browser** tab is instant (no re-fetch when the same taxon is still selected)

#### Scenario: Active tab styling

- GIVEN the explorer is mounted and the viewer is visible
- WHEN any Raw / Table / Tree tab is active
- THEN the active tab uses `bg-surface-container-lowest shadow-sm`
- AND inactive tabs render flat
- AND the meta strip shows `FORMAT | SIZE | ENCODING` aligned to the right of the tab strip

### Requirement: Strict-TDD coverage

Backend tests MUST cover both endpoints and all path-safety edge cases
before implementation lands. Tests are written first (RED), then
implementation makes them pass (GREEN).

#### Scenario: Required test cases for `tests/test_api_file_explorer.py`

- `tests/test_api_file_explorer.py` MUST cover at minimum:
  - `GET /api/taxon/{id}/files` happy path with mixed folders and files (folders before files, case-insensitive sort)
  - `GET /api/taxon/{id}/files` when the research folder does not exist on disk (`exists: false`, status 200)
  - `GET /api/taxon/{id}/files` for an unknown taxon (status 404, detail `"taxon {id} not found"`)
  - `GET /api/taxon/{id}/files` for a synonym taxon (uses parent-chain walk — same path math as `materialize`)
  - `GET /api/taxon/{id}/files/serve` happy path for one extension per supported format (9 formats: pdf, epub, html, txt, md, doc, docx, xls, xlsx)
  - `GET /api/taxon/{id}/files/serve` with `path=".."` — status 400, detail `"Path escapes research root"`
  - `GET /api/taxon/{id}/files/serve` with `path="../../etc/passwd"` — status 400
  - `GET /api/taxon/{id}/files/serve` with absolute path `"/etc/passwd"` — status 400
  - `GET /api/taxon/{id}/files/serve` when the resolved file does not exist — status 404
  - `GET /api/taxon/{id}/files/serve` when the taxon has no research folder — status 404, detail `"Research folder not materialized"`
  - `GET /api/taxon/{id}/files/serve` returns `Content-Type` matched per the extension table
  - `GET /api/taxon/{id}/files/serve` returns `Content-Disposition: inline; filename="<basename>"`

#### Scenario: Tests follow the project fixture pattern

- GIVEN the existing `tests/test_api_materialize.py` fixture pattern (in-memory SQLite + `monkeypatch.setattr("api.server.db", fake_db)` + `monkeypatch.setattr("api.server.RESEARCH_DIR", tmp_path / "Research")`)
- WHEN `tests/test_api_file_explorer.py` is written
- THEN the file MUST follow the same fixture pattern so RESEARCH_DIR never touches the real `./Research`
- AND each test MUST arrange its own fixture files inside `tmp_path` and tear down via the fixture scope

### Requirement: Existing tests unaffected

The change MUST NOT regress the existing 63-pass test baseline, and the
new tests MUST be additive.

#### Scenario: Existing test suite still passes

- GIVEN the file explorer implementation has landed
- WHEN the orchestrator runs `.venv/bin/python3 -m pytest tests/ etl/tests/ -q`
- THEN the result is `"63 + N passed, 8 skipped"` where `N ≥ 12` (≥ 12 new tests for the file explorer — at least the cases enumerated in the prior requirement)
- AND no existing test fails or is removed
- AND no test is moved between files

#### Scenario: Smoke endpoint still healthy

- GIVEN `make smoke` runs the OpenAPI smoke against the live API on port 8765
- WHEN the change is merged
- THEN `make smoke` continues to pass
- AND the smoke MUST be extended to assert that `GET /api/taxon/{id}/files` is listed in the OpenAPI schema

## Notes

- CDN URLs for `mammoth.js`, `SheetJS`, and `epub.js` MUST be pinned to
  specific versions in `web/index.html` and documented as inline code
  comments next to each `<script>` tag — the proposal explicitly bans
  unversioned imports.
- No new Python dependencies; no new entry in `requirements.txt`. All
  client-side libraries are loaded via pinned CDN `<script>` tags only.
- No changes to the `./Research/` on-disk layout, the materialize
  behaviour, or the taxonomy schema. This change reuses
  `_build_segments()` and `_sanitize_segment()` from `api/server.py`
  verbatim.
- `state.explorer` MUST be added to `web/state.js` with the shape
  `{ rootTaxonId, tree, openFilePath, openFileFormat, viewerTab }`. No
  other state fields change.
- `web/nav.js` MUST expose a `mountFileExplorer(rootTaxonId)` and
  `clearFileExplorer()` hook so the new file-explorer module plugs in
  without disturbing the existing click delegation.
- Frontend behaviour is verified manually + via the existing
  `make smoke` API smoke. No new JS test runner is introduced.
