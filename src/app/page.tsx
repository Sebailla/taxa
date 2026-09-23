/**
 * `/` route — per-route metadata split (ODD-ASN-002).
 *
 * Server Component. Exports the Next.js `metadata` object so the
 * browser tab renders `<title>Taxonomic Tree — taxa</title>` (the
 * `"<SurfaceTitle> — taxa"` pattern the `/explorer`, `/help`, and
 * `/settings` routes already use). The composition that owns the
 * lifted `searchQuery` state — the AppShell + TaxonomyTree mount
 * with the `searchQuery` / `onSearchQueryChange` prop pair — lives
 * in the route-private client island
 * `src/app/_components/HomeClient.tsx` so this page stays free of
 * `"use client"`.
 *
 * The split closes the per-route metadata contract for `/`: the
 * Next.js metadata API forbids `metadata` exports from Client
 * Components, so the pre-split `"use client"` page rendered only
 * the root-layout fallback `<title>taxa</title>`. Splitting the
 * lifted state out lets this page become a Server Component and
 * declare the per-route title without touching the lifted-state
 * contract the AppShell + TaxonomyTree already share.
 *
 * spec.md rule 5 — imports come only from the route-private
 * client island under `./_components/HomeClient` (the underscore
 * prefix means the App Router ignores the directory for routing
 * while TypeScript + ESLint still pick it up).
 */
import { HomeClient } from "./_components/HomeClient";

export const metadata = {
  title: "Taxonomic Tree — taxa",
  description:
    "Taxonomic Tree — the default taxa shell route. Browse the Catalogue of Life + WoRMS + Freshwater taxonomy backed by the FastAPI search API.",
};

export default function Page(): React.ReactElement {
  return <HomeClient />;
}