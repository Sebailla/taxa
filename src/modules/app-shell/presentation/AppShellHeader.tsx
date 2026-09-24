/**
 * AppShellHeader — the ODD-ASN-002 header row.
 *
 * Server component (no `"use client"`): the brand mark + the
 * static four-destination navigation layout are SSR-friendly, and
 * the only client-side concerns (the route-aware `usePathname()`
 * active affordance in `AppShellNav`, the global-search input +
 * keyboard wiring in `AppShellGlobalSearch`, the typed-source
 * segmented control in `AppShellSourceSelector`) live in client
 * islands nested inside this row.
 *
 * ODD-HSS-001 — the source-selector (CoL / WoRMS / Freshwater
 * segmented control) joined the header row. The selector used
 * to live inside `TaxonomyTree.tsx` and was only visible after
 * the user expanded the tree; the hoist promotes it to the
 * AppShell so it is visible on every route (and on every page
 * state — loading / error / empty / loaded) from the first
 * paint. See `AppShellSourceSelector.tsx` for the JSX render +
 * the typed-hook boundary.
 *
 * Layout: the selector sits BETWEEN the global-search flex
 * block AND the navigation `<AppShellNav />`. Placing it next
 * to the search input groups the two data-shape affordances
 * (typed source + typed search query) on the same row, with
 * the route nav at the right edge. The segmented control's own
 * height (32px from `.tree-source-toggle`) sits flush with the
 * search input + the nav row inside `flex items-center gap-4
 * px-6 py-3`, so the header reads as a single row even when
 * the source-selector is co-mounted.
 *
 * spec.md rule 4 / rule 5: this component depends only on React
 * + the design-system tokens in `globals.css`. No framework, no
 * HTTP, no browser-state — the navigation surface stays purely
 * declarative + the three client islands underneath stay
 * focused.
 */
import AppShellNav from "./AppShellNav";
import AppShellGlobalSearch from "./AppShellGlobalSearch";
import AppShellSourceSelector from "./AppShellSourceSelector";

export interface AppShellHeaderProps {
  /** Optional lifted search query (ODD-ASN-002 controlled mode). */
  readonly searchQuery?: string;
  /** Optional lifted search-mutator (ODD-ASN-002 controlled mode). */
  readonly onSearchQueryChange?: (next: string) => void;
  /**
   * ODD-EXP-001 — the route that is rendering the AppShell.
   * Threads into `AppShellGlobalSearch` so the header search
   * input can become inert on `/explorer` (the global search
   * produces no results dropdown on the explorer route). On
   * every other route the search input stays fully active.
   */
  readonly currentRoute?:
    | "classification"
    | "explorer"
    | "help"
    | "settings"
    | "hydration-probe"
    | "not-found";
}

export default function AppShellHeader(
  props: AppShellHeaderProps,
): React.ReactElement {
  return (
    <header
      className="app-shell-header border-b border-outline-variant bg-surface"
      data-app-shell-header=""
    >
      <div className="mx-auto flex w-full max-w-5xl items-center gap-4 px-6 py-3">
        <a
          href="/"
          className="app-shell-brand font-semibold tracking-tight text-on-surface"
          data-app-shell-brand=""
        >
          taxa
        </a>
        <div className="app-shell-global-search flex-1">
          <AppShellGlobalSearch
            searchQuery={props.searchQuery}
            onSearchQueryChange={props.onSearchQueryChange}
            currentRoute={props.currentRoute}
          />
        </div>
        {/* ODD-HSS-001 — the source-selector is hoisted to the
            AppShell header so it is reachable on every route
            from the first paint. Rendered as a client island
            (the typed `useTreeSource()` hook is client-only).
            The selector's own segmented-control layout lives
            inside the `AppShellSourceSelector` component; this
            row simply slots it next to the global-search block
            + the route nav.

            The `.tree-source-toggle-wrapper` flex wrapper that
            ODD-NTP-003 introduced to share the 8px vertical
            rhythm between the source-selector + the collapse-all
            button row follows the source-selector through the
            hoist (the wrapper now hosts just the selector, with
            the flex layout + `margin: 8px 0` preserved). The
            CSS rule stays load-bearing for the ODD-PHASE3 dead-
            rule audit invariant; the wrapper class is no longer
            referenced in `TaxonomyTree.tsx`. */}
        <div className="tree-source-toggle-wrapper">
          <AppShellSourceSelector />
        </div>
        <AppShellNav />
      </div>
    </header>
  );
}
