# Apply Progress: migrate-nextjs-tailwind4

> Hybrid-mode persistence artifact. Mirrors the structured
> apply-progress in Engram (`topic_key` = `sdd/migrate-nextjs-tailwind4/apply-progress`).
>
> **Reconciliation notice (2026-08-29)**: this change has **6 / 14
> sub-PRs delivered to `origin/develop`** based on commit history
> (1a.1, 1b.1, 2a, 2b, 2c, 2d — see per-row provenance below);
> **5 / 14 sub-PRs are uncertain** because named-slice provenance
> cannot be determined from commit boundaries (1a.2, 1b.2,
> 1b.3a, 1b.3b, 2e); **3 / 14 sub-PRs remain reconstruction
> pending** (PR 3, PR 4, PR 5). The prior "7 / 35 tasks
> complete" framing was a planning artefact and is superseded.

---

## Reconstruction State (supersedes prior apply batches)

| Sub-PR | Scope | LoC budget | Source files | Status |
|--------|-------|------------|--------------|--------|
| PR 1a.1 | Build-profile emitter | 296 | `scripts/emit_build_profile.mjs` + script-contract block of `tests/test_build_profile.py` | delivered — origin/develop #75 (`646f00d`) ships `scripts/emit_build_profile.mjs` + entire `tests/test_build_profile.py` (321 LoC) |
| PR 1a.2 | Build-profile schema test | 241 | remainder of `tests/test_build_profile.py` | uncertain — #75 added `tests/test_build_profile.py` whole; named-slice boundary with 1a.1 (script-contract block vs schema remainder) not determinable from commit history |
| PR 1b.1 | Chromium pin | 247 | `scripts/verify_chromium.py` + chromium block of `tests/test_evidence_baseline.py` | delivered — origin/develop #76 (`97776de`) ships entire `tests/test_evidence_baseline.py` (829 LoC); `scripts/verify_chromium.py` predates the slice (#3c16dad, feat(security)) |
| PR 1b.2 | Evidence baseline | 250 | remainder of `tests/test_evidence_baseline.py` | uncertain — #76 added `tests/test_evidence_baseline.py` whole; named-slice boundary with 1b.1 (chromium block vs evidence remainder) not determinable |
| PR 1b.3a | Hydration measurement script | 339 | `scripts/measure_hydration.py` + schema subset of `tests/test_hydration_timing.py` | uncertain — #77 (`9d2e8a4`) ships `scripts/measure_hydration.py` (189 LoC) + entire `tests/test_hydration_timing.py` (331 LoC); named-slice boundary with 1b.3b (script + schema subset vs remainder) not determinable |
| PR 1b.3b | Hydration timing test | 181 | remainder of `tests/test_hydration_timing.py` | uncertain — #77 added `tests/test_hydration_timing.py` whole; named-slice boundary with 1b.3a not determinable |
| PR 2a | Layer scaffold | 409* | `tsconfig.json` + 5 barrels + 20 `.gitkeep` + `tests/test_module_layers.py` | delivered — origin/develop #78 (`3e596db`); `size:exception` accepted (409 code+test lines, +9 / +2.3 % over 400-line budget) |
| PR 2b | ESLint config (literal + alias enforcement) | 388 | `.eslintrc.cjs` + `scripts/eslint-fixtures/{barrel_import,deep_import,deep_import_research}.js` + `tests/test_no_restricted_imports.py` | delivered — origin/develop #80 (`00560db`); under 400-line budget (-12 / -3.0 %) |
| PR 2c | ESLint triangulation | 239 | 20 fixtures + runtime-triangulation block of `tests/test_no_restricted_imports.py` | delivered — origin/develop #82 (`0bd294a`); under 400-line budget (-161 / -40.25 %) |
| PR 2d | Taxonomy domain | 350 | `src/modules/taxonomy/domain/taxon.ts` + `tests/test_taxonomy_domain.py` | delivered — origin/develop #84 (`8315c0b`); 347 code+test lines |
| PR 2e | Domain purity guard | 176 | `tests/test_domain_purity.py` | uncertain — #86 (`53a33be`) ships `tests/test_domain_purity.py` (320 LoC) but exceeds the 176 LoC plan budget; named-slice provenance uncertain (plan budget vs delivered size mismatch) |
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

