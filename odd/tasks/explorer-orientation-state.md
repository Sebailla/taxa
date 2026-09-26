# Explorer orientation and state persistence

## Objective
Improve first-visit orientation in Explorer without eagerly expanding a potentially large tree, and restore the user's research working set when returning to the route.

## User decisions and constraints
- User selected orientation controls/counts and browser-local persistence of search, selection, and expanded paths; accepted the privacy warning.
- Keep the tree collapsed by default. Keep all `localStorage` access behind the typed `browser-state` boundary; Research helpers remain pure.
- Strict TDD; existing exact runners are the project pytest suite and `npx tsc --noEmit --strict --project tsconfig.json`.
- Issue-first delivery: approved issue #421. User authorized commits, stacked PRs targeting `develop`, one additional slicing pass, and documented size exceptions for the five identified cohesive over-budget slices.
- Preserve unrelated untracked `tests/test_5c_2_b_react_harness.py` and `tools/react-e2e-harness/**` untouched.

## Work units

| Unit | Status / evidence | Commit / delivery |
|---|---|---|
| 1. Feature request form | Done; issue #421 approved. | PR #422, 86 lines. |
| 2. Freshwater selector correction | Done; scoped locator fix. | PR #423, 28 lines. |
| 3. Explorer orientation kernel | Done; pure orientation helpers. | PR #424, 254 lines. |
| 4. Explorer orientation UI | Done; accurate counts, accessible expand/collapse-all; collapsed by default. | PR #425, 656 lines, authorized documented exception. |
| 5. Browser-state model | Done: versioned typed state and canonical key/default; fixture repair verified 43 browser-state tests and strict tsc. | `859121b`, correction `f1719c8`; PR #426, 210 lines. |
| 6. Browser-state store | Done: typed read/write/clear/subscribe; 49 browser-state tests passed, strict tsc clean. | `2249497`, stack-alignment merge `5f3c343`; PR #427, 451 lines, authorized documented exception. |
| 7. Hook and aggregate reset | Done: typed per-key hook, public barrel export, reset integration; 77 passed, 2 expected legacy-fixture skips, strict tsc clean. | `f4a5c0a`; PR #428, 211 lines. |
| 8. Enforce persistence bounds at the canonical store boundary | Done: independently verified with 52 browser-state tests, strict TypeScript, clean `git diff --check`, and exact read/write byte-boundary cases (65,535 accepted; 65,538 rejected). Native ASSESS was unassessable due to untracked tool directories; the separate risk-gated verifier passed. | Commit `378f964`; PR #429 OPEN, base `feat/explorer-state-hook-reset`, head `feat/explorer-state-bounds`, linked issue #421, sole label `type:bug`, 389 additions + 8 deletions. No CI checks are reported yet. |
| 9. Pure Research persistence helpers | Done under Strict TDD: canonical key/version/cap parity, comment-aware barrel checks, stable first-seen dedup, and raw-byte rejection before `JSON.parse`. Independent verification passed 230 Research tests, 1 unrelated DOM-server skip (`127.0.0.1:8765` unavailable), 52 browser-state tests, strict TypeScript, and `git diff --check`. Exact size: 2,241 changed lines; native ASSESS was unassessable due untracked toolchain entries, so the separate verifier passed. | Commit `63ce31a`; PR #430 OPEN, base `feat/explorer-state-bounds`, head `feat/explorer-research-storage-pr430`, issue #421, sole `type:feature` label, 2,231 additions + 10 deletions. No CI checks are reported yet. User authorized a documented size exception for this cohesive unit. |
| 10. Explorer persistence integration | Done under Strict TDD: Explorer.tsx consumes `useExplorerState`, lazy-initialisers `expanded` / `selectedPath` / `searchQuery` from the persisted snapshot, validates against the freshly loaded tree, and persists the working set on every user change. Storage never read during render. Independent verification passed 314 Research / hydration / browser-state tests (2 unrelated source-missing skips), strict TypeScript clean, `git diff --check` clean. Native ASSESS was unassessable due untracked toolchain entries; separate verifier passed. | Commit `606580f` (`feat(explorer): wire hydration-safe persistence integration`); PR #431 OPEN, base `feat/explorer-research-storage-pr430` (PR #430 head), head `feat/explorer-state-integration-pr431`, issue #421, sole `type:feature` label, 680 additions + 10 deletions = 690 changed lines (user-authorized documented exception for this cohesive hydration-safe integration + contract pin suite). No CI checks are reported yet. |

