"use client";

// DetailPanel — taxon detail surface consuming the design-system
// `TabStrip` primitive (PR 5b.4 promotion).
//
// 5a.3 / 5a.4 shipped DetailPanel with a LOCAL `TabStrip` and
// `SearchTabStub` / `FolderTabStub` placeholders. 5b.4 promotes
// `TabStrip` to `@taxa/design-system` (verbatim port) and swaps the
// taxonomy stubs for the real `SearchTab` / `FolderTab` from the
// research module (`@taxa/research`). The detail panel continues to
// own local active-tab state (default `Overview`) and the
// `forceOpenSearch` prop regression guard from 5a.4 (the per-row
// kebab's `Search online` action forces the Search tab active even for
// top-level taxa whose default would otherwise be Overview).
//
// The `forceOpenSearch` prop is a counter-shaped scalar (callers bump
// it to retrigger) so the same value can be re-applied after the user
// manually switches back to Overview without the panel having to track
// equality itself. The snapshot lives in a ref so the effect doesn't
// fire on every parent render.

import type { ReactElement } from "react";
import { useEffect, useRef, useState } from "react";

import { type TaxonRecord } from "@taxa/taxonomy";
import { TabStrip, type TabDefinition } from "@taxa/design-system";
import { SearchTab, FolderTab } from "@taxa/research";

import { OverviewTab } from "./OverviewTab";

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
      {activeKey === "search" ? <SearchTab taxonId={selectedId} /> : null}
      {activeKey === "folder" ? <FolderTab taxonId={selectedId} /> : null}
    </aside>
  );
}
