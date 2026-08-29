# Tasks: migrate-nextjs-tailwind4

> Strict TDD: RED → GREEN (→ Refactor). Modular-monolith rules from
> `specs/modular-architecture/spec.md` apply to every UI/file unit.

## Reconstruction Notice

Worktree `feat/migrate-nextjs-tailwind4-pr1` holds planning artefacts
plus untracked material against `origin/develop` (`09ef767`).
**Nothing merged.** Previous `[x]` for Phase 1 + Phase 2a was a
planning artefact, not delivered work. **All tasks reconstruction
pending.** Sequential to `develop` (no stacked branches, no child
bases) per `AGENTS.md` §4. Backup worktree is read-only source.
Per-sub-PR forecast, tests, harnesses, and rollback live in
`apply-progress.md` §Reconstruction State (the per-sub-PR source
column) and §Rollback boundary per sub-PR.

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

> Order: **1a.1 → 1a.2 → 1b.1 → 1b.2 → 1b.3a → 1b.3b → 2a → 2b →
> 2c → 2d → 2e → 3 → 4 → 5**. Each PR → `develop` directly. PR 1
> was 1554 LoC untracked; now split into six sub-PRs ≤ 339 LoC.
> Rollback = revert the offending sub-PR.

## Phase 1a.1: Build-profile emitter (PR 1a.1 → develop)

- [ ] 1a.1.1 R — `tests/test_build_profile.py` (script-contract): emitter exits 0 + valid JSON schema for `web/dist/`.
- [ ] 1a.1.2 G — `scripts/emit_build_profile.mjs`: walks build dir, emits `build-profile.json`; exits non-zero on missing/empty build.
- [ ] 1a.1.3 Refactor — error message names missing path.

## Phase 1a.2: Build-profile schema test (PR 1a.2 → develop)

- [ ] 1a.2.1 R — `tests/test_build_profile.py` (remainder): shape asserts for `chunks`, `total_bytes`, `per_route_bytes`.
- [ ] 1a.2.2 G — second test expansion (no production code).
- [ ] 1a.2.3 Refactor — parameterize schema assertions.

## Phase 1b.1: Chromium pin (PR 1b.1 → develop)

- [ ] 1b.1.1 R — `tests/test_evidence_baseline.py` (chromium block): installed binary matches pinned SHA256.
- [ ] 1b.1.2 G — `scripts/verify_chromium.py`: prints pin + diff vs installed binary; exits non-zero on mismatch.
- [ ] 1b.1.3 Refactor — error message names expected vs actual hash.

## Phase 1b.2: Evidence baseline (PR 1b.2 → develop)

- [ ] 1b.2.1 R — `tests/test_evidence_baseline.py` (remainder): legacy module roster, total source size, evidence-baseline JSON schema.
- [ ] 1b.2.2 G — second test expansion.
- [ ] 1b.2.3 Refactor — parameterize legacy roster assertions.

## Phase 1b.3a: Hydration measurement script (PR 1b.3a → develop)

- [ ] 1b.3a.1 R — `tests/test_hydration_timing.py` (schema subset): `measure_hydration.py` exits 3 on schema violation.
- [ ] 1b.3a.2 G — `scripts/measure_hydration.py`: reads hydration JSON, emits human-readable summary; exits non-zero on missing keys.
- [ ] 1b.3a.3 Refactor — split read+summary into two pure functions.

## Phase 1b.3b: Hydration timing test (PR 1b.3b → develop)

- [ ] 1b.3b.1 R — `tests/test_hydration_timing.py` (remainder): shape asserts for `delta_server_to_tree_first_paint_ms` and `console_warnings`.
- [ ] 1b.3b.2 G — second test expansion.
- [ ] 1b.3b.3 Refactor — strip legacy-build baseline numbers (already in `design.md` §"Migration Evidence Baseline").

## Phase 2a: Layer scaffold (PR 2a → develop)

- [ ] 2a.1 R — `tests/test_module_layers.py`: 4 layer folders + `index.ts` per capability.
- [ ] 2a.2 G — scaffold 5 capabilities × 4 layer folders + barrels; `tsconfig.json` aliases.
- [ ] 2a.3 Refactor — `test_no_forbidden_layer_name_per_module` + cap on total folder count.

## Phase 2b: ESLint config (PR 2b → develop)

