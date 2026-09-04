"use client";

// Breadcrumb — root-first rank/name chain above the tree (PR 5a.2).
// Pure projection of `BreadcrumbViewModel`. Selection routes through
// the same `onSelect` callback the tree uses.

import type { ReactElement } from "react";

import { type BreadcrumbViewModel } from "@taxa/taxonomy";

export interface BreadcrumbProps {
  readonly viewModel: BreadcrumbViewModel | null;
  readonly onSelect: (id: number) => void;
}

export function Breadcrumb({ viewModel, onSelect }: BreadcrumbProps): ReactElement {
  if (viewModel === null || viewModel.segments.length === 0) {
    return <nav className="breadcrumb" aria-label="Taxon breadcrumb" />;
  }
  return (
    <nav className="breadcrumb" aria-label="Taxon breadcrumb"
         data-source={viewModel.source}>
      {viewModel.segments.map((segment, index) => (
        <span key={segment.id} className="breadcrumb-segment">
          <button type="button" className="breadcrumb-link"
                  data-taxon-id={segment.id}
                  onClick={() => onSelect(segment.id)}>
            <span className="authorship">{segment.rank}</span>
            <span className="scientific-name">{segment.name}</span>
          </button>
          {index < viewModel.segments.length - 1
            ? <span className="authorship" aria-hidden="true">{">"}</span>
            : null}
        </span>
      ))}
    </nav>
  );
}