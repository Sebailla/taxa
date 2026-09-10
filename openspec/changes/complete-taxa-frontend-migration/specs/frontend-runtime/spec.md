# Frontend Runtime Specification

> Domain: `frontend-runtime`. New domain. Authored under
> `complete-taxa-frontend-migration`. The canonical home is the change
> folder; archive copies this file verbatim into
> `openspec/specs/frontend-runtime/spec.md` at activation.

## Purpose

The single-screen Taxa UI renders as a Next.js 16 (App Router)
+ React 19 application that is **statically exported** to `out/`
and served by FastAPI's existing `StaticFiles` mount at the sole
origin `127.0.0.1:8765`. There is no SSR, no Next.js route handler,
no server component, and no second dev-server port. The contract
preserved against the legacy vanilla build is **total-app functional
parity** across every user flow, every ARIA / keyboard surface, every
state key, and every `data-*` attribute.

The runtime MUST preserve all legacy UI surfaces (header tabs, tree,
breadcrumb, detail panel, file explorer, file viewer, dialogs,
banners, settings, help) without visible regression against the
playwright chromium fixture the predecessor captured.

## Requirements

### Requirement: Single origin served by FastAPI

The system MUST serve the production frontend from the FastAPI
process on `127.0.0.1:8765`, with no second origin, no second
dev-server port, and no extension manifest change.

#### Scenario: `make api` boots FastAPI and serves the static export

- GIVEN `out/index.html` exists and is a non-empty file produced by
  `next build`
- WHEN the user runs `make api`
- THEN uvicorn binds `127.0.0.1:8765`
- AND `GET /` returns `200` with the contents of `out/index.html`
- AND `GET /index.html` returns `200` with the same content
- AND no listener is opened on any other port

#### Scenario: Static asset requests succeed

- GIVEN the static export produced JS chunks, CSS chunks, fonts, and
  image assets under `out/_next/static/**`
- WHEN the browser follows the relative references from `out/index.html`
- THEN every referenced `_next/static/**` URL returns `200`
- AND the response's `Content-Type` matches the file extension

#### Scenario: SPA fallback for deep links

- GIVEN FastAPI's `StaticFiles(directory=str(WEB_DIR), html=True)`
  is the sole mount
- WHEN the user navigates directly to a deep path (e.g. `/taxon/123`)
- THEN FastAPI's `html=True` fallback returns `out/index.html`
- AND the client-side router inside the SPA decides the final route
- AND no second fallback mechanism is introduced

### Requirement: Static export under FastAPI

The system MUST produce the production frontend via `next build` to
the `out/` directory; FastAPI MUST serve that directory via its
existing `StaticFiles` mount.

#### Scenario: `next build` produces `out/`

- GIVEN `package.json` pins `next@^16`, `react@^19`, `react-dom@^19`,
  and `engines.node >= 20.9.0`
- AND `next.config.mjs` declares `output: "export"` plus
  `images: { unoptimized: true }` and `trailingSlash: false`
- WHEN the apply worker runs `next build`
- THEN `next build` exits `0`
- AND the directory `out/` exists
- AND `out/index.html` is non-empty
- AND `<candidate>/out/.next/build-manifest.json` is staged (atomic)
  from `<candidate>/.next/build-manifest.json`
- AND `<candidate>/out/.next/app-build-manifest.json`, if present, is
  staged atomically; its absence is recorded as `not_emitted` and
  is **never** a missing-class failure

#### Scenario: Asset classes present

- GIVEN `next build` succeeded
- WHEN `scripts/verify_build.py` classifies `out/`
- THEN `application_route_html` has exactly one entry — `out/index.html`
- AND `js_class` has at least one non-empty `*.js` file anywhere
  under `out/_next/static/chunks/**`
- AND `css_class` has at least one non-empty `*.css` file anywhere
  under `out/_next/static/chunks/**` (CSS co-located with JS chunks;
  no `_next/static/css/` directory is required)
- AND `staged_manifest` lists the staged `build-manifest.json`
- AND `404.html` / `500.html`, if present, are reported under the
  separate `error_pages` asset class; their absence is **never** a
  missing-class failure for the application-route contract
- AND `missing_classes` is empty

#### Scenario: Build failure never silently falls back

- GIVEN `next build` exits non-zero (Node version below `20.9.0`,
  missing dependency, missing entry, etc.)
- WHEN `make api` is invoked
- THEN the Makefile target exits non-zero **before** uvicorn binds
  the port
- AND `out/BUILD-INVENTORY.json` is **not** emitted
- AND the legacy vanilla files are reachable only via an explicit
  `git revert <cutover-sha>`, never via a quiet degraded mode

### Requirement: All legacy UI surfaces render

