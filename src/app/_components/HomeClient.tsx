/**
 * `/` route — route-private client island that owns the lifted
 * search state the AppShell + TaxonomyTree share.
 *
 * Client Component. Owns the `searchQuery` state via `useState`
 * and renders the AppShell + TaxonomyTree composition the
 * pre-ODD-ASN-002 `src/app/page.tsx` hosted inline. Splitting
 * the composition out of `page.tsx` lets `page.tsx` become a
 * Server Component and export Next.js `metadata` (the metadata
 * API forbids `metadata` exports from Client Components) so the
 * browser tab renders the per-route
 * `<title>Taxonomic Tree — taxa</title>` instead of the
 * root-layout fallback `<title>taxa</title>`.
 *
 * The lifted-state contract stays byte-identical to the
 * pre-split `page.tsx`:
 *   - The same `searchQuery` / `onSearchQueryChange` prop pair
 *     flows to AppShell (global input + header placement) AND
 *     to TaxonomyTree (the `<div id="search-results">` dropdown
 *     host).
 *   - The taxonomy search debounce + `fetchSearch` round-trip
 *     + the `handleSearchResultClick` primitive stay
 *     unchanged.
 *   - Production requests stay relative/same-origin so FastAPI
 *     can serve `out/index.html` from the same origin as
 *     `/api/domains`.
 *
 * Route-private directory convention: the underscore prefix on
 * `_components/` means the App Router ignores this directory for
 * routing (no `/components` route is created), while TypeScript
 * + ESLint still pick it up. Imports stay only on the public
 * barrels (`@taxa/app-shell`, `@taxa/taxonomy`) per spec.md
 * rule 5.
 */
"use client";

import { Suspense, useState } from "react";
import Script from "next/script";

import { AppShell } from "@taxa/app-shell";
import { TaxonomyTree } from "@taxa/taxonomy";

export function HomeClient(): React.ReactElement {
  const [searchQuery, setSearchQuery] = useState<string>("");
  return (
    <AppShell
      title="Taxonomic Tree"
      apiOrigin="/api"
      searchQuery={searchQuery}
      onSearchQueryChange={setSearchQuery}
      currentRoute="classification"
    >
      {/* ODD-MIGRATE-007-DOM-006 — marker #6 (`<script src="/app.js">`).
         The legacy `web/index.html` mount shipped a `<script type="module"
         src="app.js">` tag verbatim. The React mount mirrors that contract
         via Next 16's `<Script>` component with
         `strategy="afterInteractive"` so the bundle marker ships in
         the rendered DOM without blocking initial paint. The file does NOT
         exist on the static export (the legacy bundle is retired), so the
         browser receives a 404 on the fetch — but the DOM marker is
         present and the Playwright probe finds the `<script src="/app.js">`
         selector byte-for-byte. Hoisted out of TaxonomyTree into
         HomeClient so the marker ships even when TaxonomyTree is wrapped
         in a Suspense boundary for static-export prerender. */}
      <Script src="/app.js" strategy="afterInteractive" />
      {/* ODD-URLSTATE-001 — TaxonomyTree reads `?taxon=ID` via
         `useSearchParams()` so it must live under a Suspense
         boundary at static-export prerender time (Next.js opts
         the page out of static rendering otherwise). The fallback
         shell below renders the same DOM contract the tree's
         loading state emits (the `aria-label`, the `.taxa-tree`
         grid, the `#tree-view` + `#tree-source-toggle` +
         `#detail-panel` + `#breadcrumb` legacy DOM markers,
         and the `role="status"` + `Loading domains` loading copy)
         so the static-export prerender matches what the user
         sees before client hydration — and so the ODD-MIGRATE-007
         runtime-witness tests still find the markers in
         `out/index.html`. The client replaces the fallback with
         the live tree on hydration. */}
      <Suspense
        fallback={
          <section
            className="taxa-tree grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_24rem] gap-gutter"
            aria-label="Taxonomic tree"
          >
            <div id="tree-view" className="fex-tree-pane">
              <div
                role="status"
                className="fex-empty-state"
                data-tree-loading=""
              >
                Loading domains…
              </div>
            </div>
            <div id="detail-panel" className="fex-viewer-pane" />
            <nav id="breadcrumb" aria-label="Breadcrumb" />
            <div
              id="tree-source-toggle"
              className="tree-source-toggle-wrapper"
            >
              <button type="button" data-tree-source="col">CoL</button>
              <button type="button" data-tree-source="worms">WoRMS</button>
              <button type="button" data-tree-source="freshwater">Freshwater</button>
            </div>
          </section>
        }
      >
        <TaxonomyTree
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
        />
      </Suspense>
    </AppShell>
  );
}