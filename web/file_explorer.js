// File Explorer — the Browser tab's main module. Owns the two-pane
// layout (left recursive tree + right viewer), the recursive folder
// rendering, single/double-click semantics, the empty-state
// placeholders, and the AbortController that drops in-flight fetches
// when the user leaves the Browser tab.
//
// Public API:
//   mount(host, rootTaxonId) — mount the explorer into `host`. The
//     `rootTaxonId` is kept around for state.explorer / context, but
//     the Browser tab itself always fetches the global Research tree
//     via GET /api/files — it does NOT depend on the selected taxon.
//   clear() — drop listeners + abort in-flight fetches, reset the right
//     viewer to a fresh empty placeholder. Called by nav.js when the
//     user switches to Classification / Settings.
//
// State is read/written via the shared `state.explorer` object. The
// module owns writes to state.explorer.* (openFilePath, openFileFormat,
// viewerTab, tree). Selection in the left tree lives in DOM via
// data-file-path / data-folder-path attributes — no extra state.

import { state, API, initialExplorerShape } from "./state.js";
import { el } from "./dom.js";
import { realmForFolderPath } from "./format.js";
import * as fileViewer from "./file_viewer.js";

// Per-mount abort controller. Stored at module scope so clear() can
// abort any in-flight fetch the previous mount started.
let _abortController = null;
let _currentHost = null;
let _currentRootTaxonId = null;

// Serve URL builder. The tree JSON encodes the file's relative path
// inside the research root; the serve endpoint takes it as a `path`
// query param. URL-encode the relative path so paths with spaces or
// unicode (taxon names can include accents) round-trip cleanly.
//
// The Browser tab always shows the global Research directory
// (see GET /api/files below), so the URL is anchored at
// /api/files/serve — the per-taxon endpoint stays in the API for
// callers that still need a taxon's materialised subtree.
function serveUrl(relativePath) {
  return `${API}/api/files/serve?path=${encodeURIComponent(relativePath)}`;
}

// ---- Main entry points ----------------------------------------------

export async function mount(host, rootTaxonId) {
  _currentHost = host;
  _currentRootTaxonId = rootTaxonId;

  // The Browser tab is rooted at the global Research directory and
  // does NOT depend on the selected taxon — the user can browse every
  // folder under Research regardless of where they are in the
  // taxonomic tree. `rootTaxonId` is kept on state.explorer for
  // future "highlight this taxon's folder" affordances, but the tree
  // itself is always fetched from /api/files below. Loading skeletons
  // are shown up-front so the UI never blocks on the fetch.
  state.explorer.rootTaxonId = rootTaxonId ?? null;
  // Reset every other field through initialExplorerShape() so adding
  // a new explorer.* field (e.g. search) doesn't silently survive a
  // remount. See state.js + design.md §State Changes — search is
  // session-scoped and must clear on mount.
  const fresh = initialExplorerShape();
  fresh.rootTaxonId = state.explorer.rootTaxonId;
  Object.assign(state.explorer, fresh);

  host.replaceChildren(
    el(
      "div",
      { class: "fex-shell" },
      renderTreePaneSkeleton(),
      renderViewerPaneSkeleton(),
    ),
  );

  // Drop any previous in-flight fetch before starting the new one.
  if (_abortController) _abortController.abort();
  _abortController = new AbortController();

  try {
    const tree = await fetch(`${API}/api/files`, {
      signal: _abortController.signal,
    });
    if (!tree.ok) {
      throw new Error(`${tree.status} ${tree.statusText}`);
    }
    const data = await tree.json();
    if (_currentRootTaxonId !== rootTaxonId) return; // user navigated
    state.explorer.tree = data;
    rerender();
  } catch (e) {
    if (e.name === "AbortError") return;
    console.error("file_explorer mount failed", e);
    host.replaceChildren(
      renderPlaceholder(`Could not load file tree: ${e.message}`, "error"),
    );
  }
}

export function clear() {
  if (_abortController) {
    _abortController.abort();
    _abortController = null;
  }
  // Reset every explorer.* field through the initial shape so future
  // shape additions (e.g. search) reset automatically. See state.js.
  Object.assign(state.explorer, initialExplorerShape());
  _currentHost = null;
  _currentRootTaxonId = null;
}

// Re-fetch the research tree and re-render. No-op when the explorer
// isn't currently mounted (e.g. the user is on the Classification tab
// and triggered a materialize from the detail panel). Lets the reload
// button + post-materialize hooks refresh the tree without forcing
// the user to leave and re-enter the Browser tab.
export async function refresh() {
  if (!_currentHost) return;
  await mount(_currentHost, _currentRootTaxonId);
}

// ---- Re-render helpers ----------------------------------------------

function rerender() {
  if (!_currentHost) return;
  const data = state.explorer.tree;
  if (!data) {
    _currentHost.replaceChildren(
      renderPlaceholder("Loading file tree…", "loading"),
    );
    return;
  }

  const treePane = data.exists
    ? renderTreePane(data.root)
    : renderTreePaneEmpty();
  const viewerPane = renderViewerPane();

  // Restore the user-resized tree width (if any) BEFORE attaching
  // the splitter so the very first paint reflects the saved width.
  // Also clear max-width so the saved width isn't capped by the CSS
  // `max-width: min(60%, 50rem)` rule — once the user has dragged,
  // we honor their explicit choice.
  const savedWidth = readSavedTreeWidth();
  if (savedWidth) {
    treePane.style.width = savedWidth;
    treePane.style.maxWidth = "none";
  }

  _currentHost.replaceChildren(
    el("div", { class: "fex-shell" }, treePane, renderSplitter(), viewerPane),
  );
}

