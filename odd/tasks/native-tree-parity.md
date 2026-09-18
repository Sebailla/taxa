# Restore native taxonomy tree parity

## Objective
Replace the merged React hybrid tree with a faithful migration of the legacy taxonomy-tree surface: separate CoL, WoRMS, and Freshwater trees; source-bound hierarchy behavior; and the native tree's visual and interaction contract.

## Problem and rationale
The current React island renders all API roots in one generic hierarchy. The native UI instead exposes three independent source views with different roots, parent relationships, filtering, reset behavior, row semantics, and tier pagination. This hybrid output makes valid source data look incorrect and is not acceptable as a migration.

## User decision
The legacy `web/` tree is the parity oracle. The React tree must be identical in source behavior and rendered tree presentation, not merely visually similar. Preserve FastAPI contracts and do not alter the legacy tree during migration.

## Scope
- Preserve the complete source-aware taxon wire contract needed by the native tree.
- Implement the CoL, WoRMS, and dynamically present Freshwater source selector.
- Thread source selection through root/child loading, source filtering, source-bound cache/state reset, and parent resolution.
- Restore native tree rendering: real hierarchy indentation, rank/name treatment, source/status/count/extinction affordances, realm tint, tier grouping, incremental loading, collapse-all, and native disclosure semantics.
- Restore source-aware tree navigation behavior required by the surface: selection/focus state and breadcrumb path where their absence prevents native tree parity.
- Prove parity against legacy behavior using focused source/runtime and browser evidence.

## Non-goals
- FastAPI endpoint, database, ETL, or legacy `web/` changes.
- Production static-export cutover from legacy `web/` to Next `out/`.
- Header-level Browser, Settings, Help, and global research-explorer migration unless directly required by an in-tree action.

## Constraints
- The existing FastAPI payload and `source=col|worms|freshwater` semantics are authoritative.
- `coldp_id`, `worms_id`, `freshwater_id`, `parent_id`, `worms_parent_id`, and `freshwater_parent_id` must not be coerced or dropped by the React projection.
- Initial source state and the Freshwater-toggle availability must match native boot behavior.
- Switching sources must clear source-bound expansion, paging, cache, selection, focus, and detail state exactly as native does.
- Do not introduce a new UI library or an invented visual system; port the native taxonomy-tree contract.
- TDD mode: disabled/unknown. Use existing focused source/runtime harnesses plus observed browser verification.

## Delivery strategy
feature-branch-chain (user selected). Forecast: roughly 1,400 authored lines across several cohesive work units. Each slice is committed and opened as a chained PR against its predecessor; no PR is merged automatically unless the user explicitly asks.

## Tasks
- [x] ODD-NTP-001 Preserve the complete source-aware taxonomy wire contract.
  - Implementation: canonical projection now retains every FastAPI field used by the native tree (`coldp_id`, `worms_id`, `freshwater_id`, `freshwater_parent_id`, status/extinction/path/species-count/materialization metadata) with exact nullability; public `TaxonomySource` options flow through both canonical API helpers.
  - Correction: `worms_parent_id` is an internal database/query column, not a FastAPI response field. The React contract deliberately does not invent it; later WoRMS ancestry must use attached tree edges unless a separately authorized backend contract adds the field.
  - Evidence: independent verifier approved; 55 targeted domain/infra/application/tree/shell tests, strict typecheck, and static build passed. Full offline suite had one confirmed pre-existing unrelated search-category failure. No presentation layer changed.
  - Delivery: published as PR #302 (`feat/native-tree-parity` → `develop`) with exactly `type:feature`; Smoke tests are pending.
- [x] ODD-NTP-002 Implement source selector and three-tree loading semantics.
  - Implementation: React now renders native-order CoL/WoRMS plus conditional Freshwater controls; roots filter from one cached `/api/domains` response and children load through the active `source` query with source filtering before attachment.
  - Correction: switching sources does not refetch domains. It clears roots, child cache, expanded IDs, load state, and row errors, then reprojects cached raw roots; a separate regression prevents the React dependency race that previously would have reloaded domains.
  - Evidence: independent verifier approved 134 focused tests, strict typecheck, static build, and live Chromium/API coverage. Browser proved all three root sets, all three source-qualified lazy requests, no root refetch across four switches, and a collapsed CoL return state.
  - Delivery: published as PR #303 (`feat/native-tree-source-selector` → `feat/native-tree-parity`) with exactly `type:feature`; checks are pending.
- [x] ODD-NTP-003 Restore native tree structure, tier paging, and disclosure behavior.
  - Implementation: replaced flattened grid rows with native 24px full-row depth blocks; restored rank-tier grouping, PAGE_SIZE=5 staircase, tier load-more, source auto-unroll, leaf/non-leaf disclosure, and collapse-all.
  - Evidence: independent verifier approved 151 focused checks and 21 live browser/API assertions: full depth formula, CoL tier pagination, per-tier load-more, WoRMS auto-unroll, source reset, no domains refetch, collapse-all, and leaf semantics.
  - Delivery: published as replacement PR #306 (`feat/native-tree-structure-rebased` → `develop`) after the deleted-base chain recovery; Smoke tests passed and it merged.
- [x] ODD-NTP-004 Restore native row identity and source affordances.
  - Implementation: ported pure native row formatting, realm tint, status/extinction/count/source/folder indicators, source tooltip/cross-link, and accessible kebab state. Deferred Search online/Open folder actions are explicitly disabled until their React behavior lands in ODD-NTP-005.
  - Evidence: independent verifier approved focused taxonomy/style checks, strict typecheck, and production CSS inspection. Browser rendering could not run because the verifier correctly did not start an API server; live API behavior was validated by the writer.
  - Delivery: ready to commit and open a PR against `develop`.
- [ ] ODD-NTP-005 Restore source-aware in-tree navigation and prove parity.
  - Acceptance: selection/focus/breadcrumb parent paths use the active source relation; focused tests, typecheck, static build, API/CORS checks, and browser comparisons of all three trees pass.
- [ ] ODD-NTP-006 Publish parity work units.
  - Acceptance: each coherent work unit has a Conventional Commit and PR linked to approved issue #74 with exactly one `type:*` label; no automatic merge.

## Progress
ODD-NTP-001, ODD-NTP-002 (replacement PR #305), and ODD-NTP-003 (replacement PR #306) are merged into `develop`. ODD-NTP-004 is independently verified and ready to publish from `feat/native-tree-row-affordances`.

## Next step
Commit and open the row-affordance PR against `develop`, then complete ODD-NTP-005 final navigation/parity verification.