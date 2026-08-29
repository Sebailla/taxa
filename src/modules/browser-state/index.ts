/**
 * Public barrel for the `browser-state` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/browser-state` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * PR 2a (Phase 2 scaffold work unit) ships an empty barrel — the real
 * exports land with the PR 4 browser-state work unit (tasks 4.1–4.4):
 *   - `keys.ts`                  → four localStorage keys, exactly
 *                                  one getItem + one setItem each
 *   - `defaults.ts`              → typed default values
 *   - `store.ts`                 → useThemeStore, useTreeSourceStore,
 *                                  useLastTaxonStore, useKebabStore
 *                                  (each behind a `mounted` flag)
 *
 * Rehydration gates behind a `mounted` flag inside `useEffect` to
 * prevent SSR/CSR hydration mismatches. The four keys are pinned:
 *   - `theme`            → "light" | "dark"
 *   - `tree-source`      → "col"   | "worms"
 *   - `last-taxon-id`    → number | null
 *   - `kebab-open-id`    → string | null
 *
 * An empty barrel is intentionally a no-op re-export so this file is
 * a valid TypeScript module and `tsc --noEmit` accepts it.
 */
export {};
