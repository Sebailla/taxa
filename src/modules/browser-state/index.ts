/**
 * Public barrel for the `browser-state` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/browser-state` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * ODD-BSTATE-001 ships the typed four-key browser-state prerequisite:
 *   - `domain/keys.ts`        → typed `StorageKey` union + the four
 *                               `localStorage` literals
 *                               (`taxa.settings.theme`,
 *                                `taxa.tree.source`,
 *                                `taxa.tree.lastTaxonId`,
 *                                `taxa.tree.kebabOpenId`) plus the
 *                                `Listener` / `Unsubscribe` types.
 *   - `domain/defaults.ts`    → typed defaults per key (theme:
 *                                `"light"`, tree-source: `"col"`,
 *                                last-taxon-id / kebab-open-id:
 *                                `null`).
 *   - `infrastructure/store.ts` → typed `read*` / `write*` /
 *                                `subscribe*` surface per key plus
 *                                `reset()`. The ONLY place in the
 *                                project that touches `localStorage`;
 *                                every storage failure (private mode
 *                                / quota exceeded / missing `window`
 *                                during SSR) is swallowed via
 *                                `safeStorage` and the typed default
 *                                is returned so the application keeps
 *                                rendering.
 *   - `application/useBrowserStateKey.ts` → hydration-safe React
 *                                hooks (`useTheme`, `useTreeSource`,
 *                                `useLastTaxonId`, `useKebabOpenId`)
 *                                built on `useSyncExternalStore`. The
 *                                server snapshot is the typed default;
 *                                the first client render agrees; the
 *                                post-mount render returns the stored
 *                                value, so React's hydration guard
 *                                never trips.
 *
 * The barrel re-exports only the typed surface — no raw
 * `localStorage` getter/setter leaks through here, so cross-module
 * consumers cannot bypass the typed store.
 */
export {
  THEME_STORAGE_KEY,
  TREE_SOURCE_STORAGE_KEY,
  LAST_TAXON_ID_STORAGE_KEY,
  KEBAB_OPEN_ID_STORAGE_KEY,
  ALL_STORAGE_KEYS,
} from "./domain/keys";
export type {
  StorageKey,
  Listener,
  Unsubscribe,
  Theme,
  TreeSource,
} from "./domain/keys";

export {
  DEFAULT_THEME,
  DEFAULT_TREE_SOURCE,
  DEFAULT_LAST_TAXON_ID,
  DEFAULT_KEBAB_OPEN_ID,
} from "./domain/defaults";

export {
  readTheme,
  writeTheme,
  subscribeTheme,
  readTreeSource,
  writeTreeSource,
  subscribeTreeSource,
  readLastTaxonId,
  writeLastTaxonId,
  subscribeLastTaxonId,
  readKebabOpenId,
  writeKebabOpenId,
  subscribeKebabOpenId,
  reset,
} from "./infrastructure/store";

export {
  useTheme,
  useTreeSource,
  useLastTaxonId,
  useKebabOpenId,
} from "./application/useBrowserStateKey";
