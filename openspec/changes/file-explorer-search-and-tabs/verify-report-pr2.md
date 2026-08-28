# Verify Report — PR2 (Viewer Tabs Block) — `file-explorer-search-and-tabs`

> Scope: the **viewer-tabs block** staged for PR2 (Table + Tree renderer
> dispatch). PR1 (search block) is verified in `verify-report-pr1.md`
> (PASS) and is already merged into `main`. This report covers the PR2
> delta: `web/file_viewer.js` `renderTable`/`renderJsonTree`/RENDERERS
> map extension + Papa CDN URL + `web/file_explorer.js` `handleTabClick`
> rewrite + openFile dispatcher.

| Field | Value |
|-------|-------|
| Status | **FAIL** |
| Verification date | 2026-08-27 |
| Commit(s) verified | `4dd8b91e feat(file-explorer): complete Table + Tree viewer tabs` on `feat/file-explorer-search-and-tabs` (squashed into `1d7a3b3` on `main`) |
| Code LOC verified | 374 insertions (`file_explorer.js` 99 / `file_viewer.js` 285) — `git show 4dd8b91 --stat` |
| Test command | `make test` (pytest, `tests/`, `-p no:randomly`) |
| Test result | **104 passed, 8 skipped, 0 failed** (no regressions; same baseline as PR1) |
| Backend smoke | `make smoke` not re-run in this verify — no backend changes; surface identical to PR1 |
| Risk level | **High** — viewer-tabs CSS for `web/index.html` is **missing from the committed diff**, breaking the spec's visual contracts (sticky thead, 16 px indent, type-coloured leaves). Functional logic intact; visuals are regressed. |

## 0. Premise reconciliation

The task brief said: "PR2 is unstaged PR2 code on the branch
`feat/file-explorer-search-and-tabs`". The actual repo state differs:

- `main` is at `1d7a3b3` — a **squash merge** of the entire SDD stack
  (commit message combines PR1 `1cd03ab` and PR2 `4dd8b91`).
- The branch `feat/file-explorer-search-and-tabs` is at `4dd8b91`. With
  PR1 already merged into `main` as a squash, the branch's delta over
  `main` is effectively empty (`git diff main feat/file-explorer-search-and-tabs`
  returns 0 lines). The verification was conducted against the squash
  commit `1d7a3b3` on `main`, which contains both feat() commits.
- **There is no unstaged PR2 working tree** — `git worktree list` shows
  only `main`. The branch tip already carries everything, so the verify
  objective ("ensure the PR2 delta matches the spec") reduces to verifying
  the code that `4dd8b91` produced.

The PR2 commit's stat (from `git show 4dd8b91 --stat`) is the ground
truth for the PR2 delta:

```
web/file_explorer.js |  99 ++++++++++++++++--
web/file_viewer.js   | 285 +++++++++++++++++++++++++++++++++++++++++++++++++++
2 files changed, 374 insertions(+), 10 deletions(-)
```

**`web/index.html` is NOT in the PR2 commit's diff.** This is the
critical regression flagged in §1 below.

## 1. Spec-to-Implementation Matrix

The PR2 delta covers the **Table viewer tab** (3 scenarios), **Tree
viewer tab** (3 scenarios), and the **Table/Tree tab dispatch** sub-section
of the MODIFIED Multi-format file viewer requirement (3 scenarios, lines
203–225 of `specs/research/spec.md`). The PDF/HTML/TXT/MD/DOCX/XLSX/EPUB/
Unsupported-format/CDN-failure scenarios are pre-existing behaviour that
PR2 must not regress.

