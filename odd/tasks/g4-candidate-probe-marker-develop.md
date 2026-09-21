# Restore the G4 candidate probe marker on develop

## Objective
Resolve approved issue #245 by adding the strict, hydration-safe candidate DOM probe marker required by G4 capture to the current `develop` frontend.

## Problem
Current `src/app/layout.tsx` has no `data-testid="g4-probe-marker"`. The historical integration patch cannot be replayed because its App Router context diverged from current `develop`, so the behavior must be implemented and verified against the present layout contract.

## Scope
- Add a static, hidden, hydration-safe marker to the current App Router root layout.
- Add focused hermetic regression coverage for the marker's source-level contract.
- Do not change G4 capture tooling, Makefile parity behavior, runtime APIs, or unrelated App Router topology guards.

## Constraints
- Approved issue: #245 (`bug: add strict G4 candidate probe marker`).
- Branch: `fix/g4-candidate-probe-marker-develop` from current `develop` (`bb87aed`).
- Allowed edit surfaces: `src/app/layout.tsx`, `tests/test_g4_candidate_probe_marker.py`, `odd/tasks/g4-candidate-probe-marker-develop.md`.
- Exclude pre-existing `odd/tasks/g4-integration-delivery.md` and all other untracked artifacts.
- TDD mode: focused RED/GREEN contract test; runner: `.venv/bin/python -m pytest tests/test_g4_candidate_probe_marker.py -q`.
- Delivery strategy: ask-on-risk; expected scope is under 400 authored lines.
- No commit, push, PR, or merge is authorized by this implementation request.

## Tasks
- [x] ODD-G4-PROBE-DEVELOP-001 Add a RED/GREEN marker contract and implement the marker in the current root layout.
  Route: delegated writer (multi-file write rule).
  Evidence: RED observed before implementation; marker has exact `data-testid`, remains hidden from visual UI and assistive semantics, and no prohibited behavior is introduced.
- [x] ODD-G4-PROBE-DEVELOP-002 Independently verify the focused contract and inspect the final diff.
  Route: delegated verifier.
  Evidence: focused marker tests (9 passed), topology guard (2 passed), and `git diff --check` all passed; tracked diff is only `src/app/layout.tsx`, with the allowed new test/task files untracked.
- [ ] ODD-G4-PROBE-DEVELOP-003 Commit the verified work unit when explicitly authorized.
  Route: awaiting user delivery decision.
  Evidence: one Conventional Commit includes the layout, focused test, and task record; no pre-existing untracked artifact is staged.

## Acceptance criteria
- Built candidate markup can expose an element carrying `data-testid="g4-probe-marker"`.
- The marker is static and does not alter visible layout, focus order, or accessible content.
- Focused regression coverage fails without the marker and passes with it.

## Progress
- Triage on current `develop` found #245 and #246 are still open while the historical G4 foundation is already represented.
- #245 is selected first because it is the smaller independent contract; #246 remains a dependent follow-up.
- Implemented `<span hidden data-testid="g4-probe-marker" />` in `src/app/layout.tsx`, placed at the top of `<body>` so it is the first child before `{children}`. The HTML5 `hidden` attribute sets `display: none` AND removes the element from the accessibility tree in one place; `<span>` is non-focusable and the element is self-closing with no text content, so focus order, visible layout, and accessible content stay unchanged.
- RED observed (pre-implementation, with the marker absent): `6 failed, 3 passed in 0.01s` — the six failures are exactly the marker-dependent tests (`test_layout_authored_an_element_with_probe_marker_testid`, `test_layout_marker_is_static_with_no_handlers_or_hooks`, `test_layout_marker_has_no_jsx_expression_in_opening_tag`, `test_layout_marker_is_hidden_from_visual_and_accessibility_tree`, `test_layout_marker_is_not_focusable`, `test_layout_marker_has_no_text_content`); the three passing tests are the file-existence + expression-form + topology-guard checks that stay green in either state.
- GREEN observed (post-implementation): `9 passed in 0.01s`. `git diff --check` is clean (no output, exit 0). Diff stays strictly within the allowed edit surfaces (`src/app/layout.tsx`, `tests/test_g4_candidate_probe_marker.py`, this task file); the pre-existing untracked `odd/tasks/g4-integration-delivery.md` was not touched, and no other tracked files were modified. The chain-topology guard test (`tests/test_app_shell_render.py::test_app_file_does_not_import_owners_of_later_prs`) still passes — `layout.tsx` continues to import only `next`, `next/font/google`, and `./globals.css`.
- Independent verifier reproduced: focused marker tests `9 passed`; topology guard `2 passed`; `git diff --check` clean. Delivery is pending explicit commit authorization; no files have been staged or committed.
