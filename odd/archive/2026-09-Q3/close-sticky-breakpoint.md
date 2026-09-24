# Close P2 — Detail panel sticky-breakpoint responsive fix

## Objective

Close one of the remaining P2 items from the 2026-09-23T18-52-32Z re-critique: **"Detail panel `position: sticky top: 144px` breaks under 800px"**.

`globals.css:423-424` pins `.detail-panel { position: sticky; top: 144px; z-index: 30; }`. At viewports below ~800px the sticky offset eats the visible tree (the tree header + breadcrumb + source selector consume the first 144px, then the detail panel sticks). Users on 13" laptops see tree rows slide under the panel; tablet users see the panel consume half the viewport; phone users see the panel eat the entire tree.

The fix: add a single responsive breakpoint at `< md` (`@media (max-width: 768px)`) that flips `.detail-panel` from `position: sticky` to in-flow (`position: static`). The tree and panel stack vertically below the breakpoint.

## User decision

- Continue with "Pendientes restantes" — pick the smallest bounded one first.
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/app/globals.css`

Add a `@media (max-width: 768px) { .detail-panel { position: static; ... } }` rule. The rule must come AFTER the existing `.detail-panel` rule (CSS source order determines cascade specificity when both selectors are the same specificity).

The responsive rule should also flip the related `.detail-card` (if it has any max-height) and `.detail-header` (which has `position: sticky` for the in-card sticky header — should also flip to static at the same breakpoint).

Verify the rule is in alphabetic order within the @media block (the alphabetical-order test from `tests/test_research_styles.py::test_top_level_selectors_are_alphabetically_ordered` checks top-level selectors, but the new selectors inside `@media` also need to be alphabetical — verify).

### Tests

Update existing tests in `tests/test_visible_taxonomy_tree.py`:
- The tests that pin the `.detail-panel { position: sticky; top: 144px; z-index: 30; }` rule must NOT break (the sticky behavior stays for ≥ md viewports).

Add new tests:
- `test_detail_panel_below_md_is_static` (source-level: assert the `@media (max-width: 768px) { .detail-panel { position: static; ... } }` rule exists in `globals.css`).
- `test_detail_panel_above_md_remains_sticky` (regression guard: the existing sticky behavior for ≥ md viewports stays).

### Other consumers

`globals.css:423-424` is in the `@layer components` block. The responsive rule goes in the same block (after the existing `.detail-panel` rule). The chain-topology test (`tests/test_research_styles.py::test_layer_components_research_chrome_block_does_not_leak_taxonomy`) checks that no taxonomy selector leaks into the research/chrome block. The new rule uses the `.detail-panel` selector which is already in the research/chrome block — no leak.

## Non-goals

- Migrating other consumers.
- Removing the `.fex-*` cascade.
- The 8 Playwright follow-up failures from PR #386 — separate follow-up PR.
- Other P1/P2/P3 from the re-critique (separate branches).

## TDD discipline

1. **FIRST**, add the new tests asserting the responsive rule exists.
2. **THEN**, add the `@media` rule to `globals.css`.
3. **THEN**, re-run the tests → GREEN.
4. **THEN**, run the FULL regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 / #392 / #393 / #394 protected test files → 0 failed.
5. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 / #392 / #393 / #394 protected test files.
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.
- The alphabetical-order test (`tests/test_research_styles.py::test_top_level_selectors_are_alphabetically_ordered`) MUST stay green — verify the new selectors inside `@media` are in alphabetical order.

## Allowed edit surfaces

src/app/globals.css
tests/test_visible_taxonomy_tree.py

## What to return

- The RED → GREEN transition for each new test.
- The full regression + full sweep outputs.
- The `npx next build` exit code + route table.
- The `git diff --check` output.
- A list of every file you created or edited, with the line count delta.
- Any test failures or warnings encountered, with a one-sentence reason.

Do NOT commit.

## Runtime harness

Use `.venv/bin/python -m pytest` for Python tests and `npx --no-install next build` for the static export. Both run from `/Users/sebailla/Developer/taxa`. Build allowed up to 300s; tests should complete in under 60s for the targeted sweep.

## Rollback

If anything fails, run `git restore src/app/globals.css tests/test_visible_taxonomy_tree.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.