| # | Scenario (spec §) | Implementation | Verdict | Evidence |
|---|-------------------|----------------|---------|----------|
| S1 | **Table viewer tab — CSV opens with sticky header** | `renderTable(target, file)` at `web/file_viewer.js:397–467` | **PARTIAL** | Logic paints `<table class="fex-csv-table">` inside `<div class="fex-csv-scroller">` (lines 444, 462). **Sticky `thead` CSS rule is missing** — no selector for `.fex-csv-table thead { position: sticky; … }` exists anywhere in `web/index.html` (verified by `rg -n "fex-csv-\|fex-tree-leaf" web/index.html` returning zero matches). The header will render in document flow and scroll out of view |
| S2 | **Table viewer tab — TSV uses tab delimiter** | `renderTable` at `web/file_viewer.js:404`: `const delimiter = ext === "tsv" ? "\t" : ",";` passed to `window.Papa.parse(text, { delimiter, … })` (line 405–408) | **COMPLIANT** | `delimiter: ext === "tsv" ? "\t" : ","` at line 404; `Papa.parse` invocation at line 405 |
| S3 | **Table viewer tab — CDN load failure falls back to Raw** | `renderTable` `try/catch` at `web/file_viewer.js:398–466`; on Papa parse-error or fetch-failure falls through to `renderOfflineBanner(target, file)` at line 464; uses existing `loadScriptOnce("Papa")` at line 399 (rejects on `onerror`, no static `<script>`) | **COMPLIANT** | `loadScriptOnce("Papa")` at line 399; `renderOfflineBanner` call at line 464; CDN failure rejection handled by existing helper at `file_viewer.js:48–54` (drops cached promise, surfaces error to caller) |
| S4 | **Tree viewer tab — JSON root expands on click** | `renderJsonTree` at `web/file_viewer.js:489–512`; `buildJsonWalker` at lines 521–596; root auto-expanded via `expand(rootNode.element, root)` at line 584; click handler at lines 562–574 | **COMPLIANT (logic) / FAILING (visuals)** | Caret + summary structure correct (`renderJsonNode`, lines 619–643). `fex-json-summary` click wires a custom expander (`onClick`, lines 562–574). **Visually a regression:** 16 px indent CSS (`.fex-json-children { padding-left: 16px; }` per design §CSS Additions) is missing — `rg` returns no matches for `fex-json-children` |
| S5 | **Tree viewer tab — Leaf values are type-coloured** | `renderJsonNode` for primitives at `web/file_viewer.js:605–612`: paints `<div class="fex-tree-leaf type-{string\|number\|boolean\|null}">` via `jsonType(value)` (lines 645–649) | **COMPLIANT (logic) / FAILING (visuals)** | DOM nodes carry the `fex-tree-leaf type-${type}` class (line 608). **CSS rules for `.fex-tree-leaf.type-string`, `type-number`, `type-boolean`, `type-null` are missing** from `web/index.html`. Leaves render as plain divs with no colour tokens applied |
| S6 | **Tree viewer tab — Large JSON is truncated with a hint** | `MAX_JSON_NODES = 50000` at `web/file_viewer.js:487`; iterative walker in `buildJsonWalker` checks `count > MAX_JSON_NODES` at line 544 (sets `truncated = true` and breaks); truncation banner painted at lines 499–507 (`<p class="fex-tree-truncated">"Tree truncated — open raw"</p>`) | **COMPLIANT (logic)** | Cap constant at line 487; cap-check at line 544; banner painted at lines 499–507. The 50 000 cap, the iterative walker (avoids call-stack blowup on deep arrays per design rationale comment at lines 476–479), and the user-facing message are all in place. Style for `.fex-tree-truncated` (warning visual) is missing — text will still appear, just unstyled |
| S7 | **Multi-format — Table tab dispatches to Table renderer for CSV** | `handleTabClick` at `web/file_explorer.js:1212–1261`; supported-branch dispatch via `fileViewer.render(body, file)` at line 1260 (uses `body` from line 1219 — the snippet body `div[data-viewer-body]`); tab active-class toggle at lines 1215–1217. CSV is in RENDERERS map at `web/file_viewer.js:678` | **COMPLIANT** | `state.explorer.viewerTab = tab` at line 1214; tabs toggled via `classList.toggle("active", b === btn)` at line 1217; `csv: renderTable` at file_viewer.js:678; `fileViewer.render(body, file)` at line 1260 |
| S8 | **Multi-format — Tree tab dispatches to Tree renderer for JSON** | Same `handleTabClick` flow. JSON is in RENDERERS map at `web/file_viewer.js:681` (`json: renderJsonTree`) | **COMPLIANT** | `json: renderJsonTree` at file_viewer.js:681 |
| S9 | **Multi-format — Non-tabular file ignores Table/Tree tabs** | `handleTabClick` spec-conformant branch at `web/file_explorer.js:1222–1257`: when `tab === "Table" || tab === "Tree"` and the format is NOT in the supported set (CSV/TSV for Table; JSON for Tree), paints the explicit message `"${tab} view not available for .${ext} files — use Raw."` (line 1243) with a `Download file` link (lines 1245–1253). Comparison is via `renderUnsupported` is **NOT** triggered — the contract wording is painted directly so it matches the spec verbatim | **COMPLIANT** | Lines 1222–1257 of `file_explorer.js`; message literal at line 1243; download `<a>` at lines 1245–1253. `renderUnsupported` (file_viewer.js:358) is reserved for the no-renderer-at-all case (e.g. legacy `.doc` on double-click) per the wiring comment at file_explorer.js:1138–1142 |

