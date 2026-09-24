# Phase 2 — AppShell migrate to design-system primitives

## Objective

Fourth consumer migration in Phase 2 of the design-system extract (post-PR #385). Migrate the AppShell sub-components (`AppShell.tsx` + `AppShellHeader.tsx` + `AppShellFooter.tsx` + `AppShellNav.tsx` + `AppShellGlobalSearch.tsx`) to use `Button` + `IconButton` + `Text` from `@taxa/design-system`.

The AppShell is the navigation surface — every visitor sees it on every route. Migration is the most user-facing Phase 2 work.

## User decision

- AppShell is the fourth Phase 2 consumer.
- Push + PR creation + merge remain the user's decisions.

## Scope

### `src/modules/app-shell/presentation/AppShell.tsx` + `AppShellHeader.tsx` + `AppShellFooter.tsx` + `AppShellNav.tsx` + `AppShellGlobalSearch.tsx` (5 files)

- **Import from `@taxa/design-system`** (where applicable): `Button`, `IconButton`, `Text` (3 of 8 primitives — AppShell doesn't use Badge / Card / EmptyState / Spinner / InlineMessage).
- **`AppShell.tsx`** (orchestrator): no migration needed beyond `currentRoute` prop pass-through (already wired). The `AppShellFooter` + `AppShellHeader` are the primary targets.
- **`AppShellHeader.tsx`**:
  - The brand `<a href="/">taxa</a>` is a link (Next.js `<Link>` would be more idiomatic but the existing `<a>` works for static export). KEEP as-is or convert to `<Link>` from `next/link` (out of scope — Phase 3 work).
  - The global search input is inside `<AppShellGlobalSearch>` (separate component). NO migration here.
  - The nav is inside `<AppShellNav>` (separate component). NO migration here.
  - The `skip-to-main` `<a>` (which has been DELETED in ODD-ASN-002's duplicate-removal work — but the link is still in AppShell.tsx, not Header). KEEP.
- **`AppShellFooter.tsx`**:
  - The brand mark `<span>taxa</span>` + static-export marker `<span>static export</span>` (left column) → wrap in `<Text variant="caption">` (typography) OR keep as-is (specialized footer layout).
  - The shortcut legend `<span className="app-shell-footer-shortcut-legend">Cmd+K Search · / Search · ? Help · Esc Close</span>` → wrap the kbd elements in `<Text variant="caption">` OR keep as-is (specialized kbd typography).
  - The API origin + schema version `<code>{apiOrigin}</code>` + `<span>{schemaVersion}</span>` (right column) → wrap in `<Text variant="caption">` OR keep as-is.
  - **Decision**: KEEP all footer elements as-is (specialized footer layout). The `<Text>` primitive would add the `text-on-surface-variant` + `text-xs` Tailwind utilities that the inline copy already has. Migration adds little value here. The footer is a single specialized layout that doesn't benefit from primitive decomposition.
- **`AppShellNav.tsx`**:
  - The 4 destinations are wrapped in `next/link`'s `<Link>` (specialized routing primitive, not in our set). KEEP.
  - The brand mark `<Link href="/">taxa</Link>` (or whatever the implementation uses) — KEEP.
  - The `usePathname()` hook — KEEP.
  - The active-state `aria-current="page"` — KEEP.
  - **Decision**: NO migration here (the nav uses `next/link`'s `<Link>` which is its own primitive; the design-system primitives don't cover routing links).
- **`AppShellGlobalSearch.tsx`**:
  - The search `<input>` is a native `<input>` (specialized — needs focus management + keyboard wiring). KEEP.
  - The "close" button is currently inside the global search dropdown (the search results panel when results exist). If there's a close button, replace with `<IconButton variant="subtle" aria-label="Close search">close</IconButton>`.
  - The "inert on /explorer" disabled state uses Tailwind utilities. KEEP.

**Net migration**: very limited for AppShell. The user-facing components (Header / Footer / Nav) use specialized patterns that don't benefit from primitive decomposition. The only meaningful migration is in `AppShellGlobalSearch.tsx` (the close button if it exists).

**Decision**: This PR is a small one. If the migration is too small to be worth a PR, this branch should be skipped or merged as a no-op. The user authorized "Phase 2 — AppShell" but the actual migration may not be substantive enough to warrant the work.

Per the user's pattern of "scope acotado, visible progreso en cada uno", if the migration is too small, the right move is to be honest about it and propose either:
1. A no-op merge of this branch (no changes — but wastes a PR slot)
2. Cancel this work and pick a different consumer (Explorer with EmptyState + Spinner would be more substantive)
3. Do the small AppShell migration anyway (close any inline button/icon in the AppShell sub-components)

Given the user has authorized "Phase 2 — AppShell", the right move is to:
1. Inspect each AppShell sub-component carefully for migration opportunities
2. Ship whatever substantive migration exists (even if small)
3. Document the AppShell-specific reasoning for what stays (specialized patterns, Next.js Link, etc.)

### `src/app/globals.css` — REMOVE rules that AppShell no longer uses

After the JSX rewrite (minimal in this case), these rules MAY become dead — but most are still used by AppShell's specialized patterns. KEEP all `.app-shell-*` rules (specialized navigation surface). Verify by grep -rE.

### Tests (in `tests/test_app_shell_render.py`)

Tests that pin the pre-migration AppShell composition:
- Existing tests pin the 4 destinations, the active-state, the skip-link, the footer legend, the global search input — KEEP all. The migration is small enough that no test updates are needed for AppShell specifically.
- Add new Phase 2 coverage tests:
  - `test_appshell_does_not_use_inline_button_classes` (asserts no `<button className="...inline...">` patterns)
  - `test_appshell_uses_text_primitive_or_inline_typography` (asserts AppShell uses either `<Text>` or inline Tailwind typography — no specific primitive required)
  - `test_appshell_uses_iconbutton_primitive_or_native_input` (asserts the search input is a native `<input>` OR the close button is `<IconButton>`)

If the migration is truly small (no close button to convert, no inline button classes), the new tests just pin the current contract.

## Non-goals

- Migrating other Phase 2 consumers (`Explorer`, `Splitter`, `FileTree`, `Viewer`) — separate branches.
- Converting `next/link` `<Link>` to a design-system primitive — out of scope (Next.js Link is the routing primitive).
- Removing the `.fex-*` cascade (Phase 3 once no consumer uses it).
- The 8 Playwright follow-up failures from PR #386 — separate follow-up PR.

## TDD discipline

1. **FIRST**, the worker inspects each AppShell sub-component for substantive migration opportunities.
2. **IF migration opportunities exist**: ship the JSX changes + globals.css cleanup (if any).
3. **IF migration is too small**: document the AppShell-specific reasoning (specialized routing + footer + header patterns) and ship a minimal commit that adds the Phase 2 coverage tests + documents the AppShell decision.
4. **THEN**, add the Phase 2 coverage tests (whether or not a substantive migration was shipped).
5. **THEN**, run the FULL regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 protected test files → 0 failed.
6. **FINAL**: `npx --no-install next build` → exit 0; 6 routes prerendered; `git diff --check` clean.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 / #384 / #385 / #386 / #387 / #388 protected test files.
- The new primitives (if used) must be imported from `@taxa/design-system` (the public barrel).
- The data attributes (`data-app-shell`, `data-app-shell-header`, `data-app-shell-brand`, `data-app-shell-skip-link`, `data-app-shell-nav`, `data-app-shell-nav-link`, `data-app-shell-nav-link--active`, `data-app-shell-footer`, `data-app-shell-footer-col--left`, `data-app-shell-footer-col--center`, `data-app-shell-footer-col--right`, `data-app-shell-footer-shortcut-legend`, `data-app-shell-search-input`, `data-app-shell-search-inert`) MUST stay.
- The `next/link` `<Link>` usage in `AppShellNav.tsx` MUST stay (it's the routing primitive).
- The `usePathname()` hook usage MUST stay.
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green.

## Allowed edit surfaces

src/modules/app-shell/presentation/AppShell.tsx
src/modules/app-shell/presentation/AppShellHeader.tsx
src/modules/app-shell/presentation/AppShellFooter.tsx
src/modules/app-shell/presentation/AppShellNav.tsx
src/modules/app-shell/presentation/AppShellGlobalSearch.tsx
src/app/globals.css
tests/test_app_shell_render.py

## Files referenced (read-only)

src/modules/design-system/index.ts (the public barrel — verify Button + IconButton + Text exports exist)

## Acceptance criteria

- AppShell sub-components use Button + IconButton + Text from `@taxa/design-system` where applicable.
- Any dead globals.css rules removed (after `grep -rE` confirmation).
- All Phase 2 coverage tests pass.
- Regression sweep on PR #382 / #384 / #385 / #386 / #387 / #388 protected files stays GREEN.
- `npx --no-install next build` → exit 0; 6 routes prerendered.
- `git diff --check` → clean.

## Risks + follow-ups (out of scope)

- The 8 Playwright follow-up failures from PR #386 remain.
- Other Phase 2 consumers (Explorer, Splitter, FileTree, Viewer) still use inline Tailwind + `.fex-*`.
- AppShell may end up with minimal/no migration (most of the AppShell surface uses specialized patterns). That's OK — the Phase 2 coverage tests document the decision.

## Rollback

If anything fails, run `git restore src/modules/app-shell/presentation/AppShell.tsx src/modules/app-shell/presentation/AppShellHeader.tsx src/modules/app-shell/presentation/AppShellFooter.tsx src/modules/app-shell/presentation/AppShellNav.tsx src/modules/app-shell/presentation/AppShellGlobalSearch.tsx src/app/globals.css tests/test_app_shell_render.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.