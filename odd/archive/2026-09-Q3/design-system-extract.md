# Design-system extract — Phase 1: ship the primitives barrel

## Objective

Close the original P1 from the 2026-09-23 critique (21/40) + the re-critique (28/40):

> "design-system module is a placeholder; no tokens module, no component library, no primitives. The shared visual world lives entirely in globals.css (2,721 lines) and the Tailwind 4 @theme block. Meanwhile, the taxonomy tree composes visual states with inline Tailwind utilities, and the explorer uses dedicated .fex-* classes. Both work. Neither shares a primitive."

This is a **LARGE P1** that warrants a phased approach. **Phase 1 (this branch)** ships the primitive components themselves in the `design-system` module + the typed `tokens.ts` domain surface. **Phase 2 (future branch)** migrates consumers (`TaxonomyTree`, `Explorer`, `TreeRow`, etc.) to use the primitives — large refactor, separate scope.

Phase 1 scope: ship 8 primitives + the token surface + the barrel exports + the global stylesheet migration. No consumer changes in Phase 1.

## User decision

- Phased approach (Phase 1 first, Phase 2 later).
- Push + PR creation + merge remain the user's decisions.

## Phase 1 Scope

### Tokens (domain layer)

Create `src/modules/design-system/domain/tokens.ts` — typed design-token surface that mirrors the Tailwind 4 `@theme` block in `globals.css`. Re-export the legacy CSS variables as TypeScript constants so feature components can read them with full type-safety:

- `surfaceContainerLowest`, `surfaceContainerLow`, `surfaceContainer`, `surfaceContainerHigh`, `surfaceContainerHighest` (the `surface-container-*` family — 5 tokens)
- `surface`, `onSurface`, `onSurfaceVariant`, `outline`, `outlineVariant` (4 tokens)
- `primary`, `accent`, `onPrimary` (3 tokens)
- `elevated` (1 token)
- `realmBacteria`, `realmArchaea`, `realmViruses`, `realmAnimalia`, `realmFungi`, `realmPlantae`, `realmChromista`, `realmOther` (8 tokens)

Total: 21 typed tokens. Re-export from the public barrel.

### Components (presentation layer)

8 primitives in `src/modules/design-system/presentation/`. Each is a small Server Component (no `"use client"` unless it needs interactivity). Each has a typed Props surface. Each re-exports from the public barrel.

1. **`Button`** (`src/modules/design-system/presentation/Button.tsx`)
   - 3 variants: `primary` (filled `bg-primary text-on-primary`), `secondary` (outline `border-outline-variant text-on-surface`), `ghost` (no border, hover `bg-surface-container-low`).
   - 2 sizes: `sm` (`text-xs px-3 py-1.5`), `md` (`text-sm px-4 py-2`).
   - Props: `variant?: ButtonVariant`, `size?: ButtonSize`, `children`, plus standard `<button>` HTML attrs.
   - Uses Tailwind utility classes (no new CSS in globals.css).

2. **`IconButton`** (`src/modules/design-system/presentation/IconButton.tsx`)
   - 2 variants: `default` (`text-on-surface-variant hover:text-primary`), `subtle` (`text-on-surface-variant hover:bg-surface-container-low`).
   - Props: `variant?`, `children: ReactNode` (the icon glyph), `aria-label` (required for a11y), plus standard `<button>` HTML attrs.
   - Replaces the `material-symbols-outlined text-[14px] text-on-surface-variant hover:text-primary transition-colors` pattern that appears in `TreeRow`, `AppShellHeader`, etc.

3. **`Badge`** (`src/modules/design-system/presentation/Badge.tsx`)
   - 4 variants: `default` (`bg-surface-container-highest text-on-surface-variant`), `primary` (`bg-primary/10 text-primary`), `warning` (`bg-red-50 text-red-700`), `subtle` (`bg-surface text-on-surface-variant`).
   - Props: `variant?`, `children`, `uppercase?: boolean` (defaults to `true` for the rank-badge pattern).
   - Replaces the `rank-badge text-on-surface-variant bg-surface-container-highest uppercase tracking-[0.1em] px-2 py-0.5 rounded` pattern.

