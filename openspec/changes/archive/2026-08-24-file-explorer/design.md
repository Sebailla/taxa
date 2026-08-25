# File Explorer & Viewer — Design

> **Source**: Engram observation `sdd/file-explorer/design` (id 4223). Full original content reconstructed verbatim (838 lines).

## Outcome

Add a two-pane file explorer that mounts in the existing **Browser** tab when the
user selects a taxon. The explorer reads the already-materialized
`./Research/<sanitized root→taxon>/…` tree via two new endpoints and renders any
of the nine supported file formats inline. No new on-disk layout, no schema
changes, no duplication of the path-sanitization logic — the design reuses
`_build_segments()`, `_sanitize_segment()`, and `RESEARCH_DIR` from
`api/server.py` verbatim.

## Quick path

1. Add two endpoints to `api/server.py`: `GET /api/taxon/{id}/files` and
   `GET /api/taxon/{id}/files/serve`.
2. Land `web/file_explorer.js` + `web/file_viewer.js` and wire the Browser
   tab click in `web/nav.js`.
3. Pin three CDN libraries in `web/index.html` (mammoth, SheetJS, epub.js).
4. Verify with `make test` (63 + 12 passing) and a manual browser smoke.

---

## 1. Architecture overview

The change fits the existing app without disturbing it. The tree view in
`<main>` is the only region that needs to be replaced when the user clicks
**Browser**; everything else (header, footer, search, detail panel, breadcrumb)
keeps working unchanged.

```
Browser tab click
  → nav.js routes to mountFileExplorer(state.selected)
  → file_explorer.js renders left tree + empty right viewer
  → GET /api/taxon/{id}/files  (recursive tree JSON)
  → state.explorer.tree populated → re-render left tree
  → user double-clicks file → GET /api/taxon/{id}/files/serve?path=…
  → file_viewer.js dispatches by extension → inline render
```

## 2. Module structure

### New files

| File | Purpose | Approx. lines |
| --- | --- | --- |
| `web/file_explorer.js` | Tree rendering, file selection, single/double-click handlers, mount/clear hooks, empty-state placeholders. Owns `state.explorer` writes. | ~250 |
| `web/file_viewer.js` | Format dispatcher (extension → renderer), CDN lazy loader, meta-strip + Raw/Table/Tree tab strip. | ~250 |
| `tests/test_api_file_explorer.py` | 12 pytest cases against the existing in-memory SQLite + monkeypatch fixture pattern. | ~250 |

### Modified files

| File | Additions / edits |
| --- | --- |
| `api/server.py` | Top-level imports: add `from datetime import datetime`, `from fastapi.responses import FileResponse`. Module-level `_STREAM_CAP_BYTES = 100 * 1024 * 1024` and `_CONTENT_TYPE_BY_EXT` dict. Two endpoints `list_files` + `serve_file` before the StaticFiles mount. One helper `_walk_tree`. |
| `web/index.html` | Three `<script defer>` tags with pinned CDN URLs + inline comments. mammoth@1.8.0, xlsx@0.18.5, epubjs@0.3.93. |
| `web/state.js` | Append `explorer` to `state`. |
| `web/nav.js` | Add `mountFileExplorer(rootTaxonId)` / `clearFileExplorer()` exports + a `data-path` click branch. |
| `web/app.js` | No structural changes. |
| `tests/test_smoke.py` | Add the two new paths to `expected_paths`. |
| `Makefile` | Extend `smoke` with one curl hit. |
| `openspec/CHANGELOG.md` | One line under unreleased. |

## 3. Backend design

### Endpoint 1 — `GET /api/taxon/{taxon_id}/files`

**Purpose.** Return the full recursive tree under the taxon's sanitized
research root in one response. Reuses `_build_segments()` + `_sanitize_segment()`.

**Request:** `GET /api/taxon/{taxon_id}/files` (no query params).

**Response — happy path (200):**

```json
{
  "exists": true,
  "taxon_id": 5413596,
  "taxon_name": "Biota",
  "taxon_path": "Eukaryota/Animalia/Chordata/Mammalia/Homo sapiens",
  "filesystem_path": "/abs/path/to/Research/Eukaryota/Animalia/.../Homo sapiens",
  "root": { "name": "Homo sapiens", "path": "", "type": "folder", "children": [...] }
}
```

**Response — taxon not materialized (200):** `exists: false`, `root: null`.

