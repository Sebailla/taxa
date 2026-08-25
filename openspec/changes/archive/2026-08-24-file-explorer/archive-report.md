# File Explorer — Archive Report (closed change)

> **Source**: Engram observation `sdd/file-explorer/archive-report` (id 4235). Verbatim — Engram frontmatter stripped.

## Status

**PASS** — archived 2026-08-24 (system clock; orchestrator hint of
2026-08-25 was stale).

## Key metrics

- 24/24 tasks `[x]` (21 implementation + 3 parent-owned lifecycle).
- 0 unchecked implementation tasks (Final Task Completion Gate PASSED).
- 2 PRs merged: PR #25 backend (`d8bda4b`) + PR #26 frontend (`6d6085e`).
- 835 lifetime changed lines across both PRs (294 backend + 541
  frontend).
- 24 new backend tests (`tests/test_api_file_explorer.py`); baseline
  63/8 → 87/8 (no regressions).
- `gentle-ai sdd-verify` ran with **PASS**; observation id 4234.
- `gentle-ai sdd-attempt status`: `complete: True`, `next_action: complete`.
- `size:exception` approved for PR 2 (orchestrator carve-out).

## Domain synced

- `research` (NEW canonical) — full domain spec copied verbatim from
  `openspec/changes/archive/2026-08-24-file-explorer/specs/research/spec.md`
  to `openspec/specs/research/spec.md` via archive-time sync fallback
  (orchestrator pre-approved). No ADDED/MODIFIED/REMOVED delta; the
  change spec IS the canonical spec. 398 lines, identical bytes.

## Active same-domain conflict

- None. The other active change (`add-freshwater-and-search`) uses the
  legacy flat `spec.md` layout and does not touch the `research`
  domain.

## Archived path

```
openspec/changes/archive/2026-08-24-file-explorer/
```

Contents preserved as audit trail: `proposal.md`, `design.md`,
`specs/research/spec.md`, `tasks.md`, `apply-progress.md`,
`verify-report.md`, `archive-report.md`.

## Engram observation IDs (this change)

| Artifact | Topic key | Obs id |
| --- | --- | --- |
| Init refresh | `sdd-init/taxa` | 4217 |
| Proposal | `sdd/file-explorer/proposal` | 4221 |
| Spec | `sdd/file-explorer/spec` | 4222 |
| Design | `sdd/file-explorer/design` | 4223 |
| Tasks | `sdd/file-explorer/tasks` | 4224 |
| Apply progress (PR 1) | `sdd/file-explorer/apply-progress` | 4225 |
| Apply progress (PR 2) | `sdd/file-explorer/apply-progress-pr2` | 4228 (merge) |
| Verify report | `sdd/file-explorer/verify-report` | 4234 |
| **Archive report (this obs)** | `sdd/file-explorer/archive-report` | assigned at save |

## Follow-up actions for the orchestrator

- Commit the canonical sync (`openspec/specs/research/spec.md`) to git
  via `gh api` REST workaround (this archive phase deliberately did
  not call `git commit` per the bash-harness carve-out).
- No follow-up archive work expected — canonical sync is final.

## Carry-forward context for future changes

- File explorer uses the existing `Browser` header tab; mount is
  opt-in via `mountFileExplorer(state.selected)` from `web/nav.js`.
- Path safety: `_safe_resolve(root, rel)` in `api/server.py` is the
  canonical traversal guard; reuse it (do not duplicate) in any future
  research-folder endpoint.
- CDN libraries are pinned in `web/index.html` (mammoth@1.8.0,
  xlsx@0.18.5, epubjs@0.3.93); bumping requires manual smoke per the
  inline reproducibility comment.
- Frontend has no JS test runner; new Browser-tab behavior is verified
  via the manual checklist in `apply-progress.md` PR 2 section.
- `_STREAM_CAP_BYTES = 100 MB` is the canonical streaming cap; reuse
  it for any future streaming endpoint that touches research folders.