**Coverage: 9/9 PR2 scenarios COMPLIANT or PARTIAL at the logic level;
2/9 are visual regressions because the companion CSS in
`web/index.html` was not committed.**

### Non-regression sub-matrix — pre-existing scenarios

| # | Scenario | Verdict | Evidence |
|---|----------|---------|----------|
| NR1 | PDF rendering (`file_viewer.js:90–109 renderPdf`) | **UNCHANGED** | Function untouched in PR2 commit (`git show 4dd8b91 -- web/file_viewer.js` diff is additive only) |
| NR2 | HTML rendering (`renderHtml` lines 114–123) | **UNCHANGED** | — |
| NR3 | Plain-text / Markdown rendering (`renderText` / `renderMd` at lines 154–160) | **UNCHANGED** | — |
| NR4 | DOCX rendering (`renderDocx` lines 166–188) | **UNCHANGED** | — |
| NR5 | XLS / XLSX rendering (`renderSheet` lines 193–260, with multi-sheet picker) | **UNCHANGED** | — |
| NR6 | EPUB rendering (`renderEpub` lines 268–351, with prev/next nav) | **UNCHANGED** | — |
| NR7 | Legacy DOC fallback (`.doc` → `renderUnsupported` legacy message at file_viewer.js:360–363) | **UNCHANGED** | `renderUnsupported` untouched in PR2; legacy message branch (line 361) intact |
| NR8 | Unsupported format fallback (`zip`, `exe`, etc. → `renderUnsupported` at file_viewer.js:358–381) | **UNCHANGED** | — |
| NR9 | CDN failure banner copy is identical across all CDN-using renderers | **UNCHANGED** | `renderOfflineBanner` shared at file_viewer.js:63–84; banner shape `fex-banner` + `cloud_off` glyph + `Download file` link is the same single template |
| NR10 | `render()` dispatcher fallback to `renderUnsupported` for unknown extensions (file_viewer.js:660–664) | **UNCHANGED** | `const fn = RENDERERS[ext] \|\| renderUnsupported` |
| NR11 | Search block from PR1 (already in main) is untouched by PR2 | **PASS** | PR2 commit `4dd8b91 --stat` lists only `web/file_explorer.js` and `web/file_viewer.js`; PR1's CSS block in `web/index.html` lines 1426–1542 (search block) is not in PR2's diff |

## 2. Behavioural Assertions (per the user's checklist)