The system MUST render every legacy UI surface that the vanilla build
ships today, with the same visual affordances, the same ARIA
semantics, the same keyboard handlers, and the same `data-*`
attribute contract.

#### Scenario: Header tabs

- GIVEN the user lands on `/`
- WHEN the header renders
- THEN the three named tabs — **Browser**, **Classification**,
  **Settings** — render in the same order as the legacy build
- AND each tab carries the legacy `data-action="nav-tab"` and
  `data-path="<tab>"` attributes
- AND the active tab uses the legacy active-tab styling
  (`bg-surface-container-lowest shadow-sm`)

#### Scenario: Tree rendering

- GIVEN a top-level domain is loaded via `GET /api/domains`
- WHEN the user clicks a domain row
- THEN `GET /api/taxon/{id}/children?source=col` (default) is fired
- AND the recursive tree renders with the legacy row layout
  (per-row kebab, per-row search icon, per-row materialize
  indicator)
- AND the `tree-source` toggle (`col` ↔ `worms`) re-renders the
  tree with the matching source

#### Scenario: Breadcrumb rendering

- GIVEN a taxon is selected (`state.selected !== null`)
- WHEN the breadcrumb renders
- THEN the breadcrumb walks the parent chain via
  `GET /api/taxon/{id}` for each ancestor
- AND the breadcrumb links navigate the focused position
- AND the breadcrumb uses the legacy monospace family for the
  scientific-name segments

#### Scenario: Detail panel tab strip

- GIVEN a taxon is selected
- WHEN the user opens the detail panel
- THEN the tab strip renders in the legacy order — **Búsquedas**,
  **Carpeta**, **Vernáculares**, **Sinónimos**, **Distribución**
- AND **Búsquedas** is the default tab on a fresh selection
- AND explicit tab clicks persist via `state.activeTab[taxonId]`
- AND the active tab uses the legacy active-tab styling
- AND the Search tab groups engines under the legacy category
  headers (`general`, `taxonomic`, `academic`, `multimedia`,
  `documents`) per `CATEGORIES` in the search-engines literal

#### Scenario: Per-row search and materialize indicators

- GIVEN the user expands a tier group
- WHEN each child row renders
- THEN the per-row search icon selects the taxon and opens the
  **Búsquedas** tab
- AND the per-row materialize indicator is saturated green when
  `state.materialized` contains the row's id
- AND the materialize indicator fades / unsaturates otherwise

#### Scenario: Settings view

- GIVEN the user clicks the **Settings** tab
- WHEN the settings view mounts
- THEN the theme toggle (light / dark) persists to
  `localStorage.taxa.settings.theme` via the new typed store
- AND the toggle stamps `data-theme` on `<html>` so the CSS
  variables re-resolve
- AND the OS `prefers-color-scheme` media query is honoured as
  the default when no stored preference exists
- AND the **Reset tree pane width** control clears
  `localStorage.taxa.fex.treeWidth` and asks the file explorer to
  re-render with the CSS default (30 %)

#### Scenario: Help view

- GIVEN the user clicks the `?` header tab
- WHEN the help view mounts
- THEN the help shell renders the legacy keyboard-shortcut table
- AND clicking a nav tab (`Classification`, `Settings`, `Browser`)
  drops the help shell out of `<main>`

#### Scenario: Banners

- GIVEN any banner condition from the legacy build fires (offline,
  server 5xx, materialize failure, save-url failure)
- WHEN the banner renders
- THEN the banner text and the dismiss control match the legacy
  build line-for-line
- AND the banner data attributes (`data-banner`, `data-banner-kind`)
  are preserved

### Requirement: File explorer parity

The system MUST render the file explorer inside the **Browser** tab
with the same two-pane layout, the same single-click vs
double-click semantics, the same Raw / Table / Tree tab strip, and
the same CDN-library lazy loading as the legacy build.

#### Scenario: Browser tab mounts the file explorer

- GIVEN a taxon is selected
- WHEN the user clicks the **Browser** tab
- THEN `GET /api/taxon/{selected}/files` is fired
- AND the left pane (`w-72`) renders the recursive folder tree
- AND the right pane renders the empty-viewer placeholder
- AND the meta strip shows the empty state until a file opens

#### Scenario: Single-click vs double-click on a file

- GIVEN a file row in the left tree
- WHEN the user single-clicks it
- THEN the row highlights with `bg-primary-fixed` +
  `text-on-primary-fixed` + `rounded-r-md`
- AND no network request fires
- AND the right viewer state is unchanged
- WHEN the user double-clicks the same row
- THEN the viewer fetches the file via
  `GET /api/taxon/{id}/files/serve?path=<rel>`
