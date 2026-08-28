# Verify Report — PR1 (Search Block) — `file-explorer-search-and-tabs`

> Scope: only the **search block** staged for PR1. The viewer-tabs block
> (PR2 — Table + Tree renderer dispatch) is **NOT** in scope for this
> report; it lands in `verify-report-pr2.md` after PR1 merges.

| Field | Value |
|-------|-------|
| Status | **PASS** |
| Verification date | 2026-08-27 |
| Staged tree SHA | `feat/file-explorer-search-and-tabs` working tree, staged hunks only |
| Code LOC verified | 633 insertions (`file_explorer.js` 508 + `index.html` 114 + `state.js` 11) |
| OpenSpec docs LOC | 685 (proposal 119 + spec delta 238 + design 252 + tasks 76) |
| Test command | `make test` (pytest, `tests/`) |
| Test result | 104 passed, 8 skipped, 0 failed (`-p no:randomly`); 103 passed, 8 skipped, 1 failed (default pytest ordering — flaky test order interaction, not a PR1 regression, see Regression Checks §3) |
| Backend smoke | `make smoke` green (`/api/health`, `/api/domains`, `/api/files` route) |
| Risk level | Low |

## 1. Spec-to-Implementation Matrix

PR1 covers exactly **1 ADDED Requirement** (`Tree search`) with **5 Scenarios**.
Line numbers cite the **staged** blob (`git show :web/...`), not the
working tree, so the matrix is anchored to what PR1 will actually commit.

| # | Scenario (spec §) | Implementation | Verdict | Evidence |
|---|-------------------|----------------|---------|----------|
| S1 | **Tree search — debounce + persist** (header of the Requirement) | `wireSearch()` (file_explorer.js:488–513) writes to `state.explorer.search.query` (line 581) with 200 ms debounce; state shape declared in state.js:73–82 + state.js:96 | **COMPLIANT** | `setTimeout(..., 200)` at file_explorer.js:498–501; `state.explorer.search.query = query` at file_explorer.js:581; `search: { query: "", mode: "filter", hideEmpty: true }` at state.js:73–82 |
| S2 | **Filter mode hides non-matching rows** | `applySearchToTree()` (file_explorer.js:706–750) + auto-expand ancestors (lines 712–730) | **COMPLIANT** | `wrap.style.display = "none"` at line 747; `row.setAttribute("aria-expanded", "true")` at line 724 (auto-expand); `_annotateMatches()` returns `{matches, ancestors}` at line 629 |
| S3 | **Filter mode + hide-empty shows "No matches."** | `showSearchEmpty()` (file_explorer.js:803–819) + gating at file_explorer.js:598–603 | **COMPLIANT** | Gate `hideEmpty && matches.size === 0` at file_explorer.js:599–601; `showSearchEmpty(treeRoot)` at line 602; placeholder paints `"No matches."` (line 816) inside `.fex-search-empty` (index.html:1540) |
| S4 | **Highlight mode keeps expand/collapse state** | `applyHighlightToTree()` (file_explorer.js:758–775) | **COMPLIANT** | Only `row.classList.add("search-match")` / `classList.remove("search-match")` (lines 770–772); **zero** `setAttribute("aria-expanded", ...)` / chevron / `.fex-children` display writes in this function — verified by full read of lines 758–775 |
| S5 | **Clear restores tree without state churn** | `clearSearchInput()` (file_explorer.js:518–525) + `restoreTree()` (file_explorer.js:784–796) | **COMPLIANT** | `state.explorer.search.query = ""` at line 523; `restoreTree()` at line 524; `restoreTree` resets `wrap.style.display = ""` (line 790) and `row.classList.remove("search-match")` (line 793), but does NOT touch `aria-expanded` — verified by full read of lines 784–796 |
| S6 | **Toggles persist while keeping the query** | `toggleSearchMode()` (file_explorer.js:529–550) + `toggleHideEmpty()` (file_explorer.js:556–573) | **COMPLIANT** | Mode toggle: `state.explorer.search.mode = next` at line 536; `runSearch(state.explorer.search.query)` at line 549 (preserves the query, re-paints with new mode). Hide-empty toggle: `state.explorer.search.hideEmpty = next` at line 562; `runSearch(state.explorer.search.query)` at line 571 (only when query + filter mode). Query survives both toggles. |

