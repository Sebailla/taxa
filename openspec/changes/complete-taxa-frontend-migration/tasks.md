# Tasks: complete-taxa-frontend-migration

> Strict TDD: RED → GREEN → TRIANGULATE → REFACTOR. Modular-monolith
> rules from
> `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
> apply to every UI/file unit. **Approach A is FINAL** (locked
> 2026-09-02; recorded in `design.md::§1`); no override path is open.
> **Predecessor `migrate-nextjs-tailwind4/` is frozen** — its files
> MUST stay byte-identical through this change's apply phase.

> **2026-09-02 — corrective plan revision**. The 13-child Feature
> Branch Chain topology was reordered and rescoped after the apply
> gate identified a dependency-order defect: original PR 3a required
> `next build`/`out/index.html` before the Next/React/Tailwind/
> TypeScript toolchain and the Node ≥ 20.9.0 runtime contract
> existed (those landed in original PR 3c, AFTER original PR 3a).
> The corrected topology introduces a **toolchain bootstrap PR at
> position 1** (which absorbs the `package.json` dep pins and
> `scripts/check-runtime.mjs` previously attributed to original
> PR 3c), demotes the **App Router static export** to position 2
> (now safe to test against `out/index.html` because the toolchain
> already exists), keeps **Tailwind/tokens** at position 3, fuses
> the **Makefile rewrite** with the `WEB_DIR` repoint + AC-21 into
> position 4, and follows with **state → ports → e2e → validation
> → atomic cutover** in dependency-correct order. The 13-child
> count is preserved; only the chain topology, per-child scope, and
> per-child test witnesses change. **Approach A, FastAPI/SQLite,
> and the frozen predecessor remain unchanged.**

## Scope boundary for this tasks file

- **In scope**: every sub-PR under Approach A listed in `design.md`
  §"Sub-PR slice under Approach A" (positions 1 / 13 through 13 / 13
  in the corrected chain: toolchain bootstrap, App Router static
  export, Tailwind/tokens, Makefile/mount, 4a, 4b, 5a, 5b, 5c, 6a,
  6b, 6c, 3e) plus the **Phase 6 validation block** (G5
  reconstruction / G6 rehearsal authoring / G4 measurement) that
  runs **after the complete candidate path is accumulated on the
  tracker branch `docs/complete-taxa-frontend-migration-plan`**
  but **before** PR 3e can land. PR 3e (atomic cutover) ships only
  when all six gates are green.
- **G4 / G5 / G6 closure is validation work**, not a standalone
  migration objective: their artifacts are recorded in
  `apply-progress.md` §Change log as gate-flips, and they MUST NOT
  generate new `web/**` source, new `api/server.py` route handlers,
  or new `extension/**` files. The closure tests/measurers run
  against the already-landed candidate build (positions 1–9) under
  the chromium fixture the predecessor captured.
- **Predecessor frozen**: `openspec/changes/migrate-nextjs-tailwind4/**`
  is read-only history. Branch-protection rejects any PR that edits
  it. Phase 6 references the predecessor's `apply-progress.md` and
  `cutover-manifest.json` only as planning inputs.
- **FastAPI backend invariants preserved**: route handlers,
  SQLite/WAL logic, materialize flow, `save-url` SSRF defence, and
  `/api/*` byte shapes stay unchanged. `api/server.py:54` (the
  `WEB_DIR` constant) is the only line that may change in `api/server.py`
  under Approach A, plus the `next/font` `<link rel="preload">` /
  `StaticFiles` SPA fallback middleware strictly required to serve
  `out/index.html` from the existing `StaticFiles(html=True)` mount.
- **Strict TDD enforced**: every implementation task writes its
  failing test FIRST. Tasks follow `R` (RED), `G` (GREEN), `T`
  (TRIANGULATE — extra scenarios beyond the minimum that fail the
  first GREEN), `Refactor` (clean-up without behaviour drift)
  markers.
- **Dependency-order contract**: no sub-PR may require a file that
  its predecessors have not yet produced. The corrected chain
  enforces `toolchain bootstrap` → `App Router static export` →
  `Tailwind/tokens` → `Makefile/mount` → `state` → `ports` →
  `e2e` → `validation` → `atomic cutover`. PR 3a (toolchain
  bootstrap) lands before any PR that calls `next build`; the App
  Router static export depends on `next`, `react`, `react-dom`,
  `typescript`, `tailwindcss` being installed and on the Node ≥
  20.9.0 check existing; Tailwind/tokens depends on `tailwindcss@^4`
  being installed; the Makefile rewrite depends on the toolchain
  + Tailwind being installed so `npm run build:web` resolves; the
  `WEB_DIR` repoint depends on `out/index.html` being produced by
  the Makefile `api` target; the typed store + hydration guard
  depend on App Router + Tailwind being live; the capability ports
  depend on the typed store being live (for `tree-source` and
  `last-taxon-id`); `e2e` updates depend on the capability ports;
  Phase 6 validation depends on the complete candidate path; PR 3e
  depends on all six gates being green.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2,245 authored across 13 sub-PRs (toolchain bootstrap + App Router static export + Tailwind/tokens + Makefile/mount + 2 browser-state + 2 capability ports + e2e/delete-legacy + 3 Phase 6 validation + 1 atomic cutover) |
| 400-line budget risk | Low for authored work (largest is 5b at ~360 lines; 3d is ~240; 11 / 13 are ≤230). PR 3a has one user-approved exception for regenerated `package-lock.json` lines only; its authored source/test/config work remains ≤400 and no unrelated lockfile churn is allowed. |
| Chained PRs recommended | **Yes** — 13 chained child PRs (~2,245 total authored lines ≫ 400, and the atomic cutover requires the feature to integrate before it reaches `develop`) |
| Suggested split | PR 3a (toolchain bootstrap) → 3b (App Router static export) → 3c (Tailwind/tokens) → 3d (Makefile/mount) → 4a → 4b → 5a → 5b → 5c → Phase 6a (G5) → Phase 6b (G6) → Phase 6c (G4 measurement) → PR 3e (atomic cutover, gated) |
| Delivery strategy | ask-on-risk (per preflight; Approach A already locked, no override open) |
| Chain strategy | **feature-branch-chain** (user-selected). Tracker `docs/complete-taxa-frontend-migration-plan` is draft/no-merge and is the **only** PR targeting `develop`; child PR 3a targets the tracker; every later child targets its immediate predecessor branch. Supersedes the `AGENTS.md` §4 direct-to-`develop` default for this change. |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Low (PR 3a generated package-lock.json exception approved)
```

### Chain topology (Feature Branch Chain)

The tracker branch already exists: **`docs/complete-taxa-frontend-migration-plan`**.
It stays **draft / no-merge** until all 13 child PRs are reviewed
and integrated. **Nothing reaches `develop` until the tracker
merges.**

> **Reordering rationale (corrective plan revision)**. Original
> `apply-progress.md` placed App Router entry at position 1 with
> a `next build` → `out/index.html` witness that required
> `next`, `react`, `tailwindcss`, `typescript` to be installed and
> the Node ≥ 20.9.0 runtime check to exist; the toolchain itself
> was scheduled for position 3, AFTER the App Router witness had
> to be green. The corrected topology moves the toolchain to
> position 1, demotes the App Router witness to position 2 (now
> satisfiable), keeps Tailwind/tokens at position 3 (depends on
> Tailwind installed), fuses the Makefile rewrite with the
> `WEB_DIR` repoint at position 4 (depends on `next build`
> producing `out/`), then follows with state, ports, e2e, Phase 6
> validation, and the atomic cutover. The 13-child count is
> preserved.

| Position | Sub-PR | Branch | Base (PR target) |
|---|---|---|---|
| Tracker | — | `docs/complete-taxa-frontend-migration-plan` | `develop` — **draft / no-merge** |
| 1 / 13 | 3a | `feat/complete-taxa-frontend-migration-01-3a` | `docs/complete-taxa-frontend-migration-plan` (tracker) |
| 2 / 13 | 3b | `feat/complete-taxa-frontend-migration-02-3b` | `feat/complete-taxa-frontend-migration-01-3a` |
| 3 / 13 | 3c | `feat/complete-taxa-frontend-migration-03-3c` | `feat/complete-taxa-frontend-migration-02-3b` |
| 4 / 13 | 3d | `feat/complete-taxa-frontend-migration-04-3d` | `feat/complete-taxa-frontend-migration-03-3c` |
| 5 / 13 | 4a | `feat/complete-taxa-frontend-migration-05-4a` | `feat/complete-taxa-frontend-migration-04-3d` |
| 6 / 13 | 4b | `feat/complete-taxa-frontend-migration-06-4b` | `feat/complete-taxa-frontend-migration-05-4a` |
| 7 / 13 | 5a | `feat/complete-taxa-frontend-migration-07-5a` | `feat/complete-taxa-frontend-migration-06-4b` |
| 8 / 13 | 5b | `feat/complete-taxa-frontend-migration-08-5b` | `feat/complete-taxa-frontend-migration-07-5a` |
| 9 / 13 | 5c | `feat/complete-taxa-frontend-migration-09-5c` | `feat/complete-taxa-frontend-migration-08-5b` |
| 10 / 13 | 6a | `feat/complete-taxa-frontend-migration-10-6a` | `feat/complete-taxa-frontend-migration-09-5c` |
| 11 / 13 | 6b | `feat/complete-taxa-frontend-migration-11-6b` | `feat/complete-taxa-frontend-migration-10-6a` |
| 12 / 13 | 6c | `feat/complete-taxa-frontend-migration-12-6c` | `feat/complete-taxa-frontend-migration-11-6b` |
| 13 / 13 | 3e | `feat/complete-taxa-frontend-migration-13-3e` | `feat/complete-taxa-frontend-migration-12-6c` |

```text
develop
 └── docs/complete-taxa-frontend-migration-plan   ← tracker PR (draft / no-merge)
      ↑ PR 3a base: docs/complete-taxa-frontend-migration-plan
      └── feat/complete-taxa-frontend-migration-01-3a   ← toolchain bootstrap
           ↑ PR 3b base: …-01-3a
           └── feat/complete-taxa-frontend-migration-02-3b   ← App Router static export
                ↑ PR 3c base: …-02-3b
                └── feat/complete-taxa-frontend-migration-03-3c   ← Tailwind/tokens
                     ↑ PR 3d base: …-03-3c
                     └── feat/complete-taxa-frontend-migration-04-3d   ← Makefile/mount
                          ↑ … 4a → 4b → 5a → 5b → 5c → 6a → 6b → 6c …
                          └── feat/complete-taxa-frontend-migration-13-3e
                               ← atomic cutover, last child in the chain
```

**Per-sub-PR dependency (the contract the corrective plan
revision enforces)**:

- **PR 3a — toolchain bootstrap**. Self-contained. Produces
  `package.json` (with `next`, `react`, `react-dom`,
  `tailwindcss`, `typescript`, `@types/react`, `@types/react-dom`,
  `@types/node` pinned; `engines.node ">=20.9.0"`; `scripts.check-runtime`
  and `scripts.build:web` scripts), `scripts/check-runtime.mjs`,
  `tsconfig.json` (modified in place; the predecessor
  already exists at repo root; base config + `@taxa/<capability>`
  path aliases), and `.nvmrc`. Verification: `npm ci`
  exits 0;
  `node scripts/check-runtime.mjs` exits 0 on Node ≥ 20.9.0,
  exits non-zero below; `npx tsc --noEmit` resolves every
  `@taxa/*` alias (against an empty alias map; subsequent PRs
  populate the modules).
- **PR 3b — App Router static export**. Depends on **3a**: deps
  installed + Node ≥ 20.9.0 contract. Produces
  `src/app/{layout,page}.tsx`, `next.config.mjs`, and the
  `tests/test_app_shell_render.py` witness that runs `npx next
  build` and reads `out/index.html`. This witness is satisfiable
  here because the toolchain is live; it could not be satisfied in
  the original ordering because `npx next build` had no `next`
  binary yet.
- **PR 3c — Tailwind/tokens**. Depends on **3a** (`tailwindcss@^4`
  installed). Produces `src/app/globals.css` (Tailwind 4
  `@import "tailwindcss"` + `@theme` + `@layer base`) and the
  `src/modules/design-system/{infrastructure/index.ts,
  presentation/Icon.tsx, presentation/Button.tsx}` barrel. The
  parity test enumerates legacy `:root` tokens and `var(--token)`
  references against `globals.css` and the generated
  `out/_next/static/chunks/*.css`.
- **PR 3d — Makefile/mount**. Depends on **3b** (App Router
  produces `out/index.html` when `next build` runs) and **3c**
  (Tailwind 4 tokens flow through `next build`). Produces
  `Makefile::api` rewrite (`check-runtime.mjs` → `npm run build:web`
  → `uvicorn … --port 8765` in order, with `make css` becoming a
  no-op shim), the 1-line `api/server.py:54` `WEB_DIR` repoint,
  `src/data/search-engines.js` (byte copy of `web/search_urls.js`
  with `SEARCH_ENGINES` named export), the `tests/test_smoke.py`
  `open()` path update (AC-21 contract preserved), and the
  `tests/test_make_api_build.py` witness plus
  `tests/test_static_mount.py` witness.
- **PR 4a — typed store**. Depends on **3c** (design-system module
  loaded); produces `src/modules/browser-state/**` typed store
  with four read + four write sites.
- **PR 4b — hydration guard**. Depends on **4a** (store available)
  and **3b** (`AppShell` host composition; hydration-safe
  `mounted` flag). Produces `src/modules/app-shell/**` and the
  Playwright zero-hydration-warnings witness.
- **PR 5a — taxonomy port**. Depends on **4b** (hydration-safe
  state read for `tree-source`). Produces
  `src/modules/taxonomy/**` + the port of `web/{tree,
  detail,breadcrumb}.js` to React.
- **PR 5b — research port + CDN pin**. Depends on **5a**
  (taxonomy state read flows shared with research) and **3d**
  (`src/data/search-engines.js` for the `Engine` named export).
  Produces `src/modules/research/**` + CDN pin.
- **PR 5c — E2E selectors + `data-*` contract + delete legacy**.
  Depends on **5b** (all UI components live). Deletes
  `web/*.{html,js,css}` + `tailwind.config.js`.
- **PR 6a / 6b / 6c — Phase 6 validation**. Depends on **5c**
  (candidate path complete). Author the three gate-closure
  verifiers against the candidate build.
- **PR 3e — atomic cutover**. Depends on all six gates green.
  Flips `cutover-manifest.json` working copy, re-runs G3 Tier-2
  verifier against the activated selection, flips
  `apply-progress.md` §Status footer.

**Integration flow**: children merge **in order** into the
tracker. As each child merges, the next child is retargeted onto
the tracker (GitHub retargets automatically when the base branch
is merged and deleted); the tracker accumulates the full feature.
Once PR 3e (the last child) merges, the tracker leaves draft and
merges to `develop` as the single integration point.

**Every child PR body MUST carry** the `## Chain Context`
section (Chain / Tracker PR / Position / Base / Depends on /
Follow-up / Review budget / Starts at / Ends with) plus a
dependency diagram marking the current PR with `📍`. The Chain
Context section is **appended** to the repo PR template — it
does not replace the required `## Resumen` / `## Cambios` /
`## Validación` / `## Lo que NO cambió` sections.

**Diff hygiene**: a child PR whose diff shows files outside its
own slice is a **base bug**, not a review finding. Retarget or
rebase onto the correct predecessor until only the current work
unit appears.

> Order: **3a → 3b → 3c → 3d → 4a → 4b → 5a → 5b → 5c → 6a (G5)
> → 6b (G6) → 6c (G4 measurement) → 3e**. Each child PR targets
> its **immediate predecessor branch**; only the tracker targets
> `develop`. Phase 6 runs **after** the complete candidate path
> (positions 1–9) is green and accumulated on the tracker, and
> **before** PR 3e can land. PR 3e is gated on G1 + G2 + G3
> Tier-1 (all recorded from the predecessor) plus G4 + G5 + G6
> closure (all three delivered by Phase 6). Rollback =
> `git revert <pr3e-sha>` (see §"Rollback under the chain").

## Strict-TDD markers

Every task below uses one of four markers, matching the
predecessor's task vocabulary and the
`tests/test_module_layers.py` /
`tests/test_no_restricted_imports.py` strict-TDD precedent:

- `R` — RED. Author the failing test (or expanded assertion)
  FIRST. The repo MUST remain green before the test is added; the
  new test MUST fail for the right reason before any production
  code is written.
- `G` — GREEN. Implement the minimum production code that flips
  the RED to GREEN. No scope creep beyond the failing test.
- `T` — TRIANGULATE. Add the additional scenarios that catch the
  next failure mode (parametrised matrix, edge cases, RFC-2119-style
  "and / and / and" clauses). Each triangulation scenario lands
  with its own failing-test-then-pass assertion cycle.
- `Refactor` — Clean up GREEN code (rename, extract, dedupe).
  Tests MUST stay green; the refactor MUST NOT change observable
  behaviour or push the diff over the 400-line review budget.

## Phase 3a: Toolchain bootstrap (PR 3a → tracker branch)

Installs the Next 16 / React 19 / Tailwind 4 / TypeScript
toolchain, pins the Node ≥ 20.9.0 runtime contract, and writes
the repository conventions every subsequent sub-PR depends on.
**This PR MUST land before any other sub-PR in the chain** —
the App Router static export at position 2 cannot satisfy its
`next build` witness without the toolchain installed here.

Rescoped from the original `tasks.md` of
2026-09-02 (which placed this work in `Phase 3c` AFTER the
App Router entry): the dependency-order defect the apply gate
identified moved the `package.json` dep pins, the
`scripts/check-runtime.mjs` Node-runtime check, the
`tsconfig.json` base + path-alias config, and the `.nvmrc`
helper forward into position 1. Original Phase 3c's
`Makefile::api` rewrite alone moves into position 4 (`Phase 3d`
in the corrected topology).

- [ ] 3a.1 R — `tests/test_toolchain_bootstrap.py` (new): reads
      `package.json` and asserts (a) `engines.node` literal equals
      `">=20.9.0"`, (b) every required dep is present in
      `dependencies` or `devDependencies` —
      `next@^16`, `react@^19`, `react-dom@^19`,
      `tailwindcss@^4`, `typescript@>=5.1.0`,
      `@types/react@^19`, `@types/react-dom@^19`,
      `@types/node` — and the legacy `autoprefixer`, `postcss`,
      `@tailwindcss/forms` are absent; asserts
      `scripts.check-runtime` and `scripts.build:web` are
      defined; asserts `tsconfig.json` exists at the repo root
      with `compilerOptions.paths` containing the
      `@taxa/<capability>` aliases that match the predecessor
      `tests/test_module_layers.py::CAPABILITIES` set; asserts
      `.nvmrc` exists and pins Node ≥ 20.9.0 (literal). The test
      MUST fail on a fresh repo clone (no `package.json` deps
      yet). <!-- sdd-owner: implementation -->
- [ ] 3a.2 G — `package.json` (modified, ~50 LoC delta) plus regenerated `package-lock.json` (the sole user-approved size exception; it must contain only resolution changes required by this manifest and be reviewed together with it): bumps
      `next`, `react`, `react-dom`, `tailwindcss` to the
      pinned major versions above; adds the TypeScript
      toolchain; removes the legacy `autoprefixer`, `postcss`,
      `@tailwindcss/forms`; sets
      `engines.node = ">=20.9.0"`; adds
      `scripts.check-runtime = "node scripts/check-runtime.mjs"`
      and `scripts.build:web = "next build"`. No other
      fields change. <!-- sdd-owner: implementation -->
- [ ] 3a.3 G — `scripts/check-runtime.mjs` (new, ~25 LoC):
      compares `process.versions.node` against the required
      `20.9.0` floor (encoded as a literal in the script so
      the test asserts it); exits non-zero with a clear error
      naming the observed vs required Node version when below
      the floor; exits 0 on ≥ 20.9.0. <!-- sdd-owner: implementation -->
- [ ] 3a.4 G — `tsconfig.json` (modified in place; the predecessor already exists at repo root; ~50 LoC delta):
      base TypeScript config — `compilerOptions.target`,
      `module`, `moduleResolution`, `jsx`, `strict`,
      `noUncheckedIndexedAccess`, `paths` (the
      `@taxa/<capability>` aliases mapped to
      `src/modules/<capability>`), `baseUrl`. The alias
      contract matches the `CAPABILITIES` set the predecessor
      ships in `tests/test_module_layers.py`. No `src/**`
      files yet — `npx tsc --noEmit` against an empty
      `include: ["src/**/*.ts", "src/**/*.tsx"]` is a no-op
      (the alias map is in place even before any module
      file exists; subsequent PRs add module files). <!-- sdd-owner: implementation -->
