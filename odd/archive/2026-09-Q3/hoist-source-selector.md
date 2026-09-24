# Close P2 — Hoist source-selector to AppShell

## Objective

Close one of the remaining P2 items from the 2026-09-23T18-52-32Z re-critique: **"Source-selector is still buried inside the tree section"**.

`src/modules/taxonomy/presentation/TaxonomyTree.tsx:2214-2223` renders the `.tree-source-toggle` only after roots load (after `state.rootIds.length > 0`). The first-time user has expanded the tree, seen root rows, and noticed the segmented control. The selector is no longer "above the visible chrome" — a user who has never used the product does not see the three data sources (CoL / WoRMS / Freshwater) until they look at the tree.

The fix: hoist the source-selector to the AppShell header so it's visible on every route (and on every surface — even on `/explorer` where it's not relevant today). PRODUCT.md treats CoL / WoRMS / Freshwater as a first-class concept worth a legend in `/help`; the selector should be visible on every route.

## User decision

- Continue with "Pendientes restantes" — hoist source-selector.
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/app-shell/presentation/AppShell.tsx` (+ `AppShellHeader.tsx`)

Add the source-selector to the AppShell header (above the search input, OR below the search input — pick the placement that doesn't break the layout).

The selector has 3 options (CoL / WoRMS / Freshwater) + the conditional Freshwater appearance (only when the fetched root payload exposes a row with `freshwater_id != null`).

Props the AppShell needs to pass to the header → selector:
- `freshwaterRootId: number | null` (passed from `HomeClient` or `Explorer` — wherever the AppShell is mounted)
- `activeSource: TreeSource` (passed from `HomeClient` which currently owns the lifted state)
- `onSourceChange: (next: TreeSource) => void` (passed from `HomeClient`)

The current source-selector lives in `src/modules/taxonomy/presentation/TaxonomyTree.tsx` and uses `useTreeSource()` from `@taxa/browser-state/tree-source`. Hoisting it to the AppShell means the AppShell reads `useTreeSource()` + `useTreeSource().freshwaterRootId()` (or the equivalent) and renders the selector.

### `src/modules/taxonomy/presentation/TaxonomyTree.tsx`

REMOVE the source-selector from inside `TaxonomyTree`. Keep the `data-tree-source-toggle=""` + the per-button `data-tree-source="col|worms|freshwater"` attributes IF the AppShell selector preserves them (for tests + a11y contract).

### `src/modules/research/presentation/Explorer.tsx`

The Explorer doesn't currently use the source-selector (it has its own dedicated file search). No changes needed UNLESS we want to expose the source-selector on the Explorer route too (the plan says "visible on every route" — that means `/`, `/explorer`, `/help`, `/settings`).

For Phase 1 of this PR, focus on `/` only (where the selector is currently buried). The other routes can show a disabled selector OR a "Coming soon" note (Phase 2 work).

### `src/app/globals.css`

The `.tree-source-toggle` + `.tree-source-toggle-wrapper` + `.tree-source-btn` + `.tree-source-btn.active` CSS rules in globals.css are still load-bearing (the AppShell selector uses the same classes). Verify by grep + no removal needed.

### Tests (in `tests/test_visible_taxonomy_tree.py`)

Update existing tests:
- The test that pins the source-selector inside `TaxonomyTree.tsx` (likely `test_taxonomy_tree_renders_source_selector`) — UPDATE: assert the selector is NOT inside `TaxonomyTree.tsx` (it's now in `AppShell.tsx` / `AppShellHeader.tsx`).
- Add new tests:
  - `test_appshell_renders_source_selector` (asserts the AppShell renders the `.tree-source-toggle` with the 3 buttons + `data-tree-source="col|worms|freshwater"` + `data-active-source` + `aria-pressed`).
  - `test_taxonomy_tree_does_not_render_source_selector` (regression guard).

## Non-goals

- Wiring the source-selector on `/explorer` (Phase 2 — the explorer is independent).
- The 8 Playwright follow-up failures from PR #386 — separate follow-up PR.
- The Explorer search DOM-mutation → render-puro (P1 grande — separate PR).

## TDD discipline

1. **FIRST**, update existing tests for the source-selector migration.
2. **THEN**, hoist the source-selector to the AppShell header.
3. **THEN**, remove the source-selector from `TaxonomyTree.tsx`.
4. **THEN**, re-run the tests → GREEN.
5. **THEN**, run the FULL regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 / #392 / #393 / #394 / #395 protected test files → 0 failed.
6. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 / #392 / #393 / #394 / #395 protected test files.
- The data attributes (`data-tree-source-toggle=""`, `data-tree-source="col|worms|freshwater"`, `data-active-source`, `aria-pressed`) MUST stay (the AppShell selector preserves them).
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/modules/app-shell/presentation/AppShell.tsx
src/modules/app-shell/presentation/AppShellHeader.tsx
src/modules/taxonomy/presentation/TaxonomyTree.tsx
src/app/globals.css
tests/test_visible_taxonomy_tree.py
tests/test_app_shell_render.py

## What to return

- The RED → GREEN transition for each updated test.
- The full regression + full sweep outputs.
- The `npx next build` exit code + route table.
- The `git diff --check` output.
- A list of every file you created or edited, with the line count delta.
- Any test failures or warnings encountered, with a one-sentence reason.

Do NOT commit.

## Runtime harness

Use `.venv/bin/python -m pytest` for Python tests and `npx --no-install next build` for the static export. Both run from `/Users/sebailla/Developer/taxa`. Build allowed up to 300s; tests should complete in under 60s for the targeted sweep.

## Rollback

If anything fails, run `git restore src/modules/app-shell/presentation/AppShell.tsx src/modules/app-shell/presentation/AppShellHeader.tsx src/modules/taxonomy/presentation/TaxonomyTree.tsx src/app/globals.css tests/test_visible_taxonomy_tree.py tests/test_app_shell_render.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.