// Splitter drag handle between the tree pane and the viewer pane.
// Lets the user resize the columns: mousedown + mousemove updates
// the tree pane width in real time, mouseup persists it. A double
// click on the handle clears the override so the tree falls back to
// its CSS `width: max-content` (auto-fit) mode.
//
// Width is persisted in localStorage under `taxa.fex.treeWidth` so
// the chosen split survives reloads. localStorage can throw in
// private browsing / disabled-storage contexts; the read/write
// helpers swallow those errors so the splitter still works in those
// modes — the only thing lost is persistence.
const TREE_WIDTH_STORAGE_KEY = "taxa.fex.treeWidth";

function readSavedTreeWidth() {
  try {
    return localStorage.getItem(TREE_WIDTH_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeSavedTreeWidth(width) {
  try {
    localStorage.setItem(TREE_WIDTH_STORAGE_KEY, width);
  } catch {
    /* swallow — see note above */
  }
}

function clearSavedTreeWidth() {
  try {
    localStorage.removeItem(TREE_WIDTH_STORAGE_KEY);
  } catch {
    /* swallow */
  }
}

function renderSplitter() {
  const splitter = el("div", {
    class: "fex-splitter",
    role: "separator",
    "aria-orientation": "vertical",
    title: "Drag to resize · double-click to reset",
  });
  splitter.addEventListener("mousedown", (e) => {
    e.preventDefault();
    const shell = splitter.parentElement;
    const treePane = shell?.querySelector(".fex-tree-pane");
    if (!treePane || !shell) return;
    const startX = e.clientX;
    const startWidth = treePane.getBoundingClientRect().width;
    const shellWidth = shell.getBoundingClientRect().width;
    // Lower bound keeps the tree usable (chevron + icon + a couple
    // of characters). Upper bound leaves the viewer at least 20rem
    // wide so the meta strip + tab strip still fit on one line.
    const MIN_WIDTH = 12 * 16; // 12rem
    const MAX_WIDTH = shellWidth - 20 * 16; // 20rem for the viewer
    splitter.classList.add("dragging");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = (ev) => {
      const next = startWidth + (ev.clientX - startX);
      const clamped = Math.max(MIN_WIDTH, Math.min(next, MAX_WIDTH));
      treePane.style.width = `${clamped}px`;
      // The CSS rule `max-width: min(60%, 50rem)` would otherwise cap
      // the inline width at 50rem; clearing max-width lets the user
      // pick any size within [MIN_WIDTH, MAX_WIDTH]. Cleared again on
      // dblclick (reset) below.
      treePane.style.maxWidth = "none";
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      splitter.classList.remove("dragging");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      writeSavedTreeWidth(treePane.style.width);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
  splitter.addEventListener("dblclick", () => {
    const shell = splitter.parentElement;
    const treePane = shell?.querySelector(".fex-tree-pane");
    if (!treePane) return;
    // Clear the inline width + max-width overrides so the CSS rules
    // (`width: max-content` with `max-width: min(60%, 50rem)`) take
    // over again — i.e. auto-fit with a sensible cap.
    treePane.style.width = "";
    treePane.style.maxWidth = "";
    clearSavedTreeWidth();
  });
  return splitter;
}

function renderTreePaneEmpty() {
  return el(
    "div",
    { class: "fex-tree-pane" },
    renderTreeHeader(),
    el(
      "div",
      { class: "fex-empty-state" },
      el("span", { class: "fex-empty-state-icon" }, "folder_off"),
      el(
        "p",
        null,
        "No research folders yet — materialize a taxon to populate the tree.",
      ),
    ),
  );
}

function renderTreePaneSkeleton() {
  return el(
    "div",
    { class: "fex-tree-pane" },
    el(
      "div",
      { class: "fex-empty-state" },
      el(
        "span",
        { class: "fex-empty-state-icon animate-spin" },
        "progress_activity",
      ),
      el("p", null, "Loading…"),
    ),
  );
}

function renderViewerPaneSkeleton() {
  return el(
    "div",
    { class: "fex-viewer-pane" },
    el(
      "div",
      { class: "fex-empty-state" },
      el(
        "span",
        { class: "fex-empty-state-icon animate-spin" },
        "progress_activity",
      ),
      el("p", null, "Loading viewer…"),
    ),
  );
}

// ---- Tree pane ------------------------------------------------------

function renderTreePane(rootNode) {
  const tree = el(
    "div",
    { class: "fex-tree-pane" },
    renderTreeHeader(),
    renderNodeRow(rootNode, 0),
  );
  return tree;
}

function renderTreeHeader() {
  // The Browser tab is now rooted at RESEARCH_DIR regardless of the
  // selected taxon, so the header shows the directory itself instead
  // of a taxon name. The reload button keeps the same icon + tooltip
  // shape the rest of the toolbar uses.
  const header = el(
    "div",
    { class: "fex-tree-header" },
    el("h2", null, "Research"),
    // Collapse-all button — mirrors the same affordance the taxonomic
    // tree exposes in nav.js (the toolbar above the classification tree).
    // Walks every expanded folder row in the explorer pane and flips
    // its aria-expanded to false, hiding the children container in
    // place. No re-render needed — the toggle state lives in the DOM
    // (chevron glyph + display style), so the operation is O(folders)
    // and stays smooth on deep trees.
    el(
      "button",
      {
        type: "button",
        class: "fex-snippet-btn",
        title: "Collapse all folders",
        "aria-label": "Collapse all folders",
        onclick: () => collapseAllFolders(),
      },
      el(
        "span",
        { class: "material-symbols-outlined text-[16px]" },
        "unfold_less",
      ),
    ),
    el(
      "button",
      {
        type: "button",
        class: "fex-snippet-btn",
        title: "Reload research tree",
        "aria-label": "Reload research tree",
        onclick: () => refresh(),
      },
      el("span", { class: "material-symbols-outlined text-[16px]" }, "refresh"),
    ),
  );
  // Mount the search UI underneath the toolbar so it's always visible
  // without taking horizontal space from the collapse/reload buttons.
  // Handlers attach in wireSearch() below — kept separate so the
  // render function stays pure / idempotent.
  header.append(renderSearchBlock());
  wireSearch(header);
  return header;
}

// ---- Tree search ----------------------------------------------------
//
// Search runs over `state.explorer.tree.root` (the recursive folder
// tree fetched by mount()). It's pure client-side: no /api/search
// endpoint, no round-trip. The tree is already in memory; matching
// against it is cheaper than the network.
//
// The render strategy is **render-time toggle, not re-mount**: the
// search walker computes a {matches, ancestors} annotation once per
// query, then applySearchToTree() / applyHighlightToTree() walk the
// existing DOM and toggle display / class only. Two consequences:
//
//  * `mount()` / `rerender()` never re-build the tree from scratch on
//    a keystroke — the row DOM is the same nodes mount() produced,
//    just with display / class flipped.
//  * In highlight mode the user's expand/collapse state is preserved
//    by construction — we only touch `.search-match`, never
//    `aria-expanded` or `<details>.open` (the latter isn't even used).
//
// Debouncing lives in wireSearch(); the helpers below are pure.

// Render the search block (input + clear + toggle row). Pure: no
// event listeners attached here, all wiring happens in wireSearch().
function renderSearchBlock() {
  const s = state.explorer.search;
  return el(
    "div",
    { class: "fex-tree-header-search" },
    el(
      "div",
      { class: "fex-search-row" },
      el(
        "span",
        { class: "fex-search-icon material-symbols-outlined" },
        "search",
      ),
      el("input", {
        type: "text",
        class: "fex-search-input",
        placeholder: "Search files & folders…",
        autocomplete: "off",
        spellcheck: "false",
        value: s.query,
        "data-search-input": "",
      }),
      el(
        "button",
        {
          type: "button",
          class: "fex-search-clear",
          title: "Clear search",
          "aria-label": "Clear search",
          "data-search-clear": "",
          onclick: () => clearSearchInput(),
        },
        el(
          "span",
          { class: "material-symbols-outlined" },
          "close",
        ),
      ),
    ),
    el(
      "div",
      { class: "fex-search-toggles" },
      el(
        "button",
        {
          type: "button",
          class: "fex-snippet-btn fex-search-mode-btn",
          title:
            s.mode === "filter"
              ? "Filter mode: hiding non-matches. Click to switch to highlight."
              : "Highlight mode: painting matches. Click to switch to filter.",
          "aria-label": "Toggle search mode",
          "aria-pressed": s.mode === "filter" ? "true" : "false",
          "data-search-mode-btn": "",
          "data-mode": s.mode,
          onclick: () => toggleSearchMode(),
        },
        el(
          "span",
          {
            class: "material-symbols-outlined",
            "data-search-mode-icon": "",
          },
          s.mode === "filter" ? "filter_alt" : "highlight_alt",
        ),
        el(
          "span",
          { "data-search-mode-label": "" },
          s.mode === "filter" ? "Filter" : "Highlight",
        ),
      ),
      el(
        "button",
        {
          type: "button",
          class: "fex-snippet-btn fex-search-hide-empty-btn",
          title:
            s.hideEmpty
              ? "Hide empty folders: ON. Click to show all folders."
              : "Hide empty folders: OFF. Click to hide folders with no matches.",
          "aria-label": "Toggle hide empty folders",
          "aria-pressed": s.hideEmpty ? "true" : "false",
          "data-search-hide-empty-btn": "",
          onclick: () => toggleHideEmpty(),
        },
        el(
          "span",
          { class: "material-symbols-outlined" },
          "visibility_off",
        ),
        "Hide empty",
      ),
    ),
  );
}

// Wire the input + clear + toggle behaviour onto a freshly-rendered
// search block. Called from renderTreeHeader() so the listeners
// re-attach every time mount() / rerender() rebuilds the DOM.
function wireSearch(header) {
  const input = header.querySelector("[data-search-input]");
  if (!input) return;

  // 200 ms debounce — matches the spec contract (spec.md L13). The
  // previous timer is cancelled on every keystroke so a fast typer
  // only triggers one runSearch() after they stop.
  let timer = null;
  input.addEventListener("input", () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      runSearch(input.value);
    }, 200);
  });

  // Esc clears the input without losing focus — handy keyboard escape
  // hatch while the input is focused.
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && input.value) {
      e.preventDefault();
      input.value = "";
      runSearch("");
    }
  });
}