**Response — unknown taxon (404):** `{ "detail": "taxon {id} not found" }`.

**Safety properties.** No `path` query param — entire path computed from
`taxon_id` server-side. Depth cap mirrors `_MAX_PARENT_DEPTH`. Symlinks
skipped (serve endpoint rejects them anyway). Dotfiles skipped.

### Endpoint 2 — `GET /api/taxon/{taxon_id}/files/serve?path=<rel>`

**Purpose.** Stream a single file with `Content-Type` by extension and
`Content-Disposition: inline` so `<iframe>` / `<embed>` / native PDF viewer
consume it directly.

**Extension → Content-Type table:**

| Extension | Content-Type |
| --- | --- |
| `.pdf` | `application/pdf` |
| `.epub` | `application/epub+zip` |
| `.html`, `.htm` | `text/html` |
| `.md` | `text/markdown` |
| `.txt` | `text/plain` |
| `.doc` | `application/msword` |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.xls` | `application/vnd.ms-excel` |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| (anything else) | `application/octet-stream` |

**Error envelope:**

| Status | `detail` | When |
| --- | --- | --- |
| 400 | `Path escapes research root` | `..`, absolute, or symlink resolves outside root. |
| 404 | `taxon {id} not found` | `_build_segments()` mirrors materialize-preview. |
| 404 | `Research folder not materialized` | Taxon's research root doesn't exist on disk. |
| 404 | `File not found` | Path inside root, file missing. |
| 413 | `File exceeds streaming cap (...)` | File size > 100 MB. |

**Safety properties.** `Path.resolve()` follows symlinks before the
strict-parent check. Cap enforced **before** opening the file
(`stat().st_size` only). `FileResponse` is chunked, memory-bounded.

## 4. Frontend design

### `state.explorer` shape

Appended to `state` in `web/state.js`:

```js
explorer: {
  rootTaxonId: null,    // number | null  — taxon the tree is rooted at
  tree: null,           // object | null  — response from GET /files
  openFilePath: null,   // string | null  — relative path inside tree
  openFileFormat: null, // string | null  — extension (e.g. "pdf")
  viewerTab: "Raw",     // "Raw" | "Table" | "Tree"
}
```

### Mount / clear hooks (nav.js)

```js
function mountFileExplorer(rootTaxonId) {
  // Update header tab active state.
  // Strip classification view from <main>.
  // fileExplorer.mount(main, rootTaxonId);  (import ./file_explorer.js)
  // render();
}

function clearFileExplorer() {
  state.explorer.rootTaxonId = null;
  state.explorer.tree = null;
  state.explorer.openFilePath = null;
  state.explorer.openFileFormat = null;
  state.explorer.viewerTab = "Raw";
  // Restore <main> classification shell.
  // render();
}
```

### `web/file_explorer.js` — public API

```js
export function mount(host, rootTaxonId) { /* ... */ }
export function clear()                 { /* clears DOM listeners */ }
```

### `web/file_viewer.js` — format dispatcher

```js
const VIEWERS = {
  ".pdf":  renderPdf, ".html": renderHtml, ".htm": renderHtml,
  ".txt":  renderText, ".md": renderMarkdown,
  ".docx": renderDocx,  // lazy-loads mammoth
  ".doc":  renderDocFallback,
  ".xls":  renderSheet, ".xlsx": renderSheet,  // lazy-loads xlsx
  ".epub": renderEpub,  // lazy-loads epubjs
};

