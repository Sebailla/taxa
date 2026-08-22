/**
 * Taxonomic Tree — frontend
 *
 * Vanilla JS, no build step.
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
 */

const API = ""; // same-origin (served by FastAPI)
const PAGE_SIZE = 5; // children per tier group before "Load all"

// ------------------------------------------------------------------
// State
// ------------------------------------------------------------------
const state = {
  roots: [], // top-level domains returned by /api/domains (CoL only)
  expanded: new Set(), // ids whose direct children are shown
  showAll: new Set(), // "${parentId}::${rank}" — tier groups fully unrolled
  selected: null, // species/subspecies id for the detail panel + URL
  focused: null, // current "position" in the tree (drives the breadcrumb)
  cache: new Map(), // id → { taxon, children: Taxon[] | null }
  extantOnly: true,
  treeSource: "col", // "col" | "worms" — header toggle filter (default CoL)

  // Search
  searchOpen: false,
  searchResults: [],
  searchTimer: null,

  // Detail panel
  detail: null,
  detailOpen: true,
  detailLoading: false,
};

// ------------------------------------------------------------------
// API helpers
// ------------------------------------------------------------------
async function api(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} for ${path}`);
  return r.json();
}

async function loadTaxon(id) {
  const node = state.cache.get(id);
  if (node) return node.taxon;
  const taxon = await api(`/api/taxon/${id}`);
  state.cache.set(id, { taxon, children: null });
  return taxon;
}

async function loadChildren(id) {
  let node = state.cache.get(id);
  if (!node) {
    await loadTaxon(id);
    node = state.cache.get(id);
  }
  if (node.children === null) {
    // In WoRMS view the tree walks the WoRMS hierarchy (worms_parent_id),
    // which is independent of CoL's parent_id. This lets Biota → Animalia
    // → Mollusca → ... drill through the marine tree even though those
    // CoL rows have parent_id pointing at Eukaryota, not Biota.
    // In Freshwater view the tree walks the freshwater overlay
    // (freshwater_parent_id); the freshwater rows are isolated, so the
    // CoL/WoRMS branches return empty for a freshwater taxon and vice
    // versa. Without `source=freshwater` here, clicking the freshwater
    // root fetches its CoL children (zero matches) and the tree looks
    // empty.
    let src = "";
    if (state.treeSource === "worms") src = "&source=worms";
    else if (state.treeSource === "freshwater") src = "&source=freshwater";
    let children = await api(`/api/taxon/${id}/children?limit=200${src}`);
    if (state.extantOnly) children = children.filter((t) => !t.is_extinct);
    node.children = children;
    for (const c of children) {
      if (!state.cache.has(c.id)) {
        state.cache.set(c.id, { taxon: c, children: null });
      }
    }
  }
  return node.children;
}

// ------------------------------------------------------------------
// Navigation: toggle expand/collapse, select a species
// ------------------------------------------------------------------
async function toggleExpand(id) {
  if (state.expanded.has(id)) {
    state.expanded.delete(id);
    render();
    return;
  }
  await loadChildren(id);
  state.expanded.add(id);
  // In WoRMS view, auto-unroll every tier of this node so the user sees
  // the full marine subtree on a single click — Biota → Animalia → phylum
  // → class → ... → species without hitting "Load N more" at every level.
  // CoL view keeps the PAGE_SIZE=5 default to stay snappy.
  if (state.treeSource === "worms") {
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

// ------------------------------------------------------------------
// Rendering
// ------------------------------------------------------------------

// Build a DOM element from a spec. Every string child flows through
// textContent (XSS-safe), every attribute goes through setAttribute.
function el(tag, props, ...children) {
  const node = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v == null || v === false) continue;
      if (k === "class" || k === "className") {
        node.className = v;
      } else if (k === "style" && typeof v === "string") {
        node.setAttribute("style", v);
      } else if (k.startsWith("on") && typeof v === "function") {
        node.addEventListener(k.slice(2).toLowerCase(), v);
      } else if (v === true) {
        node.setAttribute(k, "");
      } else {
        node.setAttribute(k, String(v));
      }
    }
  }
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    if (c instanceof Node) {
      node.appendChild(c);
    } else {
      node.appendChild(document.createTextNode(String(c)));
    }
  }
  return node;
}

// Center a tree row in the area BELOW the sticky detail card.
// scrollIntoView({block: "center"}) centers in the viewport, which puts
// the row halfway under the card when the card is sticky at the top.
// We measure the card's bottom edge in viewport coords and scroll so the
// row's center matches the vertical center of the remaining space.
function scrollTaxonBelowCard(el) {
  const main = document.querySelector("main");
  if (!main) return;
  const card = document.querySelector(".detail-card");
  // No visible card → fall back to plain centering in the viewport.
  if (!card || card.closest(".hidden") !== null) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  const cardRect = card.getBoundingClientRect();
  const cardBottom = cardRect.bottom;
  const visibleTreeHeight = window.innerHeight - cardBottom;
  // If the card covers everything, there is no visible tree area —
  // skip the scroll instead of producing a wild negative delta.
  if (visibleTreeHeight <= 0) return;
  const visibleTreeCenter = cardBottom + visibleTreeHeight / 2;
  const taxonRect = el.getBoundingClientRect();
  const taxonCenter = taxonRect.top + taxonRect.height / 2;
  // Use scrollTo with an absolute target. scrollBy is relative to the
  // current scrollTop, which the browser silently adjusts when content
  // is inserted above the visible area (the sticky card lands in flow
  // when first rendered, pushing the tree down). Absolute scrollTo
  // ignores that drift and lands exactly where we want.
  const targetScroll = main.scrollTop + (taxonCenter - visibleTreeCenter);
  main.scrollTo({ top: targetScroll, behavior: "auto" });
}

// Wait for loadDetail to finish so the detail card is at its final height
// before we calculate the scroll position. loadDetail fetches the three
// sub-endpoints in parallel and then re-renders the card. While the fetch
// is in flight the card shows "Loading details…" (~100px); once it lands
// the card is at its full size (~300–500px). Scrolling against the stub
// leaves the taxon too low once the real content paints in.
function waitForDetailReady(id) {
  return new Promise((resolve) => {
    const tick = () => {
      // If the user navigated away, give up.
      if (state.selected !== id) return resolve();
      // detail populated + card actually rendered with content (not just
      // the loading stub). Checking for two or more detail-item rows
      // ensures the panel has real data, not the loading placeholder.
      const card = document.querySelector(".detail-card");
      const ready =
        state.detail &&
        card &&
        card.querySelectorAll(".detail-item").length > 0;
      if (ready) resolve();
      else setTimeout(tick, 40);
    };
    tick();
  });
}

function rankLabel(rank) {
  return rank.charAt(0).toUpperCase() + rank.slice(1);
}

// Latin plurals for the few ranks that don't follow English +s.
// Most ranks pluralize the same as English; these don't.
const RANK_PLURAL = {
  domain: "domains",
  kingdom: "kingdoms",
  phylum: "phyla",
  class: "classes",
  family: "families",
  genus: "genera",
  species: "species",
  subspecies: "subspecies",
  variety: "varieties",
  // sub-ranks follow the same irregularity as their parent
  subphylum: "subphyla",
  subclass: "subclasses",
  subfamily: "subfamilies",
  subgenus: "subgenera",
  suborder: "suborders",
  subkingdom: "subkingdoms",
  subvariety: "subvarieties",
  // remaining ranks (order, tribe, etc.) fall back to English +s
};
function rankPlural(rank) {
  return RANK_PLURAL[rank] || rankLabel(rank) + "s";
}

function statusDot(status) {
  if (status === "accepted")
    return el("span", {
      class: "w-2 h-2 rounded-full bg-green-500",
      title: "Accepted",
    });
  if (status === "synonym")
    return el("span", {
      class: "w-2 h-2 rounded-full bg-amber-500",
      title: "Synonym",
    });
  return el("span", {
    class: "w-2 h-2 rounded-full bg-outline",
    title: "Unknown",
  });
}

function speciesCountBadge(n) {
  if (n === null || n === undefined) return "";
  if (n >= 1_000_000) {
    const m = (n / 1_000_000).toFixed(1).replace(/\.0$/, "");
    return `${m}M spp.`;
  }
  if (n >= 1_000) {
    const k = Math.round(n / 1_000);
    return `${k}k spp.`;
  }
  return `${n} spp.`;
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
  const cls = isSelected
    ? "bg-primary/5 border-l-[3px] border-primary rounded-r-lg cursor-pointer"
    : isFocused
      ? "bg-surface-container-low border-l-[3px] border-outline rounded-r-lg cursor-pointer"
      : "hover:bg-surface-container-low transition-colors rounded-r-lg cursor-pointer";
  const rankCls = isSelected
    ? "text-primary bg-primary/10"
    : isFocused
      ? "text-primary bg-primary/5"
      : "text-on-surface-variant bg-surface-container-highest";
  const nameCls = isSelected
    ? "font-h1 text-h1 text-primary font-bold"
    : isFocused
      ? "font-h1 text-h1 text-primary"
      : depth === 0
        ? "font-h1 text-h1 text-on-surface"
        : "font-body-lg text-body-lg text-on-surface";
  // For species, render a small marker (•) instead of the chevron so the row
  // doesn't look like it has children to expand.
  const chevron = hasChildren
    ? el(
        "span",
        { class: "material-symbols-outlined text-[20px]" },
        isExpanded ? "arrow_drop_down" : "chevron_right",
      )
    : el(
        "span",
        { class: "text-on-surface-variant text-[18px] select-none" },
        "•",
      );
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
      { class: `${nameCls} truncate ${extinctCls}` },
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

const RANK_ORDER = [
  "domain",
  "kingdom",
  "subkingdom",
  "phylum",
  "subphylum",
  "class",
  "subclass",
  "order",
  "suborder",
  "family",
  "subfamily",
  "genus",
  "subgenus",
  "species",
  "subspecies",
  "variety",
  "form",
];
const RANK_INDEX = new Map(RANK_ORDER.map((r, i) => [r, i]));

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
  frag.appendChild(
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
          frag.appendChild(
            renderTierHeader(taxon, filteredGroup, more, depth + 1),
          );
        }
        for (const child of visible) {
          frag.appendChild(renderNode(child, depth + 1));
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
  if (state.treeSource === "col") return !!taxon.coldp_id;
  if (state.treeSource === "worms") return !!taxon.worms_id;
  if (state.treeSource === "freshwater") return !!taxon.freshwater_id;
  return true;
}

function renderTree() {
  const view = document.getElementById("tree-view");
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
    wrapper.appendChild(renderNode(root, 0));
  }
  view.replaceChildren(wrapper);
}

function renderBreadcrumb() {
  const nav = document.getElementById("breadcrumb");
  if (!state.focused) {
    nav.replaceChildren();
    return;
  }
  // Walk up parent_id chain to build the path of the focused node.
  const pathSegments = [];
  let currentId = state.focused;
  let safety = 30; // hard cap to avoid infinite loops on data corruption
  while (currentId && safety-- > 0) {
    const node = state.cache.get(currentId);
    if (!node) break;
    pathSegments.unshift({
      id: currentId,
      name: node.taxon.scientific_name,
      rank: node.taxon.rank,
    });
    currentId = node.taxon.parent_id;
  }
  if (pathSegments.length === 0) {
    nav.replaceChildren();
    return;
  }

  const frag = document.createDocumentFragment();

  // Home icon (clickable — clears focus).
  frag.appendChild(
    el(
      "button",
      {
        class: "hover:text-primary transition-colors flex items-center gap-1",
        "data-action": "focus-home",
        title: "Clear focus (go to tree root)",
      },
      el("span", { class: "material-symbols-outlined text-[16px]" }, "home"),
    ),
  );
  // Each path segment: intermediate ones are clickable buttons; the last is
  // the current position (rendered as text, not clickable).
  for (let i = 0; i < pathSegments.length; i++) {
    const seg = pathSegments[i];
    frag.appendChild(
      el(
        "span",
        { class: "material-symbols-outlined text-[14px]" },
        "chevron_right",
      ),
    );
    if (i === pathSegments.length - 1) {
      frag.appendChild(
        el("span", { class: "text-on-surface font-medium" }, seg.name),
      );
    } else {
      frag.appendChild(
        el(
          "button",
          {
            class: "hover:text-primary transition-colors",
            "data-action": "focus-segment",
            "data-taxon-id": seg.id,
          },
          seg.name,
        ),
      );
    }
  }
  nav.replaceChildren(frag);
}

async function loadDetail(id) {
  state.detailLoading = true;
  try {
    const [vern, syn, dist] = await Promise.all([
      api(`/api/taxon/${id}/vernaculars?limit=200`),
      api(`/api/taxon/${id}/synonyms?limit=200`),
      api(`/api/taxon/${id}/distribution?limit=200`),
    ]);
    if (state.selected !== id) return; // user navigated away
    state.detail = { vernaculars: vern, synonyms: syn, distribution: dist };
  } catch (e) {
    console.error("detail load failed", e);
    state.detail = { vernaculars: [], synonyms: [], distribution: [] };
  } finally {
    state.detailLoading = false;
    render();
  }
}

function buildDetailSection(icon, title, count, items) {
  return el(
    "div",
    { class: "detail-section" },
    el(
      "h3",
      null,
      el("span", { class: "material-symbols-outlined text-[16px]" }, icon),
      ` ${title} `,
      el("span", { class: "count" }, String(count)),
    ),
    ...items,
  );
}

function renderDetailPanel() {
  const panel = document.getElementById("detail-panel");
  if (!state.detailOpen || !state.selected || !state.detail) {
    panel.classList.add("hidden");
    panel.replaceChildren();
    return;
  }
  const taxon = state.cache.get(state.selected)?.taxon;
  if (!taxon) return;
  const d = state.detail;
  const extinctCls = taxon.is_extinct ? "line-through opacity-70" : "";
  const hasVern = d.vernaculars.length > 0;
  const hasSyn = d.synonyms.length > 0;
  const hasDist = d.distribution.length > 0;
  const hasAny = hasVern || hasSyn || hasDist;
  if (!hasAny && !state.detailLoading) {
    panel.classList.add("hidden");
    panel.replaceChildren();
    return;
  }

  const card = el("div", { class: "detail-card" });

  // Header badges (rank, status, extinct).
  const badges = el(
    "div",
    { class: "flex items-center gap-3 mb-1 flex-wrap" },
    el(
      "span",
      {
        class:
          "rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded text-primary bg-primary/10",
      },
      rankLabel(taxon.rank),
    ),
    el(
      "span",
      {
        class:
          "rank-badge text-on-surface-variant bg-surface-container-highest uppercase tracking-[0.1em] px-2 py-0.5 rounded",
      },
      taxon.status,
    ),
  );
  if (taxon.is_extinct) {
    badges.appendChild(
      el(
        "span",
        {
          class:
            "rank-badge text-red-700 bg-red-50 uppercase tracking-[0.1em] px-2 py-0.5 rounded",
        },
        "† Extinct",
      ),
    );
  }
  // CoL source badge — only in CoL view for CoL-only taxa (no WoRMS match).
  // Mirrors the WoRMS badge symmetry: same outline weight, neutral gray so
  // it doesn't compete with the rank badge.
  if (state.treeSource === "col" && taxon.coldp_id && !taxon.worms_id) {
    badges.appendChild(
      el(
        "span",
        {
          class:
            "rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded text-on-surface-variant bg-surface-container-highest",
          title: `CoL-only — ColDP ID ${taxon.coldp_id} (no WoRMS match).`,
        },
        `CoL · ${taxon.coldp_id}`,
      ),
    );
  }
  // WoRMS enrichment link — only in WoRMS view (CoL stays clean) and
  // only when the taxon has a worms_id. Clickable badge that jumps
  // straight to the WoRMS taxon page.
  else if (taxon.worms_id && state.treeSource !== "col") {
    badges.appendChild(
      el(
        "a",
        {
          href: `https://www.marinespecies.org/aphia.php?p=taxdetails&id=${taxon.worms_id}`,
          target: "_blank",
          rel: "noopener noreferrer",
          class:
            "rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded text-accent bg-accent/10 hover:bg-accent/20 transition-colors no-underline",
          title: `WoRMS AphiaID ${taxon.worms_id} — open in WoRMS`,
        },
        `WoRMS · ${taxon.worms_id}`,
      ),
    );
  }

  const titleBlock = el(
    "div",
    { class: "flex-1 min-w-0" },
    badges,
    el(
      "h2",
      { class: `font-display text-display ${extinctCls}` },
      taxon.scientific_name,
    ),
  );
  if (taxon.authorship) {
    titleBlock.appendChild(
      el(
        "p",
        {
          class: "text-body-sm text-on-surface-variant mt-1",
        },
        taxon.authorship,
      ),
    );
  }

  card.appendChild(
    el(
      "div",
      { class: "detail-header" },
      titleBlock,
      el(
        "button",
        {
          class:
            "material-symbols-outlined text-on-surface-variant hover:text-on-surface p-1 rounded",
          "data-action": "close-detail",
          title: "Hide details",
        },
        "close",
      ),
    ),
  );

  if (state.detailLoading && !hasAny) {
    card.appendChild(
      el(
        "div",
        {
          class: "detail-section text-on-surface-variant text-body-sm",
        },
        "Loading details…",
      ),
    );
  }

  if (hasVern) {
    const items = d.vernaculars.map((v) => {
      const item = el("div", { class: "detail-item" });
      if (v.language)
        item.appendChild(el("span", { class: "lang" }, v.language));
      if (v.country)
        item.appendChild(el("span", { class: "country" }, v.country));
      item.appendChild(el("span", null, v.name));
      return item;
    });
    card.appendChild(
      buildDetailSection(
        "translate",
        "Vernacular names",
        d.vernaculars.length,
        items,
      ),
    );
  }

  if (hasSyn) {
    const items = d.synonyms.map((s) => {
      const item = el(
        "div",
        { class: "detail-item" },
        el("span", { class: "lang" }, s.rank),
        el("span", null, s.scientific_name),
      );
      if (s.authorship)
        item.appendChild(el("span", { class: "authorship" }, s.authorship));
      return item;
    });
    card.appendChild(
      buildDetailSection("history", "Synonyms", d.synonyms.length, items),
    );
  }

  if (hasDist) {
    const items = d.distribution.map((x) => {
      const means = x.establishment_means || "unknown";
      return el(
        "div",
        { class: "detail-item" },
        el("span", { class: `means means-${means}` }, means),
        el("span", null, x.area),
      );
    });
    card.appendChild(
      buildDetailSection(
        "public",
        "Distribution",
        d.distribution.length,
        items,
      ),
    );
  }

  panel.classList.remove("hidden");
  panel.replaceChildren(card);
}

