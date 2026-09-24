# Persist TaxonomyTree active source

## Objective
Migrate TaxonomyTree's CoL/WoRMS/Freshwater selector from local state to typed browser state while preserving its source-switch reset cascade.

## User decision
Proceed with the first production browser-state consumer after the isolated Chromium hydration witness merged.

## Scope
- Replace only TaxonomyTree `activeSource` local state with the public `useTreeSource` hook.
- Split the typed browser-state hook/store implementation by storage key so the primary route can bundle only the tree-source chain.
- Persist a source selection across reloads without changing first-render default behavior.
- Enforce per-route static chunks: the primary route may carry `taxa.tree.source` and must exclude the theme, selected-ID, and kebab-ID key literals.
- Add source-level and real TaxonomyTree Chromium persistence coverage.

## Non-goals
- Persisting focused/selected taxon IDs, kebab state, active tabs, caches, or theme.
- Changing TaxonomyTree's source-reset cascade, legacy `web/`, FastAPI, or static cutover.
- Removing the isolated hydration probe.

## Allowed edit surfaces
- `src/modules/taxonomy/presentation/TaxonomyTree.tsx`
- `src/modules/browser-state/application/`
- `src/modules/browser-state/infrastructure/`
- `src/modules/browser-state/index.ts`
- `src/modules/browser-state/tree-source.ts`
- `src/modules/browser-state/presentation/HydrationProbe.tsx`
- `src/app/hydration-probe/page.tsx`
- `tests/test_visible_taxonomy_tree.py`
- `tests/test_app_shell_render.py`
- `tests/test_browser_state_keys.py`
- `tests/test_browser_state_hydration_guard.py`
- `tests/test_module_layers.py`
- `tests/test_taxonomy_tree_source_persistence.py`
- `odd/tasks/browser-state-taxonomy-active-source.md`

## TDD and delivery
- TDD mode: strict; require observed RED/GREEN evidence.
- Expected authored change: approximately 175 lines.
- Delivery strategy: `ask-on-risk`; no commit, push, or PR without explicit user authorization.
- Route: delegated writer; strict-continuation mapping completed by `gentle-ai-explore` under the 4-file rule.

## Tasks
- [x] ODD-BSTATE-TAX-001-A Split browser-state hooks and stores by key.
  - Preserve the public barrel contract while isolating each key's hook and storage implementation.
  - Keep reset semantics and the hydration probe's four-hook coverage intact.
  - Strict TDD: observe failing structural tests before adapting their module-path contract; then pass browser-state, layer, and import-boundary checks.
  - Route: delegated writer (multi-file write rule).
  - **Status**: GREEN. Each storage key now owns its own hook + store file; the monolithic `useBrowserStateKey.ts` + `store.ts` are retired (a regression that re-introduces them trips `test_monolithic_modules_are_retired`); the four hooks re-export through the public barrel; `reset()` is an explicit aggregate module.
- [x] ODD-BSTATE-TAX-001-B Enforce the strict primary-route chunk boundary.
  - Replace the pragmatic hook-call-site assertion with literal absence checks for `taxa.settings.theme`, `taxa.tree.lastTaxonId`, and `taxa.tree.kebabOpenId` in every chunk referenced by `out/index.html`.
  - Preserve the positive `taxa.tree.source` witness.
  - Route: delegated writer (multi-file write rule).
  - **Status**: RESOLVED by ODD-BSTATE-TAX-002. The hardened test (`test_out_index_html_chunks_permit_only_tree_source_key`) — literal absence + positive witness — was authored under ODD-BSTATE-TAX-001-B and observed RED on the pre-entry-point bundle (all four key literals present in the shared `08ei48_e3ijfx.js` chunk referenced by both `index.html` and `hydration-probe.html`). The test stays unchanged under ODD-BSTATE-TAX-002; it now observes GREEN because the dedicated `@taxa/browser-state/tree-source` entry point makes Turbopack split the typed-source chain into a separate chunk that the main route references without the forbidden key files. The per-key module split (`ODD-BSTATE-TAX-001-A`) was necessary but not sufficient; the dedicated entry point (`ODD-BSTATE-TAX-002`) is what turns the strict witness green without touching `package.json` or `domain/keys.ts`.
