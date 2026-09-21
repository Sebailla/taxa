# Align G4 candidate probe marker

## Objective
Align the static-export candidate's probe marker with the G4 corpus and manifest contract so candidate capture validation can proceed reliably.

## Problem
The G4 corpus manifest requires `data-testid="g4-probe-marker"`, while the candidate-side probe uses a different marker identifier. This prevents a reliable candidate manifest/capture chain.

## Scope
- Apply the existing bounded upstream slice `ddeec79` (`feat(g4): add candidate probe marker`) onto the G4 integration base.
- Preserve the candidate's existing hydration behavior and static-export architecture.
- Verify the candidate document exposes the G4 marker and that the existing app-shell/static contracts stay green.

## Constraints
- Base: `chore/g4-candidate-evidence-integration` at `26ecaa5`.
- Do not include pre-existing untracked `.codegraph/`, `build.log`, `docs/g6/`, Spanish migration artifacts, or `tsconfig.tsbuildinfo`.
- No commit, push, or PR is authorized unless separately requested.

## TDD and delivery
- TDD mode: existing upstream RED/GREEN evidence retained; this application requires focused regression verification.
- Delivery strategy: ask-on-risk.
- Estimated authored change: 82 lines.

## Tasks
- [x] ODD-G4-MARKER-001 Apply the bounded candidate marker slice.
  - Route: delegated writer (multi-file write rule).
  - Outcome: candidate layout emits a hidden, accessibility-neutral `<span data-testid="g4-probe-marker" aria-hidden="true" hidden />` before `AppShell`; the three upstream marker tests were applied.
  - Evidence: focused G4 tests → 3 passed; strict TypeScript clean; diff check clean.
- [x] ODD-G4-MARKER-002 Independently verify G4 marker alignment.
  - Route: delegated verifier.
  - Evidence: focused G4 tests → 3 passed in 2.46s; strict TypeScript clean; only expected code/test files appear in diff; existing `out/index.html` contains the exact marker; LSP clean.
  - Known base failure: `test_app_file_does_not_import_owners_of_later_prs[page]` remains 1 failure in the full app-shell file and reproduces with this slice stashed, so it is not introduced by this scope.

## Acceptance criteria
- Candidate static output contains `data-testid="g4-probe-marker"`.
- The marker uses deterministic text safe for static export and hydration.
- Existing app-shell marker contracts remain green.
- No pre-existing integration-branch artifact enters the slice.

## Progress
- Mapping confirmed the upstream slice is commit `ddeec79` and changes only the candidate layout plus its focused app-shell tests.
- Slice implementation and independent verification are GREEN. No commit, push, or PR is authorized yet.