function renderSearchDropdown() {
  const drop = document.getElementById("search-results");
  if (state.searchResults.length === 0) {
    drop.replaceChildren(
      el(
        "div",
        {
          class: "p-3 text-body-sm text-on-surface-variant",
        },
        "No matches.",
      ),
    );
    drop.classList.add("open");
    return;
  }
  const frag = document.createDocumentFragment();
  for (const h of state.searchResults) {
    const t = h.taxon;
    const row = el(
      "div",
      {
        class: "search-hit",
        "data-taxon-id": t.id,
        "data-action": "select-from-search",
      },
      el("span", { class: `tag tag-${h.match_type}` }, h.match_type),
      el(
        "span",
        {
          class:
            "rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded bg-surface-container-highest text-on-surface-variant",
        },
        rankLabel(t.rank),
      ),
      el(
        "span",
        {
          class: "font-body-md text-body-md text-on-surface truncate",
        },
        t.scientific_name,
      ),
    );
    if (t.authorship) {
      row.appendChild(
        el(
          "span",
          {
            class: "text-body-sm text-on-surface-variant truncate",
          },
          t.authorship,
        ),
      );
    }
    frag.appendChild(row);
  }
  drop.replaceChildren(frag);
  drop.classList.add("open");
}

function closeSearch() {
  state.searchResults = [];
  state.searchOpen = false;
  document.getElementById("search-results").classList.remove("open");
}

