/**
 * Taxonomic Tree — frontend entry point.
 *
 * Vanilla JS, no build step. Loads as `type="module"` from
 * web/index.html; pulls in the rest of the frontend from the modules
 * below.
 *
 * Interaction model:
 *   - Click on a node = toggle its expansion (open/close its direct children).
 *     The tree grows downward, never re-positions.
 *   - Click on a species/subspecies = also selects it (shows the detail panel
 *     and updates the URL hash for shareable links / back-forward).
 *   - "Load all" button = expand a tier group past the default N children.
 *   - The breadcrumb and detail panel react to the *selected* species, while
 *     the tree view is driven by the *expanded* set. The two are independent
 *     — you can browse the tree with the panel closed, or with it open on a
 *     specific species.
 *
 * Module layout:
 *   state.js       — shared `state` object + constants (API, PAGE_SIZE)
 *   api.js         — fetch helpers (api, loadTaxon, loadChildren)
 *   format.js      — pure formatting helpers + rank-order constants
 *   dom.js         — el() builder + scroll/wait helpers
 *   tree.js        — tree rendering pipeline
 *   breadcrumb.js  — breadcrumb renderer
 *   detail.js      — detail panel renderer + loadDetail + buildDetailSection
 *   search.js      — search dropdown + runSearch + input handlers
 *   nav.js         — actions (toggleExpand/selectTaxon/collapseAll/…) +
 *                    main click delegation + tree-source toggle
 *   banner.js      — version-mismatch banner (DB outdated indicator)
 *
 * Circular imports: nav.js and detail.js both import `render` from this
 * file. ES module live bindings resolve the cycle correctly because the
 * imported binding is only USED inside function bodies (never at module
 * init). The same pattern applies to tree.js ↔ nav.js (tree's el()
 * callbacks call toggleExpand/selectTaxon; nav's actions call renderTree).
 */

import { state } from "./state.js";
import { api } from "./api.js";
import { renderTree } from "./tree.js";
import { renderBreadcrumb } from "./breadcrumb.js";
import { renderDetailPanel, loadDetail } from "./detail.js";
import {
 renderCollapseAllButton,
 selectTaxon,
 expandAncestorsOf,
} from "./nav.js";
import { el } from "./dom.js";
import { renderVersionBanner } from "./banner.js";

// Top-level render orchestrator. Called after any state mutation that
// changes what the page should display. Re-renders every region; the
// cost is fine for the 5.4M-row dataset because the visible tree is
// bounded by state.expanded + PAGE_SIZE.
export function render() {
 renderTree();
 renderBreadcrumb();
 renderCollapseAllButton();
 renderDetailPanel();
}

async function boot() {
 // Health check (best-effort; doesn't block render).
 try {
  const h = await api("/api/health");
  document.querySelector("#footer-status").textContent =
   `System Online · ${h.taxa.toLocaleString()} taxa · ${h.vernaculars.toLocaleString()} vernaculars`;
  // Version-mismatch banner: shown when the DB's PRAGMA user_version
  // is older than the API's CURRENT_SCHEMA_VERSION. Hidden when they
  // match. The /api/health response carries both values.
  renderVersionBanner(h.db_schema_version, h.expected_schema_version);
 } catch {
  document.querySelector("#footer-status").textContent = "API unreachable";
  document
   .querySelector("#footer-status")
   .previousElementSibling.classList.remove("bg-green-500");
  document
   .querySelector("#footer-status")
   .previousElementSibling.classList.add("bg-red-500");
 }

 // Load the 4 domains as roots.
 const roots = await api("/api/domains");
 for (const r of roots) {
  state.cache.set(r.id, { taxon: r, children: null });
 }
 state.roots = roots;

 // If freshwater is loaded, append a "Freshwater" toggle button. The
 // event delegation set up in nav.js handles its click.
 if (roots.some((r) => r.freshwater_id != null)) {
  const toggle = document.querySelector("#tree-source-toggle");
  if (toggle && !toggle.querySelector('[data-tree-source="freshwater"]')) {
   const freshBtn = el(
    "button",
    {
     type: "button",
     "data-tree-source": "freshwater",
     class: "tree-source-btn",
    },
    "Freshwater",
   );
   toggle.append(freshBtn);
  }
 }

 // If the URL has a hash, select that species and focus its path.
 const hashId = parseInt(location.hash.replace("#", ""), 10);
 if (hashId && Number.isFinite(hashId)) {
  await expandAncestorsOf(hashId);
  state.focused = hashId;
  selectTaxon(hashId, { updateUrl: "replace" });
 }
 // Otherwise: no pre-expansion, no initial focus. The tree shows the
 // 6 root domains collapsed with nothing highlighted; the breadcrumb
 // is empty. The user picks a starting node by clicking.

 render();
}

// Browser back/forward: restore the selected species from the URL hash.
// Lives in app.js because it's a window-level handler wired once at
// module load and doesn't fit any other module's responsibility.
window.addEventListener("popstate", () => {
 const hash = location.hash.replace(/^#/, "").trim();
 const id = parseInt(hash, 10);
 if (hash === "" && state.selected !== null) {
  // Back to "no selection" (e.g., after Home was clicked).
  state.selected = null;
  state.detail = null;
  state.detailOpen = false;
  render();
 } else if (Number.isFinite(id) && id !== state.selected) {
  state.selected = id;
  state.detailOpen = true;
  loadDetail(id);
  render();
 }
});

render();
boot();