| # | Assertion | Verdict | Evidence |
|---|-----------|---------|----------|
| B1 | `renderTable`: sticky thead | **FAILING (CSS missing)** | `<thead>` produced at `file_viewer.js:445–451`; CSS rule for `position: sticky; top: 0;` missing from `web/index.html` |
| B2 | `renderTable`: scrollable body | **FAILING (CSS missing)** | `<div class="fex-csv-scroller">` wrapper at `file_viewer.js:462`; CSS for `max-height: calc(100vh - 240px); overflow: auto;` missing |
| B3 | `renderTable`: fallback to `renderOfflineBanner` on CDN failure | **PASS** | `loadScriptOnce("Papa")` rejection → caught at file_viewer.js:463 `catch (e)` → `renderOfflineBanner(target, file)` at line 464 |
| B4 | `renderJsonTree`: collapsible | **PASS (logic)** | `fex-json-summary` `role="button" tabindex="0"` click + Enter/Space handlers at file_viewer.js:562–574; `expand()` toggles `dataset.expanded` + `classList.add("open")` (lines 532–534) |
| B5 | `renderJsonTree`: 16 px indent per level | **FAILING (CSS missing)** | DOM structure applies padding-left via nested `<ul class="fex-json-children">`; CSS for `padding-left: 16px;` missing |
| B6 | `renderJsonTree`: type-coloured leaves using Tailwind tokens | **FAILING (CSS missing)** | Classes `fex-tree-leaf type-{string\|number\|boolean\|null}` set at line 608; CSS for each `.fex-tree-leaf.type-X` colour rule missing (no `--realm-*` overrides applied — Tailwind config tokens are referenced in the comment but never wired up in actual CSS) |
| B7 | `renderJsonTree`: hard 50 000-node cap | **PASS** | `MAX_JSON_NODES = 50000` constant at file_viewer.js:487; cap-check at line 544; `truncated` flag and banner at lines 499–507 |
| B8 | `renderJsonTree`: Raw fallback for oversize files | **PARTIAL** | Spec contract says "AND the Raw tab still renders the full body" (spec.md L106). The renderer appends the truncation banner (line 500–506), but the **raw-body fallback is not implemented** — the Raw tab still works because it's a fresh renderer invocation against `renderAsPre` (file_viewer.js:130–152), but the user has to click Raw. No automatic "click here for raw" link is wired (the docstring at line 473 mentions "open raw" but no anchor is rendered). Low priority — raw tab is one click away |
| B9 | `handleTabClick`: dispatches to `fileViewer.render()` with the same `file` captured in closure | **PASS** | `handleTabClick(viewerPane, btn, file)` is closed over `file` from `openFile` (file_explorer.js:1144 binds `file` into the click handler); at click time, file_viewer.js's `render(body, file)` is called with that exact reference (file_explorer.js:1260) |
| B10 | `handleTabClick`: NO re-run of `openFile()` | **PASS** | `openFile()` is NOT called inside `handleTabClick` (lines 1212–1261). Only `fileViewer.render(body, file)` (line 1260), `classList.toggle("active", …)` (line 1217), and the explicit unsupported-format branch |
| B11 | Tab switch preserves scroll position (does NOT `replaceChildren` on `viewerPane` — only on the body div) | **PASS** | `handleTabClick` operates on `body = viewerPane.querySelector("[data-viewer-body]")` (line 1219); all `replaceChildren` calls are on `body` (lines 1231, …), never on `viewerPane`. Meta strip / tab strip / snippet frame chrome persist on tab clicks |
| B12 | Non-tabular format on Table/Tree tabs: spec-conformant message (NOT the generic `renderUnsupported` message) | **PASS** | The spec-conformant message is painted directly at file_explorer.js:1228–1256 (`"${tab} view not available for .${ext} files — use Raw."`). `renderUnsupported` is NEVER called from `handleTabClick` — the function short-circuits with `return` at line 1256 before reaching `fileViewer.render()` |
| B13 | `RENDERERS` map includes `csv`, `tsv`, `json` keys | **PASS** | file_viewer.js:678 (`csv: renderTable`), 679 (`tsv: renderTable`), 681 (`json: renderJsonTree`) |
| B14 | Papa Parse loaded via `loadScriptOnce` (no new helper, no static `<script>` in `web/index.html`) | **PASS** | `CDN_URLS.Papa` at file_viewer.js:32; `await loadScriptOnce("Papa")` at file_viewer.js:399. **Verified `web/index.html` has NO `<script>` tag for Papa** — `rg -n "papaparse\|papa@" web/index.html` returns zero matches. This matches `apply-progress.md` §Deviations "Papa Parse `<script>` tag" |
| B15 | CSV fallback when `renderTable` fails on a malformed CSV: `renderOfflineBanner` (not a crash) | **PASS** | `try { …Papa.parse… } catch (e) { renderOfflineBanner(target, file); console.error("renderTable failed", e); }` at file_viewer.js:398–466. The Papa-parse-error branch (lines 409–419) throws a synthetic `Error` only for non-benign codes (`TooFewFields`/`TooManyFields` are warned-but-skipped, matching the docstring at lines 393–396), so the actual crash-free path on malformed CSV routes to `renderOfflineBanner` |
| B16 | JSON > 50 000 nodes: explicit user-facing note | **PASS** | `<p class="fex-tree-truncated">"Tree truncated — open raw"</p>` at file_viewer.js:499–507 |

