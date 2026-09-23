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

import { useState } from "react";

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
      <TaxonomyTree
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
      />
    </AppShell>
  );
}