# Design: File Explorer — Search + Complete Placeholder Tabs

## Context

`web/file_explorer.js` shipped in the `2026-08-24-file-explorer` change
with two known gaps:

1. **Search.** The recursive Research tree has no locate affordance. In a
   deeply nested taxon (typical: 50–500 folders under `Eukaryota/.../<species>`)
   the user scrolls the tree pane looking for one file.
2. **Table + Tree viewer tabs are dead UI.** Lines 647–657 toggle
   `viewerTab` state but never call a renderer. CSV opens as `<pre>`;
   JSON opens as `<pre>`.

This change closes both gaps with three additions:

- **Tree search** — debounced input in the left header, with **filter**
  (hide non-matches, auto-expand ancestors) and **highlight** (class only,
  preserves user expand/collapse) modes, plus a **hide-empty** toggle.
- **Table tab** — CSV/TSV via Papa Parse with a sticky `<thead>` and
  scrollable body.
- **Tree tab** — JSON as a native collapsible tree with 16 px indent
  per level and type-coloured leaves.

## Goals

| Goal | Outcome |
| --- | --- |
| Search → match within 250 ms of stopping typing | 200 ms debounce + single-pass walk + per-node memo |
| Filter preserves no state — pure render-side | Search walks `state.explorer.tree.root` once; render filters, never mutates |
| Highlight preserves user expand/collapse | Highlight adds a class only; `aria-expanded` untouched |
| CSV/TSV renders with header pinned | `position: sticky` on `<thead>`, body scrolls both axes |
| JSON tree is collapsible with type colour | Native `<details>`/`<summary>` + Tailwind token classes |
| Search survives within session but not reload | `state.explorer.search` cleared by `clear()` / `mount()` |

## Non-Goals

- No `/api/search` endpoint (tree already in memory).
- No regex, glob, or case-sensitive options.
- No content search — only `name` + `path` substring match.
- No upload / rename / delete / multi-select.
- No new JS test runner.
- No localStorage for search (session-scoped only — explicitly noted).
- No syntax highlighting in the JSON tree.

## Architecture

The existing explorer module boundary stays intact. **All new code is
additive inside the two existing files**, plus a small state shape
extension.

```
openspec/changes/file-explorer-search-and-tabs/
├── proposal.md
├── specs/
│   └── research/spec.md           ← delta (ADDED + MODIFIED Requirements)
└── design.md                      ← this file
```

### Module boundaries

| File | New responsibilities |
| --- | --- |
| `web/file_explorer.js` (+~120 lines) | Search input UI + 200 ms debouncer, mode + hide-empty toggle buttons, `runSearch(query)` single-pass walker, `applySearchToTree()` filter pass, `applyHighlightToTree()` class pass, `renderSearchMatch` recursive dispatch. Update `openFile()` so tab clicks dispatch to renderers. |
| `web/file_viewer.js` (+~110 lines) | Add `Papa` to `CDN_URLS`. New `renderTable()` (CSV/TSV via Papa Parse). New `renderTree()` (JSON via native DOM, 50 000-node cap). |
| `web/state.js` (+~5 lines) | Add `search: { query: "", mode: "filter", hideEmpty: true }` to `state.explorer` + mirror in `initialExplorerShape()`. |
| `web/index.html` (+~60 lines CSS + 1 `<script>`) | `.fex-tree-header-search` row, `.fex-search-input`, `.fex-row.search-match`, `.fex-tree-leaf` + type tokens, `.fex-csv-table` + sticky thead, `.fex-json-tree` indent guide, pinned `papaparse@5.4.1` CDN. |

Total touched: **~295 lines** — comfortably inside the 400-line review budget.

### What stays put

- `mount()`, `clear()`, `refresh()` — unchanged. `clear()` resets
  `state.explorer.search` to initial shape.
- `rerender()` — unchanged. The search render is a separate pass that
  re-uses the existing DOM (no full re-mount).
- `openFile()` shell (meta strip + tab strip + snippet frame) — unchanged.
- All renderers in `file_viewer.js` — unchanged. `render()` dispatcher
  gains two entries (`csv`/`tsv` → `renderTable`, `json` → `renderTree`).