export async function render(host, ext, serveUrl) {
  const fn = VIEWERS[ext.toLowerCase()] || renderUnsupported;
  await fn(host, serveUrl);
}
```

### CDN library loading strategy

**Decision: lazy, on first use.** Three libraries total ~600 KB; most
sessions only open PDFs or text. Lazy via dynamic `<script>` injection:

```js
const _scriptPromises = {};
function loadScriptOnce(name, src) {
  if (_scriptPromises[name]) return _scriptPromises[name];
  _scriptPromises[name] = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src; s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(s);
  });
  return _scriptPromises[name];
}
```

Failure renders the banner: "Viewer offline — raw download unavailable."

## 5. Styling decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| New design tokens? | **No.** | Reuse existing `primary`, `primary-fixed`, `primary-container`, `surface-container-low`, `surface-container-lowest`, `surface`, `outline-variant`. |
| Where do new classes live? | **Inline via `el()`**, plus a small `<style>` block for `.fex-*` chrome helpers. | Matches existing pattern. |
| Animation | **None.** | Existing app uses instant state changes. |

## 6. Testing strategy

### Backend — `tests/test_api_file_explorer.py`

Follows the `db_client_and_base` fixture pattern from
`tests/test_api_materialize.py`. 12 cases:

1. `test_tree_happy_path_mixed_children`
2. `test_tree_not_materialized_returns_exists_false`
3. `test_tree_unknown_taxon_returns_404`
4. `test_tree_synonym_walks_parents`
5. `test_serve_happy_path_*` (parametrized ×9 formats)
6. `test_serve_path_traversal_dotdot`
7. `test_serve_path_traversal_multi`
8. `test_serve_absolute_path`
9. `test_serve_symlink_escape`
10. `test_serve_file_not_found`
11. `test_serve_research_folder_not_materialized`
12. `test_serve_exceeds_streaming_cap`

### Frontend — NO JS test runner

Manual browser smoke only. Documented checklist:

- Select materialized taxon → Browser → tree renders.
- No taxon → Browser → placeholder only.
- Single-click file → highlight, no fetch.
- Double-click file → viewer loads.
- Double-click each of `.pdf`, `.html`, `.txt`, `.md`, `.docx`, `.doc`, `.xls`/`.xlsx`, `.epub`, unsupported `.zip`.
- Switch to Classification → restores tree view.
- Switch taxon while on Browser → `state.explorer` clears.
- Throttle network to "Offline" → CDN-dependent formats show banner.

## 7. Migration / rollout

- No schema changes. No data migration. `./Research/` layout untouched.
- Backwards compatible. The Browser tab previously had no behavior.
- Rollback: `git revert` the merge commit (documented in proposal).
- No feature flag needed — behavior is opt-in via tab click.

## 8. Risks & open decisions

### Spec-level risks (resolved here)

| Risk | Status | Resolution |
| --- | --- | --- |
| URL mismatch (flat vs taxon-scoped) | **Resolved** | Taxon-scoped `GET /api/taxon/{id}/files[/serve]`. |
| Streaming cap needs confirmation | **Resolved** | `_STREAM_CAP_BYTES = 100 MB` enforced pre-open. |
| CDN pinning reproducibility | **Resolved** | Pinned URLs + inline comment + `loadScriptOnce`. |
| No JS test runner | **Resolved** | Manual smoke + extended `make smoke` + OpenAPI smoke test. |

### New risks

| Risk | Mitigation |
| --- | --- |
| **Large JSON tree** — thousands of files in one folder → multi-MB JSON. | Ship recursive walk in v1. TODO comment for lazy children / pagination as later refinement. |
| **CDN upgrade cadence** — mammoth/xlsx/epubjs release monthly. | Quarterly review process. Pinned URL comment in `web/index.html`. |
| **mammoth.js XSS surface** — `convertToHtml` returns HTML set via `innerHTML`. | mammoth already sanitizes `<script>` etc. Same-origin policy is the broader defense. |
| **EPUB render lifecycle** — opening a new EPUB leaks listeners/DOM. | Module-scoped `ePub` var + `book.destroy()` on clear / new file. |
| **Selection persistence on tab switch** — re-mount may re-fetch. | mount() checks `state.explorer.tree` for current taxon and skips re-fetch. |

### Open product decisions

None. All product decisions are resolved.

## 9. Reference links

| Resource | Location |
| --- | --- |
| Stitch screen | `projects/11955314884511019764/screens/ab45d37bf0d54a7e8cd6256f0d3d9c7a` |
| Stitch HTML reference | `/tmp/file_explorer.html` |
| Stitch screenshot | `/tmp/file_explorer.png` |
| `_build_segments()` | `api/server.py` lines 583–650 |
| `_sanitize_segment()` | `api/server.py` lines 511–560 |
| `_research_path_exists()` | `api/server.py` lines 640–650 |
| `RESEARCH_DIR` constant | `api/server.py` line 47 |
| Test fixture pattern | `tests/test_api_materialize.py::db_client_and_base` |
| OpenAPI path assertion | `tests/test_smoke.py::test_openapi_schema_is_valid_json` |
| Project SDD conventions | `openspec/AGENTS.md` |

## Next step

`sdd-tasks` — break this design into atomic, TDD-ordered implementation units
with budget forecasts for the chained-PR decision.
