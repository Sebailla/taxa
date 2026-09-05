"use client";

// DetailPanel — taxon detail surface with local TabStrip (PR 5a.3).
//
// Owns local active-tab state (default `Overview`). 5a.4 EXTENDS the
// surface with a `forceOpenSearch` prop so the per-row kebab's
// `Search online` action can snap the active tab to Search even for
// top-level taxa where the default would otherwise be Overview.
//
// The prop is intentionally a counter-shaped scalar (callers bump it
// to retrigger) so the same `forceOpenSearch` value can be re-applied
// after the user manually switches back to Overview without the panel
// having to track equality itself. The snapshot lives in a ref so the
// effect doesn't fire on every parent render.

import type { ReactElement } from "react";
import { useEffect, useRef, useState } from "react";

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
/** Key the kebab's `Search online` action forces the active tab to. */
const FORCE_SEARCH_KEY = "search";

export interface DetailPanelProps {
  readonly selected: TaxonRecord | null;
  /**
   * Counter that, when bumped, forces the active tab to Search even
   * for taxa whose default would be Overview. Wired by `page.tsx` to
   * the kebab's `onSearchOnline` callback. `0` means "no override";
   * any positive integer is treated as one bump.
   */
  readonly forceOpenSearch?: number;
}

export function DetailPanel({
  selected,
  forceOpenSearch = 0,
}: DetailPanelProps): ReactElement {
  const [activeKey, setActiveKey] = useState<string>(DEFAULT_TAB_KEY);
  const selectedId = selected?.id ?? null;
  const lastForceRef = useRef<number>(0);

  // React to forceOpenSearch bumps: snap activeKey to Search every
  // time the counter increments past the last-seen value. A ref
  // (instead of state) keeps the dependency comparison cheap and
  // avoids re-running the effect on unrelated re-renders.
  useEffect(() => {
    if (forceOpenSearch > lastForceRef.current) {
      lastForceRef.current = forceOpenSearch;
      setActiveKey(FORCE_SEARCH_KEY);
    }
  }, [forceOpenSearch]);

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