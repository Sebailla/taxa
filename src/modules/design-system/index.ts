/**
 * Public barrel for the `design-system` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via `@taxa/design-system`). Deep imports into the layer
 * folders below are blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * Exports: `TabStrip` + types (PR 5b.4); `Icon` / `Button` + types
 * (PR 3c-iv-barrel.3 / .4); `THEME_TOKENS` + `ThemeToken` typed token
 * surface (3c-iv-barrel.2 — literal hex values live in
 * `src/app/globals.css::@theme`).
 */

export {
  THEME_TOKENS,
  type ThemeToken,
} from "./infrastructure";
export {
  Button,
  type ButtonProps,
  Icon,
  type IconName,
  type IconProps,
  TabStrip,
  type TabDefinition,
  type TabStripProps,
} from "./presentation";