- AND the viewer renders the file in the matching format
- AND the file row remains highlighted

#### Scenario: Single-click on a folder

- GIVEN a folder row in the left tree
- WHEN the user single-clicks it
- THEN the folder row highlights with `bg-primary/5` +
  `border-l-2 border-primary` + the `folder_open` icon
- AND the folder toggles its children visibility
- AND a 1 px outline-variant/20 vertical guide connects the
  folder's children visually

#### Scenario: Raw / Table / Tree tab strip

- GIVEN the user has double-clicked `data.csv`
- WHEN they click the **Table** tab
- THEN the right viewer re-renders the file via Papa Parse with a
  sticky `<thead>` and a scrollable body
- AND the **Table** tab is the active tab in the tab strip
- AND the **Tree** tab is **not** auto-activated
- AND the meta strip shows `FORMAT=CSV | SIZE=<bytes>`

#### Scenario: JSON Tree tab

- GIVEN the user has double-clicked `spec.json`
- WHEN they click the **Tree** tab
- THEN the root object appears as a clickable caret node
- AND clicking the caret expands children with 16 px indent per
  nesting level
- AND leaf values are type-coloured using the Tailwind config
  tokens (no hardcoded hex)

#### Scenario: Multi-format file rendering

- GIVEN a `.pdf`, `.html`, `.txt`, `.md`, `.docx`, `.xls`, `.xlsx`,
  or `.epub` file in the tree
- WHEN the user double-clicks it
- THEN the matching legacy renderer dispatches — PDF → iframe,
  HTML → sandboxed iframe (`sandbox=""`, no `allow-same-origin`),
  TXT / MD → fenced `<pre>` (MD via `marked.min.js`), DOCX → mammoth
  (`mammoth.js@1.8.0`), XLS/XLSX → SheetJS (`xlsx@0.18.5`) with a
  sheet picker for multi-sheet workbooks, EPUB → epubjs
  (`epubjs@0.3.93`) with prev/next page controls
- AND the meta strip shows the matching `FORMAT=<EXT> | SIZE=<bytes> |
  ENCODING=UTF-8`
- AND CDN libraries load lazily via `loadScriptOnce(name, src)` so
  the user never pays the ~600 KB download cost for unused formats

#### Scenario: Legacy DOC fallback

- GIVEN a `.doc` file
- WHEN the user double-clicks it
- THEN the viewer shows `"Legacy .doc cannot be rendered inline.
  <Download file>"` with a `<a href="<serve-url>" download>` link
- AND the meta strip shows `FORMAT=DOC`

#### Scenario: Unsupported format fallback

- GIVEN a file with extension outside the nine supported formats
- WHEN the user double-clicks it
- THEN the viewer shows `"Format not supported in viewer."` with a
  download link
- AND the underlying `GET /files/serve` returns
  `Content-Type: application/octet-stream` with
  `Content-Disposition: inline; filename="<basename>"`

#### Scenario: CDN failure fallback

- GIVEN any of the pinned CDN libraries fails to load
- WHEN the user double-clicks a file that requires that library
- THEN the viewer renders the banner
  `"Viewer offline — raw download unavailable"` and keeps the tree
  interactive
- AND no uncaught exception is raised

#### Scenario: Tree search

- GIVEN the tree is mounted
- WHEN the user types in the left-tree search input
- THEN the input is debounced by 200 ms
- AND filter mode hides non-matching rows
- AND any folder whose subtree contains a match is auto-expanded
- AND highlight mode keeps expand/collapse state and paints matching
  rows with `.fex-row.search-match`
- AND `state.explorer.search.{query, mode, hideEmpty}` is updated

#### Scenario: Switching taxon clears the explorer state

- GIVEN the explorer is mounted showing files for taxon A
- WHEN the user selects taxon B in the taxonomy tree
- THEN `state.explorer` is cleared: `rootTaxonId = null`,
  `tree = null`, `openFilePath = null`, `openFileFormat = null`,
  `viewerTab = "Raw"`
- AND re-opening the **Browser** tab triggers a fresh
  `GET /api/taxon/{B}/files` request

### Requirement: Total-app functional parity

The system MUST preserve every user flow the legacy build supports
without visible regression.

#### Scenario: Browse flow

- GIVEN the user opens the application at `/`
- WHEN the user expands a domain → a sub-tree → a species row
- THEN the breadcrumb updates, the detail panel loads, and the
  selected taxon's metadata is rendered
- AND the URL is updated to `<root>/<taxon>` matching the legacy
  build's URL shape

#### Scenario: Search flow

- GIVEN the user opens the search modal (header search icon)
- WHEN they type a query
- THEN `GET /api/search?q=<q>` is debounced and fired
- AND results from all three sources (`col`, `worms`,
  `freshwater`) appear in the legacy result grouping