4. **`Card`** (`src/modules/design-system/presentation/Card.tsx`)
   - 3 variants: `default` (`bg-surface border border-outline-variant rounded-md`), `elevated` (with `box-shadow` matching the detail panel cascade), `subtle` (`bg-surface-container-low rounded-md`).
   - Props: `variant?`, `children`, `className?`.
   - Replaces the `.detail-panel { border: 1px solid var(--outline-variant); border-radius: 16px; box-shadow: ... }` cascade.

5. **`EmptyState`** (`src/modules/design-system/presentation/EmptyState.tsx`)
   - Props: `icon?: ReactNode`, `title: string`, `description?: string`, `children?: ReactNode` (for CTA buttons), `size?: "sm" | "md" | "lg"`.
   - Replaces the `.fex-empty-state` cascade + the inline `flex flex-col items-center justify-center gap-2 px-2 py-6 text-center text-on-surface-variant` pattern.

6. **`Spinner`** (`src/modules/design-system/presentation/Spinner.tsx`)
   - Client Component (uses `useEffect` for accessibility announcement, optional).
   - Props: `size?: "sm" | "md"`, `label?: string` (default `"Loading…"`).
   - Replaces the `.animate-spin` + `material-symbols-outlined progress_activity` pattern in `Explorer`, `DetailPanel`, etc.

7. **`InlineMessage`** (`src/modules/design-system/presentation/InlineMessage.tsx`)
   - 3 variants: `info` (default `bg-surface-container-low border-outline-variant text-on-surface-variant`), `error` (`bg-red-50 border-red-200 text-red-700`), `success` (`bg-green-50 border-green-200 text-green-700`).
   - Props: `variant?`, `children`, `className?`.
   - Replaces the `mt-2 rounded-md border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface-variant` inline status pattern.

8. **`Text`** (`src/modules/design-system/presentation/Text.tsx`)
   - 5 variants: `body` (default), `body-sm`, `mono` (uses `font-mono-data`), `caption` (uses `text-on-surface-variant text-xs`), `label` (uses `font-semibold text-on-surface`).
   - Props: `variant?`, `as?: "p" | "span" | "div"` (defaults to `p`), `children`, `className?`.
   - Centralizes the `text-on-surface` / `text-on-surface-variant` / `text-body-sm` / `font-mono-data` typography decisions.

### Tailwind 4 utility surface — no new globals.css rules

All primitives use existing Tailwind utilities that map to the `@theme` tokens in `globals.css`. NO new CSS rules in `globals.css` for Phase 1 — the design tokens are already there; Phase 1 just gives them a typed component surface.

The `globals.css` rule surface stays byte-identical to PR #384 (which is identical to PR #383 which is identical to PR #382). This is critical: the alphabetical-order test + the research_styles tests + the chunk-boundary contract all stay green without any globals.css churn.

### Barrel

Update `src/modules/design-system/index.ts` to re-export the 8 components + the token surface.

## Non-goals

