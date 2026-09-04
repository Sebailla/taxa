"use client";

// OverviewTab — Overview body for the DetailPanel (PR 5a.3).
// Surfaces scientific name / rank / status / species count from the
// TaxonRecord shape. Authorship is omitted (TaxonRecord doesn't carry
// it). Parent chain visualization lives in Breadcrumb.

import type { ReactElement } from "react";

import { type TaxonRecord } from "@taxa/taxonomy";

export interface OverviewTabProps {
  readonly selected: TaxonRecord | null;
}

export function OverviewTab({ selected }: OverviewTabProps): ReactElement {
  if (selected === null) {
    return (
      <div className="overview-tab" data-tab-content="overview">
        <h2 className="scientific-name">Select a taxon</h2>
        <p className="authorship">
          Overview opens once you pick a node in the tree.
        </p>
      </div>
    );
  }
  const extinctCls = selected.is_extinct ? " line-through opacity-70" : "";
  const statusText = selected.status === "accepted"
    ? "Accepted"
    : selected.status === "synonym" ? "Synonym" : "Unknown";
  return (
    <div className="overview-tab" data-tab-content="overview">
      <h2 className={`scientific-name${extinctCls}`.trim()}>
        {selected.scientific_name}
      </h2>
      <p className="authorship">
        <span className="rank-badge">{selected.rank}</span>
        {" \u00b7 "}
        <span>{statusText}</span>
        {selected.is_extinct ? " \u00b7 extinct" : ""}
      </p>
      <p className="species-count">
        {selected.species_count.toLocaleString("en-US")} species
      </p>
    </div>
  );
}