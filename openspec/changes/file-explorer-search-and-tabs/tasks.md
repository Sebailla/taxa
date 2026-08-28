# Tasks: File Explorer — Search + Complete Placeholder Tabs

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~295 (state +5, file_explorer.js +120, file_viewer.js +110, index.html +60) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Single PR — state, search + filter/highlight, Table + Tree renderers, tab dispatch, CSS, smoke | PR 1 | `make test` (pytest, 63+ pass baseline) | Manual browser smoke on `make smoke` (tree ≥200 files, sample `.csv`/`.tsv`/`.json`) | `git revert` of merge commit restores documented placeholder-tab state. |

---

Strict TDD per `openspec/AGENTS.md`. Browser code uses manual RED pre-checks (no JS test runner).

## Phase 1 — State shape

- [x] 1.1 GREEN: add `search: { query: "", mode: "filter", hideEmpty: true }` to `state.explorer` literal in `web/state.js` and mirror in `initialExplorerShape()`.
- [x] 1.2 GREEN: confirm `clear()` / `mount()` leave `state.explorer.search` at initial shape via `Object.assign(state.explorer, initialExplorerShape())`.

## Phase 2 — Tree search

- [x] 2.1 RED: add empty CSS rules in `web/index.html` for the search header/input/clear/toggles/mode-btn/hide-empty-btn/search-match/search-empty classes. Verify no live Computed match.
- [x] 2.2 GREEN: flesh out CSS per `design.md` §CSS Additions using Tailwind tokens only (`--tertiary-container`, `--primary`, `--realm-*`, `--on-surface-variant`). No hardcoded hex.
- [x] 2.3 GREEN: extend `renderTreeHeader()` in `web/file_explorer.js` with input + toggle rows using Material Symbols `filter_alt` / `highlight_alt` / `visibility_off`.
- [x] 2.4 GREEN: add `_annotateMatches(rootNode, query)` — single recursive walk returning `{ matches: Set<path>, ancestors: Set<path> }`; case-insensitive substring on `name` OR `path`; per-node memo.
- [x] 2.5 GREEN: add `applySearchToTree(rootEl, annotation, hideEmpty)` — toggles `style.display` + `<details>.open` only; never touches `aria-expanded` or class churn.
- [x] 2.6 GREEN: add `applyHighlightToTree(rootEl, annotation)` — toggles `.search-match` class only; never touches `aria-expanded`, `<details>.open`, or `.fex-children` display.
- [x] 2.7 GREEN: wire input `oninput` — 200 ms debounce, writes `state.explorer.search.query`, dispatches to filter or highlight pass; empty query → `restoreTree()`.
- [x] 2.8 GREEN: wire clear button — empties input + `state.explorer.search.query`, calls `restoreTree()`. No `.search-match` remnants in highlight mode.
- [x] 2.9 GREEN: wire `.fex-search-mode-btn` — toggles `state.explorer.search.mode` filter↔highlight, swaps icon, updates `aria-pressed`, re-applies search if query active. Query survives.
- [x] 2.10 GREEN: wire `.fex-search-hide-empty-btn` — toggles `state.explorer.search.hideEmpty`, swaps icon, updates `aria-pressed`, re-applies filter pass if active.
- [x] 2.11 GREEN: in filter mode, when `query.length > 0 && matches.size === 0`, paint `.fex-search-empty` (`"No matches."`) and hide tree body. Unreachable in highlight mode.

## Phase 3 — Table + Tree viewer tabs