**Tally:** 11/16 assertions PASS, 4/16 FAIL on visual contracts (B1, B2, B5, B6), 1/16 PARTIAL (B8 — works but no auto-link to Raw).

## 3. No Regressions in Non-PR2 Code Paths

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| R1 | Raw tab still renders for `.md`, `.txt`, `.pdf`, `.html`, `.docx`, `.xlsx`, `.epub`, `.doc` | **PASS** | All pre-existing `render*` functions in `file_viewer.js` are untouched by PR2 commit; `RENDERERS` map additive (csv/tsv/json INSERTED; no key rewritten) |
| R2 | `render()` falls through to `renderUnsupported` for unknown extensions | **PASS** | `const fn = RENDERERS[ext] \|\| renderUnsupported;` (file_viewer.js:662) |
| R3 | `render()` renders `.txt` via `renderText` | **PASS** | `txt: renderText` at file_viewer.js:670 |
| R4 | `render()` renders `.pdf` via `renderPdf` (iframe + PDF type) | **PASS** | `pdf: renderPdf` at file_viewer.js:667 |
| R5 | Tab persistence — `state.explorer.viewerTab` drives `active` class | **PASS** | `handleTabClick` writes `state.explorer.viewerTab = tab` (file_explorer.js:1214); initial `openFile` paints the active class on the matching button (lines 1068, 1077, 1086); refresh path (`renderViewerPane` line 1272–1278) re-calls `openFile` which re-reads `state.explorer.viewerTab` to paint the right active tab |
| R6 | Search block (PR1, already in main) is untouched by PR2 | **PASS** | PR2 commit stat lists only `file_explorer.js` and `file_viewer.js`; PR1's `web/index.html` CSS block at lines 1426–1542 is preserved as-is in `git show 1d7a3b3:web/index.html` |
| R7 | PR1's `state.explorer.search` shape is untouched | **PASS** | PR2 commit does not touch `web/state.js`; the shape from PR1 (state.js:82, 96) is preserved |
| R8 | `make test` baseline (104 passed / 8 skipped / 0 failed under `-p no:randomly`) | **PASS** | Same baseline as PR1; PR2 doesn't touch Python / FastAPI / SQLite backend. The pre-existing `test_e2e_file_explorer.py::test_file_explorer_full_flow` flake under default pytest ordering remains pre-existing — verified by `git stash` against clean HEAD per apply-progress.md §Issues Found |
| R9 | `fileViewer.render()` dispatcher signature unchanged | **PASS** | `function render(host, file)` at file_viewer.js:660 — `file_explorer.js` calls it with the same `(body, file)` shape on line 1175 and on the new `handleTabClick` line 1260 |
| R10 | `loadScriptOnce` helper unchanged (Papa uses the same helper) | **PASS** | Helper at file_viewer.js:40–58 unchanged in PR2 |