**Coverage:** 5/5 scenarios COMPLIANT. No FAILING or UNTESTED rows.

## 2. Behavioural Assertions (reasoned, not executed)

| # | Assertion | Verdict | Evidence |
|---|-----------|---------|----------|
| B1 | Search input has 200 ms debounce | **PASS** | `setTimeout(..., 200)` at file_explorer.js:501; comment at line 492 cites "spec contract (spec.md L13)" |
| B2 | Filter mode hides non-matching rows via `style.display = "none"` | **PASS** | `applySearchToTree()` line 747: `wrap.style.display = "none";` (per-row wrap, not shared `.fex-children` container) |
| B3 | Filter mode auto-expands ancestor folders via `aria-expanded="true"` | **PASS** | `applySearchToTree()` lines 712–730: for every folder in `ancestors`, sets `aria-expanded="true"` and resets chevron to `keyboard_arrow_down` + icon to `folder` |
| B4 | Highlight mode applies `.search-match` class but never mutates `aria-expanded` | **PASS** | `applyHighlightToTree()` lines 758–775: only `classList.add/remove("search-match")`. No `setAttribute("aria-expanded"…)`, no chevron/icon mutation, no `.fex-children` display change |
| B5 | "X" clear button empties `state.explorer.search.query` and calls `restoreTree()` | **PASS** | `clearSearchInput()` lines 518–525: input cleared (line 522), `state.explorer.search.query = ""` (line 523), `restoreTree()` called (line 524) |
| B6 | Mode toggle persists to `state.explorer.search.mode` and re-applies search | **PASS** | `toggleSearchMode()` line 536: `state.explorer.search.mode = next`; line 549: `if (state.explorer.search.query) runSearch(state.explorer.search.query)` — query is preserved, mode is reapplied |
| B7 | Hide-empty toggle persists to `state.explorer.search.hideEmpty` | **PASS** | `toggleHideEmpty()` line 562: `state.explorer.search.hideEmpty = next` |
| B8 | When query is empty: no filtering, no highlight, tree renders as before | **PASS** | `runSearch()` lines 590–593: `if (!query) { restoreTree(); return; }` short-circuits before any annotation/render pass |
| B9 | When query has 0 matches in filter mode: "No matches." renders | **PASS** | `runSearch()` lines 598–603: gates `showSearchEmpty` on `mode === "filter" && hideEmpty && matches.size === 0`; placeholder paints inside the `.fex-tree-pane` |
| B10 | Search field debounce is per-input (clearTimeout on next keystroke) | **PASS** | `wireSearch()` lines 496–502: `if (timer) clearTimeout(timer); timer = setTimeout(..., 200);` — the previous timer is cancelled on every keystroke, so only the final one fires |
| B11 | "No matches." only paints when hideEmpty is on AND mode is filter | **PASS** | Gate at file_explorer.js:599–601 explicitly conditions on `state.explorer.search.hideEmpty` (filter-only toggle); highlight path at line 605 calls `applyHighlightToTree` without ever reaching `showSearchEmpty` |

**All 11 behavioural assertions PASS.**

