# Browser-state Playwright hydration witness

## Objective
Prove in Chromium that the typed browser-state hooks hydrate without console hydration errors or premature storage reads in a static Next export.

## User decision
Implement the Playwright follow-up after the typed browser-state store merged. Keep the witness isolated from production taxonomy consumers.

## Scope
- Mount a dedicated, static-exported hydration probe using the public browser-state hooks.
- Add Chromium coverage for first paint, stored-value rehydration, setter updates, console hydration errors, and storage-read timing.
- Preserve the main route's no-browser-state static-chunk boundary while allowing the isolated probe route.

## Non-goals
- Migrating `TaxonomyTree`, `AppShell`, or any production consumer to browser state.
- Changing `web/`, FastAPI routing, `WEB_DIR`, or the static cutover.
- Changing the browser-state store API or persistence schema.

## Allowed edit surfaces
- `src/modules/browser-state/index.ts`
- `src/modules/browser-state/presentation/HydrationProbe.tsx`
- `src/app/hydration-probe/page.tsx`
- `tests/test_hydration_console.py`
- `tests/test_app_shell_render.py`
- `odd/tasks/browser-state-playwright-hydration.md`

## TDD and delivery
- TDD mode: strict; require observed RED/GREEN evidence.
- Expected authored change: approximately 350 lines.
- Delivery strategy: stacked PR chain, selected by the user after the Chromium fixtures and chunk contracts exceeded the review budget; no commit, push, or PR without explicit user authorization.
- Route: delegated writer; mapping completed by `gentle-ai-explore` under the 4-file rule.

## Tasks
- [x] ODD-BSTATE-PW-001 Add the isolated hydration probe and Chromium contract tests.
  - Test first paint defaults, stored-value rehydration, setter round trip, console hydration failures, and storage read timing.
  - Keep the main route and `TaxonomyTree` free from browser-state imports.
  - Status: complete (RED → GREEN → TRIANGULATE evidence below).
- [x] ODD-BSTATE-PW-002 Independently validate the static export and Chromium witness.
  - Independent verifier passed typecheck, 6 Chromium tests, 35 existing browser-state tests, 21 static-shell tests, and 142 module/layer tests.
  - Parent spot check passed the 6 Chromium tests; `git diff --check` and LSP found no errors.
  - `tests/test_web_toggle.py` retains two base-proven, unrelated legacy 14-vs-17 search-catalog failures; no CI-only prerequisite or Chromium binary limitation remains.
  - Status: complete.

## Acceptance criteria
- `out/hydration-probe.html` renders through an isolated static server in Chromium.
- First paint and rehydration produce no hydration warnings or page errors.
- Stored browser-state values rehydrate after the default first render without warning.
- The probe's setter round trip persists and re-renders without warning.
- The primary route's static chunks remain browser-state free.

## Delivery chain
- Source route: `19dcd5d feat(browser-state): add hydration witness route`.
- Static-export contract: `dafbc30 test(browser-state): add static hydration contract`.
- Route-boundary contract: `6d19fbc test(app-shell): protect hydration probe boundary`.
- Chromium contract: `3a277d1 test(browser-state): verify Chromium hydration`.
- The source-contract slice measured 398 lines after the final split, so the previously accepted +1 contingency was not needed.

## Evidence

### RED — failing test authored before production source
- `tests/test_hydration_console.py` was committed BEFORE
  `src/app/hydration-probe/page.tsx` existed. `pytest
  tests/test_hydration_console.py -v` produced **6 errors** (the
  module-scoped `static_export` fixture failed because `next build`
  did not produce `out/hydration-probe.html`):
  ```
  tests/test_hydration_console.py::test_probe_route_is_statically_exported ERROR
  tests/test_hydration_console.py::test_probe_static_html_uses_typed_defaults ERROR
  tests/test_hydration_console.py::test_probe_first_paint_defaults_have_no_console_errors ERROR
  tests/test_hydration_console.py::test_probe_storage_reads_happen_after_dom_content_loaded ERROR
  tests/test_hydration_console.py::test_probe_rehydrates_stored_values_without_warnings ERROR
  tests/test_hydration_console.py::test_probe_setter_round_trip_persists_and_rerenders ERROR
  ```
  Failure root cause (from `static_export` fixture): `missing
  out/hydration-probe.html — next build did not produce the probe
  route's static HTML. ODD-BSTATE-PW-001 must ship
  `src/app/hydration-probe/page.tsx` so the static export registers
  the route.`

### GREEN — production source + static export + Playwright witness
- `src/modules/browser-state/presentation/HydrationProbe.tsx` — the
  isolated `"use client"` witness component. Uses the four typed
  hooks (`useTheme`, `useTreeSource`, `useLastTaxonId`,
  `useKebabOpenId`) and renders them through stable selectors
  (`data-testid="hydration-probe"`, `data-test-value="theme"`,
  `data-test-value="source"`, `data-test-value="last-taxon-id"`,
  `data-test-value="kebab-open-id"`, plus per-setter
  `data-action` attributes).
- `src/app/hydration-probe/page.tsx` — dedicated route that mounts
  the probe via `import { HydrationProbe } from "@taxa/browser-state";`
  (public barrel, no deep imports). The
  `tests/test_app_shell_render.py::test_probe_page_mounts_browser_state_via_public_barrel`
  test pins the barrel-only wiring.
