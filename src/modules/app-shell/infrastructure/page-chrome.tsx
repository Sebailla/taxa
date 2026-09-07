/**
 * Page chrome — header tabs, theme toggle, help / settings / banner hosts (PR 4b.3).
 *
 * Renders the host-side skeleton the AppShell composes on top of:
 *
 *   - `<header>` with the primary nav tabs (`data-action="nav-tab"` /
 *     `data-path="<tab>"` — pinned by tests/test_hydration_console.py
 *     so the e2e + screenshot harnesses can drive navigation without
 *     coupling to copy).
 *   - A theme toggle (`data-action="theme-toggle"`) that stamps /
 *     unstamps `data-theme` on `<html>` via the typed `browser-state`
 *     store. The store is the SINGLE write site per key (4 + 4
 *     contract enforced by tests/test_browser_state_keys.py).
 *   - Help / settings / banner hosts — empty placeholders that later
 *     PRs (PR 5a, PR 5b) populate with the kebab menu, the Search /
 *     Folder tabs, and the help overlay.
 *   - `<main>` wrapper carrying `data-selected` / `data-tree` so the
 *     taxonomy presentation layer (PR 5a) can read the shell state
 *     without re-reading `localStorage`.
 *
 * `PageChrome` is `presentation`-adjacent — the styled DOM lives
 * here, the typed-state machine lives in `AppShell.tsx`. The page-
 * chrome does not own a store; the AppShell passes a single
 * `BrowserStateStore` instance and the rehydrated `ShellState`.
 */

"use client";

import { useCallback, type ReactElement, type ReactNode } from "react";

import {
  type BrowserStateStore,
} from "@taxa/browser-state";

/** Pinned tab list — order is part of the G2 chrome contract. */
const NAV_TABS: ReadonlyArray<{ path: string; label: string }> = [
  { path: "browser", label: "Browser" },
  { path: "classification", label: "Classification" },
  { path: "settings", label: "Settings" },
];

/** Canonical default for the primary-tab state. Classification is
 *  the legacy landing surface; Browser is the new global research
 *  surface (5b.4). */
export const DEFAULT_NAV_TAB = "classification";

export type NavTabPath = "browser" | "classification" | "settings";

export interface ShellState {
  selected: string | null;
  tree: string | null;
  lastTaxonId: number | null;
}

export interface PageChromeProps {
  /** True after the first `useEffect` — gates theme-write availability. */
  mounted: boolean;
  /** Rehydrated shell state (AppShell owns the source of truth). */
  state: ShellState;
  /** Typed store — passed through so the theme toggle persists writes. */
  store: BrowserStateStore | null;
  /** Active primary nav tab (5b.4 addendum). Drives the
   *  `aria-selected` / `data-tab-active` attribute on each nav button. */
  activeTab: NavTabPath;
  /** Called when the user clicks a nav tab. */
  onNavTab: (path: NavTabPath) => void;
  children: ReactNode;
}

export function PageChrome({
  mounted,
  state,
  store,
  activeTab,
  onNavTab,
  children,
}: PageChromeProps): ReactElement {
  // Theme toggle — stamps/unstamps `data-theme` on <html> via the typed
  // store. Before mount the toggle is a no-op (graceful degradation:
  // theme stays at the SSR default until rehydration). The single
  // `setTheme` call below is the only write site for `taxa.settings.theme`
  // outside the typed store factory's own seeded writes.
  const handleToggleTheme = useCallback((): void => {
    if (!mounted || !store) return;
    const html = document.documentElement;
    const nextTheme: "light" | "dark" =
      html.dataset.theme === "dark" ? "light" : "dark";
    if (nextTheme === "dark") {
      html.dataset.theme = "dark";
    } else {
      delete html.dataset.theme;
    }
    store.setTheme(nextTheme);
  }, [mounted, store]);

  const handleNavClick = useCallback((path: NavTabPath) => {
    onNavTab(path);
  }, [onNavTab]);

  return (
    <>
      <header data-mounted={mounted ? "true" : "false"}
              data-active-tab={activeTab}>
        <nav role="tablist" aria-label="Primary">
          {NAV_TABS.map((tab) => {
            const isActive = tab.path === activeTab;
            return (
              <button
                key={tab.path}
                type="button"
                role="tab"
                data-action="nav-tab"
                data-path={tab.path}
                data-tab-active={isActive ? "true" : "false"}
                aria-selected={isActive ? "true" : "false"}
                onClick={() => handleNavClick(tab.path as NavTabPath)}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
        <button
          type="button"
          data-action="theme-toggle"
          aria-label="Toggle theme"
          onClick={handleToggleTheme}
          disabled={!mounted}
        >
          Theme
        </button>
      </header>
      <main
        data-selected={state.selected ?? ""}
        data-tree={state.tree ?? ""}
        data-active-tab={activeTab}
      >
        {children}
      </main>
      <div
        role="region"
        aria-label="Help shell"
        data-slot="help-shell"
        hidden
      />
      <div
        role="region"
        aria-label="Settings view"
        data-slot="settings-view"
        hidden
      />
      <div
        role="region"
        aria-label="Banner host"
        data-slot="banner-host"
        hidden
      />
    </>
  );
}
