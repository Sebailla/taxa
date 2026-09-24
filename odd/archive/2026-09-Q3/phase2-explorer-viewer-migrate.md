# Phase 2 restantes — Explorer panel states + Viewer specialized panels

## Objective

Seventh (and likely final) Phase 2 consumer migration. Inspect + migrate the remaining specialized patterns:

1. **`Explorer.tsx` panel-level states** (8 states: image-error, video-error, unsupported, cdn-pending, docx-loading, sheet-loading, epub-loading, csv-loading) — these render `<div className="fex-empty-state" role="alert|status">` + specialized icons + error messages. They COULD potentially migrate to `<EmptyState icon=... size="md|lg">` + `<InlineMessage variant="error|info">` for the error states + `<Spinner>` for the loading states.

2. **`Viewer.tsx` (2707 lines) panel variants** (table / image / video / EPUB / JSON tree / snippet frame / sheet) — each panel is a separate sub-component with specialized rendering. Most use specialized patterns that don't benefit from primitives.

Both are specialized. The honest scope: a few small migrations + mostly documentation + coverage tests.

## User decision

- Phase 2 restantes is the seventh consumer migration.
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/research/presentation/Explorer.tsx` + `Viewer.tsx` (2 files)

- **`Explorer.tsx`** (697 lines, post-PR #390):
  - The 3 viewer-level states (no-file-selected, bytes-error, bytes-loading) were already migrated in PR #390.
  - The 8 panel-level states (image-error, video-error, unsupported, cdn-pending, docx-loading, sheet-loading, epub-loading, csv-loading) are SPECIALIZED — each has a specific icon + message + sometimes a CTA button.
  - **Migration opportunity**: `image-error` + `video-error` + `unsupported` + `cdn-pending` could be `<EmptyState icon={error|...} title="..." description="..." size="md" />`. `docx-loading` + `sheet-loading` + `epub-loading` + `csv-loading` could be `<Spinner size="md" label="Loading..." />`.
  - **Decision**: Inspect each panel-level state. Migrate the ones where the primitive composition matches the existing semantics.

- **`Viewer.tsx`** (2707 lines):
  - The viewer variants (table / image / video / EPUB / JSON tree / snippet frame / sheet) are SPECIALIZED.
  - The `.fex-snippet-btn` cascade is the codebase-standardized button for the snippet panel + error-fallback contexts (per PR #391 reasoning).
  - **Migration opportunity**: minimal — the variants are too complex for primitives.

### `src/app/globals.css` — REMOVE rules that the panel states no longer use

If the panel states migrate to primitives, the corresponding `.fex-empty-state` + `.fex-empty-state-icon` + `.fex-banner` references may become dead. Check with `grep -rE`.

**KEEP**: the `.fex-*` specialized panel rules (`.fex-image`, `.fex-video`, `.fex-epub-frame`, `.fex-snippet-frame`, `.fex-csv-table`, `.fex-sheet-*`, `.fex-json-*`, `.fex-tab-strip`, `.fex-snippet-btn`, `.fex-tree-leaf`, `.fex-banner` etc.) — these are still load-bearing for the Viewer panel variants.

### Tests

Update existing tests + add Phase 2 coverage tests for the new migrations.

## Non-goals

- Migrating other consumers.
- Removing the `.fex-*` cascade wholesale (Phase 3 already removed the dead rules; remaining `.fex-*` rules are load-bearing).
- The 8 Playwright follow-up failures from PR #386 — separate follow-up PR.

## TDD discipline

1. **FIRST**, update existing tests for the panel state migrations.
2. **THEN**, ship the JSX rewrite + globals.css cleanup.
3. **THEN**, re-run the updated tests → GREEN.
4. **THEN**, add Phase 2 coverage tests for the new migrations.
5. **THEN**, run the FULL regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 / #392 protected test files → 0 failed.
6. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 / #391 / #392 protected test files.
- The new primitives (if used) must be imported from `@taxa/design-system` (the public barrel).
- The data attributes (e.g. `data-viewer-error`, `data-viewer-loading`) MUST stay.
- The `.fex-snippet-btn` cascade MUST stay (per PR #391 reasoning — consistency with Viewer.tsx error fallbacks).
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/modules/research/presentation/Explorer.tsx
src/modules/research/presentation/Viewer.tsx
src/app/globals.css
tests/test_research_explorer_mount.py

## What to return

- The inspection findings: per-state summary of what was inspected + what migration opportunities exist (or don't).
- IF migration was shipped: the RED → GREEN transition for each test + the JSX changes.
- IF no migration: the documentation of the specialized reasoning + the Phase 2 coverage tests added.
- The full regression + full sweep outputs.
- The `npx next build` exit code + route table.
- The `git diff --check` output.
- A list of every file you created or edited, with the line count delta.
- Any test failures or warnings encountered, with a one-sentence reason.

Do NOT commit.

## Runtime harness

Use `.venv/bin/python -m pytest` for Python tests and `npx --no-install next build` for the static export. Both run from `/Users/sebailla/Developer/taxa`. Build allowed up to 300s; tests should complete in under 60s for the targeted sweep.

## Rollback

If anything fails, run `git restore src/modules/research/presentation/Explorer.tsx src/modules/research/presentation/Viewer.tsx src/app/globals.css tests/test_research_explorer_mount.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.