- `src/modules/browser-state/index.ts` — single-line wiring edit
  (collateral to the new `presentation/HydrationProbe` component):
  `export { default as HydrationProbe } from "./presentation/HydrationProbe";`.
  Without this re-export the dedicated route cannot legally mount
  the probe through the project's `no-restricted-imports` ESLint
  guard (deep paths into `presentation/` are blocked). Existing
  typed-surface exports stay unchanged; the barrel stays the only
  consumer surface for cross-module mounts.
- `pnpm exec next build` produces `out/hydration-probe.html` —
  `next build` route table:
  ```
  Route (app)
  ┌ ○ /
  ├ ○ /_not-found
  └ ○ /hydration-probe
  ```
- `pytest tests/test_hydration_console.py -v -s` → **6 passed**:
  ```
  tests/test_hydration_console.py::test_probe_route_is_statically_exported PASSED
  tests/test_hydration_console.py::test_probe_static_html_uses_typed_defaults PASSED
  tests/test_hydration_console.py::test_probe_first_paint_defaults_have_no_console_errors PASSED
  tests/test_hydration_console.py::test_probe_storage_reads_happen_after_dom_content_loaded PASSED
  tests/test_hydration_console.py::test_probe_rehydrates_stored_values_without_warnings PASSED
  tests/test_hydration_console.py::test_probe_setter_round_trip_persists_and_rerenders PASSED
  ```

### TRIANGULATE — boundary contract + collateral tests
- `tests/test_app_shell_render.py` (allowed edit surface): the old
  blanket `test_out_next_static_chunks_reference_no_browser_state`
  test (which scans EVERY chunk for the alias) is left in place
  (the alias is resolved at build time and never appears in chunks,
  so the test stays a vacuous-but-correct no-op). Three new tests
  pin the per-route boundary contract:
  - `test_out_index_html_chunks_reference_no_browser_state` —
    parses `out/index.html` (extracting `<script src=>` tags + the
    RSC payload's `__next_f.push` entries), then asserts every
    referenced chunk is FREE of the four `taxa.*` storage key
    literals the typed store hard-codes. The main route stays
    browser-state free.
  - `test_probe_route_html_chunks_do_reference_browser_state` —
    parses `out/hydration-probe.html` and asserts at least one
    referenced chunk DOES carry the four `taxa.*` literals (the
    probe is useless otherwise). The probe route is the ONLY place
    the typed store + hooks are allowed to land.
  - `test_probe_page_mounts_browser_state_via_public_barrel` —
    source-level witness that `src/app/hydration-probe/page.tsx`
    imports through `@taxa/browser-state` (barrel) and references
    `HydrationProbe`; a deep import into `presentation/` would
    break the modular monolith's layer rule.
- `pytest tests/test_app_shell_render.py -q` → **21 passed** (18
  pre-existing + 3 new boundary tests).
- `pytest tests/test_browser_state_keys.py
  tests/test_browser_state_hydration_guard.py -q` → **35 passed**
  (no regressions; the probe lives in `browser-state/presentation/`
  so the existing 4-read / 4-write / 4-subscribe /
  `localStorage`-only-in-`store.ts` storage-ownership contracts
  stay intact).

### Verification (full required suite)
| Command | Result |
| --- | --- |
| `pnpm exec tsc --noEmit` | exit 0 (no errors) |
| `python -m playwright install chromium` | exit 0 (chromium-1234 already installed; dry-run reported `INSTALLATION_COMPLETE`) |
| `pytest tests/test_hydration_console.py -v -s` | 6 passed |
| `pytest tests/test_browser_state_keys.py tests/test_browser_state_hydration_guard.py -q` | 35 passed |
| `pytest tests/test_app_shell_render.py -q` | 21 passed |
| `pytest tests/test_web_toggle.py -v -s` | 15 passed, **2 pre-existing failures** (`test_search_tab_renders_with_14_links`, `test_search_engines_rendered_as_button_grid`) — both expect **14** search-engine buttons; the live `web/` ships **17** (verified by running the same tests on a clean stash of this branch). These failures predate ODD-BSTATE-PW-001 (they assert against the legacy `web/` search-engine catalog, which is outside the ODD-BSTATE-PW-001 allowed edit surfaces and unrelated to the browser-state probe). |
| `pytest tests/test_module_layers.py tests/test_no_restricted_imports.py -q` | 142 passed |
| Independent verifier + parent spot check | PASS — 6 Chromium tests, `git diff --check`, and zero LSP errors in the probe/barrel files |

### Boundary witness — what the chunks prove
- `out/index.html` references 8 JS chunks; **0** carry the four
  `taxa.*` storage key literals. The main route's static chunk
  boundary stays clean.
- `out/hydration-probe.html` references chunks; **1** chunk
  (`out/_next/static/chunks/3a7n5x_-e0n56.js`) carries all four
  `taxa.*` storage key literals (the typed store + hooks, inlined
  by Turbopack after the path alias `@taxa/browser-state` was
  resolved at build time). The probe route bundles browser-state
  code as expected.

### Storage read timing — instrumentation witness
- `Storage.prototype.getItem` is wrapped via `context.addInitScript`
  (`tests/test_hydration_console.py::INIT_SCRIPT`) BEFORE any user
  script runs. The wrapper records `{key, t: performance.now()}`
  for every read.
- After first paint + hydration, the first recorded read of any
  browser-state key happens at or after `DOMContentLoaded` — the
  static HTML render (which happens at build time) carries the
  typed defaults literally (verified by
  `test_probe_static_html_uses_typed_defaults`), so no storage
  read is required during the first paint.