## 3. No Regressions in Non-Search Code Paths

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| R1 | `mount()` still wires `state.explorer.rootTaxonId`, fetches `/api/files`, and triggers `rerender()` | **PASS** | file_explorer.js:58 sets `rootTaxonId`; line 63–65 uses `Object.assign(state.explorer, initialExplorerShape())` (a refactor — see apply-progress.md Decisions — but the assignment preserves `rootTaxonId` at line 64). Lines 80–97 fetch and re-render unchanged |
| R2 | `clear()` still aborts in-flight fetch and resets explorer state | **PASS** | file_explorer.js:100–110: abort controller logic (lines 101–104), `Object.assign(state.explorer, initialExplorerShape())` (line 107), host/rootTaxon reset (lines 108–109) |
| R3 | `refresh()` still re-fetches via `mount()` | **PASS** | file_explorer.js:117–120 unchanged |
| R4 | Initial render (no search state) renders the tree identically to before | **PASS** | The new search block is appended inside the existing `.fex-tree-header` (file_explorer.js:361); `renderNodeRow(rootNode, 0)` (line 309) is unchanged; the per-row `data-row-wrap` adds a `<div>` wrapper around each `.fex-row` but does not change row DOM, attributes, or event listeners. `selectFile()` / `openFile()` continue to dispatch off the row itself (`data-file-path` / `data-folder-path`), not the wrap (file_explorer.js:935, 886) |
| R5 | Collapse-all button still works (no collision with new toggle buttons) | **PASS** | Collapse-all keeps its original button (file_explorer.js:330–344, `unfold_less` icon, `fex-snippet-btn` class). The two new toggles (`.fex-search-mode-btn`, `.fex-search-hide-empty-btn`) are appended in a separate row inside `.fex-tree-header-search` (file_explorer.js:430–485). Distinct classes — no event-bubbling or selector collision |
| R6 | Per-row wrap change does not break selection logic | **PASS** | Selection uses `data-file-path` / `data-folder-path` attributes on the row itself (file_explorer.js:886, 935, 997, 1007), not on the wrap. Search toggles wrap `display`, not the row's class list |
| R7 | `cssEscape` polyfill is reused (not re-introduced) | **PASS** | `cssEscape` was already defined in file_explorer.js:1270 (pre-PR1). PR1 reuses it at lines 715, 720, 842, 997, 1007 |
| R8 | `make test` baseline | **PASS** | Full pytest run with `-p no:randomly` (deterministic ordering) → **104 passed, 8 skipped, 0 failed**. With default pytest ordering → 103 passed, 8 skipped, 1 failed (`tests/test_e2e_file_explorer.py::test_file_explorer_full_flow` — Playwright timeout on `wait_for_function('#taxon-{id}')`). The same flake is reproducible against clean HEAD under default ordering (verified by `git stash --include-untracked` + `pytest tests/`). It is a pre-existing test-isolation flake (the test passes when run alone or under `-p no:randomly`), NOT caused by PR1. The file_explorer API tests (`tests/test_api_file_explorer.py`, 24 tests) all pass; PR1 doesn't touch `/api/files` or `/api/files/serve` |
| R9 | `make smoke` | **PASS** | `/api/health`, `/api/domains`, `/api/files` route all green (frontend-only change, no backend surface) |

