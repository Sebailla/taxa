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
| `complete-frontend-migration.md` | superseded (OpenSpec `complete-taxa-frontend-migration` → SUPERSEDED.md) | n/a |
| `supersede-frontend-migration-plan.md` | superseded (PR #143 closed without merge per this plan) | n/a |
| `w6-3-record-and-w6-4-chain.md` | PR #364 + #365 + #366 + #367 | merged chain |
| `test-cleanup.md` | PR #400 + #401 + #402 | `33997e8` + `56b2166` + `0e975df` |

## What stays in `odd/tasks/`

Empty after wave 2. `odd/tasks/` is reserved for drafts whose work has not
yet been merged to `develop`. The next in-flight task should land there.

## Archived-but-not-merged

Wave 2 includes `complete-frontend-migration.md` and
`supersede-frontend-migration-plan.md`, which were **never executed as
planned** (the 16-child PR #143 chain was superseded by direct-to-develop
ODD deliveries, and PR #143 was closed without merge). They are preserved
here as historical records of the delivery decision. The concise reader
record for the actual delivery lives at
`openspec/changes/complete-taxa-frontend-migration/SUPERSEDED.md`.