- [x] 3.1 GREEN: add `Papa: "https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js"` to `CDN_URLS` in `web/file_viewer.js` with pinned-version comment. No `<script>` in `web/index.html`.
- [x] 3.2 RED: stub `renderTable(target, file)` as no-op. Verify Table tab on CSV renders empty body.
- [x] 3.3 GREEN: implement `renderTable` — `loadScriptOnce("Papa", …)`, `Papa.parse(text, { delimiter: ext === "tsv" ? "\t" : "," })`, sticky `<thead>` `<table class="fex-csv-table">` inside `<div class="fex-csv-scroller">`, `target.replaceChildren(scroller)`. On Papa failure → `renderOfflineBanner(target)`.
- [x] 3.4 GREEN: register `csv: renderTable` and `tsv: renderTable` in `RENDERERS` map.
- [x] 3.5 RED: stub `renderJsonTree(target, file)` as no-op. Verify Tree tab on JSON renders empty body.
- [x] 3.6 GREEN: implement `renderJsonTree` — `JSON.parse(text)`, iterative stack walk capped at 50 000 nodes; object/array → `<details><summary class="fex-row">` with 16 px indent per level; leaves → `<div class="fex-tree-leaf type-{string|number|boolean|null}">`; on cap → `<p class="fex-tree-truncated">"Tree truncated — open raw"</p>`. `try/catch` parse errors → offline banner.
- [x] 3.7 GREEN: register `json: renderJsonTree` in `RENDERERS` map.
- [x] 3.8 GREEN: add CSS for `.fex-csv-table` (sticky `thead`, `var(--surface-container)` bg), `.fex-csv-scroller` (max-height + overflow auto), `.fex-json-tree` (16 px indent + `var(--outline-variant)` left border per `.fex-tree-leaf-children`), `.fex-tree-leaf.type-*` colour rules using `--realm-*` tokens. No hardcoded hex.
- [x] 3.9 RED: inspect tab-strip click handler in `web/file_explorer.js` (~lines 650–657). Confirm manually `fileViewer.render` is NOT called on tab click.
- [x] 3.10 GREEN: modify tab-strip click handler — after setting `state.explorer.viewerTab`, call `fileViewer.render(bodyEl, openFile*)` to dispatch the matching renderer. Non-tabular formats get `"Table/Tree view not available for this format — use Raw."`.

## Phase 4 — Smoke + regression

- [ ] 4.1 Hand-test filter mode (200+ files, type `acr` → matches visible, parents auto-expanded). Asserts `spec.md` §Filter mode hides non-matching rows.
- [ ] 4.2 Hand-test filter + hide-empty = `"No matches."` (`zzzzz` → empty-state copy). Asserts `spec.md` §Filter mode + hide-empty shows "No matches.".
- [ ] 4.3 Hand-test highlight keeps expand/collapse (collapse `X`, switch to highlight, match inside `X` → `X` collapsed, leaves carry `.search-match`). Asserts `spec.md` §Highlight mode keeps expand/collapse state.
- [ ] 4.4 Hand-test clear restores tree (query + `×` → input empty, tree restored, no class remnants). Asserts `spec.md` §Clear restores tree without state churn.
- [ ] 4.5 Hand-test toggles persist query (filter + `acr` → highlight → query stays, icon flips, rows painted not hidden). Asserts `spec.md` §Toggles persist while keeping the query.
- [ ] 4.6 Hand-test CSV opens with sticky header (`data.csv` + Table → first row sticky, body scrolls both axes). Asserts `spec.md` §CSV opens with sticky header.
- [ ] 4.7 Hand-test TSV uses tab delimiter (`data.tsv` + Table → no `\t` artefacts). Asserts `spec.md` §TSV uses tab delimiter.
- [ ] 4.8 Hand-test Papa CDN failure (throttle, `data.csv` + Table → `.fex-banner`, Raw works). Asserts `spec.md` §CDN load failure falls back to Raw.
- [ ] 4.9 Hand-test JSON root expands (`spec.json` + Tree → root caret, 16 px indent per level). Asserts `spec.md` §JSON root expands on click.
- [ ] 4.10 Hand-test leaf types colour-coded (expand object → string/number/boolean/null each carry Tailwind token class). Asserts `spec.md` §Leaf values are type-coloured.
- [ ] 4.11 Hand-test large JSON truncation (60 000-node JSON → `"Tree truncated — open raw"`, Raw works). Asserts `spec.md` §Large JSON is truncated with a hint.
- [ ] 4.12 Hand-test non-tabular ignores tabs (`notes.md` + Table/Tree → `"Table/Tree view not available for this format — use Raw."`, no console error). Asserts `spec.md` §Non-tabular file ignores Table/Tree tabs.
- [ ] 4.13 Regression: Raw tab still renders for `.md`, `.txt`, `.pdf`, `.html`, `.docx`, `.xlsx`, `.epub`, `.doc` per `spec.md` §Multi-format file viewer.
- [ ] 4.14 Regression: `make test` green (63-pass baseline). `make smoke` green (no backend changes; curl hits for `/api/taxon/{id}/files` and `/api/taxon/{id}/files/serve` still pass).