- Migrating consumers to use the primitives (Phase 2 — separate branch).
- Removing or replacing existing `.fex-*` selectors in `globals.css` (Phase 3 if needed).
- Replacing Tailwind utility compositions in `TreeRow`, `TaxonomyTree`, `Explorer`, `DetailPanel` (Phase 2).
- Adding design tokens (Phase 1 mirrors what's already in `@theme`; does not add new ones).
- Removing the existing placeholder content from `src/modules/design-system/index.ts` (it's the public barrel; Phase 1 expands it).

## TDD discipline

Per primitive:

1. **FIRST add tests** in a new `tests/test_design_system_primitives.py` (or extend `tests/test_app_shell_render.py` if the test fits better there):
   - Each component gets 2-4 tests:
     - Renders without crashing with the documented props
     - Renders the documented children / content
     - Applies the documented Tailwind class per variant
     - A11y attributes are correct (e.g. `aria-label` is required on `IconButton`)
   - The token surface gets a typecheck test (`tsc --noEmit`) — the test file imports the tokens + verifies they match the CSS custom property names in `globals.css`.
2. Run new tests → confirm RED.
3. Ship the primitive file + the barrel re-export.
4. Run new tests → confirm GREEN.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch `src/app/globals.css` (no new CSS rules; Phase 1 is pure component extraction).
- DO NOT touch any consumer (`TreeRow`, `TaxonomyTree`, `Explorer`, `DetailPanel`, etc.) — Phase 2 work.
- DO NOT remove the existing comment block from `src/modules/design-system/index.ts` that documents PR 2a. Add new re-exports BELOW the existing `export {}` line.
- The new `tests/test_design_system_primitives.py` MUST NOT break the PR #382 + #384 contracts (regression sweep).
- `npx --no-install next build` MUST exit 0 (the build emits the 6 routes unchanged).

## Allowed edit surfaces

src/modules/design-system/index.ts
src/modules/design-system/domain/tokens.ts (new)
src/modules/design-system/presentation/Button.tsx (new)
src/modules/design-system/presentation/IconButton.tsx (new)
src/modules/design-system/presentation/Badge.tsx (new)
src/modules/design-system/presentation/Card.tsx (new)
src/modules/design-system/presentation/EmptyState.tsx (new)
src/modules/design-system/presentation/Spinner.tsx (new)
src/modules/design-system/presentation/InlineMessage.tsx (new)
src/modules/design-system/presentation/Text.tsx (new)
tests/test_design_system_primitives.py (new)

## Files referenced (read-only)

src/app/globals.css (the @theme block + the @layer components cascade — read for the existing Tailwind utility mapping + the design tokens)

## Acceptance criteria

- All 8 primitives exported from `@taxa/design-system` barrel.
- `domain/tokens.ts` exports the typed surface for all 21 tokens.
- New tests in `tests/test_design_system_primitives.py` cover each primitive (2-4 tests per primitive + a token surface typecheck test) and ALL pass.
- Regression sweep on PR #382 + #384 protected test files stays GREEN (the new primitives don't break any existing test contract).
- `npx --no-install next build` exits 0; 6 routes prerendered.
- `git diff --check` clean.
- No consumer migration in Phase 1 (the existing components keep their inline Tailwind utility compositions / `.fex-*` classes).

## Risks + follow-ups (out of scope)

- Phase 2 (consumer migration): each consumer (`TreeRow`, `TaxonomyTree`, `Explorer`, `DetailPanel`, `Splitter`, `FileTree`, `Viewer`) gets refactored to use the primitives. This is the LARGER work — could be 4-8 PRs depending on how aggressive the migration is.
- The `.fex-*` cascade in `globals.css` could be deprecated and removed in Phase 3 once no consumer uses it. Defer until Phase 2 is complete.
- The design tokens are currently CSS custom properties in `@theme`. A future PR could move them to a runtime-loaded JSON file for SSR consistency. Out of scope.
- Adding new tokens (e.g. `surface-container-lowest` if it doesn't exist; check `globals.css:30-37`) is out of scope. Phase 1 mirrors what's already in `@theme`.

## Rollback

If anything fails, run `git restore src/modules/design-system/index.ts src/modules/design-system/domain/tokens.ts src/modules/design-system/presentation/Button.tsx src/modules/design-system/presentation/IconButton.tsx src/modules/design-system/presentation/Badge.tsx src/modules/design-system/presentation/Card.tsx src/modules/design-system/presentation/EmptyState.tsx src/modules/design-system/presentation/Spinner.tsx src/modules/design-system/presentation/InlineMessage.tsx src/modules/design-system/presentation/Text.tsx tests/test_design_system_primitives.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.