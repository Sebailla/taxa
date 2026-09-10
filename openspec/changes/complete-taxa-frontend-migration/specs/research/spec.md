# Delta for Research

> Delta spec against the canonical
> `openspec/specs/research/spec.md` (which captures the file
> explorer + multi-format viewer change). The canonical spec is
> **preserved unchanged** — every requirement and every scenario
> remains binding. This delta captures **only the migration
> contract**: React components consume the same `/api/*` shapes,
> the AC-21 search-engine contract test keeps the same byte shape,
> and the literal's location MAY move under `src/data/`.

## ADDED Requirements

### Requirement: Migration contract — same `/api/*` shapes from React

The system MUST consume every `/api/*` endpoint that the canonical
research spec enumerates from React components (server or client
components) without changing the request shape, the response
shape, the status code, or the headers.

#### Scenario: `/api/taxon/{id}/files` shape unchanged from React

- GIVEN the canonical research spec enumerates the response shape
  of `GET /api/taxon/{id}/files`
- WHEN the React file-explorer component fires the request via
  `fetch('/api/taxon/{id}/files')`
- THEN the response is 200 with the same JSON body shape
  (`{ exists, taxon_id, taxon_name, taxon_path,
  filesystem_path, root: { … } | null }`)
- AND 404 is returned with `detail: "taxon {id} not found"` when
  the taxon is unknown
- AND 200 with `exists: false, root: null` is returned when the
  taxon exists but the research folder is not materialised
- AND the synonym parent-chain walk is reused (`_build_segments()`
  from `api/server.py`)

#### Scenario: `/api/taxon/{id}/files/serve` shape unchanged from React

- GIVEN the canonical research spec enumerates the response shape
  of `GET /api/taxon/{id}/files/serve?path=<rel>`
- WHEN the React file viewer fires the request via
  `fetch('/api/taxon/{id}/files/serve?path=<rel>')`
- THEN the response is 200 with the file body, the matching
  `Content-Type`, and `Content-Disposition: inline`
- AND path traversal (`..`), absolute paths, and symlink escapes
  are rejected with 400 `detail: "Path escapes research root"`
- AND unknown file paths return 404 `detail: "File not found"`
- AND non-materialised taxa return 404 `detail: "Research folder
  not materialized"`
- AND files larger than the 100 MB cap return 413
- AND `Content-Type` matches the canonical extension table

### Requirement: AC-21 search-engine contract test preserved

The system MUST preserve the AC-21 search-engine contract test
byte shape. If the search-engines literal relocates, the test's
`open()` path updates in the same release; the literal's byte
shape (key, label, with_authorship, ordering) is unchanged.

#### Scenario: AC-21 byte-shape parity

- GIVEN `tests/test_smoke.py::test_search_engine_contract`
  (AC-21) parses the search-engines literal as text and asserts
  every `{ key, label, with_authorship }` triple matches
  `api/server.py::_SEARCH_ENGINES` byte-for-byte in the same
  order
- WHEN the apply worker ships the cutover
- THEN AC-21 still passes
- AND if the literal moved from `web/search_urls.js` to
  `src/data/search-engines.js`, AC-21's `open()` path is updated
  in the same release
- AND the literal's byte shape is unchanged (no reformat, no
  reordered entries, no renamed fields)
- AND `api/server.py::_SEARCH_ENGINES` is unchanged
- AND the Search tab in the detail panel still groups engines
  under the legacy `CATEGORIES` headers (`general`, `taxonomic`,
  `academic`, `multimedia`, `documents`)

#### Scenario: Server-side mirror unchanged

- GIVEN `api/server.py::_SEARCH_ENGINES` is the server-side
  source of truth for `/api/taxon/{id}/searches`
- WHEN the apply worker ships the cutover
- THEN the server response (URL templates, `with_authorship`
  flag, ordering) is byte-identical to the legacy response
- AND the frontend never builds URLs locally; URLs always come
  from the server (`urllib.parse.quote_plus`)

### Requirement: Research UI surfaces are React components

The system MUST render every research UI surface (file explorer,
file viewer, tree search, Raw / Table / Tree tab strip, CDN
library lazy loader, meta strip, breadcrumb, error banners) as
React components under the modular-architecture capability
`research`. The React components MUST preserve every visible
behaviour, every ARIA role / label, every keyboard handler, and
every `data-*` attribute the canonical research spec enumerates.

#### Scenario: File explorer tree behaviour from React

- GIVEN the canonical research spec enumerates the
  single-click / double-click semantics, the folder expand /
  collapse semantics, the tree search debounce (200 ms), the
  filter / highlight modes, the switching-taxon-clears-state
  behaviour, and the empty-state messages
- WHEN the React file explorer renders
- THEN every behaviour matches the canonical spec scenario
- AND every `data-*` attribute on the tree rows is preserved
  (`data-file-path`, `data-folder-path`)

#### Scenario: File viewer format dispatch from React

- GIVEN the canonical research spec enumerates the format
  dispatcher (PDF, EPUB, HTML, TXT, MD, DOC, DOCX, XLS, XLSX,
  unsupported fallback, legacy DOC fallback, CDN failure fallback)
- WHEN the React file viewer dispatches the open file's format
- THEN every renderer matches the canonical spec scenario
- AND the CDN URLs (`mammoth@1.8.0`, `xlsx@0.18.5`,
  `epubjs@0.3.93`) are loaded by the React lazy loader (or
  pinned inline in `out/index.html`) and the URLs are pinned

#### Scenario: Save URL flow unchanged from React

- GIVEN the Chrome extension POSTs `{url, suggested_filename}` to
  `/api/taxon/{id}/save-url`
- WHEN the React rendering layer refreshes after the save
- THEN the per-row materialize indicator updates without a page
  reload
- AND the SSRF defence in `api/server.py` (private-nets rejection,
  allowlist, byte cap, timeouts) is unchanged

## Notes

- The canonical `openspec/specs/research/spec.md` is the
  authoritative contract for behaviour, scenarios, and tests.
  This delta does not modify any of its requirements; it adds
  the migration contract that the React-aware rendering layer
  binds to.
- The search-engines literal MAY move from
  `web/search_urls.js` to `src/data/search-engines.js` under the
  `research/infrastructure/` layer (per modular-architecture
  rule 3) — if it does, AC-21's `open()` path updates in the
  same release.
- `web/search_urls.js` is enumerated as a separate ownership
  edge in the predecessor's `design.md::§3.1.2`. Five consumers
  are named: `web/detail.js:24`, `:325`, `:332`,
  `tests/test_smoke.py:77–100` (AC-21), and
  `tests/test_search_categories.py:141`. The cutover updates all
  five atomically.
- The predecessor's `apply-progress.md` §"G3 canonical PASS
  record" records all 26 §3.1 consumers (21 web mount + 5
  search URLs) green against the controlled fixture; the React
  cutover preserves that coverage.