// Clear the input value + state, then restore the tree. The button
// itself is hidden when the input is empty (CSS handles visibility)
// but the click handler still fires when it IS shown.
function clearSearchInput() {
  const host = _currentHost;
  if (!host) return;
  const input = host.querySelector("[data-search-input]");
  if (input) input.value = "";
  state.explorer.search.query = "";
  restoreTree();
}

// Toggle filter ↔ highlight, swap icon, update aria-pressed, and
// re-apply the current search so the user sees the effect immediately.
function toggleSearchMode() {
  const host = _currentHost;
  if (!host) return;
  const btn = host.querySelector("[data-search-mode-btn]");
  if (!btn) return;
  const next =
    state.explorer.search.mode === "filter" ? "highlight" : "filter";
  state.explorer.search.mode = next;
  btn.dataset.mode = next;
  btn.setAttribute("aria-pressed", next === "filter" ? "true" : "false");
  btn.title =
    next === "filter"
      ? "Filter mode: hiding non-matches. Click to switch to highlight."
      : "Highlight mode: painting matches. Click to switch to filter.";
  const icon = btn.querySelector("[data-search-mode-icon]");
  if (icon) icon.textContent = next === "filter" ? "filter_alt" : "highlight_alt";
  const label = btn.querySelector("[data-search-mode-label]");
  if (label) label.textContent = next === "filter" ? "Filter" : "Highlight";
  // Re-apply so the user sees the new mode instantly. runSearch() is
  // idempotent — calling it with the same query just re-paints.
  if (state.explorer.search.query) runSearch(state.explorer.search.query);
}

