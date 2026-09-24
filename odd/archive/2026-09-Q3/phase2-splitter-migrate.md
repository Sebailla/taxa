# Phase 2 — Splitter + ExplorerErrorBoundary migrate to design-system primitives

## Objective

Sixth (and likely final) Phase 2 consumer migration. Migrate `Splitter.tsx` + `ExplorerErrorBoundary.tsx` to use the design-system primitives where applicable. This completes the Phase 2 sweep (all consumers that benefit from primitive decomposition have been migrated).

`Splitter.tsx` is 387 lines (the drag-handle for the tree pane / viewer pane). `ExplorerErrorBoundary.tsx` is 107 lines (the React error boundary for the Explorer surface).

Both are specialized — the honest outcome is likely "minimal/no migration" similar to AppShell. The work may be Phase 2 coverage tests pinning the contract.

## User decision

- Splitter is the sixth Phase 2 consumer (the "last" in the user's "scope acotado" pattern).
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/research/presentation/Splitter.tsx` + `ExplorerErrorBoundary.tsx` (2 files)

- **`Splitter.tsx`** (387 lines):
  - The drag-handle uses the `.fex-splitter` CSS cascade (specialized — `position: relative; cursor: col-resize; ::after pseudo-element for hit-area; :hover / .dragging / :focus-visible states`). Migration to a primitive is NOT possible (the primitive doesn't cover drag-handle patterns).
  - The component uses native `<div>` + event handlers + `useState` + `useEffect` + `useRef` for the drag logic. No inline buttons / icons / typography that would benefit from primitives.
  - **Decision**: NO JSX migration. Ship Phase 2 coverage tests pinning the contract (the Splitter is a specialized drag-handle, NOT a candidate for `<Button>` / `<IconButton>` / `<Text>` / `<Card>` / `<EmptyState>` / `<Spinner>` / `<InlineMessage>` / `<Badge>` primitives).

- **`ExplorerErrorBoundary.tsx`** (107 lines):
  - The error boundary uses native React lifecycle methods (`componentDidCatch` / `getDerivedStateFromError`). The fallback renders a heading + a retry button.
  - The retry button (currently `<button type="button" className="fex-snippet-btn mt-2" onClick={handleRetry} aria-label="Retry loading the file tree">Retry</button>`) COULD be replaced with `<Button variant="secondary" onClick={handleRetry}>` — but `<Button>` and `<button className="fex-snippet-btn">` serve different purposes (`fex-snippet-btn` is for the snippet frame panel; `<Button>` is the generic primitive). The retry button here serves the error-boundary context — could go either way.
  - **Decision**: Inspect the component for migration opportunity. If the retry button is the only candidate, replace with `<Button variant="secondary">` + add coverage test. If the component is purely specialized (no inline button / icon / typography), ship coverage tests pinning the contract.

### `src/app/globals.css` — REMOVE rules that the two components no longer use

After the JSX rewrite (if any), check if any rules become dead:
- Run `grep -rE` across `src/` for any rule that's no longer referenced.
- IF dead rules exist: remove them.
- IF no dead rules: no change to globals.css.

### Tests

Update existing tests if the JSX changed; add Phase 2 coverage tests for the contract (whether or not JSX changed):

- `tests/test_research_explorer_mount.py` (Splitter is rendered inside the Explorer):
  - If `ExplorerErrorBoundary` retry button migrates to `<Button>`: update the existing test that pins the retry button's HTML + class. Add a Phase 2 coverage test pinning the `<Button>` primitive import.
  - If Splitter stays as-is: add a Phase 2 coverage test pinning the specialized drag-handle contract (the Splitter is a `<div>` with the `.fex-splitter` class + the `::after` hit-area extension + the `:hover / .dragging / :focus-visible` states; NOT a primitive).

## Non-goals

- Migrating other Phase 2 consumers (Viewer panel states, etc.) — Phase 3.
- Removing the `.fex-*` cascade (Phase 3 once no consumer uses it).
- The 8 Playwright follow-up failures from PR #386 — separate follow-up PR.

## TDD discipline

1. **FIRST**, inspect both components for migration opportunities.
2. **IF substantive migration exists** (ExplorerErrorBoundary retry button → `<Button>`): update the existing test + ship the JSX change.
3. **IF no substantive migration**: document the Splitter + ExplorerErrorBoundary specialized reasoning + ship Phase 2 coverage tests pinning the contract.
4. **THEN**, run the FULL regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 protected test files → 0 failed.
5. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 / #388 / #389 / #390 protected test files.
- The new primitives (if used) must be imported from `@taxa/design-system` (the public barrel).
- The data attributes (`data-splitter-for`, `data-fex-splitter`, `data-error-boundary`, etc.) MUST stay.
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/modules/research/presentation/Splitter.tsx
src/modules/research/presentation/ExplorerErrorBoundary.tsx
src/app/globals.css
tests/test_research_explorer_mount.py

## What to return

- The inspection findings: per-component summary of what was inspected + what migration opportunities exist (or don't).
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

If anything fails, run `git restore src/modules/research/presentation/Splitter.tsx src/modules/research/presentation/ExplorerErrorBoundary.tsx src/app/globals.css tests/test_research_explorer_mount.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.