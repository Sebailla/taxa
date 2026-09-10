"use client";

// KebabStub — minimal per-row kebab trigger (PR 5a.2).
//
// Renders the kebab glyph with `data-action="kebab"` so the next slice
// can locate the trigger via the existing e2e / screenshot harness.
// The real `.kebab-menu` body, `.open` toggle, and force-tab callback
// land in 5a.4 — none of them are wired here. No `onClick` handler
// either: the glyph is disabled.

import type { ReactElement } from "react";

export interface KebabStubProps {
  readonly taxonId: number;
}

export function KebabStub({ taxonId }: KebabStubProps): ReactElement {
  return (
    <span className="kebab">
      <button type="button" data-action="kebab"
              data-taxon-id={taxonId}
              aria-label="Row actions" disabled>
        {"\u22EF"}
      </button>
    </span>
  );
}