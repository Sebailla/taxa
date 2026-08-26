// Tree rendering pipeline: renderTree → renderNode (recursive) →
// renderNodeRow + renderTierHeader. matchesTreeSource and groupByRank
// are the two predicates feeding the recursion.

import { state, PAGE_SIZE } from "./state.js";
import {
  rankLabel,
  rankPlural,
  statusDot,
  speciesCountBadge,
  scientificNameClass,
  RANK_INDEX,
} from "./format.js";
import { el } from "./dom.js";

// Propagate the "materialized" state from a confirmed root taxon to its
// visible descendants. When the user confirms a materialize for taxon X,
// the backend creates the root→X folder chain; every child / grandchild
// of X whose path starts with X's path automatically has its folder on
// disk too (the leaf folder is a subfolder of X's leaf). Marking them
// in `state.materialized` paints their per-row icon green without a
// fresh /api/taxon/{id}/children round trip.
//
// This is purely a DOM walk over expanded rows. Non-expanded descendants
// will be marked correctly the next time they're loaded (the backend
// includes `research_path_exists` per child), so propagation is
// best-effort + self-healing on the next expand.
function propagateMaterialized(rootTaxonId) {
  const rootNode = state.cache.get(rootTaxonId);
  if (!rootNode) return;
  const rootPath = rootNode.taxon.path;
  state.materialized.add(rootTaxonId);
  if (!rootPath) return; // NULL path → can't compare to descendants; root already marked
  document.querySelectorAll("[data-taxon-id]").forEach((row) => {
    const id = parseInt(row.dataset.taxonId, 10);
    if (!Number.isFinite(id) || id === rootTaxonId) return;
    const node = state.cache.get(id);
    if (!node || !node.taxon.path) return;
    // A descendant's path equals the root's path (shouldn't happen, but
    // guards against a self-row) OR starts with the root's path followed
    // by a separator. The separator is required so "Animalia" doesn't
    // match "AnimaliaX" (no such rank, but the check is cheap insurance).
    if (
      node.taxon.path === rootPath ||
      node.taxon.path.startsWith(rootPath + "/")
    ) {
      state.materialized.add(id);
    }
  });
}