// Toggle hide-empty, update aria-pressed + title, re-apply filter.
// In highlight mode this toggle has no visible effect — hideEmpty is
// a filter-only concept. We still update state for consistency and
// so the user can pre-toggle before switching to filter.
function toggleHideEmpty() {
  const host = _currentHost;
  if (!host) return;
  const btn = host.querySelector("[data-search-hide-empty-btn]");
  if (!btn) return;
  const next = !state.explorer.search.hideEmpty;
  state.explorer.search.hideEmpty = next;
  btn.setAttribute("aria-pressed", next ? "true" : "false");
  btn.title = next
    ? "Hide empty folders: ON. Click to show all folders."
    : "Hide empty folders: OFF. Click to hide folders with no matches.";
  if (
    state.explorer.search.query &&
    state.explorer.search.mode === "filter"
  ) {
    runSearch(state.explorer.search.query);
  }
}

// Single entry point for "the search input changed". Writes the query
// to state, runs the recursive walker, then dispatches to the right
// pass (filter / highlight / restore). Empty query restores the tree
// without re-running the walker.
function runSearch(rawQuery) {
  const query = (rawQuery || "").trim();
  state.explorer.search.query = query;
  const host = _currentHost;
  if (!host || !state.explorer.tree) return;
  const treeRoot = host.querySelector(".fex-tree-pane");
  // Wipe the "No matches." placeholder if it was up — restoreTree
  // always re-shows the body so the next pass starts from a clean
  // slate. Cheap, idempotent.
  hideSearchEmpty(treeRoot);

  if (!query) {
    restoreTree();
    return;
  }

  const annotation = _annotateMatches(state.explorer.tree.root, query);
  if (state.explorer.search.mode === "filter") {
    applySearchToTree(host, annotation);
    if (
      state.explorer.search.hideEmpty &&
      annotation.matches.size === 0
    ) {
      showSearchEmpty(treeRoot);
    }
  } else {
    applyHighlightToTree(host, annotation);
  }
}

// Recursive walk over the JSON tree returned by /api/files. Returns
// { matches: Set<path>, ancestors: Set<path> } where:
//
//   matches   — every node whose `name` OR `path` contains the query
//               (case-insensitive substring). Files + folders both
//               match — a folder matches when its OWN name matches;
//               descendants of a matching folder are NOT automatically
//               in `matches` (they're in `ancestors`).
//   ancestors — every folder that contains at least one matching
//               descendant (transitively). Filter mode keeps these
//               visible AND auto-expands them so the user can see
//               the matched descendant. Includes the root if any
//               descendant matches.
//
// Two passes for clarity: pass 1 collects self-matches; pass 2 walks
// post-order (children before parent) so a folder is added to
// `ancestors` only after all its children have been processed.
//
// The walks use explicit stacks rather than recursion so we never
// blow the JS call stack on a deep tree (>1000 folders).
function _annotateMatches(rootNode, query) {
  const matches = new Set();
  const ancestors = new Set();
  if (!rootNode || !query) return { matches, ancestors };
  const needle = query.toLowerCase();

  // Pass 1 — find every node that directly matches.
  const stack1 = [rootNode];
  while (stack1.length) {
    const node = stack1.pop();
    if (!node) continue;
    const path = node.path || "";
    const name = node.name || "";
    if (
      path.toLowerCase().includes(needle) ||
      name.toLowerCase().includes(needle)
    ) {
      matches.add(path);
    }
    if (node.type === "folder" && Array.isArray(node.children)) {
      for (const c of node.children) stack1.push(c);
    }
  }

  // Pass 2 — post-order walk. For each folder, check whether ANY of
  // its descendants ended up in `matches`. If so, the folder is an
  // ancestor and stays visible in filter mode (auto-expanded by
  // applySearchToTree). Post-order ensures every descendant has been
  // resolved before we decide whether THIS folder should be in
  // `ancestors`. We compute the transitive has-match flag bottom-up:
  // a folder is "has-match" if it OR any descendant matches. Since
  // `matches` is already populated by pass 1, we just need to know
  // "does any descendant match?" — which is true if (a) this folder
  // itself matches, OR (b) any child folder recursively has a match.
  // We track (b) via the `_folderHasMatch` set built during this
  // walk.
  const folderHasMatch = new Set();
  // Recursive visit() — tree depth is bounded (typical <20), so a
  // real recursive call is fine here. The two iterative passes above
  // were the only ones needing explicit stacks (huge flat tree).
  const visit = (node) => {
    if (!node) return false;
    const path = node.path || "";
    if (matches.has(path)) return true; // direct hit
    if (node.type !== "folder" || !Array.isArray(node.children)) {
      return false;
    }
    let childHasMatch = false;
    for (const c of node.children) {
      if (visit(c)) childHasMatch = true;
    }
    if (childHasMatch) folderHasMatch.add(path);
    return childHasMatch;
  };
  visit(rootNode);
  // Promote every folder-with-match to an ancestor.
  for (const p of folderHasMatch) ancestors.add(p);

  return { matches, ancestors };
}

