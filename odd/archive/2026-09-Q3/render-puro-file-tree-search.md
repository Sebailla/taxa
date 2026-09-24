# Render-puro refactor — FileTree search

## Objective

Replace the FileTree search's DOM-mutation pattern (post-render `useEffect` that mutates `aria-expanded`, chevron glyphs, `style.display`, and `.search-match` class via `querySelector` lookup) with a render-puro derivation (visibility + class come from props at render time, no `useEffect`).

Closes the LAST remaining P1 from the impeccable re-critique (2026-09-23 + re-critique): *Explorer search DOM-mutation → render-puro*.

## Why

The current implementation (W6.2 contract) mirrors the legacy `web/file_explorer.js::applySearchToTree(host, annotation)` byte-for-byte — an imperative post-render `useEffect` that walks `data-row-wrap` elements and toggles DOM state. This works but:

- **Non-deterministic between render and effect commit**: a fast-typing user can observe stale matches.
- **90 LOC of imperative code** (`applyFilterMutation` + `applyHighlightMutation` + `restoreTreeMutation` + `cssEscape` helper + the `useEffect` orchestrator) that React renders around rather than through.
- **Test complexity**: 3 tests in `tests/test_research_explorer_mount.py` pin the mutation contract *literally* (reference `restoreTreeMutation` by name) — they have to use Playwright `waitForFunction` patterns instead of pure DOM observation.

The render-puro refactor derives visibility + classes from `(tree, expanded, searchAnnotation, searchMode, searchHideEmpty)` at render time. The user-visible contract (data attributes, ARIA, classes, behavior) stays byte-for-byte identical; only *how* the contract is *applied* changes.

## External contract (must stay byte-for-byte)

- `data-row-wrap="folder" | "file"` on every wrap
- `data-folder-path`, `data-file-path` on every row
- `aria-expanded="true" | "false"` on folder rows (the auto-expand flip is the SAME outcome, just derived from props instead of DOM mutation)
- `data-search-empty=""` on the EmptyState wrapper when filter+hideEmpty+zero matches
- `.search-match` class on highlight-mode matches (idempotent toggle)
- `role="button"`, `tabIndex={0}`, `aria-label` per row (unchanged)
- Selection (`.selected` class) survives every keystroke (unchanged)

## Current mutation surface (to be removed)

| Function | Lines in FileTree.tsx | What it does |
|---|---|---|
| `cssEscape` | ~358-364 | Polyfill for `CSS.escape` (no longer needed) |
| `applyFilterMutation` | ~366-413 | Sets `aria-expanded="true"`, flips chevron glyph, sets folder icon, then `style.display = "none"` on non-match wraps |
| `applyHighlightMutation` | ~430-470 | Toggles `.search-match` class on matching rows |
| `restoreTreeMutation` | ~479-489 | Un-hides all wraps + removes `.search-match` |
| `useEffect` + `treeRootRef` | ~525-545 | Orchestrator: dispatches based on (annotation, mode, hideEmpty) |

## Strategy

### Phase A — Derivation helpers (pure functions, new)

Three pure helpers that derive the relevant render state from props. These are internal to `FileTree.tsx` (not exported):

1. `deriveExpandedSet(expanded, searchAnnotation, searchMode): ReadonlySet<string>`
   - When `searchAnnotation === null` or `searchMode === "highlight"`: returns `expanded` unchanged (highlight never touches expansion)
   - When `searchMode === "filter"`: returns `expanded ∪ searchAnnotation.ancestors` (auto-expand every ancestor chain member)

2. `isRowVisible(path, searchAnnotation, searchMode): boolean`
   - When `searchAnnotation === null`: `true` (no filter active, every row renders)
   - When `searchMode === "filter"`: `searchAnnotation.matches.has(path) || searchAnnotation.ancestors.has(path)`
   - When `searchMode === "highlight"`: `true` (highlight only paints class, never hides)

3. `rowHasMatchClass(path, searchAnnotation, searchMode): boolean`
   - When `searchAnnotation === null`: `false`
   - When `searchMode === "highlight"`: `searchAnnotation.matches.has(path)`
   - When `searchMode === "filter"`: `false` (filter hides non-matches via `display: none` / render-time conditional; class is highlight-only)

### Phase B — Recursive walker update

Modify `renderChildren` and `renderChildrenShim` so they:
- Accept the derived `expandedSet` (instead of the raw `expanded` prop)
- Compute `wrapDisplay` per child: omit children whose path is not visible (when filter mode)
- Compute `rowClassName`: include `"search-match"` when `rowHasMatchClass(child.path, annotation, mode)` returns `true`
- Compute `aria-expanded` + chevron glyph from `expandedSet.has(child.path)` instead of `expanded.has(child.path)`