function render() {
  renderTree();
  renderBreadcrumb();
  renderCollapseAllButton();
  renderDetailPanel();
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
// Search
// ------------------------------------------------------------------
async function runSearch(q) {
  state.searchQuery = q;
  if (!q || q.length < 2) {
    closeSearch();
    return;
  }
  try {
    const results = await api(
      `/api/search?q=${encodeURIComponent(q)}&limit=15`,
    );
    state.searchResults = results;
    renderSearchDropdown();
  } catch (e) {
    console.error("search failed", e);
  }
}

// ------------------------------------------------------------------
// Event delegation
// ------------------------------------------------------------------
document.addEventListener("click", (e) => {
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
  } else if (action === "select-from-search") {
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    closeSearch();
    // IIFE so we can await expandAncestorsOf before scrolling — the
    // click handler itself is sync, and without await the row isn't in
    // the DOM yet when scrollIntoView runs.
    (async () => {
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
    })();
  } else if (action === "focus-segment") {
    const id = parseInt(
      e.target.closest("[data-taxon-id]").dataset.taxonId,
      10,
    );
    state.focused = id;
    render();
    // After render, bring the focused node into view, centered in the
    // area below the sticky card.
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
      if (state.treeSource === "worms") {
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

// Search input
document.getElementById("search-input").addEventListener("input", (e) => {
  clearTimeout(state.searchTimer);
  const q = e.target.value.trim();
  state.searchTimer = setTimeout(() => runSearch(q), 200);
});
document.getElementById("search-input").addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    e.target.value = "";
    closeSearch();
    e.target.blur();
  }
});
document.getElementById("search-input").addEventListener("focus", (e) => {
  if (e.target.value.trim().length >= 2) runSearch(e.target.value.trim());
});

// Browser back/forward: restore the selected species from the URL hash.
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

// Collapse-all: clear every expanded node + every "load all" group.
function collapseAll() {
  if (state.expanded.size === 0 && state.showAll.size === 0) return;
  state.expanded.clear();
  state.showAll.clear();
  render();
}

// Collapse all button
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

// ------------------------------------------------------------------
// Boot
// ------------------------------------------------------------------
async function boot() {
  // Health check (best-effort; doesn't block render).
  try {
    const h = await api("/api/health");
    document.getElementById("footer-status").textContent =
      `System Online · ${h.taxa.toLocaleString()} taxa · ${h.vernaculars.toLocaleString()} vernaculars`;
  } catch {
    document.getElementById("footer-status").textContent = "API unreachable";
    document
      .getElementById("footer-status")
      .previousElementSibling.classList.remove("bg-green-500");
    document
      .getElementById("footer-status")
      .previousElementSibling.classList.add("bg-red-500");
  }

  // Load the 4 domains as roots.
  const roots = await api("/api/domains");
  for (const r of roots) {
    state.cache.set(r.id, { taxon: r, children: null });
  }
  state.roots = roots;

  // If freshwater is loaded, append a "Freshwater" toggle button. The
  // event delegation set up at module-load handles its click.
  if (roots.some((r) => r.freshwater_id != null)) {
    const toggle = document.getElementById("tree-source-toggle");
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
      toggle.appendChild(freshBtn);
    }
  }

  // Pre-expand Eukaryota (most populous) for a useful initial view.
  const euk = roots.find((r) => r.scientific_name === "Eukaryota");
  if (euk) {
    await loadChildren(euk.id);
    state.expanded.add(euk.id);
  }

  // If the URL has a hash, select that species and focus its path.
  const hashId = parseInt(location.hash.replace("#", ""), 10);
  if (hashId && Number.isFinite(hashId)) {
    await expandAncestorsOf(hashId);
    state.focused = hashId;
    selectTaxon(hashId, { updateUrl: "replace" });
  } else {
    // Initial focus: Eukaryota (so the breadcrumb shows "home > Eukaryota"
    // from the start, not empty).
    state.focused = euk ? euk.id : null;
  }

  render();
}

render();
boot();