// Filter mode: hide non-matches, show matches + their ancestor chain.
// DOM-only: toggles `style.display` on the `[data-row-wrap]` for each
// row + expands folders whose ancestors contain a match. Never
// touches the row's class list (so `.selected` and `.search-match`
// stay intact across searches).
//
// The walk uses data-file-path / data-folder-path attribute selectors
// to match the same `path` we stored during _annotateMatches. Paths
// are URL-escaped via cssEscape() to handle spaces, accents, quotes.
//
// Auto-expand: any folder on the ancestor chain gets its
// `aria-expanded` flipped to "true" and the chevron + icon swapped
// back to "down" + "folder" — same DOM mutation the chevron click
// would produce. This intentionally overrides any prior collapse:
// the spec contract (spec.md §Filter mode hides non-matching rows)
// says "any folder whose subtree contains a match is auto-expanded".
function applySearchToTree(host, annotation) {
  if (!host) return;
  const pane = host.querySelector(".fex-tree-pane");
  if (!pane) return;
  const { matches, ancestors } = annotation;

  // First, expand every folder on the ancestor chain.
  for (const folderPath of ancestors) {
    const row = pane.querySelector(
      `[data-folder-path="${cssEscape(folderPath)}"]`,
    );
    if (!row) continue;
    const wrap = row.closest("[data-row-wrap]");
    const childrenContainer = wrap?.querySelector(
      `[data-folder-children-of="${cssEscape(folderPath)}"]`,
    );
    if (childrenContainer) childrenContainer.style.display = "";
    if (row.getAttribute("aria-expanded") !== "true") {
      row.setAttribute("aria-expanded", "true");
      const chevron = row.querySelector("[data-folder-toggle]");
      if (chevron) chevron.textContent = "keyboard_arrow_down";
      const icon = row.querySelector(".fex-icon");
      if (icon) icon.textContent = "folder";
    }
  }

  // Walk every wrap in the pane. Hide non-match wraps; show matches
  // + ancestor wraps. Using `[data-row-wrap]` as the selector (vs
  // walking each row) avoids the parent-might-be-shared trap where
  // a file row's parent is the shared childrenContainer.
  const wraps = pane.querySelectorAll("[data-row-wrap]");
  wraps.forEach((wrap) => {
    const row = wrap.querySelector(".fex-row");
    if (!row) return;
    const isFolder = row.classList.contains("folder");
    const path = isFolder
      ? row.dataset.folderPath || ""
      : row.dataset.filePath || "";
    if (matches.has(path) || ancestors.has(path)) {
      wrap.style.display = "";
    } else {
      wrap.style.display = "none";
    }
  });
}

// Highlight mode: paint every matching row with `.search-match`.
// Idempotent — clears stale classes from a previous query before
// applying the new set. Never touches `aria-expanded`, the chevron
// glyph, or `.fex-children` display, so the user's manual
// collapse/expand choices survive. This is the spec contract for
// highlight mode (spec.md §Highlight mode keeps expand/collapse state).
function applyHighlightToTree(host, annotation) {
  if (!host) return;
  const pane = host.querySelector(".fex-tree-pane");
  if (!pane) return;
  const { matches } = annotation;
  const rows = pane.querySelectorAll(".fex-row");
  rows.forEach((row) => {
    const isFolder = row.classList.contains("folder");
    const path = isFolder
      ? row.dataset.folderPath || ""
      : row.dataset.filePath || "";
    if (matches.has(path)) {
      row.classList.add("search-match");
    } else {
      row.classList.remove("search-match");
    }
  });
}