## Data Flow

### Search → render

```
type "acr" in .fex-search-input
   ↓ input event
onSearchInput() → clearTimeout(prev) → setTimeout(200ms, runSearch)
   ↓
runSearch(query):
   state.explorer.search.query = query
   if !query → restoreTree(); return
   state._search = { matches: Set<path>, ancestors: Set<path>, mode, hideEmpty }
   (one recursive walk; memo per node; see Decisions)
   ↓
applySearchToTree() OR applyHighlightToTree():
   filter mode  → walk DOM, hide non-matches, expand ancestors, "No matches." if empty
   highlight    → walk DOM, add .search-match class, do NOT touch aria-expanded
   ↓
(no re-render — just classList/display toggles on the DOM that mount() built)
```

### Tab click → renderer

```
click [data-viewer-tab="Table"]
   ↓
state.explorer.viewerTab = "Table"
   ↓
   if (ext in {csv, tsv})  → fileViewer.render(body, file)   // render() dispatches
   if (ext === "json")     → fileViewer.render(body, file)   // render() dispatches
   else → "Table view not available for this format — use Raw."
   ↓
flip .active on tab buttons
```

### Mode toggle → re-apply

```
click .fex-search-mode-btn
   ↓
state.explorer.search.mode = mode === "filter" ? "highlight" : "filter"
update toggle icon (filter_alt_off ↔ highlight_alt)
if (query) applySearchToTree() / applyHighlightToTree()
```

## State Changes

`state.explorer.search` (added to `state.js`):

```js
search: {
  query: "",                  // current debounced input value
  mode: "filter",             // "filter" | "highlight"
  hideEmpty: true,            // filter-only: hide folders with no descendant matches
}
```

**Persistence: session-only.** Reloading the page calls `mount()` → which
resets `state.explorer.search = { query: "", mode: "filter", hideEmpty: true }`.
This is **deliberately not** `localStorage` (unlike the splitter width
in `file_explorer.js:165`):

| Reason | Detail |
| --- | --- |
| Privacy | `localStorage` survives across sessions and across the same-domain visit patterns — research folders may contain sensitive taxon names. |
| Spec contract | The proposal's "Out of Scope" explicitly excludes "Persisting query across reloads (session-scoped)." |
| Simplicity | The tree itself is re-fetched on reload anyway; persisting the query without the tree produces a stale empty result. |

A module-level `_searchCache` (Map<query, {matches, ancestors}>) lives on
`file_explorer.js` scope — same idea, dropped on `clear()`.

## Decisions

| Decision | Choice | Alternatives considered | Rationale |
| --- | --- | --- | --- |
| Backend search | **None — pure client-side** | Add `GET /api/taxon/{id}/files/search?q=` | The full tree is already in `state.explorer.tree` (one-shot fetch in `mount()`). Server search duplicates that walk. A round-trip per keystroke (even debounced) is wasted bandwidth on what the client already has. |
| Filter algorithm | **Recursive walk, render-time toggle** | CSS `:has()` selector to hide non-matches | `:has()` is broadly supported but cannot *expand* collapsed ancestors without JS anyway, and 50 000-node `:has()` walks show up in DevTools perf traces. The render-time walk is one pass, deterministic, and lets us collect the ancestor set in the same pass. |
| Highlight approach | **`.search-match` class only** | Re-render a separate "search results" tree alongside the main one | Class-only keeps `selectFile`/`openFilePath` semantics untouched — the row is the same DOM node, just visually highlighted. A separate tree would fork selection state and double-click handling. |
| Tree viewer | **Native `JSON.parse` + recursive DOM** | `jsoneditor` CDN | The user can already view JSON via the Raw tab (fenced `<pre>`). What they need from the Tree tab is *expand/collapse* + indent — both native `<details>` give us for free. Adding `jsoneditor` doubles the CDN surface for one benefit (drag-and-drop edit) the spec explicitly excludes. |
| JSON cap | **50 000 nodes** | Streaming JSON.parse (`oboe.js`) or no cap | The proposal's "Risks" row calls out JSON > 10 MB freezing the renderer. 50 000 nodes is roughly the largest realistic taxonomic metadata file we've seen; beyond that, the user gets the truncation message and falls back to Raw. Streaming is overkill for a viewer tab. |
| Table viewer | **Papa Parse via existing `loadScriptOnce` pattern** | Hand-rolled CSV parser (handle quoted commas, newlines, etc.) | Papa Parse is 45 KB gzipped, already lazy-loaded by the existing pattern (`file_viewer.js:24–28`), and handles the edge cases (escaped quotes, CRLF, empty cells) correctly. A hand-rolled parser is a recurring bug source. |
| Toggle persistence | **`state.explorer.search` only** | `localStorage` | See "Persistence" above — session-scoped is the spec contract. |
| Search debounce | **200 ms** | 100 ms (snappier) / 300 ms (cheaper) | 200 ms is the spec's contract (`spec.md:13`) and matches the human "I've finished typing" threshold. Faster feels live but doubles work on every typo. |

