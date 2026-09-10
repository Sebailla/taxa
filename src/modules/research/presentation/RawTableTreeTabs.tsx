"use client";

// RawTableTreeTabs — the file-viewer tab strip (Raw / Table / Tree).
// Local to the research module per the 5b.3 brief: not promoted to
// design-system, not imported by other modules. Active tab is
// EXTERNALLY controlled — the parent owns selection so the explorer
// hook stays the single source of truth. Matches the explorer pattern
// (selection lives in the hook, not in DOM).
//
// Renderers (PR 5c) will swap the active tab via
// `data-viewer-tab="Raw|Table|Tree"`; the wrapper element gets
// `role="tablist"` + `role="tab"` + `aria-selected` so screen readers
// announce the active tab as the user navigates (WCAG 2.2 AA).

import type { ReactElement } from "react";

import type { ExplorerViewerTab } from "@taxa/research";

export interface RawTableTreeTabsProps {
  /** Active tab — must be one of `"Raw" | "Table" | "Tree"`. */
  readonly active: ExplorerViewerTab;
  /** Called with the next tab id when the user clicks a button. */
  readonly onSelect: (tab: ExplorerViewerTab) => void;
  /** Disable a tab (e.g. Table on a non-tabular file). Optional. */
  readonly disabled?: Partial<Record<ExplorerViewerTab, boolean>>;
}

const TABS: readonly ExplorerViewerTab[] = ["Raw", "Table", "Tree"] as const;

export function RawTableTreeTabs({
  active, onSelect, disabled,
}: RawTableTreeTabsProps): ReactElement {
  return (
    <div className="fex-tab-strip" role="tablist" aria-label="Viewer tab">
      {TABS.map((tab) => {
        const isActive = tab === active;
        const isDisabled = disabled?.[tab] === true;
        return (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls="fex-snippet-body"
            tabIndex={isActive ? 0 : -1}
            disabled={isDisabled}
            data-viewer-tab={tab}
            className={isActive ? "active" : ""}
            onClick={() => { if (!isDisabled) onSelect(tab); }}
          >
            {tab}
          </button>
        );
      })}
    </div>
  );
}