#### Scenario: Materialize flow

- GIVEN a taxon has no materialised folder on disk
- WHEN the user confirms the materialize modal
- THEN `POST /api/taxon/{id}/materialize` is fired
- AND the modal callback merges the returned ids into
  `state.materialized`
- AND the per-row materialize indicator turns saturated green for
  the new ids and their visible descendants

#### Scenario: Save URL flow

- GIVEN the Chrome extension POSTs `{url, suggested_filename}` to
  `/api/taxon/{id}/save-url`
- WHEN the request is processed
- THEN the response body is written to the materialised research
  folder
- AND the SSRF defence (`_PRIVATE_NETS` rejection, allowlist on
  `_SAVE_URL_ALLOWED_TYPES`, 50 MB byte cap, 30 s connect /
  60 s read timeouts) is unchanged
- AND the extension receives a 2xx response that the React-aware
  rendering layer can re-render without code changes

### Requirement: Accessibility parity

The system MUST preserve every ARIA role, label, and keyboard
handler from the legacy build, with no new axe violations.

#### Scenario: Keyboard handlers

- GIVEN the user uses the legacy keyboard shortcuts
  (e.g. `/` to open search, `Esc` to close modals, arrow keys in the
  tree, `Enter` to open the focused file)
- WHEN they trigger the shortcut
- THEN the matching legacy behaviour fires
- AND focus management matches the legacy build (focus trap inside
  modals, focus restore on close, skip-link for the tree)

#### Scenario: ARIA semantics

- GIVEN any interactive element from the legacy build
- WHEN the screen reader or axe inspects it
- THEN the element carries the same `role`, `aria-label`,
  `aria-controls`, `aria-expanded`, `aria-selected`, `aria-current`
  attributes as the legacy build

#### Scenario: Axe scan

- GIVEN the new frontend is fully mounted
- WHEN the axe scan runs against the chromium fixture
- THEN the count of `serious` / `critical` violations is **not
  greater than** the legacy baseline
- AND every previously-reported violation either resolves to
  `resolved` or carries a documented exemption

### Requirement: Performance parity

The system MUST NOT regress the initial-paint or interaction-latency
budget on the chromium fixture the predecessor captured.

#### Scenario: Initial paint

- GIVEN the chromium fixture is the same one used by the G4
  Playwright + Lighthouse harness
- WHEN the apply worker measures initial paint against the
  `/api/health` round-trip
- THEN the delta vs. the legacy baseline is `≤ 0 %` per the
  predecessor's success criteria

#### Scenario: Interaction latency

- GIVEN the user interacts with the tree, the detail panel, and the
  file viewer
- WHEN the apply worker measures interaction latency
- THEN the delta vs. the legacy baseline is `≤ 0 %`

#### Scenario: Build profile regression

- GIVEN `next build` has run
- WHEN the apply worker compares `out/BUILD-INVENTORY.json`
  (`chunks`, `total_bytes`, `per_route_bytes`) against the legacy
  evidence baseline
- THEN no metric regresses by more than `0 %` without a documented
  exemption signed off in `design.md`

### Requirement: Browser-state hydration without mismatch

The system MUST hydrate browser-local state without raising
hydration-mismatch warnings.

#### Scenario: First paint under hydration guard

- GIVEN the React tree is mounted for the first time
- WHEN the initial render fires
- THEN the `mounted` flag is `false`
- AND `localStorage` reads are deferred to `useEffect`
- AND the tree structure defaults to the empty state on first paint
- AND no React hydration warning fires in the browser console

#### Scenario: Hydration after first paint

- GIVEN the first paint completed with the empty state
- WHEN `useEffect` runs and reads `localStorage`
- THEN the typed store rehydrates each of the four keys
  (`theme`, `tree-source`, `last-taxon-id`, `kebab-open-id`) via
  one read site per key
- AND a follow-up render applies the rehydrated state
- AND no hydration warning fires

## Notes

- The static export forfeits dynamic routes and image optimisation
  (acceptable for v1; switching to the full Next.js dev server is a
  separate change).
- `next build` MUST run before uvicorn binds the port; the
  `scripts/check-runtime.mjs` runtime check (Node `>= 20.9.0`)
  MUST exit non-zero before uvicorn starts if Node is too old.
- The legacy CDN pin URLs (`mammoth@1.8.0`, `xlsx@0.18.5`,
  `epubjs@0.3.93`) are loaded by the file viewer's lazy loader and
  ship as part of the static export (either via inline
  `<script>` tags in `out/index.html` or via the React component
  tree); whichever path is taken, the URLs MUST remain pinned.