## API Contracts

**None new.** This change is frontend-only. The existing
`GET /api/files` (returns the recursive tree) and
`GET /api/files/serve?path=…` (streams a single file) are the only
endpoints touched. No schema, no Python deps, no new FastAPI routes.

## CSS Additions

All new selectors live in the existing `<style>` block inside
`web/index.html`, right after `.fex-row.folder[data-realm="chromista"]`:

| Selector | Purpose |
| --- | --- |
| `.fex-tree-header-search` | Two-row header below `.fex-tree-header` — input row + toggle row. |
| `.fex-search-input` | 100% width, monospace (`JetBrains Mono`), rounded-md, outline-variant border, focus ring. Clear button (`.fex-search-clear`) overlays the right edge. |
| `.fex-search-toggles` | Flex row with `.fex-search-mode-btn` (filter ↔ highlight icon) + `.fex-search-hide-empty-btn`. Active state mirrors `.fex-snippet-btn` styling. |
| `.fex-row.search-match` | `background: color-mix(in srgb, var(--primary) 12%, transparent); outline: 1px solid color-mix(in srgb, var(--primary) 40%, transparent);` — clearly distinct from `.selected` (solid primary background). |
| `.fex-tree-leaf` | Indent guide per JSON nesting level (16 px). |
| `.fex-tree-leaf.type-string` | `color: var(--realm-fungi)` (Tailwind token, green family). |
| `.fex-tree-leaf.type-number` | `color: var(--realm-bacteria)` (blue family). |
| `.fex-tree-leaf.type-boolean` | `color: var(--realm-archaea)` (purple family). |
| `.fex-tree-leaf.type-null` | `color: var(--on-surface-variant); font-style: italic;` |
| `.fex-csv-table` | `width: 100%; border-collapse: collapse;` + `<thead>` with `position: sticky; top: 0; background: var(--surface-container);` |
| `.fex-csv-table td, .fex-csv-table th` | 1 px outline-variant border, monospace, 12 px, padding 4 px 8 px. |
| `.fex-csv-scroller` | `max-height: calc(100vh - 240px); overflow: auto;` — vertical scroll, horizontal scroll on overflow. |
| `.fex-json-tree` | `<details>` reset (margin-left: 0), `<summary>` row uses `.fex-row` shape (chevron + icon + label), children get 16 px padding-left. |
| `.fex-search-empty` | "No matches." message reusing `.fex-empty-state` chrome. |

