# File Explorer & Viewer — Tasks

> **Source**: Engram observation `sdd/file-explorer/tasks` (id 4224) + the in-progress checkbox state at the time of the orchestrator's inline write (after sdd-tasks sub-agent failed twice and the orchestrator wrote the file inline per user instruction "vos"). All 24 checkboxes marked `[x]` after the orchestrator marked the 3 parent-owned ones post-merge.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | 600-800 new code + 250 tests + 20 docs |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend, ~250 lines) → PR 2 (frontend, ~400 lines) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main (user-picked; pending → resolved) |

```
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

Tasks are sequenced **RED → GREEN → TRIANGULATE → REFACTOR** per the
project's strict TDD policy (`openspec/config.yaml` `strict_tdd: true`).
Every implementation checkbox ends with exactly one ownership marker.

---

## PR 1 — Backend (apply first, shippable on its own) ✅ MERGED as PR #25

Ships the two new endpoints + 13 backend tests + smoke-test extension.
After this PR lands, the frontend still does nothing on Browser-tab
clicks — that's fine; the explorer module mounts in PR 2.

### Group 1.1 — RED scaffold ✅

- [x] RED: write `tests/test_api_file_explorer.py` with the 12 cases from the spec (tree happy path, traversal `..`, absolute path `/etc/passwd`, unknown taxon 404, unsupported extension, symlink excluded from tree walk, file not found, content-type parametrized over the 9 extensions, streaming cap 413). Mirror `tests/test_api_materialize.py`'s pattern: `monkeypatch.setattr("api.server.RESEARCH_DIR", tmp_path / "Research")` plus `monkeypatch.setattr("api.server.db", fake_db)`. Confirm pytest collects the file and all 12 tests fail with 404 / connection errors (no endpoints exist yet). <!-- sdd-owner: implementation -->

### Group 1.2 — GREEN: tree endpoint ✅

- [x] GREEN: add `from datetime import datetime` and `from fastapi.responses import FileResponse` to the imports block in `api/server.py`. Add module-level `_STREAM_CAP_BYTES = 100 * 1024 * 1024` and `_CONTENT_TYPE_BY_EXT` dict (10 entries). Add a private helper `_walk_tree(path: Path, rel: str, depth: int = 0) -> dict` that recursively walks a directory, skipping symlinks (`not entry.is_symlink()`), sorting folders-first then files case-insensitive, capping depth at `_MAX_PARENT_DEPTH`. <!-- sdd-owner: implementation -->

- [x] GREEN: add `GET /api/taxon/{taxon_id}/files` to `api/server.py` (insert before the StaticFiles mount). Reuse `_build_segments(conn, taxon_id)` for the sanitized root path; resolve `RESEARCH_DIR.joinpath(*sanitized)` and check `exists()`; return `{ exists, taxon_id, taxon_name, taxon_path, filesystem_path, subpath, root }` where `root` is the recursive tree from `_walk_tree()`. Confirm the tree tests pass. <!-- sdd-owner: implementation -->

### Group 1.3 — GREEN: streaming endpoint ✅

- [x] GREEN: add `GET /api/taxon/{taxon_id}/files/serve` with `Query` parameter `path: str` (URL-decoded automatically by FastAPI). Implementation: load taxon via `db()` context; compute `sanitized = _build_segments(...)`; resolve `target = (root_dir / path).resolve()`; assert `target.is_relative_to(root_dir.resolve())` (rejects traversal, absolute paths, and symlinks pointing outside); check `target.is_file()` (404 if not); if `target.stat().st_size > _STREAM_CAP_BYTES` return HTTPException(413, ...). <!-- sdd-owner: implementation -->

### Group 1.4 — TRIANGULATE ✅

- [x] TRIANGULATE: parametrize the content-type test over all 9 extensions ✅
- [x] TRIANGULATE: add a symlink test ✅
- [x] TRIANGULATE: add a streaming-cap test ✅
- [x] GREEN: confirm all `tests/test_api_file_explorer.py` tests pass (`87 passed, 8 skipped`). <!-- sdd-owner: implementation -->

### Group 1.5 — REFACTOR + smoke ✅

- [x] REFACTOR: extract a small private helper `_safe_resolve(root: Path, rel: str) -> Path`. <!-- sdd-owner: implementation -->
- [x] Extend `make smoke` with one new curl hit. <!-- sdd-owner: implementation -->
- [x] Confirm `make test` green: `63 + N passed, 8 skipped` (N ≥ 13). <!-- sdd-owner: implementation -->

---

## PR 2 — Frontend (apply on top of PR 1) ✅ MERGED as PR #26

Ships the file-explorer ES module, the format dispatcher, CDN pins,
state and mount-hook wiring, the OpenSpec CHANGELOG, and the manual
browser smoke. Depends on PR 1's endpoints.

### Group 2.1 — state + mount hooks ✅

- [x] Add `state.explorer = { rootTaxonId: null, tree: null, openFilePath: null, openFileFormat: null, viewerTab: "Raw" }` to `web/state.js`. <!-- sdd-owner: implementation -->
- [x] In `web/nav.js`, wire the existing `[data-path="browser"]` click handler: mount explorer, placeholder if null, `clearFileExplorer()` on Classification/Settings. Export `mountFileExplorer` and `clearFileExplorer`. <!-- sdd-owner: implementation -->

### Group 2.2 — CDN pins + index.html ✅

- [x] In `web/index.html`, add three `<script>` tags immediately before the closing `</body>` (after the existing module imports), with these pinned CDN URLs and a code comment naming the pinned version + reproducibility note for each:
  - mammoth.js `@1.8.0` — `https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js`
  - xlsx (SheetJS community) `@0.18.5` — `https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js`
  - epubjs `@0.3.93` — `https://cdn.jsdelivr.net/npm/epubjs@0.3.93/dist/epub.min.js` <!-- sdd-owner: implementation -->

