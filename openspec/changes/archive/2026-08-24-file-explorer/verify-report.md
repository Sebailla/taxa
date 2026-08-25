# File Explorer & Viewer — Verify Report

> **Source**: Engram observation `sdd/file-explorer/verify-report` (id 4234). This is the condensed version; the original 8817-byte file had a full per-requirement spec coverage table + test command output.

## Pass/fail

**PASS** — both PRs merged, all 21 implementation tasks `[x]`, all 8 spec requirements PASS, 87/8 test baseline preserved.

- PR #25 backend (`d8bda4b`): `merged=true`
- PR #26 frontend (`6d6085e`): `merged=true`
- Implementation: 21/21 checkboxes
- Tests: 87 passed, 8 skipped, 0 failed
- No blockers.

## Spec coverage (all 8 requirements PASS)

| # | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Browsable research folder tree per taxon (left pane + empty-state + no-taxon placeholder) | PASS | `web/file_explorer.js` two-pane shell; mount(null)/exists-false branches. |
| 2 | Recursive directory listing endpoint `GET /api/taxon/{id}/files` (200/404, synonyms, sort: folders-first, case-insensitive) | PASS | `api/server.py:_walk_tree`; 4 tree tests PASS. |
| 3 | Path-traversal-safe streaming endpoint `GET /api/taxon/{id}/files/serve?path=<rel>` (9-format content-type table, traversal/absolute/symlink blocked, 413 cap, FileResponse streaming) | PASS | `api/server.py:_safe_resolve`; 7 safety tests PASS. |
| 4 | Multi-format file viewer (PDF, HTML sandboxed, TXT/MD, DOCX via mammoth.js, DOC fallback, XLS/XLSX via SheetJS, EPUB via epub.js, CDN-failure banner) | PASS | `web/file_viewer.js` 8 renderers + CDN pins (mammoth@1.8.0, xlsx@0.18.5, epubjs@0.3.93). |
| 5 | Tree interaction semantics (single-click highlight, double-click open, folder expand/collapse, switch-taxon clears state) | PASS | single-click highlight, double-click open, AbortController in `clear()`. |
| 6 | Header integration (mount on Browser click, placeholder when no selection, clean unmount on Classification/Settings) | PASS | `web/nav.js` mountFileExplorer/clearFileExplorer + nav-tab delegation. |
| 7 | Strict-TDD coverage (≥ 12 new tests in `tests/test_api_file_explorer.py`) | PASS | 24-test `tests/test_api_file_explorer.py`, fixture pattern matches materialize. |
| 8 | Existing tests unaffected (`63 + N passed, 8 skipped` where N ≥ 12) | PASS | baseline 63+24=87, 8 skipped pre-existing. |

## Task completion status

- **Implementation: 21/21 ✓** (PR 1: 11, PR 2: 10)
- **Parent-owned: 3** (2 verified DONE in repo: PR #25 + PR #26 merged; 1 in progress: this sdd-verify → later marked complete by orchestrator post-merge)
- **Unchecked implementation: 0**

## Test results

- `pytest tests/ etl/tests/ -v`: 87 passed, 8 skipped, 0 failed in 17.47s
- `pytest tests/test_api_file_explorer.py -v`: 24 passed in 0.27s (14 functions; 10 parametrized extension cases)
- `node --check web/file_viewer.js && node --check web/file_explorer.js`: OK

## Strict TDD compliance

- **TDD Cycle Evidence tables present: YES** (PR 1 + PR 2 in apply-progress.md)
- **Assertion quality audit: PASS** — no tautologies, ghost loops, type-only, smoke-only, or impl-detail CSS assertions
- **Cross-referenced test files exist: YES** (test_api_file_explorer.py present, 523 lines)
- **Frontend TDD degrades to manual checklist** per documented project convention (no JS test runner)

## Review workload / PR boundary

- **Chained PRs respected: YES** (PR #25 backend only, PR #26 frontend only, stacked-to-main)
- **size:exception recorded: YES** (PR #26 = 541 vs 500 budget; substantive JS within budget; ~250 LOC of CSS chrome in index.html)
- **Scope creep: NONE**

## Deviations (non-blocking)

1. Content-Disposition via Starlette 0.41's `content_disposition_type="inline"` + `filename=basename` (vs design.md raw header string). Byte-identical to spec.
2. `subpath: null` extra field in tree response (forward-compat). Silent.
3. Refresh icon instead of + in EXPLORER header (ambiguity avoidance).
4. Raw/Table/Tree tabs: only Raw triggers renderer (Table/Tree are decoration for non-textual formats per design.md).
5. `Range.createContextualFragment` over `innerHTML` (lint-clean, XSS surface unchanged).
6. 8 SKIPPED tests are pre-existing (`test_smoke.py::TestDbBackedEndpoints` + health).

## next_recommended

`sdd-archive` — all implementation complete, no blockers, no scope creep.

## Verification metadata

- Artifact store: hybrid (openspec primary, Engram fallback)
- Strict TDD: ACTIVE
- Files audited: api/server.py, tests/test_api_file_explorer.py, tests/test_smoke.py, Makefile, web/file_viewer.js, web/file_explorer.js, web/state.js, web/nav.js, web/index.html, openspec/CHANGELOG.md
- Commands: pytest (full + new file), node --check, git log, gh api
- Lines changed total: 835 across 3 SDD attempts (294 backend + 541 frontend + 0 finalize)
