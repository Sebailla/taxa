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
 mountFileExplorer,
 clearFileExplorer,
} from "./nav.js";
import { el } from "./dom.js";
import { renderVersionBanner } from "./banner.js";
import { renderHelp } from "./help.js";
import { bootKeymap } from "./keymap.js";

// Top-level render orchestrator. Called after any state mutation that
// changes what the page should display. Re-renders every region; the
// cost is fine for the 5.4M-row dataset because the visible tree is
// bounded by state.expanded + PAGE_SIZE.
//
// When state.helpOpen is true, the About / Help view takes over <main>
// and the classification renderers (tree / breadcrumb / detail) are
// skipped — there's nothing to render under help mode, and calling them
// would re-stamp the classification shell on top of the help view.
export function render() {
 if (state.helpOpen) {
  const main = document.querySelector("main > div");
  if (main) renderHelp(main);
  return;
 }
 renderTree();
 renderBreadcrumb();
 renderCollapseAllButton();
 renderDetailPanel();
}

async function boot() {
 // Global keyboard shortcuts (see web/keymap.js). Attached exactly once
 // at boot — never re-attached on render() so the listener stays a
 // single source of truth for key events.
 bootKeymap();

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

 // Route the initial view from the URL hash. Two cases:
 //   - #help     → reload landed on the Help view (URL pushed by
 //                 mountHelpView; set the flag + highlight the Help
 //                 tab inline without pushing history again, since
 //                 the URL already encodes the view).
 //   - #<taxon>  → deep link to a species; select it and expand its
 //                 ancestors (replacing the current history entry's
 //                 state so the back/forward stack stays clean).
 // Otherwise: no pre-expansion, no initial focus. The tree shows the
 // 6 root domains collapsed with nothing highlighted; the breadcrumb
 // is empty. The user picks a starting node by clicking.
 if (location.hash === "#help") {
  state.helpOpen = true;
  // Highlight the Help tab inline (mirror setActiveHeaderTab("help")
  // from nav.js without exporting it). The Help button's bg-primary
  // styling is permanent; only aria-current flips.
  document.querySelectorAll("[data-path]").forEach((a) => {
   const isActive = a.dataset.path === "help";
   a.setAttribute("aria-current", isActive ? "page" : "false");
  });
 } else {
  const hashId = parseInt(location.hash.replace("#", ""), 10);
  if (hashId && Number.isFinite(hashId)) {
   await expandAncestorsOf(hashId);
   state.focused = hashId;
   selectTaxon(hashId, { updateUrl: "replace" });
  }
 }

 render();
}

// Browser back/forward: restore the right view from the popped
// history entry. The pushed states (set by selectTaxon,
// mountHelpView, and the nav-tab handler) carry a discriminator:
//   - { view: "help" }            → mount Help
//   - { view: "browser" }         → mount the file explorer
//   - { view: "classification" }  → clear the explorer, restore the
//                                   classification shell
//   - { id: <taxonId> }           → legacy deep-link routing
//                                   (selectTaxon pushes this shape)
//   - null                        → initial page-load entry
//
// When transitioning out of help mode we MUST rebuild the
// classification shell — render() with state.helpOpen=false paints
// into the existing shell, but the help view replaced <main>'s
// children, so the shell has to be re-created first. clearFileExplorer
// does exactly that (it's idempotent when the explorer isn't mounted),
// and it's awaited so the legacy taxon-id branch below runs against
// a freshly-rebuilt shell.
//
// Lives in app.js because it's a window-level handler wired once at
// module load and doesn't fit any other module's responsibility.
window.addEventListener("popstate", async (e) => {
 const view = e.state?.view;
 if (view === "help") {
  if (!state.helpOpen) state.helpOpen = true;
  render();
  return;
 }
 if (view === "browser") {
  if (state.helpOpen) state.helpOpen = false;
  // Fire-and-forget — mountFileExplorer is async (lazy import +
  // async fetch). By the time it renders, state.helpOpen is already
  // false so any subsequent global render() won't overwrite the
  // explorer with the help view.
  mountFileExplorer(state.selected);
  return;
 }
 if (view === "classification") {
  if (state.helpOpen) state.helpOpen = false;
  // clearFileExplorer also rebuilds the classification shell and
  // calls render() at the end (no-op if the explorer wasn't mounted).
  clearFileExplorer();
  return;
 }
 // Legacy taxon-id routing. If we're leaving help mode, rebuild the
 // shell first so the render() below paints into a real host instead
 // of the orphaned help view's leftover DOM.
 if (state.helpOpen) {
  state.helpOpen = false;
  await clearFileExplorer();
 }
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
 } else {
  // Same id (or no id and no selection) — still render so the
  // newly-rebuilt classification shell paints the current tree.
  render();
 }
});

render();
boot();
