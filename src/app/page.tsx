/**
 * Single-screen client entry for the App Router static export.
 *
 * ODD-VTREE-002 — visible AppShell with a lazily-expandable taxonomy
 * tree backed by the existing FastAPI endpoints. The route itself
 * stays a server component; only `<TaxonomyTree>` carries the client
 * boundary (state + fetch). Production requests stay
 * relative/same-origin so FastAPI can serve `out/index.html` from the
 * same origin as `/api/domains`.
 *
 * spec.md rule 5 — imports come only from the public barrels
 * (`@taxa/app-shell`, `@taxa/taxonomy`). The ESLint
 * `no-restricted-imports` guard rejects deep paths into the layer
 * folders of every capability module.
 */
import { AppShell } from "@taxa/app-shell";
import { TaxonomyTree } from "@taxa/taxonomy";

export default function Page(): React.ReactElement {
  return (
    <AppShell title="Taxonomic Tree" apiOrigin="/api">
      <TaxonomyTree />
    </AppShell>
  );
}