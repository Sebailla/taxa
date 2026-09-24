# Test cleanup — close the 12 pre-existing test failures on develop

## Objective

The Next.js migration to develop left **12 pre-existing test failures** that pre-date the ODD-ASN-001/002/003/004/005 work. The smoke tests that block PRs (the `Smoke tests` CI check on PRs to develop) only catch a subset of these. The full `pytest tests/` sweep reveals the rest. This branch closes them so `pytest tests/` returns 0 failures (modulo skips).

## Current failure list (post-merge of #382)

Source: `pytest tests/ --ignore=tests/test_smoke.py` on `develop` at commit `f02ed6e`.

| # | Test | File | Category |
|---|------|------|----------|
| 1 | `test_research_explorer_mount.py::test_dom_markers_present_in_rendered_taxonomy_page` | test_research_explorer_mount.py | Contract update (DOM markers migrated) |
| 2 | `test_search_categories.py::test_search_engines_grouped_by_category` | test_search_categories.py | Environment + contract (Playwright needs uvicorn) |
| 3 | `test_taxonomy_tree_source_persistence.py::test_main_route_empty_storage_first_render_starts_with_col` | test_taxonomy_tree_source_persistence.py | Contract update (selector hooks may have moved) |
| 4 | `test_taxonomy_tree_source_persistence.py::test_main_route_selector_click_persists_and_rehydrates_after_reload` | test_taxonomy_tree_source_persistence.py | Contract update (same as #3) |
| 5-12 | 8 failures in `test_web_toggle.py::*` (see below) | test_web_toggle.py | Legacy Playwright tests for `web/` mount |

The 8 `test_web_toggle.py` failures (all require `api_server` / `uvicorn`):

- `test_freshwater_view_isolates_to_root`
- `test_freshwater_view_expands_to_families`
- `test_search_tab_renders_with_14_links`
- `test_search_engines_rendered_as_button_grid`
- `test_kebab_menu_toggles_on_repeated_trigger_click`
- `test_view_details_reopens_detail_panel_after_close`
- `test_folder_tab_shows_open_and_copy_after_materialize`
- `test_open_in_finder_button_calls_endpoint`

## User decision

- Run the cleanup now as a separate feature branch (`feat/test-cleanup`).
- Do NOT touch P1/P2/P3 from the original critique in this branch — those are separate work streams (design-system extract, explorer search render-puro, etc.).
- Push + PR creation + merge remain the user's decisions.

## Strategy per failure

The strategy depends on what each test pins. The worker must investigate each failure before deciding the fix.

### Category A: Legacy Playwright tests for `web/` mount (8 tests in `test_web_toggle.py`)

The `web/` mount is no longer the production UI — `out/index.html` is. The legacy tests boot `uvicorn` + load `web/index.html` + drive Playwright. They were kept as a transition witness but the migration made them dead weight.

Strategy:

- **Read** each test + the `api_server` fixture + the `web/` directory.
- **Decide** per-test:
  - **Migrate** if the test's contract is still valuable and could be ported to the Next.js mount (e.g., `test_version_banner_shows_on_outdated_db` is valuable — check if it can be ported to test `out/index.html`'s version banner).
  - **Delete** if the test pins a legacy-only contract that has no parallel in the React mount (e.g., `test_kebab_menu_toggles_on_repeated_trigger_click` — kebab still exists in the React mount but the DOM hooks changed).
  - **Skip with a documented reason** if Playwright/chromium unavailable (current skip path).
- **Document** the per-test decision in this plan + a comment in the deleted/skip block explaining why.

### Category B: `test_research_explorer_mount.py::test_dom_markers_present_in_rendered_taxonomy_page`

