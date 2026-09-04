"use client";

// TaxonDetailPlaceholder — minimal detail-panel surface (PR 5a.2).
// Real `DetailPanel` body (Overview/Search/Folder tab strip + full
// metadata) lands in 5a.3. 5a.2 ships the minimum that proves
// reachability: an `<aside>` with `data-slot="taxon-detail"` and a
// one-line summary of the currently selected taxon.

import type { ReactElement } from "react";

import { type TaxonRecord } from "@taxa/taxonomy";

export interface TaxonDetailPlaceholderProps {
  readonly selected: TaxonRecord | null;
}

export function TaxonDetailPlaceholder({ selected }: TaxonDetailPlaceholderProps): ReactElement {
  return (
    <aside className="detail-panel" data-slot="taxon-detail"
           aria-label="Taxon detail (5a.3 placeholder)">
      <header className="overview-tab">
        <h2 className="scientific-name">
          {selected?.scientific_name ?? "Select a taxon"}
        </h2>
        <p className="authorship">
          {selected === null
            ? "The full DetailPanel lands with PR 5a.3."
            : `${selected.rank} \u00b7 ${selected.status}${selected.is_extinct ? " \u00b7 extinct" : ""}`}
        </p>
      </header>
    </aside>
  );
}