## 4. Strict TDD Compliance

`apply-progress.md` §TDD Cycle Evidence records explicit RED → GREEN
markers for the PR2 tasks. Each row is reproduced below:

| Task | Cycle | Compliance |
|------|-------|------------|
| 3.1 Add `Papa` to `CDN_URLS` | GREEN-only | State-shape change (CDN_URLS map). No observable behaviour on its own. GREEN is acceptable; RED applies to the renderer that uses it |
| 3.2 Stub `renderTable` (RED) | RED → GREEN | Stub cleared the body — manual check noted |
| 3.3 Implement `renderTable` (GREEN) | GREEN | Real impl |
| 3.4 Register `csv`/`tsv` in `RENDERERS` | GREEN | Map entry addition |
| 3.5 Stub `renderJsonTree` (RED) | RED → GREEN | Stub cleared the body |
| 3.6 Implement `renderJsonTree` (GREEN) | GREEN | Real impl |
| 3.7 Register `json` in `RENDERERS` | GREEN | Map entry addition |
| 3.8 CSV + JSON CSS | GREEN-only | **No RED marker recorded** — and the CSS was NEVER actually committed (see §0 and Risk §R-CSS below), so the GREEN marker is aspirational |
| 3.9 Inspect tab handler (RED) | RED → GREEN | Tab handler inspection noted |
| 3.10 Modify tab handler (GREEN) | GREEN | Real impl |

**Verdict on Strict TDD for PR2: PARTIAL.** The behavioural tasks
(3.2, 3.3, 3.5, 3.6, 3.9, 3.10) have explicit RED→GREEN markers in
`apply-progress.md`. The CSS task 3.8 has only a GREEN marker — and
since the corresponding CSS is missing from the committed diff, the
GREEN marker was applied without ever running an observable test (e.g.
"open `data.csv` in browser, screenshot to verify sticky header"). The
hand-testable scenarios in §4.6–4.12 of `tasks.md` were never run, as
the apply-phase landed without commit-level verification of them.

Process takeaway: per PR1's verdict (also PARTIAL on RED markers),
the apply phase for browser code without a JS runner cannot prove
GREEN without committing the CSS and visually verifying in a browser.
Per the strict TDD contract, "GREEN" means the failing assertion is
fixed — without CSS, the assertion "table has a sticky header" is
still unprovable.

## 5. CSS Sanity (the regression)

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| C1 | `.fex-csv-table` exists with sticky `thead` (`position: sticky; top: 0; background: var(--surface-container);`) | **FAIL** | `rg -n "fex-csv-table" web/index.html` returns 0 matches. Class is referenced only in `file_viewer.js:444`. The `thead` will scroll out of view |
| C2 | `.fex-csv-scroller` has `max-height: calc(100vh - 240px); overflow: auto;` | **FAIL** | `rg -n "fex-csv-scroller" web/index.html` returns 0 matches. Body will not scroll within the snippet frame |
| C3 | `.fex-json-tree` + `.fex-json-children` 16 px indent | **FAIL** | `rg -n "fex-json-\|fex-tree" web/index.html` returns 0 matches. Tree will render flat with no indent |
| C4 | `.fex-tree-leaf.type-string\|number\|boolean\|null` colour rules using `--realm-*` tokens | **FAIL** | `rg -n "type-string\|type-number\|type-boolean\|type-null" web/index.html` returns 0 matches. Leaves render unstyled (default text colour) |
| C5 | `.fex-tree-truncated` styling for truncation banner | **FAIL** | `rg -n "fex-tree-truncated" web/index.html` returns 0 matches. Banner text still appears (DOM is painted), but with no visual treatment |
| C6 | No hardcoded hex in new CSS | **N/A — CSS missing** | The class names referenced in JS are never defined; no new CSS was added to verify |
| C7 | Papa Parse lazy-loaded via `loadScriptOnce` (no static `<script>`) | **PASS** | `rg -n "papaparse\|papa@" web/index.html` returns 0 matches (no static tag); `CDN_URLS.Papa` injected via `loadScriptOnce` at file_viewer.js:399 |