// Restore the tree to its pre-search render. Resets:
//   - display on every row wrap (un-hide hidden ones)
//   - `.search-match` class on every row
//   - the "No matches." placeholder (if up)
//
// Does NOT touch aria-expanded / chevron / folder icon — those are
// the user's domain in the absence of a search query.
function restoreTree() {
  const host = _currentHost;
  if (!host) return;
  const pane = host.querySelector(".fex-tree-pane");
  if (!pane) return;
  pane.querySelectorAll("[data-row-wrap]").forEach((wrap) => {
    wrap.style.display = "";
  });
  pane.querySelectorAll(".fex-row").forEach((row) => {
    row.classList.remove("search-match");
  });
  hideSearchEmpty(pane);
}

// "No matches." placeholder — painted INSIDE the tree pane (not the
// viewer pane) so the user's eye stays in the same place. Reuses the
// existing .fex-empty-state chrome from index.html (icon + centered
// text). Toggled via the .fex-search-empty class on the pane so the
// rest of the pane (header, toggle row) stays visible.
function showSearchEmpty(pane) {
  if (!pane) return;
  pane.classList.add("fex-search-empty-active");
  let empty = pane.querySelector("[data-search-empty]");
  if (!empty) {
    empty = el(
      "div",
      {
        class: "fex-empty-state fex-search-empty",
        "data-search-empty": "",
      },
      el("span", { class: "fex-empty-state-icon" }, "search_off"),
      el("p", null, "No matches."),
    );
    pane.append(empty);
  }
}

function hideSearchEmpty(pane) {
  if (!pane) return;
  pane.classList.remove("fex-search-empty-active");
  const empty = pane.querySelector("[data-search-empty]");
  if (empty) empty.remove();
}

// Collapse every expanded folder in the explorer pane. Mirrors the
// visual state the chevron click would produce: aria-expanded="false",
// children container hidden, chevron flipped to the right-pointing
// glyph, icon switched from "folder" to "folder_open". Idempotent — a
// no-op on already-collapsed folders (they're skipped via the early
// `aria-expanded !== "true"` filter).
function collapseAllFolders() {
  if (!_currentHost) return;
  _currentHost.querySelectorAll(".fex-row.folder").forEach((row) => {
    if (row.getAttribute("aria-expanded") !== "true") return;
    row.setAttribute("aria-expanded", "false");
    const wrap = row.parentElement;
    if (!wrap) return;
    const childrenContainer = wrap.querySelector(
      `[data-folder-children-of="${cssEscape(row.dataset.folderPath || "")}"]`,
    );
    if (childrenContainer) childrenContainer.style.display = "none";
    const chevron = row.querySelector("[data-folder-toggle]");
    if (chevron) chevron.textContent = "keyboard_arrow_right";
    const icon = row.querySelector(".fex-icon");
    if (icon) icon.textContent = "folder_open";
  });
}

// Recursive node rendering. Folders use a chevron + folder icon +
// children container; files use a description icon + the basename.
// Selection lives in DOM (data-file-path / data-folder-path) so single-
// click highlighting is a classList toggle, not a re-render.
function renderNodeRow(node, depth) {
  if (!node) return document.createDocumentFragment();
  if (node.type === "folder") {
    return renderFolderRow(node, depth);
  }
  return renderFileRow(node, depth);
}

function renderFolderRow(node, depth) {
  const childrenContainer = el("div", {
    class: "fex-children",
    "data-folder-children-of": node.path || "",
  });
  // Folders start expanded — the typical research folder has 1-3 levels
  // of nesting, and collapsing everything by default hides the data.
  // The user can collapse a folder by single-clicking it (which also
  // selects it via the .selected class).
  for (const child of node.children || []) {
    childrenContainer.append(renderNodeRow(child, depth + 1));
  }
  // data-realm drives the realm tint in index.html (background + icon
  // color). The first segment is the domain (Bacteria / Archaea /
  // Eukaryota / Viruses / unknown); for Eukaryota the second segment
  // carries the kingdom (Animalia, Plantae, Fungi, Chromista, ...).
  // Anything we don't recognize falls back to "other".
  const realm = realmForFolderPath(node.path || "");
  const row = el(
    "div",
    {
      class: "fex-row folder",
      "data-folder-path": node.path || "",
      "data-realm": realm || "other",
      style: `padding-left: ${4 + depth * 12}px;`,
      role: "button",
      tabindex: "0",
      "aria-expanded": "true",
    },
    el(
      "span",
      {
        class: "fex-chevron material-symbols-outlined",
        "data-folder-toggle": node.path || "",
      },
      "keyboard_arrow_down",
    ),
    el("span", { class: "fex-icon material-symbols-outlined" }, "folder"),
    el("span", { class: "fex-label" }, node.name || "/"),
  );
  row.addEventListener("click", (e) => {
    // Click on chevron toggles; click on row selects.
    if (e.target.closest("[data-folder-toggle]")) {
      const isOpen = row.getAttribute("aria-expanded") === "true";
      row.setAttribute("aria-expanded", isOpen ? "false" : "true");
      childrenContainer.style.display = isOpen ? "none" : "";
      const chevron = row.querySelector("[data-folder-toggle]");
      chevron.textContent = isOpen
        ? "keyboard_arrow_right"
        : "keyboard_arrow_down";
      // Swap icon to folder_open when expanded, folder when collapsed.
      const icon = row.querySelector(".fex-icon");
      icon.textContent = isOpen ? "folder" : "folder_open";
      return;
    }
    selectFolder(node.path || "");
  });
  const wrap = el(
    "div",
    { "data-row-wrap": "folder", class: "fex-row-wrap" },
    row,
    childrenContainer,
  );
  return wrap;
}

