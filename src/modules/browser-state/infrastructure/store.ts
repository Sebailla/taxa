/**
 * Typed browser-state store (PR 4a, extended by PR 5c.1a).
 *
 * The store is the ONLY module that calls `getItem(` or `setItem(`:
 *   - 5 reads (one per BROWSER_STATE_KEYS entry, inside the factory body)
 *   - 5 writes (one per set* method, on every user-driven update)
 *   - try/catch around every storage call so SSR, private-browsing,
 *     and quota errors do not break the application
 *   - typed `subscribe(listener)` for change notifications (Phase 4b
 *     wraps this in `useSyncExternalStore` behind a `mounted` flag)
 *   - `reset()` that reverts all five keys to BROWSER_STATE_DEFAULTS
 *
 * The 5 + 5 contract is enforced statically by
 * `tests/test_browser_state_keys.py` (grep for `getItem(` / `setItem(`
 * under `src/`). Every read and every write is written inline rather
 * than factored into a shared helper — a helper would collapse the
 * count below 5 and break the contract. PR 5c.1a extends the prior
 * PR 4a 4 + 4 contract by exactly one inline read and one inline
 * write for the `versionBannerDismissed` boolean; the React side of
 * the contract is deferred to PR 5c.1b.
 */

import {
  BROWSER_STATE_DEFAULTS,
  BROWSER_STATE_KEYS,
  isValidKebabOpenId,
  isValidTaxonId,
  isValidTheme,
  isValidTreeSource,
  isValidVersionBannerDismissed,
  type Theme,
  type TreeSource,
} from "../domain/keys";
import {
  getBrowserStorage,
  tryJsonParse,
  tryJsonStringify,
} from "./safe-storage";

/** Public store surface — 5 typed getters, 5 typed setters, a typed
 *  listener registration, and a reset back to defaults. */
export interface BrowserStateStore {
  getTheme():                  Theme;
  getTreeSource():             TreeSource;
  getLastTaxonId():            number | null;
  getKebabOpenId():            string | null;
  getVersionBannerDismissed(): boolean;
  setTheme(next: Theme):       void;
  setTreeSource(next: TreeSource):  void;
  setLastTaxonId(next: number | null): void;
  setKebabOpenId(next: string | null): void;
  setVersionBannerDismissed(next: boolean): void;
  subscribe(listener: () => void): () => void;
  reset(): void;
}

/** Factory that builds a fresh store with the five keys rehydrated from
 *  the safe-storage accessor. */
export function createBrowserStateStore(): BrowserStateStore {
  const storage = getBrowserStorage();

  // 5 reads — one inline block per key so each contributes exactly one
  // `getItem(` token to the static count.
  let theme: Theme = BROWSER_STATE_DEFAULTS.theme;
  {
    let raw: string | null = null;
    try {
      raw = storage?.getItem(BROWSER_STATE_KEYS.theme) ?? null;
    } catch {
      raw = null;
    }
    theme = tryJsonParse<Theme>(raw, theme, isValidTheme);
  }

  let treeSource: TreeSource = BROWSER_STATE_DEFAULTS.treeSource;
  {
    let raw: string | null = null;
    try {
      raw = storage?.getItem(BROWSER_STATE_KEYS.treeSource) ?? null;
    } catch {
      raw = null;
    }
    treeSource = tryJsonParse<TreeSource>(raw, treeSource, isValidTreeSource);
  }

  let lastTaxonId: number | null = BROWSER_STATE_DEFAULTS.lastTaxonId;
  {
    let raw: string | null = null;
    try {
      raw = storage?.getItem(BROWSER_STATE_KEYS.lastTaxonId) ?? null;
    } catch {
      raw = null;
    }
    lastTaxonId = tryJsonParse<number | null>(raw, lastTaxonId, isValidTaxonId);
  }

  let kebabOpenId: string | null = BROWSER_STATE_DEFAULTS.kebabOpenId;
  {
    let raw: string | null = null;
    try {
      raw = storage?.getItem(BROWSER_STATE_KEYS.kebabOpenId) ?? null;
    } catch {
      raw = null;
    }
    kebabOpenId = tryJsonParse<string | null>(raw, kebabOpenId, isValidKebabOpenId);
  }

  let versionBannerDismissed: boolean =
    BROWSER_STATE_DEFAULTS.versionBannerDismissed;
  {
    let raw: string | null = null;
    try {
      raw = storage?.getItem(BROWSER_STATE_KEYS.versionBannerDismissed) ?? null;
    } catch {
      raw = null;
    }
    versionBannerDismissed = tryJsonParse<boolean>(
      raw,
      versionBannerDismissed,
      isValidVersionBannerDismissed,
    );
  }

  const listeners = new Set<() => void>();
  function notify(): void {
    for (const listener of listeners) listener();
  }

  // 5 writes — one inline block per setter so each contributes exactly
  // one `setItem(` token to the static count.
  function setTheme(next: Theme): void {
    theme = next;
    const serialized = tryJsonStringify(next);
    if (serialized === null) return;
    try {
      storage?.setItem(BROWSER_STATE_KEYS.theme, serialized);
    } catch {
      /* storage quota / denied / removed; keep in-memory state */
    }
    notify();
  }

  function setTreeSource(next: TreeSource): void {
    treeSource = next;
    const serialized = tryJsonStringify(next);
    if (serialized === null) return;
    try {
      storage?.setItem(BROWSER_STATE_KEYS.treeSource, serialized);
    } catch {
      /* swallow */
    }
    notify();
  }

  function setLastTaxonId(next: number | null): void {
    lastTaxonId = next;
    const serialized = tryJsonStringify(next);
    if (serialized === null) return;
    try {
      storage?.setItem(BROWSER_STATE_KEYS.lastTaxonId, serialized);
    } catch {
      /* swallow */
    }
    notify();
  }

  function setKebabOpenId(next: string | null): void {
    kebabOpenId = next;
    const serialized = tryJsonStringify(next);
    if (serialized === null) return;
    try {
      storage?.setItem(BROWSER_STATE_KEYS.kebabOpenId, serialized);
    } catch {
      /* swallow */
    }
    notify();
  }

  function setVersionBannerDismissed(next: boolean): void {
    versionBannerDismissed = next;
    const serialized = tryJsonStringify(next);
    if (serialized === null) return;
    try {
      storage?.setItem(BROWSER_STATE_KEYS.versionBannerDismissed, serialized);
    } catch {
      /* swallow */
    }
    notify();
  }

  // reset() reuses the five existing setters above; no extra `setItem(`
  // call sites are introduced, so the 5 + 5 contract stays intact.
  function reset(): void {
    setTheme(BROWSER_STATE_DEFAULTS.theme);
    setTreeSource(BROWSER_STATE_DEFAULTS.treeSource);
    setLastTaxonId(BROWSER_STATE_DEFAULTS.lastTaxonId);
    setKebabOpenId(BROWSER_STATE_DEFAULTS.kebabOpenId);
    setVersionBannerDismissed(BROWSER_STATE_DEFAULTS.versionBannerDismissed);
  }

  return {
    getTheme:                  () => theme,
    getTreeSource:             () => treeSource,
    getLastTaxonId:            () => lastTaxonId,
    getKebabOpenId:            () => kebabOpenId,
    getVersionBannerDismissed: () => versionBannerDismissed,
    setTheme,
    setTreeSource,
    setLastTaxonId,
    setKebabOpenId,
    setVersionBannerDismissed,
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    reset,
  };
}