**CSS regression summary:** 5/7 visual contracts FAIL because their
companion CSS rules were never committed. The DOM emits all the right
class names; the rendering layer just doesn't have styles to apply.

## 6. Critical regression — PR2 commit stats vs apply-progress.md claim

`apply-progress.md` §Files Changed reports:

> `web/index.html` | +216 | … `.fex-csv-table` + `.fex-csv-scroller`, `.fex-json-tree` + `.fex-tree-leaf.type-*`. No `<script>` tag for Papa.

And §Split into stacked PRs reports:

> PR2 — viewer tabs block | 474 LOC (86 file_explorer.js + 285 file_viewer.js + 103 index.html).

`git show 4dd8b91 --stat` (the actual PR2 commit) reports:

```
web/file_explorer.js |  99 ++++++++++++++++--
web/file_viewer.js   | 285 +++++++++++++++++++++++++++++++++++++++++++++++++++
2 files changed, 374 insertions(+), 10 deletions(-)
```

**`web/index.html` is NOT in the diff.** The +103 lines of CSS that
apply-progress claims for PR2 are **not in the commit** — only PR1's
+114-line CSS block (the search styles, lines 1426–1542 of
`web/index.html`) made it in.

The discrepancy is consistent with `apply-progress.md` §Staging Mechanics
which documents the manual hunk split: the staging for `web/index.html`
involved deleting the table/tree CSS, staging the remaining search CSS,
"then restoring the table/tree CSS from `/tmp/opencode/index_full.html`
so the unstaged diff contains only the commit-2 hunks." The restoration
step evidently did not survive the staging operation — when the commit
landed, the unstaged diff had not been re-included.

This is a **process defect** (the staging script lost hunks) and a
**product regression** (the users see unstyled tables / trees). The
functional logic is intact; the styling is missing.

