# Phase 2 — TreeRow migrate to design-system primitives + collapse per-row density

## Objective

Two P1s collapse into one PR:

1. **Original P1 from 2026-09-23 critique**: "Per-tree-row meta block too dense (6-7 elements)"
2. **Phase 2 of design-system extract** (post-PR #385): migrate the first consumer (`TreeRow`) to use the new primitives from `@taxa/design-system`.

`TreeRow.tsx` currently renders **9 visible elements per row**:
1. disclosure glyph (▾ / ▸ / •)
2. rank badge (inline `<span className="rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded ...">`)
3. scientific name (`<span className="... truncate ...">` with inline Tailwind)
4. materialize indicator (Material Symbols `folder` glyph + `materialize-indicator` class)
5. source info glyph (Material Symbols `info` glyph + `source-info` class)
6. status dot (Material Symbols dot + `status-dot-{accepted,synonym,unknown}` class)
7. species count badge (inline `<span className="species-count-badge ...">`)
8. visibility icon button (`tree-search-icon` Material Symbols `visibility` glyph)
9. kebab trigger (Material Symbols `more_vert` + `kebab-trigger`)

**Target after migration**: 5 visible elements per row:
1. disclosure glyph (kept — needed for the expand/collapse affordance)
2. **Badge** for the rank (replaces the inline rank-badge span)
3. scientific name (kept as inline — too context-specific to extract to a Text variant)
4. **Badge** for the status dot + species count composite (replaces both the status dot span AND the species-count-badge span)
5. **IconButton** for the kebab trigger (replaces the visibility icon button + kebab trigger; the kebab menu itself already contains "View details", "Open folder", and "View on WoRMS" — `View details` is the duplicate affordance and gets dropped from the kebab since it's the same action as clicking the row)

Net effect: 9 → 5 elements (-44%); the materialize indicator and source info glyph collapse into the kebab menu (where the user can discover them on demand); the duplicate `View details` affordance is dropped (clicking the row is the same action).

## User decision

- TreeRow is the first Phase 2 consumer (the row density P1 was the most-cited critique observation across both rounds).
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/taxonomy/presentation/TreeRow.tsx` (rewrite of the JSX render section + the rowClassFor helpers)

- **Import from `@taxa/design-system`**: `Badge`, `IconButton` (no `Button` needed for TreeRow; no `Card` needed; no `EmptyState` / `Spinner` / `InlineMessage` / `Text` needed — this PR only uses 2 of the 8 primitives).
- Replace inline rank-badge span with `<Badge variant="subtle" uppercase={true}>{rankLabel(taxon.rank)}</Badge>` (the default Badge class already includes the rank-badge pattern via the `bg-surface text-on-surface-variant border border-outline-variant` subtle variant + the `uppercase tracking-[0.1em] text-[11px] font-semibold px-2 py-0.5 rounded` defaults).
- Replace the materialize indicator + source info glyph + visibility icon button + kebab trigger with **one `<IconButton variant="subtle" aria-label="More actions for {taxon.name}">more_vert</IconButton>`** that opens the existing kebab menu. The kebab menu already has "View details" (which is the duplicate affordance — drop it), "Open folder" (conditional on `isMaterialized`), and "View on WoRMS" (conditional on `wormsUrl`).
- Replace the status dot + species count composite with a `<Badge variant="subtle" uppercase={false}>` containing both the status indicator + the species count text. The status dot is currently a CSS class (`status-dot-{accepted,synonym,unknown}`) carrying a colored dot via `::before`. Convert to an inline `<span>` with the Tailwind utility that maps to the status (green-500 for accepted, amber-500 for synonym, on-surface-variant for unknown) — render a `•` glyph (or a small `<span>` with background-color) + the species count text.
- Collapse the source info glyph into a `<abbr title="...">` wrapper on the scientific name span (the title attribute already carries the source info tooltip text). The Material Symbols `info` glyph and the `source-info` class disappear.
- Collapse the authorship into the `title` attribute on the name (it already is in the `nameTitle` variable) — no change needed.

### `src/app/globals.css` — REMOVE rules that TreeRow no longer uses

After the JSX rewrite, several `globals.css` rules become dead:
- `.rank-badge` (line ~1961 — used by the old inline span; the new `<Badge>` primitive centralizes this)
- `.materialize-indicator` (line ~1930 — used by the old materialize icon; gone from JSX)
- `.source-info` (line ~1935 — used by the old source info glyph; gone from JSX)
- `.status-dot` + `.status-dot-accepted` / `.status-dot-synonym` / `.status-dot-unknown` (lines ~1900-1925 — used by the old status dot; converted to inline Tailwind)
- `.tree-search-icon` (line ~2043 — used by the old visibility icon; gone from JSX)
- `.species-count-badge` (line ~1985 — used by the old species count span; folded into the new status+count Badge)

Removal of these rules MUST NOT break any other consumer:
- `.rank-badge` is also used by the detail panel header (`src/modules/taxonomy/presentation/DetailPanel.tsx`). Phase 2 of TreeRow does NOT migrate DetailPanel; the test contract `test_rank_badge_appears_in_detail_panel` (if it exists in the visible-taxonomy test file) MUST be updated to migrate the detail panel header too OR we keep the rule and accept a transient dual-render. **Decision**: keep `.rank-badge` for now (DetailPanel is a separate consumer; Phase 3 work); only remove rules that have ZERO references after the rewrite. The test file `tests/test_visible_taxonomy_tree.py` may have assertions that pin these rules — the worker must verify + update.
- `.materialize-indicator` — only used by TreeRow; safe to remove.
- `.source-info` — only used by TreeRow; safe to remove.
- `.status-dot-*` — only used by TreeRow; safe to remove.
- `.tree-search-icon` — only used by TreeRow; safe to remove.
- `.species-count-badge` — only used by TreeRow; safe to remove.

The worker MUST run a `grep -rE` across `src/` BEFORE removing any rule to confirm zero references remain after the JSX rewrite.

### Tests (in `tests/test_visible_taxonomy_tree.py`)

Update tests that pin the OLD row composition:
- `test_tree_row_uses_semantic_disclosure_button` — keep (still true; the disclosure button stays).
- `test_tree_row_renders_a_real_block` — keep (still true; the row is still a `<div>`).
- `test_tree_row_disclosure_glyphs_match_native` — keep (still true).
- `test_tree_row_stamps_data_action_per_rank` — keep (still true; `data-action` still stamped per rank).
- `test_tree_row_stamps_depth_and_leaf_attributes` — keep.
- `test_tree_row_renders_status_dot` — UPDATE: the new composition renders an inline `<span>` with status-specific Tailwind color (no `.status-dot-{accepted,synonym,unknown}` class). Change the assertion to check for the inline span + the appropriate Tailwind color utility.
- `test_tree_row_renders_materialize_indicator` — UPDATE: the materialize indicator is now inside the kebab menu (only when `isMaterialized` is true). The test should check that the kebab menu contains a "folder_open" glyph + "Open folder" label when materialized.
- `test_tree_row_renders_source_info_affordance` — UPDATE: the source info is now an `abbr` title attribute on the name span. The test should check that the name span carries a `title` attribute with the source info tooltip text.
- `test_tree_row_renders_species_count_badge` — UPDATE: the species count is now inside the new status+count Badge. The test should check for the count text inside a Badge component.
- `test_tree_row_renders_kebab_trigger` — UPDATE: keep (the kebab trigger is still rendered, now via `<IconButton>`).
- `test_tree_row_renders_kebab_menu_items` — UPDATE: drop "View details" (it was a duplicate affordance). Keep "Open folder" (conditional) + "View on WoRMS" (conditional).
- `test_tree_row_renders_view_details_icon_button` — REMOVE or REPURPOSE: the old per-row visibility button is gone. Either remove the test or repurpose it to assert that the kebab menu contains the "View details" item (which it does — but that's tested by `test_tree_row_renders_kebab_menu_items`).
- `test_tree_row_view_details_kebab_is_enabled` — UPDATE: same as above.
- `test_tree_row_view_details_button_invokes_on_select` — UPDATE: the row click still invokes `onSelect(taxon.id)` per the existing `onClick` handler on the disclosure button. The view details button is gone; the kebab menu's `View details` item (which is being removed) is the one that called `onSelect`. Update the test to assert that clicking the row's disclosure button still invokes `onSelect`.
- `test_tree_row_view_details_button_uses_existing_css_class` — REMOVE: the class `tree-search-icon` no longer exists (the IconButton primitive uses its own classes).
- `test_tree_row_view_details_kebab_is_enabled_for_materialized_rows` — UPDATE: the kebab "Open folder" item is still conditional on `isMaterialized`; keep the test.
- `test_out_index_html_has_view_details_button_styles` — REMOVE (the `tree-search-icon` styles are gone).

Tests that pin `data-test-value` for the species count badge etc. need to be updated to look inside the Badge component. Tests that pin the kebab menu items must update to remove "View details".

### Tests (new in `tests/test_visible_taxonomy_tree.py` for Phase 2 coverage)

Add new tests:
- `test_tree_row_uses_badge_primitive_for_rank` — asserts `<Badge variant="subtle" uppercase={true}>` is used for the rank.
- `test_tree_row_uses_iconbutton_primitive_for_kebab` — asserts `<IconButton variant="subtle">` is used for the kebab trigger.
- `test_tree_row_collapsed_density_count` — asserts the rendered row has at most 6 visible elements per row (5 in the typical case: disclosure + Badge rank + name + status+count Badge + IconButton kebab; 6 with the materialize indicator inside the open kebab menu).
- `test_tree_row_no_inline_rank_badge_span` — asserts the old `<span className="rank-badge ...">` is gone (replaced by the Badge primitive).
- `test_tree_row_no_inline_status_dot_class` — asserts the old `status-dot-{accepted,synonym,unknown}` class is gone.
- `test_tree_row_no_inline_tree_search_icon` — asserts the old `<span className="material-symbols-outlined tree-search-icon">visibility</span>` is gone (replaced by the kebab IconButton).
- `test_tree_row_no_inline_materialize_indicator_class` — asserts the old `<span className="materialize-indicator ...">` is gone (the materialize affordance is now in the kebab menu).
- `test_tree_row_no_inline_source_info_class` — asserts the old `<span className="material-symbols-outlined source-info">info</span>` is gone.

## Non-goals

- Migrating `DetailPanel` to use the design-system primitives (Phase 3 work).
- Migrating `Explorer` / `FileTree` / `Viewer` / `Splitter` (later Phase 2 work).
- Migrating `AppShell` sub-components (Header / Footer / Nav) (later Phase 2 work).
- Wiring the global search input to the explorer's file search (original P1 from the critique; out of scope).
- Removing the legacy `.fex-*` cascade (Phase 3 once no consumer uses it).
- Removing `.rank-badge` from globals.css (DetailPanel still uses it; Phase 3 work).

## TDD discipline

1. **FIRST**, the worker updates the affected tests in `tests/test_visible_taxonomy_tree.py` (the list above). Run the tests — they should fail with the OLD assertions (because the implementation hasn't changed yet).
2. **THEN**, ship the JSX rewrite + the globals.css cleanup.
3. **THEN**, re-run the updated tests → GREEN.
4. **THEN**, add the new Phase 2 coverage tests (the 8 new tests above).
5. **THEN**, run the FULL regression sweep on PR #382 + #384 + #385 protected test files → 0 failed.
6. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 protected test files (`test_app_shell_render.py`, `test_hydration_console.py`, `test_browser_state_keys.py`, `test_research_styles.py`, `test_search_engine_consumer_manifest.py`, `test_design_system_primitives.py`, `test_smoke.py`).
- DO NOT remove `.rank-badge` from globals.css (DetailPanel uses it; Phase 3).
- DO NOT remove any globals.css rule that still has references in `src/` after the JSX rewrite — run `grep -rE` first.
- The new `<Badge>` and `<IconButton>` primitives must be imported from `@taxa/design-system` (the public barrel), NOT deep-imported into `src/modules/design-system/presentation/`.
- The kebab menu items must drop "View details" (it was a duplicate affordance — clicking the row OR clicking the kebab "View details" both call `onSelect`; the row click is the more discoverable path; the kebab item is redundant).
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.
- The `data-test-value` / `data-taxon-id` / `data-action` etc. data attributes on the row MUST stay (other tests depend on them).

## Allowed edit surfaces

src/modules/taxonomy/presentation/TreeRow.tsx
src/app/globals.css
tests/test_visible_taxonomy_tree.py

## Files referenced (read-only)

src/modules/design-system/index.ts (the public barrel — verify the Badge + IconButton exports exist; they do, post-PR #385)
src/modules/design-system/presentation/Badge.tsx
src/modules/design-system/presentation/IconButton.tsx
src/modules/taxonomy/presentation/DetailPanel.tsx (verify it still uses `.rank-badge` — if so, do NOT remove the rule from globals.css)

## Acceptance criteria

- TreeRow renders at most 6 visible elements per row in the typical case (5: disclosure + Badge rank + name + status+count Badge + IconButton kebab).
- The 9-element row composition collapses to the 5-element composition (or 6 with the kebab open).
- `.rank-badge` is NOT removed from globals.css (DetailPanel still uses it).
- `.materialize-indicator`, `.source-info`, `.status-dot`, `.status-dot-{accepted,synonym,unknown}`, `.tree-search-icon`, `.species-count-badge` ARE removed from globals.css (after `grep -rE` confirms zero references in `src/`).
- The kebab menu drops "View details" (was a duplicate affordance).
- Clicking the row's disclosure button still invokes `onSelect(taxon.id)`.
- The new `<Badge>` and `<IconButton>` are imported from `@taxa/design-system`.
- All updated tests pass + all new Phase 2 tests pass.
- Regression sweep: 555+ tests pass (PR #382 + #384 + #385 contracts stay green).
- `npx --no-install next build` → exit 0; 6 routes prerendered.
- `git diff --check` → clean.

## Risks + follow-ups (out of scope)

- The DetailPanel still uses inline `.rank-badge` and other patterns that the design-system primitives could replace. Phase 3 work.
- The `AppShell` sub-components (Header / Footer / Nav) still use inline Tailwind utility compositions for buttons + icons. Phase 2 later work.
- The "View details" affordance being dropped from the kebab might affect users who discovered it via the kebab menu. Mitigation: the row click still invokes `onSelect(taxon.id)`; the kebab "View details" was redundant. Acceptable.
- The Materialize indicator (the green folder glyph when `research_path_exists`) was a quick visual signal that's now in the kebab menu. Power users might notice the loss of immediate visibility. Mitigation: the kebab is one click away; the kebab "Open folder" item still exists for materialized rows. Acceptable.
- The source info tooltip now lives on the name span's `title` attribute. Screen-reader users will hear the source info when focusing on the name span. Acceptable a11y improvement.

## Rollback

If anything fails, run `git restore src/modules/taxonomy/presentation/TreeRow.tsx src/app/globals.css tests/test_visible_taxonomy_tree.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.