\*\* **PR 2b measured size and alias-form expansion**: the PR 2b row above
shows the actual measured figure (**388** code+test lines), not the
original forecast (**227**). Breakdown: `.eslintrc.cjs` 66 +
`scripts/eslint-fixtures/barrel_import.js` 4 +
`scripts/eslint-fixtures/deep_import.js` 4 +
`scripts/eslint-fixtures/deep_import_research.js` 5 +
`tests/test_no_restricted_imports.py` 309 = **388** (`wc -l` on the
staged files). This **fits the 400-line per-PR review budget** with
**-12 lines (-3.0 %)** of headroom after the trim pass. The growth
from the original 227-line forecast comes entirely from the
maintainer's explicit alias-form enforcement expansion: the literal
`src/modules/<cap>/<layer>/*` rule alone (the original forecast)
ships in ~32 LoC of patterns inside `.eslintrc.cjs`, but the alias
form `@taxa/<cap>/<layer>/*` adds another ~32 LoC of patterns plus
~50 LoC of alias-form triangulation tests in the test file, plus
~30 LoC for the `_load_eslint_patterns` Node-loading helper that lets
the test assert on the *resolved* config (rather than scanning source
text, which would have broken the programmatic-pattern-array
refactor). PR 2b ships under the 400-line budget without a
`size:exception`; the expanded alias coverage is part of the design
contract, not an overrun.

**Total delivered to `develop`**: 6 / 14 sub-PRs (1a.1, 1b.1, 2a, 2b,
2c, 2d — based on origin/develop commit history).
**Total uncertain (named-slice provenance)**: 5 / 14 sub-PRs
(1a.2, 1b.2, 1b.3a, 1b.3b, 2e — file content present in
`origin/develop`, named-slice boundary not determinable from commit
history).
**Total reconstruction pending**: 3 / 14 sub-PRs (PR 3, PR 4, PR 5).

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
- Each sub-PR ≤ 339 LoC authored, **except**:
  - **PR 2a at 409 code+test lines**, which ships under the
    maintainer-accepted `size:exception` (+9 lines, +2.3 % over
    the 400-line review budget).
  - **PR 2b at 388 code+test lines**, which ships **under the
    400-line review budget** (-12 lines, -3.0 % headroom). PR 2b's
    expanded surface (vs. the original 227-line forecast) is the
    maintainer's explicit alias-form enforcement expansion
    (`@taxa/<cap>/<layer>/*` in addition to
    `src/modules/<cap>/<layer>/*`) plus the corresponding
    alias-form triangulation tests.
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

**6 / 14 sub-PRs delivered to `develop`** based on commit history
(1a.1, 1b.1, 2a, 2b, 2c, 2d); **5 sub-PRs are uncertain**
(named-slice provenance not determinable: 1a.2, 1b.2, 1b.3a,
1b.3b, 2e); **3 sub-PRs remain reconstruction pending**
(PR 3, PR 4, PR 5). Prior PR 2a / 2b / 2c staging records below
are preserved as historical context — those units have since been
delivered to `develop` via PRs #78 (#3e596db), #80 (#00560db),
and #82 (#0bd294a). PR 2a work unit was staged in worktree
`taxa-worktrees/migrate-nextjs-tailwind4-2a` (scaffold
+ test + tsconfig + OpenSpec evidence + Spanish mirrors); focused
test `tests/test_module_layers.py` passes 40 / 40 (RED → GREEN →
TRIANGULATE captured). At **409** code+test lines against the **400**-line
per-PR review budget, PR 2a carries an **accepted `size:exception`**:
on 2026-08-29 the maintainer explicitly authorized the +9-line (+2.3 %)
overrun, so the delivery choice was settled (accepted 2026-08-29) and
PR 2a has since been delivered to `develop` under the
`size:exception` label.

