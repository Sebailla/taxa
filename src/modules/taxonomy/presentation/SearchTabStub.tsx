"use client";

// SearchTabStub — placeholder for the Search tab body (PR 5a.3).
// Real SearchTab lands in PR 5b. Kebab force-Search wiring lands in 5a.4.

import type { ReactElement } from "react";

export interface SearchTabStubProps {
  readonly selectedId: number | null;
}

export function SearchTabStub({ selectedId }: SearchTabStubProps): ReactElement {
  return (
    <div className="search-tab" data-tab-content="search">
      <p className="authorship">
        {selectedId === null
          ? "Search opens once you pick a taxon."
          : "Search links land with PR 5b."}
      </p>
    </div>
  );
}