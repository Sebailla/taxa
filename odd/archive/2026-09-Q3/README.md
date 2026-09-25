# ODD task archive — 2026-09 Q3

Working drafts from `odd/tasks/` that are no longer actionable, archived here
to keep `odd/tasks/` focused on in-flight work.

## Why these were archived

Each task file in this directory is a **local working draft** (0 commits in
git) that described a single feature branch + PR cycle. The work itself has
been merged into `develop` via the listed PR (or explicitly abandoned), so
the draft is now a historical artifact rather than active planning.

## Archive contents

### Wave 1 — Phase 2/3 design-system extract (PR #399, commit `9c0aa6f`)

| Draft | Merged via | Commit |
|---|---|---|
| `app-shell-navigation-rebuild.md` | PR #382 | `f02ed6e` |
| `explorer-search-shortcuts.md` | PR #384 | `351d683` |
| `design-system-extract.md` | PR #385 | `5853479` |
| `phase2-treerow-migrate.md` | PR #386 | `dfc09de` |
| `phase2-detailpanel-migrate.md` | PR #387 | `cd6a1a9` |
| `phase2-foldertab-migrate.md` | PR #388 | `3449d2d` |
| `phase2-appshell-migrate.md` | PR #389 | `dbcf9b4` |
| `phase2-explorer-migrate.md` | PR #390 | `d4fabcd` |
| `phase2-splitter-migrate.md` | PR #391 | `146c71b` |
| `phase3-globals-cleanup.md` | PR #392 | `1d1b6a5` |
| `close-skip-link-duplicate.md` | PR #394 | `f53f5d8` |
| `close-sticky-breakpoint.md` | PR #395 | `1e27c07` |
| `hoist-source-selector.md` | PR #396 | `d61ebc3` |
| `phase2-explorer-viewer-migrate.md` | PR #390 + #393 (implicit) | `d4fabcd` + `9debb9a` |

The 15th file (`g4-integration-delivery.md`) was **explicitly abandoned by the
user** per ODD-G4-INTEGRATION-005 — the plan itself records the abandonment
and is preserved here as a historical record of the G4 delivery decision.

### Wave 2 — Frontend-migration + browser-state + test-cleanup closure

24 additional drafts archived after the wave-1 ship. Every entry below is
either merged to `develop` via the listed PR(s) or explicitly superseded.

| Draft | Merged via | Commit |
|---|---|---|
| `repair-tailwind-next-pipeline.md` | PR #299 | `9c25ed8` |
| `resolve-nextjs-integration-details.md` | PR #298 | `9c25ed8` |
| `visible-taxonomy-tree.md` | PR #300 + #301 | `871d6f7` + `20a4bc3` |
| `native-tree-parity.md` | PR #302 + #306 + #307 + #308 | `346e641` + `0503ffc` + `3bcc0e4` + `c8ff6ee` |
| `taxonomy-detail-overview.md` | PR #309 | `a8ba85a` |
| `taxonomy-detail-search.md` | PR #310 | `5e1a208` |
| `taxonomy-detail-vernaculars.md` | PR #311 + #312 + #313 | merged chain |
| `taxonomy-detail-synonyms.md` | PR #314 + #315 + #316 | merged chain |
| `taxonomy-detail-folder.md` | PR #319 + #320 + #321 | merged chain |
| `enable-taxonomy-open-folder-action.md` | PR #323 | `0689ee4` |
| `taxonomy-detail-distribution.md` | PR #318 | `405ea2f` |
| `taxonomy-detail-discoverability.md` | PR #322 | `fb78bd7` |
| `prepare-next-static-cutover.md` | PR #326 | `67dcee3` |
| `typed-browser-state-prerequisite.md` | PR #327 → #335 (8-PR chain) | merged chain |
| `browser-state-playwright-hydration.md` | PR #336 → #341 (4-test chain + docs) | merged chain |
| `browser-state-taxonomy-active-source.md` | PR #342 + #343 + #344 + #346 | merged chain |
| `single-command-dev-launcher.md` | PR #347 | `774f577` |
| `g4-candidate-probe-marker-develop.md` | PR #348 | `311b4a6` |
| `g4-candidate-manifest-develop.md` | PR #349 | `fc07995` |
| `supersede-frontend-migration-plan.md` | superseded (PR #143 closed without merge per this plan) | n/a |
| `test-cleanup.md` | PR #400 + #401 + #402 | `33997e8` + `56b2166` + `0e975df` |

### Wave 3 — P1 render-puro refactor (this branch)

One additional draft archived after the wave-2 ship. The plan described a bounded refactor that has since merged.

| Draft | Merged via | Commit |
|---|---|---|
| `render-puro-file-tree-search.md` | PR #407 | `ebd4bfa` |

### Wave 4 — final state (no new archives)

No additional drafts to archive. `odd/tasks/` is at its minimum — only the two test-coupled files (`complete-frontend-migration.md` + `w6-3-record-and-w6-4-chain.md`) remain, both pinned by `tests/test_search_engine_consumer_manifest.py`'s W65-MANIFEST-008 audit (it reads both files by their `odd/tasks/` path; co-updating the test is out of scope for housekeeping passes).

Wave 4 closed the ODD housekeeping cycle with a documentation pass instead of a file-move pass:
- A top-level `odd/README.md` documents the directory structure + the
  `tasks/` + `archive/<quarter>/` rule + the 2 test-coupled
  exceptions + how to start a new plan / archive a finished one.

The 2026-Q3 archive ends here at 39 files (16 wave-1 + 22 wave-2 + 1 wave-3 = 39 archived drafts + this README).

## What stays in `odd/tasks/`

After wave 2, two drafts remain because they are **actively referenced by
`tests/test_search_engine_consumer_manifest.py`** (W65-MANIFEST-008 audit),
not because they describe in-flight work:

| Draft | Why it stays | Audit |
|---|---|---|
| `w6-3-record-and-w6-4-chain.md` | Test reads `odd/tasks/w6-3-record-and-w6-4-chain.md` to verify the W6.3 chain records the KEEP decision + the W65 manifest task | W65-MANIFEST-008 |
| `complete-frontend-migration.md` | Test reads `odd/tasks/complete-frontend-migration.md` to verify the W18 migration tracker carries the cutover task | W65-MANIFEST-008 |

The audit references both files by their `odd/tasks/` path, and the tests
are smoke-blockers. Moving the files to the archive would require
co-updating the test, which is out of scope for this housekeeping pass.
A future cleanup can relocate these (and update the test in the same PR).

## Archived-but-not-merged

Wave 2 includes `supersede-frontend-migration-plan.md`, which was
**never executed as planned** (the 16-child PR #143 chain was superseded
by direct-to-develop ODD deliveries, and PR #143 was closed without
merge). It is preserved here as a historical record of the delivery
decision. The concise reader record for the actual delivery lives at
`openspec/changes/complete-taxa-frontend-migration/SUPERSEDED.md`.