// Detail panel: loads vernaculars/synonyms/distribution/searches from the
// API, renders the card with its 4 tabs (Search / Vernaculars /
// Synonyms / Distribution), and persists per-taxon tab memory so
// reopening the same taxon remembers which tab was active. The detail
// panel is the single place that calls loadDetail — the [data-tab] click
// handler lives in nav.js (alongside the other delegated actions).

import { state } from "./state.js";
import {
  api,
  loadTaxon,
  previewMaterialize,
  materializeResearch,
} from "./api.js";
import {
  rankLabel,
  scientificNameClass,
  statusDot,
  speciesCountBadge,
} from "./format.js";
import { el, showToast } from "./dom.js";
import { propagateMaterialized } from "./tree.js";
import { SEARCH_ENGINES, CATEGORIES } from "./search_urls.js";

async function loadDetail(id) {
  state.detailLoading = true;
  try {
    // The searches endpoint returns 422 when scientific_name is empty;
    // mirror that guard client-side so we never trigger an avoidable
    // error response.
    const taxon = state.cache.get(id)?.taxon ?? (await loadTaxon(id));
    // The materialize-preview is fetched in parallel with the rest so
    // the Folder tab is ready when the panel renders. A failure here
    // is non-fatal — the tab shows an inline error and the rest of
    // the panel still works. Always fetched (no scientific_name
    // guard) because the preview endpoint handles empty names via
    // the id-{taxon_id} fallback.
    const [vern, syn, dist, searches, preview] = await Promise.all([
      api(`/api/taxon/${id}/vernaculars?limit=200`),
      api(`/api/taxon/${id}/synonyms?limit=200`),
      api(`/api/taxon/${id}/distribution?limit=200`),
      taxon.scientific_name
        ? api(`/api/taxon/${id}/searches`)
        : Promise.resolve([]),
      previewMaterialize(id, state.treeSource).catch((e) => ({ error: e.message })),
    ]);
    if (state.selected !== id) return; // user navigated away
    state.detail = {
      vernaculars: vern,
      synonyms: syn,
      distribution: dist,
      searches,
      materializePreview: preview,
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

// Render the Overview section content — a self-contained summary of
// the taxon's essential metadata (rank badge + scientific name +
// status + authorship + species count + parent chain). P1 #1 from
// the Impeccable critique: the detail panel used to be search-grid-
// first even for top-level taxa, which is pedagogically empty. This
// section is rendered BEFORE the tab strip when the selected taxon
// has empty vernaculars + synonyms + distribution data. When any
// of those three has data, the Overview is suppressed entirely so
// the data tabs can take the stage.
//
// Source-aware parent chain — mirrors breadcrumb.js. CoL walks
// parent_id; WoRMS walks worms_parent_id; Freshwater walks
// freshwater_parent_id. The chain shows the focused taxon + all
// ancestors up to the root, each segment clickable via
// data-action="focus-segment" (the same handler the breadcrumb
// uses, already wired in nav.js). The chain row is hidden when
// there's only one segment (no ancestors) — the title already
// shows the taxon's own name.
function renderOverview(taxon) {
  const src = state.treeSource;
  const parentIdOf = (t) => {
    if (src === "worms") return t.worms_parent_id;
    if (src === "freshwater") return t.freshwater_parent_id;
    return t.parent_id;
  };
  // Walk from the selected taxon up to the root, unshift so the
  // final array goes root → ... → focused (matches the breadcrumb
  // order). 30-step safety cap mirrors breadcrumb.js; data
  // corruption could otherwise spin forever.
  const segments = [];
  let currentId = state.selected;
  let safety = 30;
  while (currentId && safety-- > 0) {
    const node = state.cache.get(currentId);
    if (!node) break;
    segments.unshift({
      id: currentId,
      name: node.taxon.scientific_name,
      rank: node.taxon.rank,
    });
    currentId = parentIdOf(node.taxon);
  }

  // Build each key:value row. The label sits in a fixed-width left
  // column; the value sits in the right. CSS grid handles the
  // alignment so labels stay flush.
  const grid = el("dl", { class: "overview-grid" });

  // Scientific name — italic via the .scientific-name class added
  // in 878cc4b (mirrors how the tree rows + breadcrumb render Latin
  // binomials). scientificNameClass() picks italic for genus +
  // below and roman for higher ranks per ICZN convention.
  grid.append(
    el(
      "div",
      { class: "overview-row" },
      el("dt", { class: "overview-label" }, "Scientific name:"),
      el(
        "dd",
        {
          class: `overview-value font-display text-display ${scientificNameClass(taxon.rank)}`,
        },
        taxon.scientific_name,
      ),
    ),
  );

  // Status — colored dot + text label. statusDot() returns the
  // span; the label maps the raw status string to a friendlier
  // capitalized form (Accepted / Synonym / Unknown).
  const statusText =
    taxon.status === "accepted"
      ? "Accepted"
      : taxon.status === "synonym"
        ? "Synonym"
        : "Unknown";
  grid.append(
    el(
      "div",
      { class: "overview-row" },
      el("dt", { class: "overview-label" }, "Status:"),
      el(
        "dd",
        { class: "overview-value inline-flex items-center gap-2" },
        statusDot(taxon.status),
        statusText,
      ),
    ),
  );

  // Authorship — only render the row when the field has content.
  // An empty/null authorship is suppressed entirely (no "—"
  // placeholder) so the Overview isn't padded with meaningless
  // rows. Wrapped in parens to match the convention used elsewhere
  // in the panel (see the title block's authorship line).
  if (taxon.authorship) {
    grid.append(
      el(
        "div",
        { class: "overview-row" },
        el("dt", { class: "overview-label" }, "Authorship:"),
        el(
          "dd",
          { class: "overview-value text-on-surface-variant" },
          `(${taxon.authorship})`,
        ),
      ),
    );
  }

  // Species count — reuse speciesCountBadge so the formatting
  // (1.2k / 3.4M / 763 / etc.) stays consistent with the tree rows.
  // null/undefined renders as an em dash so the row is preserved
  // (the spec asks for "—", not row suppression) — preserves the
  // visual rhythm of the Overview.
  const sc = taxon.species_count;
  grid.append(
    el(
      "div",
      { class: "overview-row" },
      el("dt", { class: "overview-label" }, "Species count:"),
      el(
        "dd",
        { class: "overview-value" },
        sc === null || sc === undefined ? "—" : speciesCountBadge(sc),
      ),
    ),
  );

  // Parent chain — skip when there's only one segment (no
  // ancestors). The focused taxon's own name is already shown by
  // the "Scientific name:" row above, so a one-segment chain would
  // just duplicate it.
  if (segments.length > 1) {
    // Each segment is a clickable button — the same
    // data-action="focus-segment" + data-taxon-id shape the
    // breadcrumb uses, so the existing nav.js handler picks it up.
    // Italic/roman styling follows scientificNameClass per rank.
    // Chevron separators sit BETWEEN segments (not after the
    // last) — same pattern as the breadcrumb.
    const segEls = [];
    segments.forEach((s, i) => {
      segEls.push(
        el(
          "button",
          {
            type: "button",
            class: `overview-chain-segment ${scientificNameClass(s.rank)}`,
            "data-action": "focus-segment",
            "data-taxon-id": s.id,
          },
          s.name,
        ),
      );
      if (i < segments.length - 1) {
        segEls.push(
          el(
            "span",
            {
              class:
                "material-symbols-outlined text-[14px] text-on-surface-variant",
            },
            "chevron_right",
          ),
        );
      }
    });
    grid.append(
      el(
        "div",
        { class: "overview-row" },
        el("dt", { class: "overview-label" }, "Parent chain:"),
        el("dd", { class: "overview-value overview-chain" }, ...segEls),
      ),
    );
  }

  // Section wrapper — .detail-section gives the padding + bottom
  // border that all other sections share. .overview-section adds
  // the rank-badge row at the top.
  const extinctCls = taxon.is_extinct ? "line-through opacity-70" : "";
  return el(
    "div",
    { class: `detail-section overview-section ${extinctCls}`.trim() },
    // h3 mirrors the section heading pattern used by
    // buildDetailSection() for consistency.
    el(
      "h3",
      null,
      el("span", { class: "material-symbols-outlined text-[16px]" }, "info"),
      " Overview",
    ),
    // Rank badge — visual anchor at the top of the section.
    // Reuses the existing rank-badge styling from the title block
    // so the badge looks identical when seen in the header vs.
    // inside the Overview.
    el(
      "div",
      { class: "overview-rank" },
      el(
        "span",
        {
          class:
            "rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded text-primary bg-primary/10",
        },
        rankLabel(taxon.rank),
      ),
    ),
    grid,
  );
}

// Render the Search tab: a grid of 14 search-engine buttons, each
// opening in a new tab. The URLs come pre-composed from the server
// (urllib.parse.quote_plus); the icon glyph + label come from the local
// SEARCH_ENGINES table as a fallback (offline / 5xx case). The server
// response is the source of truth for the URL itself.
//
// Layout (P1 #3): engines are grouped by category so first-time users
// can tell which engines target taxonomic literature vs. general web.
// Categories render as full-width section headers inside the same
// single CSS grid (.search-engines-grid remains display:grid; the
// headers use grid-column: 1 / -1 to span every column so each
// category's buttons flow into the next row). Order: CATEGORIES order
// drives section order; within a section, engines keep their order
// from SEARCH_ENGINES. Categories without engines in the response are
// skipped silently (defensive — the server always returns all 14).
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
  // Build a {key: engine} lookup once so the inner loop is O(1).
  const engineByKey = new Map(SEARCH_ENGINES.map((e) => [e.key, e]));
  // Index the response by engine key — the server may not return all
  // 14, and the client never knows which keys map to which response
  // entries (the server is the source of truth for URLs).
  const children = [];
  for (const cat of CATEGORIES) {
    let emittedHeader = false;
    for (const e of SEARCH_ENGINES) {
      if (e.category !== cat.key) continue;
      const s = searches.find((row) => row.engine === e.key);
      if (!s) continue;
      if (!emittedHeader) {
        children.push(
          el(
            "div",
            {
              class: "search-category-header",
              "data-category": cat.key,
            },
            el("span", { class: "material-symbols-outlined" }, cat.icon),
            el("span", null, cat.label),
          ),
        );
        emittedHeader = true;
      }
      const meta = engineByKey.get(s.engine);
      const icon = meta ? meta.icon : "search";
      children.push(
        el(
          "a",
          {
            href: s.url,
            target: "_blank",
            rel: "noopener",
            class: "search-engine-btn",
            "data-engine-key": s.engine,
            "data-category": cat.key,
            title: `Open ${s.label} search for this taxon in a new tab`,
          },
          el("span", { class: "material-symbols-outlined" }, icon),
          el("span", null, s.label),
        ),
      );
    }
  }
  return el("div", { class: "search-engines-grid" }, ...children);
}

// Render the Folder tab content — the line-by-line preview of the
// root→taxon folder chain under ./Research, plus the count summary,
// the info banner (when the path is fully materialized), and the
// [Create N folders] action button (when something new would be
// created). Reused CSS classes from the previous standalone modal
// (.materialize-modal-list, .materialize-modal-marker, etc.) so the
// visual language stays consistent.
function renderFolderTab(taxon) {
  const preview = state.detail?.materializePreview;

  // Loading state — the preview fetch is in flight alongside the
  // other detail data; this branch is hit on the first render of
  // the tab before the Promise.all resolves.
  if (!preview) {
    return el(
      "div",
      { class: "materialize-tab-loading" },
      el(
        "span",
        { class: "material-symbols-outlined text-[20px] animate-spin" },
        "progress_activity",
      ),
      el("span", null, "Loading preview…"),
    );
  }

  // Error state — the preview fetch failed (network, 5xx, etc.).
  if (preview.error) {
    return el(
      "div",
      { class: "materialize-tab-error" },
      el("span", { class: "material-symbols-outlined text-[20px]" }, "error"),
      el("span", null, `Could not load the preview: ${preview.error}`),
    );
  }

  // Line-by-line preview list.
  const list = el("ul", { class: "materialize-modal-list" });
  let acc = preview.research_dir;
  for (const seg of preview.segments) {
    acc = `${acc}/${seg.name}`;
    const marker = seg.exists ? "✓" : "+";
    const markerCls = seg.exists
      ? "materialize-modal-marker-exists"
      : "materialize-modal-marker-new";
    list.append(
      el(
        "li",
        { class: "materialize-modal-list-item" },
        el("span", { class: `materialize-modal-marker ${markerCls}` }, marker),
        el("span", { class: "materialize-modal-segment-path" }, acc),
      ),
    );
  }

  const counts = el(
    "div",
    { class: "materialize-modal-counts" },
    `${preview.new_count} ${preview.new_count === 1 ? "new folder" : "new folders"} · ${preview.existing_count} already existed`,
  );

  const infoBanner = preview.all_exist
    ? el(
        "div",
        { class: "materialize-modal-info-banner" },
        el(
          "span",
          { class: "material-symbols-outlined text-[20px]" },
          "check_circle",
        ),
        el("span", null, "Path already exists on disk."),
      )
    : null;

  // The create button only shows when there's something new to
  // create. In the all-exist state, the tab is read-only.
  let createBtn = null;
  if (!preview.all_exist) {
    const label = `Create ${preview.new_count} ${preview.new_count === 1 ? "folder" : "folders"}`;
    const btn = el(
      "button",
      {
        class: "materialize-modal-btn materialize-modal-btn-primary",
        type: "button",
      },
      label,
    );
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = "Creating…";
      try {
const response = await materializeResearch(taxon.id, state.treeSource);
        state.materialized.add(taxon.id);
        propagateMaterialized(taxon.id);
        const newPreview = await previewMaterialize(taxon.id, state.treeSource).catch((e) => ({
          error: e.message,
        }));
        if (state.selected === taxon.id && state.detail) {
          state.detail.materializePreview = newPreview;
          render();
        }
        showToast(
          `Folders materialized: ${response.relative_path} ` +
            `(${response.folders_created} new, ${response.folders_existed} already existed)`,
        );
      } catch (err) {
        btn.disabled = false;
        btn.textContent = label;
        showToast(`Error materializing: ${err.message}`, { error: true });
      }
    });
    createBtn = btn;
  }

  return el(
    "div",
    { class: "materialize-tab-content" },
    el(
      "div",
      { class: "materialize-modal-preview-wrap" },
      el("div", { class: "materialize-modal-section-title" }, "Path preview:"),
      list,
    ),
    counts,
    infoBanner,
    createBtn,
  );
}