### Group 2.3 — file_viewer.js (format dispatcher) ✅

- [x] Create `web/file_viewer.js`. <!-- sdd-owner: implementation -->

### Group 2.4 — file_explorer.js (main module) ✅

- [x] Create `web/file_explorer.js`: `mount(rootTaxonId)`, recursive tree, double-click dispatch, Raw/Table/Tree tabs, empty-state. <!-- sdd-owner: implementation -->
- [x] Handle `mount(null)` placeholder. <!-- sdd-owner: implementation -->
- [x] `clear()` resets state + AbortController cleanup. <!-- sdd-owner: implementation -->

### Group 2.5 — manual smoke + regression ✅

- [x] Manual browser smoke documented (11-item checklist). <!-- sdd-owner: implementation -->
- [x] Confirm `make test` + `make smoke` still green. <!-- sdd-owner: implementation -->

### Group 2.6 — OpenSpec artifacts ✅

- [x] Create `openspec/CHANGELOG.md` with a top-level `## Unreleased` section. <!-- sdd-owner: implementation -->

---

## Parent / post-apply lifecycle gates ✅ COMPLETE

- [x] Orchestrator merges PR 1 (backend), fast-forwards main, deletes the branch. ✅ Done — PR #25 merged at `d8bda4b`. <!-- sdd-owner: parent -->
- [x] Orchestrator merges PR 2 (frontend) on top of PR 1, fast-forwards main, deletes the branch. ✅ Done — PR #26 merged at `6d6085e`. <!-- sdd-owner: parent -->
- [x] Orchestrator runs `sdd-verify` against main with both PRs merged. ✅ Done — verify-report PASS, observation 4234. <!-- sdd-owner: parent -->

---

## Engram cross-reference

- Initiative observation: `sdd/file-explorer/tasks` (id 4224).
- PR 1 apply-progress: `sdd/file-explorer/apply-progress` (id 4225, revised 4228).
- PR 2 apply-progress: `sdd/file-explorer/apply-progress-pr2` (id 4228).
- Verify: `sdd/file-explorer/verify-report` (id 4234).
- Archive: `sdd/file-explorer/archive-report` (id 4235).
