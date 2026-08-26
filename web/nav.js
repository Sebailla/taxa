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

import { state, initialExplorerShape } from "./state.js";
import { loadChildren, loadTaxon } from "./api.js";
import { loadDetail } from "./detail.js";
import { renderTree } from "./tree.js";
import { closeSearch } from "./search.js";
import { el } from "./dom.js";

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
  const pickParentId = (t) => {
    if (!t) return null;
    if (state.treeSource === "worms") return t.taxon.worms_parent_id;
    if (state.treeSource === "freshwater") return t.taxon.freshwater_parent_id;
    return t.taxon.parent_id;
  };
  let parentId = pickParentId(taxon);
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
    parentId = pickParentId(parent);
  }
}

function renderCollapseAllButton() {
  const btn = document.querySelector("#collapse-all");
  if (!btn) return;
  const hasExpansion = state.expanded.size > 0 || state.showAll.size > 0;
  btn.disabled = !hasExpansion;
  btn.classList.toggle("opacity-40", !hasExpansion);
  btn.classList.toggle("cursor-not-allowed", !hasExpansion);
}

// ------------------------------------------------------------------
// Header navigation tabs (Browser / Classification / Settings / Help)
// ------------------------------------------------------------------
// The header carries four nav links (Browser / Classification / Settings /
// Help), each stamped with `data-path="<tab>"`. Clicking Browser mounts
// the file explorer (if a taxon is selected) or the placeholder (if
// state.selected is null). Clicking Help mounts the About / Help view
// (web/help.js) into <main>. Clicking Classification or Settings clears
// the explorer and restores the classification view. The Explorer and
// Help modules are imported lazily inside the function body so nav.js
// can boot before they're resolved — and so the same nav.js stays
// usable even if either fails to load (the classification path is
// untouched).

// Highlight a single header tab (Browser / Classification / Settings /
// Help) by toggling the same primary-color + bold treatment the
// index.html ships with. Shared by mountFileExplorer / clearFileExplorer
// / mountHelpView so the active
// styling stays consistent.
function setActiveHeaderTab(activePath) {
  document.querySelectorAll("[data-path]").forEach((a) => {
    const isActive = a.dataset.path === activePath;
    a.classList.toggle("text-primary", isActive);
    a.classList.toggle("font-bold", isActive);
    a.classList.toggle("text-on-surface-variant", !isActive);
    a.classList.toggle("font-medium", !isActive);
    a.setAttribute("aria-current", isActive ? "page" : "false");
  });
}

// Build the empty classification-view shell inside <main>'s flex column.
// Two children — the sticky breadcrumb host and the inner column hosting
// the detail panel + tree view. Static markup, no user-controlled data,
// so el() from dom.js (which already powers every other renderer) is
// the safe choice and avoids the innerHTML XSS lint rule.
function buildClassificationShell() {
  const breadcrumbHost = el("div", {
    id: "breadcrumb-host",
    class:
      "sticky top-0 z-40 w-full px-margin-page py-6 border-b border-outline-variant/20 bg-surface/95 backdrop-blur-md",
  });
  const breadcrumbInner = el(
    "div",
    { class: "flex items-center justify-between gap-gutter" },
    el("nav", {
      id: "breadcrumb",
      class:
        "flex items-center gap-2 text-body-sm font-body-sm text-on-surface-variant min-w-0 overflow-x-auto",
    }),
    el(
      "button",
      {
        id: "collapse-all",
        type: "button",
        class:
          "shrink-0 flex items-center gap-1 text-body-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low px-3 py-1.5 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent",
        title: "Collapse all expanded nodes",
      },
      el(
        "span",
        { class: "material-symbols-outlined text-[18px]" },
        "unfold_less",
      ),
      el("span", null, "Collapse all"),
    ),
  );
  breadcrumbHost.append(breadcrumbInner);
  const detailPanel = el("div", {
    id: "detail-panel",
    class: "hidden mb-6",
  });
  const treeView = el("div", {
    id: "tree-view",
    class: "flex flex-col gap-1 w-full relative",
  });
  const inner = el(
    "div",
    {
      class:
        "flex flex-col w-full max-w-5xl mx-auto py-8 px-row-padding-x lg:px-0",
    },
    detailPanel,
    treeView,
  );
  return el(
    "div",
    { class: "flex flex-col w-full text-on-surface" },
    breadcrumbHost,
    inner,
  );
}

// Mount the file explorer into <main>. Idempotent: if the explorer is
// already mounted for the same taxon, the call is a no-op (no re-fetch).
// Pass rootTaxonId=null to render the placeholder ("Select a taxon to
// browse its files.") instead of the explorer's tree+viewer shell.
async function mountFileExplorer(rootTaxonId) {
  setActiveHeaderTab("browser");
  const main = document.querySelector("main > div");
  if (!main) return;
  // Lazy import — keeps the top-level cycle simple (file_explorer.js
  // also imports render() from app.js; mirroring the same lazy pattern
  // nav.js uses for dom.js avoids module-init ordering bugs).
  const fileExplorer = await import("./file_explorer.js");
  await fileExplorer.mount(main, rootTaxonId);
}

