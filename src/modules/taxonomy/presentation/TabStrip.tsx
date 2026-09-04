"use client";

// TabStrip — local segmented control (PR 5a.3). Three tabs in fixed
// order (`Overview` / `Search` / `Folder`); stays local to `presentation/`
// until 5b promotes it to design-system.

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