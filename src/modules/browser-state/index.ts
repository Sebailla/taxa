/**
 * Public barrel for the `browser-state` capability module (PR 4a).
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/browser-state` path alias). Direct imports
 * into the layer folders below are blocked by `.eslintrc.cjs`.
 *
 * PR 4a exports: the four pinned key literals, the typed defaults, the
 * typed value unions, the typed store factory + interface, and the
 * typed listener signature. The barrel exposes typed APIs only — the
 * raw platform-storage reference and the JSON helpers stay private
 * inside the infrastructure layer.
 */

export {
  BROWSER_STATE_KEYS,
  BROWSER_STATE_DEFAULTS,
  type BrowserStateKey,
  type BrowserStateValueMap,
  type Theme,
  type TreeSource,
} from "./domain/keys.js";

export {
  createBrowserStateStore,
  type BrowserStateStore,
} from "./infrastructure/store.js";

/** Typed listener signature used by `BrowserStateStore.subscribe`. */
export type BrowserStateListener = () => void;
