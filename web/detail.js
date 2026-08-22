// Detail panel: loads vernaculars/synonyms/distribution/searches from the
// API, renders the card with its 4 tabs (Búsquedas / Vernáculares /
// Sinónimos / Distribución), and persists per-taxon tab memory so
// reopening the same taxon remembers which tab was active. The detail
// panel is the single place that calls loadDetail — the [data-tab] click
// handler lives in nav.js (alongside the other delegated actions).

import { state } from "./state.js";
import { api, loadTaxon } from "./api.js";
import { rankLabel } from "./format.js";
import { el } from "./dom.js";
import { SEARCH_ENGINES } from "./search_urls.js";

async function loadDetail(id) {
  state.detailLoading = true;
  try {
    // The searches endpoint returns 422 when scientific_name is empty;
    // mirror that guard client-side so we never trigger an avoidable
    // error response.
    const taxon = state.cache.get(id)?.taxon ?? (await loadTaxon(id));
    const [vern, syn, dist, searches] = await Promise.all([
      api(`/api/taxon/${id}/vernaculars?limit=200`),
      api(`/api/taxon/${id}/synonyms?limit=200`),
      api(`/api/taxon/${id}/distribution?limit=200`),
      taxon.scientific_name
        ? api(`/api/taxon/${id}/searches`)
        : Promise.resolve([]),
    ]);
    if (state.selected !== id) return; // user navigated away
    state.detail = {
      vernaculars: vern,
      synonyms: syn,
      distribution: dist,
      searches,
    };
  } catch (e) {
    console.error("detail load failed", e);
    state.detail = {
      vernaculars: [],
      synonyms: [],
      distribution: [],
      searches: [],
    };
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

// Render the Búsquedas tab: a grid of 14 search-engine buttons, each
// opening in a new tab. The URLs come pre-composed from the server
// (urllib.parse.quote_plus); the icon glyph + label come from the local
// SEARCH_ENGINES table as a fallback (offline / 5xx case). The server
// response is the source of truth for the URL itself.
//
// Layout: 14 button-like cards in a CSS grid (auto-fill, 120px min).
// Each card has the engine icon on top and the label underneath so the
// user can scan all 14 at a glance. No arrow suffix — the icon
// communicates "open in new tab" via the standard browser link
// behaviour (target="_blank" on the <a>).
function renderSearchesTab(searches) {
  if (!searches || searches.length === 0) {
    return el(
      "div",
      {
        class: "text-body-sm text-on-surface-variant px-2 py-4 text-center",
      },
      "No search links available for this taxon.",
    );
  }
  const items = searches.map((s) => {
    const engine = SEARCH_ENGINES.find((e) => e.key === s.engine);
    const icon = engine ? engine.icon : "search";
    return el(
      "a",
      {
        href: s.url,
        target: "_blank",
        rel: "noopener",
        class: "search-engine-btn",
        title: `Open ${s.label} search for this taxon in a new tab`,
      },
      el("span", { class: "material-symbols-outlined" }, icon),
      el("span", null, s.label),
    );
  });
  return el("div", { class: "search-engines-grid" }, ...items);
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
  const hasSearches = d.searches.length > 0;
  const hasVern = d.vernaculars.length > 0;
  const hasSyn = d.synonyms.length > 0;
  const hasDist = d.distribution.length > 0;
  const hasAny = hasSearches || hasVern || hasSyn || hasDist;
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

  // ----- Tab strip ----------------------------------------------------
  // Tabs in this order: Búsquedas first, then Vernáculares, Sinónimos,
  // Distribución. Each non-Búsquedas tab is conditional on its data
  // being non-empty (matches today's "hide empty sections" behaviour).
  // Búsquedas is always shown when the panel renders so the per-row
  // search icon always has a target.
  const tabs = [];
  tabs.push({ key: "busquedas", label: "Búsquedas", icon: "travel_explore" });
  if (hasVern)
    tabs.push({ key: "vernaculars", label: "Vernáculares", icon: "translate" });
  if (hasSyn)
    tabs.push({ key: "synonyms", label: "Sinónimos", icon: "history" });
  if (hasDist)
    tabs.push({ key: "distribution", label: "Distribución", icon: "public" });

  // Decide the active tab. Per-taxon memory wins; otherwise default to
  // Búsquedas (the new spec'd default) and fall back to the first
  // available tab when Búsquedas isn't visible (e.g., empty name).
  const taxonId = state.selected;
  const remembered = state.activeTab[taxonId];
  const activeKey = tabs.some((t) => t.key === remembered)
    ? remembered
    : tabs[0].key;
  // Belt-and-braces: if for some reason tabs[0] is missing (empty
  // tabs array — can't happen given Búsquedas is always pushed, but
  // keep the guard), hide the panel.
  if (!activeKey) {
    panel.classList.add("hidden");
    panel.replaceChildren();
    return;
  }
  state.activeTab[taxonId] = activeKey;

  // Tab strip — horizontal flex row of buttons. Click handler lives in
  // the global delegation block; here we just stamp data-tab on each
  // button. The active tab's button gets .active for the colored
  // underline + primary text color.
  const tabStrip = el(
    "div",
    { class: "detail-tabs" },
    ...tabs.map((t) =>
      el(
        "button",
        {
          type: "button",
          class: `detail-tab ${t.key === activeKey ? "active" : ""}`.trim(),
          "data-tab": t.key,
          "aria-pressed": t.key === activeKey ? "true" : "false",
          role: "tab",
        },
        el("span", { class: "material-symbols-outlined text-[16px]" }, t.icon),
        t.label,
      ),
    ),
  );
  card.appendChild(tabStrip);

  // ----- Tab content --------------------------------------------------
  // Each section is wrapped in a div with data-tab-content="<key>".
  // Non-active sections are hidden via inline display:none — switching
  // tabs is O(1) (just toggles a class on the strip and a style on the
  // sections), no re-fetch.
  const sections = [];
  sections.push({
    key: "busquedas",
    node: el(
      "div",
      { class: "detail-section", "data-tab-content": "busquedas" },
      renderSearchesTab(d.searches),
    ),
  });

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
    sections.push({
      key: "vernaculars",
      node: buildDetailSection(
        "translate",
        "Vernacular names",
        d.vernaculars.length,
        items,
      ),
    });
    sections[sections.length - 1].node.setAttribute(
      "data-tab-content",
      "vernaculars",
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
    sections.push({
      key: "synonyms",
      node: buildDetailSection("history", "Synonyms", d.synonyms.length, items),
    });
    sections[sections.length - 1].node.setAttribute(
      "data-tab-content",
      "synonyms",
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
    sections.push({
      key: "distribution",
      node: buildDetailSection(
        "public",
        "Distribution",
        d.distribution.length,
        items,
      ),
    });
    sections[sections.length - 1].node.setAttribute(
      "data-tab-content",
      "distribution",
    );
  }
  for (const s of sections) {
    if (s.key !== activeKey) {
      s.node.setAttribute("style", "display: none;");
    }
    card.appendChild(s.node);
  }

  panel.classList.remove("hidden");
  panel.replaceChildren(card);
}

export { loadDetail, buildDetailSection, renderSearchesTab, renderDetailPanel };

// Note: `render()` is imported via a circular reference from app.js. It's
// only used inside loadDetail's catch/finally block (runtime), not at
// module init — ES module live bindings resolve correctly in this case.
import { render } from "./app.js";
