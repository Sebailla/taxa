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
  - Delivery: ready as the first chained PR against `develop`.
- [ ] ODD-NTP-002 Implement source selector and three-tree loading semantics.
  - Acceptance: CoL, WoRMS, and conditional Freshwater controls match native visibility and active state; each source requests correct children and filters foreign rows; source switch resets source-bound state.
- [ ] ODD-NTP-003 Restore native tree structure, tier paging, and disclosure behavior.
  - Acceptance: recursive rows preserve full-row depth; rank-tier headers, incremental load/load-all, collapse-all, leaf behavior, and WoRMS/Freshwater auto-unroll match native observable behavior.
- [ ] ODD-NTP-004 Restore native row identity and source affordances.
  - Acceptance: rank/name typography, realm tint, status/extinction/count/source/folder affordances, kebab behavior, and accessible focus/selection match the legacy tree.
- [ ] ODD-NTP-005 Restore source-aware in-tree navigation and prove parity.
  - Acceptance: selection/focus/breadcrumb parent paths use the active source relation; focused tests, typecheck, static build, API/CORS checks, and browser comparisons of all three trees pass.
- [ ] ODD-NTP-006 Publish parity work units.
  - Acceptance: each coherent work unit has a Conventional Commit and PR linked to approved issue #74 with exactly one `type:*` label; no automatic merge.

## Progress
User selected chained PR delivery. ODD-NTP-001 is independently verified and ready to publish as the first chain slice. Renderer behavior remains unchanged pending ODD-NTP-002.

## Next step
Commit and open the ODD-NTP-001 PR to `develop`; then build ODD-NTP-002 on that PR branch.