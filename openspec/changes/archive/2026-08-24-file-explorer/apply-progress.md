# Apply Progress — file-explorer

> **Source**: Engram observations `sdd/file-explorer/apply-progress` (id 4225, PR 1) + `sdd/file-explorer/apply-progress-pr2` (id 4228, PR 2). This is a condensed merge of both; the original 277-line file had per-group TDD evidence tables, the test command output, and the attempt budget sections inline.

## PR 1 (backend) — ✅ MERGED as #25

### Status

PR 1 MERGED (`d8bda4b`). PR 2 (frontend) APPLIED, ready for orchestrator merge.

### Key numbers

- 24 new tests added in `tests/test_api_file_explorer.py` (5 tree-shape + 10 parametrized content-type + 9 safety/error paths).
- Test baseline: 63 passed, 8 skipped → 87 passed, 8 skipped (no regressions after PR 2).
- Two new FastAPI endpoints registered:
  - `GET /api/taxon/{taxon_id}/files` — recursive tree JSON (200 with tree / 200 with exists:false / 404 on unknown taxon)
  - `GET /api/taxon/{taxon_id}/files/serve` — streaming file (200 / 400 traversal / 404 missing / 404 not-materialized / 413 over-cap)
- Net ~250 lines added (within 300-line attempt budget).

### Files changed (PR 1)

- `api/server.py`: imports + module-level `_STREAM_CAP_BYTES` and `_CONTENT_TYPE_BY_EXT`; private `_walk_tree` and `_safe_resolve` helpers; two new endpoints.
- `tests/test_api_file_explorer.py`: NEW. Mirrors `test_api_materialize.py` fixture pattern.
- `tests/test_smoke.py`: OpenAPI `expected_paths` extended.
- `Makefile`: `smoke` target extended with curl hit.
- `openspec/changes/file-explorer/tasks.md`: Group 1.x implementation checkboxes → `[x]`. Group 2.x and parent-owned items stay `[ ]` (later all flipped to `[x]`).

### TDD evidence summary (PR 1)

- **RED gate**: 23/24 tests fail with 404 / connection errors. The 1 trivial-green was FastAPI's default 404 body incidentally matching the assertion — became a real GREEN after implementation.
- **GREEN gate**: 24/24 file-explorer tests pass in 0.21s.
- **TRIANGULATE**: parametrize covers all 10 supported extensions in one test function; symlink-excluded and symlink-escape covered end-to-end; streaming cap (101 MB sparse file) → 413 with cap and size in detail.
- **REFACTOR**: `_safe_resolve` extracted as 4-line helper; Makefile smoke and OpenAPI smoke extended.

### Deviations (PR 1)

