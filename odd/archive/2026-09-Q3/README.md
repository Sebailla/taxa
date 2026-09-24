# ODD task archive — 2026-09 Q3

Working drafts from `odd/tasks/` that are no longer actionable, archived here
to keep `odd/tasks/` focused on in-flight work.

## Why these were archived

Each task file in this directory is a **local working draft** (0 commits in
git) that described a single feature branch + PR cycle. The work itself has
been merged into `develop` via the listed PR, so the draft is now a historical
artifact rather than active planning.

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

The 14th file (`g4-integration-delivery.md`) was **explicitly abandoned by the
user** per ODD-G4-INTEGRATION-005 — the plan itself records the abandonment
and is preserved here as a historical record of the G4 delivery decision.

## What stays in `odd/tasks/`

Only drafts whose work is **not yet merged into develop**:

- `phase2-explorer-viewer-migrate.md` — seventh + final Phase 2 consumer
  migration; partial plan, mostly coverage tests + specialized reasoning for
  Viewer panels.
- `test-cleanup.md` — close 12 pre-existing test failures left on develop
  after the Next.js migration.

## Project docs vs ODD drafts

`odd/tasks/` also holds project-level feature docs (`taxonomy-detail-*`,
`complete-frontend-migration.md`, `w6-3-record-and-w6-4-chain.md`, etc.).
Those are **not** ODD working drafts — they are versioned project artifacts
committed to git alongside their feature work. They stay in `odd/tasks/`
regardless of merge status.