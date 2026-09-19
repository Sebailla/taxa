# Typed browser-state prerequisite

## Objective
Establish a typed, hydration-safe browser-state capability for the Next static export without changing legacy production routing or mounting it in the taxonomy UI yet.

## User decision
Proceed with the browser-state prerequisite after confirming the AC-21 React catalog migration is already functionally complete.

## Scope
- Add the typed browser-state domain model, local-storage-backed infrastructure store, and public module API.
- Guard client reads behind hydration so static export emits a stable first render.
- Add focused contract tests for storage ownership, quota safety, subscriptions, and hydration behavior.

## Non-goals
- Migrating `TaxonomyTree` state consumers; that is a follow-up interaction slice.
- Changing `web/`, FastAPI's `WEB_DIR`, `Makefile`, AC-21, or production routing.
- Introducing Playwright coverage in this work unit; browser-console verification is a follow-up after the unit-level contract is established.

## Allowed edit surfaces
- `src/modules/browser-state/index.ts`
- `src/modules/browser-state/domain/keys.ts`
- `src/modules/browser-state/domain/defaults.ts`
- `src/modules/browser-state/infrastructure/store.ts`
- `src/modules/browser-state/application/useBrowserStateKey.ts`
- `tests/test_browser_state_keys.py`
- `tests/test_browser_state_hydration_guard.py`
- `odd/tasks/typed-browser-state-prerequisite.md`

## TDD and delivery
- TDD mode: strict; observed RED/GREEN/TRIANGULATE/REFACTOR evidence is recorded below.
- Expected authored change: approximately 350 lines.
- Delivery strategy: Feature Branch Chain, selected by the user after the verified diff measured 1,991 changed lines. Commits are authorized; push and PR creation remain unrequested.
- Route: delegated writer, because this is a multi-file non-trivial change. Mapping completed by `gentle-ai-explore` under the 4-file rule.

## Tasks
- [x] ODD-BSTATE-001 Implement typed browser-state store and hydration guard.
  - Define the four typed keys and defaults.
  - Isolate every `localStorage` access in the infrastructure store; tolerate unavailable or quota-limited storage.
  - Expose typed reads/writes, reset, and subscription behavior only through the public barrel.
  - Keep all initial browser reads behind the mounted/hydration guard.
  - Add focused contract tests and run declared verification.
  - Status: complete.
- [x] ODD-BSTATE-002 Independently validate the static-export/browser boundary.
  - Confirmed focused tests, typecheck, module-layer rules, legacy AC-21, and static-export contract.
  - Independent verifier passed 186 tests and `tsc`; parent spot check passed 35 focused tests, `git diff --check`, and LSP reported zero errors in the five production files.
  - Browser-console/Playwright coverage remains necessary as a separate follow-up before any consumer migration/cutover.
  - Status: complete.

## Acceptance criteria
- Browser state has typed defaults for theme, tree source, last taxon ID, and kebab-open ID.
- No feature module outside `src/modules/browser-state/` accesses `localStorage`.
- Storage read, write, and removal failures do not crash rendering or subscriptions.
- Static/server snapshots use typed defaults until the browser mounts.
- Legacy `web/` mount, AC-21 contract, and static-export contract remain green.

## Delivery chain
- Tracker branch: `feat/typed-browser-state-prerequisite` (will advance to the final chain tip).
- Foundation: `50cdc41 feat(browser-state): add typed state foundation`.
- Store: `ea3b1cb feat(browser-state): add resilient storage store`.
- Hooks: `2583cae feat(browser-state): add hydration-safe hooks`.
- Public API: `47e0029 feat(browser-state): expose typed public API`.
- Source-contract tests: `aea8b37 test(browser-state): lock storage ownership contract` (523-line exception explicitly accepted).
- Storage runtime contract: `3e10953 test(browser-state): exercise storage runtime contract`.
- Hydration hook contract: `d3c0e3a test(browser-state): verify hydration hook contract` (411-line exception explicitly accepted).
- Earlier planned runtime exception is unnecessary after the source-contract boundary was measured correctly: the runtime addition is 289 lines.

## Evidence
- Feature branch: `feat/typed-browser-state-prerequisite`.
- Authored change: 5 production files (keys.ts + defaults.ts +
  store.ts + useBrowserStateKey.ts + index.ts) + 2 contract tests
  (test_browser_state_keys.py + test_browser_state_hydration_guard.py).
- Strict TDD cycle observed:
  - RED: 10 focused tests failed before any source files existed
    (canonical-file-present, layer-folder-present, barrel exports,
    hook-file-present, barrel re-exports per-key hooks).
  - GREEN: every failing test turned green after the production
    files landed; the runtime harness exercises defaults,
    hydration, round-trip, subscribers, reset, storage-failure
    safety, SSR safety, and garbage-value fallbacks.
  - TRIANGULATE: extra assertions pin the storage-ownership
    contract (no `localStorage` access outside
    `infrastructure/store.ts`), the no-other-module rule
    (parametrized over `taxonomy`, `research`, `app-shell`,
    `design-system`), the four-typed-defaults shape, and the
    hydration-guard surface (`useSyncExternalStore`,
    `"use client";` directive, per-key hook signatures).
  - REFACTOR: storage header comments updated to reflect the
    inlined-reset affordance + safe-helper split; comment-
    stripping helper introduced in tests so docblocks do not
    false-positive purity guards (mirrors
    `tests/test_domain_purity.py`).
- Verification commands observed (all green):
  - `pnpm exec tsc --noEmit` — exit 0, no diagnostics.
  - `pytest tests/test_module_layers.py -q` — 40 passed.
  - `pytest tests/test_no_restricted_imports.py -q` — 102 passed.
  - `pytest tests/test_smoke.py::test_search_engine_contract -q`
    — 1 passed (AC-21 preserved).
  - `pytest tests/test_static_export_contract.py -q` — 8 passed
    (G2 contract preserved).
  - `pytest tests/test_browser_state_keys.py
    tests/test_browser_state_hydration_guard.py -q` — 35 passed
    (the focused contract tests).
- Browser-console / Playwright hydration-mismatch coverage remains
  a separate follow-up before consumer migration or cutover; it was
  intentionally excluded from this store-boundary work unit.
- Independent verification: 186 tests passed and `tsc --noEmit`
  was clean. Parent spot check: 35 focused tests passed, `git diff
  --check` was clean, and LSP found zero errors in the five production
  files.