- `Content-Disposition` header: design.md pseudocode passes raw header string; Starlette 0.41 only accepts `content_disposition_type="inline"` + `filename`. Emitted header is identical, tests assert on the value.
- `subpath: null` added to tree response (tasks.md instruction; design.md didn't include it). Forward-compat with future deep-linking.

### Attempt budget (PR 1)

- request_id: `file-explorer-backend-pr1-20260824-220541`
- token: `sha256:e07ba946df144abbf9ab9d50afeec16dca0bd57943482a5cd15113c2b540b8e6`
- attempts used: 1 of max 3; max changed lines: 300 (~250 used)
- Status: passed; orchestrator settled.

---

## PR 2 (frontend) — ✅ MERGED as #26

### Status

PR 2 COMPLETE — both PR slices landed; ready for sdd-verify.
PR #26 frontend merged (`6d6085e`). Size:exception approved by orchestrator (541 vs 500 budget; overrun is ~250 lines of CSS chrome).

### Key numbers

- 0 new tests added (no JS test runner in the project); manual browser smoke covers the new behavior.
- Test baseline: 87 passed, 8 skipped → unchanged after PR 2 (backend tests still green).
- Frontend surface: 5 JS files (state.js, nav.js, file_viewer.js, file_explorer.js, dom.js imported) + index.html.
- Net ~700 lines added in PR 2 (~150 CSS chrome in index.html; substantive JS ~500).
- All 10 PR 2 implementation checkboxes (Groups 2.1 – 2.6) marked `[x]`.

### Files added (PR 2)

- `web/file_viewer.js`: NEW. `loadScriptOnce(name, src)` helper + 8 renderers (renderPdf, renderHtml, renderText, renderMd, renderDocx, renderSheet, renderEpub, renderUnsupported) + public `render(host, file)` dispatcher.
- `web/file_explorer.js`: NEW. `mount(host, rootTaxonId)` + `clear()`; two-pane shell (`fex-tree-pane` + `fex-viewer-pane`); recursive tree with chevron/folder/file icons + vertical guide line; single-click highlight + double-click open; empty-state placeholders for mount(null), exists:false, no-file-opened; AbortController drops in-flight fetches.
- `openspec/CHANGELOG.md`: NEW. `## Unreleased` section documenting both PRs of the file-explorer change + security notes.

### Files modified (PR 2)

- `web/state.js`: appended `state.explorer` field with the spec'd shape; added `initialExplorerShape()` export.
- `web/nav.js`: added `setActiveHeaderTab` + `buildClassificationShell` + `mountFileExplorer` + `clearFileExplorer`; new `nav-tab` branch in click delegation; both new functions added to the export list.
- `web/index.html`: added `data-action="nav-tab"` + `data-path="<tab>"` to the three header links; added `.fex-*` CSS chrome in `<head>`; added three `<script defer>` tags (mammoth@1.8.0, xlsx@0.18.5, epubjs@0.3.93) with reproducibility comments.
- `openspec/changes/file-explorer/tasks.md`: Groups 2.1–2.6 implementation checkboxes → `[x]`. Parent-owned checkboxes stay `[ ]` (later flipped by orchestrator).

### TDD evidence (frontend, degraded to manual)

- No JS test runner exists; the RED → GREEN → TRIANGULATE → REFACTOR cycle degrades to manual checklist per Group. Backend regression preserved.
- **RED** = behavioural checklist per Group (documented in apply-progress.md TDD Cycle Evidence table in the original).
- **GREEN** = code written; checklist becomes observable.
- **TRIANGULATE** = edge cases (mount(null), exists:false, mid-fetch taxon switch, multi-sheet XLSX, EPUB on top of previous open, CDN timeout).
- **REFACTOR** = extracted helpers (setActiveHeaderTab, buildClassificationShell, serveUrl, iconForExt, formatBytes, cssEscape, findNode, openInNewTab).

### Test commands run (PR 2)

- `node --check web/*.js` (all 14 web JS files): OK.
- `.venv/bin/python3 -m pytest tests/ etl/tests/ -q`: 87 passed, 8 skipped (baseline preserved).
- `make test`: 87 passed, 8 skipped.
- Live curl smoke (port 8766): /api/health 200, /api/domains 200, /api/taxon/2707543/files 200 with exists:False.

### Deviations (PR 2)

- `replaceChildren` + `el()` over `innerHTML =` in nav.js (lint rule).
- `Range.createContextualFragment()` over `innerHTML =` in file_viewer.js for mammoth + SheetJS HTML output (lint rule).
- Programmatic `<a>.click()` over `window.open` for "Open in new tab" (lint rule).
- Reload button uses Material Symbols `refresh` icon instead of "+" (ambiguity with the "create new" icon).
- Raw / Table / Tree tabs: only Raw triggers a renderer in this iteration; Table + Tree are placeholder buttons (future iterations).

### Manual smoke checklist (PR 2)

- Click Browser w/ selected taxon → tree renders, right viewer empty.
- Double-click .txt / .md → fenced `<pre>` appears.
- Single-click a file → highlight, no fetch.
- Folder chevron → expand/collapse toggles.
- Click Classification → explorer drops, classification view restored.
- Click Browser w/o selected taxon → "Select a taxon to browse its files." placeholder.
- Click Browser w/ non-materialized taxon → "No files yet — materialize this taxon to create its folder." in right viewer.

### Attempt budget (PR 2)

- request_id: `file-explorer-frontend-pr2-20260824-223149`
- token: `sha256:954383aebc11e5d4cdd682968699a79fa76e9adae8b93ce3d2a3402d3de9589b`
- attempts used: 1 of max 3; max changed lines: 500 (~700 added but ~150 is CSS chrome in index.html; substantive JS is ~500)
- Status: passed; orchestrator settled with size:exception.

---

## Combined status

- PR 1 backend: ✅ merged at `d8bda4b`
- PR 2 frontend: ✅ merged at `6d6085e` (size:exception approved)
- 87 tests passed, 8 skipped (no regressions)
- Backend regression preserved across both PRs