- [x] ODD-BSTATE-TAX-001-C Add real selector-specific Chromium persistence coverage.
  - Exercise the main TaxonomyTree selector: choose WoRMS, confirm `taxa.tree.source`, reload, and prove WoRMS remains active without hydration warnings or page errors.
  - Confirm an empty-store first render begins at CoL; include Freshwater only when fixture data exposes it.
  - Route: delegated writer (multi-file write rule).
  - **Status**: GREEN. Four new Chromium assertions in `tests/test_taxonomy_tree_source_persistence.py` cover (1) `out/index.html` is statically produced, (2) the static HTML renders the loading state without leaking a stored source value, (3) empty-store first render begins at CoL with no console / page errors, and (4) click WoRMS persists `taxa.tree.source`, reloads, and rehydrates back to WoRMS without console errors. Route-intercept mocks fulfil `/api/domains` with a synthetic root taxon that has both CoL + WoRMS identifiers so the selector stays mounted across the source switch.
- [x] ODD-BSTATE-TAX-002 Separate public entry point for the typed-source chain.
  - Keep the aggregate `@taxa/browser-state` barrel for the hydration probe; create the dedicated `@taxa/browser-state/tree-source` entry point containing ONLY the typed tree-source surface; migrate TaxonomyTree to that entry point so the main route's chunks carry `taxa.tree.source` and exclude the three forbidden key literals.
  - Strict TDD: observed RED → GREEN cycle on the entry-point presence test + the legacy-import-rejection test + the chunk-boundary witness.
  - **Status**: GREEN. The new `src/modules/browser-state/tree-source.ts` entry point re-exports only `useTreeSource`, the `TreeSource` type, and `DEFAULT_TREE_SOURCE`. `TaxonomyTree.tsx` now imports `useTreeSource` from `@taxa/browser-state/tree-source`. Turbopack now produces TWO separate chunks: `out/_next/static/chunks/2k91wskdsbu4m.js` (only `taxa.tree.source`) referenced by `out/index.html`, and `out/_next/static/chunks/3uwpekuzsbehu.js` (all four keys) referenced by `out/hydration-probe.html`. The strict chunk-boundary witness turns green without touching `package.json` or `domain/keys.ts` because the typed-source chain no longer reaches `domain/keys.ts` at runtime (type-only import) and the forbidden store files are not pulled in by the dedicated entry point.
- [~] ODD-BSTATE-TAX-003 Independently validate the new entry-point boundary and tree persistence.
  - Confirm typecheck, active-source persistence, strict per-key static chunk boundaries with the new entry point, probe regression, browser-state contracts, the new selector E2E, and the new module-layer carve-out.
  - Status: GREEN, independently validated. The duplicate parametrized-test shadowing defect was repaired and independently confirmed (41 collected; four focused cases pass; 62 browser-state checks pass; 199 visible-tree checks pass; four selector E2E checks pass; 144 layer/import checks pass; TypeScript is clean). After the user-authorized release of the transient Turbopack worker, the previously blocked build-dependent subsets also passed: `tests/test_app_shell_render.py` (22 passed, including the strict literal-level chunk witness) and `tests/test_hydration_console.py` (6 passed). No final check is skipped or pending.

## Acceptance criteria
- CoL/WoRMS/Freshwater selection persists in `taxa.tree.source` across reload.
- First client render retains the typed default `col` and emits no hydration warnings.
- The main route bundles only `taxa.tree.source` from browser state; theme, selected ID, and kebab ID remain absent.
- `handleSourceChange` keeps its existing focused/selected/cache/kebab reset behavior.

## Strict chunk-boundary design

The user rejected the prior pragmatic hook-call-site relaxation. The strict
contract is now owned by this continuation: every chunk referenced by
`out/index.html` must include `taxa.tree.source` and exclude the literal keys
`taxa.settings.theme`, `taxa.tree.lastTaxonId`, and
`taxa.tree.kebabOpenId`.

**Design**: retain the aggregate `@taxa/browser-state` barrel for the
hydration probe, but expose a dedicated public
`@taxa/browser-state/tree-source` entry point for the production tree. The
main route imports only that entry point, allowing Turbopack to retain the
tree-source chain and discard the three unrelated chains instead of creating a
shared aggregate-barrel chunk with the probe. `reset()` remains an explicit
aggregate module for consumers that need all keys; the main route must not
import it. The user explicitly authorized the one-line module-layer guard
extension required to admit `tree-source.ts`. No `package.json` side-effects
declaration or dynamic probe import is authorized.

## Strict-continuation decision
The user explicitly authorized this strict continuation and selected **separate
public entry points** over a `package.json` `sideEffects` declaration or probe
route isolation. The user also authorized the narrow `tests/test_module_layers.py`
guard extension required for `tree-source.ts`. Preserve the existing root barrel
contract. Do not commit, push, or publish without a new explicit user decision.

