# Phase 2 — DetailPanel migrate to design-system primitives

## Objective

Second consumer migration in Phase 2 of the design-system extract (post-PR #385). Migrate `DetailPanel.tsx` to use `Badge`, `Card`, `IconButton`, `Text` from `@taxa/design-system`. The panel itself (sticky + scrollable + max-height) stays — too specialized to be a generic Card variant. The inner elements migrate.

`DetailPanel.tsx` is 587 lines (`"use client"`). It renders the native-style selected-taxon panel:
- `.detail-panel` (sticky wrapper — STAYS as a specialized class; not a generic card pattern)
- `.detail-card` (inner card with `border-radius + background + overflow + max-height` — migrates to `<Card variant="default">` + className for the max-height)
- `.detail-header` (sticky header inside the scrollable card — STAYS, but its inner badges migrate)
- `.tab-strip` + 6 tabs (Overview + Search + Folder + Vernaculars + Synonyms + Distribution)
- Body sections (overview grid + parent chain + status indicators)

The migration closes one half of the original P1 from the 2026-09-23 critique + enables Phase 3 cleanup of `.rank-badge` + other DetailPanel-specific CSS rules.

## User decision

- DetailPanel is the second Phase 2 consumer (uses 4 of 8 primitives: Badge + Card + IconButton + Text).
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/taxonomy/presentation/DetailPanel.tsx` (JSX rewrite + helper consolidation)

- **Import from `@taxa/design-system`**: `Badge`, `Card`, `IconButton`, `Text` (4 of 8 primitives).
- Replace inline `<span className="rank-badge ...">` (rank + status + extinct + CoL-only + WoRMS badges in the header) with `<Badge>`:
  - `rank-badge` → `<Badge variant="subtle" uppercase={true}>` (the rank label)
  - `text-primary bg-primary/10` → `<Badge variant="primary" uppercase={true}>` (the rank label, primary variant for emphasis)
  - `text-red-700 bg-red-50` → `<Badge variant="warning" uppercase={true}>` (the extinct marker)
  - `text-on-surface-variant bg-surface-container-highest` → `<Badge variant="subtle" uppercase={true}>` (the status badge)
- Replace the close `<button>` with `<IconButton variant="subtle" aria-label="Hide details">close</IconButton>` (Material Symbols `close` glyph).
- Replace inline `<div className="detail-card ...">` with `<Card variant="default" className="overflow-hidden h-auto max-h-[calc(90vh-2px)] rounded-2xl">`.
- Keep `.detail-panel` (the sticky wrapper) and `.detail-header` (the sticky header) — too specialized for the generic Card primitive.
- Replace the overview grid inline typography with `<Text>`:
  - `dl.overview-grid dd.overview-value` (the value column) → `<Text variant="body">`
  - `dt.overview-label` → `<Text variant="caption">`
  - The `.overview-chain-segment` `<button>` → keeps the `<button>` (it has special styling for the italic/roman name); BUT can wrap in `<Text>` for the typography if helpful.
- Keep the `<Fragment>` + `renderChain` helper for the parent chain (special case).
- Keep the `.tab-strip` + 6 `<button className="tab-button">` elements (tab-strip is a specialized control pattern, not a generic Card variant).
- Keep the `renderOverview` helper structure (it's already cleanly factored).
- Keep all the data attributes (`data-detail-panel`, `data-detail-panel-source`, `data-detail-panel-tab`, `data-realm`, `data-detail-extinct`, `data-detail-source-badge`, `data-detail-title`, `data-detail-authorship`, `data-detail-tab-strip`, `data-tab`, `data-tab-content`, `data-detail-overview-rank`, `data-detail-overview-grid`, `data-detail-overview-field`, `data-detail-overview-row`, `data-detail-chain-segment`, `data-detail-chain-rank`, `data-action="close-detail"`, `data-action="focus-segment"`) — other tests + the parent `TaxonomyTree` depend on these.
- Keep the `aria-pressed`, `aria-disabled`, `aria-controls`, `role="tablist"`, `role="tab"` a11y attributes — the existing test contracts pin them.
- Keep the `data-test-value` attributes on the overview grid items (used by `tests/test_visible_taxonomy_tree.py::test_detail_overview_renders_for_top_level_taxon_without_data` and other tests).

### `src/app/globals.css` — REMOVE rules that DetailPanel no longer uses after the JSX rewrite

After the JSX rewrite, these rules become dead:
- `.rank-badge` (the standalone rule — used only by DetailPanel post-Phase 2; TreeRow now uses `<Badge variant="subtle">` which uses its own classes; this rule was the one DetailPanel was using all along — REMOVE)
- `.authorship` (used in `.detail-header-authorship` — used by DetailPanel only; if DetailPanel's authorship `<p>` uses inline Tailwind classes, REMOVE this rule)
- `.overview-tab .overview-grid dd.overview-value` typography → replaced by `<Text variant="body">` which uses Tailwind utilities; the `.overview-value` class is dead.
- `.overview-tab .overview-rank` → replaced by `<Badge variant="primary">`; the `.overview-rank` class is dead.
- `.overview-tab dt.overview-label` → replaced by `<Text variant="caption">`; the `.overview-label` class is dead.

CRITICAL: run `grep -rE` across `src/` BEFORE removing each rule to confirm zero references remain after the JSX rewrite. If any rule still has references (e.g. in another consumer), do NOT remove it.

**KEEP** these rules (still have references):
- `.detail-panel` (the sticky wrapper — STAYS as a specialized class)
- `.detail-panel .detail-card` (the wrapper inside the detail-panel) — wait, if we replace `.detail-card` with `<Card variant="default">`, this rule becomes dead. Need to verify.
- `.detail-header` + `.detail-header-title` (the sticky header) — STAYS as a specialized class
- `.detail-section` (the scrollable body sections) — STAYS
- `.tab-strip` + `.tab-button` + `.tab-button.active` (the tab strip + tabs) — STAYS
- `.tab-strip > .tab-button[aria-disabled="true"]` (disabled tabs) — STAYS
- `.detail-panel[data-realm="..."] .scientific-name` (the realm tint cascade) — STAYS
- `.detail-close` (the close button styles) — if we replace with `<IconButton variant="subtle">`, this rule becomes dead (but the IconButton primitive uses its own classes)

The worker MUST run a `grep -rE` across `src/` BEFORE removing any rule to confirm zero references remain after the JSX rewrite.

### Tests (in `tests/test_visible_taxonomy_tree.py`)

Tests that pin the pre-migration DetailPanel composition:
- `test_detail_panel_file_exists` — keep (file still exists).
- `test_detail_panel_is_a_client_component` — keep (still true; `"use client"` stays).
- `test_detail_panel_uses_canonical_helpers` — keep.
- `test_detail_panel_emits_native_overview_identity` — keep (still true; rank + name + authorship + status + extinct + count).
- `test_detail_panel_emits_native_source_affordances` — keep.
- `test_detail_panel_emits_extinct_treatment` — UPDATE: the extinct marker is now `<Badge variant="warning">` instead of `<span className="rank-badge text-red-700 bg-red-50">`. Change the assertion to check for the Badge primitive OR check for the visual treatment (red-700 text + red-50 bg).
- `test_detail_panel_stamps_data_realm_attribute` — keep.
- `test_detail_panel_emits_tab_strip_with_six_tabs` — keep (the 6 tabs are unchanged).
- `test_detail_panel_disables_unavailable_tabs` — keep.
- `test_detail_panel_enables_search_tab` — keep.
- `test_detail_panel_renders_search_tab_when_active` — keep.
- `test_detail_panel_renders_close_button` — UPDATE: the close button is now `<IconButton variant="subtle" aria-label="Hide details">close</IconButton>`. Update the assertion to check for the IconButton primitive OR check for `aria-label="Hide details"`.
- `test_detail_panel_chain_segment_routes_to_breadcrumb_handler` — keep.
- `test_detail_panel_threads_folder_callbacks` — keep.
- `test_detail_overview_renders_for_top_level_taxon_without_data` — keep (the overview grid still renders; the `<Text>` primitive replaces the inline typography).
- `test_globals_css_declares_detail_panel_overview_selectors` — UPDATE: some selectors are gone (`.rank-badge`, `.overview-value`, `.overview-rank`, `.overview-label`, `.authorship`). Either remove this test or update it to assert the surviving selectors (`.detail-panel`, `.detail-header`, `.tab-strip`, etc.).
- `test_out_index_html_has_detail_panel_overview_styles` — UPDATE: same as above (some selectors gone).

### Tests (new in `tests/test_visible_taxonomy_tree.py` for Phase 2 coverage)

Add new tests:
- `test_detail_panel_uses_card_primitive_for_detail_card` — asserts `<Card variant="default" className="... overflow-hidden ...">` is used.
- `test_detail_panel_uses_badge_primitive_for_rank` — asserts `<Badge variant="primary" uppercase={true}>` is used for the rank.
- `test_detail_panel_uses_badge_primitive_for_status` — asserts `<Badge variant="subtle" uppercase={true}>` is used for the status.
- `test_detail_panel_uses_badge_primitive_for_extinct` — asserts `<Badge variant="warning" uppercase={true}>` is used for the extinct marker.
- `test_detail_panel_uses_iconbutton_primitive_for_close` — asserts `<IconButton variant="subtle" aria-label="Hide details">close</IconButton>` is used.
- `test_detail_panel_uses_text_primitive_for_overview_labels` — asserts `<Text variant="caption">` is used for `dt.overview-label`.
- `test_detail_panel_no_inline_rank_badge_span` — asserts the old `<span className="rank-badge ...">` is gone.
- `test_detail_panel_no_inline_overview_value_class` — asserts the old `dd.overview-value` class is gone.

## Non-goals

- Migrating other Phase 2 consumers (`AppShell`, `Explorer`, `Splitter`, `FileTree`, `Viewer`, `FolderTab`) — separate branches.
- Removing the `.fex-*` cascade (Phase 3 once no consumer uses it).
- Wiring the global search input to the explorer's file search (original P1 from the critique; out of scope).
- The 8 Playwright follow-up failures from PR #386 (test_web_toggle.py + test_search_categories.py + test_detail_overview.py) — separate follow-up PR.

## TDD discipline

1. **FIRST**, the worker updates the affected tests in `tests/test_visible_taxonomy_tree.py` (the list above). Run the tests — they should fail with the OLD assertions (because the implementation hasn't changed yet).
2. **THEN**, ship the JSX rewrite + the globals.css cleanup.
3. **THEN**, re-run the updated tests → GREEN.
4. **THEN**, add the 8 new Phase 2 coverage tests (the list above).
5. **THEN**, run the FULL regression sweep on PR #382 + #384 + #385 + #386 protected test files → 0 failed.
6. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 protected test files (`test_app_shell_render.py`, `test_hydration_console.py`, `test_browser_state_keys.py`, `test_research_styles.py`, `test_search_engine_consumer_manifest.py`, `test_design_system_primitives.py`, `test_smoke.py`, `test_web_toggle.py`, `test_search_categories.py`, `test_detail_overview.py`).
- The new `<Badge>` / `<Card>` / `<IconButton>` / `<Text>` primitives must be imported from `@taxa/design-system` (the public barrel).
- The `.detail-panel` (sticky wrapper), `.detail-header`, `.detail-section`, `.tab-strip`, `.tab-button`, `.tab-button.active`, `.tab-button[aria-disabled="true"]`, `.detail-panel[data-realm="..."] .scientific-name` CSS rules MUST STAY (they're specialized panel patterns, not generic primitives).
- The data attributes (`data-detail-panel`, `data-detail-panel-source`, `data-detail-panel-tab`, `data-realm`, `data-detail-extinct`, `data-detail-source-badge`, `data-detail-title`, `data-detail-authorship`, `data-detail-tab-strip`, `data-tab`, `data-tab-content`, `data-detail-overview-rank`, `data-detail-overview-grid`, `data-detail-overview-field`, `data-detail-overview-row`, `data-detail-chain-segment`, `data-detail-chain-rank`, `data-action="close-detail"`, `data-action="focus-segment"`, `data-test-value`) MUST stay.
- The a11y attributes (`aria-pressed`, `aria-disabled`, `aria-controls`, `aria-label`, `role="tablist"`, `role="tab"`) MUST stay.
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/modules/taxonomy/presentation/DetailPanel.tsx
src/app/globals.css
tests/test_visible_taxonomy_tree.py

## Files referenced (read-only)

src/modules/design-system/index.ts (the public barrel — verify Badge + Card + IconButton + Text exports exist; they do, post-PR #385)
src/modules/design-system/presentation/Badge.tsx
src/modules/design-system/presentation/Card.tsx
src/modules/design-system/presentation/IconButton.tsx
src/modules/design-system/presentation/Text.tsx

## Acceptance criteria

- DetailPanel renders using `Badge` + `Card` + `IconButton` + `Text` from `@taxa/design-system`.
- The `.rank-badge`, `.authorship`, `.overview-value`, `.overview-rank`, `.overview-label` CSS rules are removed from globals.css (after `grep -rE` confirms zero references).
- The `.detail-panel`, `.detail-header`, `.detail-section`, `.tab-strip`, `.tab-button`, `.tab-button.active`, `.detail-panel[data-realm="..."] .scientific-name` CSS rules are kept (still have references).
- All updated tests pass + all 8 new Phase 2 coverage tests pass.
- Regression sweep on PR #382 + #384 + #385 + #386 protected files stays GREEN.
- `npx --no-install next build` → exit 0; 6 routes prerendered.
- `git diff --check` → clean.

## Risks + follow-ups (out of scope)

- The 8 Playwright follow-up failures from PR #386 remain.
- The `.fex-*` cascade stays until Phase 3.
- Other Phase 2 consumers (AppShell, Explorer, etc.) still use inline Tailwind + `.fex-*`.
- The `Spinner` + `EmptyState` + `InlineMessage` primitives are still unused — Phase 2+ consumers (FolderTab's loading + error states, Explorer's loading state, etc.) will pick them up.

## Rollback

If anything fails, run `git restore src/modules/taxonomy/presentation/DetailPanel.tsx src/app/globals.css tests/test_visible_taxonomy_tree.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.