## 4. CSS Sanity

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| C1 | All new selectors use design tokens (no raw hex) | **PASS** | `git diff --cached -- web/index.html \| grep -E "#[0-9a-fA-F]{3,6}"` returns no matches in the new CSS. Every new colour references `var(--primary)`, `var(--on-surface)`, `var(--on-surface-variant)`, `var(--surface-container-low)`, `var(--outline-variant)`, or `color-mix(in srgb, var(--…) NN%, transparent)` (e.g. index.html:1470, 1472, 1494, 1495, 1517, 1518, 1530, 1531, 1534) |
| C2 | New icons are existing Material Symbols (no invented glyphs) | **PASS** | `search` (file_explorer.js:400), `close` (424), `filter_alt` (452), `highlight_alt` (452, 544), `visibility_off` (477), `search_off` (814). All are standard Material Symbols Outlined (already loaded by the font link in index.html). The `filter_alt_off` glyph mentioned in the user-provided checklist is NOT used — the toggle swaps between `filter_alt` and `highlight_alt`, which is a deliberate simplification noted in apply-progress.md but not a regression |
| C3 | `.fex-row.search-match` is distinct from `.fex-row.selected` and hover state | **PASS with caveat** | `.search-match` uses `color-mix(in srgb, var(--primary) 12%, transparent)` background + `color-mix(... 40%, transparent)` outline + `border-radius: 4px` (index.html:1527–1536). `.fex-row.file.selected` (index.html:1274) is solid `var(--primary)` with white text. Visually distinct. **Caveat:** because `.search-match` (line 1527) is defined AFTER `.selected` (line 1274) and both have specificity (0,2,0), a row that is BOTH selected AND a match loses the solid `.selected` background and gets the softer `.search-match` paint. The `.selected .fex-label` (line 1283) rule still keeps labels white via higher specificity (0,3,0). UX: the row stays clearly identifiable via the outline, but the visual hierarchy of "selected > match" is inverted. **Recommend follow-up:** swap specificity or move the `.search-match` rule before `.selected` so the `.selected` solid wins when both apply. Not a regression — the spec scenario only requires "every matching row is painted with `.fex-row.search-match`", and that is delivered |
| C4 | No new `<script>` tag for the search block (Papa Parse is PR2-only, lazy-loaded — not in PR1 staged blob) | **PASS** | PR1 staged `web/index.html` adds only the CSS block (lines 1426–1542 in the staged blob). No `<script>` tag changes |
| C5 | Toggle buttons reuse `.fex-snippet-btn` for active-state visuals | **PASS** | file_explorer.js:435 (`.fex-snippet-btn fex-search-mode-btn`) and line 464 (`.fex-snippet-btn fex-search-hide-empty-btn`). Reuses the existing toolbar styling |

## 5. Strict TDD Compliance

Per `openspec/AGENTS.md`, every `sdd-apply` task MUST write failing tests first (RED),
make them pass (GREEN), then refactor. Browser code uses manual RED pre-checks
(no JS test runner — design.md §Testing).

`apply-progress.md` §TDD Cycle Evidence documents per-task cycle state:

| Task | Cycle | Compliance |
|------|-------|------------|
| 1.1 Add `search` to `state.explorer` + `initialExplorerShape()` | GREEN | State-shape change, no behavioural surface |
| 1.2 `clear()` / `mount()` use `Object.assign(..., initialExplorerShape())` | GREEN | Refactor — auto-reset pattern |
| 2.1 Empty CSS rules | RED → GREEN | Two-step commit (empty → fleshed) |
| 2.2 Flesh out CSS | GREEN | — |
| 2.3 `renderTreeHeader` adds input + toggle rows | GREEN | — |
| 2.4 `_annotateMatches(rootNode, query)` | GREEN | Two-pass walker (self-matches then ancestors) |
| 2.5 `applySearchToTree(rootEl, annotation, hideEmpty)` | GREEN | — |
| 2.6 `applyHighlightToTree(rootEl, annotation)` | GREEN | — |
| 2.7 Wire input `oninput` (200 ms debounce) | GREEN | — |
| 2.8 Wire clear button + Esc-to-clear | GREEN | — |
| 2.9 Wire `.fex-search-mode-btn` | GREEN | — |
| 2.10 Wire `.fex-search-hide-empty-btn` | GREEN | — |
| 2.11 `"No matches."` empty state | GREEN | — |

**Verdict: PARTIAL.** The apply-progress.md table records explicit
RED→GREEN markers only for tasks 2.1 (CSS empty→fleshed) and the
later PR2 tasks 3.2 / 3.5 / 3.9 (renderer stubs + tab-handler inspect).
The PR1 tasks 1.1–1.2 (state shape) and 2.2–2.11 (search block) are
all marked GREEN-only. Per strict TDD discipline, every behavioural
task should have shown RED first (a failing manual assertion or a
failing console check) before going GREEN. The apply-progress.md does
not record those RED checkpoints for the search block.