Tests that the legacy DOM markers (e.g., `<div id="search-input">` — wait, that's still there per ODD-MIGRATE-007-DOM-006) appear in the rendered taxonomy page. The legacy `web/index.html` shipped 7 specific DOM markers; the React mount reproduces them via ODD-MIGRATE-007-DOM-006 in `src/app/page.tsx` and `src/modules/taxonomy/presentation/TaxonomyTree.tsx`.

Strategy:

- **Read** the test + the ODD-MIGRATE-007-DOM-006 marker contract (look at `odd/tasks/g4-integration-delivery.md` or the relevant docblock in `TaxonomyTree.tsx`).
- **Determine** which marker is missing (the test failure message identifies the line).
- **Fix** by:
  - If the marker is supposed to be present per the ODD-MIGRATE-007 contract but is missing in the implementation: add it.
  - If the marker was a legacy contract that's been retired (e.g., superseded by the new ODD-ASN-002 search-input lift): update the test to assert the new contract (the input now lives in `AppShellGlobalSearch.tsx`).

### Category C: `test_search_categories.py::test_search_engines_grouped_by_category`

The docstring says "Browser-level tests for the category grouping of search engines (P1 #3 from the Impeccable critique)". This is the P1 from the critique that the user explicitly deferred (the user chose "sólo P0" for #382; design-system extract is the next P1).

Strategy:

- **Read** the test + the implementation in `src/modules/taxonomy/presentation/search-categories.ts` + `src/modules/taxonomy/presentation/SearchTab.tsx`.
- **Determine** if the test fails because:
  - The test environment lacks uvicorn (`api_server` fixture) — fix by adding a skip or a static-export alternative.
  - The grouping logic isn't implemented yet (the P1 itself is unimplemented) — fix by implementing the P1 OR by adding a `pytest.mark.xfail` / `pytest.skip` until the P1 lands.
  - The grouping IS implemented but the DOM contract is wrong — fix the contract.

Given the user deferred the P1 to a follow-up cycle, the right fix is likely to **mark the test as `pytest.mark.xfail(reason="P1 deferred; see critique 2026-09-23")` + add a static-export-friendly pre-check** so the CI knows the contract is documented but not yet enforced. Alternatively, **delete the test** until the P1 lands. Pick whichever the worker thinks cleaner after reading the test.

### Category D: `test_taxonomy_tree_source_persistence.py` (2 tests)

Both tests use `static_export` (no uvicorn needed) + Playwright. They pin the source-selector's DOM hooks (`data-tree-source="worms"`, `data-active-source`, `aria-pressed`) and the localStorage persistence contract.

Strategy:

- **Read** the 2 tests + the source-selector implementation in `src/modules/taxonomy/presentation/TaxonomyTree.tsx` (look for the `data-tree-source-toggle` host + the per-button `data-tree-source` / `aria-pressed` stamps).
- **Determine** if the contract changed (likely the ODD-ASN-002 AppShell rebuild moved the source selector OR kept it where it was — the worker must check).
- **Fix** by:
  - Updating the test to assert the current selector DOM hooks (if the React mount still exposes them, the test just needs the new selectors).
  - Updating the implementation to re-expose the legacy hooks (if the React mount dropped them — only do this if the hooks are still semantically valid).
  - Deleting the test if the source selector moved out of the taxonomy tree (per the user's earlier decision on "Mover a AppShell" — but wait, the user actually chose "Mover a AppShell (global)" for the SEARCH INPUT, not the source selector. Re-read `odd/tasks/app-shell-navigation-rebuild.md` ODD-ASN-002 — the source selector stayed in TaxonomyTree. The failure is likely a stale contract).

## TDD discipline

1. **FIRST** run each failing test individually to capture the RED error message. The error message identifies which assertion failed (e.g., "Element not found", "expected 'worms' but got None", "page.wait_for_selector timed out"). The worker MUST read the message before fixing.
2. **THEN** read the test source + the implementation source + any linked docs (e.g., the ODD-MIGRATE-007-DOM-006 marker contract) to understand the contract.
3. **THEN** decide: migrate / update contract / delete / skip.
4. **THEN** apply the fix.
5. **THEN** re-run the test → GREEN.
6. **REPEAT** for each of the 12 failures.
7. **FINAL** full sweep: `pytest tests/ --ignore=tests/test_smoke.py 2>&1 | tail -3` → 0 failures (modulo skips).

## Constraints

- DO NOT modify any implementation file (`src/**`) in this branch. The cleanup is test-only. If a test fails because the implementation has a bug, the worker MUST report it (out of scope for this PR) rather than fix it.
- DO NOT touch `tests/test_app_shell_render.py` / `tests/test_visible_taxonomy_tree.py` / `tests/test_hydration_console.py` / `tests/test_browser_state_keys.py` / `tests/test_research_styles.py` / `tests/test_search_engine_consumer_manifest.py` (already touched in PR #382).
- DO NOT touch `tests/test_smoke.py` (excluded from the sweep; CI uses a different filter).
- DO NOT add new dependencies. The fixes use what's already installed.
- The `pi-lens` automated check that fired 4 advisories during plan creation is informational only — those are `python-no-print` + `python-unsafe-regex` warnings on existing tests, no blockers.

## Allowed edit surfaces

tests/test_web_toggle.py
tests/test_research_explorer_mount.py
tests/test_search_categories.py
tests/test_taxonomy_tree_source_persistence.py

(No implementation files; no docs; no plan files.)

## Test plan

Per-category expectations after the work:

- **`test_web_toggle.py`**: 8 failures resolved (either migrated, deleted, or skipped with documented reason). Net file length may decrease.
- **`test_research_explorer_mount.py`**: 1 failure resolved (DOM marker contract updated to match the React mount's actual markup).
- **`test_search_categories.py`**: 1 failure resolved (either marked xfail with reason, deleted, or made static-export-compatible).
- **`test_taxonomy_tree_source_persistence.py`**: 2 failures resolved (selector DOM hooks updated to match the React mount's current implementation).

## Acceptance criteria

- `pytest tests/ --ignore=tests/test_smoke.py 2>&1 | tail -3` → 0 failed (modulo skips).
- `pytest tests/test_app_shell_render.py tests/test_visible_taxonomy_tree.py tests/test_hydration_console.py tests/test_browser_state_keys.py tests/test_research_styles.py tests/test_search_engine_consumer_manifest.py 2>&1 | tail -3` → 0 failed (regression sweep for the PR #382 contracts).
- `npx --no-install next build` → exit 0 (no implementation changes means the build should be byte-identical to PR #382's build).
- No new warnings introduced; existing warnings preserved.

## Risks + follow-ups (out of scope)

- The 13 → 12 pre-existing test failures count varies between sweep runs (CI smoke filter vs full sweep). The cleanup targets the 12 visible in the full sweep on develop at commit `f02ed6e`.
- If the worker determines that a test should be migrated rather than deleted, the migration MUST be documented in this plan + a comment in the test file explaining what changed.
- The P1 from the original critique (search-tab grouped engines) is explicitly deferred per the user's earlier decision. If the worker decides to implement it as part of this cleanup, they MUST get explicit user approval first.
- The 5 newly unused exports flagged by `pi-lens` in `src/modules/browser-state/index.ts` (storage keys) are intentional public barrel surface for cross-module consumers — the worker MUST NOT remove them.

## Rollback

If anything fails or you need to abandon the change, run `git restore tests/test_web_toggle.py tests/test_research_explorer_mount.py tests/test_search_categories.py tests/test_taxonomy_tree_source_persistence.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.