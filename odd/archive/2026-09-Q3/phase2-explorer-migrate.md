# Phase 2 — Explorer migrate to design-system primitives

## Objective

Fifth consumer migration in Phase 2 of the design-system extract (post-PR #385). Migrate the Explorer sub-components (`Explorer.tsx` + `FileTree.tsx` + `Viewer.tsx` + `Splitter.tsx` + `ExplorerErrorBoundary.tsx`) to use `EmptyState` + `Spinner` + `Card` from `@taxa/design-system`.

The Explorer is the most substantive Phase 2 work remaining — it has loading + empty + error states that map directly to `Spinner` + `EmptyState` + `InlineMessage` + `Card`. This PR uses **4 of 8 primitives** (Spinner + EmptyState + Card + InlineMessage).

## User decision

- Explorer is the fifth Phase 2 consumer.
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/research/presentation/Explorer.tsx` + `FileTree.tsx` + `Viewer.tsx` + `Splitter.tsx` + `ExplorerErrorBoundary.tsx` (5 files)

- **Import from `@taxa/design-system`**: `Card`, `EmptyState`, `InlineMessage`, `Spinner` (4 of 8 primitives).
- **`Explorer.tsx`** (orchestrator, 681 lines):
  - The loading state (currently `<div className="fex-empty-state" role="status" data-tree-loading=""><span className="fex-empty-state-icon material-symbols-outlined animate-spin">progress_activity</span><p>Loading…</p></div>`) → use `<Spinner size="md" label="Loading file tree…" />`. The `data-tree-loading=""` attribute MUST stay.
  - The error state (currently `<div className="fex-empty-state" role="alert" data-tree-error=""><span className="fex-empty-state-icon material-symbols-outlined">error</span><p className="font-semibold text-on-surface">Could not load file tree</p><p className="text-on-surface-variant text-body-sm">{message}</p><button …>Retry</button></div>`) → use `<EmptyState icon="error" title="Could not load file tree" description={message} size="lg"><Button variant="secondary" onClick={handleRetry}>Retry</Button></EmptyState>`. The `data-tree-error=""` attribute + `role="alert"` + `Retry` button + the error icon MUST stay semantically equivalent.
  - The empty state (currently `<div className="fex-empty-state" role="status" data-tree-empty=""><span className="fex-empty-state-icon material-symbols-outlined">folder_off</span><p>No research folders yet — materialize a taxon to populate the tree.</p><p className="text-on-surface-variant text-body-sm">{tree.filesystem_path || ""}</p></div>`) → use `<EmptyState icon="folder_off" title="No research folders yet" description="Materialize a taxon to populate the tree." size="lg">{tree.filesystem_path || ""}</EmptyState>`. The `data-tree-empty=""` attribute + `role="status"` + the folder_off icon MUST stay semantically equivalent.
- **`FileTree.tsx`** (734 lines):
  - The "No matches." empty state (currently `<div className="fex-empty-state fex-search-empty"><span className="fex-empty-state-icon">search_off</span><p>No matches.</p></div>`) → use `<EmptyState icon="search_off" title="No matches." size="sm" />`. The `data-search-empty=""` attribute MUST stay.
  - The loading/empty/error states are rendered by the parent `Explorer.tsx` (per the `renderTreePane()` switch). FileTree itself is the recursive tree renderer.
- **`Viewer.tsx`** (2707 lines):
  - The various panels (table viewer, image viewer, video viewer, EPUB viewer, snippet frame, etc.) use the `.fex-*` cascade — these are specialized patterns. Phase 3 work to migrate.
  - The loading state (if any) → use `<Spinner size="md" />`.
  - The empty state (if any) → use `<EmptyState>`.
- **`Splitter.tsx`** (specialized drag-handle) — NO migration (too specialized).
- **`ExplorerErrorBoundary.tsx`** — KEEP (specialized error boundary, not a candidate for primitives).

### `src/app/globals.css` — REMOVE rules that Explorer no longer uses

After the JSX rewrite, these rules become dead (since `Explorer.tsx`'s loading/empty/error states use the primitives):
- `.fex-empty-state` (the wrapper) — replaced by `<EmptyState>` for the error + empty states; replaced by `<Spinner>` for the loading state. Safe to remove IF no other consumer uses it (verify with `grep -rE`).
- `.fex-empty-state .fex-empty-state-icon` (the icon span) — replaced by the `<EmptyState icon=...>` prop. Safe to remove.
- `.fex-search-empty` (the search empty state) — replaced by `<EmptyState size="sm" />`. Safe to remove.

**KEEP** (still have references — used by other consumers or specialized patterns):
- `.fex-empty-state` MAY have references in Viewer.tsx (table/image/video/EPUB viewer states). Verify with grep.
- All `.fex-banner`, `.fex-snippet-*`, `.fex-csv-*`, `.fex-sheet-*`, `.fex-image-*`, `.fex-video-*`, `.fex-json-*`, `.fex-tree-*`, `.fex-epub-*`, `.fex-meta-*`, `.fex-row*`, `.fex-tab-strip`, `.fex-splitter`, `.fex-shell`, `.fex-viewer-pane`, `.fex-tree-pane`, `.fex-tree-leaf*`, `.fex-search-clear`, `.fex-search-empty`, `.fex-search-hide-empty-btn`, `.fex-search-icon`, `.fex-search-input`, `.fex-search-mode-btn`, `.fex-search-row`, `.fex-search-toggles`, `.fex-tree-header`, `.fex-tree-header h2`, `.fex-tree-header-search`, `.fex-tree-truncated`, `.fex-tree-truncated .material-symbols-outlined` — KEEP (specialized Explorer patterns + Viewer state patterns).

CRITICAL: run `grep -rE` across `src/` BEFORE removing any rule to confirm zero references remain after the JSX rewrite.

### Tests

Tests that pin the pre-migration Explorer composition:
- `tests/test_research_explorer_mount.py::test_dom_markers_present_in_rendered_taxonomy_page` — likely references the `data-tree-loading` / `data-tree-empty` / `data-tree-error` attributes + the loading/empty/error copy. UPDATE: the primitives use the same attributes; the test should pass unchanged.
- Other Explorer tests likely check the loading/empty/error states. UPDATE: the primitives preserve the visual contract; the test assertions need to check the primitives' data attributes + the icon + the title.

### Tests (new Phase 2 coverage)

Add new tests:
- `test_explorer_uses_spinner_primitive_for_loading_state` — asserts `<Spinner size="md" label="Loading file tree…" />` is used.
- `test_explorer_uses_emptystate_primitive_for_empty_state` — asserts `<EmptyState icon="folder_off" title="No research folders yet" ...>` is used.
- `test_explorer_uses_emptystate_primitive_for_error_state` — asserts `<EmptyState icon="error" title="Could not load file tree" ...>` is used.
- `test_filetree_uses_emptystate_primitive_for_no_matches` — asserts `<EmptyState icon="search_off" title="No matches." size="sm" />` is used.

## Non-goals

- Migrating the `.fex-*` cascade (Phase 3 once no consumer uses it).
- Migrating `Splitter` (specialized drag-handle).
- Migrating `ExplorerErrorBoundary` (specialized error boundary).
- The 8 Playwright follow-up failures from PR #386 — separate follow-up PR.

## TDD discipline

1. **FIRST**, update the affected tests.
2. **THEN**, ship the JSX rewrite + globals.css cleanup.
3. **THEN**, re-run the updated tests → GREEN.
4. **THEN**, add the 4 new Phase 2 coverage tests.
5. **THEN**, run the FULL regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 / #389 protected test files → 0 failed.
6. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 / #388 / #389 protected test files.
- The new primitives must be imported from `@taxa/design-system` (the public barrel).
- The data attributes (`data-tree-loading`, `data-tree-empty`, `data-tree-error`, `data-search-empty`, etc.) MUST stay.
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/modules/research/presentation/Explorer.tsx
src/modules/research/presentation/FileTree.tsx
src/modules/research/presentation/Viewer.tsx
src/modules/research/presentation/Splitter.tsx
src/modules/research/presentation/ExplorerErrorBoundary.tsx
src/app/globals.css
tests/test_research_explorer_mount.py

## Files referenced (read-only)

src/modules/design-system/index.ts (verify Card + EmptyState + InlineMessage + Spinner exports exist)

## Acceptance criteria

- Explorer sub-components use Card + EmptyState + InlineMessage + Spinner from `@taxa/design-system`.
- The `.fex-empty-state` + `.fex-search-empty` + `.fex-empty-state-icon` CSS rules are removed from globals.css (after `grep -rE` confirmation).
- All updated tests pass + all 4 new Phase 2 coverage tests pass.
- Regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 / #389 protected files stays GREEN.
- `npx --no-install next build` → exit 0; 6 routes prerendered.
- `git diff --check` → clean.

## Risks + follow-ups (out of scope)

- The 8 Playwright follow-up failures from PR #386 remain.
- The `.fex-*` cascade stays until Phase 3.
- Splitter + ExplorerErrorBoundary + Viewer specialized panels remain for Phase 3.

## Rollback

If anything fails, run `git restore src/modules/research/presentation/Explorer.tsx src/modules/research/presentation/FileTree.tsx src/modules/research/presentation/Viewer.tsx src/modules/research/presentation/Splitter.tsx src/modules/research/presentation/ExplorerErrorBoundary.tsx src/app/globals.css tests/test_research_explorer_mount.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.