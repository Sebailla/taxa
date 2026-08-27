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
  realmForFolderPath,
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

  // titleBlock now collapses three visual elements (rank badge + name +
  // authorship) into two. Rank badge stays inline as a quick tier cue;
  // the scientific-name span owns the row's identity. Authorship moves
  // into the span's `title` attribute so it surfaces on hover only —
  // the row no longer needs to render a separate low-opacity span next
  // to the name. See P1 #2 in the Impeccable critique for the rationale.
  const nameTitle = taxon.authorship
    ? `${taxon.scientific_name} ${taxon.authorship}`
    : null;
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
      {
        class: `${nameCls} truncate ${extinctCls} ${scientificNameClass(taxon.rank)}`,
        title: nameTitle,
        "aria-label": nameTitle || undefined,
      },
      taxon.scientific_name,
    ),
  );

  // Source affordances — previously two inline pills ("WoRMS" / "CoL")
  // next to the species count. Now both collapse into a single small
  // info icon whose hover tooltip carries the same descriptive text
  // the pills used. The click-through WoRMS URL survives as a kebab
  // menu item (when worms_id is present), so the path to marinespecies
  // is preserved without taking up row real-estate.
  //
  //   * CoL view AND taxon is CoL-only (coldp_id set, worms_id NULL):
  //     small info glyph — tooltip: "CoL-only — ColDP ID N (no WoRMS
  //     match)."
  //   * WoRMS view AND taxon has worms_id: tooltip describes whether
  //     the taxon is WoRMS-only or CoL+WoRMS. The kebab menu adds a
  //     "View on WoRMS" item (an <a target="_blank">) that opens the
  //     same marinespecies.org URL the old badge linked to.
  //   * Every other case (CoL+WoRMS in CoL view, no source data at
  //     all): no icon at all — keeps the row visually clean.
  let sourceTooltipText = null;
  let sourceWormsUrl = null;
  if (state.treeSource === "col" && taxon.coldp_id && !taxon.worms_id) {
    sourceTooltipText = `CoL-only — ColDP ID ${taxon.coldp_id} (no WoRMS match).`;
  } else if (taxon.worms_id && state.treeSource !== "col") {
    const isWormsOnly = !taxon.coldp_id;
    sourceWormsUrl = `https://www.marinespecies.org/aphia.php?p=taxdetails&id=${taxon.worms_id}`;
    sourceTooltipText = isWormsOnly
      ? `WoRMS-only — AphiaID ${taxon.worms_id} (no CoL match). Open in WoRMS.`
      : `WoRMS cross-link — AphiaID ${taxon.worms_id}. Open in WoRMS.`;
  }
  const sourceInfo = sourceTooltipText
    ? el(
        "span",
        {
          class:
            "material-symbols-outlined text-[14px] text-on-surface-variant hover:text-primary transition-colors cursor-help",
          title: sourceTooltipText,
          role: "img",
          "aria-label": sourceTooltipText,
        },
        "info",
      )
    : null;

  // Kebab dropdown — collapses the per-row search (lupa) and folder
  // (create_new_folder) actions into a single `more_vert` button that
  // opens on click. Items inside the menu reuse the same `data-action`
  // / `data-taxon-id` attributes the row used to expose inline, so
  // nav.js keeps working unchanged. The kebab trigger is hover-gated
  // via CSS (`.tree-row:hover .kebab-trigger { opacity: 1 }` in
  // index.html) so the visual weight stays low for full-tree scrolls.
  //
  // Items, in render order:
  //   1. "Search online"   — data-action="open-searches" — always when
  //      scientific_name is non-empty (today's lupa).
  //   2. "Open folder"     — data-action="open-folder-tab" — only when
  //      the root→taxon folder exists on disk (today's materialize
  //      icon).
  //   3. "View on WoRMS"   — <a target="_blank"> — only when
  //      sourceWormsUrl is set. Carries the same marinespecies URL as
  //      the legacy inline pill; rendering as a menu item keeps the
  //      row clean without losing the click-through.
  const taxonIdStr = String(taxon.id);
  const hasFolder = Boolean(
    taxon.research_path_exists || state.materialized.has(taxon.id),
  );
  const kebabItems = [];
  if (taxon.scientific_name) {
    kebabItems.push(
      el(
        "button",
        {
          class: "kebab-item",
          "data-action": "open-searches",
          "data-taxon-id": taxonIdStr,
          role: "menuitem",
          type: "button",
        },
        el(
          "span",
          {
            class:
              "material-symbols-outlined text-[16px] text-on-surface-variant",
          },
          "search",
        ),
        el("span", { class: "kebab-item-label" }, "Search online"),
      ),
    );
  }
  if (hasFolder && taxon.scientific_name) {
    kebabItems.push(
      el(
        "button",
        {
          class: "kebab-item",
          "data-action": "open-folder-tab",
          "data-taxon-id": taxonIdStr,
          role: "menuitem",
          type: "button",
        },
        el(
          "span",
          {
            class:
              "material-symbols-outlined text-[16px] text-on-surface-variant",
          },
          "folder_open",
        ),
        el("span", { class: "kebab-item-label" }, "Open folder"),
      ),
    );
  }
  if (sourceWormsUrl) {
    kebabItems.push(
      el(
        "a",
        {
          class: "kebab-item",
          href: sourceWormsUrl,
          target: "_blank",
          rel: "noopener noreferrer",
          role: "menuitem",
        },
        el(
          "span",
          {
            class:
              "material-symbols-outlined text-[16px] text-on-surface-variant",
          },
          "open_in_new",
        ),
        el("span", { class: "kebab-item-label" }, "View on WoRMS"),
      ),
    );
  }
  const kebab =
    kebabItems.length > 0
      ? el(
          "div",
          { class: "kebab", "data-kebab-for": taxonIdStr },
          el(
            "button",
            {
              class:
                "kebab-trigger material-symbols-outlined text-[16px] text-on-surface-variant hover:text-primary transition-colors",
              "data-action": "toggle-kebab",
              "data-taxon-id": taxonIdStr,
              type: "button",
              "aria-label": `More actions for ${taxon.scientific_name || taxonIdStr}`,
              "aria-haspopup": "menu",
              "aria-expanded": "false",
              title: "More actions",
            },
            "more_vert",
          ),
          el("div", { class: "kebab-menu", role: "menu" }, ...kebabItems),
        )
      : null;

  const metaBlock = el(
    "div",
    { class: "flex items-center gap-2 shrink-0" },
    sourceInfo,
    statusDot(taxon.status),
    // Species count stays inline — it's the primary "this taxon has
    // data" signal. Hovering reveals the full binomial + count in the
    // tooltip so users who want context can still get it without
    // opening the detail panel.
    taxon.species_count
      ? el(
          "span",
          {
            class:
              "font-mono-data text-mono-data text-on-surface-variant bg-surface-container px-2 py-1 rounded",
            title: `${speciesCountBadge(taxon.species_count)} under ${taxon.scientific_name}`,
          },
          speciesCountBadge(taxon.species_count),
        )
      : null,
    kebab,
  );

  // Realm tint — the Classification tree mirrors the Browser folder
  // tint: every row carries data-realm so the CSS in index.html can
  // color .scientific-name per domain / kingdom. Same path encoding
  // (taxonomic backbone == Browser folder paths), so the helper from
  // format.js works for both views. "other" fallback prevents
  // data-realm="" which CSS attribute selectors won't match.
  const realm = realmForFolderPath(taxon.path || "");
  return el(
    "div",
    {
      id: `taxon-${taxon.id}`,
      class: `tree-row group flex items-center w-full px-4 py-row-padding-y ${cls} relative`,
      "data-taxon-id": taxon.id,
      "data-action": action,
      "data-realm": realm || "other",
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
  // Guard: renderTree() can be called from boot()'s final render() or
  // from a popstate handler AFTER the user has navigated to the
  // Browser tab (which replaces <main> with the file explorer shell,
  // destroying #tree-view). Bail silently when the tree view isn't
  // mounted — there's nothing to render in the explorer tab and the
  // file_explorer.js module owns the explorer pane rendering.
  const view = document.querySelector("#tree-view");
  if (!view) return;
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
//
// `selected` and `focused` are stable class names (NOT Tailwind utilities)
// so the realm-tint CSS in index.html can override the .scientific-name
// color when a row is selected or focused — the realm hue would
// otherwise fight the primary-color treatment that the Tailwind
// `text-primary` class already applies.
function rowClassFor(isSelected, isFocused) {
  if (isSelected) {
    return "selected bg-primary/5 border-l-[3px] border-primary rounded-r-lg cursor-pointer";
  }
  if (isFocused) {
    return "focused bg-surface-container-low border-l-[3px] border-outline rounded-r-lg cursor-pointer";
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
