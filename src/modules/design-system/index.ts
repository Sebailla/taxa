/**
 * Public barrel for the `design-system` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/design-system` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * PR 2a (Phase 2 scaffold work unit) ships an empty barrel — the real
 * exports land with the PR 3 frontend-bootstrap (tasks 3.1–3.8):
 *   - `infrastructure/globals.css`      → `@import "tailwindcss"` + `@theme`
 *   - `infrastructure/tailwind-preset.ts` → legacy utility → Tailwind 4 mapping
 *   - `domain/tokens.ts`                → typed design-token surface
 *
 * The legacy `--primary`, `--bg-surface`, `--realm-*` tokens resolve
 * unchanged because they are re-exported as aliases inside `@layer
 * base { :root { … } }` (design.md §Architecture Decisions, "Design
 * tokens" row).
 *
 * An empty barrel is intentionally a no-op re-export so this file is
 * a valid TypeScript module and `tsc --noEmit` accepts it.
 */
export {};
