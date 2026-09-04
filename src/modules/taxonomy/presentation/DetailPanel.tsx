"use client";

// DetailPanel — taxon detail surface with local TabStrip (PR 5a.3).
// Owns local active-tab state (default `Overview`). Kebab force-Search
// callback lands in 5a.4 — no global activation contract yet.

import type { ReactElement } from "react";
import { useState } from "react";

import { type TaxonRecord } from "@taxa/taxonomy";

import { TabStrip, type TabDefinition } from "./TabStrip";
import { OverviewTab } from "./OverviewTab";
import { SearchTabStub } from "./SearchTabStub";
import { FolderTabStub } from "./FolderTabStub";

const TABS: readonly TabDefinition[] = [
  { key: "overview", label: "Overview" },
  { key: "search", label: "Search" },
  { key: "folder", label: "Folder" },
] as const;

const DEFAULT_TAB_KEY = "overview";

export interface DetailPanelProps {
  readonly selected: TaxonRecord | null;
}

export function DetailPanel({ selected }: DetailPanelProps): ReactElement {
  const [activeKey, setActiveKey] = useState<string>(DEFAULT_TAB_KEY);
  const selectedId = selected?.id ?? null;
  return (
    <aside className="detail-panel" data-slot="taxon-detail"
           aria-label="Taxon detail">
      <TabStrip tabs={TABS} activeKey={activeKey}
                onChange={setActiveKey} />
      {activeKey === "overview" ? <OverviewTab selected={selected} /> : null}
      {activeKey === "search" ? <SearchTabStub selectedId={selectedId} /> : null}
      {activeKey === "folder" ? <FolderTabStub selectedId={selectedId} /> : null}
    </aside>
  );
}