- [ ] 3a.5 G — `.nvmrc` (new, 1 LoC): contains the literal
      `20` (nvm will resolve to the latest 20.x.y, which is
      ≥ 20.9.0 once Node 20.9 ships; the `engines.node`
      declaration is the binding contract, `.nvmrc` is a
      convenience hint). <!-- sdd-owner: implementation -->
- [ ] 3a.6 R — `tests/test_check_runtime.py` (new): mocks
      `process.versions.node` (via a small `require`-time
      shim or by patching `process.versions` inside a child
      Node process) to (a) a value below `20.9.0` and asserts
      `scripts/check-runtime.mjs` exits non-zero with a clear
      stderr line naming the observed version; (b) a value
      at or above `20.9.0` and asserts it exits 0. The test
      runs via `subprocess.run([node, scripts/check-runtime.mjs])`
      in two scenarios by passing a small override file
      `scripts/_test-check-runtime.mjs` that throws before
      reaching the floor check. <!-- sdd-owner: implementation -->
- [ ] 3a.7 T — `tests/test_toolchain_bootstrap.py`
      triangulation: assert (a) the `engines.node` literal is
      `">=20.9.0"` exactly (no `~`, `^`, or pinned
      sub-version drift); (b) every pinned dep satisfies
      `^MAJOR` with the major version listed above (no
      `next@^15` sneaking back); (c) `scripts.check-runtime`
      starts with the literal `node scripts/check-runtime.mjs`
      (not `nodejs` and not a path with whitespace); (d)
      `tsconfig.json::paths` resolves every entry in the
      `CAPABILITIES` set the predecessor pins; (e) `.nvmrc`
      is exactly the `20` literal (single line, trailing
      newline). <!-- sdd-owner: implementation -->