PR 2b work unit was staged in worktree
`taxa-worktrees/migrate-nextjs-tailwind4-2b` (delivered via PR #80
/ #00560db) (ESLint config + 3 fixtures
+ focused test + OpenSpec progress records + Spanish mirror); focused
test `tests/test_no_restricted_imports.py` passes 32 / 32 (RED → GREEN
→ TRIANGULATE → REFACTOR captured; runtime ESLint invocation of all
40 `(capability × layer × form)` combinations confirmed). At **388**
code+test lines against the **400**-line per-PR review budget, PR 2b
shipped **under budget** (-12 lines, -3.0 % headroom). The expanded
surface vs. the original 227-line forecast is the maintainer's
explicit alias-form enforcement expansion
(`@taxa/<cap>/<layer>/*` in addition to `src/modules/<cap>/<layer>/*`)
plus the corresponding alias-form triangulation tests — no
`size:exception` is required.

PR 2c work unit was staged in worktree
`taxa-worktrees/migrate-nextjs-tailwind4-2c` (delivered via PR #82
/ #0bd294a) (20 literal fixtures +
runtime-triangulation block of `tests/test_no_restricted_imports.py` +
OpenSpec progress records + Spanish mirror); focused test
`tests/test_no_restricted_imports.py` passes 102 / 102 (32 PR 2b + 70
PR 2c; RED → GREEN → TRIANGULATE → REFACTOR captured). Runtime ESLint
invocation proves all **40 deep-import forms** are rejected: 20 literal
fixtures (`src/modules/<cap>/<layer>/deep`) + 20 dynamic alias inputs
(`@taxa/<cap>/<layer>/deep` in `tmp_path`), parametrized across the full
`CAPABILITIES × LAYERS` matrix. Public barrels stay allowed under both
spelling forms (10 barrel-allow cases). At **239** code+test lines
against the **400**-line per-PR review budget, PR 2c shipped
**under budget** (-161 lines, -40.25 % headroom). Breakdown: 20 fixtures
(`scripts/eslint-fixtures/deep_import_<cap>_<layer>.js`) at 5 LoC each
= **100** + `tests/test_no_restricted_imports.py` delta of **139**
(`wc -l` on the staged file = 448 vs the PR 2b baseline 309) = **239**
(`wc -l` on the staged files). No `size:exception` is required.

