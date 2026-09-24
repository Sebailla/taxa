# Close 2 new P0s from re-critique — explorer search shortcut + footer legend

## Objective

The 2026-09-23T18-52-32Z re-critique (28/40, post-PR #382 + #383) identified 2 new P0s the rebuild introduced:

1. **Global search is a visual no-op on `/explorer`** — `src/modules/research/presentation/Explorer.tsx:131` destructures `searchQuery: _searchQuery, onSearchQueryChange: _onSearchQueryChange` (discarded). Header input renders on every route with `placeholder="Search taxa… (Cmd+K)"`, takes focus on `Cmd+K`/`/`, but produces no results dropdown on `/explorer`.
2. **Footer shortcut legend documents `/` as opening Help — implementation focuses global search** — `src/modules/app-shell/presentation/AppShellFooter.tsx:51` reads `<kbd>/</kbd> Help`. `src/modules/app-shell/presentation/AppShellGlobalSearch.tsx:88-92` wires `/` to focus the global search input. Footer contradicts actual contract.

This branch closes both P0s. User-confirmed direction (2026-09-23):

- **Search contract (P0 #1)**: route-aware placeholder + visual disable. The header input on `/explorer` becomes "visible but inert" with explicit copy ("Taxa search on Classification only"). The explorer's local file search stays primary for that route.
- **Shortcut legend (P0 #2)**: `?` = Help, `/` = Search (Vim/GitHub/Linear/GitHub/Algolia/Slack platform conventions). Wire `?` to navigate to `/help`. Update footer legend + help page shortcut map to sync.

## User decision

- Both P0s in one PR scope (single feature branch).
- Push + PR creation + merge remain the user's decisions.

## Scope

- `src/modules/app-shell/presentation/AppShellGlobalSearch.tsx` — accept `currentRoute` prop; render route-aware placeholder; add `?` keyboard shortcut that navigates to `/help`.
- `src/modules/app-shell/presentation/AppShellFooter.tsx` — update shortcut legend to include `? Help` and clarify the `/` shortcut is for search (not help).
- `src/app/help/page.tsx` — sync shortcut map to reflect `?` opens Help + `/` focuses search.
- `src/app/page.tsx` + `src/app/_components/HomeClient.tsx` — pass `currentRoute="classification"` to AppShell.
- `src/app/explorer/page.tsx` — pass `currentRoute="explorer"` to AppShell (the input becomes inert with explicit copy).
- `src/app/settings/page.tsx` — pass `currentRoute="settings"`.
- `src/app/hydration-probe/page.tsx` — pass `currentRoute="hydration-probe"` (the gate will render, the global search is hidden inside the gate fallback).
- `src/app/_not-found` / `src/app/not-found.tsx` — pass `currentRoute="not-found"`.
- `src/modules/research/presentation/Explorer.tsx` — no code change (the local file search stays primary; the header input becomes inert via the `currentRoute="explorer"` prop on AppShell).
- `tests/test_app_shell_render.py` — add tests for placeholder-by-route + `?` shortcut + footer legend.
- `tests/test_help_route_renders.py` (if not exists; otherwise extend) — assert the shortcut map reflects the new contract.

## Non-goals

- Wiring the global search input to the explorer's file search (deferred — requires rewriting FileTree's DOM-mutation search to render-pure; that's the original P1 from the 2026-09-23 critique that the user chose to defer).
- Removing the AppShell duplicate skip-link (P1 from re-critique; out of scope here).
- Per-tree-row density collapse (P1 from re-critique; out of scope).
- Source-selector hoist (P2 from re-critique; out of scope).
- Detail-panel sticky-breakpoint fix (P2 from re-critique; out of scope).
- Design-system extract (P1 from original critique; out of scope).

## TDD discipline

Per task:

### ODD-EXP-001 — Route-aware placeholder + visual disable

1. FIRST add new tests in `tests/test_app_shell_render.py`:
   - `test_app_shell_search_placeholder_is_route_aware` — asserts the rendered `<input>` placeholder matches the route:
     - `/`, `/help`, `/settings`, `/not-found`, `/hydration-probe` → `"Search taxa…  (Cmd+K)"`
     - `/explorer` → `"Taxa search is on the Classification route  (Cmd+K)"` (or similar — see copy below)
   - `test_app_shell_search_input_is_inert_on_explorer` — asserts the input is `aria-disabled="true"` or carries `data-app-shell-search-inert=""` on `/explorer` only. The visual disable mirrors the contract: present but inert.
   - `test_explorer_page_passes_current_route` — asserts `src/app/explorer/page.tsx` passes the `currentRoute="explorer"` prop to AppShell.
2. Run new tests to confirm RED.
3. Implement:
   - Add `currentRoute?: "classification" | "explorer" | "help" | "settings" | "hydration-probe" | "not-found"` prop to `AppShellProps`.
   - In `AppShellGlobalSearch`, branch on `currentRoute`:
     - `"explorer"` → render placeholder `"Taxa search is on the Classification route"` + `aria-disabled="true"` + a `data-app-shell-search-inert=""` attribute + visual `cursor: not-allowed` + slightly reduced opacity (e.g. `opacity-60`).
     - Other routes → render the existing `"Search taxa…  (Cmd+K)"` placeholder.
   - Update the `placeholder` + `aria-disabled` + data-attr based on the prop.
   - Thread `currentRoute` through `AppShell.tsx` → `AppShellHeader.tsx` → `AppShellGlobalSearch.tsx`.
   - Update each page (`page.tsx`, `explorer/page.tsx`, `help/page.tsx`, `settings/page.tsx`, `hydration-probe/page.tsx`, `not-found.tsx`) to pass `currentRoute={...}`.
   - The `HydrationProbeGate` is mounted inside `hydration-probe/page.tsx` so the global search isn't visible there; pass `currentRoute="hydration-probe"` for completeness even though it's hidden.
4. Re-run new tests → GREEN.
5. Confirm regression sweep on PR #382 protected test files stays GREEN.

### ODD-EXP-002 — Wire `?` shortcut + sync footer + sync help page

1. FIRST add new tests in `tests/test_app_shell_render.py`:
   - `test_app_shell_shortcut_question_navigates_to_help` — Playwright: press `?` from any non-editable context, assert the URL changes to `/help` OR the help link gets focus.
   - `test_app_shell_footer_shortcut_legend_says_question_for_help` — source-level: `AppShellFooter.tsx` carries the literal `<kbd>?</kbd>` + the literal `Help` adjacent (in the same `<kbd>` / `<span>` run) + the literal `<kbd>/</kbd>` + the literal `Search` adjacent (NOT adjacent to `Help`).
   - `test_app_shell_shortcut_slash_focuses_search` — Playwright: press `/` from a non-editable context on `/`, assert the global search input gets focus.
   - `test_help_page_shortcut_map_lists_question_for_help` — source-level: `src/app/help/page.tsx` shortcut map includes an entry for `?` → "Open Help" (or similar) AND the `/` entry says "Focus the global search input" (NOT "Open Help").
2. Run new tests to confirm RED.
3. Implement:
   - In `AppShellGlobalSearch.tsx`, add a `useEffect` keydown listener that, on `?` keypress (with the same "not in editable field" guard as the `/` shortcut), uses Next.js `useRouter().push("/help")` to navigate.
   - Update `AppShellFooter.tsx` shortcut legend from current `"Cmd+K Search · / Help · Esc Close"` to `"Cmd+K Search · / Search · ? Help · Esc Close"` (or a more readable form — see copy notes).
   - Update `src/app/help/page.tsx` shortcut map (around lines 84-129) to include a `?` entry that says "Open this help page" + correct the `/` entry to say "Focus the global search input".
4. Re-run new tests → GREEN.
5. Confirm regression sweep.

## Constraints

- DO NOT modify any implementation file outside the allowed edit surfaces.
- DO NOT touch the PR #382 protected test files (`test_visible_taxonomy_tree.py`, `test_hydration_console.py`, `test_browser_state_keys.py`, `test_research_styles.py`, `test_search_engine_consumer_manifest.py`).
- The placeholder copy on `/explorer` must be HONEST about why the input is inert — no fake "search files" placeholder that doesn't work. Suggested copy: `"Taxa search lives on Classification (Cmd+K)"` (terse, links the actual capability).
- The footer copy must clearly distinguish the `/` (search) and `?` (help) shortcuts — no single `· / Help ·` cluster that conflates them.
- The `?` keyboard shortcut handler must respect the same "skip when in editable field" guard the `/` handler uses. A researcher typing in any `<input>`, `<textarea>`, or `[contenteditable]` element must NOT trigger the `?` → help navigation.
- The chunk-boundary contract (`test_out_index_html_chunks_permit_only_tree_source_key`) MUST stay green. The new `currentRoute` prop on AppShell does NOT touch browser-state; the new `?` handler uses `useRouter` from `next/navigation` (a Server Component import, but the handler runs in a Client Component island — should be fine).
- The new keyboard handler must use `useRouter` from `next/navigation`, not `window.location.href` — `useRouter` triggers a client-side navigation that preserves React state (vs. a hard reload).

## Allowed edit surfaces

src/modules/app-shell/presentation/AppShell.tsx
src/modules/app-shell/presentation/AppShellHeader.tsx
src/modules/app-shell/presentation/AppShellFooter.tsx
src/modules/app-shell/presentation/AppShellGlobalSearch.tsx
src/modules/app-shell/index.ts
src/app/page.tsx
src/app/_components/HomeClient.tsx
src/app/explorer/page.tsx
src/app/help/page.tsx
src/app/settings/page.tsx
src/app/hydration-probe/page.tsx
src/app/not-found.tsx
tests/test_app_shell_render.py

## Files referenced (read-only)

src/app/layout.tsx (already wires the skip-link; no change needed)
src/app/globals.css (may need a tiny `cursor: not-allowed` + `opacity-60` rule for the inert state — see Implementation notes)

## Test plan

- All 4 new tests for ODD-EXP-001 + ODD-EXP-002 PASS.
- Full regression sweep on PR #382 protected test files stays GREEN (`test_app_shell_render`, `test_visible_taxonomy_tree`, `test_hydration_console`, `test_browser_state_keys`, `test_research_styles`, `test_search_engine_consumer_manifest`, `test_help_route_renders`).
- `npx --no-install next build` → exit 0. The build emits the 6 routes unchanged.
- `git diff --check` clean.

## Acceptance criteria

- Global search input on `/explorer` shows the inert placeholder + `aria-disabled="true"` + `data-app-shell-search-inert=""` + reduced opacity + `cursor: not-allowed`. Pressing `?` on `/explorer` navigates to `/help`. Pressing `/` on `/explorer` does NOT focus the search (input is disabled).
- Pressing `?` on any non-editable context navigates to `/help`. Pressing `/` focuses the global search input (on routes where the input is enabled).
- Footer legend reads `"Cmd+K Search · / Search · ? Help · Esc Close"` (or equivalent that clearly separates the `/` (search) and `?` (help) shortcuts).
- Help page shortcut map includes an entry for `?` → "Open this help page" AND the `/` entry says "Focus the global search input" (NOT "Open Help").
- The `/explorer` page still works as before (its local file-search in the tree pane is unchanged).
- All 274+ tests still pass after the work.

## Risks + follow-ups (out of scope)

- Wiring the global search to the explorer's file search is a separate P1 from the original critique (FileTree DOM-mutation → render-puro). Out of scope for this branch.
- Removing the AppShell duplicate skip-link is a separate P1 from the re-critique. Out of scope.
- The `?` shortcut conflicts with Vimium's "?" hint mode — a power user running Vimium may need to press Escape first. Acceptable trade-off; documented behavior.
- The new placeholder copy + visual disable on `/explorer` are visible UX changes — they may attract user feedback. Acceptable.

## Rollback

If anything fails, run `git restore src/modules/app-shell/presentation/AppShell.tsx src/modules/app-shell/presentation/AppShellHeader.tsx src/modules/app-shell/presentation/AppShellFooter.tsx src/modules/app-shell/presentation/AppShellGlobalSearch.tsx src/modules/app-shell/index.ts src/app/page.tsx src/app/_components/HomeClient.tsx src/app/explorer/page.tsx src/app/help/page.tsx src/app/settings/page.tsx src/app/hydration-probe/page.tsx src/app/not-found.tsx tests/test_app_shell_render.py` from `/Users/sebailla/Developer/taxa`. The branch + develop stay intact.