## 7. Risks for PR2

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R-CSS-1 | Table/Tree CSS rules are missing — sticky thead, scrollable body, 16 px indent, type-coloured leaves all regress | **High** | Re-add the missing CSS block to `web/index.html`. Per `apply-progress.md` §Files Changed, the original was ~103 lines covering `.fex-csv-table`, `.fex-csv-scroller`, `.fex-json-tree`, `.fex-tree-leaf.type-{string,number,boolean,null}`, `.fex-json-children`, `.fex-tree-truncated`. Add as a single commit (or amend `4dd8b91` before PR2 is merged) — under 200 LOC, well within a single work-unit budget |
| R-CSS-2 | If the missing CSS lived elsewhere (e.g. an external stylesheet I haven't found), the regression assessment is wrong | Low | `rg -n "fex-csv-\|fex-json-\|fex-tree-leaf\|fex-tree-truncated"` across the whole repo returns ONLY matches in `web/file_viewer.js` — zero in any CSS source. Conclusion: the CSS is genuinely missing |
| R-TAB-1 | `handleTabClick` on a non-supported format short-circuits the renderer; spec says "AND no renderer error is thrown" — verified at file_explorer.js:1256 (`return` before `fileViewer.render()`) | Low | Spec contract met; no error path |
| R-JSON-1 | JSON > 50 000 nodes: spec says "AND the Raw tab still renders the full body". The current renderer paints a banner but does NOT auto-navigate to Raw | Low | One-click recovery (user clicks Raw tab). Could be polished to add a `<a href="#" data-raw-link>` later. Spec wording is "the Raw tab still renders" not "auto-opens"; the literal contract is met |
| R-JSON-2 | JSON tree falls back to `renderOfflineBanner` on parse error; the user sees "Viewer offline" copy for a malformed JSON file (not "invalid JSON") | Low | Same banner reuse as other CDN-failure paths; matches the design's "one banner covers all unrecoverable failures" approach |
| R-CSS-3 | `.fex-csv-table th` is set without explicit border-collapse or cell padding — without CSS, the table renders with browser defaults (cell-padding 0, no header bg). Functional but ugly | Low (resolved by R-CSS-1) | Same fix as R-CSS-1 |
| R-TSV-1 | The TSV `header` row treatment: when the TSV has no header row, Papa.parse still treats row 0 as header. The synthetic "Col N" header only kicks in if `headerRow` is empty (every cell empty/whitespace). For TSVs with a header row, the user's row 0 becomes the table header — matches CSV behaviour | Low | Acceptable per design §Decisions |
| R-PARSE-1 | Papa.parse `TooFewFields` / `TooManyFields` errors are silenced (not surfaced to banner) on the assumption they're benign. A user who genuinely has malformed data may not see an error | Low | The line-length heuristic catches most "real" errors first; benign row-length drift is the common noise |
| R-DEVPROC-1 | The staging script for split-PRs (apply-progress §Staging Mechanics) lost hunks for `web/index.html`. If the same pattern is reused for the fix commit, recommend using `git add -p` for the entire file rather than the delete-and-restore dance | Low | Process improvement; document in apply-progress.md follow-up |
| R-DEVPROC-2 | PR1 noted a similar CSS-finding deviation (apply-progress §Deviations — `--tertiary-container` token didn't exist, used `--surface-container-low` instead). PR2 inherits that same design-vs-actual gap (104 LOC of PR2 CSS was supposed to land); the design's exact selectors can't be applied if the design referenced non-existent tokens — the apply-phase should have flagged the token gap in design instead of silently substituting | Low | Design process improvement; surface token gaps at design time, not at apply time |

## 8. Verdict

**Status: FAIL.**

PR2's functional logic (Papa CDN load, CSV/TSV parsing, JSON tree
construction, tab dispatch with spec-conformant unsupported message,
50 000-node cap, raw/offline fallback) is correct and matches the spec.
The functional code paths are exercised by the existing pytest suite
without regression.

The PR is **not mergeable in its current form** because the spec's
visual contracts — sticky thead, scrollable body, 16 px indent,
type-coloured leaves, truncation banner styling — are unmet. The CSS
for these selectors (`.fex-csv-*`, `.fex-json-*`, `.fex-tree-leaf.*`,
`.fex-tree-truncated`) was never committed to `web/index.html`, despite
`apply-progress.md` claiming it was. The regression is unambiguous:
`git show 4dd8b91 --stat` lists only two files (file_explorer.js +
file_viewer.js), and `rg` across the entire `web/` tree confirms
zero CSS rules for these class names exist anywhere.

This is recoverable in a single small follow-up commit (re-add the
missing ~100 lines of CSS using the design's specifications, with the
R-CSS-2 token gap worked around as PR1 did). After that commit, the
spec matrices in §1 and §5 will read PASS.

**next_recommended**: **apply** (for the follow-up CSS-recovery commit
on a fix branch), not `archive`.

The follow-up commit must:

1. Add the missing CSS rules to `web/index.html`'s `<style>` block.
2. Re-run scenarios §4.6, §4.7, §4.9, §4.10, §4.11 of `tasks.md` in a
   browser (`make smoke`), confirming visually that sticky header,
   indent, colour tokens, and truncation work.
3. Update `apply-progress.md` to note the staging defect and the
   recovery commit, so the SDD audit trail captures the regression +
   fix pair.

Once the recovery commit lands and the visual hand-tests pass, the
verify-report can be re-issued with status PASS and `next_recommended`
flipped to `archive`.
