"use client";

// TabStrip — design-system primitive (5b.4 promotion).
//
// The local `TabStrip` authored in 5a.3 (taxonomy/presentation/TabStrip.tsx)
// is promoted verbatim to the design-system module here. The
// taxonomy DetailPanel now imports it from `@taxa/design-system`.
//
// The promotion is the 5b.4 close-out of the 5a.3 addendum (see
// openspec/changes/complete-taxa-frontend-migration/tasks.md
// §"Addendum — 2026-09-04: Phase 5a four-slice replan"). The verbatim
// port keeps the contract identical so the 3c-c CSS selectors
// (`[data-tab="Overview"].active`, etc.) and the force-search useEffect
// in DetailPanel continue to match without any new wiring.
//
// API surface (unchanged from 5a.3):
//   - `tabs: readonly TabDefinition[]` — the canonical tab definitions
//   - `activeKey: string` — the externally-controlled active tab
//   - `onChange: (key: string) => void` — the parent owns selection

import type { ReactElement } from "react";

export interface TabDefinition {
  readonly key: string;
  readonly label: string;
}

export interface TabStripProps {
  readonly tabs: readonly TabDefinition[];
  readonly activeKey: string;
  readonly onChange: (key: string) => void;
}

export function TabStrip({ tabs, activeKey, onChange }: TabStripProps): ReactElement {
  return (
    <div className="tab-strip" role="tablist" aria-label="Taxon detail tabs">
      {tabs.map((tab) => {
        const isActive = tab.key === activeKey;
        return (
          <button key={tab.key} type="button"
                  className={`tab-button${isActive ? " active" : ""}`.trim()}
                  data-tab={tab.label} role="tab"
                  aria-pressed={isActive ? "true" : "false"}
                  aria-selected={isActive ? "true" : "false"}
                  onClick={() => onChange(tab.key)}>
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
