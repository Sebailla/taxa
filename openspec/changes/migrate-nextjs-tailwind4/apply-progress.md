# Apply Progress: migrate-nextjs-tailwind4

> Hybrid-mode persistence artifact. Mirrors the structured
> apply-progress in Engram (`topic_key` = `sdd/migrate-nextjs-tailwind4/apply-progress`).
>
> **Reconstruction notice**: this change has **no work delivered** to
> `origin/develop` yet. The current worktree
> (`taxa-worktrees/migrate-nextjs-tailwind4-pr1`) holds planning
> artefacts plus untracked implementation files. The previous
> version of this file reported "7 / 35 tasks complete" for PR 1 +
> PR 2a; that count was a planning artefact, not delivered work.
> All 35 tasks are reconstruction pending per the updated
> `tasks.md` §Reconstruction Notice.

---

## Reconstruction State (supersedes prior apply batches)

| Sub-PR | Scope | LoC budget | Source files | Status |
|--------|-------|------------|--------------|--------|
| PR 1a.1 | Build-profile emitter | 296 | `scripts/emit_build_profile.mjs` + script-contract block of `tests/test_build_profile.py` | reconstruction pending |
| PR 1a.2 | Build-profile schema test | 241 | remainder of `tests/test_build_profile.py` | reconstruction pending |
| PR 1b.1 | Chromium pin | 247 | `scripts/verify_chromium.py` + chromium block of `tests/test_evidence_baseline.py` | reconstruction pending |
| PR 1b.2 | Evidence baseline | 250 | remainder of `tests/test_evidence_baseline.py` | reconstruction pending |
| PR 1b.3a | Hydration measurement script | 339 | `scripts/measure_hydration.py` + schema subset of `tests/test_hydration_timing.py` | reconstruction pending |
| PR 1b.3b | Hydration timing test | 181 | remainder of `tests/test_hydration_timing.py` | reconstruction pending |
| PR 2a | Layer scaffold | 409* | `tsconfig.json` + 5 barrels + 20 `.gitkeep` + `tests/test_module_layers.py` | `size:exception` **accepted** by the maintainer (2026-08-29); work unit in `taxa-worktrees/migrate-nextjs-tailwind4-2a` cleared for commit + push to `develop` as staged |
| PR 2b | ESLint config | 227 | `.eslintrc.cjs` + 3 fixtures + config+barrel blocks of `tests/test_no_restricted_imports.py` | reconstruction pending |
| PR 2c | ESLint triangulation | 259 | 20 fixtures + runtime-triangulation block of `tests/test_no_restricted_imports.py` | reconstruction pending |
| PR 2d | Taxonomy domain | 350 | `src/modules/taxonomy/domain/taxon.ts` + `tests/test_taxonomy_domain.py` | reconstruction pending |
| PR 2e | Domain purity guard | 176 | `tests/test_domain_purity.py` | reconstruction pending |
| PR 3 | Frontend-bootstrap (Tailwind 4, Makefile, static mount, search_urls) | TBD | not yet authored | reconstruction pending |
| PR 4 | Browser-state | TBD | not yet authored | reconstruction pending |
| PR 5 | Capability ports + delete legacy `web/*` | TBD | not yet authored | reconstruction pending |

