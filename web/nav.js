// Navigation controller: state-mutating actions (toggleExpand, selectTaxon,
// closeDetail, collapseAll, expandAncestorsOf) plus the main click
// delegation that maps every data-action in the page to one of those
// actions. Also owns the tree-source toggle (CoL / WoRMS / Freshwater)
// and the collapse-all button handler.
//
// Circular imports: this module calls render() from app.js inside its
// function bodies (never at module-init), and tree.js calls toggleExpand/
// selectTaxon inside its el() event handlers (never at module-init).
// ES module live bindings handle both cycles correctly.

import { state } from "./state.js";
import { loadChildren, loadTaxon } from "./api.js";
import { loadDetail } from "./detail.js";
import { renderTree } from "./tree.js";
import { closeSearch } from "./search.js";

// ------------------------------------------------------------------
// Actions
// ------------------------------------------------------------------

async function toggleExpand(id) {
  if (state.expanded.has(id)) {
    state.expanded.delete(id);
    render();
    return;
  }
  await loadChildren(id);
  state.expanded.add(id);
  // In WoRMS view (and Freshwater view), auto-unroll every tier of this
  // node so the user sees the full subtree on a single click — Biota →
  // Animalia → phylum → class → ... → species without hitting "Load N
  // more" at every level. CoL view keeps the PAGE_SIZE=5 default to stay
  // snappy.
  if (state.treeSource === "worms" || state.treeSource === "freshwater") {
    const kids = state.cache.get(id)?.children;
    if (kids && kids.length > 0) {
      for (const k of kids) state.showAll.add(`${id}::${k.rank}`);
    }
  }
  render();
}

function selectTaxon(id, opts = {}) {
  const { updateUrl = "push" } = opts;
  if (state.selected === id) return;
  state.selected = id;
  if (id === null) {
    // Clearing the selection: keep the URL clean (no trailing " ").
    if (updateUrl === "push")
      history.pushState({ id: null }, "", location.pathname);
    state.detail = null;
    state.detailOpen = false;
  } else {
    // Selecting a new species always re-opens the detail panel. The X button
    // is what hides it. New selections always win.
    state.detailOpen = true;
    if (updateUrl === "push") history.pushState({ id }, "", `#${id}`);
    else if (updateUrl === "replace")
      history.replaceState({ id }, "", `#${id}`);
    loadDetail(id);
  }
  render();
}

function closeDetail() {
  state.detailOpen = false;
  render();
}

function collapseAll() {
  if (state.expanded.size === 0 && state.showAll.size === 0) return;
  state.expanded.clear();
  state.showAll.clear();
  render();
}

async function expandAncestorsOf(id) {
  const taxon =
    state.cache.get(id) ||
    (await (async () => {
      await loadTaxon(id);
      return state.cache.get(id);
    })());
  if (!taxon) return;
  // Walk the hierarchy that matches the current view. CoL uses
  // `parent_id` (the global backbone); WoRMS uses `worms_parent_id`
  // (Biota → kingdom → phylum → ... → species), independent of CoL.
  // Freshwater uses `freshwater_parent_id`, isolated from both.
  const useWorms = state.treeSource === "worms";
  const useFreshwater = state.treeSource === "freshwater";
  let parentId = useWorms
    ? taxon.taxon.worms_parent_id
    : useFreshwater
      ? taxon.taxon.freshwater_parent_id
      : taxon.taxon.parent_id;
  while (parentId) {
    if (!state.expanded.has(parentId)) {
      await loadChildren(parentId);
      state.expanded.add(parentId);
      // In WoRMS view, auto-unroll every tier of every ancestor so the
      // chain doesn't get stuck behind PAGE_SIZE=5 hides (e.g. Chordata
      // being the 7th phylum of Animalia alphabetically).
      // In CoL view we keep PAGE_SIZE=5 staircase — clicking "Load N
      // more" expands deeper tiers on demand. That keeps the DOM small
      // and avoids opening every kingdom/phylum/order/family/genus in the
      // chain just to reach a single deep target.
      if (state.treeSource === "worms" || state.treeSource === "freshwater") {
        const kids = state.cache.get(parentId)?.children;
        if (kids && kids.length > 0) {
          for (const k of kids) state.showAll.add(`${parentId}::${k.rank}`);
        }
      }
    }
    const parent = state.cache.get(parentId);
    parentId = useWorms
      ? parent?.taxon.worms_parent_id
      : useFreshwater
        ? parent?.taxon.freshwater_parent_id
        : parent?.taxon.parent_id;
  }
}

function renderCollapseAllButton() {
  const btn = document.getElementById("collapse-all");
  if (!btn) return;
  const hasExpansion = state.expanded.size > 0 || state.showAll.size > 0;
  btn.disabled = !hasExpansion;
  btn.classList.toggle("opacity-40", !hasExpansion);
  btn.classList.toggle("cursor-not-allowed", !hasExpansion);
}