The conditional render (`{isExpanded ? <div className="fex-children">...</div> : null}`) already supports render-time toggle — we just change the input from raw `expanded` to the derived set.

### Phase C — FileTree default export update

Replace the `useEffect` orchestrator + `treeRootRef` with:
- Compute `derivedExpanded = deriveExpandedSet(expanded, searchAnnotation, searchMode)` at render time
- Pass `derivedExpanded` into `renderChildrenShim` (the synthetic-root walker)
- The `showSearchEmpty` boolean (already derived at render time) controls the JSX conditional
- No `useEffect`, no `treeRootRef`

### Phase D — Test updates

Three tests in `tests/test_research_explorer_mount.py` reference `restoreTreeMutation` literally:
- Lines ~740, ~764, ~810

Refactor them to test the SAME user-visible behavior (no matches → EmptyState, search clear → tree restored, etc.) via the **rendered DOM contract** (data attributes + ARIA + classes), not the internal mutation function name. The tests should now be deterministic without `waitForFunction` timing tricks.

### Phase E — Playwright verification

Manual verification of filter mode + highlight mode + clear query, via the existing Playwright test suite (`tests/test_research_explorer_mount.py`).

## Non-goals

- No changes to `Explorer.tsx`, `explorer-state.ts`, or `SearchAnnotation` shape — the props surface stays identical.
- No changes to the user-visible behavior (keyboard nav, click handlers, double-click handlers).
- No changes to selection state (`selectedPath`, `internalSelectedFolder`) — those survive every keystroke (unchanged contract).
- No deletion of `.search-match` CSS rule (the class still applies in highlight mode).

## Constraints

- The 3 derivation helpers MUST be pure (no DOM lookup, no refs, no `useState`/`useEffect`).
- The refactor MUST NOT change `FileTreeProps` (the public surface stays the same so `Explorer.tsx` is unchanged).
- The refactor MUST preserve the `cssEscape` polyfill REMOVAL — verify no other consumer uses it.
- Tests that pin user-visible behavior (data attributes + ARIA + classes) MUST keep passing.
- The `fex-tree-root` outer wrapper stays (`data-tree-root=""` or similar — verify which data attribute the tests check).
- Do NOT touch `Explorer.tsx` or `explorer-state.ts` — the refactor is internal to `FileTree.tsx`.
- Do NOT commit / push / open PR — parent owns the local commit authorization.

## Allowed edit surfaces

- `src/modules/research/presentation/FileTree.tsx`
- `tests/test_research_explorer_mount.py`

## Acceptance criteria

- `grep -nE "applyFilterMutation|applyHighlightMutation|restoreTreeMutation|cssEscape|treeRootRef" src/modules/research/presentation/FileTree.tsx` returns 0 matches
- `grep -nE "restoreTreeMutation" tests/test_research_explorer_mount.py` returns 0 matches (the literal-name references update to contract assertions)
- `pytest tests/test_research_explorer_mount.py -q` → 0 failed
- `pytest tests/test_research_styles.py -q` → 0 failed
- `pytest tests/test_module_layers.py tests/test_no_restricted_imports.py -q` → 0 failed (layer rules still hold)
- `pnpm exec tsc --noEmit` → exit 0
- `pnpm exec next build` → exit 0 (static export builds clean, all 5 routes register)
- Playwright headless verification: filter mode hides non-matches + auto-expands ancestors, highlight mode paints `.search-match` without touching expansion, clear query restores the tree

## Risks + follow-ups

- The `fex-tree-root` outer wrapper: the current code applies `ref={treeRootRef}` directly to it (no `data-tree-root` attribute in the JSX). Verify whether tests check for `data-tree-root` or for `.fex-tree-root` class — if data attribute is checked, the refactor must add it.
- The render-puro derivation means the tree is computed on EVERY render (currently the effect runs only when annotation flips). With a recursive tree of ~1000 rows this could be a perf concern — but the recursion only walks visible folders (collapsed folders skip), so the actual cost stays bounded.
- The `EmptyState` JSX already replaces the imperative `showSearchEmptyMutation` helper per ODD-EXP-PHASE2-004 — confirm the EmptyState wrapper still has `data-search-empty=""` after the refactor.

## Rollback

If anything fails or you need to abandon the change, run `git restore src/modules/research/presentation/FileTree.tsx tests/test_research_explorer_mount.py` from the feature branch root. The branch + develop stay intact.