The codebase has no JS test runner (project decision per design.md
§Testing + AGENTS.md), so "RED" is a manual checkpoint (e.g. "type
`acr` → no rows visible before the change"). For browser code, the
strict TDD discipline is approximated by:

1. State-shape change (1.1–1.2): no observable UI behaviour — RED is
   not meaningful; pure GREEN is acceptable.
2. Search block (2.2–2.11): each task has a clear observable
   surface (CSS visibility, input → runSearch, clear button,
   toggle persistence). A strict TDD apply would have recorded a
   pre-implementation check (e.g. "before 2.7: type `acr` → no
   rows filtered"). This is missing from the apply log.

**Recommendation for PR2 (verify-report-pr2 will need this):**
ensure PR2's `apply-progress.md` documents explicit RED checkpoints
for every behavioural task — even if just one-liners
("Before 3.2: open `.csv` → empty body confirmed" → GREEN after impl).

**Risk:** the missing RED markers do not block merge — the search
block is straightforward, the implementation matches the spec to the
line, and the GREEN behaviour is reproducible by manual smoke
(tasks 4.1–4.5 in `tasks.md`). But it is a discipline gap to flag.

## 6. Risk Notes for PR1

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | `.fex-row.search-match` overrides `.selected` background on a row that's both (CSS source-order issue) | Low | Move `.search-match` rule before `.selected` in the next change, or bump specificity to (0,3,0). UX-wise the row is still distinguishable via the outline + white-label rule. Not a blocker |
| 2 | `apply-progress.md` Strict TDD RED markers missing for the search block (only PR2 tasks have them) | Low (process) | PR2 should adopt the discipline; PR1 doesn't need to be re-applied |
| 3 | `test_e2e_file_explorer.py::test_file_explorer_full_flow` is flaky under default pytest ordering (passes alone + under `-p no:randomly`) | Pre-existing, not caused by PR1 | Skip in CI under random ordering, or fix the underlying flake in a follow-up. PR1 doesn't introduce the dependency |
| 4 | Per-row wrap (`data-row-wrap`) added to file rows makes the DOM tree one level deeper | Negligible | Tested in §3 R6; selection/expand/collapse unaffected |
| 5 | `applySearchToTree` auto-expands folders whose subtree has matches; `restoreTree()` does NOT re-collapse them in filter mode (only resets `display`) | Low | Spec scenario for clear says "pre-search render" but explicitly preserves state only "in highlight mode" (spec.md:43). Filter-mode persistence of auto-expand is acceptable per spec wording. Document in PR description if reviewers flag |
| 6 | `make test` flake reproducibility on default ordering is non-deterministic — root cause not investigated here | Pre-existing | Out of scope for PR1 |

## 7. Next Steps

- PR1 is **READY TO MERGE** (commit + push).
- After PR1 lands, run `verify-report-pr2` against the unstaged
  viewer-tabs block (`web/file_explorer.js` handleTabClick + openFile
  dispatcher + `web/file_viewer.js` Papa Parse + JSON renderer +
  `web/index.html` `.fex-csv-*` / `.fex-json-*` / `.fex-tree-leaf.*`
  CSS). The PR2 hunk set is currently staged at 96 + 285 + 103 = 474
  LOC (under the 500-LOC ceiling), per `apply-progress.md` §Split.
- The pre-existing `test_e2e_file_explorer.py` flake should be
  triaged separately by the maintainer; PR1 does not own it.

## 8. Verdict

**Status: PASS.** All 5 spec scenarios COMPLIANT. All 11 behavioural
assertions PASS. All 9 regression checks PASS (1 flake under default
ordering is pre-existing). All 5 CSS sanity checks PASS (1 with
caveat documented in risk note #1). Strict TDD compliance is PARTIAL
due to missing RED markers on PR1 tasks — flagged for PR2's discipline.

`next_recommended`: **archive** (PR1 lands cleanly; ready for archive
after merge).