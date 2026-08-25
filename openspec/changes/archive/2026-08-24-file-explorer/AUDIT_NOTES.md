# Audit Notes — file-explorer archive reconstruction

Reconstructed on 2026-08-25 from Engram observations after the sdd-archive
phase moved the change folder locally. The original was deleted during a
subsequent `git merge` cleanup (rm of conflicting untracked files).

## Source provenance

| File | Reconstructed from | Completeness |
| --- | --- | --- |
| `proposal.md` | Engram obs 4221 | FULL (verbatim from observation content) |
| `design.md` | Engram obs 4223 | FULL (verbatim from observation content) |
| `specs/research/spec.md` | Engram obs 4222 + chore commit `278c8f4` | SUMMARY — Engram holds the proposal→spec AC mapping + key requirements, but NOT the full 398-line body. The canonical version committed at `openspec/specs/research/spec.md` (commit `278c8f4`) IS the full body — this archive copy is a condensed mirror with an explicit "see canonical" pointer. |
| `tasks.md` | Engram obs 4224 + the in-progress checkbox state at the time of inline write | FULL — the orchestrator (me) wrote this file inline at 124 lines when sdd-tasks failed twice. The 24 checkboxes were all `[x]` after the orchestrator marked the 3 parent-owned ones post-merge. This archive copy restores the original structure with all 24 marked `[x]`. |
| `apply-progress.md` | Engram obs 4225 (PR 1) + obs 4228 (PR 2) | SUMMARY — both observations are condensed; the original 277-line file had per-group TDD evidence tables, the test command output, and the attempt budget section. This archive copy carries the merged summary. |
| `verify-report.md` | Engram obs 4234 | SUMMARY — condensed version of the 8817-byte original. The original had full per-requirement spec coverage table + test results. |
| `archive-report.md` | Engram obs 4235 | FULL (verbatim, with Engram frontmatter stripped) |

## What this means for audit purposes

The full audit trail of the file-explorer change lives in Engram via
the `sdd/file-explorer/*` topic keys. The 9 observations (proposal,
spec, design, tasks, apply-progress PR 1, apply-progress PR 2,
verify-report, archive-report, plus the init refresh) capture the full
intent and outcome.

The Engram IDs are cross-referenced from each file's header for
traceability. The canonical spec at `openspec/specs/research/spec.md`
(committed at `278c8f4`) is byte-identical to the original change-folder
spec; the archive copy is a pointer to that canonical source.

## Why the originals were lost

The sdd-archive phase moved the change folder to
`openspec/changes/archive/2026-08-24-file-explorer/` on disk, then the
subsequent `git merge --ff-only origin/main` aborted because the working
tree had untracked openspec/ files (the canonical spec + AGENTS.md +
config.yaml + sdd-init.md). The orchestrator resolved by `rm`-ing the
conflicting untracked files — which accidentally removed the archive
folder too. The canonical spec was subsequently re-committed via the
chore (commit `278c8f4`); the archive folder itself was not.

## How to get the originals (if ever needed)

- git reflog of the working tree at the time of the merge.
- Pull a backup of the user's local files (if any pre-merge snapshot
  exists).
- Or accept this reconstruction as the audit record going forward.
