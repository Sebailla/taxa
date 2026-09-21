# Wire G4 candidate manifest generation

## Objective
Provide a bounded `make g4-candidate-manifest` entry point that generates the strict G4 candidate manifest from an already-built static export, ready for the existing `make parity` pipeline.

## Problem
The manifest producer and its validation exist, and `make parity` requires a caller-supplied `PARITY_MANIFEST`, but there is no reproducible Make entry point that generates that manifest from `out/index.html` and the candidate URL.

## Scope
- Add a standalone `make g4-candidate-manifest` target.
- Require `CANDIDATE_URL` and `CANDIDATE_MANIFEST`; default `CANDIDATE_HTML` to `out/index.html`.
- Invoke the existing `scripts/generate_g4_candidate_manifest.mjs` producer through the existing package script.
- Add hermetic Makefile contract tests.
- Preserve `make parity` unchanged and fail closed for its existing required variables.

## Constraints
- Base: `origin/chore/g4-candidate-evidence-integration` at merge `311b4a6` (PR #348).
- Do not install dependencies, start a server, or run `next build` from the new target.
- Do not include pre-existing `.codegraph/`, `build.log`, `docs/g6/`, Spanish migration artifacts, or `tsconfig.tsbuildinfo`.
- No commit, push, or PR is authorized unless separately requested.

## TDD and delivery
- TDD mode: focused Makefile contract tests; source: G4 test conventions.
- Delivery strategy: exception-ok — user selected one cohesive PR.
- Authored change: 642 lines including the target and 24 hermetic contracts; splitting them would separate behavior from its proofs.

## Tasks
- [x] ODD-G4-MANIFEST-001 Add a RED/GREEN Makefile target contract for candidate manifest generation.
  - Route: delegated writer (multi-file write rule).
  - RED: 15 tests reported no `g4-candidate-manifest` target before implementation.
  - GREEN: target defaults `CANDIDATE_HTML=out/index.html`, requires URL/manifest, and invokes the producer with literal `--html`, `--url`, and `--out` flags; 24 new hermetic tests pass.
- [x] ODD-G4-MANIFEST-002 Independently verify manifest pipeline wiring.
  - Route: delegated verifier.
  - Evidence: new target tests → 24 passed; existing parity contract → 24 passed; producer tests → 27 passed; TypeScript and diff checks clean; `make parity` is byte-identical to base and the diff contains only `Makefile` plus the new in-scope test/task artifacts.

## Acceptance criteria
- `make g4-candidate-manifest CANDIDATE_URL=<http(s) URL> CANDIDATE_MANIFEST=<path>` invokes the existing generator with `--html`, `--url`, and `--out`.
- Missing/invalid input fails before producer execution.
- The target does not install dependencies, build Next, start services, or weaken `make parity`.
- Generated manifests remain consumable by the current G4 capture path.

## Progress
- Mapping confirmed the producer and its 13 tests are already on the integration branch; this slice owns only the missing Makefile wiring.
- Work-unit commit: `a6307d3 feat(g4): wire candidate manifest pipeline`.
- Slice implementation and independent verification are GREEN. User authorized a single size-exception PR for #246; publication is in progress.
