# Close P1 — AppShell duplicate skip-link

## Objective

Close one of the remaining P1 items from the 2026-09-23T18-52-32Z re-critique: **"Skip-to-main link is rendered twice on AppShell-mounted routes"**.

`src/app/layout.tsx:108-117` AND `src/modules/app-shell/presentation/AppShell.tsx:64-73` both render `<a href="#main">Skip to main content</a>` as the first focusable element on every route mounted under AppShell (`/`, `/explorer`, `/help`, `/settings`, `/_not-found`). A screen-reader user tabbing through the page lands on "Skip to main content" twice. The disambiguating `data-app-shell-skip-link-layout=""` attribute is invisible to assistive tech.

The fix: remove the AppShell duplicate. The layout's link is sufficient — the layout always pins the link in advance (every route inherits from the root layout).

## User decision

- The user authorized "Pendientes del critique" — attack the remaining P1/P2/P3 items. Starting with the smallest: AppShell duplicate skip-link.
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/app-shell/presentation/AppShell.tsx`

Remove the AppShell duplicate skip-link (lines 64-73 of the current file per the original re-critique). Keep the layout's skip-link (`src/app/layout.tsx:108-117`).

The AppShell comment block ("ODD-ASN-002 — skip-to-main link. The layout MUST render its own skip-link at the top of every route; this in-Shell duplicate was authored 'to cover the edge case where the layout does not pin the link in advance' — but the edge case doesn't exist.") becomes obsolete; remove or update it.

### `tests/test_app_shell_render.py`

Update the test that asserts the skip-link exists in BOTH layout AND AppShell:
- `test_app_shell_has_skip_to_main` (or whatever the test is named) — assert the skip-link exists in `src/app/layout.tsx` (NOT in `src/modules/app-shell/presentation/AppShell.tsx`).
- Add a negative-witness test: assert `AppShell.tsx` does NOT render its own skip-link (the `<a href="#main">` is not present in the AppShell JSX).
- Verify the layout skip-link still exists.

### `src/app/globals.css` (if needed)

The `.app-shell-skip-link` class lives in globals.css (used by the removed AppShell skip-link). Check with `grep -rE` whether any other consumer uses it. If zero references remain, remove the rule.

### Tests (new — for the contract)

Add a new test in `tests/test_app_shell_render.py`:
- `test_app_shell_does_not_render_duplicate_skip_to_main` (negative-witness that the AppShell JSX does NOT contain `<a href="#main">`).

## Non-goals

- Removing other AppShell duplicates or adding other a11y improvements (Phase 3).
- Migrating other consumers (already complete).
- Removing the `.fex-*` cascade (Phase 3 complete).
- The 8 Playwright follow-up failures from PR #386 — separate follow-up PR.

## TDD discipline

1. **FIRST**, update the affected test to assert the AppShell does NOT render the skip-link.
2. **THEN**, remove the duplicate skip-link from AppShell.tsx.
3. **THEN**, re-run the test → GREEN.
4. **THEN**, run the FULL regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 / #392 / #393 protected test files → 0 failed.
5. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 / #392 / #393 protected test files.
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/modules/app-shell/presentation/AppShell.tsx
src/app/globals.css
tests/test_app_shell_render.py

## What to return

- The RED → GREEN transition for each updated test.
- The full regression + full sweep outputs.
- The `npx next build` exit code + route table.
- The `git diff --check` output.
- A list of every file you created or edited, with the line count delta.
- Any globals.css rule you removed (or the audit-only no-op if nothing was dead).
- Any test failures or warnings encountered, with a one-sentence reason.

Do NOT commit.

## Runtime harness

Use `.venv/bin/python -m pytest` for Python tests and `npx --no-install next build` for the static export. Both run from `/Users/sebailla/Developer/taxa`. Build allowed up to 300s; tests should complete in under 60s for the targeted sweep.

## Rollback

If anything fails, run `git restore src/modules/app-shell/presentation/AppShell.tsx src/app/globals.css tests/test_app_shell_render.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.