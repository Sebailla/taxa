# Complete the frontend migration

## Objective
Finish issue #74 by replacing the legacy `web/` frontend with the React/Next static export served by FastAPI, while preserving behavior, a single local origin, and an atomic rollback.

## Authorization and boundaries
- User authorized beginning this migration plan on branch `feat/complete-frontend-migration`.
- This tracker starts with planning and read-only mapping; no production cutover, legacy deletion, commit, push, or PR creation is authorized yet.
- Preserve pre-existing worktree changes: `next-env.d.ts` and `odd/tasks/g4-integration-delivery.md`.
- The final Approach selection remains evidence-gated. Static export under FastAPI (Approach A) is the default only if its gates pass.

## Delivery strategy
Feature Branch Chain. Each code-bearing slice keeps its tests and documentation. The final cutover is a single atomic release even if it exceeds the usual review budget, because partial activation would break active consumers and rollback.

## Tasks
- [x] ODD-MIGRATE-001 Map the remaining legacy research surface into exact React replacement slices.
  - Route: delegated explorer (four-file rule).
  - Scope: file explorer, viewers/renderers, materialization, keyboard behavior, and AC-21 consumers.
  - Evidence: the read-only map identifies 18 dependency-ordered units (W1–W18). W1–W6 establish pure Research domain/ports/API/search/renderers; W7–W12 mount explorer/viewer/folder/keymap/settings/detail UI; W13–W15 relocate AC-21/search/CSS; W16–W17 integrate the route; W18 is the separately authorized atomic cutover. The map forecasts 16 reviewable child slices plus one atomic release, and preserves Tier-1 consumers until cutover. Key boundaries: raw `taxa.fex.treeWidth` must stay local to Explorer to avoid browser-state chunk scope expansion; React materialize propagation must update typed tree state rather than legacy DOM markers; `next-env.d.ts` remains untouched.

- [ ] ODD-MIGRATE-002 Define failing React contracts for the research replacement.
  - Route: delegated worker after the map is approved.
  - Scope: domain/application ports, API contract seams, and hermetic tests only.
  - Progress: W1 Research domain contract is implemented and independently verified: `src/modules/research/domain/explorer.ts` defines pure, readonly ExplorerState/SearchState/ViewerTab/FileFormat and the legacy-faithful initial-state factory; `tests/test_research_domain.py` passes 20 tests. Independent verification also passed 170 relevant purity/layer tests and strict isolated TypeScript compilation. Work-unit commit: `2699e8f feat(research): add explorer domain contract`. The user explicitly accepted its documented size exception: 1,130 added lines keep the domain contract, its runtime proof, and the feature tracker cohesive; splitting would separate behavior from proof. W2 is also implemented and independently verified: `src/modules/research/application/ports.ts` adds the pure inward-only ExplorerRepository contract for tree retrieval and file serving; `tests/test_research_application.py` passes 16 focused tests, including strict compilation and a runtime port-compatibility harness. The user explicitly accepted W2's documented size exception (~1,091 lines) because the pure port and its runtime proof must remain together. No FastAPI mount change.
  - Evidence: RED → GREEN → triangulation test record; no FastAPI mount change.

- [ ] ODD-MIGRATE-003 Deliver the Research explorer and supported file-preview behavior in reviewable slices.
  - Route: delegated worker; chained PRs expected.
  - Scope: `src/modules/research/` and focused tests, preserving legacy behavior.
  - Evidence: focused contracts and browser verification for explorer, materialization, open-folder, and each supported preview family.

- [ ] ODD-MIGRATE-004 Move AC-21 and remaining active consumers off `web/`.
  - Route: delegated worker.
  - Scope: search-engine catalog, consumer manifest, and affected tests.
  - Evidence: AC-21, smoke, and consumer-manifest tests pass against the React replacement path.

- [ ] ODD-MIGRATE-005 Produce fresh candidate evidence and select the cutover approach.
  - Route: delegated verification.
  - Scope: reproducible build inventory (G2), behavior/a11y parity (G4), candidate-baseline comparison (G5), and canonical dry-run rehearsal (G6).
  - Evidence: all artifacts are current, comparable, and pass their fail-closed thresholds. If any gate fails, stop before activation.

- [ ] ODD-MIGRATE-006 Perform the atomic production cutover.
  - Route: delegated worker after ODD-MIGRATE-005 passes and the user explicitly authorizes activation.
  - Scope: `make api` build path, `api/server.py::WEB_DIR`, all Tier-2 consumer updates, the selected build artifact, and legacy `web/` retirement in one release.
  - Evidence: a single rollback boundary and no active consumer pointed at a retired path.

- [ ] ODD-MIGRATE-007 Verify the activated runtime and rollback.
  - Route: delegated verifier.
  - Scope: full relevant tests, FastAPI-served smoke/browser/a11y validation, G3 Tier-2 readiness, G6 execution/rollback rehearsal, and a revert proof.
  - Evidence: CI-equivalent suite and the rollback restore the legacy behavior as one unit.

- [ ] ODD-MIGRATE-008 Close issue #74.
  - Route: parent after all evidence and explicit user authorization.
  - Evidence: every acceptance criterion is met, CI is green, and the issue closure comment links the cutover and verification evidence.

## Current evidence
- The React taxonomy surface, detail panels, browser-state store, static-export preparation, and G4/G6 supporting slices are merged into `develop`.
- FastAPI still serves `web/`; this branch has not changed that behavior.
- `src/modules/research/` remains the main functional gap.
- G6 canonical dry-run is recorded, but G3 Tier-2, G4 candidate parity, G5 candidate comparison, activation, and rollback rehearsal remain incomplete.

## Work-unit policy
No work-unit commit is made unless the user explicitly authorizes commits. Once authorized, each completed task must include its tests/docs and use a Conventional Commit message; the final atomic cutover is a separately authorized release boundary.