- [ ] 2b.1 R — `tests/test_no_restricted_imports.py` (config-presence): `.eslintrc.cjs` exists; 20 patterns present.
- [ ] 2b.2 G — `.eslintrc.cjs` barrel-only patterns for 5 caps × 4 layers.
- [ ] 2b.3 R — barrel-import runtime test (`barrel_import.js` exits 0).

## Phase 2c: ESLint triangulation (PR 2c → develop)

- [ ] 2c.1 R — `tests/test_no_restricted_imports.py` (runtime-triangulation block): every (capability, layer) pair rejected at runtime.
- [ ] 2c.2 G — 20 `scripts/eslint-fixtures/deep_import_<capability>_<layer>.js` fixtures.

## Phase 2d: Taxonomy domain (PR 2d → develop)

- [ ] 2d.1 R — `tests/test_taxonomy_domain.py`: compiles without Next/React/FastAPI; field shape + invariant surface.
- [ ] 2d.2 G — `src/modules/taxonomy/domain/taxon.ts` plain types + invariants.

## Phase 2e: Domain purity guard (PR 2e → develop)

- [ ] 2e.1 R — `tests/test_domain_purity.py`: zero framework matches in domain.
- [ ] 2e.2 Refactor — strip JSDoc comments before regex; add forbidden-token parametrizations.

## Phase 3: Frontend-Bootstrap (PR 3 → develop)

- [ ] 3.1 R — `tests/test_tailwind_4_parity.py`: every `var(--token)` from `web/index.html`.
- [ ] 3.2 G — `src/modules/design-system/infrastructure/globals.css`: `@import "tailwindcss"` + `@theme` + `@layer base`.
- [ ] 3.3 R — `tests/test_make_api_build.py`: `Makefile::api` runs Next build then uvicorn.
- [ ] 3.4 G — `Makefile::api` runs `npm install && npm run build:web && uvicorn`; `scripts/check-runtime.mjs` enforces Node ≥20.9.0.
- [ ] 3.5 R — `tests/test_static_mount.py`: `GET /` returns Next HTML; `GET /_next/static/<h>.js` 200.
- [ ] 3.6 G — `api/server.py:54` `WEB_DIR = Path("out")`; mount signature kept.
- [ ] 3.7 R/G — relocate `web/search_urls.js` → `src/modules/research/infrastructure/search-engines.js`; AC-21 test `open()` updated.
- [ ] 3.8 Refactor — grep `src/` for hex; assert none outside design-system module.

## Phase 4: Browser state (PR 4 → develop)

- [ ] 4.1 R — `tests/test_browser_state_keys.py`: greps `src/`; expects 4 getItem + 4 setItem.
- [ ] 4.2 G — `src/modules/browser-state/{store,keys,defaults}.ts`: 4+4 callsites inside `useEffect`.
- [ ] 4.3 R — `tests/test_hydration_console.py` (Playwright) fails until reads mounted-gated.
- [ ] 4.4 G — `useSyncExternalStore` behind `mounted` flag; zero hydration warnings.

## Phase 5: Capability ports (PR 5 → develop)

- [ ] 5.1 R — `tests/test_taxonomy_infra.py`: mocks `fetchTaxon`/`fetchChildren`.
- [ ] 5.2 G — `src/modules/taxonomy/infrastructure/api.ts`; application exposes view-models only.
- [ ] 5.3 G — `useTaxonTree()` + port `web/{tree,detail,breadcrumb}.js` → `src/modules/taxonomy/presentation/{Tree,DetailPanel,Breadcrumb}.tsx`.
- [ ] 5.4 R — `tests/test_research_infra.py`: mocks `/api/taxon/{id}/files{,/serve}`.
- [ ] 5.5 G — `src/modules/research/infrastructure/api.ts`; domain types first.
- [ ] 5.6 G — port `web/{file_explorer,file_viewer,format,keymap}.js` → React; CDN pinned.
- [ ] 5.7 R — Playwright + e2e selectors updated.
- [ ] 5.8 G — `data-*` contract preserved; perf ≤ 0%.
- [ ] 5.9 Refactor — delete `web/*.{html,js,css}` + `tailwind.config.js`.

## Out of scope (per AGENTS.md)

No `git push`, `git commit`, `gh pr create`, `git stash`; no new
worktrees; no source/test edits. Only `tasks.md`,
`apply-progress.md`, their Spanish mirrors, and Engram change.