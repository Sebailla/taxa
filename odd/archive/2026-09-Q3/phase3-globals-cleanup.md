# Phase 3 — globals.css cleanup after design-system extract

## Objective

After Phase 1 (PR #385, design-system foundation) + Phase 2 (PRs #386-#391, consumer migrations), the shared CSS surface in `src/app/globals.css` (2,800+ lines) may have rules that are no longer referenced. Phase 3 audits the cascade + removes the rules that are confirmed dead (zero non-comment references in `src/` after the Phase 2 migrations).

The honest scope: most `.fex-*` rules STAY (specialized Explorer panel states + Viewer panel states + FileTree specialized patterns all use them). Only the rules that have ZERO references get removed.

## User decision

- Phase 3 is the final cleanup of the design-system extract.
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/app/globals.css` (1 file, ~2,800 lines)

The worker must:

1. **Audit** every rule in `@layer components` block (the main consumer-facing cascade) for dead references.
2. **Run `grep -rE`** across `src/` for each rule's selector to confirm zero references remain.
3. **Remove** rules with zero references.
4. **KEEP** rules with active references.
5. **Document** the audit results in the PR body (which rules were removed + which were kept + why).

The worker should NOT proactively remove `.rank-badge` + `.authorship` + `.fex-*` if they have active references. The previous Phase 2 plans kept these rules because they were still consumed (DetailPanel uses `.rank-badge`, SynonymTab uses `.authorship`, Explorer.tsx + Viewer.tsx use `.fex-*` heavily).

The expected outcome:
- Some `.app-shell-*` rules may be removable (Phase 2 AppShell migration didn't change the AppShell sub-components, but the rules are still load-bearing).
- `.rank-badge` — likely KEEP (DetailPanel.tsx still uses it as an inline class fallback).
- `.authorship` — likely KEEP (SynonymTab.tsx still uses it).
- `.fex-*` rules — most KEEP (Explorer + Viewer + FileTree specialized patterns).
- The dead rules are the few that the Phase 2 migrations removed their consumers for (the 14+ rules removed across PRs #386-#390).

If the worker finds that NO additional rules are dead (i.e. all remaining rules have active references), the PR body should document the audit findings + ship a no-op commit that just records the audit. The Phase 2 PRs already removed the dead rules.

### Tests (in `tests/test_research_styles.py` + other test files)

Tests that pin the globals.css cascade:
- `tests/test_research_styles.py::test_layer_components_declares_every_research_chrome_selector` — asserts specific selectors exist in `@layer components`. The whitelist may need updating if any of the dead rules WERE pinned by this test.
- `tests/test_research_styles.py::test_layer_components_research_chrome_block_does_not_leak_taxonomy` — asserts no taxonomy selectors leak into the research/chrome block.
- `tests/test_research_styles.py::test_top_level_selectors_are_alphabetically_ordered` — asserts alphabetical order.
- `tests/test_globals_css_declares_folder_tab_selectors` (in `test_visible_taxonomy_tree.py`) — asserts specific selectors exist.
- `tests/test_globals_css_declares_detail_panel_overview_selectors` (in `test_visible_taxonomy_tree.py`) — asserts specific selectors exist.

If any of these tests pin selectors that are now dead, update them to remove the dead selectors from the whitelist + assert they MUST NOT reappear.

### Tests (new — audit documentation)

Add new tests that document the Phase 3 audit:
- `test_globals_css_no_dead_research_chrome_selectors` (asserts every `@layer components` rule has at least one non-comment reference in `src/`).
- `test_globals_css_phase3_audit_documents_kept_selectors` (asserts the rules kept — `.rank-badge` + `.authorship` + the still-referenced `.fex-*` rules — all have active references).

## Non-goals

- Migrating more consumers (Phase 2 is complete).
- Removing the `.fex-*` cascade wholesale (most `.fex-*` rules are still load-bearing; only the few that became dead get removed).
- The 8 Playwright follow-up failures from PR #386 — separate follow-up PR.

## TDD discipline

1. **FIRST**, run `grep -rE` across `src/` for every `@layer components` selector. Identify the dead ones.
2. **THEN**, update any tests that pin the dead selectors (the whitelist tests in `test_research_styles.py` + `test_visible_taxonomy_tree.py`).
3. **THEN**, remove the dead rules from globals.css.
4. **THEN**, add the Phase 3 audit documentation tests.
5. **THEN**, run the FULL regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 protected test files → 0 failed.
6. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 protected test files.
- DO NOT remove rules that have active references (run `grep -rE` first).
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/app/globals.css
tests/test_research_styles.py
tests/test_visible_taxonomy_tree.py

## What to return

- The audit results: per-rule summary of what was inspected + what was dead (removed) + what was kept.
- The `grep -rE` evidence for each dead rule (zero non-comment references in `src/`).
- The full regression + full sweep outputs.
- The `npx next build` exit code + route table.
- The `git diff --check` output.
- A list of every file you created or edited, with the line count delta.
- A list of every globals.css rule you removed (or the audit-only no-op if nothing was dead).
- Any test failures or warnings encountered, with a one-sentence reason.

Do NOT commit.

## Runtime harness

Use `.venv/bin/python -m pytest` for Python tests and `npx --no-install next build` for the static export. Both run from `/Users/sebailla/Developer/taxa`. Build allowed up to 300s; tests should complete in under 60s for the targeted sweep.

## Rollback

If anything fails, run `git restore src/app/globals.css tests/test_research_styles.py tests/test_visible_taxonomy_tree.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.