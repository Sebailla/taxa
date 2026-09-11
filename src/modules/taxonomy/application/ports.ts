// Taxonomy application — typed port compatible with the merged
// infrastructure adapter. spec.md rule 4: application depends on
// domain ONLY; presentation depends on this port; infrastructure
// satisfies it via TypeScript structural subtyping. Application
// stays pure: no React, no Next, no HTTP transport, no DOM, no
// browser state, no process state.
//
// The merged adapter declares wider signatures that carry transport
// options; the application port intentionally drops those (they are
// HTTP transport concerns, not domain concerns) and keeps only the
// `source` filter. Structural function subtyping lets the adapter's
// wider signatures satisfy this narrower port.

import type { Taxon } from "../domain/taxon.js";

/** Source qualifier for `fetchChildren` — mirrors the merged
 *  adapter's source field. "col" = Catalogue of Life (default),
 *  "worms" = World Register of Marine Species, "freshwater" =
 *  Freshwater Fishes slice. */
export type SourceFilter = "col" | "worms" | "freshwater";

/** Application-layer port for the taxonomy data source.
 *  Structurally compatible with the merged infrastructure adapter:
 *  the adapter's `fetchTaxon` + `fetchChildren` satisfy this port
 *  via TypeScript's structural function subtyping (the adapter's
 *  extra optional transport parameters are silently ignored when
 *  assigned to the narrower port signature). */
export interface TaxonomyRepository {
  fetchTaxon(id: number): Promise<Taxon>;
  fetchChildren(
    id: number,
    opts?: { readonly source?: SourceFilter },
  ): Promise<readonly Taxon[]>;
}

/** Stable string identity for DI containers / diagnostic guards. */
export const TAXONOMY_PORT_NAME = "TaxonomyRepository";
