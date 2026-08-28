# Delta Spec — research (file-explorer-search-and-tabs)

> Extends `openspec/specs/research/spec.md`. Archive replaces the
> canonical requirement block listed under `MODIFIED Requirements`
> below and adds the new requirements verbatim.

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Multi-format file viewer

The system MUST render each of the supported file types in the right
viewer when the user double-clicks the file, MUST pin a single CDN URL
per library, and MUST dispatch the **Raw / Table / Tree** tab buttons to
the matching renderer for the open file's format (CSV/TSV → Table,
JSON → Tree, everything else → Raw).

(Previously: tab buttons toggled classes only; only Raw had a renderer —
Table and Tree were dead UI for CSV/JSON.)

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

- GIVEN an `.xls` or `.xlsx` file
- WHEN the user double-clicks it
- THEN the viewer fetches the file as `ArrayBuffer`
- AND parses it with `SheetJS` (pinned CDN URL)
- AND renders the first sheet as an HTML table inside the viewer
- AND for multi-sheet workbooks, a sheet picker is rendered above the table so the user can switch sheets
- AND the meta strip shows `FORMAT=XLS` or `FORMAT=XLSX`

#### Scenario: EPUB rendering

- GIVEN an `.epub` file
- WHEN the user double-clicks it
- THEN the viewer fetches the file as `ArrayBuffer`
- AND renders it with `epub.js` (pinned CDN URL)
- AND the viewer shows prev/next page navigation and the current page content
- AND the meta strip shows `FORMAT=EPUB`

#### Scenario: Unsupported format fallback

- GIVEN a file with extension `.zip`, `.exe`, or any extension outside the supported formats
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

## Notes

- Search persistence is session-scoped only; reloading the page clears
  `state.explorer.search`.
- Type-coloured leaves use Tailwind config tokens (no hardcoded hex).
- Papa Parse CDN URL MUST be pinned to `papaparse@5.4.1` in
  `web/index.html` and documented as an inline comment next to the
  `<script>` tag, matching the existing pinning discipline for
  `mammoth.js`, `SheetJS`, `epub.js`, and `marked.min.js`.
- No new Python deps, no new JS build step, no new entry in
  `requirements.txt`.
- Frontend behaviour is verified via the hand-testable scenarios above
  on a fresh `make smoke` run; no JS test runner is introduced.
