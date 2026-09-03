"use client";

/**
 * Single-screen client entry for the App Router static export (PR 3b + PR 4b).
 *
 * Minimal semantic placeholder inside the ``<AppShell>`` from
 * ``@taxa/app-shell``. The AppShell (PR 4b.2) imports `useEffect` /
 * `useSyncExternalStore` and is a client component, so this page is
 * also a client component to keep the React 19 server-vs-client
 * bundle split explicit (a later PR — taxonomy port 5a — will add
 * the real taxon tree, detail panel, and breadcrumbs here).
 *
 * Chain-topology guard: this file MUST NOT directly import
 *   - ``@taxa/app-shell``        (AppShell is composed by layout.tsx;
 *                                  this file only renders content)
 *   - ``./globals.css``          (owned by PR 3c Tailwind tokens; the
 *                                  layout imports it once)
 *
 * The ``<main>`` landmark and the visible ``<h1>`` are the minimum
 * semantic content ``next build`` needs to render a non-empty page so
 * the G2 ``out/index.html`` witness is satisfiable.
 */
export default function Page(): React.ReactElement {
  return (
    <>
      <h1>taxa</h1>
    </>
  );
}