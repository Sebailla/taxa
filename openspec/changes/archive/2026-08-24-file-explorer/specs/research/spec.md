# Research Specification

> **Source**: Engram observation `sdd/file-explorer/spec` (id 4222) + canonical at `openspec/specs/research/spec.md` (committed at `278c8f4`).
>
> **NOTE**: This archive copy is a **condensed mirror** of the 398-line canonical spec. The full body — including all 8 requirements and 28+ scenarios with verbatim GIVEN/WHEN/THEN bullets — lives at the canonical path. The Engram observation holds a summary + requirement→AC mapping table, not the full body. If you need the exact scenario wording, read the canonical.

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

## Requirements at a glance

| # | Requirement |
| --- | --- |
| 1 | Browsable research folder tree per taxon (left pane + empty-state + no-taxon placeholder) |
| 2 | Recursive directory listing endpoint `GET /api/taxon/{id}/files` (200/404, synonyms, sort: folders-first, case-insensitive) |
| 3 | Path-traversal-safe streaming endpoint `GET /api/taxon/{id}/files/serve?path=<rel>` (9-format content-type table, traversal/absolute/symlink blocked, 413 cap, FileResponse streaming) |
| 4 | Multi-format file viewer (PDF, HTML sandboxed, TXT/MD, DOCX via mammoth.js, DOC fallback, XLS/XLSX via SheetJS, EPUB via epub.js, CDN-failure banner) |
| 5 | Tree interaction semantics (single-click highlight, double-click open, folder expand/collapse, switch-taxon clears state) |
| 6 | Header integration (mount on Browser click, placeholder when no selection, clean unmount on Classification/Settings) |
| 7 | Strict-TDD coverage (≥ 12 new tests in `tests/test_api_file_explorer.py` following the existing fixture pattern from `test_api_materialize.py`) |
| 8 | Existing tests unaffected (`63 + N passed, 8 skipped` where N ≥ 12) |

## Hard rules anchored

- Path traversal blocked at the API layer via `Path.resolve()` + strict-parent assertion.
- CDN library URLs MUST be pinned (mammoth.js, SheetJS, epub.js, marked.min.js) and documented as inline comments in `web/index.html`.
- No new Python deps; no new JS build step.
- `state.explorer = { rootTaxonId, tree, openFilePath, openFileFormat, viewerTab }` added to `web/state.js`; nothing else changes.
- `web/nav.js` MUST expose `mountFileExplorer(rootTaxonId)` and `clearFileExplorer()` hooks.
- Frontend behavior is verified manually + via `make smoke`; no new JS test runner.

## Mapping to proposal acceptance criteria

| AC | Spec requirement(s) |
| --- | --- |
| AC-1 (Browser with selected taxon) | Req 1, Req 6 |
| AC-2 (Browser with no selection) | Req 1, Req 6 |
| AC-3 (Recursive tree + guide line) | Req 5 |
| AC-4 (Folder/file highlight colors) | Req 5 |
| AC-5 (Single-click file only highlights) | Req 5 |
| AC-6 (Double-click loads file) | Req 4, Req 5 |
| AC-7 (Raw/Table/Tree tabs + meta strip) | Req 4, Req 6 |
| AC-8 (MacOS-style pre panel) | Req 4 (TXT/MD scenarios) |
| AC-9 (404 + empty-state when not materialized) | Req 1, Req 2 |
| AC-10 (Path traversal blocked) | Req 3 |
| AC-11 (Content-Type + Content-Disposition: inline) | Req 3 |
| AC-12 (Existing 63 tests stay green) | Req 8 |
| AC-13 (New tests cover both endpoints + edge cases) | Req 7, Req 8 |

## Full spec body — see canonical

For the complete spec text (all 8 requirements with their full
scenarios in GIVEN/WHEN/THEN format), read
`openspec/specs/research/spec.md` — that is the authoritative source.
This archive copy carries only the purpose + requirements summary +
acceptance-criteria mapping + hard rules.

## Notes

- CDN URLs MUST be pinned in web/index.html (mammoth.js, SheetJS, epub.js, marked.min.js).
- No new Python deps, no new JS build step.
- Reuses _build_segments() and _sanitize_segment() verbatim from api/server.py.
- state.explorer added to web/state.js with shape { rootTaxonId, tree, openFilePath, openFileFormat, viewerTab }.
- web/nav.js MUST expose mountFileExplorer(rootTaxonId) + clearFileExplorer() hooks.
- Frontend verified manually + via make smoke; no new JS test runner.

## Engram cross-reference

This condensed mirror is the sdd-archive phase's record. Full
authoritative spec: `openspec/specs/research/spec.md` (committed at
`278c8f4`). Cross-session Engram observation id 4222.
