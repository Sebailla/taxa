/**
 * `BrowserStateStoreContext` — typed-store React context (PR 5c.1b-A).
 *
 * AppShell owns the single typed `BrowserStateStore` instance for the
 * application lifetime (see `presentation/AppShell.tsx`); the context
 * publishes that SAME instance to descendants so cross-module consumers
 * (currently only `src/app/page.tsx`, which reads the `treeSource`
 * value to drive `useTaxonTree`) can subscribe via
 * `useSyncExternalStore` WITHOUT constructing a parallel store.
 *
 * Spec.md rule 5 hygiene: this context lives in `presentation/`
 * (React is allowed there per rule 4) and is re-exported through the
 * `app-shell` public barrel. Cross-module consumers import via
 * `@taxa/app-shell` — never by deep import.
 *
 * The hook (`useBrowserStateStore`) returns the typed store; reading
 * an individual key is then `useSyncExternalStore`-wrapped at the
 * call site (page.tsx owns that wiring so the AppShell stays free of
 * per-key selector logic).
 */

"use client";

import { createContext, useContext } from "react";

import type { BrowserStateStore } from "@taxa/browser-state";

/** Context value — the single typed store instance. */
export const BrowserStateStoreContext = createContext<BrowserStateStore | null>(null);

BrowserStateStoreContext.displayName = "BrowserStateStoreContext";

/** Returns the single typed store, or `null` if no AppShell is
 *  mounted above the call site. Callers that require a non-null
 *  store (e.g. `useTaxonTree` for the `treeSource` value) MUST be
 *  rendered under `<AppShell>` — see `src/app/layout.tsx`. */
export function useBrowserStateStore(): BrowserStateStore | null {
  return useContext(BrowserStateStoreContext);
}