Remaining sub-PRs (PR 3, PR 4, PR 5) are reconstruction pending
per `tasks.md` §Reconstruction Notice.

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
- **2026-08-29** — PR 2b work unit staged in the dedicated worktree
  `taxa-worktrees/migrate-nextjs-tailwind4-2b`. Files added:
  `.eslintrc.cjs` (66 LoC, CommonJS legacy form; `no-restricted-imports`
  patterns derived from a `CAPABILITIES × LAYERS` matrix and emit
  BOTH path spellings — literal `src/modules/<cap>/<layer>/*` AND
  alias `@taxa/<cap>/<layer>/*` — per the maintainer's explicit
  decision to prevent alias-form bypass);
  `scripts/eslint-fixtures/{barrel_import,deep_import,deep_import_research}.js`
  (3 fixtures, 13 LoC total);
  `tests/test_no_restricted_imports.py` (309 LoC, 32 focused
  assertions including 2 alias-form triangulation tests using
  pytest's `tmp_path` so no extra fixture files are committed).
  Focused test passes 32 / 32 against `.eslintrc.cjs` (RED → GREEN
  → TRIANGULATE → REFACTOR captured). Runtime ESLint invocation
  was used to verify all 40 `(capability × layer × form)`
  combinations are rejected and all 10 barrel paths (5 caps × 2
  spellings) are allowed. Measured size **388** code+test lines
  against the **400**-line per-PR review budget — under budget by
  **-12 lines (-3.0 %)** after the trim pass. The expanded surface
  vs. the original 227-line forecast is the maintainer's explicit
      alias-form enforcement expansion; no `size:exception` is required.
      This record changes no code or tests and performs no commit or
      push. Spanish mirror updated in lockstep.
    - **2026-08-29** — PR 2c work unit staged in the dedicated worktree
      `taxa-worktrees/migrate-nextjs-tailwind4-2c`. Files added:
      `scripts/eslint-fixtures/deep_import_<cap>_<layer>.js` (20
      committed literal fixtures, 5 LoC each = 100 LoC total, covering
      every `(capability × layer)` pair across the 5 capabilities
      × 4 layers matrix); the existing
      `tests/test_no_restricted_imports.py` was extended with a
      parametrized runtime-triangulation block (delta of +139 LoC
      bringing the file from 309 to 448 LoC, +70 focused assertions:
      20 fixture-existence, 20 literal-form runtime, 20 alias-form
      runtime via `tmp_path`, 10 barrel-allow covering both literal
      and alias barrel spellings). Focused test passes 102 / 102
      (32 PR 2b + 70 PR 2c) against `.eslintrc.cjs` (RED → GREEN →
      TRIANGULATE → REFACTOR captured). Runtime ESLint invocation
      proves all **40 deep-import forms** are rejected: 20 literal
      fixtures (`src/modules/<cap>/<layer>/deep`) plus 20 dynamic
      alias inputs (`@taxa/<cap>/<layer>/deep` written into
      `tmp_path` per test). Public barrels stay allowed under both
      spelling forms. Measured size **239** code+test lines
      (20 fixtures 100 + test file delta 139) against the
      **400**-line per-PR review budget — under budget by **-161
          lines (-40.25 %)** headroom. No `size:exception` is required.
          This record changes no code or tests and performs no commit or
          push. Spanish mirror updated in lockstep.
    - **2026-08-29** — Ledger reconciliation pass (this entry). Per
      the parent task, the `apply-progress.md` ledger is reconciled
      against `origin/develop` commit history. **6 / 14 sub-PRs
      marked delivered** (1a.1 → #75 / `646f00d`; 1b.1 → #76 /
      `97776de`; 2a → #78 / `3e596db`; 2b → #80 / `00560db`; 2c → #82
      / `0bd294a`; 2d → #84 / `8315c0b`). **5 / 14 sub-PRs marked
      uncertain** (1a.2, 1b.2, 1b.3a, 1b.3b, 2e) because the
      named-slice boundary within the merged test file is not
      determinable from the commit boundary (the relevant commits
      added the test file whole, not split). **PR 3, PR 4, PR 5
status preserved exactly as origin** (reconstruction pending,
          not yet authored). Totals updated; PR 2a / 2b / 2c "staged in
          worktree" framing converted to past tense because those units
          have since been delivered. PR 2e named-slice provenance
          further uncertain because delivered size (320 LoC) exceeds the
          176 LoC plan budget. PR 2a `size:exception` (409 / +9 / +2.3 %)
          and PR 2b alias-form expansion notes retained verbatim. No
          code or test changes; no commit / push performed in this pass.
          Spanish mirror updated in lockstep.
        - **2026-08-30** — G2 / G5 docs-only reconciliation pass (this
          entry). Per the parent task, the canonical planning artifacts
          (`proposal.md`, `design.md`, `apply-progress.md`) and their
          faithful Spanish mirrors (`proposal-es.md`, `design-es.md`,
          `apply-progress-es.md`) are reconciled against the current
          state. **No source, tests, scripts, tasks, product files,
          evidence files, or `tools/g2-candidate/` workspace created.**
          Authorizations from the parent task: (1) isolated non-activation
          candidate workspace at `tools/g2-candidate/` is **authorized
          but not created** in this pass — it must not wire FastAPI,
          `web/`, CI, root `package.json`, `Makefile`, or
          `extension/manifest.json`, and it does not select Approach
          A / B / C or static export; (2) legacy audit disposition is
          **unreproducible and not accepted for G5**. Concrete deltas:
          (a) `design.md::§3.3.2.1` records the G2 contract (candidate
          root `tools/g2-candidate/`, build command
          `<candidate-root>/node_modules/.bin/next build`, output root
          `<candidate-root>/out/`, asset classes, `BUILD-INVENTORY.json`
          schema/location, Node `>= 20.9.0` requirement, failure
          semantics without silent legacy fallback, and the strict-TDD
          G2 verifier preconditions); (b) `design.md::§3.3.5` records
          the G5 disposition as **unreproducible**, enumerates the
          evidence files reviewed by name only
          (`web/dist/evidence-baseline.json`,
          `tests/test_evidence_baseline.py`,
          `tools/static-export-probe/scripts/capture.mjs`,
          `tools/static-export-probe/evidence/*.json`), lists the
          missing-proof inventory (capture command, log, environment,
          iteration count, raw Playwright, raw Lighthouse, delta row,
          CLI/schema match), and pins the closure path. Status footer
updated: G2 remains `blocked — contract defined; verifier not
              implemented`; G5 remains `blocked — baseline not reproducible;
              comparison not attempted`; PR3e activation still blocked until
              G1–G6 close. Spanish mirrors updated in lockstep. No commit
              or push performed in this pass.
        - **2026-08-30** — G2 contract corrections pass (three explicit
          maintainer decisions applied to `design.md::§3.3.2.1`; this
          entry). Per the parent task, the canonical G2 contract is
          corrected to record three explicit maintainer decisions while
          **remaining `blocked — contract defined; verifier not
          implemented`** (no G2 verifier is authored in this pass, no gate
          passes, no source / tests / scripts / candidate workspace /
          package-lock / evidence files are touched).
          (1) **Size exception (generated file, conditional)** — a
          `size:exception` applies **only** to
          `tools/g2-candidate/package-lock.json`, and **only after**
          `npm ci` exits 0 against the candidate's local
          `tools/g2-candidate/package.json`. The exception is conditional
          and void if `npm ci` fails (no `package-lock.json` is
          committed). **No other generated file under `tools/g2-candidate/`
          is excepted** from the per-PR review budget — every other
          generated artifact (build output, manifests, logs, capture
          artifacts, other lockfiles) is counted under the authored-lines
          cap. Recorded in `design.md::§3.3.2.1` as a new
          `Size exception (generated file, conditional)` table row.
          (2) **Post-build manifest staging (atomic)** — the G2 verifier
          MUST atomically copy the required Next manifests from
          `<candidate-root>/.next/` into `<candidate-root>/out/.next/`
          (specifically `<candidate-root>/.next/build-manifest.json` →
          `<candidate-root>/out/.next/build-manifest.json` and
          `<candidate-root>/.next/app-build-manifest.json` →
          `<candidate-root>/out/.next/app-build-manifest.json`) before
          inventory validation. The copy is all-or-nothing: any
          individual copy failure aborts the staging step, removes any
          partial staging, leaves **no** valid `BUILD-INVENTORY.json`
          on disk, and propagates a non-zero exit. Missing source
          manifests are also a staging failure. Recorded in
          `design.md::§3.3.2.1` as a new `Post-build manifest staging
          (atomic)` table row, and the `Failure semantics` and
          `Inventory schema & location` rows are updated to enumerate
          the staging failure branch.
          (3) **HTML entry classification** — `index.html` is the **sole**
          normal application-route HTML entry. `404.html` and `500.html`
          are explicitly permitted error-page exemptions: if Next.js
          emits them, the verifier records them under the **separate**
          `error_pages` asset class — they are **not** promoted to
          application-route entries, are **not** listed under `assets[]`
          for the `application_route_html` class, and their absence is
          **never** a missing-classes failure for the application-route
          contract. Recorded in `design.md::§3.3.2.1` by splitting the
          original `Required asset classes` row into a new
          `Required asset classes (application-route)` row plus a new
          `Error-page exemptions (classified separately)` row, and
          updating the `Verification boundary` row to assert the
          classification.
        The `Verification boundary` and `Inventory schema & location`
        rows are updated so the later strict-TDD G2 verifier must assert
        the three corrections as preconditions. The status footer in
        `design.md` (and its Spanish mirror) is updated to enumerate the
        three corrections; the G2 / G5 / PR3e blocking language is
        preserved verbatim. No boundary selected, no gate passing, no
        cutover manifest, no G2 verifier authored, no source /
        tests / scripts / candidate workspace / package-lock /
        evidence files touched. Spanish mirrors updated in lockstep. No
        commit or push performed in this pass.