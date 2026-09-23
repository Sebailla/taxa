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
 *   - Renders a skip-to-main `<a href="#main">` as the FIRST
 *     focusable element (the layout MUST render the same link
 *     above `{children}` so every route satisfies the WCAG
 *     skip-link contract — the link here is the in-shell
 *     duplicate that covers routes whose layout does not pin
 *     the skip-link in advance).
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
 *     skip-link target resolves on every route.
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
  readonly children: ReactNode;
}

export default function AppShell({
  title: _title,
  apiOrigin,
  schemaVersion,
  searchQuery,
  onSearchQueryChange,
  children,
}: AppShellProps): React.ReactElement {
  return (
    <div
      className="app-shell flex min-h-screen flex-col bg-surface-container-lowest text-on-surface"
      data-app-shell=""
    >
      {/* ODD-ASN-002 — skip-to-main link. The layout renders its
           own skip-link at the top of every route; this in-shell
           duplicate covers the edge case where the layout does
           not pin the link (e.g. the probe route) so the
           WCAG skip-link contract stays honoured on every page
           the AppShell wraps. Rendered BEFORE the header so the
           skip-link is the FIRST focusable element on every
           route (per the brief). */}
      <a
        href="#main"
        className="app-shell-skip-link sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-on-primary focus:outline-none"
        data-app-shell-skip-link=""
      >
        Skip to main content
      </a>
      <AppShellHeader
        searchQuery={searchQuery}
        onSearchQueryChange={onSearchQueryChange}
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