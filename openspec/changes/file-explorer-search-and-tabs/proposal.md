# Proposal: File Explorer — Search + Complete Placeholder Tabs

## Intent

`file_explorer.js` lines 647–649 mark Table and Tree viewer tabs as
placeholders. CSV / JSON users see a flat `<pre>`; there is no way to
locate a file in a deep research folder without scrolling. This
change adds client-side tree search (filter + highlight + hide-empty)
and completes Table (CSV/TSV via Papa Parse) + Tree (JSON, native)
viewer tabs.

## Scope

### In Scope

- Search input in the left tree header. 200 ms debounce. "X" clear.
  Persisted in `state.explorer.search = { query, mode, hideEmpty }`.
- Mode toggle (icon button):
  - **filter** (default) — hide non-matching rows; auto-expand
    folders whose subtree has matches.
  - **highlight** — keep tree as-is; paint `.fex-row.search-match`.
- "Hide empty folders" toggle (filter only).
- **Table tab** — CSV / TSV via Papa Parse, lazy `loadScriptOnce`,
  sticky `<thead>` + scrollable body.
- **Tree tab** — JSON, ~80-line native collapsible renderer,
  16 px indent / level, type-coloured leaves.

### Out of Scope

- Backend changes (no new endpoints, no schema).
- Upload / edit / rename / delete / drag-drop / multi-select.
- Regex / glob / case-sensitive search options.
- Persisting query across reloads (session-scoped).
- Syntax highlighting in Tree tab. Search across file contents.
- New JS test runner (frontend verified via hand-testable scenarios
  in `tasks.md`).

## Capabilities

### Modified Capabilities

- `research` (delta extends `openspec/specs/research/spec.md`):
  - **ADDED**: Tree search — filter + highlight + hide-empty modes,
    200 ms debounce, persisted in `state.explorer.search`.
  - **ADDED**: Table viewer tab — CSV/TSV via Papa Parse, sticky
    header + scrollable body.
  - **ADDED**: Tree viewer tab — JSON as collapsible tree,
    type-coloured leaves, 16 px indent.
  - **MODIFIED (Multi-format file viewer)** — Table + Tree tab
    buttons dispatch to renderers (csv/tsv → Table, json → Tree).

### New Capabilities

None. Both additions extend the existing `research` capability.

## Approach

**Search.** One pass over `state.explorer.tree.root` builds a flat
`{path, name, type, matches}` list + ancestor-folder set (filter
only). Highlight = class-only, never touches `aria-expanded`.
Debounce via `setTimeout(200)`. Clear restores tree without flipping
user expand/collapse state in highlight mode.

**Table viewer.** Add `Papa` to `CDN_URLS` in `file_viewer.js`;
follow existing `loadScriptOnce` + `target.replaceChildren(...)`.
Render `{ header, data }` into `<table>` with sticky thead.

**Tree viewer.** Native `JSON.parse` + recursive DOM builder.
Object / array nodes are `<details>`/`<summary>`; leaves are typed
rows with type-colour glyphs. Reuses `fex-row` styling; new
`.fex-tree-leaf` adds type tokens from the Tailwind config.

## Affected Areas

| File | Impact |
| --- | --- |
| `web/file_explorer.js` | Modified — search input, mode + hideEmpty toggles, search pass, `search-match` class, Table/Tree tab dispatch. |
| `web/file_viewer.js` | Modified — `Papa` in `CDN_URLS`, add `renderTable` + `renderTree`. |
| `web/state.js` | Modified — `search: { query: "", mode: "filter", hideEmpty: false }` in `state.explorer` + `initialExplorerShape()`. |
| `web/index.html` | Modified — CSS for `.fex-tree-header-search`, `.fex-row.search-match`, `.fex-tree-leaf`; pin `papaparse@5.4.1` CDN URL. |
| `openspec/specs/research/spec.md` | Modified via delta — see Capabilities. |

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Search lags on >1000-file trees | Med | One pass + memoized path lookups; 200 ms debounce. |
| Highlight mode mutates expand/collapse state | Med | Filter is the only mode that auto-expands. |
| Papa Parse CDN fails → CSV opens raw | Low | Same `loadScriptOnce` retry pattern; offline banner covers it. |
| JSON > 10 MB freezes renderer | Med | Cap 50 000 nodes + "Tree truncated — open raw" message. |
| Existing tab wiring only toggles classes, no body re-render | Med | Tab click calls matching renderer after setting state. |

## Rollback Plan

Revert the merge commit. Search field lives under the existing tree
header; Table / Tree renderers are additive in `file_viewer.js`,
dispatched via `fileViewer.render`. Removing them restores the
documented placeholder-tab state. No on-disk data, no schema, no
backend changes — `git revert` is sufficient and safe.

## Dependencies

- `papaparse@5.4.1` from `cdn.jsdelivr.net` (pinned, lazy).
- No backend, npm, or Python package additions.

## Success Criteria

- [ ] Typing filters (or highlights) within 200 ms of stopping;
      matching parents auto-expand in filter mode.
- [ ] Toggling filter ↔ highlight keeps query + selection.
- [ ] "Hide empty folders" hides folders with no matches (filter).
- [ ] Double-clicking `.csv` / `.tsv` shows header + body, header
      pinned, body scrolls vertically.
- [ ] Double-clicking `.json` shows collapsible tree with
      type-coloured leaves.
- [ ] Hand-testable scenarios in `tasks.md` pass on fresh
      `make smoke`; 63-pass baseline unaffected.
- [ ] No console errors; no `Co-Authored-By` trailers; branch
      matches `^feat/[a-z0-9._-]+$`.