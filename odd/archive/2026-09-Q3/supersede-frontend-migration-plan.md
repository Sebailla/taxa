# Supersede the obsolete frontend migration plan

## Objective
Replace planning artifacts that falsely describe the frontend migration as entirely undelivered with a concise, auditable record of the ODD slices that superseded them and the work that remains.

## User decision
The obsolete OpenSpec tracker and PR #143 will be explicitly superseded and closed without merge.

## Scope
- Reconcile stale ODD delivery checkboxes using merged-history evidence.
- Add an explicit supersession record to the obsolete OpenSpec change.
- Close PR #143 without merging after the supersession record is published.

## Non-goals
- Replan or implement the remaining production cutover.
- Delete historical OpenSpec artifacts or legacy frontend files.
- Rewrite implementation history or create a new OpenSpec change.

## Allowed edit surfaces
- `odd/tasks/make-api-pnpm-bootstrap.md`
- `odd/tasks/native-tree-parity.md`
- `odd/tasks/taxonomy-detail-discoverability.md`
- `odd/tasks/taxonomy-detail-distribution.md`
- `odd/tasks/taxonomy-detail-overview.md`
- `odd/tasks/taxonomy-detail-search.md`
- `odd/tasks/visible-taxonomy-tree.md`
- `odd/tasks/supersede-frontend-migration-plan.md`
- `openspec/changes/complete-taxa-frontend-migration/SUPERSEDED.md`
- `openspec/changes/complete-taxa-frontend-migration/proposal.md`
- `openspec/changes/complete-taxa-frontend-migration/design.md`
- `openspec/changes/complete-taxa-frontend-migration/spec.md`
- `openspec/changes/complete-taxa-frontend-migration/tasks.md`
- `openspec/changes/complete-taxa-frontend-migration/apply-progress.md`

## Tasks
- [x] ODD-PLANDEBT-001 Map delivered slices and remaining work.
- [x] ODD-PLANDEBT-002 Reconcile stale ODD and OpenSpec planning artifacts.
  - Evidence: PRs #299–#302, #306, #308–#310, #318, #322, and #323 are merged; their relevant work-unit commits are reachable from `origin/develop`. PR #303 is closed, with its source-selector work superseded by the merged tree-structure/navigation chain.
  - Delivery: seven ODD trackers (`make-api-pnpm-bootstrap.md`, `native-tree-parity.md`, `taxonomy-detail-discoverability.md`, `taxonomy-detail-distribution.md`, `taxonomy-detail-overview.md`, `taxonomy-detail-search.md`, `visible-taxonomy-tree.md`) now record their verify-and-publish tasks as complete with merge commits; five top-level OpenSpec artifacts (`proposal.md`, `design.md`, `spec.md`, `tasks.md`, `apply-progress.md`) carry prominent `SUPERSEDED` pointers to `SUPERSEDED.md`; `SUPERSEDED.md` is the concise canonical reader record (delivered evidence, explicitly not claimed, remaining production cutover gap).
- [x] ODD-PLANDEBT-003 Verify the documentation disposition, publish it, and close PR #143.
  - Delivery: PR #324 (`docs(openspec): supersede frontend migration plan`) merged as `916ba1a` after Smoke tests passed. PR #143 was then closed without merge; its supersession notice and audit record live in `openspec/changes/complete-taxa-frontend-migration/SUPERSEDED.md`.