\* **PR 2a line-count correction and accepted `size:exception`**: the
LoC budget column above shows the actual measured figure (**409**
code+test lines), not the earlier draft estimate (**377**). Breakdown:
`tsconfig.json` 45 + 5 barrels (`src/modules/<capability>/index.ts`)
115 + 20 layer `.gitkeep` placeholders 0 + `tests/test_module_layers.py`
249 = **409** (`wc -l` on the staged files). This **exceeds the 400-line
per-PR review budget** by **9 lines (+2.3 %)**. On **2026-08-29** the
maintainer was presented with the three options from the worker's
delegation contract — accept-with-flag (`size:exception`, commit as
staged), re-slice (split the test or one barrel into PR 2a'), or trim
(reduce the focused test) — and **explicitly chose accept-with-flag**.
The +9-line (+2.3 %) overrun is therefore an **authorized
`size:exception`**, not an open question: PR 2a ships as staged at 409
code+test lines against the 400-line budget, and the PR carries the
`size:exception` label. No further re-slicing or trimming is required.
This record documents the decision only; it changes no code or tests and
performs no commit or push.

**Total delivered to `develop`**: 0 / 14 sub-PRs.
**Total reconstruction pending**: 13 sub-PRs.
**Total staged in worktree, authorized for commit**: 1 sub-PR (PR 2a,
accepted `size:exception`).

### Reconstruction order (deterministic, sequential to `develop`)

```
1a.1 → 1a.2 → 1b.1 → 1b.2 → 1b.3a → 1b.3b → 2a → 2b → 2c → 2d → 2e → 3 → 4 → 5
```

Each sub-PR's base = `origin/develop` after the previous merge.
No stacked branches. No child PR bases. Every PR targets `develop`
directly per `AGENTS.md` §4.

### Worktree policy

- **Backup worktree** at `taxa-worktrees/migrate-nextjs-tailwind4-pr1`:
  read-only reference source of files for each sub-PR.
  Do **not** edit, rebase, or merge from it after this plan lands.
- **Reconstruction worktrees** spawned by the apply worker for each
  sub-PR: created under the user's home as siblings of the backup
  per CodeGraph guidance. Each worktree gets its own `.codegraph/`
  index; the CodeGraph-aware placement rule applies.

### Reconstruction manifest (per sub-PR)

For each sub-PR, the apply worker MUST:

1. Create a new worktree from `origin/develop` named
   `taxa-worktrees/migrate-nextjs-tailwind4-pr<N>`.
2. Copy only the files listed for that sub-PR in
   `tasks.md` §Reconstruction Notice (file list per sub-PR) from
   the backup worktree
   into the new worktree using `cp -p`. No edits on copy.
3. Run the focused test command (see the per-sub-PR task rows in
   `tasks.md` §Phases 1a.1–5). It MUST pass before any commit.
4. Run the runtime harness (see same table). It MUST exit 0 / return
   the expected output.
5. Conventional Commit with English subject (no AI trailer). PR body
   in Spanish per `AGENTS.md` §Hard Rules: `## Resumen`,
   `## Cambios`, `## Validación`, `## Lo que NO cambió`.
6. Open the PR against `develop` via the `branch-pr` skill.
7. On green CI: mark that sub-PR's tasks `[x]` in `tasks.md` and
   `tasks-es.md`; prepend a per-sub-PR batch record here and in
   `apply-progress-es.md`.
8. Continue to the next sub-PR by repeating from step 1 with a
   fresh worktree off the now-merged `develop`.

### Rollback boundary per sub-PR

Each sub-PR revert removes **only** its own files (see
`tasks.md` §Phases 1a.1–5 (file list per sub-PR) and the
   corresponding `Rollback boundary` note in this
   `apply-progress.md`. No
sub-PR touches `web/*`, `package.json`, `api/server.py`,
`Makefile`, `extension/manifest.json`, or PR 1 capture artefacts.

---

## Historical context — PR 2 (rejected, repartitioned)

The narrative below documents the original PR 2 unit (~1369 LoC)
that was rejected for exceeding the 400-line per-PR review budget.
The work is preserved here for reference; ownership of the
artefacts was repartitioned in the replanned `tasks.md`
§Phases 2a–2e (PR 2 → PR 2a–2e).

PR 2 closed tasks 2.1–2.7. Task 1.5 remained deferred to the
design phase. The user's chosen path was the chained-PR repartition
(2a–2e) over `size:exception`.

PR 1 (the evidence-only baseline) was originally shipped as a
single ~1554 LoC unit. After the same 400-line review rejected PR 2,
PR 1 is also repartitioned in this pass into six sub-PRs (1a.1,
1a.2, 1b.1, 1b.2, 1b.3a, 1b.3b).

The two repartitions together yield **14 sub-PRs** targeting
`develop` sequentially, each ≤ 400 lines authored.

## Workload / PR Boundary (post-reconstruction)

- Mode: **stacked-to-main chained PR** (sequential sub-PRs of Phase 1 + Phase 2).
- Total sub-PRs after reconstruction: **14** (1a.1, 1a.2, 1b.1, 1b.2, 1b.3a, 1b.3b, 2a, 2b, 2c, 2d, 2e, 3, 4, 5 — note 3, 4, 5 are single-PR per original plan).
- Each sub-PR ≤ 339 LoC authored, **except PR 2a at 409 code+test
  lines**, which ships under the maintainer-accepted `size:exception`
  (+9 lines, +2.3 % over the 400-line review budget).
- Each sub-PR's base = `origin/develop` after the previous sub-PR merges.
  No stacked branches. No child PR bases.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reconstruction sequence interrupted; partial merge of Phase 1 sub-PRs leaves the project in an inconsistent state. | Medium | Each sub-PR's focused test passes independently of subsequent sub-PRs. A stuck PR blocks only its successor, not the whole chain. |
| Backup worktree is edited accidentally during reconstruction; source files drift from plan. | High | Backup worktree is marked read-only at filesystem level; all reconstruction work happens in new worktrees branched off `develop`. |
| PR 3, 4, 5 file lists aren't yet itemised; future planning pass must update `tasks.md` §Phases 3–5 with explicit per-sub-PR file lists. | Medium | Phases 3, 4, 5 are kept under `not yet authored` in this pass; the apply worker is told to pause before PR 3 and update the per-sub-PR file lists. |
| Six new PRs (1a.x, 1b.x) plus five existing (2a–2e) inflates the total PR count the maintainers review. | Low | Each PR ≤ 400 lines; review focus stays narrow; chain strategy is `stacked-to-main` per the user's prior choice. |

## Status

**0 / 35 tasks delivered to `develop`.** PR 2a work unit is staged
in worktree `taxa-worktrees/migrate-nextjs-tailwind4-2a` (scaffold
+ test + tsconfig + OpenSpec evidence + Spanish mirrors); focused
test `tests/test_module_layers.py` passes 40 / 40 (RED → GREEN →
TRIANGULATE captured). At **409** code+test lines against the **400**-line
per-PR review budget, PR 2a carries an **accepted `size:exception`**:
on 2026-08-29 the maintainer explicitly authorized the +9-line (+2.3 %)
overrun, so the delivery choice is settled and PR 2a is cleared to
commit + push to `develop` as staged under the `size:exception` label.
Remaining sub-PRs (1a.x, 1b.x, 2b–2e, 3, 4, 5) are reconstruction
pending per `tasks.md` §Reconstruction Notice.

---

## Change log

- **2026-08-28** — Initial companion artifact created.
- **2026-08-28** — PR 1 + PR 2a batches reported complete; that
  state was a planning artefact and is superseded by this
  reconstruction pass.
- **2026-08-28** — Reconstruction pass: PR 1 split into six sub-PRs
  (1a.1, 1a.2, 1b.1, 1b.2, 1b.3a, 1b.3b); PR 2 split into five
  sub-PRs (2a–2e); PR 3, 4, 5 kept as single PRs per original plan.
  All 14 sub-PRs target `develop` directly (no stacked branches, no
  child bases). Backup worktree locked as read-only reference.
  Spanish mirror updated in lockstep.
- **2026-08-29** — PR 2a work unit staged in dedicated worktree
  `taxa-worktrees/migrate-nextjs-tailwind4-2a`. Files added:
  `tsconfig.json` (strict mode + 5 capability path aliases),
  `src/modules/{taxonomy,research,design-system,browser-state,app-shell}/index.ts`
  (5 empty barrels), `src/modules/{capability}/{presentation,application,domain,infrastructure}/.gitkeep`
  (20 layer placeholders), `tests/test_module_layers.py` (40 focused
  assertions). OpenSpec evidence migrated and versioned:
  `openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks}.md` +
  `specs/modular-architecture/spec.md`; Spanish mirrors under
  `documents-es/openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks}-es.md`
  + `specs/modular-architecture/spec-es.md`. Subsequent sub-PRs
  continue under the same reconstruction plan.
- **2026-08-29** — PR 2a `size:exception` **accepted**. Measured size is
  **409** code+test lines (`tsconfig.json` 45 + 5 barrels 115 + 20 layer
  `.gitkeep` placeholders 0 + `tests/test_module_layers.py` 249) against
  the **400**-line per-PR review budget — an overrun of **+9 lines
  (+2.3 %)**. The maintainer explicitly authorized that exception rather
  than re-slicing or trimming, so PR 2a ships as staged with the
  `size:exception` label and the delivery choice is no longer pending.
  This record changes no code or tests and performs no commit or push.
  Spanish mirror updated in lockstep.