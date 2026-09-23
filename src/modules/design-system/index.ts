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
 *
 * Phase 1 of ODD-DSE expands the barrel below: the typed token surface
 * (mirrors the `@theme` block in `globals.css`) + eight Server-Component
 * primitives (Button / IconButton / Badge / Card / EmptyState /
 * Spinner / InlineMessage / Text). Spinner is the only `"use client"`
 * primitive — it owns the aria-live announcement region via
 * `useEffect`. Cross-module consumers MUST keep importing from this
 * file (the `.eslintrc.cjs::no-restricted-imports` rule blocks deep
 * imports into the layer folders).
 */
export {};

// Re-exports added by ODD-DSE Phase 1. Order: tokens first, then
// presentation primitives. Keep the `export {};` placeholder above —
// the PR 2a comment block is the public rationale for the empty barrel
// and MUST stay byte-identical until the design-system fully retires.
export * from "./domain/tokens";
export { default as Button } from "./presentation/Button";
export { default as IconButton } from "./presentation/IconButton";
export { default as Badge } from "./presentation/Badge";
export { default as Card } from "./presentation/Card";
export { default as EmptyState } from "./presentation/EmptyState";
export { default as Spinner } from "./presentation/Spinner";
export { default as InlineMessage } from "./presentation/InlineMessage";
export { default as Text } from "./presentation/Text";
