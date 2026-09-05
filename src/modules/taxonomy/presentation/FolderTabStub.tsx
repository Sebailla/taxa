"use client";

// FolderTabStub — placeholder for the Folder tab body (PR 5a.3).
// Real FolderTab (materialize preview) lands in PR 5b.

import type { ReactElement } from "react";

export interface FolderTabStubProps {
  readonly selectedId: number | null;
}

export function FolderTabStub({ selectedId }: FolderTabStubProps): ReactElement {
  return (
    <div className="folder-tab" data-tab-content="folder">
      <p className="authorship">
        {selectedId === null
          ? "Folder preview opens once you pick a taxon."
          : "Folder materialize preview lands with PR 5b."}
      </p>
    </div>
  );
}