function renderDetailPanel() {
  const panel = document.querySelector("#detail-panel");
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
    badges.append(
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
    badges.append(
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
    badges.append(
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
      {
        class: `font-display text-display ${extinctCls} ${scientificNameClass(taxon.rank)}`,
      },
      taxon.scientific_name,
    ),
  );
  if (taxon.authorship) {
    titleBlock.append(
      el(
        "p",
        {
          class: "text-body-sm text-on-surface-variant mt-1",
        },
        taxon.authorship,
      ),
    );
  }

  card.append(
    el(
      "div",
      { class: "detail-header" },
      titleBlock,
      el(
        "button",
        {
          id: "close-detail",
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
    card.append(
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
  // Tabs in this order: Overview (when applicable), then Search,
  // then Folder, then Vernaculars, Synonyms, Distribution. The
  // Overview tab only renders when vernaculars + synonyms +
  // distribution are ALL empty (P1 #1 from the Impeccable critique)
  // — when ANY of those three has data, the Overview is suppressed
  // so the data tabs can take the stage. Search + Folder are always
  // shown so the per-row search / folder icons always have a
  // target.
  const hasOverview = !hasVern && !hasSyn && !hasDist;
  const tabs = [];
  if (hasOverview)
    tabs.push({ key: "overview", label: "Overview", icon: "info" });
  tabs.push({ key: "searches", label: "Search", icon: "travel_explore" });
  // Folder is always present (unlike Vernaculars / Synonyms /
  // Distribution which are conditional on having data). The tab
  // shows the materialize preview; in the all_exist state it's a
  // read-only "path is already on disk" view.
  tabs.push({ key: "folder", label: "Folder", icon: "create_new_folder" });
  if (hasVern)
    tabs.push({ key: "vernaculars", label: "Vernaculars", icon: "translate" });
  if (hasSyn)
    tabs.push({ key: "synonyms", label: "Synonyms", icon: "history" });
  if (hasDist)
    tabs.push({ key: "distribution", label: "Distribution", icon: "public" });

  // Decide the active tab. Per-taxon memory wins; otherwise the
  // default is:
  //   - "overview" when the Overview tab is present (i.e. when
  //     vernaculars + synonyms + distribution are all empty) — the
  //     user just clicked a top-level taxon and Overview teaches
  //     them what it is (P1 #1).
  //   - first available tab otherwise (Search for taxa with data,
  //     Folder for taxa with empty scientific_name where Search
  //     isn't rendered).
  const taxonId = state.selected;
  const remembered = state.activeTab[taxonId];
  const defaultKey = hasOverview ? "overview" : tabs[0].key;
  const activeKey = tabs.some((t) => t.key === remembered)
    ? remembered
    : defaultKey;
  // Belt-and-braces: if for some reason tabs[0] is missing (empty
  // tabs array — can't happen given Search is always pushed, but
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
  card.append(tabStrip);

  // ----- Tab content --------------------------------------------------
  // Each section is wrapped in a div with data-tab-content="<key>".
  // Non-active sections are hidden via inline display:none — switching
  // tabs is O(1) (just toggles a class on the strip and a style on the
  // sections), no re-fetch.
  const sections = [];
  // Overview section — only included when hasOverview is true
  // (vernaculars + synonyms + distribution all empty). The Overview
  // section reuses the .detail-section class so it shares the
  // padding/border treatment with the data tabs.
  if (hasOverview) {
    sections.push({
      key: "overview",
      node: el(
        "div",
        { class: "detail-section", "data-tab-content": "overview" },
        renderOverview(taxon),
      ),
    });
  }
  sections.push({
    key: "searches",
    node: el(
      "div",
      { class: "detail-section", "data-tab-content": "searches" },
      renderSearchesTab(d.searches),
    ),
  });
  sections.push({
    key: "folder",
    node: el(
      "div",
      { class: "detail-section", "data-tab-content": "folder" },
      // Defensive try/catch: a malformed preview should not prevent
      // the rest of the detail panel from rendering.
      (() => {
        try {
          return renderFolderTab(taxon);
        } catch (e) {
          console.error("Folder tab render failed", e);
          return el(
            "div",
            { class: "materialize-tab-error" },
            el(
              "span",
              { class: "material-symbols-outlined text-[20px]" },
              "error",
            ),
            el("span", null, `Could not render the Folder tab: ${e.message}`),
          );
        }
      })(),
    ),
  });

  if (hasVern) {
    const items = d.vernaculars.map((v) => {
      const item = el("div", { class: "detail-item" });
      if (v.language) item.append(el("span", { class: "lang" }, v.language));
      if (v.country) item.append(el("span", { class: "country" }, v.country));
      item.append(el("span", null, v.name));
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
    sections.at(-1).node.setAttribute("data-tab-content", "vernaculars");
  }

  if (hasSyn) {
    const items = d.synonyms.map((s) => {
      const item = el(
        "div",
        { class: "detail-item" },
        el("span", { class: "lang" }, s.rank),
        el("span", { class: scientificNameClass(s.rank) }, s.scientific_name),
      );
      if (s.authorship)
        item.append(el("span", { class: "authorship" }, s.authorship));
      return item;
    });
    sections.push({
      key: "synonyms",
      node: buildDetailSection("history", "Synonyms", d.synonyms.length, items),
    });
    sections.at(-1).node.setAttribute("data-tab-content", "synonyms");
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
    sections.at(-1).node.setAttribute("data-tab-content", "distribution");
  }
  for (const s of sections) {
    if (s.key !== activeKey) {
      s.node.setAttribute("style", "display: none;");
    }
    card.append(s.node);
  }

  panel.classList.remove("hidden");
  panel.replaceChildren(card);
}

export { loadDetail, buildDetailSection, renderSearchesTab, renderDetailPanel };

// Note: `render()` is imported via a circular reference from app.js. It's
// only used inside loadDetail's catch/finally block (runtime), not at
// module init — ES module live bindings resolve correctly in this case.
import { render } from "./app.js";
