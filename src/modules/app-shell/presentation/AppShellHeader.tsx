/**
 * AppShellHeader — the ODD-ASN-002 header row.
 *
 * Server component (no `"use client"`): the brand mark + the
 * static four-destination navigation layout are SSR-friendly, and
 * the only client-side concern (`usePathname()` for the active
 * affordance) lives in `AppShellNav` (the client island nested
 * inside this component).
 *
 * spec.md rule 4 / rule 5: this component depends only on React
 * + the design-system tokens in `globals.css`. No framework, no
 * HTTP, no browser-state — the navigation surface stays purely
 * declarative.
 */
import AppShellNav from "./AppShellNav";
import AppShellGlobalSearch from "./AppShellGlobalSearch";

export interface AppShellHeaderProps {
  /** Optional lifted search query (ODD-ASN-002 controlled mode). */
  readonly searchQuery?: string;
  /** Optional lifted search-mutator (ODD-ASN-002 controlled mode). */
  readonly onSearchQueryChange?: (next: string) => void;
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
          />
        </div>
        <AppShellNav />
      </div>
    </header>
  );
}