## Delivery state (post-merge)
- Repository: `Sebailla/taxa`; issue #421 is **closed** by the chain.
- All 10 stacked PRs merged into `develop`. PR #422 was merged directly via the GitHub UI at `70cc308`. PRs #423–#431 were consolidated into PR #432 because GitHub's auto-merge-base algorithm flagged the stacked chain as conflicting after #422 merged; PR #432 carried the rest as merge commits and was merged into `develop` at `39a9f4e` after the Smoke tests CI check passed.
- Merge commits on develop (newest → oldest): `39a9f4e` (PR #432), `f2bcbaa` (PR #431), `eccb76a` (PR #430), `e6c69b2` (PR #429), `4d7da62` (PR #428), `adc4663` (PR #427), `47b907d` (PR #426), `d2a204b` (PR #425), `b7ca530` (PR #424), `360009a` (PR #423), `70cc308` (PR #422).
- PRs #423–#431 are individually closed with a comment pointing to the consolidation PR #432. PR #210 (a docs PR) remains open and is unrelated to this chain.
- Local and remote feature branches for #422–#431 cleaned up. The 9 temporary worktrees under `/var/folders/.../T/taxa-*` were removed; only the main workspace `/Users/sebailla/Developer/taxa` remains.
- Slice-relevant test evidence on the consolidated develop: `.venv/bin/python -m pytest tests/test_browser_state_keys.py tests/test_browser_state_hydration_guard.py tests/test_research_explorer_mount.py tests/test_web_toggle.py -v` → 313 passed, 20 skipped. The 20 skips are pre-existing FastAPI-server + chromium-availability hermetic guards, not regressions.
- Strict TypeScript: `npx tsc --noEmit --strict --project tsconfig.json` → exit 0.
- Pre-existing infrastructure test failures (`tests/test_smoke.py::test_static_app_js_served`, `tests/test_app_shell_render.py::test_out_explorer_html_still_builds`) require a built Next.js static export and a running FastAPI server — environmental, not regressions.
- PR #432 smoke tests CI: PASS (`Smoke tests completed successfully` after 4m 11s on commit `f2bcbaa`).

## Initial full-suite evidence
`.venv/bin/python -m pytest tests/ etl/tests/ -v --ignore=tests/test_5c_2_b_react_harness.py` passed with 2,096 passed, 30 skipped, 0 failed after the Freshwater selector correction. Preserved harness test was excluded and remains untouched.

## Worktree + branch cleanup
- Removed 9 temporary worktrees under `/var/folders/.../T/taxa-{pr4,pr5,pr6,pr7,pr8,pr9,pr430,pr431,develop}.*` via `git worktree remove --force`. The parent tmp dirs were also removed.
- Pruned 17 stale local feature branches (the full Explorer chain plus older WIP branches) and 10 remote feature branches (`feat/explorer-issue-form`, `test/freshwater-source-selector`, `feat/explorer-orientation-{kernel,ui}`, `feat/explorer-state-{domain,store,hook-reset,bounds}`, `feat/explorer-research-storage-pr430`, `feat/explorer-state-integration-pr431`).
- Main workspace `/Users/sebailla/Developer/taxa` on branch `wip/explorer-state-integration` (commit `2249497`) was left intact; that branch predates the chain and remains available for any follow-up WIP work.
