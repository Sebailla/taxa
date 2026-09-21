# Generate strict G4 candidate manifests on develop

## Objective
Resolve approved issue #246 by restoring a fail-closed candidate-manifest generator and a standalone Make entry point on the current `develop` branch.

## Problem
Current `develop` has the G4 parity composition but lacks both `scripts/generate_g4_candidate_manifest.mjs` and a `make g4-candidate-manifest` target. The historical implementation cannot be replayed directly because its Makefile context diverged, so the current contract must be re-established with focused coverage.

## Scope
- Add a Node generator that validates already-built candidate HTML and a candidate URL, then emits the strict G4 manifest consumed by `make parity`.
- Add a standalone Make target requiring `CANDIDATE_URL` and `CANDIDATE_MANIFEST`, defaulting `CANDIDATE_HTML` to `out/index.html`.
- Add hermetic producer and Makefile contract tests.
- Preserve the existing `make parity` contract unchanged.

## Constraints
- Approved issue: #246 (`bug: generate strict G4 candidate manifests`).
- Branch: `feat/g4-candidate-manifest-develop` from `develop@670d9af`.
- Allowed edit surfaces: `package.json`, `Makefile`, `scripts/generate_g4_candidate_manifest.mjs`, `tests/test_generate_g4_candidate_manifest.py`, `tests/test_makefile_candidate_manifest.py`, `odd/tasks/g4-candidate-manifest-develop.md`.
- Do not alter `make parity`, capture producers, runtime APIs, or the pre-existing untracked `odd/tasks/g4-integration-delivery.md`.
- TDD mode: focused RED/GREEN; runners: `.venv/bin/python -m pytest tests/test_generate_g4_candidate_manifest.py tests/test_makefile_candidate_manifest.py -q` and any direct Node validation needed by the tests.
- Delivery strategy: ask-on-risk; expected test-heavy scope may exceed 400 lines, so report the measured result before delivery and request a documented exception if it does.
- No commit, push, PR, or merge is authorized until separately requested.

## Tasks
- [x] ODD-G4-MANIFEST-DEVELOP-001 Map the strict manifest schema and current G4 consumer contract.
  Route: delegated explorer (4-file rule).
  Evidence: current `capture.mjs` requires schema `taxa.g4-capture.manifest/1`, an entry matching the candidate URL, and a non-empty literal marker; generated entries must carry URL, HTML basename, raw-byte SHA-256, status 200, and `data-testid="g4-probe-marker"`. The generator is offline and validates HTML/URL/output before an atomic write; no historical patch is copied.
- [x] ODD-G4-MANIFEST-DEVELOP-002 Add RED/GREEN generator, Make target, package script, and hermetic contract coverage.
  Route: delegated writer (multi-file write rule).
  Evidence: RED observed first (`23 failed, 13 passed in 2.36s` — the 13 passing are weaker "non-zero on missing script" assertions and the Makefile parity-unchanged structural guard); GREEN observed after implementation (`36 passed in 3.06s`). Implementation is offline: validates --candidate-html (exists, non-empty, contains the literal `data-testid="g4-probe-marker"` substring), validates --candidate-url (clean http(s) — rejects file://, javascript:, data:, ws://, ftp://, embedded credentials, whitespace/control chars), computes SHA-256 from raw HTML bytes, and atomically writes only the manifest with schema `taxa.g4-capture.manifest/1` and entry fields `url`/`path`/`expectedContentSha256`/`expectedStatus=200`/`expectedDOMMarker`. The Make target requires CANDIDATE_URL and CANDIDATE_MANIFEST, defaults CANDIDATE_HTML=out/index.html, preflights `command -v node` and the generator script, and shells out to the offline generator ONLY (no install, no `next build`, no `mkdir -p` leak, no service start). `make parity` remains byte-for-byte intact (`test_make_parity_recipe_unchanged_by_candidate_manifest_target` passes — all canonical structural invariants from the pre-#246 parity contract still present in the `parity` recipe). `package.json` exposes `g4:candidate-manifest` for direct npm access. Total authored scope is 1034 new lines across the generator (239) + two test files (442 + 353), with the tracked diff staying at 79 lines — exceeds the 400-line total-content threshold anticipated by this task's ask-on-risk clause; tracked diff remains well under the threshold.
- [x] ODD-G4-MANIFEST-DEVELOP-003 Independently verify the focused producer/Make contracts and final diff.
  Route: delegated verifier.
  Evidence: producer/Make tests (36 passed), parity tests (24 passed), and `git diff --check` all passed; scope is allowed-only. Total implementation content is 1,113 lines (1,164 including this task record), exceeding the 400-line ask-on-risk threshold.
- [x] ODD-G4-MANIFEST-DEVELOP-004 Resolve the oversized delivery strategy.
  Route: user decision.
  Evidence: user explicitly accepted one documented size-exception PR, keeping the generator, Make target, and all hermetic proofs together.
- [ ] ODD-G4-MANIFEST-DEVELOP-005 Commit and publish the approved size-exception delivery.
  Route: user-authorized delivery.
  Evidence: Conventional Commit and PR link #246, carry exactly `type:bug`, document the size exception, and remain unmerged.

## Acceptance criteria
- `make g4-candidate-manifest CANDIDATE_URL=<http(s) URL> CANDIDATE_MANIFEST=<path>` uses an already-built candidate HTML file and produces a strict manifest.
- Missing/invalid input fails closed before writing a manifest or running parity capture.
- The generator validates the G4 marker expected by the capture contract.
- No target installs dependencies, builds Next output, starts services, or weakens `make parity`.

## Implementation results
- Tracked diff: 2 files, +41/-2 = 43 lines net (`Makefile`, `package.json`).
- New (untracked, intended) files: `scripts/generate_g4_candidate_manifest.mjs` (239 lines), `tests/test_generate_g4_candidate_manifest.py` (442 lines), `tests/test_makefile_candidate_manifest.py` (353 lines).
- Total authored content for this slice: 1034 new lines + 79 lines of tracked diff.
- `git diff --check` clean (no output, exit 0).
- Pre-existing untracked `odd/tasks/g4-integration-delivery.md` not touched (still at its pre-implementation size and content).
- Task-002 evidence: focused tests `36 passed in 3.06s`; combined with `tests/test_makefile_parity.py` (24 passed) the merge-verification suite is `60 passed in 9.95s`.

## Progress
- #245 merged as PR #350 (`670d9af`).
- Independent verification is GREEN. The user explicitly accepted one documented size-exception PR for the 1,113-line implementation; commit and publication are authorized, but merging remains a separate decision.
