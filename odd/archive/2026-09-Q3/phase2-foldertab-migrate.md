# Phase 2 — FolderTab migrate to design-system primitives

## Objective

Third consumer migration in Phase 2 of the design-system extract (post-PR #385). Migrate `FolderTab.tsx` to use `Spinner`, `EmptyState`, `InlineMessage`, `Button`, `IconButton` from `@taxa/design-system`.

`FolderTab.tsx` is 766 lines (`"use client"`). It renders the native DetailPanel Folder tab body — the materialize-preview payload with line-by-line segments, counts summary, info banner, conditional Create row with confirmation gate, Open + Copy path-actions row, and inline success/error states.

The migration uses **5 of 8 primitives** (Spinner + EmptyState + InlineMessage + Button + IconButton) — the broadest primitive coverage of any Phase 2 consumer so far.

## User decision

- FolderTab is the third Phase 2 consumer.
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/taxonomy/presentation/FolderTab.tsx` (JSX rewrite + helper consolidation)

- **Import from `@taxa/design-system`**: `Button`, `EmptyState`, `IconButton`, `InlineMessage`, `Spinner` (5 of 8 primitives).
- **Replace the loading state** with `<Spinner size="md" label="Loading folder preview…" />` (the inline `<span className="material-symbols-outlined animate-spin">progress_activity</span>` + copy `<p>Loading…</p>` becomes the Spinner primitive).
- **Replace the error state** with `<InlineMessage variant="error">…</InlineMessage>` (the inline `<div className="folder-inline-message folder-inline-message-error …">` becomes the InlineMessage primitive).
- **Replace the success message** with `<InlineMessage variant="success">…</InlineMessage>` (the inline `<div className="folder-inline-message folder-inline-message-success …">` becomes the InlineMessage primitive).
- **Replace the info banner** with `<InlineMessage variant="info">…</InlineMessage>` (the `<div className="folder-info-banner …">` becomes the InlineMessage primitive).
- **Replace the Create button** with `<Button variant="primary" onClick={onArmCreate}>Create</Button>` (the inline `<button className="folder-btn folder-btn-primary …">`).
- **Replace the Confirm button** with `<Button variant="primary" onClick={onCreate}>Confirm</Button>` (the confirm-step button).
- **Replace the Cancel button** with `<Button variant="secondary" onClick={onDisarmCreate}>Cancel</Button>`.
- **Replace the Open button** with `<Button variant="secondary" onClick={onOpen}>Open in Finder</Button>` (the `<button className="folder-btn folder-btn-secondary …">`).
- **Replace the Copy button** with `<Button variant="secondary" onClick={onCopy}>Copy path</Button>`.
- **Replace the Retry button** (in the error state) with `<Button variant="secondary" onClick={onRetryPreview}>Retry</Button>`.
- **Keep unchanged**:
  - The folder segment list rendering (specialized markup — segment markers `✓` / `+` + paths).
  - The counts summary (specialized `<div className="folder-counts">` with new_count + existing_count).
  - The `<Fragment>` import (used by the segment list).
  - All the `data-*` attributes (`data-folder-tab`, `data-folder-section`, `data-folder-create-row`, `data-folder-confirm`, `data-folder-info-banner`, `data-folder-counts`, `data-folder-segment-list`, `data-folder-segment-wrap`, `data-folder-segment-item`, `data-folder-segment-marker`, `data-folder-segment-path`, `data-folder-confirm-prompt`, `data-folder-confirm-actions`, `data-folder-confirm-path`, `data-folder-path-actions`, `data-folder-inline-message`, `data-folder-inline-message-error`, `data-folder-inline-message-success`, `data-action="create-folders"`, `data-action="confirm-create-folders"`, `data-action="disarm-create-folders"`, `data-action="open-folder-tab"`, `data-action="copy-path"`, `data-folder-section-header`, `data-folder-section-count`, `data-folder-section-title`).
  - The `aria-label` / `aria-busy` attributes.
  - The `useEffect` import (used for the explorer-refresh-bridge event dispatch).
  - The `EXPLORER_REFRESH_EVENT_NAME` constant + dispatch.

### `src/app/globals.css` — REMOVE rules that FolderTab no longer uses after the JSX rewrite

After the JSX rewrite, these rules become dead:
- `.folder-tab .folder-info-banner` (replaced by `<InlineMessage variant="info">`)
- `.folder-tab .folder-inline-message` (replaced by `<InlineMessage>`)
- `.folder-tab .folder-inline-message-error` (replaced by `<InlineMessage variant="error">`)
- `.folder-tab .folder-inline-message-success` (replaced by `<InlineMessage variant="success">`)
- `.folder-tab .folder-btn` + `.folder-tab .folder-btn-primary` + `.folder-tab .folder-btn-secondary` (replaced by `<Button>` variants — keep the base button resets if Tailwind utilities don't cover them; otherwise remove)
- `.folder-tab .folder-create-row` (specialized layout — keep if still used as a wrapper)
- `.folder-tab .folder-confirm` + `.folder-tab .folder-confirm-prompt` + `.folder-tab .folder-confirm-actions` + `.folder-tab .folder-confirm-path` (specialized confirm-step layout — KEEP if still rendered)

**KEEP** (still have references after the JSX rewrite):
- `.folder-tab` (the wrapper)
- `.folder-tab .folder-segment-list` + `.folder-tab .folder-segment-list .folder-segment-item` + `.folder-tab .folder-segment-list .folder-segment-marker` + `.folder-tab .folder-segment-list .folder-segment-marker-exists` + `.folder-tab .folder-segment-list .folder-segment-marker-new` + `.folder-tab .folder-segment-list .folder-segment-path` + `.folder-tab .folder-segment-wrap` (specialized segment list — too complex for a generic primitive)
- `.folder-tab .folder-section-header` + `.folder-tab .folder-section-count` + `.folder-tab .folder-section-title` (specialized section header)
- `.folder-tab .folder-counts` (specialized counts summary)
- `.folder-tab .folder-create-row` (specialized Create row layout — KEEP if still rendered as a wrapper)
- `.folder-tab .folder-confirm` + `.folder-tab .folder-confirm-*` (specialized confirm-step layout)
- `.folder-tab .folder-path-actions` (specialized path-actions layout — contains the Open + Copy buttons)
- `.folder-tab .folder-btn:disabled` (the disabled state of the buttons — KEEP if `.folder-btn` is kept for reset styles; otherwise remove)

CRITICAL: run `grep -rE` across `src/` BEFORE removing each rule to confirm zero references remain after the JSX rewrite.

### Tests (in `tests/test_visible_taxonomy_tree.py`)

Tests that pin the pre-migration FolderTab composition:
- `test_folder_tab_file_exists` — keep.
- `test_folder_tab_is_a_client_component` — keep.
- `test_folder_tab_consumes_canonical_projection` — keep.
- `test_folder_tab_renders_loading_state` — UPDATE: the loading state is now `<Spinner size="md" label="Loading…" />`. Update to assert the Spinner primitive import OR `data-folder-loading` attribute.
- `test_folder_tab_renders_error_state` — UPDATE: the error state is now `<InlineMessage variant="error">`. Update to assert the InlineMessage primitive import OR `data-folder-inline-message` + `data-folder-status="error"`.
- `test_folder_tab_renders_preview_segments_with_markers` — keep.
- `test_folder_tab_renders_counts_summary` — keep.
- `test_folder_tab_renders_info_banner_when_all_exist` — UPDATE: the info banner is now `<InlineMessage variant="info">`. Update to assert the InlineMessage primitive import OR `data-folder-info-banner`.
- `test_folder_tab_renders_create_row_when_not_all_exist` — UPDATE: the create row buttons are now `<Button variant="primary">` + `<Button variant="secondary">`. Update to assert the Button primitive import OR the button data-attributes (preserved).
- `test_folder_tab_renders_confirm_row_when_armed` — UPDATE: the confirm row buttons are now `<Button variant="primary">` + `<Button variant="secondary">`. Update to assert the Button primitive import OR the button data-attributes (preserved).
- `test_folder_tab_renders_path_actions_when_all_exist` — UPDATE: the Open + Copy buttons are now `<Button variant="secondary">`. Update to assert the Button primitive import OR the button data-attributes (preserved).
- `test_folder_tab_renders_inline_success_and_error_messages` — UPDATE: the inline messages are now `<InlineMessage variant="success">` + `<InlineMessage variant="error">`. Update to assert the InlineMessage primitive import OR `data-folder-inline-message-success` + `data-folder-inline-message-error`.
- `test_folder_tab_does_not_invoke_clipboard_directly` — keep (the JS doesn't change).

### Tests (new in `tests/test_visible_taxonomy_tree.py` for Phase 2 coverage)

Add new tests:
- `test_folder_tab_uses_spinner_primitive_for_loading` — asserts `<Spinner size="md" label="Loading…" />` is used.
- `test_folder_tab_uses_inlinemessage_primitive_for_info_banner` — asserts `<InlineMessage variant="info">` is used for the info banner.
- `test_folder_tab_uses_inlinemessage_primitive_for_error_message` — asserts `<InlineMessage variant="error">` is used for the error message.
- `test_folder_tab_uses_inlinemessage_primitive_for_success_message` — asserts `<InlineMessage variant="success">` is used for the success message.
- `test_folder_tab_uses_button_primitive_for_create` — asserts `<Button variant="primary">` is used for the Create button.
- `test_folder_tab_uses_button_primitive_for_confirm` — asserts `<Button variant="primary">` is used for the Confirm button.
- `test_folder_tab_uses_button_primitive_for_open` — asserts `<Button variant="secondary">` is used for the Open button.
- `test_folder_tab_uses_button_primitive_for_copy` — asserts `<Button variant="secondary">` is used for the Copy button.
- `test_folder_tab_no_inline_folder_btn_classes` — asserts the old `folder-btn folder-btn-primary` / `folder-btn folder-btn-secondary` classes are gone.
- `test_folder_tab_no_inline_folder_inline_message_classes` — asserts the old `folder-inline-message folder-inline-message-error` / `folder-inline-message folder-inline-message-success` classes are gone.

## Non-goals

- Migrating other Phase 2 consumers (`AppShell`, `Explorer`, `Splitter`, `FileTree`, `Viewer`) — separate branches.
- Removing the `.fex-*` cascade (Phase 3 once no consumer uses it).
- Wiring the global search input to the explorer's file search (original P1 from the critique; out of scope).
- The 8 Playwright follow-up failures from PR #386 (test_web_toggle.py + test_search_categories.py + test_detail_overview.py) — separate follow-up PR.

## TDD discipline

1. **FIRST**, the worker updates the affected tests in `tests/test_visible_taxonomy_tree.py`. Run the tests — they should fail with the OLD assertions.
2. **THEN**, ship the JSX rewrite + the globals.css cleanup.
3. **THEN**, re-run the updated tests → GREEN.
4. **THEN**, add the 10 new Phase 2 coverage tests (the list above).
5. **THEN**, run the FULL regression sweep on PR #382 + #384 + #385 + #386 + #387 protected test files → 0 failed.
6. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 protected test files.
- The new `<Button>` / `<EmptyState>` / `<IconButton>` / `<InlineMessage>` / `<Spinner>` primitives must be imported from `@taxa/design-system` (the public barrel).
- The data attributes (`data-folder-tab`, `data-folder-section`, `data-folder-create-row`, `data-folder-confirm`, `data-folder-info-banner`, `data-folder-counts`, `data-folder-segment-list`, `data-folder-segment-wrap`, `data-folder-segment-item`, `data-folder-segment-marker`, `data-folder-segment-path`, `data-folder-confirm-prompt`, `data-folder-confirm-actions`, `data-folder-confirm-path`, `data-folder-path-actions`, `data-folder-inline-message`, `data-folder-inline-message-error`, `data-folder-inline-message-success`, `data-action="create-folders"`, `data-action="confirm-create-folders"`, `data-action="disarm-create-folders"`, `data-action="open-folder-tab"`, `data-action="copy-path"`, `data-folder-section-header`, `data-folder-section-count`, `data-folder-section-title`) MUST stay.
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/modules/taxonomy/presentation/FolderTab.tsx
src/app/globals.css
tests/test_visible_taxonomy_tree.py

## Files referenced (read-only)

src/modules/design-system/index.ts (the public barrel — verify all 5 primitive exports exist)
src/modules/design-system/presentation/Button.tsx
src/modules/design-system/presentation/EmptyState.tsx
src/modules/design-system/presentation/IconButton.tsx
src/modules/design-system/presentation/InlineMessage.tsx
src/modules/design-system/presentation/Spinner.tsx

## Acceptance criteria

- FolderTab renders using `Button` + `EmptyState` + `IconButton` + `InlineMessage` + `Spinner` from `@taxa/design-system`.
- The dead CSS rules (`.folder-tab .folder-info-banner`, `.folder-tab .folder-inline-message`, `.folder-tab .folder-inline-message-error`, `.folder-tab .folder-inline-message-success`, `.folder-tab .folder-btn`, `.folder-tab .folder-btn-primary`, `.folder-tab .folder-btn-secondary`) are removed from globals.css (after `grep -rE` confirms zero references).
- The `.folder-tab`, `.folder-tab .folder-segment-*`, `.folder-tab .folder-section-*`, `.folder-tab .folder-counts`, `.folder-tab .folder-create-row`, `.folder-tab .folder-confirm*`, `.folder-tab .folder-path-actions` CSS rules are kept (specialized panel patterns + still have references).
- All updated tests pass + all 10 new Phase 2 coverage tests pass.
- Regression sweep on PR #382 / #384 / #385 / #386 / #387 protected files stays GREEN.
- `npx --no-install next build` → exit 0; 6 routes prerendered.
- `git diff --check` → clean.

## Risks + follow-ups (out of scope)

- The 8 Playwright follow-up failures from PR #386 remain.
- The `.fex-*` cascade stays until Phase 3.
- Other Phase 2 consumers (AppShell, Explorer, etc.) still use inline Tailwind + `.fex-*`.

## Rollback

If anything fails, run `git restore src/modules/taxonomy/presentation/FolderTab.tsx src/app/globals.css tests/test_visible_taxonomy_tree.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.