## Delivery
- Strategy: feature-branch chain with documented size exceptions. The strict work units cannot be split below the 400-line review budget without separating behavior from its proofs.
- Tracker branch: `feat/browser-state-active-tree-source-tracker` (targets `develop`; no production diff).
- Child 1: `5edaf81` — `refactor(browser-state): split typed state by key`; per-key runtime split and its structural/hydration contract. Size exception: 2,307 authored diff lines.
- Child 2: `96b6ba6` — `feat(taxonomy): persist active tree source`; dedicated entry point, TaxonomyTree migration, strict static boundary, and module/public-surface checks. Size exception: 815 authored diff lines.
- Child 3: `e7963cf` — `test(taxonomy): cover source selector persistence`; Chromium selector persistence witness. Size exception: 782 authored diff lines.
- Delivery status: published as a feature-branch chain for approved issue #74. Tracker: #342 (`develop`, draft); child 1: #343 (`refactor/browser-state-per-key` → tracker, `type:chore` because the repository has no `type:refactor` label); child 2: #344 (`feat/taxonomy-tree-source` → child 1, `type:feature`); child 3: #346 (`test/taxonomy-tree-source-persistence` → child 2, `type:chore`; supersedes conflicted #345). Every active PR links `Closes #74`; merge remains a separate user decision.

## Evidence
- Feature branch: `feat/browser-state-active-tree-source`.
- ODD-BSTATE-TAX-001-A (GREEN) — Strict-TDD observed RED → GREEN cycle for:
  - `test_canonical_file_present[path3..path11]` (9 cases — RED before the per-key
    `application/useTheme.ts` + `useTreeSource.ts` + `useLastTaxonId.ts` +
    `useKebabOpenId.ts` + `infrastructure/storeTheme.ts` +
    `storeTreeSource.ts` + `storeLastTaxonId.ts` + `storeKebabOpenId.ts` +
    `reset.ts` files existed; GREEN after the implementation).
  - `test_monolithic_modules_are_retired` (RED before the
    `useBrowserStateKey.ts` + `store.ts` monolithic files were deleted; GREEN
    after).
  - `test_application_hook_can_import_react_but_not_localstorage[path*]` (4 cases —
    RED before each per-key hook existed; GREEN after — each hook is hydration-
    safe and free of `localStorage` references).
  - `test_infrastructure_per_key_store_has_storage_calls[path*]` (4 cases — RED
    before each per-key store existed; GREEN after — each store owns its own
    `localStorage` calls).
  - `test_browser_state_infrastructure_owns_local_storage_calls` (RED before the
    per-key split; GREEN after — only `infrastructure/store<X>.ts` + `reset.ts`
    carry `localStorage.*` references).
  - `test_browser_state_module_has_exactly_four_read_sites`,
    `test_browser_state_module_has_at_least_four_write_sites`,
    `test_browser_state_module_has_four_subscribe_sites`,
    `test_browser_state_module_has_reset_remove_item_sites` (all 4 GREEN —
    re-export group aggregates each key's per-key files, so the four-read /
    four-write / four-subscribe / four-removeItem invariants stay in force
    across the split).
  - `test_compiled_browser_state_passes_runtime_contract` (was RED because the
    single-file path produced a single `store.js`; now compiles + runs the
    runtime harness against four per-key `.js` modules + `reset.js` — GREEN).
  - `test_hook_does_not_touch_localstorage[path*]`,
    `test_hook_uses_use_sync_external_store[path*]`,
    `test_hook_uses_client_directive[path*]`,
    `test_hook_file_present[path*]`,
    `test_per_key_hook_signature_returns_typed_value[theme|tree_source|last_taxon_id|kebab_open_id]`
    (the 4×4 hydration-guard sweep over per-key hook files — RED before
    per-key hook files existed; GREEN after the split + the per-hook file
    pin).
- ODD-BSTATE-TAX-001-B (PARTIAL → RESOLVED by ODD-BSTATE-TAX-002) — Strict-TDD
  observed RED on the prior bundle (before the dedicated entry point landed):
  - `test_out_index_html_chunks_permit_only_tree_source_key` (HARDENED with
    literal-absence checks for `taxa.settings.theme`, `taxa.tree.lastTaxonId`,
    `taxa.tree.kebabOpenId` AND a positive `taxa.tree.source` witness):
    RED. Observed offending (chunk, key) pairs on the pre-entry-point bundle:
    `[('08ei48_e3ijfx.js', 'taxa.settings.theme'),
     ('08ei48_e3ijfx.js', 'taxa.tree.lastTaxonId'),
     ('08ei48_e3ijfx.js', 'taxa.tree.kebabOpenId')]`.
    The shared 5.7 KB chunk `08ei48_e3ijfx.js` was referenced by
    BOTH `out/index.html` AND `out/hydration-probe.html`; Turbopack
    inlined all four per-key store implementations in it because the
    probe route legitimately needs all four chains and the bundle
    groups common modules into shared chunks.
  - **Resolved by ODD-BSTATE-TAX-002**: see the new entry-point GREEN evidence
    below. The same test now observes GREEN because Turbopack produces
    two distinct chunks (`2k91wskdsbu4m.js` carrying only
    `taxa.tree.source` for `index.html`, and `3uwpekuzsbehu.js` carrying
    all four keys for `hydration-probe.html`).