**No hardcoded hex.** Every colour pulls from the Tailwind tokens defined
in `tailwind.config.js` (`--primary`, `--realm-*`, `--on-surface-variant`)
— matching the existing `.fex-banner` and `.fex-row[data-realm]` rules.

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Search lags on >1 000-file trees | Med | One recursive pass + `Set<string>` membership for path lookups. Memoize per-node `match` flag so repeated queries on the same subtree (e.g. backspace + retype) skip already-walked branches. 200 ms debounce absorbs keystroke bursts. |
| Highlight mode mutates expand/collapse state | Med | Highlight touches `classList` only — `aria-expanded`, `.fex-children` display, and the chevron glyph stay at their pre-search value. The render pass is `add .search-match` / `remove .search-match` on `.fex-row` nodes, nothing else. |
| Existing tab wiring only toggles classes | Med (already known) | The `openFile()` block at `file_explorer.js:650–657` currently calls only `classList.toggle("active", …)`. New behaviour: after setting state, look up the matching renderer for the active format — `csv`/`tsv` → `renderTable`, `json` → `renderTree`, otherwise show "Table/Tree view not available for this format — use Raw." The Raw tab keeps the existing flow (renderer dispatched on `openFile`, never re-dispatched on tab click). |
| JSON > 10 MB freezes renderer | Med | Cap walk at 50 000 nodes. Beyond the cap, append a `<p>` with `"Tree truncated — open raw"` and a link to the Raw tab. The walk is iterative (`stack.push`/`stack.pop`) to avoid stack-overflow on deep arrays. |
| Papa Parse CDN fails | Low | Reuse `loadScriptOnce("Papa", CDN_URLS.Papa)` — same retry-by-clearing-the-cached-promise pattern as `mammoth`/`XLSX`/`ePub` (`file_viewer.js:35–53`). Failure renders the existing `.fex-banner` with `"Viewer offline — raw download unavailable."` |
| Toggle state diverges between `state` and DOM | Low | Each toggle's `onclick` writes `state.explorer.search.*` first, then re-applies the search if a query is active. The render pass is idempotent. |
| `searchEmpty` "No matches." flashes during typing | Low | The "No matches." copy only paints when `query.length > 0 && matches.size === 0 && mode === "filter" && hideEmpty`. Highlight mode never shows it. |
| Search results don't survive a tree reload | Low | `refresh()` calls `mount()` which resets `state.explorer.search` to initial shape — same as `clear()`. The user re-types; this matches the "session-scoped" contract. |

## Testing

**No JS test runner** — the project ships with pytest only. Verification
is the hand-testable scenarios in `spec.md` plus a `make smoke` run.

| Scenario | Steps | Expected |
| --- | --- | --- |
| Filter mode hides non-matches | Type `acr` in the search input | Within 250 ms, only matching rows visible; matching parents auto-expanded. |
| Filter + hide-empty = "No matches." | Type `zzzzz` | Pane shows the `fex-empty-state` icon + `"No matches."`. |
| Highlight keeps expand/collapse | Collapse folder `X`, switch to highlight, type a match inside `X` | `X` stays collapsed; matching leaf has `.fex-row.search-match`. |
| Clear restores tree | Type a query, click the `×` clear button | Input empty, tree restored, no class remnants in highlight mode. |
| Toggles persist query | Filter mode with `acr` typed → click highlight toggle | Query stays, mode icon flips, rows get `.search-match`. |
| CSV opens with sticky header | Double-click `data.csv`, click Table | First row is sticky; body scrolls both axes; meta strip still `FORMAT=CSV | SIZE=…`. |
| TSV uses tab delimiter | Double-click `data.tsv`, click Table | No `\t` artefacts in cells. |
| Papa Parse CDN down | Throttle network, double-click `data.csv`, click Table | `.fex-banner` shows; Raw tab still works. |
| JSON root expands on click | Double-click `spec.json`, click Tree | Root caret; clicking expands children with 16 px indent. |
| Leaf types are colour-coded | Expand an object | Strings, numbers, booleans, `null` each carry a distinct Tailwind token class. |
| Large JSON truncated | Open a 60 000-node JSON | `"Tree truncated — open raw"` shown; Raw still renders. |
| Non-tabular file ignores tabs | Double-click `notes.md`, click Table | Message `"Table/Tree view not available for this format — use Raw."` No console error. |

## Migration / Rollout

No data migration. No schema change. No backend change.

The search input lives under the existing `.fex-tree-header` (a new row
beneath the existing buttons) — opt-in via the user's first keystroke.
The Table/Tree renderer additions are additive in `file_viewer.js`,
dispatched via `fileViewer.render`. Removing them reverts to the
documented placeholder-tab state.

Rollback: `git revert` the merge commit (per proposal §Rollback Plan).

## Open Questions

None. The proposal + spec resolve every product question.

## Next Step

`sdd-tasks` — break this design into atomic, TDD-ordered implementation
units (state shape → search input + walk → filter render → highlight
render → toggle buttons → renderTable → renderTree → CSS).