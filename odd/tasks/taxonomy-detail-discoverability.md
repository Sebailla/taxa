# Make taxonomy details discoverable

## Objective
Make the React taxon detail panel reachable through a clear row-level icon action instead of the misleading kebab item “Search online”.

## Scope
- Add a compact `visibility` icon control to each taxonomy row that selects the taxon and opens its details without changing tree expansion.
- Rename the kebab selection action to “View details” while retaining its accessible label and icon.
- Preserve disclosure, folder, source, status and WoRMS actions.
- Add focused interaction/accessibility tests and browser evidence.

## Decisions
- Use Material Symbols icons with visible tooltip/accessible labels rather than a new icon dependency.
- Detail action uses `visibility`; icon controls retain text-free visual density but explicit `aria-label`/`title`.
- Include generated `next-env.d.ts` only if it remains changed after validation.

## Non-goals
- Row click selection behavior, changing hierarchy disclosure semantics, tree kebab-folder wiring, or backend changes.

## Tasks
- [x] ODD-TDDISC-001 Add discoverable detail action and correct label.
  - Evidence: independent verifier approved; 193 tree tests, strict typecheck, static artifact check, and browser interaction test passed.
- [ ] ODD-TDDISC-002 Verify and publish.

## Progress
ODD-TDDISC-001 is ready to publish. The full web-toggle suite retains two pre-existing Search-count failures.