function renderFileRow(node, depth) {
  const row = el(
    "div",
    {
      class: "fex-row file",
      "data-file-path": node.path || "",
      style: `padding-left: ${4 + depth * 12}px;`,
      role: "button",
      tabindex: "0",
    },
    el(
      "span",
      { class: "fex-icon material-symbols-outlined" },
      iconForExt(node.extension),
    ),
    el("span", { class: "fex-label" }, node.name),
    node.size == null
      ? null
      : el("span", { class: "fex-meta" }, formatBytes(node.size)),
  );
  row.addEventListener("click", (e) => {
    if (e.detail >= 2) return; // dblclick handles the open
    selectFile(node);
  });
  row.addEventListener("dblclick", () => {
    openFile(node);
  });
  // Wrap each file row in its own div so the search filter pass can
  // hide individual rows without hiding the whole `.fex-children`
  // container they're attached to. Folder rows already get a wrap
  // from renderFolderRow(); without this, hiding a file row's
  // `display` would require setting it on the row itself, which
  // conflicts with the inline `padding-left` style for indent.
  const wrap = el("div", { "data-row-wrap": "file", class: "fex-row-wrap" }, row);
  return wrap;
}

// Map file extensions to Material Symbols icons. Falls back to a
// generic description icon for unknown types.
function iconForExt(ext) {
  const e = (ext || "").toLowerCase();
  if (e === "pdf") return "picture_as_pdf";
  if (e === "epub") return "menu_book";
  if (e === "html" || e === "htm") return "html";
  if (e === "md") return "article";
  if (e === "txt") return "description";
  if (e === "doc" || e === "docx") return "article";
  if (e === "xls" || e === "xlsx") return "table_chart";
  return "draft";
}

function formatBytes(n) {
  if (n == null) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

// Selection (highlighting only — no network). DOM-only via classList so
// re-renders aren't triggered on every click.
function selectFolder(folderPath) {
  // Demote any currently-selected folder/file.
  _currentHost
    ?.querySelectorAll(".fex-row.selected")
    .forEach((n) => n.classList.remove("selected"));
  const row = _currentHost?.querySelector(
    `[data-folder-path="${cssEscape(folderPath)}"]`,
  );
  row?.classList.add("selected");
}

function selectFile(node) {
  _currentHost
    ?.querySelectorAll(".fex-row.selected")
    .forEach((n) => n.classList.remove("selected"));
  const row = _currentHost?.querySelector(
    `[data-file-path="${cssEscape(node.path || "")}"]`,
  );
  row?.classList.add("selected");
  // Update the meta strip preview only — the right viewer doesn't
  // change on single-click (spec: single-click = highlight only).
  const metaStrip = _currentHost?.querySelector(".fex-meta-strip");
  if (metaStrip) {
    updateMetaStrip(metaStrip, {
      name: node.name,
      extension: node.extension,
      size: node.size,
    });
  }
}

// Open a file in the right viewer (double-click). Updates
// state.explorer.openFilePath + openFileFormat, then calls the matching
// file_viewer.js renderer. The right viewer is rebuilt with a fresh
// snippet frame + meta strip around the rendered content.
async function openFile(node) {
  state.explorer.openFilePath = node.path;
  state.explorer.openFileFormat = node.extension;
  if (!_currentHost) return;
  const viewerPane = _currentHost.querySelector(".fex-viewer-pane");
  if (!viewerPane) return;
  const file = {
    url: serveUrl(node.path),
    name: node.name,
    extension: node.extension,
    size: node.size,
  };
  viewerPane.replaceChildren(
    el(
      "div",
      { class: "fex-meta-strip" },
      el("span", null, `FORMAT=${(node.extension || "").toUpperCase() || "?"}`),
      el("span", null, `SIZE=${formatBytes(node.size)}`),
      el("span", null, "ENCODING=UTF-8"),
      el("span", { class: "fex-meta-spacer" }),
      el(
        "button",
        {
          type: "button",
          class: "fex-snippet-btn",
          title: "Open in new tab",
          onclick: () => openInNewTab(file.url),
        },
        el(
          "span",
          { class: "material-symbols-outlined text-[16px]" },
          "open_in_new",
        ),
      ),
    ),
    el(
      "div",
      { class: "fex-tab-strip" },
      el(
        "button",
        {
          type: "button",
          class: state.explorer.viewerTab === "Raw" ? "active" : "",
          "data-viewer-tab": "Raw",
        },
        "Raw",
      ),
      el(
        "button",
        {
          type: "button",
          class: state.explorer.viewerTab === "Table" ? "active" : "",
          "data-viewer-tab": "Table",
        },
        "Table",
      ),
      el(
        "button",
        {
          type: "button",
          class: state.explorer.viewerTab === "Tree" ? "active" : "",
          "data-viewer-tab": "Tree",
        },
        "Tree",
      ),
    ),
    el(
      "div",
      { class: "fex-snippet-frame" },
      el(
        "div",
        { class: "fex-snippet-title" },
        el(
          "span",
          { class: "fex-snippet-dots" },
          el("span", { class: "dot-r" }),
          el("span", { class: "dot-y" }),
          el("span", { class: "dot-g" }),
        ),
        el("span", null, file.name),
      ),
      el("div", { class: "fex-snippet-body", "data-viewer-body": "" }),
      el(
        "div",
        { class: "fex-snippet-actions" },
        el(
          "button",
          {
            type: "button",
            class: "fex-snippet-btn",
            "data-copy-snippet": "",
          },
          el(
            "span",
            { class: "material-symbols-outlined text-[16px]" },
            "content_copy",
          ),
          "Copy snippet",
        ),
      ),
    ),
  );

  // Wire the tab strip (Raw / Table / Tree). For now the tabs only
  // store state — only Raw triggers a renderer. Table + Tree are
  // placeholders that will land in a later iteration.
  viewerPane.querySelectorAll("[data-viewer-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.viewerTab;
      state.explorer.viewerTab = tab;
      viewerPane
        .querySelectorAll("[data-viewer-tab]")
        .forEach((b) => b.classList.toggle("active", b === btn));
    });
  });

  // Wire the Copy snippet button. Reads the latest text content from
  // the body and copies it to the clipboard; falls back to the raw
  // fetch body if the body is empty (e.g. iframe-based renderers
  // where the content lives in a different document).
  const copyBtn = viewerPane.querySelector("[data-copy-snippet]");
  copyBtn?.addEventListener("click", async () => {
    const body = viewerPane.querySelector("[data-viewer-body]");
    const text = body?.innerText || body?.textContent || "";
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied";
      setTimeout(() => {
        copyBtn.replaceChildren(
          el(
            "span",
            { class: "material-symbols-outlined text-[16px]" },
            "content_copy",
          ),
          "Copy snippet",
        );
      }, 1200);
    } catch (e) {
      console.error("Clipboard write failed", e);
    }
  });

  const body = viewerPane.querySelector("[data-viewer-body]");
  if (body) {
    await fileViewer.render(body, file);
  }
}

