/**
 * Typed literals + defaults for the four browser-state keys (PR 4a).
 *
 * Domain layer — spec.md rule 4: no React, no I/O, no browser, no HTTP,
 * no framework tokens. Pure types + as-const literals + type guards.
 * Everything else lives in infrastructure / application / presentation.
 *
 * The file-explorer panel width is intentionally absent: it is a
 * research concern and lives outside this module. Consumers that need
 * it import from `@taxa/research` (Phase 5a work, not 4a).
 */

export const BROWSER_STATE_KEYS = {
  theme:       "taxa.settings.theme",
  treeSource:  "taxa.tree.source",
  lastTaxonId: "taxa.tree.lastTaxonId",
  kebabOpenId: "taxa.tree.kebabOpenId",
} as const;

export type BrowserStateKey =
  (typeof BROWSER_STATE_KEYS)[keyof typeof BROWSER_STATE_KEYS];

export type Theme = "light" | "dark";
export type TreeSource = "col" | "worms";

export interface BrowserStateValueMap {
  theme:       Theme;
  treeSource:  TreeSource;
  lastTaxonId: number | null;
  kebabOpenId: string | null;
}

export const BROWSER_STATE_DEFAULTS: Readonly<BrowserStateValueMap> = {
  theme:       "light",
  treeSource:  "col",
  lastTaxonId: null,
  kebabOpenId: null,
};

export function isValidTheme(value: unknown): value is Theme {
  return value === "light" || value === "dark";
}

export function isValidTreeSource(value: unknown): value is TreeSource {
  return value === "col" || value === "worms";
}

export function isValidTaxonId(value: unknown): value is number | null {
  return (
    value === null ||
    (typeof value === "number" && Number.isFinite(value) && Number.isInteger(value))
  );
}

export function isValidKebabOpenId(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}