// ------------------------------------------------------------------
// Main click delegation
// ------------------------------------------------------------------
// Every interactive element in the page carries a data-action attribute
// (set by el() builders across the other modules). This single handler
// maps the action to the right controller function. The tab strip is
// checked FIRST because tab buttons carry data-tab but no data-action.
//
// Scrolling helpers (scrollTaxonBelowCard, waitForDetailReady) live in
// dom.js; they're imported lazily via the inline import below to avoid
// pulling them into this module's top-level deps. Both helpers are only
// used inside the "select-from-search" branch.
document.addEventListener("click", async (e) => {
  // Tab strip — checked BEFORE the data-action branch because tab
  // buttons carry data-tab but no data-action. Switching the active tab
  // is O(1): just persist the choice in state.activeTab and re-render
  // the detail panel (which hides non-active sections via inline style).
  const tabBtn = e.target.closest("[data-tab]");
  if (tabBtn) {
    const tabKey = tabBtn.dataset.tab;
    const taxonId = state.selected;
    if (taxonId != null) {
      state.activeTab[taxonId] = tabKey;
      render();
    }
    return;
  }
  const action = e.target.closest("[data-action]")?.dataset.action;
  if (!action) {
    if (
      !e.target.closest("#search-input") &&
      !e.target.closest("#search-results")
    ) {
      closeSearch();
    }
    return;
  }
  if (action === "toggle-expand") {
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    state.focused = id;
    toggleExpand(id);
  } else if (action === "select") {
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    state.focused = id;
    // Species are leaves: just select, no expansion.
    selectTaxon(id);
  } else if (action === "open-searches") {
    // Per-row search icon — selects the taxon and forces the Búsquedas
    // tab to be active. The icon's data-taxon-id carries the id; the
    // detail panel's tab state is set BEFORE selectTaxon so the
    // subsequent render() sees the right default.
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    if (Number.isFinite(id)) {
      state.activeTab[id] = "busquedas";
      selectTaxon(id);
    }
    return;
  } else if (action === "select-from-search") {
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    closeSearch();
    // Lazy import — only the search-result path needs scroll helpers,
    // and inline import keeps them out of the top-level cycle analysis.
    const { scrollTaxonBelowCard, waitForDetailReady } = await import(
      "./dom.js"
    );
    // IIFE so we can await expandAncestorsOf before scrolling — the
    // click handler itself is sync, and without await the row isn't in
    // the DOM yet when scrollIntoView runs.
    await expandAncestorsOf(id);
    state.focused = id;
    selectTaxon(id);
    // loadDetail fetches vernaculars/synonyms/distribution async and
    // re-renders the card at its final (much taller) size. We must
    // wait for that to finish, otherwise the manual scroll calculates
    // against the "Loading details…" stub and the taxon ends up too
    // low once the real content paints in.
    await waitForDetailReady(id);
    requestAnimationFrame(() => {
      const el = document.getElementById(`taxon-${id}`);
      if (!el) return;
      // Manual scroll — the sticky detail card sits between the
      // breadcrumb and the tree, so scrollIntoView's "center of
      // viewport" puts the row halfway under the card. Calculate the
      // visible tree area below the card and center the row in it.
      scrollTaxonBelowCard(el);
      // One-shot pulse so the user can spot which row came from the
      // search even on a deep branch. Toggling off + reflow forces
      // the animation to restart if the user clicks another result
      // quickly.
      el.classList.remove("search-pulse");
      void el.offsetWidth; // force reflow to restart the animation
      el.classList.add("search-pulse");
      setTimeout(() => el.classList.remove("search-pulse"), 1800);
    });
  } else if (action === "focus-segment") {
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    state.focused = id;
    render();
    // After render, bring the focused node into view, centered in the
    // area below the sticky card.
    const { scrollTaxonBelowCard } = await import("./dom.js");
    requestAnimationFrame(() => {
      const el = document.getElementById(`taxon-${id}`);
      if (el) scrollTaxonBelowCard(el);
    });
  } else if (action === "focus-home") {
    state.focused = null;
    selectTaxon(null);
  } else if (action === "load-all") {
    const btn = e.target.closest("[data-action=load-all]");
    const parentId = parseInt(btn.dataset.parentId, 10);
    const rank = btn.dataset.rank;
    state.showAll.add(`${parentId}::${rank}`);
    render();
  } else if (action === "home") {
    e.preventDefault();
    state.focused = null;
    selectTaxon(null);
  } else if (action === "close-detail") {
    closeDetail();
  }
});

// Collapse-all button
document.getElementById("collapse-all").addEventListener("click", () => {
  collapseAll();
});

// Tree-source toggle (CoL / WoRMS / Freshwater). Event delegation so
// dynamically appended buttons (the Freshwater toggle, appended at boot()
// when freshwater is loaded) work without re-binding. Switching views
// invalidates the children cache — CoL, WoRMS, and Freshwater children
// live in different hierarchies and must be re-fetched with the right
// `source=` param. Also clears expand/showAll so the tree rebuilds from
// the new root instead of carrying over the previous view's expansion.
document.addEventListener("click", (e) => {
  const btn = e.target.closest("#tree-source-toggle [data-tree-source]");
  if (!btn) return;
  const source = btn.dataset.treeSource;
  if (state.treeSource === source) return;
  state.treeSource = source;
  // Drop cached children — they were loaded with the previous source and
  // are stale for the new one.
  for (const node of state.cache.values()) {
    node.children = null;
  }
  state.expanded.clear();
  state.showAll.clear();
  // Reset per-taxon tab memory so the new view's detail panel starts
  // on Búsquedas (the spec'd default). Switching from freshwater to CoL
  // shouldn't carry over a Búsquedas tab from a freshwater-selected taxon.
  state.activeTab = {};
  document
    .querySelectorAll("#tree-source-toggle [data-tree-source]")
    .forEach((b) => {
      const active = b.dataset.treeSource === state.treeSource;
      b.classList.toggle("active", active);
      b.setAttribute("aria-pressed", active ? "true" : "false");
    });
  renderTree();
});

// Extant toggle removed from the header. The filter is still active by
// default (state.extantOnly = true) and can be re-enabled by re-adding the
// toggle — just uncomment the block below.

export {
  toggleExpand,
  selectTaxon,
  closeDetail,
  collapseAll,
  expandAncestorsOf,
  renderCollapseAllButton,
};

// `render()` is imported via a circular reference from app.js. It's only
// used inside the action bodies above (runtime), never at module-init —
// ES module live bindings resolve correctly in this case.
import { render } from "./app.js";
