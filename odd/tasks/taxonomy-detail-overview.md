# Restore taxonomy detail Overview

## Objective
Port the native taxon DetailPanel Overview into the React tree so selecting a taxon reveals its native identity, taxonomy context, and core metadata.

## User decision
After completing tree parity, the next selected slice is the native DetailPanel Overview. Search and Folder remain separate future surfaces.

## Scope
- Mount a selected-taxon detail panel inside the existing taxonomy client island.
- Port the Overview header, source/status affordances, scientific name, authorship, rank, count, and source-aware ancestor chain from legacy.
- Reuse current canonical taxon fields, row-format helpers, and source-aware breadcrumb walker.
- Maintain per-taxon active-tab memory while implementing Overview as the only fully rendered tab.
- Close the panel and clear selection on source switch; breadcrumb navigation reuses current source-aware handlers.
- Add focused tests, static build evidence, and local browser/API validation.

## Non-goals
- Search, Folder, Vernaculars, Synonyms, and Distribution tab content.
- FastAPI, database, ETL, legacy web, header navigation, or production cutover changes.
- New UI dependencies or a new visual system.

## Constraints
- Legacy `web/detail.js` and associated legacy CSS are the parity oracle.
- Preserve the existing minimal single React client island; no change to `src/app/page.tsx`.
- Use existing `Taxon` projection; do not duplicate wire mapping.
- TDD mode: disabled/unknown; use focused tests and observed browser behavior.
- Commit and open a PR when complete; no automatic merge.

## Tasks
- [x] ODD-TDO-001 Implement the native Overview panel and selected-taxon state integration.
  - Implementation: selected taxon now mounts native-style Overview inside the tree island, with canonical identity/source/realm/status/count/path data, close behavior, source-aware chain controls, and per-taxon tab state.
  - Evidence: independent verifier approved; 380 related tests, strict typecheck, static build, CSS export evidence, and existing tree interaction checks passed. Later tabs are visibly disabled rather than falsely wired.
  - Delivery: ready to publish.
- [ ] ODD-TDO-002 Verify and publish the Overview slice.
  - Acceptance: focused tests, strict typecheck, static build, diff check, browser/API evidence, independent verification, conventional commit, and PR linked to issue #74 with exactly one `type:*` label.

## Progress
ODD-TDO-001 is independently verified and ready for PR delivery.

## Next step
Commit, open a PR to `develop`, then wait for CI and explicit merge authorization.