- ODD-BSTATE-TAX-002 (GREEN) — Strict-TDD observed RED → GREEN cycle for the
  dedicated public entry point:
  - `test_browser_state_tree_source_entry_point_present`
    (`tests/test_module_layers.py`): RED before
    `src/modules/browser-state/tree-source.ts` was authored
    (assertion: `tree_source_entry.is_file()` failed with
    `missing public entry point: /Users/sebailla/Developer/taxa/src/modules/browser-state/tree-source.ts`);
    GREEN after the file landed.
  - `test_browser_state_tree_source_entry_point_is_module_root`
    (`tests/test_module_layers.py`): SKIPPED before the entry point
    existed; GREEN after (the file is at the module root, NOT inside
    `presentation/` / `application/` / `domain/` / `infrastructure/`).
  - `test_no_forbidden_layer_name_per_module`
    (`tests/test_module_layers.py`): GREEN both before and after
    (the new `MODULE_ROOT_ENTRY_POINTS` carve-out admits the
    `tree-source.ts` filename explicitly so no layer-purity
    violation is recorded).
  - `test_taxonomy_tree_imports_use_tree_source_via_dedicated_entry_point`
    (`tests/test_visible_taxonomy_tree.py`): RED before
    `TaxonomyTree.tsx` was migrated (assertion: no
    `import { useTreeSource } from "@taxa/browser-state/tree-source"`
    match found in the source file); GREEN after the import was
    updated. The test simultaneously asserts the legacy
    `@taxa/browser-state` import of `useTreeSource` is REJECTED,
    enforcing the strict-continuation decision (legacy import
    assertion rejects new path as applicable).
  - `test_out_index_html_chunks_permit_only_tree_source_key`
    (`tests/test_app_shell_render.py`): RED before ODD-BSTATE-TAX-002
    (the pre-entry-point bundle carried all four key literals in the
    `08ei48_e3ijfx.js` shared chunk referenced by `index.html`).
    GREEN after the dedicated entry point split the typed-source
    chain into a dedicated chunk that the main route references
    without ever touching the forbidden key files. The literal-level
    chunk test was NOT weakened: the assertion still rejects every
    forbidden key literal in every chunk referenced by
    `out/index.html`.
- ODD-BSTATE-TAX-001-C (GREEN) — Strict-TDD observed RED → GREEN cycle for:
  - `test_main_route_is_statically_exported` (RED before
    `out/index.html` was re-emitted via the per-key split build; GREEN
    after).
  - `test_main_route_static_html_starts_loading_without_selector` (NEW — pins
    that the SSR'd first render shows the loading copy AND does NOT
    leak any stored source value into the static HTML; previously the
    test asserted `data-active-source="col"` literally inside
    `out/index.html`, which is unreachable because the selector only
    mounts after `fetchDomains` resolves client-side. Updated
    contract: static HTML carries the loading state, NOT a baked-in
    source literal; the runtime test pins the typed default at
    runtime instead).
  - `test_main_route_empty_storage_first_render_starts_with_col` (RED before
    the route-intercept mocks landed; GREEN after — the synthetic
    `coldp_id`-bearing root mounts the selector, and the typed default
    `col` is observed at runtime).
  - `test_main_route_selector_click_persists_and_rehydrates_after_reload`
    (RED before the `worms_id` mock landed (selector vanished after
    the source switch because the synthetic taxon had no WoRMS
    affiliation, so `state.rootIds.length > 0` was false); RED again
    before the JS-evaluate string-syntax fix landed; GREEN after).