- [ ] 3a.8 Refactor — alphabetise `package.json` dependency
      keys; ensure `tsconfig.json` field ordering matches the
      TS 5.x canonical template; ensure `scripts/check-runtime.mjs`
      reads the floor from a `package.json::engines.node`
      parse (instead of a hardcoded literal) so a future bump
      is a single-file change. <!-- sdd-owner: implementation -->

**Per-task evidence (focused test + runtime + rollback)**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3a.1 | `.venv/bin/python3 -m pytest tests/test_toolchain_bootstrap.py -v` | `ls package.json scripts/check-runtime.mjs tsconfig.json .nvmrc` non-empty | `git revert <3a-sha>` removes `scripts/check-runtime.mjs`, `.nvmrc`, restores `tsconfig.json` to its predecessor state, restores `package.json` and `package-lock.json` to legacy deps; nothing else touched |
| 3a.2 | same | `node -e "const p=require('./package.json'); assert(p.engines.node === '>=20.9.0')"`; `npm ci` exit 0 | same |
| 3a.3 | `.venv/bin/python3 -m pytest tests/test_check_runtime.py -v` | `node scripts/check-runtime.mjs` exit 0 on Node ≥ 20.9.0, exit 1 below | same |
| 3a.4 | same as 3a.1 (alias assertions) | `npx tsc --noEmit` exit 0 against the (empty) `src/**` tree | same |
| 3a.5 | same as 3a.1 (`.nvmrc` literal assertion) | `cat .nvmrc` returns `20` literal | same |
| 3a.6 | `.venv/bin/python3 -m pytest tests/test_check_runtime.py -v` | two scenarios above | same |
| 3a.7 | same as 3a.1 | same as 3a.1 | same |
| 3a.8 | same as 3a.1 + 3a.3 | same as 3a.1 + 3a.3 | same |

## Phase 3b: App Router static export (PR 3b → PR 3a branch)

Slices predecessor task 3.1 (`src/app/{layout,page}.tsx` +
`next.config.mjs`) into a PR whose `out/index.html` witness is
satisfiable ONLY because the toolchain from PR 3a now exists.
This is the resolution of the dependency-order defect: in the
original ordering, this witness had no toolchain to satisfy it,
so the sub-PR was unsatisfiable. With PR 3a as its base, PR 3b
can run `npx next build` and assert the static export
contract.

- [ ] 3b.1 R — `tests/test_app_shell_render.py` (new): invokes
      `npx next build` in a `tmp_path` clone (or via subprocess
      shim) and asserts the build emits `out/index.html` with
      `<html lang="en">`, `<head>` carries
      `<meta name="viewport" content="width=device-width,
      initial-scale=1">`, and a `<link rel="preload" …>` for
      the Raleway font that `next/font/google` produces. The
      test reads `out/index.html` after `next build` and
      asserts the markup contract. The test MUST fail on a
      fresh PR 3b branch (no `src/app/{layout,page}.tsx` yet).
      <!-- sdd-owner: implementation -->
- [ ] 3b.2 G — `src/app/layout.tsx` (new, ~50 LoC): host
      `<html>` / `<body>` shell, imports `next/font/google`
      for `Raleway`, `JetBrains Mono`, `Material Symbols
      Outlined`, mounts the `<AppShell>` from
      `@taxa/app-shell`. Imports `./globals.css` so Tailwind 4
      utilities are available app-wide. <!-- sdd-owner: implementation -->
- [ ] 3b.3 G — `src/app/page.tsx` (new, ~70 LoC): the
      single-screen client entry — wraps `<AppShell>` behind a
      `"use client"` boundary, initialises the `mounted` flag
      for hydration safety (the slot is reserved here for use
      in 4b, but no localStorage read happens until then).
      <!-- sdd-owner: implementation -->
- [ ] 3b.4 G — `next.config.mjs` (new, ~30 LoC): declares
      `output: "export"`, `images: { unoptimized: true }`,
      `trailingSlash: false`, `reactStrictMode: true`; matches
      the G2 contract in `design.md` §"Static build / start
      lifecycle". <!-- sdd-owner: implementation -->
