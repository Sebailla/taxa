/**
 * AppShell — root chrome shell (PR 4b.2 + PR 4b.6 integration seam).
 *
 * Owns the typed `browser-state` store instance for the application
 * lifetime and gates every persisted-state read behind the
 * `useMounted()` flag so:
 *
 *   - SSR + initial CSR both render with `mounted = false` (the empty
 *     state — `selected: null`, `tree: null`, `last-taxon-id: null`).
 *     The DOM the server emits is byte-identical to what React would
 *     emit on the first client render, so React's hydration guard
 *     never trips.
 *
 *   - Once `mounted` flips (post-`useEffect`), the AppShell reads the
 *     typed store, applies the rehydrated state (`last-taxon-id`), and
 *     updates the URL via `history.replaceState` if a stored taxon
 *     exists. `replaceState` (not `pushState`) keeps the back button
 *     honest — `last-taxon-id` is *resume* state, not navigation.
 *
 * The AppShell is the only module that constructs a store; descendant
 * components (the taxonomy tree in PR 5a, the research explorer in
 * PR 5b) consume the same instance via React context (PR 5a) or by
 * re-reading via `useSyncExternalStore` on a context-exposed store
 * reference. PR 4b only ships the gating pattern; context plumbing
 * lands with PR 5a.
 */

"use client";

import { useEffect, useState, type ReactElement, type ReactNode } from "react";

import {
  createBrowserStateStore,
  useMounted,
  type BrowserStateStore,
} from "@taxa/browser-state";

import {
  PageChrome,
  type ShellState,
} from "../infrastructure/page-chrome";

/** Empty state — every shell attribute defaults to null on first paint. */
const EMPTY_STATE: ShellState = {
  selected: null,
  tree: null,
  lastTaxonId: null,
};

export function AppShell({
  children,
}: {
  children: ReactNode;
}): ReactElement {
  const mounted = useMounted();

  // Lazy-initialised store — runs ONCE per AppShell mount. SSR returns
  // a real store object but no read fires during the server render;
  // the first read is inside the `useEffect` below, gated by `mounted`.
  const [store] = useState<BrowserStateStore>(() =>
    createBrowserStateStore(),
  );

  const [state, setState] = useState<ShellState>(EMPTY_STATE);

  useEffect(() => {
    if (!mounted) return;

    // Rehydrate the persisted `last-taxon-id` and reflect it on the URL.
    const lastTaxonId = store.getLastTaxonId();
    setState({
      selected: null,
      tree: null,
      lastTaxonId,
    });

    // Stamp the persisted theme on <html> — the page-chrome toggle
    // handles future user-driven flips; this effect handles the
    // initial rehydration from `localStorage`.
    const theme = store.getTheme();
    if (typeof document !== "undefined") {
      if (theme === "dark") {
        document.documentElement.dataset.theme = "dark";
      } else {
        delete document.documentElement.dataset.theme;
      }
    }

    if (lastTaxonId !== null && typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("taxon", String(lastTaxonId));
      // `replaceState` (not push) — `last-taxon-id` is resume state,
      // not a navigation the user requested.
      window.history.replaceState(
        window.history.state,
        "",
        url.toString(),
      );
    }
  }, [mounted, store]);

  return (
    <PageChrome mounted={mounted} state={state} store={mounted ? store : null}>
      {children}
    </PageChrome>
  );
}