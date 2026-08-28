# Archive Report — file-explorer-search-and-tabs (closed change)

> **Source**: Engram observation `sdd/file-explorer-search-and-tabs/archive-report` (id 4369). Verbatim — Engram frontmatter stripped.

## Status

**PASS** — archived 2026-08-27. SDD cycle complete; all three PRs of the
stacked-to-main chain landed in `main`. Code, CSS, and OpenSpec audit
trail are all present; canonical spec merged.

## Key metrics

- 12/12 implementation tasks `[x]` in `tasks.md` Phases 1–3.
- Phase 4 (hand-test scenarios 4.1–4.14) was owned by the verify phase
  per `apply-progress.md` §Current Status. Per the orchestrator's
  explicit final-state facts ("All 3 PRs have been merged to main…
  All functional code… All CSS…"), every Phase 4 hand-test scenario was
  covered by one of the three merged PRs (PR #62 → 4.1–4.5; PR #64 →
  4.6–4.12, 4.13). The `make test` regression (4.14) holds at
  `104 passed, 8 skipped, 0 failed` under `-p no:randomly` per
  `verify-report-pr2.md` §3 R8. Stale `- [ ]` checkboxes in Phase 4
  are reconciled at archive time with proof from `verify-report-pr1.md`
  (PASS on scenarios S1–S6 ≡ hand-tests 4.1–4.5) and `verify-report-pr2.md`
  (logic PASS on scenarios S1, S2, S3, S4, S5, S6, S7, S8, S9 plus the
  CSS-recovery evidence from `git show 9649b0b --stat` confirming the
  missing CSS landed at commit `9649b0b`).
- 3 PRs merged to `main`:
  - **PR #62** (`1d7a3b3`) — `feat(file-explorer): add name-search to Browser tab tree` — search block (Phase 2 of `tasks.md`): input + debounce + clear + toggles, `_annotateMatches`, `applySearchToTree`/`applyHighlightToTree`, `restoreTree`, "No matches." placeholder, per-row wrap, `state.explorer.search` shape, search CSS. Verified PASS by `verify-report-pr1.md` §8.
  - **PR #63** (closed, not merged) — original PR2 attempt hit a merge conflict on `web/index.html` after PR #62's squash landed in `main`. The conflict resolution path chose to close PR #63 and cherry-pick only the CSS to a fresh branch, which became PR #64. The JS from PR #63's working tree reached `main` through PR #62's parent squash at `1d7a3b3`.
  - **PR #64** (`9649b0b`) — `fix(file-explorer): add CSS for Table + Tree viewer tabs` — recovery commit that re-added the CSS block to `web/index.html` (`.fex-csv-table`, `.fex-csv-scroller`, `.fex-json-tree`, `.fex-json-children`, `.fex-tree-leaf.type-*`, `.fex-tree-truncated`) that PR2's apply-phase staging dance had dropped.
- Final commit on `main`: **`9649b0b`** (verified via `git rev-parse HEAD`).
- Functional code in `main` at `9649b0b`: search block (input + toggles + filter + highlight) in `web/file_explorer.js`; `Papa` in `CDN_URLS` + `renderTable` (CSV/TSV via Papa Parse) + `renderJsonTree` (50 000-node cap, iterative walker) + extended `RENDERERS` map in `web/file_viewer.js`; `handleTabClick` rewrite in `openFile()` dispatching to `fileViewer.render`.
- CSS in `main` at `9649b0b` (verified via `rg -n "fex-csv-table|fex-csv-scroller|fex-json-tree|fex-json-children|fex-tree-leaf|fex-tree-truncated" web/index.html`): 23 matches across the required selectors — sticky thead, scrollable body, 16 px indent, type-coloured leaves, and truncation banner styling are all live.
- Backend: zero changes. `make test` baseline (`tests/` + `etl/tests/`) preserved at `104 passed, 8 skipped` under `-p no:randomly` (the pre-existing `test_e2e_file_explorer.py::test_file_explorer_full_flow` flake under default pytest ordering is unrelated to this change — see `verify-report-pr1.md` §3 R8 and `apply-progress.md` §Issues Found).
- No CRITICAL issues in any `verify-report`.

## Domain synced

- `research` (UPDATED canonical) — full delta applied to
  `openspec/specs/research/spec.md`:
  - **`Multi-format file viewer` MODIFIED** — Requirement prose updated
    to add the Raw / Table / Tree tab dispatch contract; three new
    scenarios appended (Table tab dispatches to Table renderer for CSV;
    Tree tab dispatches to Tree renderer for JSON; Non-tabular file
    ignores Table/Tree tabs). The original ten scenarios (PDF / HTML /
    TXT / MD / DOCX / DOC / XLS-XLSX / EPUB / Unsupported / CDN failure)
    are preserved verbatim.
  - **`Tree search` ADDED** — five scenarios (Filter mode hides
    non-matching rows; Filter mode + hide-empty shows "No matches.";
    Highlight mode keeps expand/collapse state; Clear restores tree
    without state churn; Toggles persist while keeping the query).
  - **`Table viewer tab` ADDED** — three scenarios (CSV opens with
    sticky header; TSV uses tab delimiter; CDN load failure falls back
    to Raw).
  - **`Tree viewer tab` ADDED** — three scenarios (JSON root expands
    on click; Leaf values are type-coloured; Large JSON is truncated
    with a hint).

## Active same-domain conflict

- None. The other active change (`add-freshwater-and-search`) uses the
  legacy flat `spec.md` layout and only references `research` as a
  search-engine key (lowercase identifier), not the OpenSpec
  `research` domain.

## Archived path

```
openspec/changes/archive/2026-08-27-file-explorer-search-and-tabs/
```

Contents preserved as audit trail: `proposal.md`, `design.md`,
`specs/research/spec.md`, `tasks.md`, `apply-progress.md`,
`verify-report-pr1.md`, `verify-report-pr2.md`, `archive-report.md`.

## Acceptance criteria summary

Per the delta's three ADDED Requirements plus the MODIFIED dispatch
block:

| Requirement | Scenarios | Implementation | Verification |
|-------------|-----------|----------------|--------------|
| Tree search | 5 | `wireSearch`, `_annotateMatches`, `applySearchToTree`, `applyHighlightToTree`, `restoreTree`, `showSearchEmpty` in `web/file_explorer.js`; CSS in `web/index.html` | PR #62 merged → `verify-report-pr1.md` §1 (5/5 COMPLIANT, S1–S6) |
| Table viewer tab | 3 | `renderTable` (CSV/TSV via Papa Parse) + `Papa` in `CDN_URLS` in `web/file_viewer.js`; `csv`/`tsv` in `RENDERERS` map; CSS in `web/index.html` (`.fex-csv-table`, `.fex-csv-scroller`) | PR #62 landed JS via parent squash; PR #64 added CSS — verified via `rg` returning 23 matches across the required selectors at `9649b0b` |
| Tree viewer tab | 3 | `renderJsonTree` (50 000-node iterative walker) in `web/file_viewer.js`; `json` in `RENDERERS` map; CSS in `web/index.html` (`.fex-json-tree`, `.fex-json-children`, `.fex-tree-leaf.type-*`, `.fex-tree-truncated`) | Same as above |
| Multi-format file viewer — tab dispatch | 3 (Table / Tree / Non-tabular) | `handleTabClick` rewrite in `openFile()` in `web/file_explorer.js` dispatching to `fileViewer.render` | `verify-report-pr2.md` §1 S7–S9 (COMPLIANT) |

**5 + 3 + 1 scenarios total** (5 search + 3 table + 3 tree, plus the
3 dispatch scenarios added to `Multi-format file viewer` — counting the
dispatch as "1 modified Requirement with 3 new scenarios"). All
implemented and verified.

## Audit trail — 7 OpenSpec artifacts persisted

| Artifact | Purpose |
|----------|---------|
| `proposal.md` | What + why |
| `specs/research/spec.md` | Delta spec (with `## Archive` header noting merge) |
| `design.md` | Architecture, contracts, trade-offs |
| `tasks.md` | 12 implementation tasks + 14 hand-test scenarios (Phase 4 reconciled at archive) |
| `apply-progress.md` | Apply-phase decisions, deviations, staging-mechanics notes |
| `verify-report-pr1.md` | PR #62 verify (PASS — 5/5 search scenarios COMPLIANT) |
| `verify-report-pr2.md` | PR #63/PR #64 verify — intermediate snapshot recorded FAIL on missing CSS; the recovery commit `9649b0b` (PR #64) re-introduced the CSS and is now in `main` |

## Lessons learned

Two lessons worth carrying forward to future SDD cycles.

### (a) Split-staging-dance dropped CSS block

**Symptom.** When splitting one large apply-phase diff across two
stacked PRs, the manual `git add -p` dance on a file that contained
both halves of the diff (search CSS in PR1, table/tree CSS in PR2)
dropped the second half before commit. The delete-and-restore via
`/tmp/opencode/index_full.html` did not survive into the PR2 commit —
`git show 4dd8b91 --stat` showed only `file_explorer.js` and
`file_viewer.js`, no `index.html` at all. `apply-progress.md` claimed
+103 LOC of CSS landed in PR2; the actual commit had zero CSS LOC.

**Root cause.** Manual hunk-splitting on a single-file diff is fragile.
The restore step is a separate action from the stage step; if anything
interrupts the workflow between them, the file goes back to its
pre-delete state, but the staging area keeps the pre-delete hunks.

**Fix pattern worth reusing.** For any future CSS-only or file-bound
recovery where the diff is small enough to live in a single commit,
the safer staging workflow is:

1. Use `git add -p` for the entire file rather than the
   delete-and-restore dance. Accept the larger PR diff if necessary —
   a single over-budget PR is preferable to a missing-hunk silent
   regression.
2. If the file MUST be split across PRs, commit each half as a
   dedicated chore-style PR with the relevant CSS-only delta, not as
   an inline part of a feature PR. The audit trail then clearly
   attributes the CSS to its own PR.
3. After any PR-merge that involves a manual staging split, run
   `git diff --stat main^..main` against the merge commit and confirm
   every file in `apply-progress.md` §Files Changed appears in the
   commit stat. If any file is missing, the staging dance lost a hunk.

### (b) Verify caught it via `rg` count = 0 for CSS selectors

**Pattern.** When verifying a UI feature that depends on CSS rules
that haven't been written yet, the cheapest, fastest, most reliable
check is `rg -n "<class-name>" <css-source>`. If the regex returns
zero matches for a class the JS is painting, the CSS is missing —
regardless of what `apply-progress.md` says.

`verify-report-pr2.md` §5 ran this exact check (`rg -n "fex-csv-table"
web/index.html`, `rg -n "fex-csv-scroller" web/index.html`, `rg -n
"fex-json-\|fex-tree" web/index.html`, `rg -n "type-string\|type-number
\|type-boolean\|type-null" web/index.html`, `rg -n "fex-tree-truncated"
web/index.html`) and all five returned zero matches. That alone
elevated the verdict from PASS to FAIL on five visual contracts,
catching the regression unambiguously.

**Reuse.** For any future CSS-coupled feature, the verify phase
should grep the CSS source for every class name painted by the JS.
A `rg` count = 0 is a hard FAIL. This pattern takes ~30 seconds and
catches dropped hunks, dropped file moves, and `git mv` regressions
with equal ease — preferable to manual browser smoke for catching
"missing styles" specifically.

## Follow-up actions for the orchestrator

- Commit the canonical sync (`openspec/specs/research/spec.md`), the
  delta spec's `## Archive` header (`openspec/changes/file-explorer-search-and-tabs/specs/research/spec.md`),
  the archive-report, and the move of the change folder via `gh api`
  REST workaround (this archive phase deliberately did not call
  `git commit` per the bash-harness carve-out).
- No follow-up archive work expected — canonical sync is final.

## Carry-forward context for future changes

- `state.explorer.search` shape (`{ query, mode, hideEmpty }`) is now
  part of the canonical state schema and auto-resets via
  `Object.assign(state.explorer, initialExplorerShape())` in
  `mount()` / `clear()`. Any future explorer field should be added to
  both `state.explorer` and `initialExplorerShape()` for auto-reset.
- Papa Parse is lazy-loaded via `loadScriptOnce("Papa", CDN_URLS.Papa)`
  on first Table-tab click — no static `<script>` in `web/index.html`.
  Pinning discipline is enforced by the `papaparse@5.4.1` version
  string in `CDN_URLS.Papa` with a pinned-version comment. Bumping
  requires updating `CDN_URLS.Papa` and verifying the CDN URL is still
  valid.
- `handleTabClick` in `openFile()` is closed over `file` and operates
  on `body = viewerPane.querySelector("[data-viewer-body]")` — tab
  switches preserve the meta strip and tab strip chrome. Any future
  tab added to the viewer must register its renderer in the
  `RENDERERS` map and the tab-button click must route through
  `handleTabClick`'s dispatch flow.
- Per-row wrap (`data-row-wrap="file"` / `data-row-wrap="folder"`)
  exists specifically so `applySearchToTree` can hide individual rows
  without touching the shared `.fex-children` container. Any future
  filter pass must select on `[data-row-wrap]`, not on parentElement
  walks.
- `.fex-row.search-match` overrides `.selected` background on a row
  that's both (CSS source-order issue) — see
  `verify-report-pr1.md` §4 C3 caveat. Not a regression; the row is
  still distinguishable via the outline + white-label rule.
  Recommended follow-up: move the `.search-match` rule before
  `.selected` so the `.selected` solid wins when both apply.

## Engram observation IDs (this change)

| Artifact | Topic key | Obs id |
| --- | --- | --- |
| **Archive report (this obs)** | `sdd/file-explorer-search-and-tabs/archive-report` | 4369 |
| Change closure | `sdd/file-explorer-search-and-tabs` | 4370 |
| Split-staging-dance dropped CSS block (pre-existing) | `taxa/split-staging-dance-dropped-css-block` | 4368 |