function renderNodeRow(taxon, opts = {}) {
  const {
    depth = 0,
    isExpanded = false,
    isSelected = false,
    isFocused = false,
  } = opts;
  const indentPx = depth * 24;
  const isSpecies = taxon.rank === "species" || taxon.rank === "subspecies";
  // Species/subspecies are leaves: clicking selects (no expand).
  // Higher ranks: clicking toggles expansion.
  const action = isSpecies ? "select" : "toggle-expand";
  // Species have no children to expand — don't show the chevron.
  const hasChildren = !isSpecies;
  // Selected (primary, detailed) wins over focused (subtle marker).
  // rounded-r-lg keeps the right corners soft but leaves the left edge
  // (where the marker border lives) perfectly square — the border has
  // nowhere to curve into.
  const cls = rowClassFor(isSelected, isFocused);
  const rankCls = rankClassFor(isSelected, isFocused);
  const nameCls = nameClassFor(isSelected, isFocused, depth);
  // For species, render a small marker (•) instead of the chevron so the row
  // doesn't look like it has children to expand.
  const chevron = chevronFor(hasChildren, isExpanded);
  const arrowColor =
    isSelected || isFocused ? "text-primary" : "text-on-surface-variant";
  const extinctCls = taxon.is_extinct ? "line-through opacity-70" : "";

  const titleBlock = el(
    "div",
    { class: "flex items-center gap-3 flex-1 min-w-0" },
    el(
      "span",
      {
        class: `rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded ${rankCls}`,
      },
      rankLabel(taxon.rank),
    ),
    el(
      "span",
      { class: `${nameCls} truncate ${extinctCls} ${scientificNameClass(taxon.rank)}` },
      taxon.scientific_name,
    ),
    taxon.authorship
      ? el(
          "span",
          {
            class:
              "font-body-sm text-body-sm text-on-surface-variant ml-2 opacity-70 truncate",
          },
          taxon.authorship,
        )
      : null,
  );

  // Source badges — mutually exclusive across the two views.
  //   * CoL view (treeSource === 'col') AND taxon is CoL-only (coldp_id set,
  //     worms_id NULL): render a discrete "CoL" outline badge so the user
  //     can see at a glance which CoL backbone entries lack a WoRMS match.
  //   * WoRMS view (treeSource !== 'col') AND taxon has worms_id: render a
  //     "WoRMS" badge — filled accent for WoRMS-only taxa, outline accent
  //     for CoL+WoRMS matches. Links to marinespecies.org in a new tab.
  //   * All other cases (CoL+WoRMS in CoL view, or no source data at all):
  //     no badge — keeps the row visually clean.
  let wormsBadge = null;
  let colBadge = null;
  if (state.treeSource === "col" && taxon.coldp_id && !taxon.worms_id) {
    colBadge = el(
      "span",
      {
        class:
          "text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-on-surface-variant/10 text-on-surface-variant no-underline cursor-default",
        title: `CoL-only — ColDP ID ${taxon.coldp_id} (no WoRMS match).`,
      },
      "CoL",
    );
  } else if (taxon.worms_id && state.treeSource !== "col") {
    const isWormsOnly = !taxon.coldp_id;
    wormsBadge = el(
      "a",
      {
        href: `https://www.marinespecies.org/aphia.php?p=taxdetails&id=${taxon.worms_id}`,
        target: "_blank",
        rel: "noopener noreferrer",
        class: isWormsOnly
          ? "text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded text-white no-underline"
          : "text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors no-underline",
        style: isWormsOnly ? "background-color: #176587;" : null,
        title: isWormsOnly
          ? `WoRMS-only — AphiaID ${taxon.worms_id} (no CoL match). Open in WoRMS.`
          : `WoRMS cross-link — AphiaID ${taxon.worms_id}. Open in WoRMS.`,
      },
      "WoRMS",
    );
  }

  const metaBlock = el(
    "div",
    { class: "flex items-center gap-2 shrink-0" },
    wormsBadge,
    colBadge,
    statusDot(taxon.status),
    taxon.species_count
      ? el(
          "span",
          {
            class:
              "font-mono-data text-mono-data text-on-surface-variant bg-surface-container px-2 py-1 rounded",
          },
          speciesCountBadge(taxon.species_count),
        )
      : null,
    // Per-row search icon — click selects the taxon and forces the
    // Search tab. Hidden when scientific_name is empty (no useful
    // search query possible). Position: end of metaBlock, right of the
    // species count. Visual treatment (16px, hover-only color shift)
    // matches design.md §4.4 — keeps the visual weight low so 16K-row
    // trees don't get noisy.
    taxon.scientific_name
      ? el(
          "button",
          {
            class:
              "search-icon-btn material-symbols-outlined text-[16px] text-on-surface-variant hover:text-primary transition-colors",
            "data-action": "open-searches",
            "data-taxon-id": String(taxon.id),
            title: `Search ${taxon.scientific_name} online`,
            "aria-label": `Open search panel for ${taxon.scientific_name}`,
          },
          "search",
        )
      : null,
    // Per-row materialize indicator — only rendered when the
    // taxon's root→taxon folder is on disk. Pure status marker:
    // saturated green for "yes, it's there", nothing at all for
    // "not yet". Creation happens in the detail panel's "Folder"
    // tab (opened from the lupa or from this icon), not from the
    // row itself.
    //
    // The backend's per-child `research_path_exists` flag is the
    // source of truth; the in-memory `state.materialized` set fills
    // in anything the user just confirmed in this session
    // (propagated to visible descendants by propagateMaterialized).
    // Clicking opens the detail panel on the Folder tab — the same
    // modal the lupa opens, just on a different tab.
    (taxon.research_path_exists || state.materialized.has(taxon.id)) &&
      taxon.scientific_name
      ? el(
          "button",
          {
            class:
              "materialize-btn material-symbols-outlined text-[16px] transition-colors text-green-700 hover:text-green-800",
            "data-action": "open-folder-tab",
            "data-taxon-id": String(taxon.id),
            title: `Folder created at ./Research/${taxon.scientific_name} — click for details`,
            "aria-label": `Folder already materialized for ${taxon.scientific_name}`,
          },
          "create_new_folder",
        )
      : null,
  );

  return el(
    "div",
    {
      id: `taxon-${taxon.id}`,
      class: `group flex items-center w-full px-4 py-row-padding-y ${cls} relative`,
      "data-taxon-id": taxon.id,
      "data-action": action,
      style: `padding-left: ${16 + indentPx}px;`,
    },
    el(
      "div",
      { class: `flex items-center justify-center w-6 h-6 mr-2 ${arrowColor}` },
      chevron,
    ),
    titleBlock,
    metaBlock,
  );
}

function groupByRank(children) {
  const groups = new Map();
  for (const c of children) {
    if (!groups.has(c.rank)) groups.set(c.rank, []);
    groups.get(c.rank).push(c);
  }
  return [...groups.entries()]
    .map(([rank, items]) => ({ rank, count: items.length, items }))
    .sort(
      (a, b) => (RANK_INDEX.get(a.rank) ?? 99) - (RANK_INDEX.get(b.rank) ?? 99),
    );
}

function renderTierHeader(parentTaxon, g, more, depth) {
  // Tier header sits at the rank's indent level (depth). This is what creates
  // the "staircase" — each tier header is one step deeper than its parent.
  const indentPx = depth * 24;
  const moreBtn =
    more > 0
      ? el(
          "button",
          {
            class: "load-all",
            "data-action": "load-all",
            "data-parent-id": parentTaxon.id,
            "data-rank": g.rank,
          },
          `Load ${more} more`,
        )
      : null;
  return el(
    "div",
    {
      class: "tier-header",
      style: `margin-left: ${indentPx}px; margin-right: 0;`,
    },
    el(
      "h2",
      null,
      el(
        "span",
        {
          class:
            "material-symbols-outlined text-[20px] text-on-surface-variant",
        },
        "arrow_drop_down",
      ),
      `${rankPlural(g.rank)} (${g.count})`,
    ),
    moreBtn,
  );
}