// Mount the About / Help view into <main>. Mirrors mountFileExplorer's
// shape — set the active header tab, drop any mounted Browser state,
// then drive the render pipeline to paint the help shell.
//
// clearFileExplorer() always calls setActiveHeaderTab("classification"),
// so we override to "help" AFTER it returns and BEFORE the final render()
// so the `?` button carries the primary-color treatment on the second
// pass. The two-pass render is intentional: the first render (inside
// clearFileExplorer) needs a fresh classification shell to land in;
// the second render (here) sees state.helpOpen=true and stamps help
// content on top of that shell.
async function mountHelpView() {
  await clearFileExplorer();
  state.helpOpen = true;
  setActiveHeaderTab("help");
  render();
}

// Drop the explorer state and listeners. Called when the user leaves the
// Browser tab (Classification or Settings) so any in-flight fetches are
// aborted and the right viewer is reset to a fresh empty placeholder.
// The classification view is re-rendered via the normal render() pipeline.
async function clearFileExplorer() {
  // Drop the explorer module's listeners + in-flight fetches first so no
  // stale render fires after we reset state.explorer.
  try {
    const fileExplorer = await import("./file_explorer.js");
    fileExplorer.clear();
  } catch (e) {
    console.error("file_explorer.clear() failed", e);
  }
  // Reset state.explorer to its initial shape via the exported helper so
  // nav.js doesn't have to duplicate the literal from state.js.
  Object.assign(state.explorer, initialExplorerShape());
  setActiveHeaderTab("classification");
  // Restore the classification-view shell so render() can re-populate it.
  const main = document.querySelector("main > div");
  if (main) {
    main.replaceChildren(buildClassificationShell());
  }
  render();
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
    // Per-row search icon — selects the taxon and forces the Search
    // tab to be active. The icon's data-taxon-id carries the id; the
    // detail panel's tab state is set BEFORE selectTaxon so the
    // subsequent render() sees the right default.
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    if (Number.isFinite(id)) {
      state.activeTab[id] = "searches";
      selectTaxon(id);
    }
    return;
  } else if (action === "open-folder-tab") {
    // Per-row folder icon (only rendered when the taxon's path is
    // already on disk — see tree.js). Opens the same detail panel
    // the lupa opens, but on the "Folder" tab instead of
    // "Search". Mirrors open-searches one-for-one: select the
    // taxon, force the tab key, render.
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    if (!Number.isFinite(id)) return;
    state.activeTab[id] = "folder";
    selectTaxon(id);
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
      const el = document.querySelector(`#taxon-${id}`);
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
      const el = document.querySelector(`#taxon-${id}`);
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
  } else if (action === "nav-tab") {
    // Header navigation (Browser / Classification / Settings / Help).
    // The data-path attribute on each link carries the tab key.
    //   - "browser" → mount the explorer (placeholder when no taxon
    //     is selected; otherwise fetch + render the tree).
    //   - "help" → mount the About / Help view (drops any mounted
    //     explorer first, then paints the help shell).
    //   - "classification" / "settings" → clear the explorer (drops
    //     listeners + aborts in-flight fetches) and restore the
    //     classification view via the normal render() pipeline.
    const tab = e.target.closest("[data-action=nav-tab]").dataset.path;
    if (tab === "browser") {
      const id = state.selected;
      if (id == null) {
        // No taxon selected → mount the placeholder only (no API call).
        mountFileExplorer(null);
      } else {
        mountFileExplorer(id);
      }
    } else if (tab === "help") {
      mountHelpView();
    } else {
      // Classification / Settings: drop the explorer if it was mounted,
      // and ensure the help shell is closed (mountHelpView sets the
      // flag; the inverse path needs to clear it).
      state.helpOpen = false;
      clearFileExplorer();
    }
    e.preventDefault();
  }
});

// Collapse-all button
document.querySelector("#collapse-all").addEventListener("click", () => {
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
  // on Search (the spec'd default). Switching from freshwater to CoL
  // shouldn't carry over a Search tab from a freshwater-selected taxon.
  state.activeTab = {};
  // Clear focus + selection so the new view starts from a blank slate,
  // not with the previous view's node still highlighted in the breadcrumb
  // or detail panel. The focused taxon from the previous view may not
  // even be visible under the new source's filter.
  state.focused = null;
  state.selected = null;
  state.detail = null;
  state.detailOpen = false;
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
  mountFileExplorer,
  clearFileExplorer,
};

// `render()` is imported via a circular reference from app.js. It's only
// used inside the action bodies above (runtime), never at module-init —
// ES module live bindings resolve correctly in this case.
import { render } from "./app.js";
