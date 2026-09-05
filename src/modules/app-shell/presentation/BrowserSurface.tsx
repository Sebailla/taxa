"use client";

// BrowserSurface — the global Research / file explorer host (5b.4).
//
// Wraps the research module's `FileExplorer` with a `taxonId={null}`
// prop so the explorer mounts in its no-taxon idle state. The header
// `Browser` tab is re-anchored as the **global** research surface
// per the 3c-c contract — it opens WITHOUT a `taxonId` filter, and
// selecting a taxon while `Browser` is active MUST NOT scope the
// explorer to that taxon (decision #3 in the 5b.4 brief — global,
// not taxon-scoped).
//
// The component is mounted by AppShell when the primary nav tab is
// `browser`; otherwise AppShell mounts the taxonomy children. The
// AppShell owns the active-tab state machine; BrowserSurface does
// NOT subscribe to taxonomy selection — that's the contract.

import type { ReactElement } from "react";

import { FileExplorer, type FileExplorerProps } from "@taxa/research";

export interface BrowserSurfaceProps {
  /** Base URL for the research endpoints. The AppShell / page.tsx
   *  passes the same base URL it passes to the taxonomy module so
   *  `/api/taxon/{id}/files` resolves to the same server. */
  readonly baseUrl?: string;
  /** Forwarded to FileExplorer for SSR / tests. Optional. */
  readonly fetchFn?: FileExplorerProps["fetchFn"];
}

export function BrowserSurface({
  baseUrl = "", fetchFn,
}: BrowserSurfaceProps): ReactElement {
  // Decision #3: the explorer is ALWAYS mounted with `taxonId={null}`
  // — the surface is global, not taxon-scoped. Selecting a taxon
  // while this surface is active MUST NOT scope the explorer to that
  // taxon (the explorer continues to show the no-taxon idle surface).
  return (
    <div className="header-browser-tab-host"
         data-slot="browser-surface"
         data-taxon-id=""
         data-browser-global="true"
         aria-label="Global research browser">
      <FileExplorer taxonId={null} baseUrl={baseUrl} fetchFn={fetchFn} />
    </div>
  );
}