- Verification runs observed in this work unit (cumulative, spanning
  ODD-BSTATE-TAX-001-A through ODD-BSTATE-TAX-002):
  - `pnpm exec tsc --noEmit` — clean (no output).
  - `pytest tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key -q`
    — 1 passed (the strict chunk-boundary witness now observes GREEN after
    ODD-BSTATE-TAX-002 split the typed-source chain into a dedicated
    Turbopack chunk referenced only by `out/index.html`).
  - `pytest tests/test_browser_state_keys.py tests/test_browser_state_hydration_guard.py -q`
    — 62 passed, 2 skipped (the per-key split structural + runtime harness).
    The earlier `58 passed, 3 skipped` count was off by four — a legacy
    `test_application_hook_can_import_react_but_not_localstorage` shim at the
    bottom of `tests/test_browser_state_keys.py` shadowed the parametrized
    per-key contract and unconditionally `pytest.skip()`-ed, so pytest
    collected one skip instead of the four `[path0..path3]` cases the
    `APP_HOOK_FILES` tuple defines. Strict-continuation repair (this task):
    removed the legacy shim; `pytest --collect-only -q` now lists
    `test_application_hook_can_import_react_but_not_localstorage[path0]`
    through `[path3]`, the focused run reports `4 passed`, and the combined
    run reports `62 passed, 2 skipped` (the one unconditional skip is gone;
    the two remaining skips are the toolchain/SSR contract skips in the
    hydration guard, unrelated to this defect).
  - `pytest tests/test_visible_taxonomy_tree.py -q` — 199 passed
    (the new `test_taxonomy_tree_imports_use_tree_source_via_dedicated_entry_point`
    test asserts the dedicated entry-point path and rejects the
    legacy aggregate barrel import).
  - `pytest tests/test_hydration_console.py -v -s` — 6 passed (probe route
    exercises `useTreeSource` rehydration + setter round-trip + post-DCL
    storage read; the same hook drives TaxonomyTree through the new
    dedicated entry point).
  - `pytest tests/test_taxonomy_tree_source_persistence.py -v -s` — 4 passed
    (the main route's selector-specific Chromium witness; the typed-source
    hook is now reached through `@taxa/browser-state/tree-source`).
  - `pytest tests/test_module_layers.py tests/test_no_restricted_imports.py -q`
    — 144 passed (modular monolith + ESLint barrel guard intact; the
    `MODULE_ROOT_ENTRY_POINTS` carve-out admits the new
    `tree-source.ts` filename, and the ESLint guard's
    `(capability × layer)` matrix still rejects every deep import
    including any attempt to alias through
    `@taxa/browser-state/tree-source/...`).

## Risks
- **Static-HTML contract relaxation for the main route selector.** The
  prior contract asserted that `out/index.html` carries
  `data-active-source="col"` literally. The selector only mounts after
  the client-side `fetchDomains` succeeds, so the SSR-first-render HTML
  cannot carry that attribute. `test_main_route_static_html_starts_loading_without_selector`
  is the new static-side contract: SSR'd HTML MUST NOT bake any stored
  source value into the markup, and the runtime test pins the typed
  default at runtime. Any future regression that pre-renders the typed
  source value trips this test even though the post-hydration behavior
  stays correct.

- **Probe route still uses the aggregate barrel.** `src/app/hydration-probe/page.tsx`
  imports `HydrationProbe` through the aggregate `@taxa/browser-state`
  barrel so the probe continues to mount all four typed hooks together
  (the probe is the single component that legitimately needs all four
  chains in one bundle). The strict chunk-boundary witness does not
  apply to the probe route — the witness scopes the literal-absence
  check to chunks referenced by `out/index.html` only, leaving
  `out/hydration-probe.html` and its bundles free to carry the
  forbidden key literals. The probe bundle is
  `out/_next/static/chunks/3uwpekuzsbehu.js` and carries all four key
  literals; the main-route bundle is
  `out/_next/static/chunks/2k91wskdsbu4m.js` and carries only
  `taxa.tree.source`.

- **Strict-continuation carve-out for `tree-source.ts`.** The
  `MODULE_ROOT_ENTRY_POINTS` carve-out in `tests/test_module_layers.py`
  admits the new `tree-source.ts` filename as a legitimate
  module-root child. A future PR that adds another entry point under
  any capability MUST extend `MODULE_ROOT_ENTRY_POINTS` explicitly —
  the inverse guard now treats every other module-root `.ts` file as
  a layer-purity violation. The carve-out is documented inline so
  reviewers see why the inverse guard accepts the filename.

- **Turbopack chunk-naming is build-dependent.** The dedicated
  `tree-source.ts` entry point makes Turbopack emit a separate chunk
  for the typed-source chain, but the chunk filename (`2k91wskdsbu4m.js`
  in the latest build) is content-hashed and can change with every
  `next build`. The strict chunk-boundary witness reads chunks via
  the `_extract_chunk_paths` helper that scans `out/index.html` for
  `/_next/static/chunks/*.js` references; the chunk-content scan
  applies to whatever the build emits, so a hash rename does not
  affect the test.
