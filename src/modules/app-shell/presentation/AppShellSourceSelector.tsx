/**
 * AppShellSourceSelector — the ODD-HSS-001 CoL / WoRMS / Freshwater
 * segmented control that lives in the AppShell header.
 *
 * Client island (the typed `useTreeSource()` hook from the
 * browser-state module is a client-only React adapter). The
 * orchestrator `AppShell.tsx` is a server component; the
 * `AppShellHeader.tsx` row is also a server component that
 * mounts this island as a focused client-only concern (mirrors
 * the `AppShellGlobalSearch` + `AppShellNav` decomposition the
 * ODD-ASN-002 AppShell rebuild introduced).
 *
 * spec.md rule 4: presentation depends on React + design-system
 * tokens (the `tree-source-toggle` + `tree-source-btn` CSS lives
 * in `globals.css`). No framework, no HTTP, no deep imports into
 * other capability modules.
 *
 * spec.md rule 5: the only cross-module import is the public
 * barrel `@taxa/browser-state/tree-source` (the dedicated
 * `useTreeSource` entry point). Direct imports into the layer
 * folders below are blocked by
 * `.eslintrc.cjs::no-restricted-imports`.
 *
 * Why this lives in the AppShell, not in TaxonomyTree:
 *
 *   The pre-ODD-HSS-001 mount owned the segmented control inside
 *   `TaxonomyTree.tsx`, only visible AFTER the user expanded the
 *   tree (`state.rootIds.length > 0`). The first-time user
 *   never saw the three data sources — CoL / WoRMS / Freshwater
 *   were a buried affordance that only became visible after the
 *   user committed to reading the tree.
 *
 *   PRODUCT.md treats CoL / WoRMS / Freshwater as a first-class
 *   concept (they appear in `/help`'s data-source legend).
 *   Hoisting them to the AppShell header makes them visible on
 *   every route (loading / error / empty / loaded) from the
 *   first paint. The data is owned by the AppShell, not by the
 *   tree.
 *
 * Source-rendering contract (pinned by
 * `tests/test_app_shell_render.py::test_appshell_renders_source_selector`
 * + `test_appshell_renders_source_selector_active_source_stamps` +
 * `test_appshell_source_selector_imports_use_tree_source_via_dedicated_entry`):
 *
 *   - `<div id="tree-source-toggle" role="group"
 *       aria-label="Tree data source" data-tree-source-toggle=""
 *       data-active-source={activeSource} className="tree-source-toggle ...">`
 *       — the React-shaped DOM contract the legacy Playwright
 *       probe + the source-persistence witness both locate via
 *       `[data-tree-source-toggle]` / `[data-active-source]` /
 *       `[aria-pressed]`.
 *   - Three per-source buttons `<button className="tree-source-btn"
 *       data-tree-source={src} aria-pressed={active ? "true" : "false"}
 *       onClick={() => setActiveSource(src)}>` — the
 *       `aria-pressed` per-button attribute + the data attributes
 *       + the segment labels `CoL` / `WoRMS` / `Freshwater` are
 *       the canonical data-source contract.
 *
 * Data flow:
 *
 *   `useTreeSource()` → `[activeSource, setActiveSource]`
 *   - The hook returns the typed default `"col"` on SSR + the
 *     first client render (matches the pre-hoist TaxonomyTree
 *     hook call).
 *   - The hook returns the stored value on the post-mount
 *     render (the source-persistence witness in
 *     `tests/test_taxonomy_tree_source_persistence.py` drives
 *     the same boundary from the AppShell now).
 *   - The setter is a stable callback that mirrors
 *     `writeTreeSource` — clicking a button writes through the
 *     typed store; `TaxonomyTree` (which still consumes
 *     `useTreeSource()` independently) sees the same value on
 *     its next render.
 *
 * Layout placement:
 *
 *   The selector sits inside the `<div className="mx-auto flex
 *   w-full max-w-5xl items-center gap-4 px-6 py-3">` row
 *   `AppShellHeader.tsx` renders — between the brand mark + the
 *   global-search input flex block + the nav. The CSS
 *   `.tree-source-toggle` rule in `globals.css` already owns the
 *   segmented-control height (32px) + outline + radius; the
 *   inline `margin: 8px 0` collapses to the 8px vertical rhythm
 *   the flex row establishes.
 */
"use client";

import { useTreeSource } from "@taxa/browser-state/tree-source";
import type { TreeSource } from "@taxa/browser-state/tree-source";

// TreeSource literal labels — typed tuple, no magic strings.
// `availableSourcesFor(rawRoots)` was the pre-hoist data-driven
// filter that hid the Freshwater toggle when no freshwater row
// existed in the `/api/domains` payload. After the hoist the
// AppShell has no `/api/domains` payload to filter against; the
// AppShell-scope selector always renders the three canonical
// sources and lets the user commit — the source-AWARE fetch
// (TaxonomyTree's `fetchChildren({ source: activeSource })`)
// returns an empty list when the source has no rows, mirroring
// the legacy DOM contract (`#tree-source-toggle` ships all
// three buttons pre-fetch).
const SOURCE_LABELS: Record<TreeSource, string> = {
  col: "CoL",
  worms: "WoRMS",
  freshwater: "Freshwater",
};

const ALL_SOURCES: readonly TreeSource[] = ["col", "worms", "freshwater"];

export default function AppShellSourceSelector(): React.ReactElement {
  const [activeSource, setActiveSource] = useTreeSource();
  return (
    <div
      id="tree-source-toggle"
      role="group"
      aria-label="Tree data source"
      data-tree-source-toggle=""
      data-active-source={activeSource}
      className="tree-source-toggle"
    >
      {ALL_SOURCES.map((src) => {
        const active = src === activeSource;
        return (
          <button
            key={src}
            type="button"
            className={`tree-source-btn${active ? " active" : ""}`}
            data-tree-source={src}
            aria-pressed={active ? "true" : "false"}
            onClick={() => setActiveSource(src)}
          >
            {SOURCE_LABELS[src]}
          </button>
        );
      })}
    </div>
  );
}