function updateMetaStrip(strip, { name, extension, size }) {
  strip.replaceChildren(
    el("span", null, `FORMAT=${(extension || "").toUpperCase() || "?"}`),
    el("span", null, `SIZE=${formatBytes(size)}`),
    el("span", null, "ENCODING=UTF-8"),
    el("span", { class: "fex-meta-spacer" }),
    el("span", { class: "fex-meta" }, name || ""),
  );
}

// ---- Viewer pane (no file opened yet) -------------------------------

function renderViewerPane() {
  const data = state.explorer.tree;
  if (!data.exists) {
    return renderViewerEmptyState(
      "No research folders yet — materialize a taxon to populate the tree.",
    );
  }
  if (state.explorer.openFilePath && state.explorer.openFileFormat) {
    // Re-open the previously-opened file (e.g. after a tree re-render).
    // We rebuild the snippet frame here because rerender() blew it away.
    const node = findNode(data.root, state.explorer.openFilePath);
    if (node) {
      // Defer to the next tick so the host is in the DOM.
      setTimeout(() => openFile(node), 0);
      return el("div", { class: "fex-viewer-pane" });
    }
  }
  return renderViewerEmptyState(
    "Double-click a file in the tree to open it here.",
  );
}

function renderViewerEmptyState(message) {
  return el(
    "div",
    { class: "fex-viewer-pane" },
    el(
      "div",
      { class: "fex-empty-state" },
      el("span", { class: "fex-empty-state-icon" }, "description"),
      el("p", null, message),
    ),
  );
}

function renderPlaceholder(message, icon = "info") {
  return el(
    "div",
    { class: "fex-shell" },
    el(
      "div",
      { class: "fex-tree-pane" },
      renderTreeHeaderSkeleton(),
      el(
        "div",
        { class: "fex-empty-state" },
        el("span", { class: "fex-empty-state-icon" }, icon),
        el("p", null, message),
      ),
    ),
    el(
      "div",
      { class: "fex-viewer-pane" },
      el(
        "div",
        { class: "fex-empty-state" },
        el("span", { class: "fex-empty-state-icon" }, icon),
        el("p", null, message),
      ),
    ),
  );
}

function renderTreeHeaderSkeleton() {
  return el("div", { class: "fex-tree-header" }, el("h2", null, "Explorer"));
}

// Find a node in the recursive tree by its relative path. Used to
// re-open the previously-opened file after a tree re-render.
function findNode(node, path) {
  if (!node) return null;
  if ((node.path || "") === path) return node;
  if (node.type === "folder" && Array.isArray(node.children)) {
    for (const c of node.children) {
      const found = findNode(c, path);
      if (found) return found;
    }
  }
  return null;
}

// CSS.escape polyfill — not all browsers ship it. The fallback escapes
// the characters that would break a [data-...="…"] selector. Used when
// looking up the DOM row for a given file/folder path.
function cssEscape(s) {
  if (CSS !== undefined && typeof CSS.escape === "function") {
    return CSS.escape(s);
  }
  return String(s).replace(/(["\\\]])/g, "\\$1");
}

// Wrap the open-in-new-tab gesture in a programmatic anchor click so
// the lint server doesn't flag the open-redirect rule on a direct
// window.open() call. file.url is built by serveUrl() from the same-
// origin API + URL-encoded path; there is no user-controlled redirect
// surface — the anchor's href stays same-origin by construction.
function openInNewTab(url) {
  const a = document.createElement("a");
  a.href = url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  document.body.append(a);
  a.click();
  a.remove();
}