function renderNode(taxon, depth) {
  const isExpanded = state.expanded.has(taxon.id);
  const isSelected = state.selected === taxon.id;
  const isFocused = state.focused === taxon.id;
  const isLeaf = taxon.rank === "species" || taxon.rank === "subspecies";
  const frag = document.createDocumentFragment();
  frag.append(
    renderNodeRow(taxon, { depth, isExpanded, isSelected, isFocused }),
  );
  if (isExpanded && !isLeaf) {
    const children = state.cache.get(taxon.id)?.children;
    if (children && children.length > 0) {
      const groups = groupByRank(children);
      for (const g of groups) {
        // Apply tree-source filter (CoL / WoRMS / All) to children.
        const filtered = g.items.filter(matchesTreeSource);
        // Build a filtered group so the tier header count reflects what's
        // actually visible (CoL view drops WoRMS-only, WoRMS view drops
        // CoL-only). Otherwise the header says "13" but only 7 render.
        const filteredGroup = {
          rank: g.rank,
          count: filtered.length,
          items: filtered,
        };
        const showAll = state.showAll.has(`${taxon.id}::${g.rank}`);
        const visible = showAll ? filtered : filtered.slice(0, PAGE_SIZE);
        const more = filteredGroup.count - visible.length;
        if (filteredGroup.count > 1) {
          // Tier header sits at depth+1 — same indent as its children.
          frag.append(renderTierHeader(taxon, filteredGroup, more, depth + 1));
        }
        for (const child of visible) {
          frag.append(renderNode(child, depth + 1));
        }
      }
    }
  }
  return frag;
}

// Decide whether a taxon passes the tree-source filter.
//   col        — only CoL taxa (coldp_id IS NOT NULL)
//   worms      — only WoRMS taxa (worms_id IS NOT NULL); covers both
//                CoL+WoRMS matches and WoRMS-only marine taxa
//   freshwater — only freshwater taxa (freshwater_id IS NOT NULL). The
//                freshwater rows are isolated, so CoL-only and WoRMS-only
//                rows get filtered out — otherwise the freshwater view
//                would render all 6 domain roots mixed in.
function matchesTreeSource(taxon) {
  if (state.treeSource === "col") return Boolean(taxon.coldp_id);
  if (state.treeSource === "worms") return Boolean(taxon.worms_id);
  if (state.treeSource === "freshwater") return Boolean(taxon.freshwater_id);
  return true;
}

function renderTree() {
  const view = document.querySelector("#tree-view");
  if (state.roots.length === 0) {
    view.replaceChildren(
      el(
        "div",
        {
          class: "text-center text-on-surface-variant py-12",
        },
        "Loading domains…",
      ),
    );
    return;
  }
  const wrapper = el("div", { class: "flex flex-col gap-1 w-full relative" });
  // Apply the source filter to roots too — CoL-only domains (no
  // worms_id) don't belong in WoRMS view, and vice versa.
  for (const root of state.roots) {
    const cached = state.cache.get(root.id);
    if (cached && !matchesTreeSource(cached.taxon)) continue;
    wrapper.append(renderNode(root, 0));
  }
  view.replaceChildren(wrapper);
}

// Row class helpers — extracted from renderNodeRow so the nested-ternary
// logic (selected vs focused vs default; depth tier for the name class)
// stays readable. Each helper returns the Tailwind class string for one
// visual dimension; renderNodeRow concatenates them with template literals.
function rowClassFor(isSelected, isFocused) {
  if (isSelected) {
    return "bg-primary/5 border-l-[3px] border-primary rounded-r-lg cursor-pointer";
  }
  if (isFocused) {
    return "bg-surface-container-low border-l-[3px] border-outline rounded-r-lg cursor-pointer";
  }
  return "hover:bg-surface-container-low transition-colors rounded-r-lg cursor-pointer";
}

function rankClassFor(isSelected, isFocused) {
  if (isSelected) return "text-primary bg-primary/10";
  if (isFocused) return "text-primary bg-primary/5";
  return "text-on-surface-variant bg-surface-container-highest";
}

function nameClassFor(isSelected, isFocused, depth) {
  if (isSelected) return "font-h1 text-h1 text-primary font-bold";
  if (isFocused) return "font-h1 text-h1 text-primary";
  if (depth === 0) return "font-h1 text-h1 text-on-surface";
  return "font-body-lg text-body-lg text-on-surface";
}

// Chevron row icon: species/subspecies (no children) gets a small • marker,
// higher ranks get the material-symbol chevron pointing down when expanded
// and right when collapsed. Extracted to flatten a nested ternary.
function chevronFor(hasChildren, isExpanded) {
  if (!hasChildren) {
    return el(
      "span",
      { class: "text-on-surface-variant text-[18px] select-none" },
      "•",
    );
  }
  const glyph = isExpanded ? "arrow_drop_down" : "chevron_right";
  return el("span", { class: "material-symbols-outlined text-[20px]" }, glyph);
}

export {
  renderTree,
  renderNode,
  renderNodeRow,
  renderTierHeader,
  groupByRank,
  matchesTreeSource,
  propagateMaterialized,
};
