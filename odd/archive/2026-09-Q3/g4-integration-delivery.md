# Deliver the G4 integration chain to develop

## Objective
Deliver the merged G4 integration branch to `develop` as a reviewable, dependency-ordered PR chain linked to approved migration issue #74.

## Problem
`chore/g4-candidate-evidence-integration` contains the G4 parity and candidate-evidence work, but it diverges from `develop` at `f48ab90` and a direct PR has 189 files and +49,320/-10,018 changed lines. A single review would be unsafe and intractable.

## Scope
- Use issue #74 (`migration: Next.js 16, React 19, and Tailwind CSS v4`) as the approved umbrella.
- Build one coherent Feature Branch Chain with a draft/no-merge tracker PR and reviewable child PRs.
- Preserve each child’s tests and documentation with its behavior.
- Do not merge any PR, alter production, or include the pre-existing untracked artifacts in the current worktree.

## Constraints
- Delivery strategy: Feature Branch Chain, selected by the user.
- Parent base: `origin/develop` at `bb87aed`.
- Source integration tip: `origin/chore/g4-candidate-evidence-integration` at `fc079958`.
- Current aggregate diff: 189 files, +49,320/-10,018 lines; never publish it as one PR.
- User authorized PR creation, not merging.
- Existing untracked paths (`.codegraph/`, `build.log`, `docs/g6/`, Spanish migration research artifacts, `tsconfig.tsbuildinfo`) are out of scope.
- TDD mode: not applicable to delivery-only branch/PR work; every child retains its existing implementation verification and must receive proportionate independent validation before publication.

## Tasks
- [x] ODD-G4-INTEGRATION-001 Map the aggregate diff into cohesive, dependency-ordered, reviewable PR boundaries.  
  Route: delegated explorer (4-file and review-size triggers).  
  Evidence: the source ancestry is partitioned into G4 capture core, parity composition, candidate capture, fixture hardening, probe marker, and manifest pipeline; non-G4 taxonomy/a11y commits are excluded. Mapping also proved a hard prerequisite: this integration branch contains the unlanded frontend-migration ancestry, so a clean G4-only child chain cannot target current `develop` without first resolving that dependency.
- [x] ODD-G4-INTEGRATION-002 Resolve the delivery boundary.  
  Route: user decision.  
  Evidence: user selected prerequisite-first delivery: land the frontend-migration chain before creating a clean G4 chain against `develop`.
- [x] ODD-G4-INTEGRATION-003 Verify the prerequisite frontend-migration chain status.  
  Route: delegated explorer plus GitHub read-only verification.  
  Evidence: historical migration PRs #146–#150 and G4 foundation PRs #223–#227, #229, #235, and #236 are already merged into `develop`; the assumed prerequisite is not an outstanding delivery chain.
- [x] ODD-G4-INTEGRATION-004 Map the clean residual G4 work by semantic/patch difference from current `develop`.  
  Route: delegated explorer plus parent Git patch-equivalence/apply checks.  
  Evidence: the integration ancestry is not a deliverable residual: #223–#226, #232, #235, and #236 are patch-equivalent to `develop`; other historical commits differ semantically and the three newer candidate commits (`2203898`, `1f0f596`, `a6307d3`) all fail `git apply --check` against the current worktree. No clean, issue-backed residual PR is proven.
- [x] ODD-G4-INTEGRATION-005 Resolve the stale integration branch disposition.  
  Route: user decision.  
  Evidence: user explicitly abandoned this historical delivery attempt. No PR, branch creation, merge, or remote mutation was performed; `fc079958` remains reference-only.

## Acceptance criteria
- No PR exceeds the review budget unless the user explicitly accepts a documented exception.
- The chain exactly covers the intended G4 integration changes and excludes `develop`-only work.
- Every PR links approved issue #74 and has exactly one `type:*` label.
- The tracker and all child PRs are clearly ordered; none is merged by this workflow.

## Progress
- Current refs were fetched and reconciled. PR #349 is merged into the integration branch as `fc079958`.
- The user selected Feature Branch Chain instead of a single oversized PR.
- Initial ancestry mapping suggested an unlanded frontend-migration prerequisite, and the user selected prerequisite-first delivery.
- GitHub verification corrected that premise: migration tracker child PRs #146–#150 and G4 foundation PRs #223–#227, #229, #235, and #236 are already merged into `develop` through historical/reconstructed paths. The remaining work must be re-mapped by semantic/patch difference, not by the divergent integration-branch ancestry.
- Residual mapping completed: `fc079958` is a divergent historical reconstruction, not a clean PR candidate. The user explicitly abandoned this delivery attempt. Any future G4 work must be newly scoped against current `develop`.