- [ ] 3b.5 T — `tests/test_app_shell_render.py` triangulation:
      assert the generated `out/.next/build-manifest.json`
      carries the expected entry for `src/app/layout.tsx` and
      `src/app/page.tsx`; assert the `<body>` element on first
      paint does **not** carry a `data-theme` attribute (no
      localStorage read before hydration); assert the generated
      `out/_next/static/chunks/*.js` includes a chunk that
      references the typed store barrel path
      `@taxa/browser-state` (no actual read yet — only the
      import resolves, confirming the path-alias contract from
      PR 3a's `tsconfig.json` is honoured at build time).
      <!-- sdd-owner: implementation -->
- [ ] 3b.6 Refactor — collapse the page/layout pair into a
      single `<AppShell>` import seam; ensure the Next.js
      + Turbopack build completes in under the recorded
      predecessor budget (no regression beyond the ≤ 0 %
      parity requirement in `design.md` §"Parity / evidence
      plan"). <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3b.1, 3b.5 | `.venv/bin/python3 -m pytest tests/test_app_shell_render.py -v` | `npx next build` exit 0; `out/index.html` non-empty; `out/.next/build-manifest.json` carries the expected entries | `git revert <3b-sha>` removes `src/app/{layout,page}.tsx`, `next.config.mjs`; the toolchain from PR 3a stays; nothing else touched |
| 3b.2, 3b.3 | same | same | same |
| 3b.4 | same | same | same |
| 3b.6 | same | `npx tsc --noEmit` exit 0 against `src/` | same |

## Phase 3c: Design tokens + Tailwind 4 `@theme` (PR 3c → PR 3b branch)

Depends on PR 3a (`tailwindcss@^4` installed). Slices predecessor
task 3.2 (`src/app/globals.css` with `@import "tailwindcss"` +
`@theme` + `@layer base`) plus the design-system barrel the
predecessor PR 2a scaffolded but did not populate. The
`tests/test_tailwind_4_parity.py` enumeration test stays as the
witness.

- [ ] 3c.1 R — `tests/test_tailwind_4_parity.py` (new): reads
      `web/index.html` (legacy source) and asserts each
      `:root { --x }` token is declared with the same name and
      a non-empty value in `src/app/globals.css`; asserts each
      `var(--x)` reference in the legacy `<style>` block
      resolves to a non-empty declaration. <!-- sdd-owner: implementation -->
- [ ] 3c.2 R — `tests/test_tailwind_4_parity.py` (utility-class
      enumeration): for every utility class the legacy build
      emits (`bg-primary`, `text-on-surface`,
      `border-outline-variant`, `bg-surface-container-lowest`,
      `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`,
      `text-on-primary-fixed`, …), the test greps the
      generated `out/_next/static/chunks/*.css` and asserts a
      non-empty CSS declaration resolves. <!-- sdd-owner: implementation -->
- [ ] 3c.3 G — `src/app/globals.css` (new, ~150 LoC): `@import
      "tailwindcss";` + `@theme { … }` block mirroring every
      legacy `:root` token (light palette, dark
      `[data-theme="dark"]` palette, `--realm-*` family);
      `@layer base { … }` block containing every bespoke rule
      from the legacy `<style>` block in source order
      (matches `design.md` §"Design tokens" cascade order
      requirement). <!-- sdd-owner: implementation -->
- [ ] 3c.4 T — extend the parity test to assert the Tailwind 4
      `--color-primary` namespace aliases resolve to the
      legacy `--primary` value (catch silent namespace drift);
      assert `@keyframes`, `.animate-spin`, `color-mix()`
      selectors, the
      `body { overscroll-behavior: none; … }` rule, and the
      `main > :first-child { margin-top: 0 !important; }` reset
      are present under `@layer base` in source order.
      <!-- sdd-owner: implementation -->
- [ ] 3c.5 G — `src/modules/design-system/infrastructure/index.ts`
      (new, ~20 LoC): barrel exports the `<Icon>` (Material
      Symbols Outlined glyph wrapper, frozen names: `search`,
      `folder_open`, `folder`, `chevron_right`,
      `expand_more`, `close`, `settings`, `help`, `science`,
      `science_off`, `download`) plus `<Button>` layout
      primitive. <!-- sdd-owner: implementation -->
- [ ] 3c.6 Refactor — strip any hex literals from `src/` outside
      the design-system module; the grep guard goes into
      `tests/test_design_system_purity.py` (parametrized).
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3c.1–3c.4 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` carries the expected declarations | `git revert <3c-sha>` removes `src/app/globals.css` and `src/modules/design-system/**`; Phase 3a + 3b untouched |
| 3c.5 | same | `npx tsc --noEmit` against `src/modules/design-system/` | same |
| 3c.6 | `.venv/bin/python3 -m pytest tests/test_design_system_purity.py -v` | same | same |

## Phase 3d: Makefile rewrite + `WEB_DIR` repoint + AC-21 reader (PR 3d → PR 3c branch)

Depends on PR 3b (`next build` produces `out/index.html`) and
PR 3c (Tailwind 4 tokens flow through `next build`). Fuses the
original Phase 3c's `Makefile::api` rewrite + the original
Phase 3d's `WEB_DIR` repoint + AC-21 reader update into a
single sub-PR sized at ~240 authored LoC (well under 400).
The Node ≥ 20.9.0 runtime contract lands here as a `Makefile`
recipe step (the script itself was authored in PR 3a).

- [ ] 3d.1 R — `tests/test_make_api_build.py` (new): invokes
      `make api` in a `tmp_path` clone (or via subprocess
      shim) and asserts the Makefile target invokes
      `node scripts/check-runtime.mjs` **first**, then
      `npm run build:web`, then uvicorn binds only after
      `out/index.html` exists; asserts uvicorn does not bind
      when `check-runtime.mjs` exits non-zero (Node < 20.9.0).
      <!-- sdd-owner: implementation -->
- [ ] 3d.2 R — `tests/test_make_api_build.py` (build/uvicorn
      order block): asserts the Makefile target invokes
      `npm run build:web` (`next build`) **before** uvicorn
      binds the port; asserts uvicorn does not bind when
      `next build` exits non-zero; asserts uvicorn fails fast
      if `out/index.html` is missing even after a successful
      `next build`. <!-- sdd-owner: implementation -->
- [ ] 3d.3 R — `tests/test_static_mount.py` (new): asserts
      `api/server.py:54` declares
      `WEB_DIR = Path(__file__).parent.parent / "out"`
      (repointed). Asserts the mount signature at
      `api/server.py:1815` stays byte-identical
      (`app.mount("/", StaticFiles(directory=str(WEB_DIR),
      html=True), name="web")`). Asserts the single-origin
      contract: `uvicorn.run(…)` binds to `127.0.0.1:8765`
      only; `extension/manifest.json::host_permissions` stays
      `["http://localhost:8765/*"]`;
      `content_scripts.matches` stays
      `["http://localhost:8765/*"]`. <!-- sdd-owner: implementation -->
- [ ] 3d.4 G — `Makefile` (modified, ~50 LoC delta in the
      `api:` and `css:` blocks): the `api:` target runs
      `node scripts/check-runtime.mjs` → `npm ci` →
      `npm run build:web` → `uvicorn … --port 8765` in that
      order; the legacy `make css` Tailwind-3.4 step is
      removed (the Tailwind 4 build lives inside
      `next build`); `make css` becomes a no-op shim that
      exits 0 (kept for backward compatibility with any
      external scripts; documented in `Makefile` header).
      <!-- sdd-owner: implementation -->
- [ ] 3d.5 G — `api/server.py` (modified, 1-line delta at
      line 54 + minimal middleware to wire `next/font` preload
      into `out/index.html` response if Next does not inline
      the `<link>` — only added if Phase 3b triangulation
      flags it): `WEB_DIR = Path(__file__).parent.parent /
      "out"`. No other line in `api/server.py` changes.
      <!-- sdd-owner: implementation -->
- [ ] 3d.6 G — `src/data/search-engines.js` (new, ~100 LoC):
      verbatim byte copy of `web/search_urls.js` with the
      export name changed to `SEARCH_ENGINES` (matches the
      canonical literal that `api/server.py::_SEARCH_ENGINES`
      mirrors). The byte shape — `key`, `label`,
      `with_authorship`, ordering — stays identical;
      `template` and `icon` stay intact per
      `tests/test_smoke.py` AC-21 contract. <!-- sdd-owner: implementation -->
- [ ] 3d.7 G — `tests/test_smoke.py` (modified, ~5 LoC delta):
      the `test_search_engine_contract` test's
      `open("web/search_urls.js").read()` is updated to
      `open("src/data/search-engines.js").read()`. The
      Python-side `open("api/server.py").read()` stays
      unchanged. AC-21 contract preserved. <!-- sdd-owner: implementation -->
- [ ] 3d.8 T — `tests/test_static_mount.py` triangulation:
      assert the file move is non-breaking for the contract
      test by running it in a fresh `tmp_path` clone; assert
      the literal's matching fields in
      `api/server.py::_SEARCH_ENGINES` are byte-identical to
      `src/data/search-engines.js` on every entry.
      <!-- sdd-owner: implementation -->
- [ ] 3d.9 T — `tests/test_make_api_build.py` triangulation:
      assert the failure mode where `out/index.html` is
      missing even after a successful `next build`
      (corrupted `out/`) causes `make api` to exit non-zero
      before uvicorn binds; assert uvicorn binds **only** to
      `127.0.0.1:8765` (no second listener on `0.0.0.0` or
      any other port). <!-- sdd-owner: implementation -->
- [ ] 3d.10 Refactor — alphabetical dep order in
      `package.json` (this PR closes any dep alphabetisation
      that PR 3a deferred); `Makefile` recipe tabs preserved
      (no spaces); `src/data/search-engines.js` line endings
      match `web/search_urls.js`. <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3d.1–3d.3 | `.venv/bin/python3 -m pytest tests/test_make_api_build.py -v tests/test_static_mount.py -v` | `make api` exit 0 on Node ≥ 20.9.0; `lsof -i :8765` shows uvicorn only | `git revert <3d-sha>` restores `Makefile::api` (legacy `make css` chain), restores `api/server.py:54` to legacy value, removes `src/data/search-engines.js`, reverts `tests/test_smoke.py` `open()` patch; Phases 3a/3b/3c untouched |
| 3d.4 | same | same | same |
| 3d.5 | same | same | same |
| 3d.6–3d.7 | `.venv/bin/python3 -m pytest tests/test_smoke.py::test_search_engine_contract -v` | `make api` boots uvicorn; `curl http://127.0.0.1:8765/index.html` returns 200 with the contents of `out/index.html` | same |
| 3d.8–3d.9 | same as 3d.1–3d.3 | same | same |
| 3d.10 | n/a (refactor) | same | same |

## Phase 4a: Typed store + 4 read + 4 write sites (PR 4a → PR 3d branch)

Slices predecessor tasks 4.1 + 4.2
(`src/modules/browser-state/{store,keys,defaults}.ts` + 4 read
+ 4 write sites inside `useEffect`). Depends on PR 3c
(design-system module loaded) and PR 3d (`src/app/page.tsx`
references `AppShell` from `@taxa/app-shell`, which imports the
store barrel).

- [ ] 4a.1 R — `tests/test_browser_state_keys.py` (new): greps
      `src/modules/browser-state/**` and asserts exactly four
      `localStorage.getItem(…)` call sites + exactly four
      `localStorage.setItem(…)` + zero
      `localStorage.removeItem(…)` outside the typed `reset()`
      affordance. Asserts no other module
      (`src/modules/taxonomy/**`, `src/modules/research/**`,
      `src/modules/app-shell/**`,
      `src/modules/design-system/**`) reads or writes
      `localStorage` directly. <!-- sdd-owner: implementation -->
- [ ] 4a.2 G — `src/modules/browser-state/domain/keys.ts`
      (new, ~30 LoC): typed `LocalStorageKey` constants
      (`"taxa.settings.theme"`, `"taxa.tree.source"`,
      `"taxa.tree.lastTaxonId"`, `"taxa.tree.kebabOpenId"`)
      plus typed default values per the
      `browser-state-hydration` spec table (`theme: "light" |
      "dark"` default `light`, `tree-source: "col" | "worms" |
      "freshwater"` default `col`, `last-taxon-id: number |
      null` default `null`, `kebab-open-id: number | null`
      default `null`). <!-- sdd-owner: implementation -->
- [ ] 4a.3 G —
      `src/modules/browser-state/infrastructure/store.ts`
      (new, ~80 LoC): four `read(key)` functions and four
      `write(key, value)` functions, one per key, each
      wrapping `try/catch` to swallow `localStorage`
      exceptions (private mode / quota exceeded). Exports a
      typed `subscribe(key, cb)` that returns an unsubscribe
      handle; exports a typed `reset()` that calls
      `localStorage.removeItem` for every key. Plain TS in
      `domain/`; `localStorage` calls live in
      `infrastructure/` per modular-architecture rule 4.
      <!-- sdd-owner: implementation -->
- [ ] 4a.4 G — `src/modules/browser-state/index.ts` (new
      barrel, ~10 LoC): re-exports the four `read`, four
      `write`, `subscribe`, `reset`, the typed defaults, and
      the typed listener type. **No** raw `localStorage`
      getter/setter is exported. <!-- sdd-owner: implementation -->
- [ ] 4a.5 T — `tests/test_browser_state_keys.py`
      triangulation: parametrize the 4-key matrix; assert
      that no `localStorage.getItem` / `setItem` exists in
      `src/modules/research/infrastructure/` (the
      `taxa.fex.treeWidth` splitter key stays owned by the
      file explorer module per the spec §Notes).
      <!-- sdd-owner: implementation -->
- [ ] 4a.6 Refactor — extract the read/write exceptions into
      a `safeStorage` helper that wraps `getItem` / `setItem`
      / `removeItem` with the try/catch; reuse it across the
      four read and four write sites. <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 4a.1, 4a.5 | `.venv/bin/python3 -m pytest tests/test_browser_state_keys.py -v` | `npx next build` exits 0; `out/_next/static/chunks/*.js` carries the typed store bundle | `git revert <4a-sha>` removes `src/modules/browser-state/**`; nothing else touched |
| 4a.2–4a.4, 4a.6 | `.venv/bin/python3 -m pytest tests/test_browser_state_keys.py -v` | `npx tsc --noEmit` against `src/modules/browser-state/` | same |

## Phase 4b: Hydration guard + Playwright zero-warnings test (PR 4b → PR 4a branch)

Slices predecessor tasks 4.3 + 4.4 (`useSyncExternalStore`
behind `mounted` flag + Playwright zero-hydration-warnings
assertion). Depends on PR 4a (store available) and PR 3b
(`AppShell` host composition; the hydration-safe `mounted`
flag was reserved at `src/app/page.tsx` in 3b).

- [ ] 4b.1 R — `tests/test_hydration_console.py` (new,
      Playwright): loads the chromium fixture against `make
      api`, asserts the browser console emits zero
      `Warning: Text content did not match`, zero
      `Warning: Expected server HTML to contain`, and zero
      `Warning: Hydration failed` messages after the first
      paint + rehydration cycle. <!-- sdd-owner: implementation -->
- [ ] 4b.2 G —
      `src/modules/app-shell/presentation/AppShell.tsx`
      (new, ~50 LoC): imports `useSyncExternalStore` from
      the `browser-state` module; reads the typed store
      behind a `mounted` flag set inside `useEffect`; on
      first paint, returns the empty state
      (`selected: null`, `tree: null`,
      `last-taxon-id: null`); on rehydration, applies the
      typed defaults from `localStorage` and updates the
      URL to the `last-taxon-id` if one is stored.
      <!-- sdd-owner: implementation -->
- [ ] 4b.3 G —
      `src/modules/app-shell/infrastructure/page-chrome.tsx`
      (new, ~30 LoC): header tabs (Browser / Classification
      / Settings) with `data-action="nav-tab"` and
      `data-path="<tab>"` attributes; theme toggle stamps /
      unstamps `data-theme` on `<html>` via the typed store;
      help shell, settings view, banner host.
      <!-- sdd-owner: implementation -->
- [ ] 4b.4 T — `tests/test_hydration_console.py`
      triangulation: assert the chromium fixture's console
      after a forced reload (where `localStorage` has a
      stored `theme: "dark"`) shows `data-theme="dark"` on
      `<html>` after the rehydration cycle; assert no
      warning fires when the user toggles the theme between
      paints. <!-- sdd-owner: implementation -->
- [ ] 4b.5 Refactor — extract the `mounted` flag into a
      small `useMounted()` hook in
      `src/modules/browser-state/` so the pattern is
      reusable; reuse it in `AppShell.tsx` and any
      descendant component that reads typed state.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 4b.1, 4b.4 | `.venv/bin/python3 -m pytest tests/test_hydration_console.py -v` | `make api` boots uvicorn; Playwright runs the chromium fixture end-to-end | `git revert <4b-sha>` removes `src/modules/app-shell/presentation/AppShell.tsx` and `infrastructure/page-chrome.tsx`; Phase 4a store stays |
| 4b.2–4b.3 | same | `npx next build` exits 0; `npx tsc --noEmit` against `src/modules/app-shell/` | same |
| 4b.5 | same | same | same |

## Phase 5a: Taxonomy module port (PR 5a → PR 4b branch)

Slices predecessor tasks 5.1 + 5.2 + 5.3
(`src/modules/taxonomy/{domain,application,infrastructure,
presentation}` + port `web/{tree,detail,breadcrumb}.js`).
Depends on PR 4b (hydration-safe state read for `tree-source`).

This sub-PR also lands the **DetailPanel tab strip**
(`Overview` / `Search` / `Folder`), the **`Overview` tab
body**, and the **`Kebab` menu including the `Search online`
action that forces the `Search` tab** (closing the current
live regression where top-level taxa land on `Overview` when
`Search online` is invoked). The header `Browser` tab
re-anchoring (global Research / file explorer) and the
`SearchTab` / `FolderTab` bodies land in PR 5b to keep the
taxonomy port focused on the tree-and-detail surface; PR 5a
only owns the **tab strip scaffolding** plus the
**force-Search contract** that PR 5b's `SearchTab` plugs
into.

- [ ] 5a.1 R — `tests/test_taxonomy_infra.py` (new): mocks
      `fetchTaxon`, `fetchChildren`, `fetchDomains`; asserts
      the application layer exposes view-models only (no raw
      JSON in the presentation layer); asserts the shape of
      `Taxon`, `TaxonTree`, `Breadcrumb` types matches the
      `taxonomy` domain layer; asserts the `DetailPanel` tab
      strip exposes three tabs in fixed order
      (`Overview`, `Search`, `Folder`); asserts `Overview`
      is always available / always visible per the
      user-selected policy; asserts the `Search online` kebab
      action forces the `Search` tab active (NOT
      `Overview`, even for top-level taxa — closes the
      current live regression). <!-- sdd-owner: implementation -->
- [ ] 5a.2 G — `src/modules/taxonomy/domain/taxon.ts`
      (~60 LoC): plain TS types for `Taxon`, `TaxonTree`,
      `Breadcrumb`, `DomainId`; invariants (parent-chain
      walker, rank ordering, materialised-set inclusion).
      Predecessor PR 2d already shipped the type surface;
      PR 5a extends with the parent-chain walker the design
      specifies. <!-- sdd-owner: implementation -->
- [ ] 5a.3 G —
      `src/modules/taxonomy/infrastructure/api.ts`
      (~50 LoC): `fetchTaxon(id)` → `GET /api/taxon/{id}`;
      `fetchChildren(id, source)` →
      `GET /api/taxon/{id}/children?source=<col|worms|
      freshwater>`; `fetchDomains()` → `GET /api/domains`.
      All return typed promises; network errors surface as
      typed `NetworkError`. <!-- sdd-owner: implementation -->
- [ ] 5a.4 G —
      `src/modules/taxonomy/application/useTaxonTree.ts`
      (~80 LoC): the `useTaxonTree()` hook; consumes the
      typed `fetch*` functions from `infrastructure`; emits
      view-models the presentation layer consumes; no React
      imports in `domain` or `infrastructure` layers.
      <!-- sdd-owner: implementation -->
- [ ] 5a.5 G —
      `src/modules/taxonomy/presentation/{Tree,DetailPanel,
      OverviewTab, Breadcrumb}.tsx` (~220 LoC combined):
      ports the legacy
      `web/{tree,detail,breadcrumb}.js` row layout (per-row
      kebab, per-row search icon, per-row materialize
      indicator, breadcrumb monospace family for
      scientific-name segments) **and ships the
      `DetailPanel` tab strip**. The tab strip renders
      **three tabs in fixed order: `Overview`, `Search`,
      `Folder`**, all three reachable from every selection;
      `Overview` is **always available and always visible**
      per the user-selected policy. The `OverviewTab`
      component renders scientific name, accepted status,
      authorship, species count. The `DetailPanel` exports a
      typed tab-activation callback that the `Kebab`'s
      `Search online` action invokes to force the `Search`
      tab active. Every legacy
      `data-action="nav-tab"`, `data-path="<tab>"`,
      `data-theme` attribute is preserved.
      <!-- sdd-owner: implementation -->
- [ ] 5a.6 G — `src/modules/taxonomy/presentation/Kebab.tsx`
      (~40 LoC): per-row kebab menu. Includes the `Search
      online` action wired to dispatch the tab-activation
      callback that **forces the `Search` tab active** on the
      selected taxon (it MUST NOT default to `Overview`, even
      for top-level taxa). The action is the closure of the
      current live regression where `Search online` on
      top-level taxa lands on `Overview`.
      <!-- sdd-owner: implementation -->
- [ ] 5a.7 T — `tests/test_taxonomy_infra.py` triangulation:
      parametrize over the three sources (`col`, `worms`,
      `freshwater`); assert the tree-source toggle re-renders
      the tree with the matching source; assert the
      breadcrumb walker handles root taxa (no parent) and
      orphaned taxa (parent missing in the source) without
      throwing; assert the `DetailPanel` tab strip renders
      all three tabs (`Overview`, `Search`, `Folder`) for
      every selection including top-level taxa; assert
      `Overview` is always visible; assert the `Search
      online` kebab action forces the `Search` tab active
      (closes the current regression).
      <!-- sdd-owner: implementation -->
- [ ] 5a.8 T — extend `tests/test_taxonomy_infra.py` with a
      tab-strip Playwright witness: load the chromium
      fixture, select a top-level taxon (e.g. `Archaea`),
      click the per-row `Search online` kebab action, assert
      the detail-panel tab strip now shows `Search` as the
      active tab (NOT `Overview`). The witness is the
      regression guard against the current live behavior.
      <!-- sdd-owner: implementation -->
- [ ] 5a.9 Refactor — extract the per-row kebab menu into
      `<Kebab>`; reuse it across `Tree` and `DetailPanel`;
      collapse the `DetailPanel` tab-strip rendering into a
      single `<TabStrip tabs={["Overview", "Search",
      "Folder"]} active={...} onChange={...} />` primitive
      exported from `src/modules/design-system/`.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 5a.1, 5a.7, 5a.8 | `.venv/bin/python3 -m pytest tests/test_taxonomy_infra.py -v` | `make api` boots uvicorn; `curl /api/domains` returns the JSON shape; Playwright tab-strip witness exits 0 | `git revert <5a-sha>` removes `src/modules/taxonomy/**` (except `domain/taxon.ts` shipped by predecessor PR 2d — that stays); nothing else touched |
| 5a.2–5a.6, 5a.9 | same | `npx next build` exits 0; `npx tsc --noEmit` against `src/modules/taxonomy/` | same |

## Phase 5b: Research module port + CDN pin (PR 5b → PR 5a branch)

Slices predecessor tasks 5.4 + 5.5 + 5.6
(`src/modules/research/{domain,application,infrastructure,
presentation}` + port `web/{file_explorer,file_viewer,format,
keymap}.js` + CDN pin). Depends on PR 5a (taxonomy state read
flows shared with research and the `DetailPanel` tab strip
scaffold the `Search online` action plugs into) and PR 3d
(`src/data/search-engines.js` for the `Engine` named export).
This is the largest sub-PR at ~395 LoC; it stays under the
400-line budget per the design §"Sub-PR slice under Approach A"
with tight headroom — maintainability is tracked and the
boundary stays within the 400-line per-PR review budget.

This sub-PR also lands the **`SearchTab`** body (categorized
outbound-link list in fixed order `General` / `Taxonomic` /
`Academic` / `Multimedia` / `Documents`), the **`FolderTab`**
body (per-taxon materialize indicator; **separate** from
`SearchTab`), the **`SearchLinkList`** presenter that maps
each `Engine` to an anchor with `target="_blank"` and
`rel="noopener noreferrer"`, and the **header `Browser` tab
re-anchored as global Research / file explorer** (NOT
taxon-scoped; selecting a taxon while `Browser` is active
MUST NOT scope the explorer to that taxon).

- [ ] 5b.1 R — `tests/test_research_infra.py` (new): mocks
      `fetchFiles`, `fetchServe` against
      `/api/taxon/{id}/files{,/serve}`; asserts the format
      dispatcher (PDF / HTML / TXT / MD / DOCX / XLS / XLSX /
      EPUB) routes to the right lazy loader; asserts CDN
      URLs are pinned to `mammoth@1.8.0`, `xlsx@0.18.5`,
      `epubjs@0.3.93`; asserts the `SearchTab` renders the
      five category sections in fixed order (`General`,
      `Taxonomic`, `Academic`, `Multimedia`, `Documents`);
      asserts the `FolderTab` is a separate body from
      `SearchTab`; asserts the header `Browser` tab opens
      the global Research file explorer without a
      `taxonId` filter.
      <!-- sdd-owner: implementation -->
- [ ] 5b.2 G —
      `src/modules/research/domain/{research-file,engine,
      file-node}.ts` (~90 LoC combined): typed `ResearchFile`,
      `Engine`, `FileNode`; the `Engine` type mirrors the
      `SEARCH_ENGINES` literal shape (key, label,
      with_authorship, ordering); the `ResearchFile`
      discriminated union covers the nine supported formats
      plus `Unsupported` and `LegacyDoc` fallbacks.
      <!-- sdd-owner: implementation -->
- [ ] 5b.3 G —
      `src/modules/research/infrastructure/api.ts`
      (~80 LoC): `fetchFiles(id)` → `GET /api/taxon/{id}/files`;
      `fetchServe(id, rel)` →
      `GET /api/taxon/{id}/files/serve?path=<rel>`;
      `loadScriptOnce(name, src)` lazy-loader for CDN
      libraries (pinned URLs; idempotent).
      <!-- sdd-owner: implementation -->
- [ ] 5b.4 G —
      `src/modules/research/infrastructure/search-engines.js`
      (re-export from `src/data/search-engines.js` shipped by
      Phase 3d for the research module's barrel, with the
      `SEARCH_ENGINES` named export unchanged).
      <!-- sdd-owner: implementation -->
- [ ] 5b.5 G —
      `src/modules/research/application/{useFileExplorer,
      useFileViewer}.ts` (~120 LoC combined): the two hooks;
      consume the typed `fetch*` functions; emit view-models
      the presentation layer consumes. <!-- sdd-owner: implementation -->
- [ ] 5b.6 G —
      `src/modules/research/presentation/{FileExplorer,
      FileViewer, RawTableTreeTabs, MetaStrip,
      BreadcrumbPanel, Banners, SearchLinkList,
      SearchTab, FolderTab}.tsx` (~290 LoC combined):
      ports the legacy
      `web/{file_explorer,file_viewer,format,keymap}.js`
      two-pane layout; the Raw / Table / Tree tab strip; the
      meta strip `FORMAT | SIZE | ENCODING`; the nine-format
      dispatcher with CDN-pin lazy loading; the legacy DOC
      and unsupported fallbacks; the CDN failure banner
      `"Viewer offline — raw download unavailable"`; the
      tree search (200 ms debounce, filter / highlight
      modes,
      `state.explorer.search.{query, mode, hideEmpty}`
      persisted); the explorer state reset on taxon switch.
      The `SearchTab` renders the five category sections
      (`General` / `Taxonomic` / `Academic` / `Multimedia` /
      `Documents`) in fixed order; the `SearchLinkList`
      presenter maps each `Engine` to an anchor with
      `target="_blank"` and `rel="noopener noreferrer"`,
      resolving the URL template from `SEARCH_ENGINES`. The
      `FolderTab` is a separate body (per-taxon materialize
      indicator); it MUST NOT be a subset of `SearchTab`.
      <!-- sdd-owner: implementation -->
- [ ] 5b.7 G —
      `src/modules/app-shell/infrastructure/page-chrome.tsx`
      (~30 LoC delta): the header `Browser` tab is
      re-anchored as the **global Research / file explorer**
      — it opens the explorer without a `taxonId` filter,
      and selecting a taxon while `Browser` is active MUST
      NOT scope the explorer to that taxon (the explorer
      continues to show the active research corpus). The
      `data-path="browser"` and `data-action="nav-tab"`
      attribute contract is preserved.
      <!-- sdd-owner: implementation -->
- [ ] 5b.8 T — `tests/test_research_infra.py` triangulation:
      parametrize over the nine formats (PDF, HTML, TXT, MD,
      DOCX, XLS, XLSX, EPUB, plus DOC fallback, plus an
      unsupported extension like `.zip`); assert each
      format dispatches to the matching legacy renderer;
      assert `Content-Type` matches the file extension;
      assert the meta strip renders the matching
      `FORMAT=<EXT> | SIZE=<bytes> | ENCODING=UTF-8`;
      assert the `SearchTab` category sections render in
      the fixed order (`General` / `Taxonomic` / `Academic`
      / `Multimedia` / `Documents`); assert every
      `SearchLinkList` anchor carries `target="_blank"` and
      `rel="noopener noreferrer"`; assert the `FolderTab` is
      rendered separately from `SearchTab`; assert the
      header `Browser` tab opens the global Research
      explorer without a taxon scope.
      <!-- sdd-owner: implementation -->
- [ ] 5b.9 Refactor — extract the meta strip into a single
      `<MetaStrip format={…} size={…} encoding="UTF-8" />`
      component; extract the CDN failure banner into
      `<BannerHost>` so it can be reused in `app-shell`;
      collapse the `SearchTab` category rendering into a
      `<SearchLinkList>` presenter that takes the
      `SEARCH_ENGINES` literal and renders the five
      category sections.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 5b.1, 5b.8 | `.venv/bin/python3 -m pytest tests/test_research_infra.py -v` | `make api` boots uvicorn; `curl /api/taxon/<id>/files` returns the JSON shape; CDN URLs return 200 | `git revert <5b-sha>` removes `src/modules/research/**` and the `Browser` tab delta in `src/modules/app-shell/infrastructure/page-chrome.tsx`; `src/data/search-engines.js` (Phase 3d) stays |
| 5b.2–5b.7, 5b.9 | same | `npx next build` exits 0; `npx tsc --noEmit` against `src/modules/research/` | same |

## Phase 5c: E2E selectors + `data-*` contract + delete legacy (PR 5c → PR 5b branch)

Slices predecessor tasks 5.7 + 5.8 + 5.9 (Playwright + e2e
selector updates + `data-*` contract preservation + delete
`web/*.{html,js,css}` + `tailwind.config.js`). Depends on PR 5b
(all UI components live).

- [ ] 5c.1 R — `tests/test_e2e_file_explorer.py` (modified,
      the test exists but selectors predate the React
      component tree): assert every legacy selector
      (`data-action="nav-tab"`, `data-path="<tab>"`,
      `data-theme`, the per-row kebab attribute, the per-row
      search icon attribute, the per-row materialize
      indicator attribute, the meta strip data attributes)
      still resolves on the new component tree.
      <!-- sdd-owner: implementation -->
- [ ] 5c.2 R — `tests/test_web_toggle.py` (modified): assert
      the theme toggle persists via
      `localStorage.taxa.settings.theme` and stamps
      `data-theme` on `<html>`; assert the OS
      `prefers-color-scheme` media query is honoured as the
      default when no stored preference exists.
      <!-- sdd-owner: implementation -->
- [ ] 5c.3 G — `tests/test_e2e_file_explorer.py` (selector
      update, ~120 LoC delta): update every DOM selector to
      the new component tree (the `data-*` attribute
      contract is preserved; the underlying CSS classes
      change to Tailwind 4 utility classes). Re-run the
      chromium fixture against `make api`; capture the
      Playwright trace artifact. <!-- sdd-owner: implementation -->
- [ ] 5c.4 G — `tests/test_web_toggle.py` (selector update,
      ~80 LoC delta): same pattern as 5c.3 for the theme
      toggle. <!-- sdd-owner: implementation -->
- [ ] 5c.5 T — Playwright + Lighthouse harness integration:
      parameterize over the legacy chromium fixture URL
      paths (`/`, `/index.html`,
      `/_next/static/<h>.js`) and assert the chromium
      fixture's traces match the new component tree.
      <!-- sdd-owner: implementation -->
- [ ] 5c.6 G — `web/index.html` deletion (file removed from
      the repo); `web/{app,state,api,tree,breadcrumb,detail,
      nav,dom,banner,help,keymap,settings,search,
      file_explorer,file_viewer,format,search_urls}.js`
      deletion (18 files removed); `web/index.css` deletion;
      `web/dist/tailwind.css` no longer tracked
      (regenerated by reverted `make css` after rollback,
      never by the new build); `tailwind.config.js`
      deletion. <!-- sdd-owner: implementation -->
- [ ] 5c.7 Refactor —
      `tests/test_evidence_baseline.py`'s
      `test_legacy_module_count_matches_exploration` test
      gets updated to assert the legacy `web/*.js` roster
      is **absent** (the test stays in the suite as a
      regression guard against legacy vanilla modules
      sneaking back into the tree). <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 5c.1, 5c.3 | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py -v` | Playwright runs the chromium fixture end-to-end against `make api` | `git revert <5c-sha>` restores `web/*.{html,js,css}` + `tailwind.config.js`; the test selector updates revert; no `src/` change |
| 5c.2, 5c.4 | `.venv/bin/python3 -m pytest tests/test_web_toggle.py -v` | same | same |
| 5c.5 | same | same; Playwright trace + Lighthouse JSON emitted | same |
| 5c.6 | same | `make api` boots uvicorn; `ls web/` empty | same |
| 5c.7 | `.venv/bin/python3 -m pytest tests/test_evidence_baseline.py::test_legacy_module_count_matches_exploration -v` | same | same |

## Phase 6: Validation work (after complete candidate path, before PR 3e)

The candidate path is the complete set of sub-PRs at positions
1–9 (toolchain bootstrap, App Router static export, Tailwind/
tokens, Makefile/mount, 4a, 4b, 5a, 5b, 5c) accumulated on the
tracker branch `docs/complete-taxa-frontend-migration-plan`
(nothing has reached `develop` yet — the tracker stays draft/
no-merge until the chain completes). Phase 6 runs **after**
that, **before** PR 3e. It is **validation work**, not a
migration objective — it does not generate new `web/**`
source, new `api/server.py` route handlers, or new
`extension/**` files. Its artifacts are recorded in
`apply-progress.md` §Change log as gate-flips (G5 reproducible,
G6 PASS, G4 PASS).

Phase 6 has three sub-steps (6a, 6b, 6c) — one per gate closure
— and they MAY ship as three chain links (the default:
positions 10 / 11 / 12) or collapse into a single child PR at
position 10 depending on whether `apply-progress.md` records
them together or apart. Collapsing shortens the chain but does
not change the topology: the batch still targets the PR 5c
branch and PR 3e still targets whatever the last Phase 6 link
is. The maintainer's `ask-on-risk` policy applies if the batch
exceeds the 400-line budget (estimated ~190 authored LoC split
across the three sub-steps; comfortably under).

### Phase 6a: G5 hydration baseline closure (PR 6a → PR 5c branch)

- [ ] 6a.1 R — `tests/test_hydration_timing.py` (already
      shipped by predecessor PR 1b.3b): the test asserts
      `scripts/measure_hydration.py` exits non-zero when the
      legacy baseline JSON is missing or schema-invalid. The
      test stays; no production code change. New helper
      script `scripts/reconstruct_hydration_baseline.py`
      reads the predecessor's documented
      `delta_server_to_tree_first_paint_ms` numbers from
      `openspec/changes/migrate-nextjs-tailwind4/design.md`
      §"Migration Evidence Baseline" and emits
      `web/dist/evidence-baseline.json` with the same schema
      the hydration test pins. <!-- sdd-owner: implementation -->
- [ ] 6a.2 G — `scripts/reconstruct_hydration_baseline.py`
      (~50 LoC): reads the legacy baseline numbers verbatim
      from the predecessor's design.md (input is the
      markdown source parsed for the table; output is a JSON
      file matching the schema
      `tests/test_hydration_timing.py` pins).
      <!-- sdd-owner: implementation -->
- [ ] 6a.3 G — run `python scripts/measure_hydration.py
      --baseline web/dist/evidence-baseline.json --candidate
      out/` against the positions 1–9-landed candidate
      build; emit the new hydration JSON next to the
      baseline; record the delta in `apply-progress.md`
      §Change log. <!-- sdd-owner: implementation -->
- [ ] 6a.4 T — assert the delta ≤ 0 % on initial paint and
      interaction latency; if it exceeds, fail closed and
      write the exemption request into `design.md` §"Risk
      register" before G5 can flip. <!-- sdd-owner: implementation -->
- [ ] 6a.5 Refactor — collapse the script + run + assert into
      a single `scripts/g5_close.sh` shim that the apply
      worker invokes once and records the outcome in
      `apply-progress.md`. <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 6a.1–6a.5 | `.venv/bin/python3 -m pytest tests/test_hydration_timing.py -v` | `scripts/g5_close.sh` exits 0; `apply-progress.md` §Change log records the gate flip | `git revert <6a-sha>` removes `scripts/reconstruct_hydration_baseline.py` and the `apply-progress.md` delta; the legacy baseline JSON stays (regenerated on the next 6a run) |

### Phase 6b: G6 cutover rehearsal (PR 6b → PR 6a branch)

- [ ] 6b.1 R — `tests/test_rehearse_cutover.py` (new):
      asserts `scripts/rehearse_cutover.py` exits 0 against
      the activated manifest; parametrize over the four
      cutover-unit subsets (`web_dir_only`, `consumers_only`,
      `makefile_only`, `artifact_only`) and assert the
      fail-closed invariant (a subset-only rehearsal
      **fails**). <!-- sdd-owner: implementation -->
- [ ] 6b.2 G — `scripts/rehearse_cutover.py` (~120 LoC):
      dry-runs the atomic cutover unit (WEB_DIR repoint + 26
      consumer updates + Makefile rewrite + `out/` build
      artifact) against a `tmp_path` clone of the candidate.
      Runs the G3 Tier-2 verifier
      (`scripts/verify_consumers.py`) against the activated
      manifest; emits `cutover-rehearsal.json` with
      `activation_complete: true`, `unselected_count: 0`,
      and `silent_fallback_paths: []`. Exits non-zero on any
      subset-only dry-run. <!-- sdd-owner: implementation -->
- [ ] 6b.3 G — flip every `activation_status` and
      `replacement.status` in
      `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
      from `selected` (legacy pre-cut, Tier-1) to the
      **post-cut activation record** (Tier-2) for every one
      of the 26 §3.1 consumers. The flip is a planning
      artifact authored by the apply worker in the same
      release as the rehearsal script. **Predecessor
      `cutover-manifest.json` lives under
      `migrate-nextjs-tailwind4/` (frozen directory) — the
      flip is written into a working copy at
      `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
      per the spec §"Cutover-manifest activation" guidance.**
      The working copy is what PR 3e reads at cutover time;
      the predecessor copy stays byte-identical (frozen).
      <!-- sdd-owner: implementation -->
- [ ] 6b.4 T — assert the rehearsal script reports zero
      silent fallback paths (no "fall back to legacy `web/`
      on build failure" code path exists in `Makefile::api`
      or `api/server.py`). <!-- sdd-owner: implementation -->
- [ ] 6b.5 Refactor — extract the G3 Tier-2 invocation into
      a small `run_g3_tier2(manifest, out)` helper so the
      rehearsal script and the apply worker's PR 3e
      verification share the same code path.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 6b.1, 6b.4 | `.venv/bin/python3 -m pytest tests/test_rehearse_cutover.py -v` | `scripts/rehearse_cutover.py` exits 0 against the activated manifest; `cutover-rehearsal.json` carries `activation_complete: true` | `git revert <6b-sha>` removes `scripts/rehearse_cutover.py`, `tests/test_rehearse_cutover.py`, and the working `cutover-manifest.json` copy; no `src/` or `api/` change |
| 6b.2 | same | same | same |
| 6b.3 | `python scripts/verify_consumers.py --manifest openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json --out out/ --serve --fixture-web-root <candidate>` | G3 Tier-2 verifier exits 0; `CONSUMER-READINESS.json` reports all 26 §3.1 consumers `selected` | same |

### Phase 6c: G4 Playwright + Lighthouse parity measurement (PR 6c → PR 6b branch)

- [ ] 6c.1 R — `tests/test_e2e_file_explorer.py` (already
      updated by Phase 5c) and `tests/test_web_toggle.py`
      (already updated by Phase 5c): the tests stay; no
      production code change. The G4 measurement is the
      delta between the Phase 5c Playwright + Lighthouse
      trace on the new candidate build and the legacy
      chromium fixture the predecessor captured.
      <!-- sdd-owner: implementation -->
- [ ] 6c.2 G — run Playwright + Lighthouse against the
      positions 1–9-landed candidate build; capture
      `out/g4-parity-report.json` with the initial paint and
      interaction latency numbers. Record the delta in
      `apply-progress.md` §Change log. <!-- sdd-owner: implementation -->
- [ ] 6c.3 T — assert the delta ≤ 0 % on initial paint and
      interaction latency; if it exceeds, fail closed and
      write the exemption request into `design.md` §"Risk
      register" before G4 can flip. <!-- sdd-owner: implementation -->
- [ ] 6c.4 Refactor — extract the measurement into
      `scripts/g4_measure.sh` so the apply worker invokes it
      once and records the outcome in `apply-progress.md`.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 6c.1–6c.4 | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py tests/test_web_toggle.py -v` | `scripts/g4_measure.sh` exits 0; `out/g4-parity-report.json` carries initial paint + interaction latency; `apply-progress.md` §Change log records the gate flip | `git revert <6c-sha>` removes the `apply-progress.md` delta; no `tests/` or `scripts/` change (the measurement script stays as a future regression guard) |

## Phase 3e: Atomic cutover (PR 3e → PR 6c branch, gated on all six gates green)

The atomic cutover unit (per `design.md` §"Atomic cutover unit")
changes **exactly the following** in a single release. **No
subset revert is supported.** PR 3e ships only when:

- [ ] **G1 PASS** (recorded from the predecessor).
      <!-- sdd-owner: parent -->
- [ ] **G2 PASS** (recorded against the verified Next 16.3.3 /
      Turbopack clean build; predecessor `apply-progress.md`
      2026-08-30 entry). <!-- sdd-owner: parent -->
- [ ] **G3 Tier-1 PASS** (recorded: all 26 §3.1 consumers
      green against the legacy pre-cut runtime via the
      controlled fixture and `scripts/verify_consumers.py`;
      PR #109 + #111 + #115 + #116).
      <!-- sdd-owner: parent -->
- [ ] **G4 PASS** (Phase 6c measured; recorded in
      `apply-progress.md` §Change log).
      <!-- sdd-owner: parent -->
- [ ] **G5 reproducible** (Phase 6a reconstructed; recorded
      in `apply-progress.md` §Change log).
      <!-- sdd-owner: parent -->
- [ ] **G6 PASS** (Phase 6b rehearsed; recorded in
      `apply-progress.md` §Change log).
      <!-- sdd-owner: parent -->

If any gate is absent, failed, stale (> 7 days), or
incomparable, PR 3e is **blocked**, never success. The four-set
cutover:

1. **`WEB_DIR` constant** at `api/server.py:54` (already
   repointed in Phase 3d; PR 3e flips the build artifact under
   `out/` from the candidate build to the production build
   with the `engines.node >= 20.9.0` runtime check live).
2. **Every active-consumer update** in the predecessor's
   `design.md::§3.1` (already authored by Phase 3d for the
   AC-21 reader path; PR 3e flips the remaining 25 §3.1
   consumers to read from the React component tree instead
   of the legacy `web/*` paths). The flip is the post-cut
   activation record in
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (working copy; predecessor copy stays frozen).
3. **The `Makefile::api` and `Makefile::web` targets**
   (already rewritten by Phase 3d; PR 3e flips the legacy
   `make css` Tailwind-3.4 step from "regenerate
   `web/dist/tailwind.css`" to "exit 0 no-op" — the Tailwind
   4 build lives inside `next build`).
4. **The build artifact** — the `out/` directory itself
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, the error-page
   classification if `404.html` / `500.html` is emitted).
   The artifact is regenerated by the production build at
   cutover time.

The PR 3e task list (only after all six gates green):

- [ ] 3e.1 R — `tests/test_verify_consumers.py` (already
      shipped by predecessor PR #109 + #111 + #115 + #116):
      the test stays; PR 3e re-runs it against the activated
      manifest at
      `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.2 G — run
      `python scripts/verify_consumers.py --manifest openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json
      --out out/` against the candidate build; assert
      `CONSUMER-READINESS.json` exits 0 with
      `activation_complete: true`, `unselected_count: 0`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.3 G — re-run `make api` against the cutover build;
      assert uvicorn binds `127.0.0.1:8765` only; assert
      `curl http://127.0.0.1:8765/index.html` returns
      `out/index.html`; assert
      `extension/manifest.json::host_permissions` stays
      `["http://localhost:8765/*"]`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.4 G — re-run `make smoke` against the cutover
      build; assert 63 passed, 8 skipped baseline preserved.
      <!-- sdd-owner: implementation -->
- [ ] 3e.5 G — flip the gate-status footer in
      `apply-progress.md` §Status from "blocked /
      unreproducible / blocked" to "PASS recorded (G4 / G5 /
      G6 closed by Phase 6a / 6b / 6c)". <!-- sdd-owner: implementation -->
- [ ] 3e.6 T — `tests/test_verify_build.py` (already shipped
      by predecessor G2 evidence): the test stays; re-run
      against `out/BUILD-INVENTORY.json` from the cutover
      build; assert no asset class is missing.
      <!-- sdd-owner: implementation -->
- [ ] 3e.7 Refactor — `apply-progress.md` §Change log
      records the cutover commit hash, the gate-flip dates,
      and the G3 Tier-2 verifier output. <!-- sdd-owner: implementation -->

### Rollback under the chain

PR 3e is the **last child**, not a `develop` PR. Two rollback
windows exist:

| Window | State | Rollback |
|---|---|---|
| Before the tracker merges | Nothing is on `develop`; the cutover lives only on the tracker branch | Hold or close the tracker PR — `develop` is untouched by construction |
| After the tracker merges | The whole chain lands on `develop` in one integration | `git revert <pr3e-sha>` restores the legacy vanilla build atomically (per `design.md` §"Rollback unit") |

For `<pr3e-sha>` to stay addressable on `develop`, the tracker
MUST merge with a **merge commit** (no squash), so the chain's
individual commits survive integration. If the tracker is
squash-merged instead, the atomic rollback unit becomes the
tracker merge itself: `git revert -m 1 <tracker-merge-sha>`.
Either way the rollback is **one** revert covering the full
four-set cutover — **no subset revert is supported**.

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3e.1–3e.2 | `.venv/bin/python3 -m pytest tests/test_verify_consumers.py -v` | G3 Tier-2 verifier exits 0; `CONSUMER-READINESS.json` carries `activation_complete: true` | `git revert <pr3e-sha>` restores the legacy vanilla build atomically (per `design.md` §"Rollback unit"): `web/index.html`, `web/app.js`, the 18 `web/*.js` modules, `web/dist/tailwind.css`, `tailwind.config.js`, the legacy `package.json` + `package-lock.json`, the legacy `Makefile::api`, the legacy `api/server.py:54` |
| 3e.3 | `curl http://127.0.0.1:8765/index.html` returns `out/index.html` | `make api` boots uvicorn on 8765; `lsof -i :8765` shows uvicorn only | same |
| 3e.4 | `make smoke` exits 0 | same | same |
| 3e.5 | n/a (planning artifact) | n/a | same |
| 3e.6 | `.venv/bin/python3 -m pytest tests/test_verify_build.py -v` | `out/BUILD-INVENTORY.json` carries no missing class | same |
| 3e.7 | n/a | n/a | same |

## Out of scope (per `AGENTS.md` and the proposal)

- **No `git push`, `git commit`, `gh pr create`, `git stash`**
  in this tasks phase. The apply phase owns those actions.
- **No new worktrees** — the apply worker creates worktrees per
  `AGENTS.md` §4.
- **No edits to `openspec/changes/migrate-nextjs-tailwind4/**`**
  (predecessor frozen).
- **No backend rewrite** (`api/server.py` route handlers,
  SQLite/WAL logic, materialize flow, SSRF defence in
  `save-url`).
- **No ETL pipeline edits** (`etl/parse_textree`,
  `etl/load_coldp`, `etl/load_worms`,
  `etl/load_freshwater`, migrations).
- **No Chrome extension parity work** — a separate change
  tracks any React-aware extension adaptation.
- **No SEO / metadata / sitemap / robots work**.
- **No new routes** (Settings, About, Help) beyond what the
  legacy UI exposes today.
- **No coverage tooling** (`coverage.available: false`).
- **No visual redesign** (impeccable / Stitch follow-up).

## Predecessor freeze contract (binding)

Every sub-PR in Phases 3a–6c and PR 3e MUST satisfy:

- [ ] `git diff --stat origin/develop -- openspec/changes/migrate-nextjs-tailwind4/`
      shows zero changes. <!-- sdd-owner: parent -->
- [ ] `git diff --stat <immediate-base-branch>` shows **only**
      this slice's files (chain diff hygiene; a polluted diff is
      a base bug — retarget or rebase, do not review around it).
      <!-- sdd-owner: parent -->
- [ ] The PR's branch-protection check rejects any PR that
      modifies `openspec/changes/migrate-nextjs-tailwind4/**`.
      <!-- sdd-owner: parent -->
- [ ] The PR's CI / lint hook rejects the same.
      <!-- sdd-owner: parent -->

If a sub-PR accidentally edits the predecessor directory, the
sub-PR is **blocked** and the apply worker must revert the
accidental edit before the PR can merge. There is no
`size:exception` path for predecessor edits.

## Forecast reconciliation

- **3a** ~210 LoC authored (toolchain bootstrap — `package.json`
  dep pins + `scripts/check-runtime.mjs` + `tsconfig.json` base
  + `.nvmrc` + 2 new tests); **3b** ~175 (App Router entry —
  `src/app/{layout,page}.tsx` + `next.config.mjs` +
  `tests/test_app_shell_render.py`, now satisfiable because 3a
  installed Next); **3c** ~230 (Tailwind tokens + design-system
  barrel); **3d** ~240 (Makefile rewrite + `WEB_DIR` repoint +
  AC-21 reader + 2 new tests, the heaviest of the new splits);
  **4a** ~180; **4b** ~90; **5a** ~280; **5b** ~360; **5c**
  ~200; **6a** ~50; **6b** ~120; **6c** ~20; **3e** ~120.
  **Total**: ~2,245 LoC authored across 13 sub-PRs.
- Largest sub-PR is **5b** at ~360 LoC authored, comfortably
  under the **400-line per-PR review budget** with -40 LoC
  (-10 %) headroom. **No `size:exception` required.**
- Heaviest of the new re-scoped sub-PRs is **3d** at ~240 LoC,
  with -160 LoC (-40 %) headroom against the 400-line budget.
- Sub-PR **6c** is the smallest at ~20 LoC; the G4 measurement
  artifact is recorded in `apply-progress.md` rather than in a
  code diff.
- Phase 6 collectively (6a + 6b + 6c) totals ~190 LoC authored
  and ~120 LoC of measurement artifact. If the maintainer
  prefers a single chained batch for Phase 6, the combined
  LoC is still well under 400; if the maintainer prefers
  three separate sub-PRs for review focus, each is also
  under.
- **Chained PRs recommended: Yes** — each sub-PR fits the
  per-PR budget on its own, but the ~2,245-line total and the
  atomic cutover (the feature MUST integrate before it
  reaches `develop`) put this change in the Feature Branch
  Chain gate.
- **Chain strategy: `feature-branch-chain`** (user-selected).
  Tracker `docs/complete-taxa-frontend-migration-plan` is
  draft/no-merge and is the **only** PR targeting `develop`;
  child PR 3a targets the tracker; each later child targets
  its immediate predecessor branch. This supersedes the
  `AGENTS.md` §4 direct-to-`develop` default and the
  predecessor's apply-progress precedent for this change.
- **Chain length: 13 child PRs + 1 tracker.** Review budget
  per child is the authored LoC listed above; the tracker
  carries no review budget of its own (it is the
  accumulation point).
- **Delivery strategy: `ask-on-risk`** (per preflight; no risk
  flag is open — Approach A is FINAL, the predecessor is
  frozen, every sub-PR fits under 400 lines).
- **Corrective plan revision overhead**: the reordering
  absorbed the work originally attributed to PR 3a, PR 3b,
  and PR 3c into the new positions 1, 2, 3, 4; the absolute
  authored line count moved by ≤ 50 LoC (from ~2,225 to
  ~2,245) because the new split moves some test wiring
  between sub-PRs but does not duplicate production code.
- **Risk / decision (if maintainer prefers a flatter chain)**:
  positions 1–2 (toolchain bootstrap + App Router static
  export) could collapse into a single sub-PR at ~385 LoC
  authored — under 400 but tight. The chain topology
  preserves the bootstrap as a separate review focus so the
  toolchain pins and the App Router contract can be reviewed
  independently; collapsing is not the default.
