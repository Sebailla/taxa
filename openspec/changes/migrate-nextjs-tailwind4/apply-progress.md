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
        - **2026-08-30** — G2 output-contract correction pass (one explicit
          maintainer decision applied to `design.md::§3.3.2.1`; this entry).
          Per the parent task, the canonical G2 contract is corrected to
          reflect the **verified Next.js 16.3.3 / Turbopack clean build**
          output layout (CSS under `out/_next/static/chunks/**`, flat JS
          chunks under `out/_next/static/chunks/**` with no
          `chunks/app/` subdirectory, and `build-manifest.json` staged /
          required while `app-build-manifest.json` is optional and never a
          missing-class failure). G2 **remains `blocked — contract defined;
          verifier not implemented`**, not `passed` (no G2 verifier is
          authored in this pass, no gate passes, no source / tests /
          scripts / candidate workspace / package-lock / evidence files /
          Next 16 candidate build artifact is touched; the build-output
          realities are implementation findings, not assumptions).
          (4) **Next.js 16 / Turbopack output-contract correction** —
          recorded in `design.md::§3.3.2.1` against the verified clean
          `next build` output layout:
          - (4.a) **CSS class** — the required CSS application-route class
            is **one-or-more non-empty `*.css` files anywhere under
            `<candidate-root>/out/_next/static/chunks/**`** (CSS bundles
            are co-located with JS chunks), **not** `out/_next/static/css/`
            (no separate CSS directory is required or asserted).
          - (4.b) **JS class** — the required JS application-route class
            is **one-or-more non-empty `*.js` files anywhere under
            `<candidate-root>/out/_next/static/chunks/**`**; the contract
            carries **no `chunks/app/` subdirectory requirement** (Next.js
            16 / Turbopack emits flat JS chunks).
          - (4.c) **Manifest staging semantics** — only
            `<candidate-root>/.next/build-manifest.json` →
            `<candidate-root>/out/.next/build-manifest.json` is
            **required** (its absence from the build output is a
            missing-class failure);
            `<candidate-root>/.next/app-build-manifest.json` →
            `<candidate-root>/out/.next/app-build-manifest.json` is
            **optional and never a missing-class failure** — the verifier
            attempts the copy only when the source manifest exists,
            records `staged` / `not_emitted` in `assets[]`, and never fails
            on its absence (the verified clean Next 16.3.3 / Turbopack
            build emits only `build-manifest.json`).
          Recorded in `design.md::§3.3.2.1` by updating the `Required asset
          classes (application-route)`, `Post-build manifest staging
          (atomic)`, `Inventory schema & location`, `Failure semantics`,
          and `Verification boundary (strict-TDD G2 verifier preconditions)`
          rows; the `Verification boundary` row additionally asserts that
          the strict-TDD G2 verifier MUST NOT require a
          `_next/static/css/` directory or a `_next/static/chunks/app/`
          subdirectory. The `Failure semantics` row adds branch (b′) for
          optional `app-build-manifest.json` absence (`not_emitted` is
          **never** a failure) and tightens branch (b) to required
          `build-manifest.json` only. The status footer in `design.md`
          (and its Spanish mirror) is updated to enumerate the **four**
          corrections; the G2 / G5 / PR3e blocking language is preserved
          verbatim. Spanish mirrors updated in lockstep. No boundary
          selected, no gate passing, no cutover manifest, no G2 verifier
              authored, no source / tests / scripts / candidate workspace /
              package-lock / evidence files / Next 16 candidate build artifact
              touched. No commit or push performed in this pass.
        - **2026-08-30** — G2 PASS record pass (this entry). Per the parent
          task, the independently verified clean-run G2 evidence captured in
          the dedicated worktree
          `taxa-worktrees/migrate-nextjs-g2-evidence-capture` (off
          `develop` at `a74289b`; PR106 learning entry already merged on
          this base with **no contract change**) is recorded here and in
          the `design.md` status footer; **no source, tests, scripts,
          tasks, product files, evidence files, candidate workspace, or
          `package-lock.json` are touched, committed, or pushed in this
          pass.** G2 **passes** against the canonical contract defined in
          `design.md::§3.3.2.1` (all **four** explicit maintainer
          corrections honoured). Evidence summary:
          - **Run timestamp** — build started
            `2026-08-30T18:10:59.430633+00:00`, build finished
            `2026-08-30T18:11:02.803400+00:00` (clean, ~3.4 s).
          - **Node version** — `v26.8.1` (≥ `20.9.0` hard requirement).
          - **Artifact location** —
            `taxa-worktrees/migrate-nextjs-g2-evidence-capture/tools/g2-candidate/out/BUILD-INVENTORY.json`
            (and `out/.next/build-manifest.json` for the staged manifest).
            The captured workspace is **not** committed; only the path
            and the inventory contents are referenced here.
          - **Build command** (as recorded in the inventory
            `build_command` field) —
            `<candidate-root>/node_modules/.bin/next build` with
            `cwd = <candidate-root>`; exit `0`.
          - **Inventory classes present** (no `missing_classes`):
            `application_route_html` ×1 (`out/index.html`),
            `js_class` ×1 (one non-empty `*.js` under
            `out/_next/static/chunks/**`), `css_class` ×1 (one non-empty
            `*.css` under `out/_next/static/chunks/**`), `staged_manifest`
            ×2 (required `build-manifest.json` `staged`, optional
            `app-build-manifest.json` `not_emitted` — absence is **never**
            a failure per the **four-correction** contract),
            `error_pages` ×1 (`out/404.html` classified separately,
            **not** promoted to `application_route_html`).
          - **Staged build-manifest** —
            `<candidate-root>/out/.next/build-manifest.json`,
            **607 bytes**, sha256
            `f52f7edd901e373a2a24a4ecf8ba61c96ad227093c6440dc4a3a6ca58a92f2a3`
            (`staged`).
          - **Optional app-build-manifest** — `not_emitted` (recorded,
            **not** a missing-class failure).
          - **Tests** — focused test `tests/test_verify_build.py` passes
            **14 / 14** (12 functions + 2 parametrized expansions over
            `(omit, label)`); focused test `tests/test_g2_candidate.py`
            passes **34 / 34** (17 functions + parametrized expansions on
            `(path)` and `(needle)`).
          - **Build log** — `<candidate-root>/build.log` captured
            (multi-lockfile warning present and **non-blocking** per the
            canonical contract — the verifier's exit propagated cleanly
            to `0`).
          - **Risk note** — the parent task brief listed the staged
            build-manifest sha256 prefix as `7ad2277db4ab4e80...`; the
            **actual** captured sha256 is
            `f52f7edd901e373a2a24a4ecf8ba61c96ad227093c6440dc4a3a6ca58a92f2a3`
            (byte count matches at 607). The brief's hash prefix appears
            to be a transcription error; the captured evidence above is
            what is on disk and is recorded verbatim. No G2 gate
            semantics depend on the hash prefix beyond
            bytes-counted + sha256-stability assertions; the canonical
            contract assertion is satisfied by the recorded sha256.
          - **Truth preserved** — G2 **passes** (clean candidate build +
            inventory reproducible, contract assertions all satisfied);
            **G3, G4, G5, G6 remain blocked** (G5 unreproducible per the
            §3.3.5 audit; G3 / G4 / G6 verifiers not authored yet);
            **static export remains unselected** (no Approach A / B / C
            chosen); **no FastAPI activation** (the candidate workspace
            remains a self-contained, non-activation build root per the
            canonical authorization in `design.md::§3.3.2.1` row 1).
            The `status:` footer in `design.md` (and its Spanish mirror)
            is updated to enumerate this G2 PASS record while preserving
            verbatim the G3 / G4 / G5 / G6 / static-export / FastAPI
            blocking language and the **four**-correction G2 contract.
            The `design.md::§3.3.2.1` G2 contract body is **not**
            changed in this pass. Spanish mirrors updated in lockstep.
            No commit, push, or PR opened in this pass.
            - **2026-08-30** — G3 cutover-manifest authoring pass (this entry).
              Per the parent task, the canonical machine-readable consumer
              manifest is added at
              `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
              and the canonical G3 contract is defined in
              `design.md::§3.3.3.1` (with faithful Spanish mirror in
              `design-es.md::§3.3.3.1`). **No source, tests, scripts, tasks,
              product files, evidence files, candidate workspace, or
              `package-lock.json` are touched, committed, or pushed in this
              pass.** G3 **contract defined; manifest authored with every
              §3.1 consumer unselected; verifier not implemented** (no G3
              verifier is authored in this pass, no gate passes, no consumer
              is flipped to `selected`).
              (1) **Canonical manifest path** —
                `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`.
                Single source of truth for every active consumer in
                `design.md::§3.1`.
              (2) **Coverage** — all **26** active consumers from §3.1 are
                enumerated verbatim: **21** consumers in §3.1.1 (FastAPI web
                mount: 2 HTML reads + 1 CSS link + 1 JS module-entry + 4 ES
                import + 3 dynamic import + 1 CDN pin + 3 smoke/evidence
                baseline tests + 2 build-profile/hydration tests + 1
                extension-manifest pin + 3 evidence-baseline tests) + **5**
                consumers in §3.1.2 (`web/search_urls.js`: 3 detail.js
                runtime uses + 2 contract tests). No consumer was collapsed
                or merged; IDs were issued from fresh `mount-` (21) and
                `search-urls-` (5) namespaces following the
                `<edge-prefix>-<kind>-NNN` convention.
              (3) **Per-consumer fields** — every consumer record carries
                the seven fields required by the task brief:
                `id`, `ownership_edge` (one of `fastapi_web_mount`,
                `web_search_urls_js`), `current_path`, `replacement`
                (`{status: "unselected"}` for every consumer in this pass),
                `verification` (`{command, expect}`), `activation_status`
                (`"unselected"` for every consumer), `rollback` (the
                exact `git revert` statement that restores `current_path`).
              (4) **Top-level shape** — the manifest also carries
                `$schema_version`, `change`, `planning_artifact`,
                `generated_by`, `scope_intent`, `anchor`, `fail_closed_summary`,
                `edges[]` (the two ownership edges with `id`, `label`,
                `anchor`, `single_origin_contract`), `consumers[]`,
                `selection_invariants` (approach_status,
                all_replacements_unselected, fail_closed_semantics,
                atomic_cutover_invariant, rollback_invariant,
                selection_rule), and `verifier_contract_summary` (producer,
                command, artifact, threshold, fail_closed_invariant).
              (5) **Fail-closed invariant** — every consumer in this pass
                has `activation_status: unselected` and
                `replacement.status: unselected`. The G3 verifier
                (`scripts/verify_consumers.py`, AÚN NO AUTORIADO —
                to land in PR3d) MUST exit non-zero AND emit no valid
                `CONSUMER-READINESS.json` while ANY consumer is unselected.
                The manifest's `fail_closed_summary` and the §3.3.3.1
                `Failure semantics (fail-closed)` row enumerate this
                invariant.
              (6) **G3 contract body** — `design.md::§3.3.3.1` (and the
                faithful Spanish mirror `design-es.md::§3.3.3.1`) define
                the canonical input for the strict-TDD G3 verifier across
                the rows: Canonical manifest path; Manifest top-level
                shape; Consumer record schema; Stable-ID convention;
                Atomic cutover unit; Rollback unit; Failure semantics
                (fail-closed); `CONSUMER-READINESS.json` schema
                (`manifest_path`, `manifest_sha256`, `node_version`,
                `verified_at`, `exit_code`, `consumers[]`,
                `unselected_count`, `failed_verifications[]`,
                `activation_complete` — invalid when `activation_complete`
                is `false` OR `exit_code != 0` OR `unselected_count > 0`
                OR any `failed_verifications[]` entry exists; verifier
                writes via temp-file + rename); Test fixture requirements
                (canonical manifest as red/green fixture + parametrized
                `tmp_path` fixtures over the four failure modes + a
                SHA256-stability fixture + a fail-closed invariant
                fixture); Selection rule (gating — requires G2/G4/G5/G6
                all `passed`); Provenance.
              (7) **§3.3.3 G3 row update** — the producer / command /
                artifact / threshold cells in `design.md::§3.3.3` (and
                `design-es.md::§3.3.3`) now reference the canonical
                `cutover-manifest.json` path instead of the prior
                `design.md::§3.4` placeholder.
              (8) **Status footer** — the `status:` footer in `design.md`
                (and the Spanish mirror) is updated to enumerate this
                G3 contract / manifest authoring record while preserving
                verbatim the G2 PASS record, the G5 unreproducible
                disposition, the G4 / G6 blocked language, the
                static-export-unselected language, and the
                no-FastAPI-activation language.
              **Truth preserved** — G3 **contract defined; manifest
              authored with every §3.1 consumer unselected; verifier
              not implemented** (no consumer is flipped to `selected`,
              no G3 verifier is authored, no gate passes); **static
              export remains unselected** (no Approach A / B / C chosen);
              **no FastAPI activation** (the cutover-manifest.json is a
              pure planning artifact — no `WEB_DIR` repoint, no
              consumer-update, no Makefile / extension / API /
              product-source change); **G4, G5, G6 remain blocked**
              (G5 unreproducible per the §3.3.5 audit; G4 / G6
              verifiers not authored yet). Spanish mirrors updated in
              lockstep. No commit, push, or PR opened in this pass.
                  **Size note (planning-only)** — this pass adds
                  `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
                  (273 lines, planning artifact analogous to the generated
                  `BUILD-INVENTORY.json` at G2 — the manifest is a data
                  file, not a code/test addition, and is bounded by the
                  number of §3.1 consumers) plus the §3.3.3 row update +
                  new §3.3.3.1 contract definition + status-footer record
                  in `design.md` and `design-es.md` (≈ 36 net lines across
                  the two files). Total authored planning-doc additions in
                  this pass stay well under the 400-line per-PR review
                  budget.
                - **2026-08-30** — G3 canonical PASS record pass (this entry).
                  Per the parent task, the independently verified clean-merge
                  G3 Tier-1 (legacy pre-cut) readiness evidence captured
                  after PR #109 + PR #111 + PR #115 + PR #116 landed on
                  `origin/develop` is recorded here and in
                  `design.md::§3.3.3` (plus the faithful Spanish mirror in
                  `design-es.md::§3.3.3`). **No source, tests, scripts,
                  tasks, product files, evidence files, candidate workspace,
                  `cutover-manifest.json`, or `package-lock.json` are
                  touched, committed, or pushed in this pass.** The
                  canonical `cutover-manifest.json` (the Tier-1 manifest
                  authored 2026-08-30) and the previously emitted
                  `<build-root>/CONSUMER-READINESS.json` (if any) are
                  **unchanged**; this pass records the Tier-1 PASS evidence
                  against the existing manifest. **G3 PASSES for Tier-1;
                  G3 is NOT PASSED for Tier-2** (atomic-cut selection
                  remains evidence-gated by G4 + G5 + G6 PASS).
                  Evidence summary:
                  - **Merged PRs on `origin/develop` at evidence capture
                    time** — PR #109 `test(g3): verify consumer readiness`
                    (verifier authored) + PR #111 `fix(g3): control
                    readiness verification runtime` (controlled runtime
                    `--serve` / `--venv` / `--repo-root` /
                    `--fixture-web-root`) + PR #115 `fix(g3): enforce HTTP
                    consumer expectations` (HTTP-shape fail-closed
                    enforcement via
                    `tools/g3-legacy-fixture/scripts/check_http_status.py`)
                    + PR #116 `fix(g3): preserve virtualenv Python paths`
                    (virtualenv-symlink preservation). All four PRs are
                    merged into `origin/develop` (current HEAD
                    `39d29ee`) — the verifier, the controlled runtime,
                    the HTTP-shape fail-closed gate, and the venv
                    symlink preservation are all on disk at evidence
                    capture time.
                  - **Canonical command line** —
                    `python scripts/verify_consumers.py --manifest openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json --out <build-root> --serve --venv <repo-root>/.venv/bin/python --fixture-web-root <repo-root>/tools/g3-legacy-fixture/web --repo-root <repo-root>`
                    — exit `0` (verifier exits `EXIT_OK`).
                  - **Artifact emitted** —
                    `<build-root>/CONSUMER-READINESS.json`, written
                    atomically via temp-file + rename by the verifier;
                    the canonical schema validates every required key.
                  - **Artifact contents (canonical)** — `manifest_path`
                    =
                    `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`,
                    `manifest_sha256` matches the on-disk canonical
                    manifest hash (stable across consecutive verifier
                    runs), `node_version ≥ 20.9.0`, `verified_at`
                    (ISO-8601 timestamp of evidence capture), `exit_code
                    = 0`, every `consumers[].status = "ready"` with the
                    corresponding `verification_exit_code = 0`,
                    `unselected_count = 0`, `failed_verifications[]`
                    empty, `activation_complete = true`. The artifact is
                    **valid** by the §3.3.3.1 schema (`activation_complete
                    = true` AND `exit_code = 0` AND `unselected_count = 0`
                    AND `failed_verifications[]` empty).
                  - **Coverage (canonical)** — all **26 / 26** §3.1
                    consumers PASS — **21** in §3.1.1 (FastAPI web mount:
                    2 HTML reads + 1 CSS link + 1 JS module-entry + 4
                    ES-import + 3 dynamic-import + 1 CDN pin + 3
                    smoke/evidence-baseline tests + 2 build-profile /
                    hydration tests + 1 extension-manifest pin, with the
                    evidence-baseline block folded by coverage summary)
                    + **5** in §3.1.2 (`web/search_urls.js`: 3 detail.js
                    runtime uses + 2 contract tests). Every consumer's
                    `verification.command` exits `0` against the
                    controlled fixture served by `python -m http.server`
                    on an isolated free TCP port picked by the OS (never
                    the legacy `8765`); HTTP-shape expectations
                    (`"200"`, `"200 for each"`) are routed through the
                    controlled `tools/g3-legacy-fixture/scripts/check_http_status.py`
                    fail-closed helper (PR #115); non-HTTP expectations
                    (`"ok"`, `"1 passed"`, `"all passed"`, arbitrary
                    text) keep shell-exit-only semantics.
                  - **Tests supporting the PASS** — `tests/test_verify_consumers.py`
                    (controlled runtime / fixture-serve / HTTP-shape /
                    symlink-preservation triangulation tests, all green
                    on `origin/develop` post-merge of PR #109 + PR #111 +
                    PR #115 + PR #116) + `tests/test_g3_legacy_fixture.py`
                    (fixture DB + served fixture asset coverage tests,
                    all green on `origin/develop` post-merge of PR #113 +
                    PR #114 + PR #115 + PR #116).
                  - **Risk note** — the Tier-1 PASS evidence is
                    **independent** of any G2 / G4 / G5 / G6 evidence;
                    Tier-1 (`legacy pre-cut`) does not require G2/G4/G5/G6
                    PASS by contract, and the canonical command exercises
                    the legacy pre-cut runtime against the controlled
                    fixture rather than any G2 candidate build root.
                    The PASS artifact does **not** exercise `<build-root>`
                    from a G2 candidate; that path is Tier-2 and remains
                    evidence-gated by G2 + G4 + G5 + G6 PASS.
                  - **Truth preserved** — G3 **Tier-1 (legacy pre-cut)
                    readiness PASSED** (clean evidence capture, all
                    consumers green, valid `CONSUMER-READINESS.json`
                    emitted); **G3 Tier-2 (atomic-cut selection against
                    the chosen Approach A / B / C build artifact) NOT
                    PASSED** — Tier-2 requires G4 (Playwright + Lighthouse
                    parity) + G5 (reproducible hydration baseline — G5
                    currently `unreproducible` per §3.3.5 audit) + G6
                    (`cutover-rehearsal.json` dry-run success); G2 PASS is
                    recorded but Tier-2 evaluation needs G4 / G5 / G6 on
                    top; **Approach A / B / C remain unselected**; **no
                    FastAPI activation** (no `WEB_DIR` repoint, no atomic
                    cutover, no `api/server.py` / Makefile / extension /
                    API / product-source change); **G4 / G6 remain
                    blocked** (verifiers not authored yet); **G5 remains
                    `unreproducible`** per the §3.3.5 audit. The Tier-1
                    PASS is a **canonical evidence record**, not a
                    cutover activation. PR3e is still blocked until
                    Tier-2 evidence closes via PR3d/PR3e.
                  - **`design.md` / `design-es.md` deltas** — §3.3.3 G3
                    row's Producer cell now references all four PRs
                    (#109, #111, #115, #116); the Command cell now
                    carries the canonical `--serve --venv
                    --fixture-web-root --repo-root` invocation; the
                    Threshold cell carries the Tier-1 PASS reference;
                    **four new rows** are added to §3.3.3 (after the
                    Threshold cell): **Disposition (2026-08-30 canonical
                    evidence — PR #116 merge)**, **Canonical command
                    line (PR #116 evidence capture)**, **Coverage
                    (2026-08-30 evidence)**, **What this PASS does NOT
                    claim**, **Closure path forward**. §3.3.3.1 opening
                    paragraph now declares **G3 PASSES for Tier-1**
                    verbatim (with `CONSUMER-READINESS.json` artifact
                    emission, all 26 / 26 consumers, fail-closed
                    invariants preserved); the Provenance row gains a
                    third-update note documenting the PR #116 evidence
                    capture. The status `status:` footer at the bottom
                    of both `design.md` and `design-es.md` flips the
                    Tier-1 language from "G3 stays `blocked — verifier
                    authored but G3 still gated by G2/G4/G5/G6 PASS for
                    Tier-2`, not `passed`" to "G3 disposition: `PASSED
                    for Tier-1; NOT PASSED for Tier-2`"; all G4 / G5 /
                    G6 / G2-Tier-2 / Approach-A-B-C-unselected /
                    no-FastAPI-activation / no-touch / no-commit / no-push
                    language is preserved verbatim. The Spanish mirror
                    carries the faithful Spanish translation of every
                    row, paragraph, and footer flip.

                  **Truth preserved** — G3 **Tier-1 PASSED** (canonical
                  evidence captured 2026-08-30 via PR #109 + PR #111 +
                  PR #115 + PR #116 merge on `origin/develop`); G3
                  Tier-2 NOT PASSED (G4 + G5 + G6 still blocked);
                  Approach A / B / C remain unselected; no FastAPI
                  activation (no `WEB_DIR` repoint, no atomic cutover,
                  no consumer update, no Makefile / extension / API /
                  product-source change); G4 / G6 remain `blocked`
                  (verifiers not authored yet); G5 remains
                  `unreproducible` per the §3.3.5 audit; the canonical
                  `cutover-manifest.json` is unchanged (26 §3.1
                  consumers, Tier-1 `selected`, Tier-2 unselected); the
                  previously emitted `CONSUMER-READINESS.json` (if any)
                  is unchanged; this pass records the Tier-1 PASS
                  evidence without mutating any prior artifact. Spanish
                  mirrors updated in lockstep. No commit, push, or PR
                  opened in this pass.

                  **Size note (planning-only)** — this pass adds the
                  `Disposition / Canonical command line / Coverage /
                  What this PASS does NOT claim / Closure path forward`
                  rows to `design.md::§3.3.3` (and the faithful Spanish
                  translation to `design-es.md::§3.3.3`) plus the
                  §3.3.3 opening paragraph G3-PASS flip + Provenance
                  row third-update note + status `status:` footer flip
                  (≈ 65 net lines across the two files), plus this
                  new change-log entry + the Spanish mirror entry (≈
                  100 net lines across the two apply-progress files).
                  Total authored planning-doc additions in this pass
                  stay well under the 400-line per-PR review budget.
                - **2026-08-30** — G3 legacy pre-cut selection authoring
                  pass (this entry). Per the parent task, every §3.1
                  consumer in the canonical cutover manifest is flipped to
                  **Tier-1 (legacy pre-cut) selection** against its on-disk
                  legacy `current_path`, the `design.md` / `design-es.md`
                  G3 contract is extended with a **two-tier selection
                  model** (Tier-1 legacy pre-cut + Tier-2 atomic-cut
                  gated by G2/G4/G5/G6 PASS), and the apply-progress
                  mirrors are updated in lockstep. **No source, tests,
                  scripts, tasks, product files, evidence files,
                  candidate workspace, or `package-lock.json` are touched,
                  committed, or pushed in this pass. No G3 verifier is
                  authored; no G3 PASS is claimed; no FastAPI activation
                  is implied.**

                  (1) **What "legacy pre-cut selection" means** — for
                  every consumer enumerated in
                  `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`,
                    `replacement.path` is set to the on-disk legacy file
                    (or set of legacy files) the consumer currently reads,
                    `replacement.status` is set to `"selected"`, and
                    `activation_status` is set to `"selected"`. The
                    consumer's `replacement.note` documents the Tier-1
                    semantics: the on-disk legacy runtime on FastAPI's
                    `127.0.0.1:8765` mount (or the equivalent test-reader
                    path) remains the active serving origin; no `WEB_DIR`
                    repoint, no atomic cutover, no FastAPI activation is
                    implied. The legacy vanilla frontend continues to be
                    served exactly as on `develop`.

                  (2) **Coverage** — all **26** active consumers in
                    `design.md::§3.1` are flipped: 21 §3.1.1 (FastAPI web
                    mount) + 5 §3.1.2 (`web/search_urls.js`). No consumer
                    is left unselected against the Tier-1 legacy pre-cut
                    baseline.

                  (3) **Per-consumer fields** — every consumer record now
                    carries a populated `replacement` block (`status`,
                    `path`, `note`) alongside the seven required fields
                    (`id`, `ownership_edge`, `current_path`,
                    `verification`, `activation_status`, `rollback`).
                    `replacement.path` is a clean file path (or
                    comma-separated set of file paths for multi-file
                    imports — e.g.
                    `web/state.js, web/api.js, web/tree.js, web/breadcrumb.js, web/detail.js, web/nav.js, web/dom.js, web/banner.js, web/help.js, web/keymap.js`
                    for
                    `mount-runtime-import-app-js-modules-005`). `replacement.note`
                    is consistently shaped: prefix
                    "Legacy pre-cut selection (planning artifact,
                    2026-08-30):" + the on-disk legacy path identifier +
                    the Tier-1 semantics + the language "Approach A / B /
                    C atomic-cut selection remains evidence-gated by
                    G2/G4/G5/G6. NOT a G3 PASS."

                  (4) **Top-level invariants flipped** —
                    `selection_invariants.all_replacements_unselected`
                    flips from `true` to `false`. A sibling invariant
                    `all_replacements_unselected_note` documents why.
                    A new invariant `legacy_pre_cut_selection_status` is
                    added: `{active: true, scope: "every §3.1 consumer …",
                    what_it_means: <doc>, what_it_does_not_claim: <doc>,
                    two_tier_model: <doc>, truth_preservation: <doc>}`.
                    A new invariant `combined_selection_rule` records the
                    two-tier contract.

                  (5) **Two-tier selection rules recorded** —
                    `selection_invariants.selection_rule_tier1_legacy_pre_cut`
                    documents the Tier-1 contract (legacy pre-cut, no
                    G2/G4/G5/G6 PASS required, every consumer satisfies
                    Tier-1 in this pass). The previous
                    `selection_invariants.selection_rule` is renamed to
                    `selection_rule_tier2_atomic_cut` and now exclusively
                    documents the Tier-2 contract (atomic-cut selection,
                    G2 PASS + G4 + G5 + G6 required, Approach A / B / C
                    remains unselected, lands in PR3d/PR3e). The G2 PASS
                    record (2026-08-30, from
                    `taxa-worktrees/migrate-nextjs-g2-evidence-capture`)
                    is cited in the Tier-2 rule.

                  (6) **`fail_closed_summary` updated** — the summary
                    now describes the two-tier state: every consumer
                    carries `selected` under Tier-1, so the
                    "any-unselected-exits-non-zero" branch does not
                    currently fire; but the verifier (when authored) must
                    still validate each `verification.command` against
                    the legacy pre-cut runtime, and a non-zero exit on
                    any `verification.command` re-triggers the
                    fail-closed branch and blocks the
                    `CONSUMER-READINESS.json`. Tier-2 atomic-cut
                    selection remains evidence-gated and is NOT in play.

                  (7) **`verifier_contract_summary` updated** — the
                    summary now carries `threshold_tier1_legacy_pre_cut`
                    (legacy runtime on `127.0.0.1:8765` reachable, every
                    `verification.command` exits `0`) +
                    `threshold_tier2_atomic_cut` (atomic-cut against
                    `<build-root>` + G2/G4/G5/G6 PASS) +
                    `evaluation_state` (Tier-1 evaluation runs first;
                    Tier-2 fires after Tier-1 passes; Tier-2 fails
                    block the artifact). The
                    `fail_closed_invariant` now describes both Tier-1
                    and Tier-2 fail-closed triggers.

                  (8) **`generated_by` flipped** — the manifest's
                    `generated_by` field now reads: "G3 planning contract
                    (planning-only; legacy pre-cut selection authored
                    for every §3.1 consumer against the on-disk legacy
                    `current_path`; Approach A / B / C atomic-cut
                    selection remains evidence-gated by G2/G4/G5/G6 and
                    is NOT made in this pass; verifier NOT YET
                    AUTHORED)".

                  (9) **`design.md::§3.3.3` and `design.md::§3.3.3.1`
                    updated** — §3.3.3 row's threshold cell now
                    documents the two-tier model. §3.3.3.1 introduces a
                    `Selection rule — Tier-1 (legacy pre-cut)` row, a
                    `Selection rule — Tier-2 (atomic-cut, gated)` row,
                    and a `Combined selection state` row (replacing the
                    former single `Selection rule (gating)` row). The
                    `Canonical manifest path` row is updated to record
                    the Tier-1 authoring state. The `Failure semantics`
                    row is renamed `Failure semantics (fail-closed,
                    two-tier)` and includes Tier-1 + Tier-2 evaluation
                    branches. The `Provenance` row records the
2026-08-30 second-pass authoring. The status footer
                    (`status:` line) enumerates the Tier-1 + Tier-2
                    contract and preservation language; **G3 stays
                    `blocked — contract defined; legacy pre-cut
                    selection authored for every §3.1 consumer;
                    verifier authored on disk (PR #109 + PR #111) but
                    G3 still gated by G2/G4/G5/G6 PASS for Tier-2`,
                    not `passed`.

                  (10) **Spanish mirrors updated in lockstep** — the
                    same edits apply to
                    `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md`
                    (Spanish: Nivel-1 legacy pre-cut + Nivel-2
                    atomic-cut acoado por PASS de G2/G4/G5/G6). The
                    changes correspond row-for-row to the English edit;
                    the Spanish status footer enumerates the same
                    Tier-1 / Tier-2 contract and preservation language.

**Truth preserved** — G3 **legacy pre-cut selection
                  authored for every §3.1 consumer; verifier AUTHORED
                  on disk (PR #109 + PR #111) but G3 still gated by
                  G2/G4/G5/G6 PASS for Tier-2**; no consumer is
                  flipped to Tier-2
                  (atomic-cut); no G3 PASS is claimed; static export
                  (Approach A) and B / C remain **unselected**; no
                  FastAPI activation (no `WEB_DIR` repoint, no
                  consumer-update, no Makefile / extension / API /
                  product-source change); G4 / G6 remain `blocked`
                  (verifiers not authored yet); G5 remains
                  `unreproducible` per the §3.3.5 audit; the Tier-1
                  legacy pre-cut pass is a **planning artifact**, not a
                  G3 gate, and does NOT claim or imply G3 PASS. No
                  commit, push, or PR opened in this pass.

                  **Size note (planning-only)** — this pass flips the
                  26-consumer `cutover-manifest.json` from
                  `replacement.status: "unselected"` to
                  `replacement.status: "selected"` with a populated
                  `replacement.path` + `replacement.note` block (manifest
                  grew from 273 lines to 391 lines, +118 lines, all in
                  the populated `replacement` block of each consumer +
                  the new `selection_invariants.legacy_pre_cut_selection_status`
                  + `all_replacements_unselected_note` + `selection_rule_tier1_*`
                  + `selection_rule_tier2_*` + `combined_selection_rule`
                  + `verifier_contract_summary.threshold_tier1_*` +
                  `threshold_tier2_*` + `evaluation_state`) plus the
                  `design.md` / `design-es.md` §3.3.3 row update +
                  `design.md::§3.3.3.1` four new rows
                  (Tier-1 selection rule + Tier-2 selection rule +
                  Combined selection state + Provenance second-pass
                  note) + `design.md` Threshold cell `Nivel-1 / Nivel-2`
                  language + `design.md::§3.3.3.1` `Ruta del manifiesto
                  canónico` flip + `Semántica de fallo` Tier-1/2
                  extension + `Procedencia` second-pass note + status
                  footer update (≈ 28 net lines across the two files).
                  Total authored planning-doc additions in this pass
                  stay well under the 400-line per-PR review budget.
- **2026-08-30** — G5 provisional reconciliation pass (this entry).
  Per the parent task, the canonical G5 contract is extended with a
  **provisional / planning-only scope** that records the existing
  G2 / G4 / G5 capture infrastructure availability and defines the
  **bundle gate** (candidate total uncompressed emitted JS + CSS ≤
  legacy baseline × 1.10), without promoting any gate to PASS.
  **No source, tests, scripts, tasks, product files, evidence files,
  candidate workspace, or `package-lock.json` are touched, committed,
  or pushed in this pass.** This pass is **provisional infrastructure
  evidence only**: it does **NOT** accept the final migrated product,
  does **NOT** select Approach A / B / C, does **NOT** transfer
  FastAPI ownership or perform a cutover, does **NOT** promote G4 to
  PASS, and does **NOT** promote G6 to PASS.
  (1) **Provisional G2 candidate** — `tools/g2-candidate/` is the
    existing G2 diagnostic shell (authorized non-activation build root
    per `design.md::§3.3.2.1` row 1) and is the candidate for the
    bundle gate. It is **provisional, diagnostic only** — no Approach
    A / B / C is selected, no FastAPI activation, no `WEB_DIR` repoint.
  (2) **Bundle gate (provisional, planning-only)** — the
    previously-TBD bundle-size line of the G5 Threshold row is now
    defined as **candidate total uncompressed emitted JS + CSS ≤
    legacy baseline total uncompressed JS + CSS × 1.10** (≤ 10 %
    delta on the combined uncompressed bundle weight). The 10 % delta
    is a **provisional planning gate**; it does **NOT** constitute
    Approach selection, FastAPI activation, or migrated-product
    acceptance.
  (3) **Capture infrastructure availability** — existing on disk for
    diagnostic / capture-only use (provisional): `tools/g4-capture/`
    (G4 / G5 capture tree landed via PRs #131–#140 on
    `docs/g5-provisional-candidate` at `3cee69b`: controlled hydration
    fixture, capture preconditions, raw Playwright samples, raw
    Lighthouse payloads, atomic publication, readiness latency,
    raw→published bridge, controlled legacy lifecycle, capture
    orchestration) + `tools/g3-legacy-fixture/web/` +
    `tools/g3-legacy-fixture/scripts/check_http_status.py` (G3
    controlled fixture + HTTP-shape fail-closed helper, PRs
    #113–#116) + `tools/g2-candidate/` (G2 diagnostic shell). These
    tools are available for diagnostic capture but **none of G2
    Tier-2, G3 Tier-2, G4, G5, or G6 is promoted to PASS**.
  (4) **Non-goals (provisional scope)** — this pass does NOT: (i)
    accept the final migrated product; (ii) select Approach A / B /
    C; (iii) transfer FastAPI ownership or perform a cutover; (iv)
    promote G4 behavior parity to PASS; (v) promote G6 cutover
    rehearsal to PASS.
  (5) **`design.md` / `design-es.md` deltas** — four new rows
    appended to `§3.3.5` after the existing `Closure path` row:
    **Provisional G2 candidate (existing, diagnostic only)**,
    **Bundle gate (provisional, planning-only)**, **Capture
    infrastructure availability (existing, provisional)**,
    **Non-goals (provisional scope)**. The existing
    `Disposition (unreproducible)`, `Threshold`, and `Closure path`
    rows are preserved verbatim. The `status:` footer gains a final
    clause recording this provisional scope while preserving
    verbatim the G2 PASS record, G3 Tier-1 PASS, G5 unreproducible
    disposition, G4 / G6 blocked language, Approach-A-B-C-unselected
    language, and no-FastAPI-activation / no-touch / no-commit /
    no-push language. The Spanish mirror carries the faithful
    translation of every new row + footer clause.
  **Truth preserved** — G5 **provisional scope recorded**; bundle
  gate defined as ≤ 10 % delta on uncompressed JS / CSS; G2 / G4 /
  G5 capture infrastructure **available for diagnostic use** without
  promoting any gate to PASS; G2 Tier-2 + G3 Tier-2 + G4 + G5 + G6
  remain blocked / unreproducible per prior audits; Approach A / B
  / C remain unselected; no FastAPI activation; no source / tests /
  scripts / config / Makefile / extension / API / product-source
  touched, committed, or pushed. Spanish mirrors updated in
  lockstep. No commit, push, or PR opened in this pass.

  **Size note (planning-only)** — this pass adds 4 new rows to
  `design.md::§3.3.5` (Spanish mirror mirrors each row) + a final
  clause to the `status:` footer in both files + this new
  change-log entry + the Spanish mirror entry. Total authored
  planning-doc additions in this pass stay well under the 400-line
  per-PR review budget.