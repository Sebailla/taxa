/**
 * Public `@taxa/browser-state/tree-source` entry point.
 *
 * ODD-BSTATE-TAX-002 — strict-continuation: the main route's
 * bundle MUST carry ONLY the typed-source chain
 * (`taxa.tree.source`). Importing `useTreeSource` through the
 * aggregate `@taxa/browser-state` barrel pulls the four per-key
 * stores into a shared chunk that the main route ends up
 * referencing, which fails the strict chunk-boundary witness
 * in
 * `tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`.
 *
 * This entry point exposes JUST the typed-source surface:
 *
 *   - `useTreeSource`           → the hydration-safe React
 *                                  hook (the typed default
 *                                  `"col"` is what SSR + the
 *                                  first client render return;
 *                                  the stored value rehydrates
 *                                  on the post-mount render).
 *   - `TreeSource` (type)       → the typed literal union
 *                                  `"col" | "worms" | "freshwater"`
 *                                  sourced from the browser-state
 *                                  domain layer.
 *   - `DEFAULT_TREE_SOURCE`     → the typed default value
 *                                  (`"col"`); declared in the
 *                                  browser-state domain layer so
 *                                  every consumer agrees on the
 *                                  first-render value.
 *
 * **Strict chain independence.** The entry point re-exports the
 * hook directly from `./application/useTreeSource` so the import
 * graph is:
 *
 *   `TaxonomyTree → tree-source → useTreeSource → storeTreeSource`
 *
 * with `domain/defaults.ts` reached for `DEFAULT_TREE_SOURCE`
 * (which exports typed defaults for all four keys but contains
 * NO localStorage key literals — those literals live in
 * `domain/keys.ts`, which is `import type`-only consumed by the
 * store / hook chain so the chunk-boundary witness stays green).
 *
 * **Aggregate surface stays untouched.** The main route's barrel
 * contract is the dedicated entry point; the hydration probe
 * route (`src/app/hydration-probe/page.tsx`) keeps importing
 * `HydrationProbe` through the aggregate `@taxa/browser-state`
 * barrel because the probe legitimately needs all four chains.
 * Both surfaces are legal; consumers choose the one matching
 * their scope.
 *
 * **Scope discipline.** The entry point MUST NOT re-export
 * anything beyond the typed-source surface (no `useTheme`, no
 * `useLastTaxonId`, no `useKebabOpenId`, no `reset`, no sibling
 * store read/write/subscribe functions). The wider surface
 * belongs to the aggregate barrel; widening this entry point
 * would silently re-bundle the forbidden chains into the main
 * route's bundle.
 */
export { useTreeSource } from "./application/useTreeSource";
export type { TreeSource } from "./domain/keys";
export { DEFAULT_TREE_SOURCE } from "./domain/defaults";
