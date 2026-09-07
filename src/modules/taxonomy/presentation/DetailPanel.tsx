"use client";

// DetailPanel — taxon detail surface consuming the design-system
// `TabStrip` primitive (PR 5b.4 promotion + PR 5c.1b-B close/sticky
// work).
//
// 5a.3 / 5a.4 shipped DetailPanel with a LOCAL `TabStrip` and
// `SearchTabStub` / `FolderTabStub` placeholders. 5b.4 promotes
// `TabStrip` to `@taxa/design-system` (verbatim port) and swaps the
// taxonomy stubs for the real `SearchTab` / `FolderTab` from the
// research module (`@taxa/research`). The detail panel continues to
// own local active-tab state (default `Overview`) and the
// `forceOpenSearch` prop regression guard from 5a.4 (the per-row
// kebab's `Search online` action forces the Search tab active even
// for top-level taxa whose default would otherwise be Overview).
//
// 5c.1b-B ADDS:
//   - `id="detail-panel"` on the root <aside> (legacy Playwright /
//     CSS selector contract preserved verbatim).
//   - `.detail-header` and `.detail-tabs` structural hooks for the
//     sticky CSS contract that pins the title + tabs while the body
//     scrolls. The hooks live inside the existing `.detail-panel`
//     scroll viewport so the existing 3c-b `.detail-panel` rules
//     keep working without drive-by refactors.
//   - A close button (`data-action="close-detail"`) wired to a new
//     `detailOpen` state; close drops the state to false and a later
//     `forceOpenSearch` bump resets it to true so the kebab's
//     Search-online flow reopens a closed panel without a silent
//     no-op regression.
//   - `data-detail-open` attribute on the aside so external observers
//     can probe panel state.

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
     * any positive integer is treated as one bump. The same counter
     * bump also reopens a panel the user previously closed
     * (`detailOpen` → true), closing the legacy silent-no-op
     * regression on re-selecting a closed taxon.
     */
    readonly forceOpenSearch?: number;
}

export function DetailPanel({
    selected,
    forceOpenSearch = 0,
}: DetailPanelProps): ReactElement {
    const [activeKey, setActiveKey] = useState<string>(DEFAULT_TAB_KEY);
    // PR 5c.1b-B — close button hides the panel via detailOpen. The next
    // forced Search interaction (the kebab "Search online" flow) resets
    // detailOpen to true so the panel reopens.
    const [detailOpen, setDetailOpen] = useState<boolean>(true);
    const selectedId = selected?.id ?? null;
    const lastForceRef = useRef<number>(0);

    // React to forceOpenSearch bumps: snap activeKey to Search AND
    // reopen a closed panel (`detailOpen` → true). The single effect
    // keeps both invariants atomic — a Search-online click reopens
    // the panel even if the user previously dismissed it.
    useEffect(() => {
        if (forceOpenSearch > lastForceRef.current) {
            lastForceRef.current = forceOpenSearch;
            setActiveKey(FORCE_SEARCH_KEY);
            setDetailOpen(true);
        }
    }, [forceOpenSearch]);

    if (!detailOpen) {
        return <aside id="detail-panel" className="detail-panel"
                      data-slot="taxon-detail"
                      data-detail-open="false"
                      aria-label="Taxon detail" hidden />;
    }

    const handleClose = (): void => {
        setDetailOpen(false);
    };

    return (
        <aside id="detail-panel" className="detail-panel"
               data-slot="taxon-detail"
               data-detail-open="true"
               aria-label="Taxon detail">
            <header className="detail-header" data-detail-header
                    data-slot="taxon-detail-header">
                <span className="detail-header-title">
                    {selected?.scientific_name ?? "—"}
                </span>
                <button type="button" className="detail-close"
                        data-action="close-detail"
                        aria-label="Close detail panel"
                        onClick={handleClose}>
                    Close
                </button>
            </header>
            <div className="detail-tabs" data-detail-tabs
                 data-slot="taxon-detail-tabs">
                <TabStrip tabs={TABS} activeKey={activeKey}
                          onChange={setActiveKey} />
            </div>
            <div className="detail-body" data-detail-body>
                {activeKey === "overview" ? <OverviewTab selected={selected} /> : null}
                {activeKey === "search" ? <SearchTab taxonId={selectedId} /> : null}
                {activeKey === "folder" ? <FolderTab taxonId={selectedId} /> : null}
            </div>
        </aside>
    );
}
