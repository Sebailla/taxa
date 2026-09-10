// Infrastructure barrel for the design-system module (3c-iv-barrel.2).
// Re-exports `<Icon>` + `<Button>` + the typed theme-token NAMES
// (`THEME_TOKENS` + `ThemeToken`); hex values live in
// `src/app/globals.css::@theme` — consumers import the typed NAME
// (e.g. `var(--primary)`), never the literal.

export {
  Button,
  type ButtonProps,
  Icon,
  type IconName,
  type IconProps,
} from "../presentation";

export const THEME_TOKENS = [
  "--accent",
  "--elevated",
  "--on-primary-fixed",
  "--on-surface",
  "--on-surface-variant",
  "--outline",
  "--outline-variant",
  "--primary",
  "--primary-fixed",
  "--realm-animalia",
  "--realm-archaea",
  "--realm-bacteria",
  "--realm-chromista",
  "--realm-fungi",
  "--realm-other",
  "--realm-plantae",
  "--realm-viruses",
  "--surface",
  "--surface-container",
  "--surface-container-high",
  "--surface-container-highest",
  "--surface-container-low",
] as const;

export type ThemeToken = (typeof THEME_TOKENS)[number];
