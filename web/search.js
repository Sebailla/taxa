// Search: dropdown rendering, debounced input handler, and the search
// input event wiring. The dropdown is rendered into #search-results by
// runSearch() after the API responds; closeSearch() empties it.

import { state } from "./state.js";
import { api } from "./api.js";
import { rankLabel } from "./format.js";
import { el } from "./dom.js";

function renderSearchDropdown() {
  const drop = document.querySelector("#search-results");
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
      row.append(
        el(
          "span",
          {
            class: "text-body-sm text-on-surface-variant truncate",
          },
          t.authorship,
        ),
      );
    }
    frag.append(row);
  }
  drop.replaceChildren(frag);
  drop.classList.add("open");
}

function closeSearch() {
  state.searchResults = [];
  state.searchOpen = false;
  document.querySelector("#search-results").classList.remove("open");
}

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

// Search input — debounced typing handler + Escape-to-clear + refocus re-run.
// Wired at module-init because #search-input exists in the static HTML that
// loads this module via app.js.
document.querySelector("#search-input").addEventListener("input", (e) => {
  clearTimeout(state.searchTimer);
  const q = e.target.value.trim();
  state.searchTimer = setTimeout(() => runSearch(q), 200);
});
document.querySelector("#search-input").addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    e.target.value = "";
    closeSearch();
    e.target.blur();
  }
});
document.querySelector("#search-input").addEventListener("focus", (e) => {
  if (e.target.value.trim().length >= 2) runSearch(e.target.value.trim());
});

export { runSearch, renderSearchDropdown, closeSearch };
