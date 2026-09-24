/**
 * AppShell — the ODD-ASN-002 product navigation surface.
 *
 * Server component (no client directive): the shell composes the
 * brand mark + the four-destination nav (Header), the global
 * search input (a client island inside Header), the main pane,
 * and the three-column footer. No client boundary lives here —
 * the stateful concerns (search state + keyboard shortcuts)
 * belong to `AppShellGlobalSearch` (a client island nested
 * inside the Header), and the route-aware active-state marker
 * belongs to `AppShellNav` (a client island nested inside the
 * Header).
 *
 * ODD-ASN-002 contract:
 *
 *   - The skip-to-main `<a href="#main">` link is owned by
 *     `src/app/layout.tsx` (rendered BEFORE `{children}` so it
 *     is the FIRST focusable element on every route). The
 *     AppShell does NOT re-render the skip-link: every
 *     AppShell-mounted route inherits the layout's link, and
 *     the previous in-Shell duplicate made screen readers hear
 *     `Skip to main content` twice on `/`, `/explorer`, `/help`,
 *     `/settings`, and `/_not-found`. The AppShell's job is to
 *     mount the `<main id="main">` target the layout's
 *     skip-link resolves to — the affordance itself is
 *     upstream.
 *
 *   - Accepts optional `searchQuery` + `onSearchQueryChange`
 *     props so a parent (e.g. `src/app/page.tsx`) can lift the
 *     search state from the global input to a route-level owner.
 *     When the props are not provided the global search input
 *     owns the state internally — the `/explorer` route relies
 *     on the internal mode because `Explorer.tsx` ignores the
 *     search props for now.
 *
 *   - Renders the children inside `<main id="main">` so the
 *     layout's skip-link target resolves on every route.
 *
 * spec.md rule 4 / rule 5: AppShell depends on React + the
 * design-system tokens in `globals.css`. No HTTP, no
 * browser-state, no deep imports into other capability modules.
 */
import type { ReactNode } from "react";

import AppShellHeader from "./AppShellHeader";
import AppShellFooter from "./AppShellFooter";

export interface AppShellProps {
  readonly title: string;
  readonly apiOrigin: string;
  readonly schemaVersion?: string;
  /** Optional lifted search query (ODD-ASN-002 controlled mode). */
  readonly searchQuery?: string;
  /** Optional lifted search-mutator (ODD-ASN-002 controlled mode). */
  readonly onSearchQueryChange?: (next: string) => void;
  /**
   * ODD-EXP-001 — the route that is rendering the AppShell.
   * Threads into `AppShellGlobalSearch` so the header search
   * input can become inert on `/explorer` (the global search
   * produces no results dropdown on the explorer route — the
   * explorer's local file-search in the tree pane is the
   * primary search surface there). On every other route the
   * search input stays fully active.
   *
   * When omitted, the AppShell defaults to `"classification"`
   * — the same active-search behavior the `/` route has had
   * since ODD-ASN-002 shipped.
   */
  readonly currentRoute?:
    | "classification"
    | "explorer"
    | "help"
    | "settings"
    | "hydration-probe"
    | "not-found";
  readonly children: ReactNode;
}

export default function AppShell({
  title: _title,
  apiOrigin,
  schemaVersion,
  searchQuery,
  onSearchQueryChange,
  currentRoute,
  children,
}: AppShellProps): React.ReactElement {
  return (
    <div
      className="app-shell flex min-h-screen flex-col bg-surface-container-lowest text-on-surface"
      data-app-shell=""
    >
      {/* ODD-ASN-002 — the skip-to-main `<a href="#main">` link
           is owned by `src/app/layout.tsx` (rendered BEFORE
           `{children}` so it is the FIRST focusable element on
           every route). The AppShell mounts the `<main id="main">`
           target the layout's skip-link resolves to; the
           affordance itself is upstream, not here. */}
      <AppShellHeader
        searchQuery={searchQuery}
        onSearchQueryChange={onSearchQueryChange}
        currentRoute={currentRoute}
      />
      <main className="app-shell-main flex-1">
        <div
          id="main"
          className="app-shell-main-anchor mx-auto w-full max-w-5xl px-6 py-6"
        >
          {children}
        </div>
      </main>
      <AppShellFooter apiOrigin={apiOrigin} schemaVersion={schemaVersion} />
    </div>
  );
}