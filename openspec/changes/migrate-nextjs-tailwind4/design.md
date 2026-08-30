# Design: migrate-nextjs-tailwind4

## PR 2a Scope Boundary

This design is the migrated PR 2a slice of the
`migrate-nextjs-tailwind4` change. It ships the **layout** of the
modular monolith only:

- the five capability module folders under `src/modules/`
- the four layer folders per module (`presentation`, `application`,
  `domain`, `infrastructure`)
- one public barrel per module (`src/modules/<capability>/index.ts`)
- the `tsconfig.json` path aliases that pin barrel-only cross-module
  access
- the focused layout test (`tests/test_module_layers.py`)

It deliberately does **not** ship:

- any runtime code inside the layer folders (the layer `.gitkeep`
  files are empty placeholders; the actual React components, Tailwind 4
  tokens, fetchers, and stores land in later slices per
  `tasks.md` §Phase 2b – §Phase 5)
- any ESLint rule (the `no-restricted-imports` guard that enforces the
  path aliases lands with PR 2b; PR 2c adds runtime triangulation)
- the finalised **Next.js ↔ FastAPI server-responsibility boundary**
  decision (proposal §Server Responsibility Boundary, §1) — that
  decision is **Open / Evidence-gated** in this slice and is recorded
  in §1 below per `specs/modular-architecture/spec.md` rule 7

This file is the canonical destination of every reference of the form
`scope-decisions.md` that previously appeared in the proposal, tasks,
and spec files. Those references are redirected to this file by the
companion repair pass.

---

## Layer Architecture Decisions

| Decision | Choice | Why |
|---|---|---|
| Capability list | `taxonomy`, `research`, `design-system`, `browser-state`, `app-shell` | Pin by `tests/test_module_layers.py::CAPABILITIES` (verbatim); matches proposal §Capabilities and `tasks.md` §Phase 5 capability ports |
| Layer list | `presentation`, `application`, `domain`, `infrastructure` | Pin by `specs/modular-architecture/spec.md` rule 3 and the test's `LAYERS` tuple |
| Barrel name | `index.ts` (not `.js`, not `barrel.ts`) | `specs/modular-architecture/spec.md` rule 5; the layout test pins the suffix as `.ts` so a future PR cannot silently downgrade to JavaScript |
| Barrel body (PR 2a) | `export {};` (empty re-export) | Keeps the file a valid TypeScript module so `tsc --noEmit` accepts it; the real exports are added slice-by-slice per the comments inside each barrel |
| Module placement | `src/modules/<capability>/` (no `src/components/`, no `src/utils/`, no `src/shared/`) | `specs/modular-architecture/spec.md` rule 2 forbids technical dumping-ground names; the layout test's `test_no_top_level_technical_dump_folders` enforces the negative set |
| Path aliases | `@taxa/<capability>` and `@taxa/<capability>/*` in `tsconfig.json` | Build-time enforcement of barrel-only access (spec rule 5); ESLint guard lands with PR 2b, the runtime triangulation with PR 2c |
| Folder-presence marker | `.gitkeep` placeholders in each layer folder | Lets `is_dir()` resolve before any real file ships; removed by the slice that drops the first real file in that layer |
| Layer-name hygiene | No silent renaming of layers mid-migration | The layout test's `test_no_forbidden_layer_name_per_module` rejects any unexpected direct child of a module |
| Module-count cap | Exactly five modules (today) | The layout test's `test_total_module_count_matches_pinned_5` fails loudly if a stray folder appears or a capability is removed without a spec revision |

---

## Module Layout (PR 2a on disk)

```
src/modules/
├── taxonomy/
│   ├── index.ts                  (barrel — PR 2a: `export {};`)
│   ├── presentation/.gitkeep
│   ├── application/.gitkeep
│   ├── domain/.gitkeep
│   └── infrastructure/.gitkeep
├── research/
│   ├── index.ts                  (barrel — PR 2a: `export {};`)
│   ├── presentation/.gitkeep
│   ├── application/.gitkeep
│   ├── domain/.gitkeep
│   └── infrastructure/.gitkeep
├── design-system/
│   ├── index.ts                  (barrel — PR 2a: `export {};`)
│   ├── presentation/.gitkeep
│   ├── application/.gitkeep
│   ├── domain/.gitkeep
│   └── infrastructure/.gitkeep
├── browser-state/
│   ├── index.ts                  (barrel — PR 2a: `export {};`)
│   ├── presentation/.gitkeep
│   ├── application/.gitkeep
│   ├── domain/.gitkeep
│   └── infrastructure/.gitkeep
└── app-shell/
    ├── index.ts                  (barrel — PR 2a: `export {};`)
    ├── presentation/.gitkeep
    ├── application/.gitkeep
    ├── domain/.gitkeep
    └── infrastructure/.gitkeep
```

Total: **5 modules × 4 layers = 20 layer folders**, **5 barrels**, **0
runtime source files** in this slice. The empty-barrel + `.gitkeep`
shape is the entire PR 2a code surface.

---

## `tsconfig.json` Path Aliases (PR 2a)

| Alias | Resolves to | Used by |
|---|---|---|
| `@taxa/taxonomy` | `src/modules/taxonomy/index.ts` | PR 5 capability ports (tasks 5.1–5.3) |
| `@taxa/taxonomy/*` | `src/modules/taxonomy/*` | PR 2b/c ESLint guard fixtures |
| `@taxa/research` | `src/modules/research/index.ts` | PR 5 ports (tasks 5.4–5.6) |
| `@taxa/research/*` | `src/modules/research/*` | PR 2b/c ESLint guard fixtures |
| `@taxa/design-system` | `src/modules/design-system/index.ts` | PR 3 frontend-bootstrap (tasks 3.1–3.8) |
| `@taxa/design-system/*` | `src/modules/design-system/*` | PR 2b/c ESLint guard fixtures |
| `@taxa/browser-state` | `src/modules/browser-state/index.ts` | PR 4 browser-state (tasks 4.1–4.4) |
| `@taxa/browser-state/*` | `src/modules/browser-state/*` | PR 2b/c ESLint guard fixtures |
| `@taxa/app-shell` | `src/modules/app-shell/index.ts` | PR 3 frontend-bootstrap (host for `src/app/page.tsx`) |
| `@taxa/app-shell/*` | `src/modules/app-shell/*` | PR 2b/c ESLint guard fixtures |

Strict mode is fully flipped on (`strict`, `noImplicitAny`,
`strictNullChecks`, `noUnusedLocals`, `noUnusedParameters`,
`noImplicitReturns`, `noFallthroughCasesInSwitch`) so the future
slices that populate the domain layer must compile under these flags
**without** React, Next, FastAPI, or any I/O subsystem — that is the
`specs/modular-architecture/spec.md` rule 4 invariant for the domain
layer.

`include` is scoped to `src/**/*.ts` and `src/**/*.tsx`; `web`, `etl`,
`tests`, `api` are excluded (they have their own toolchains; mixing
TS strict mode into the Python tooling here would be premature).

---

## File Changes (PR 2a only)

| Path | Action | Description |
|---|---|---|
| `tsconfig.json` | Create | Strict mode + 5 capability path aliases. Full Next.js / JSX / plugin config lands with PR 3 (task 3.1). |
| `src/modules/taxonomy/index.ts` | Create | Public barrel for `taxonomy`. Empty re-export in PR 2a; real exports land with PR 5 (tasks 5.1–5.3). |
| `src/modules/taxonomy/{presentation,application,domain,infrastructure}/.gitkeep` | Create × 4 | Empty layer placeholders for `taxonomy`. |
| `src/modules/research/index.ts` | Create | Public barrel for `research`. Empty re-export in PR 2a; real exports land with PR 5 (tasks 5.4–5.6). |
| `src/modules/research/{presentation,application,domain,infrastructure}/.gitkeep` | Create × 4 | Empty layer placeholders for `research`. |
| `src/modules/design-system/index.ts` | Create | Public barrel for `design-system`. Empty re-export in PR 2a; real exports land with PR 3 (tasks 3.1–3.8). |
| `src/modules/design-system/{presentation,application,domain,infrastructure}/.gitkeep` | Create × 4 | Empty layer placeholders for `design-system`. |
| `src/modules/browser-state/index.ts` | Create | Public barrel for `browser-state`. Empty re-export in PR 2a; real exports land with PR 4 (tasks 4.1–4.4). |
| `src/modules/browser-state/{presentation,application,domain,infrastructure}/.gitkeep` | Create × 4 | Empty layer placeholders for `browser-state`. |
| `src/modules/app-shell/index.ts` | Create | Public barrel for `app-shell`. Empty re-export in PR 2a; real exports land with PR 3 (the host module for the single Next.js route in `src/app/page.tsx`). |
| `src/modules/app-shell/{presentation,application,domain,infrastructure}/.gitkeep` | Create × 4 | Empty layer placeholders for `app-shell`. |
| `tests/test_module_layers.py` | Create | 40 focused layout assertions (10 test functions, parameterised over the 5 capabilities and 4 layers). The full AC-prefixed test names from the proposal §Success Criteria land with PR 5. |
| `openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks}.md` + `specs/modular-architecture/spec.md` | Migrate | Already in `origin/develop` (pre-PR-2a). PR 2a touches them only via the dangling-reference repair in §Open Questions below. |
| `documents-es/openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks}-es.md` + `specs/modular-architecture/spec-es.md` | Migrate | Spanish mirrors of the same three files, per `openspec/AGENTS.md`. |
| `openspec/changes/migrate-nextjs-tailwind4/design.md` (this file) | Create | Companion repair artifact; PR 2a scoped. |
| `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md` | Create | Faithful Spanish mirror of this file. |
| `web/**`, `api/server.py`, `Makefile`, `package.json`, `extension/manifest.json`, `etl/**` | **Unchanged** | Out of PR 2a scope per `tasks.md` §Out of scope. |

Total code+test lines in PR 2a: **409** (`tsconfig.json` 45 + 5
barrels 115 + 20 layer `.gitkeep` placeholders 0 +
`tests/test_module_layers.py` 249). PR 2a carries an accepted
`size:exception` (+9 lines, +2.3 % over the 400-line review budget);
see `apply-progress.md` §Change log (2026-08-29 entry).

---

## Interfaces / Contracts (PR 2a)

```ts
// Each barrel is a valid TypeScript module that re-exports nothing in
// PR 2a. Real exports land slice-by-slice per the comments inside
// each file (preserved verbatim from the migrated code).
//
// src/modules/taxonomy/index.ts
export {};

// src/modules/research/index.ts
export {};

// src/modules/design-system/index.ts
export {};

// src/modules/browser-state/index.ts
export {};

// src/modules/app-shell/index.ts
export {};
```

```jsonc
// tsconfig.json (relevant excerpt)
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "allowSyntheticDefaultImports": true,
    "verbatimModuleSyntax": false,
    "baseUrl": ".",
    "paths": {
      "@taxa/taxonomy":       ["src/modules/taxonomy/index.ts"],
      "@taxa/taxonomy/*":      ["src/modules/taxonomy/*"],
      "@taxa/research":        ["src/modules/research/index.ts"],
      "@taxa/research/*":      ["src/modules/research/*"],
      "@taxa/design-system":   ["src/modules/design-system/index.ts"],
      "@taxa/design-system/*": ["src/modules/design-system/*"],
      "@taxa/browser-state":   ["src/modules/browser-state/index.ts"],
      "@taxa/browser-state/*": ["src/modules/browser-state/*"],
      "@taxa/app-shell":       ["src/modules/app-shell/index.ts"],
      "@taxa/app-shell/*":     ["src/modules/app-shell/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx"],
  "exclude": ["node_modules", "web", "etl", "tests", "api"]
}
```

PR 2a adds **no** new public surface to FastAPI. The `/api/*` contract
remains byte-identical to `origin/develop` per the proposal
§Out of Scope ("Backend rewrite" row) and the existing
`tests/test_smoke.py` baseline (63 passed, 8 skipped).

---

## Testing Strategy (PR 2a)

| Layer | What | Approach |
|---|---|---|
| Layout (focused) | `tests/test_module_layers.py` | 40 assertions across 10 pytest functions, parameterised over the 5 capabilities and 4 layers (RED → GREEN → TRIANGULATE captured). Verifies: modules root exists; each capability folder exists; each layer folder exists per module; each barrel `index.ts` exists; each barrel is `.ts` not `.js`; no top-level technical dump folders; every module root is capability-aligned; total module count is exactly five; no forbidden layer name per module. |
| Backend | (unchanged) | `tests/test_smoke.py`, `etl/tests/`, the rest of the suite. PR 2a must not regress any of the existing 63 passed / 8 skipped baseline. |
| Frontend | (unchanged) | No new frontend test runner. The Playwright fixture stays untouched; PR 5 ports the selectors when React lands. |

The focused layout test pins the **constants** the rest of the design
relies on (`CAPABILITIES`, `LAYERS`, `BARREL_NAME`) so the test will
break loudly if any of these names drift without a corresponding
spec / design revision.

---

## PR 2a Out of Scope

These land in later slices per `tasks.md`; PR 2a must NOT touch any
of them:

- **PR 2b**: `.eslintrc.cjs` barrel-only patterns (5 caps × 4 layers
  = 20 patterns); `barrel_import.js` runtime test fixture.
- **PR 2c**: 20 `scripts/eslint-fixtures/deep_import_<capability>_<layer>.js`
  fixtures and the runtime-triangulation block of
  `tests/test_no_restricted_imports.py`.
- **PR 2d**: `src/modules/taxonomy/domain/taxon.ts` plain TS types +
  invariants; `tests/test_taxonomy_domain.py`.
- **PR 2e**: `tests/test_domain_purity.py` framework-token grep guard
  over the domain layer (this is where spec rule 4 becomes an
  executable test).
- **PR 3**: Frontend-bootstrap — Next.js entry (`src/app/layout.tsx`,
  `src/app/page.tsx`), Tailwind 4 `@theme` block
  (`src/modules/design-system/infrastructure/globals.css`),
  `Makefile::api` rewrite, `api/server.py:1847` repoint at the chosen
  Next.js output (`out/`, per §1 below), `web/search_urls.js`
  relocation to `src/modules/research/infrastructure/search-engines.js`.
- **PR 4**: `src/modules/browser-state/{store,keys,defaults}.ts` —
  four `localStorage` keys, each with exactly one read + one write
  site inside `useEffect` behind a `mounted` flag.
- **PR 5**: Capability ports — `src/modules/taxonomy/{domain,application,infrastructure,presentation}`,
  `src/modules/research/{domain,application,infrastructure,presentation}`,
  `AppShell` host composition; the delete of legacy
  `web/*.{html,js,css}` + `tailwind.config.js`.
- **§1 Decision** (this file, §1 below): the Next.js ↔ FastAPI
  boundary remains **Open / Evidence-gated** through PR 2a. PR 3 is
  the slice that closes it (because PR 3 is where `next build`
  actually runs and `web/dist/build-profile.json` becomes real).

---

## Rollback Boundary (PR 2a)

Reverting PR 2a's commit removes **only** these paths:

```
tsconfig.json
src/modules/taxonomy/index.ts
src/modules/taxonomy/{presentation,application,domain,infrastructure}/.gitkeep
src/modules/research/index.ts
src/modules/research/{presentation,application,domain,infrastructure}/.gitkeep
src/modules/design-system/index.ts
src/modules/design-system/{presentation,application,domain,infrastructure}/.gitkeep
src/modules/browser-state/index.ts
src/modules/browser-state/{presentation,application,domain,infrastructure}/.gitkeep
src/modules/app-shell/index.ts
src/modules/app-shell/{presentation,application,domain,infrastructure}/.gitkeep
tests/test_module_layers.py
```

plus the OpenSpec artifact migrations:

```
openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks,apply-progress,design}.md
openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md
documents-es/openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks,apply-progress,design}-es.md
documents-es/openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec-es.md
```

The PR 2a revert does **not** remove anything from `web/`, `api/`,
`Makefile`, `package.json`, `extension/manifest.json`, `etl/`, or any
of the PR 1 sub-PR artefacts (those live in their own PRs and own
commits). No other PR or sub-PR is coupled to PR 2a's surface in this
slice.

---

## §1 Server Responsibility Boundary Decision (Next.js ↔ FastAPI)

**Status: G1 boundary decision recorded; Approach (A / B / C)
selection remains evidence-gated by G2–G6 (§3.3).**

This entry records the **G1 boundary decision** selected by the
maintainer: **FastAPI remains the sole deployed origin on
`127.0.0.1:8765`**, with `/api/*` paths / methods / shapes / status
/ headers unchanged, and `extension/manifest.json::host_permissions`
staying at `["http://localhost:8765/*"]`. G1 is a boundary decision,
not an Approach selection; Approach (A / B / C) choice remains gated
by G2–G6 (§3.3). Per `specs/modular-architecture/spec.md` rule 7:

> the chosen approach is recorded in `design.md::§1 Decision`
> THEN the entry cites this spec by path as the architectural
> authority
> AND if design sees a conflict with any rule here, it is raised back
> to the proposal before implementation

This entry **cites
`openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
as the architectural authority** for the modular-monolith
constraints (rules 1–5) and confirms that **no conflict** between
the G1 boundary and any spec rule has been identified. Rules 1, 2,
3, 5 are framework-neutral and constrain every Approach equally;
rule 4 (domain stays free of framework / I/O) constrains every
Approach equally; rule 6 explicitly requires every Approach to
honour rules 1–5; rule 7 is this very entry.

### G1 decision: FastAPI sole-origin invariants (recorded)

| Invariant | Rule binding | Anchor |
|---|---|---|
| Sole deployed process / sole HTTP origin on `127.0.0.1:8765`. One FastAPI process; no second container, process group, service, or dev-server port. | spec.md rule 1 | `api/server.py:1818–1820` (`uvicorn.run(app, host="127.0.0.1", port=8765, ...)`) |
| `/api/*` continuity: paths, methods, request shapes, response shapes, status codes, and headers are unchanged. AC-21 (`tests/test_smoke.py:77 test_search_engine_contract`) may read from a new path; the contract shape stays identical. | proposal §Out of Scope | existing `/api/*` handlers in `api/server.py` |
| Extension continuity: `extension/manifest.json::host_permissions` stays at `["http://localhost:8765/*"]`; `content_scripts.matches` stays at `["http://localhost:8765/*"]`. No second origin, no new port. | spec.md rule 1 | `extension/manifest.json:13–15, :21` |
| Modular-monolith compliance: rules 1–7 of `specs/modular-architecture/spec.md` are binding on the chosen Approach. | spec.md rule 6 | spec.md itself |

G1 records these invariants. It does **not** select an Approach, does
**not** claim an evidence gate has passed, and does **not** claim
that legacy parity or performance comparability evidence exists on
disk.

### HTML and static-asset ownership (recorded for G1)

- **HTML owner**: FastAPI's existing `app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")` (at `api/server.py:1815`) serves `/`, `index.html`, and the fallback for direct navigation to unknown routes.
- **Static-asset owner**: The same `StaticFiles` mount serves every `/_next/static/*`, `/assets/*`, font file, CSS bundle, and image. **No second static origin** is permitted by G1.
- **`WEB_DIR` constant**: `WEB_DIR = Path(__file__).parent.parent / "web"` at `api/server.py:54`. Repointing `WEB_DIR` to a Next.js build output (e.g. `out/`, `web/dist/next-static/`, or equivalent) is the only allowed static-mount change in this change.
- **One mount, one rewrite**: `app.mount("/", StaticFiles(...))` stays the only mount; middleware strictly required for the chosen Approach (e.g. SPA-fallback for deep links) is added in `api/server.py` without rewriting the mount signature.
- **`uvicorn` bind**: `uvicorn.run(app, host="127.0.0.1", port=8765, ...)` is the only listener introduced by `make api`. No second port is opened under G1.

### Direct-navigation fallback (recorded for G1)

- FastAPI's `StaticFiles(directory=str(WEB_DIR), html=True)` already provides `index.html` fallback for unknown paths. Direct navigation to `/`, `/index.html`, or any path the mount does not recognise returns the SPA shell via that fallback.
- Deep links (e.g. `/taxon/{id}`, `/help`, `/settings`) resolve to `index.html` via the `html=True` fallback; the client-side router inside the SPA decides the final route. **No server-side route table is required** under G1.
- The fallback is part of the FastAPI `StaticFiles` contract; PR3 does not introduce a parallel fallback mechanism under G1. If a future Approach (e.g. Approach B) needs additional fallback, it is gated by G3 (consumer readiness, §3.3.3).

### Startup and build failure behavior (recorded for G1)

- **Build failure must NOT silently fall back to legacy**. If `next build` exits non-zero, `make api` MUST exit non-zero and MUST NOT start uvicorn. The legacy vanilla files are reachable only via an explicit `git revert` of the cutover unit (§"Atomic cutover and rollback unit" below), never via a quiet degraded mode.
- **Runtime check**: `scripts/check-runtime.mjs` (PR 3 task 3.4) verifies `node --version >= 20.9.0` before uvicorn starts. Failure exits non-zero and aborts the `make api` target.
- **Missing build artifact**: `Makefile::api` invokes the build step before uvicorn binds the port. If the Next.js build artifact is absent (clean clone, no `next build` run), the Makefile target fails before uvicorn binds. There is no implicit "serve the legacy files" code path under G1.
- **Process supervision**: uvicorn runs as the single FastAPI process. There is no second watcher / process supervisor that could swap to legacy on failure.
- **Smoke gate**: `make smoke` (which calls `tests/test_smoke.py`) returns the pre-migration baseline (63 passed, 8 skipped) **before** any Next.js build artifact exists; the smoke gate is independent of the G1 cutover.

### Affected active-consumer manifest (recorded for G1)

- The atomic cutover MUST move every active consumer in `design.md::§3.1` (FastAPI web mount consumers + `web/search_urls.js` consumers) in the same release unit. **No consumer may remain "active" against a path the cutover intends to delete.**
- `§3.1` is the authoritative active-consumer inventory; the future coordinated cutover manifest (§3.4, PR3d deliverable) names a replacement path and a verification path for every consumer.
- **G1 does not edit §3.1.** §3.1 already enumerates 20+ active consumers across `web/index.html`, `web/*.js`, the smoke tests, the evidence-baseline tests, the build-profile tests, the hydration-timing tests, the extension manifest, and `web/search_urls.js` + AC-21. G1 cites §3.1 as the binding list and defers the consumer-side update to the PR3d planning slice.

### Atomic cutover and rollback unit (recorded for G1)

- **Cutover unit (activation)**: PR3e changes exactly the following atomically, in a single release:
  1. `WEB_DIR` constant in `api/server.py:54` (repoint at the chosen Approach's build output).
  2. Every active-consumer update enumerated in `design.md::§3.1` (imports, the AC-21 reader path, every test consumer).
  3. The `make api` / `make web` Makefile targets.
  4. The build artifact itself (the chosen Approach's build output directory).
- **Rollback unit (deactivation)**: `git revert` of the PR3e commit restores all four sets together. **No subset revert is supported** under G1 — partial reverts leave consumers referencing deleted paths and break the SPA shell or AC-21.
- **Verification boundary**: after revert, `make smoke` returns to the pre-migration baseline (63 passed, 8 skipped) and `curl http://127.0.0.1:8765/index.html` returns the vanilla shell. No AC-21 regression; no extension manifest change; no `/api/*` contract drift.

### Prerequisites before PR3b / G2 (recorded for G1)

PR3b / G2 work MUST NOT begin until every prerequisite below is
satisfied. Absent, failed, stale (>7 days), or incomparable evidence
is **blocked**, never success.

| Gate | Producer / artifact | Status |
|---|---|---|
| G2 | `scripts/verify_build.py` + `BUILD-INVENTORY.json` | pending PR3b |
| G3 | `scripts/verify_consumers.py` + `CONSUMER-READINESS.json` (every `§3.1` consumer named) | pending PR3d |
| G4 | Playwright + Lighthouse parity harness (existing `tests/test_smoke.py` 63 passed / 8 skipped preserved) | pending PR3d |
| G5 | `scripts/measure_hydration.py` (PR 1b.3a, reconstruction pending) + Lighthouse comparability; legacy baseline **not** on disk | blocked until reconstruction |
| G6 | `scripts/rehearse_cutover.py` referencing `design.md::§3.4` | pending PR3d |

The disposable static-export probe (PRs #93–#97) remains
evidence-only; its artifacts are inputs to G4 / G5 evidence, not a
substitute for an Approach selection. **No claim of legacy parity
or performance comparability** is recorded in this slice.

### Evidence required to close the §1 Approach selection

The Approach selection (A, B, or C) is recorded here **only** once
**all** of the following evidence is on disk:

1. `BUILD-INVENTORY.json` from PR3b (`scripts/verify_build.py`).
2. `CONSUMER-READINESS.json` from PR3d (`scripts/verify_consumers.py`).
3. Playwright + Lighthouse delta from PR3d against the legacy baseline on the chromium fixture.
4. Hydration timing from `scripts/measure_hydration.py` (PR 1b.3a, reconstruction pending) plus Lighthouse comparability.
5. `cutover-rehearsal.json` from PR3d dry-run (`scripts/rehearse_cutover.py`).

Until all five are on disk and pass their thresholds (§3.3.2–§3.3.6),
the §1 entry stays at **G1 recorded; Approach selection
evidence-gated**, and `## §1 Approach: <A | B | C>` is **not**
written. If those measurements show that the `next build` static
export (Approach A) achieves ≤ 0 % regression on the perf budget
(G5), preserves every consumer contract (G3), preserves behaviour
parity (G4), and the cutover rehearsal succeeds (G6), then
**Approach A is the default §1 Approach selection** because it
preserves the single-port contract (G1) and has the smallest blast
radius. Any other outcome must escalate back to the proposal before
any code lands. **This default fail-safe is conditional on real
evidence; it is NOT a selection made in this slice.**

### What this entry does NOT claim

- It does **not** claim Approach A (static export under FastAPI) is selected. Approach A is one of three candidates; selection is gated by G2–G6.
- It does **not** claim G1 "passed". G1 is a boundary decision recorded by design; the evidence gates G2–G6 remain blocked.
- It does **not** claim comparable legacy-product performance or parity evidence exists, nor that the `§3.1` active-consumer manifest is finalised. The legacy baseline artifact `web/dist/evidence-baseline.json` was reconstruction-pending in PR 1b.2 / 1b.3a / 1b.3b; the G5 hydration baseline, G4 parity harness, and `§3.4` cutover manifest are separate PR3d deliverables.

---

## Runtime Engine Contract

The Next.js 16 hard requirement is recorded in `package.json::engines.node`
when `package.json` is rewritten (PR 3 task 3.4). Until then, the
contract lives in this design:

- **Node.js `>= 20.9.0`** is the only accepted runtime.
- Enforcement: `scripts/check-runtime.mjs` (lands with PR 3 task 3.4)
  exits non-zero when `node -v` reports a lower major/minor/patch.
- The check is invoked from `Makefile::api` before uvicorn starts.
- This is the canonical record replacing the prior
  `scope-decisions.md::§8` reference; PR 3 is the slice that wires
  the actual guard.

---

## Migration Evidence Baseline

The legacy-build baseline numbers (total source size, module roster,
chromium pin, hydration timing) are produced by the PR 1b.x sub-PRs
and stored in `web/dist/evidence-baseline.json` (build-time emission,
emitter ships with PR 1a.1; the schema lands with PR 1a.2; the
chromium block with PR 1b.1; the remainder with PR 1b.2; the
hydration subset with PR 1b.3a; the remainder with PR 1b.3b). PR 1b.3b
task 1b.3b.3 references this baseline as the place where the legacy
numbers already live (replacing the prior
`scope-decisions.md::§0` reference).

PR 2a does **not** consume the baseline itself; PR 5 is the first
slice that compares migrated slices against it.

---

## Dependency Surface

The dependency justification (per-capability additions, removals,
transitional `@tailwindcss/cli`, `next/font` for the existing
Material Symbols Outlined + Raleway + JetBrains Mono fonts) lives in
this design rather than a separate `scope-decisions.md` file. The
additions are:

- `next@^16` (App Router)
- `react@^19`, `react-dom@^19`
- `tailwindcss` ^4.x
- `@tailwindcss/cli` (transitional only; removed when the vanilla
  build is retired)
- `typescript >= 5.1.0`, `@types/react@^19`,
  `@types/react-dom@^19`, `@types/node`

Removals: `autoprefixer`, `postcss`, `@tailwindcss/forms`. Each
removal is justified by the proposal §Dependencies list; PR 3
task 3.4 lands the actual `package.json` rewrite.

---

## Open Questions

- [x] **§1 G1 boundary decision**: recorded in §1 above (this slice).
      FastAPI remains the sole deployed origin on `127.0.0.1:8765`;
      `/api/*` and `extension/manifest.json::host_permissions` are
      unchanged; HTML / static-asset ownership, direct-navigation
      fallback, startup / build-failure behavior, affected
      active-consumer manifest, atomic cutover / rollback unit, and
      PR3b / G2 prerequisites are defined. **G1 is a boundary
      decision, NOT an Approach selection** (see §1 above, "What this
      entry does NOT claim").
- [ ] **§1 Approach selection (G2–G6)**: still open. Closed when the
      five measurements (§1 "Evidence required to close the §1
      Approach selection") are produced by PR3b / PR3d and the chosen
      Approach is recorded here as `## §1 Approach: <A | B | C>` with
      a cite back to
      `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
      per rule 7.
- [ ] **Hydration cost on `taxonomy/tree`**: RED test in
      `tests/test_hydration_timing.py` (no console `hydration`
      warnings under Playwright). Closes when PR 5 task 5.8 lands
      and the delta is `≤ 0 %`. The legacy-product performance
      baseline that feeds this gate is **not** on disk; the gate is
      blocked until the PR 1b.3a / 1b.3b deliverables reconstruct.
- [ ] **Review budget (closed)**: the proposal's
      `apply-progress.md` §Historical context estimated ~1369 LoC for
      the original PR 2 unit. The PR 2a–2e repartition reduced the
      per-sub-PR authored count to ≤ 339 LoC except PR 2a at 409
      code+test lines, which carries an accepted `size:exception`
      (+9 lines, +2.3 %) per `apply-progress.md` §Change log
      (2026-08-29 entry).

---

## PR 2a Reference Set

Every reference this design makes back into the migrated proposal,
tasks, and spec artifacts:

| This design § | Cites |
|---|---|
| PR 2a Scope Boundary | `tasks.md` §Phase 2a, §Phase 2b, §Phase 2c, §Phase 2d, §Phase 2e, §Phase 3, §Phase 4, §Phase 5 |
| Layer Architecture Decisions | `specs/modular-architecture/spec.md` rule 2, rule 3, rule 5 |
| Module Layout (PR 2a on disk) | `tests/test_module_layers.py::CAPABILITIES`, `::LAYERS`, `::BARREL_NAME` |
| `tsconfig.json` Path Aliases | `specs/modular-architecture/spec.md` rule 5 |
| File Changes (PR 2a only) | `proposal.md` §Affected Areas, `tasks.md` §Phase 2a |
| Interfaces / Contracts | `tests/test_module_layers.py` |
| Testing Strategy (PR 2a) | `proposal.md` §Out of Scope ("Backend rewrite") |
| PR 2a Out of Scope | `tasks.md` §Phase 2b – §Phase 5 |
| Rollback Boundary (PR 2a) | `apply-progress.md` §Rollback boundary per sub-PR |
| §1 Server Responsibility Boundary Decision | `proposal.md` §Server Responsibility Boundary, `specs/modular-architecture/spec.md` rule 7 |
| Runtime Engine Contract | `proposal.md` §Dependencies ("Runtime engine"), `tasks.md` task 3.4 |
| Migration Evidence Baseline | `tasks.md` §Phase 1a.1 – §Phase 1b.3b |
| Dependency Surface | `proposal.md` §Dependencies |
| Open Questions | `apply-progress.md` §Historical context, §Change log |

---

## PR3a Boundary Scope Planning

This section supersedes the prior assumption that PR3 could bootstrap
a FastAPI-served static export and then relocate `web/search_urls.js`.
It adds the **PR3a planning artifacts only** — the active-consumer
inventory (§3.1) and the G1 boundary decision scope (§3.2). The G2–G6
evidence matrix and the coordinated cutover manifest land in later
planning slices per `tasks.md` §Phase 3d/3e and are **not** in this
artifact. **The boundary decision itself is not selected by this
artifact, no evidence is recorded as passing, and PR3e cannot activate
until G1–G6 close.** Static export under FastAPI remains blocked by
the proposal and is not reopened by this planning pass.

### §3.1 Active-consumer inventory

This is the concrete inventory of every active runtime consumer of the
two protected ownership edges. Until PR3e activates the atomic cut,
**no path in this map may be removed or relocated** without breaking
the active vanilla frontend or AC-21. The inventory is the
authoritative reference for the future coordinated cutover manifest
and G3's consumer-readiness evidence.

#### §3.1.1 Active consumers of the FastAPI web mount

The current FastAPI process serves the vanilla frontend via:

```python
# api/server.py:1815
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

(`WEB_DIR = Path(__file__).parent.parent / "web"` at `api/server.py:54`;
uvicorn bound at `api/server.py:1820` to `127.0.0.1:8765`.)

Every path below is an active runtime read of that mount:

| Consumer path | What it reads | When |
| --- | --- | --- |
| Browser / Chrome extension / `curl GET /` | `web/index.html` (via `html=True` fallback) | Every page load |
| Browser / Chrome extension `GET /index.html` | `web/index.html` directly | Direct URL load |
| `web/index.html:13` `<link>` tag | `web/dist/tailwind.css` (built by `make css`) | On every page load |
| `web/index.html:2163` `<script type="module">` tag | `web/app.js` (the **only** direct script tag in `index.html`) | On every page load |
| `web/app.js:39–54` ES `import` lines | `state.js`, `api.js`, `tree.js`, `breadcrumb.js`, `detail.js`, `nav.js`, `dom.js`, `banner.js`, `help.js`, `keymap.js` (10 modules) | First load after `app.js` parses |
| `web/app.js:88` dynamic `import()` | `settings.js` (lazy — settings panel) | When the user opens the settings panel |
| `web/nav.js:14–17` ES `import` lines | `detail.js`, `search.js`, `tree.js`, `state.js`, `api.js`, `dom.js` | On first nav.js parse |
| `web/nav.js:252, 295, 308, 331, 685` dynamic `import()` calls | `settings.js`, `file_explorer.js` (lazy) | Lazy on settings / file-explorer open |
| `web/breadcrumb.js:8` `import` | `format.js` (plus `dom.js` + `state.js`) | On every breadcrumb render |
| `web/search.js:7` `import` | `format.js` (plus `state.js` + `api.js` + `dom.js`) | On first search.js parse |
| `web/detail.js:482` dynamic `import()` | `file_explorer.js` (lazy — file viewer) | When the user opens the file explorer |
| `web/file_explorer.js:24` `import` | `file_viewer.js` (and `format.js`) | On first file_explorer parse |
| `web/file_viewer.js::loadScriptOnce` (URLs at lines 25–27, helper at 40+) | `mammoth@1.8.0`, `xlsx@0.18.5`, `epubjs@0.3.93` CDN libs — URLs pinned at `web/index.html:2180, 2188, 2194` | Lazy on .docx / .xlsx / .epub open |
| `tests/test_smoke.py:150` (`test_static_index_html_served`) | `GET /index.html` (asserts 200 + HTML) | Smoke test |
| `tests/test_smoke.py:157` (`test_static_app_js_served`) | `GET /app.js` (asserts 200 + ≥1000 bytes) | Smoke test |
| `tests/test_evidence_baseline.py:276` (`test_legacy_html_present_and_nontrivial`) | reads `WEB_DIR/index.html` | PR 1a.1 baseline evidence |
| `tests/test_evidence_baseline.py:294` (`test_legacy_module_count_matches_exploration`) | reads `WEB_DIR.glob("*.js")` | PR 1a.1 baseline evidence |
| `tests/test_evidence_baseline.py:316` (`test_legacy_total_source_size_below_threshold`) | walks `WEB_DIR` bytes | PR 1a.1 baseline evidence |
| `tests/test_build_profile.py` (e.g. `test_emit_writes_profile_with_required_keys` at line 110) | reads `web/dist/build-profile.json` (built by `scripts/emit_build_profile.mjs`) | PR 1a.1 build profile |
| `tests/test_hydration_timing.py` (e.g. `test_measure_hydration_exits_zero_on_valid_artifact` at line 140) | measures `web/index.html` server-shell first-paint | PR 1b.3a/b hydration evidence |
| `extension/manifest.json:13–15` (`host_permissions`) + `:21` (`content_scripts.matches`) | `http://localhost:8765/*` injection target | Every Chrome content-script injection on the local origin |

**Move/delete authority for the mount**: PR3e, atomic with every
active consumer listed above. No other slice may change this mount,
the `WEB_DIR` constant, or the served directory.

#### §3.1.2 Active consumers of `web/search_urls.js`

The current `web/search_urls.js` exports `SEARCH_ENGINES` (14 entries)
and `CATEGORIES` and is consumed by active vanilla code, by AC-21's
contract test, and by the search-tab grouping test:

| Consumer path | What it reads | When |
| --- | --- | --- |
| `web/detail.js:24` | `import { SEARCH_ENGINES, CATEGORIES } from "./search_urls.js"` | On every detail panel render |
| `web/detail.js:325` | `new Map(SEARCH_ENGINES.map((e) => [e.key, e]))` builds `engineByKey` | On every detail panel render |
| `web/detail.js:332` | `for (const e of SEARCH_ENGINES)` populates the Search tab UI | On every detail panel render |
| `tests/test_smoke.py:77–100` (AC-21 `test_search_engine_contract`) | `open("web/search_urls.js").read()` + regex parse on `{ key, label, with_authorship }` | Contract test on every `make test` |
| `tests/test_search_categories.py:141` | references `CATEGORIES in web/search_urls.js` (expected grouping: `general`, `taxonomic`, `academic`, `multimedia`, `documents`) | Search tab tests |

**Server-side mirror**: `api/server.py:697 _SEARCH_ENGINES = [...]` is
the server's authoritative source for `/api/taxon/{id}/searches`. The
frontend reads the JS file only for `icon` and `label` fallback when
the server response is unavailable; URLs always come from the server
(`urllib.parse.quote_plus`). The AC-21 contract test
(`tests/test_smoke.py:77–100`) enforces that the two literals agree on
`key`, `label`, and `with_authorship` in the same order.

**Move/delete authority for `web/search_urls.js`**: PR3e, atomic with
the five consumers above. PR3a may **only** author a future location
(e.g. `src/data/search-engines.js`) and document it; PR3e must update
the imports, the test reader path, and the legacy file in the same
release unit.

### §3.2 Supported single-FastAPI-origin boundary decision scope (G1 input)

The boundary to be decided is **how a single FastAPI deployable owns
the local origin `127.0.0.1:8765` while a replacement UI ships beside
it**. The scope below enumerates every input that PR3a records. **No
input is selected, evidenced, or implied to be passing by this
artifact.** The actual decision remains blocked pending a future
proposal revision that supplies the evidence the current proposal
explicitly rejects.

#### §3.2.1 Fixed (rules-bound, not subject to PR3a choice)

- **Process / origin ownership** — FastAPI is the sole deployable
  process and the sole HTTP origin on `127.0.0.1:8765`
  (`api/server.py:1818–1820`:
  `if __name__ == "__main__": uvicorn.run(app, host="127.0.0.1", port=8765, ...)`).
- **API continuity** — `/api/*` paths, methods, request shapes,
  response shapes, status codes, and headers are unchanged. AC-21
  (`tests/test_smoke.py:77 test_search_engine_contract`) is unchanged
  except for the path it reads from.
- **Extension continuity** — `extension/manifest.json::host_permissions`
  stays at `["http://localhost:8765/*"]` (lines 13–15);
  `content_scripts.matches` stays at `["http://localhost:8765/*"]`
  (line 21). No second origin, no new port.
- **Modular-monolith compliance** — rules 1–7 of
  `specs/modular-architecture/spec.md` are binding on the chosen
  approach.

#### §3.2.2 In scope (requires decision)

- **HTML owner** — which process serves `/`, `index.html`, and the
  fallback for direct navigation to unknown routes (deep links to
  `/taxon/{id}` and similar).
- **Static-asset owner** — which process serves JS bundles, CSS,
  fonts, and any other `/assets/*`.
- **Build/start contract** — exact commands, Node runtime check
  (`node --version ≥ 20.9.0`), artifact location, and failure
  behavior. **Build failure must NOT silently fall back to the legacy
  runtime.**
- **Direct-navigation fallback** — exact mechanism for `/taxon/{id}`
  and other client-only routes when reached without a server
  roundtrip.
- **Cutover/rollback unit** — exact paths changed together in
  activation and exact revert boundary.

#### §3.2.3 Out of scope (already rejected by proposal)

- **Static export under FastAPI** — blocked by evidence gates; not a
  default, fallback, or implementation target in PR3b–PR3e. Reopening
  requires a proposal revision with new evidence.
- **Two independently active runtimes** — rejected; coordinated legacy
  cut, not compatibility layer.
- **Mount-only or search-file-only migration** — rejected; both edges
  must move atomically with all consumers (§3.1).
- **Anything that requires changing `/api/*`, the extension manifest,
  or the SQLite/DB behavior** — out of scope for this change.

#### §3.2.4 Decision authority

When the G1 boundary is recorded (future proposal revision + G1
evidence), it MUST:

1. Comply with `specs/modular-architecture/spec.md` rules 1–7.
2. Cite `specs/modular-architecture/spec.md` as architectural
   authority.
3. List every active-consumer path it impacts; each must appear in the
   future coordinated cutover manifest.
4. Pass G1 (this artifact, design-review minutes) before any
   PR3b/3c/3d/3e work begins.

### §3.3 Evidence producers and thresholds

Every gate has a named producer, an invocation command, an artifact path, and an acceptance threshold. **No gate is marked passing by this artifact.** Absent, failed, stale (>7 days), or incomparable evidence is **blocked**, never success. PR3a records the producer + command + artifact + threshold matrix below; PR3b–PR3e attach actual results.

#### §3.3.2 G2 — foundation build

| Field | Value |
| --- | --- |
| Producer | `scripts/verify_build.py` (NOT YET AUTHORED — to land in PR3b alongside the foundation) |
| Command | `python scripts/verify_build.py --out <build-root> --node-min 20.9.0` |
| Artifact | `<build-root>/BUILD-INVENTORY.json` + build log + `node --version` snapshot |
| Threshold | (a) build command exits 0; (b) inventory lists every expected artifact (HTML entry, JS bundles, CSS, fonts); (c) Node version meets `≥20.9.0`; (d) build failure produces a non-zero exit and does **not** silently fall back to legacy |

##### §3.3.2.1 G2 contract definition (canonical input for the strict-TDD G2 verifier)

This subsection is the canonical input for the later strict-TDD G2 verifier (`scripts/verify_build.py` + `<build-root>/BUILD-INVENTORY.json`). **G2 is `blocked — contract defined; verifier not implemented`, not `passed`, until every assertion below is authored and green.**

| Knob | Value |
| --- | --- |
| Candidate workspace root (authorized, non-activation) | `tools/g2-candidate/` — per the parent task. The candidate workspace does **not** wire FastAPI, `web/`, CI, root `package.json`, `Makefile`, or `extension/manifest.json`. It does **not** select Approach A / B / C. It does **not** select static export. It exists as a self-contained build root for G2 verification only; mounting its output under FastAPI is a separate G3+G6 decision. |
| Expected build command | `<candidate-root>/node_modules/.bin/next build` invoked with `cwd = <candidate-root>`; non-zero exit propagates; **no** silent fallback to legacy files; capture stdout/stderr to `<candidate-root>/build.log`. |
| Expected build output root | `<candidate-root>/out/` (Next.js static export; `next.config.mjs` carries `output: "export"` plus `images: { unoptimized: true }` and `trailingSlash: false`). |
| Required asset classes (application-route) | (i) sole normal application-route HTML entry `<candidate-root>/out/index.html`; (ii) **JS class** = one-or-more non-empty `*.js` files anywhere under `<candidate-root>/out/_next/static/chunks/**` (Next.js 16 / Turbopack emits flat JS chunks with **no `chunks/app/` subdirectory requirement**); (iii) **CSS class** = one-or-more non-empty `*.css` files anywhere under `<candidate-root>/out/_next/static/chunks/**` (CSS bundles are co-located with JS chunks under `chunks/**`, **not** under a separate `static/css/` directory); (iv) static fonts under `<candidate-root>/out/_next/static/media/` if `next/font` is used. The verifier classifies `index.html` as the **only** normal application-route HTML entry; `404.html` and `500.html`, if Next.js emits them, are recorded under the **separate** `error_pages` asset class (see next row) and never under the application-route class. |
| Error-page exemptions (classified separately) | `404.html` and `500.html` are explicitly permitted error-page exemptions. If present, the verifier records them under the **separate** `error_pages` asset class — they are **not** promoted to application-route entries, are **not** listed under `assets[]` for the `application_route_html` class, and their absence is **never** a missing-classes failure for the application-route contract. Their presence is reported, not required. |
| Post-build manifest staging (atomic) | Before inventory validation, the G2 verifier MUST atomically stage the Next manifests from `<candidate-root>/.next/` into `<candidate-root>/out/.next/` against the **Next.js 16 / Turbopack verified contract**: `<candidate-root>/.next/build-manifest.json` → `<candidate-root>/out/.next/build-manifest.json` is **required** (the missing-class failure is its absence from the build output); `<candidate-root>/.next/app-build-manifest.json` → `<candidate-root>/out/.next/app-build-manifest.json` is **optional and never a missing-class failure** — the verifier attempts the copy only when the source manifest exists, records `staged` / `not_emitted` in `assets[]`, and never fails on its absence (the actual clean Next 16.3.3 / Turbopack build emits only `build-manifest.json`). `build-manifest.json` staging is all-or-nothing: any individual required-manifest copy failure aborts the staging step, removes any partial staging, leaves **no** valid `BUILD-INVENTORY.json` on disk, and propagates a non-zero exit. The verifier validates the staged manifests only after the required `build-manifest.json` copy succeeds; absence of `<candidate-root>/.next/build-manifest.json` is a staging failure. |
| Size exception (generated file, conditional) | A `size:exception` applies **only** to `tools/g2-candidate/package-lock.json`, and **only after** `npm ci` exits 0 against the candidate's local `tools/g2-candidate/package.json`. The exception is conditional and void if `npm ci` fails (no `package-lock.json` is committed). **No other generated file under `tools/g2-candidate/` is excepted** from the per-PR review budget — every other generated artifact (build output, manifests, logs, capture artifacts, other lockfiles) is counted under the authored-lines cap. |
| Inventory schema & location | `<candidate-root>/out/BUILD-INVENTORY.json` — JSON object with keys `node_version` (string, ≥ `"20.9.0"`), `candidate_root` (string), `build_command` (string), `build_started_at` / `build_finished_at` (ISO-8601 strings), `exit_code` (int), `assets[]` (each entry: `{class, path, sha256, bytes}`), `missing_classes[]` (asset classes absent from `out/`); emitted atomically by the G2 verifier **only when** every precondition holds: `npm ci` exits 0 (otherwise no `package-lock.json` exception applies); Node version `≥ 20.9.0`; the build exits 0; the post-build manifest staging (§row above) atomically stages `build-manifest.json` (required) and best-effort stages `app-build-manifest.json` (optional, `not_emitted` is **not** a missing-class entry); every required application-route asset class is present with non-zero bytes (CSS + JS both under `_next/static/chunks/**`, no `static/css/` requirement, no `chunks/app/` requirement); `404.html` / `500.html` if present are reported under the separate `error_pages` class (their absence does not fail the application-route contract). On any failure (build, staging of required manifest, missing required application-route class, Node version) the verifier exits non-zero and emits **no** valid `BUILD-INVENTORY.json`. |
| Required Node version | `>= 20.9.0` (Next.js 16 hard requirement); captured from `node --version` at G2 verifier start; mismatch fails fast with non-zero exit **before** the build invocation. |
| Failure semantics | (a) build exit non-zero → verifier exits non-zero, no `BUILD-INVENTORY.json` emitted; (b) **required** `build-manifest.json` staging copy fails or source is missing → verifier exits non-zero, no `BUILD-INVENTORY.json` emitted, partial staging cleared; (b′) optional `app-build-manifest.json` absent (`not_emitted`) → **not** a failure, recorded as `not_emitted` in `assets[]` only when the verifier elects to record it (presence/absence never gates the contract); (c) build exit 0 but missing required application-route asset class (sole `index.html`, non-empty `*.css` under `_next/static/chunks/**`, non-empty `*.js` under `_next/static/chunks/**`) → verifier exits non-zero, no `BUILD-INVENTORY.json` emitted (missing `error_pages` entries are NOT a failure); (d) Node version below `20.9.0` → verifier exits non-zero before build invocation; (e) `<candidate-root>/out/index.html` missing despite build success → verifier classifies as missing-classes failure. **No silent fallback to legacy files is permitted under any branch.** |
| Verification boundary (strict-TDD G2 verifier preconditions) | The later strict-TDD G2 verifier MUST be implemented against this contract: assert each required **application-route** asset class is present with non-zero bytes and stable `sha256` (CSS class = `*.css` under `_next/static/chunks/**`, JS class = `*.js` under `_next/static/chunks/**`; assert **no** requirement on a separate `_next/static/css/` directory or on a `_next/static/chunks/app/` subdirectory); assert `<candidate-root>/out/index.html` is the **only** application-route HTML entry (assert any `404.html` / `500.html` if present are classified under `error_pages`, **not** promoted to `application_route_html`); assert the post-build manifest staging step succeeded before any other asset-class assertion runs — `build-manifest.json` is **required** (absent source or failed copy is a failure) and `app-build-manifest.json` is **optional** (the verifier attempts the copy only when the source manifest exists, records `staged` / `not_emitted`, and never fails on its absence); assert Node version `≥ 20.9.0` from `node --version`; assert the verifier's exit code propagates to `make g2-candidate-build` so no silent fallback to legacy is possible. Mounting under FastAPI's existing `StaticFiles` mount (still on `127.0.0.1:8765`) is **not** part of G2; it is a G3+G6 concern. **Until those assertions are authored and green, G2 is `blocked — contract defined; verifier not implemented`, not `passed`.** |

#### §3.3.3 G3 — consumer readiness

| Field | Value |
| --- | --- |
| Producer | `scripts/verify_consumers.py` (NOT YET AUTHORED — to land in PR3d) |
| Command | `python scripts/verify_consumers.py --manifest openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json --out <build-root>` |
| Artifact | `<build-root>/CONSUMER-READINESS.json` |
| Threshold | for every consumer listed in §3.1, the canonical `cutover-manifest.json` (§3.3.3.1) names `current_path`, `ownership_edge`, `replacement`, `verification`, `activation_status`, `rollback`; **fail-closed**: any `activation_status: unselected` => verifier exits non-zero and emits no valid `CONSUMER-READINESS.json`; no §3.1 consumer remains "active" against a path that PR3e intends to delete |

##### §3.3.3.1 G3 contract definition (canonical input for the strict-TDD G3 verifier)

This subsection is the canonical input for the later strict-TDD G3 verifier (`scripts/verify_consumers.py` + `<build-root>/CONSUMER-READINESS.json`). It defines the canonical machine-readable inventory at `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`, the `CONSUMER-READINESS.json` schema, the atomic / failure semantics, and the test fixture requirements. **G3 is `blocked — contract defined; manifest authored with every §3.1 consumer unselected; verifier not implemented`, not `passed`, until every assertion below is authored and green.**

| Knob | Value |
| --- | --- |
| Canonical manifest path | `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` — single source of truth for every active consumer in `design.md::§3.1`. Authored 2026-08-30 with all 26 consumers enumerated (21 in §3.1.1 FastAPI web mount + 5 in §3.1.2 `web/search_urls.js`); every consumer has `activation_status: unselected` and `replacement.status: unselected`. |
| Manifest top-level shape | JSON object with keys `$schema_version`, `change`, `planning_artifact`, `generated_by`, `scope_intent`, `anchor`, `fail_closed_summary`, `edges[]` (each `{id, label, anchor, single_origin_contract}`), `consumers[]`, `selection_invariants`, `verifier_contract_summary`. The manifest MUST list **every** active consumer from §3.1 (no omission, no collapse); adding a consumer requires amending both `cutover-manifest.json` and `design.md::§3.1` in the same planning pass. |
| Consumer record schema | Each entry in `consumers[]` MUST carry the seven fields `id` (stable string), `ownership_edge` (must equal one of `edges[].id`), `current_path` (the runtime path / test reader path currently active against the chosen ownership edge), `replacement` (`{status: "unselected" | "selected", path?, note?}`), `verification` (`{command, expect}`), `activation_status` (`"unselected" | "selected"`), `rollback` (the exact revert statement that restores `current_path`). The verifier rejects any record missing one of these fields. |
| Stable-ID convention | `id` MUST follow `<edge-prefix>-<kind>-NNN` where `<edge-prefix>` is `mount-` (FastAPI web mount) or `search-urls-` (`web/search_urls.js`), `<kind>` is a short slug (e.g. `runtime-html-root`, `runtime-es-import-static`, `runtime-cdn-pin`, `test-contract-smoke`, `test-contract-ac21`, `extension-manifest-origin-pin`), and `NNN` is a zero-padded 3-digit counter per `(edge, kind)` bucket. IDs are immutable once issued; renaming an ID requires a new planning pass and a migration note in `apply-progress.md`. |
| Atomic cutover unit | PR3e MUST update (1) the `WEB_DIR` constant in `api/server.py:54`, (2) **every** consumer in `cutover-manifest.json` (imports, AC-21 reader path, every test consumer, every CDN pin line), (3) the `make api` / `make web` Makefile targets, and (4) the chosen Approach's build artifact, **in a single release**. Partial activation is rejected by the verifier; the manifest's `atomic_cutover_invariant` encodes this. |
| Rollback unit | `git revert <pr3e-sha>` restores every `current_path` in the manifest simultaneously. Partial revert is rejected under G1 (per `§1` decision record). The manifest's `rollback_invariant` encodes this. |
| Failure semantics (fail-closed) | (a) any consumer with `activation_status: unselected` => verifier exits non-zero, emits no `CONSUMER-READINESS.json`; (b) any consumer with `replacement.status: unselected` => same; (c) any consumer missing a required field => same; (d) any consumer with `verification.command` that exits non-zero against the candidate build => same; (e) Node version below `20.9.0` => same (parity with G2); (f) `CONSUMER-READINESS.json` is written **only** atomically (temp file + rename) and **only** when every precondition above holds. **No silent fallback to legacy files is permitted under any branch.** |
| `CONSUMER-READINESS.json` schema | JSON object emitted by `scripts/verify_consumers.py` at `<build-root>/CONSUMER-READINESS.json`. Required keys: `manifest_path` (string), `manifest_sha256` (string, stable hash of the canonical manifest), `node_version` (string, ≥ `"20.9.0"`), `verified_at` (ISO-8601 string), `exit_code` (int, MUST be `0` for a valid artifact), `consumers[]` (one entry per manifest consumer with `{id, current_path, replacement_path?, verification_exit_code, activation_status, status: "ready" | "not_ready"}`), `unselected_count` (int), `failed_verifications[]` (list of `{id, command, exit_code, stderr_tail}`), `activation_complete` (bool, MUST be `true` for a valid artifact). The artifact is **invalid** when `activation_complete` is `false` OR `exit_code != 0` OR `unselected_count > 0` OR any `failed_verifications[]` entry exists. The verifier writes it via temp-file + rename and removes any partial file on failure. |
| Test fixture requirements | (i) the canonical `cutover-manifest.json` itself (committed in this change; serves as the red/green fixture for the verifier's schema parser); (ii) a transient `tmp_path/<fixture-manifest>.json` per test, parametrized over (a) one consumer with `activation_status: unselected` (expects non-zero exit, no artifact), (b) one consumer with `replacement.status: unselected` (expects non-zero exit, no artifact), (c) one consumer missing a required field (expects non-zero exit, no artifact), (d) one consumer whose `verification.command` returns non-zero (expects non-zero exit, no artifact), (e) every consumer `activation_status: selected` with `verification.command` returning `0` (expects zero exit, valid artifact with `activation_complete: true`); (iii) a SHA256-stability fixture that asserts the manifest's `manifest_sha256` matches across two consecutive verifier runs against the same on-disk manifest; (iv) a fail-closed invariant fixture that asserts the verifier NEVER writes `CONSUMER-READINESS.json` when it exits non-zero. |
| Selection rule (gating) | To flip a consumer's `activation_status` from `unselected` to `selected`, the manifest MUST name `replacement.path` + `verification.command` + `verification.expect` for the new path AND failing-test evidence for the new path MUST exist AND G2 (`BUILD-INVENTORY.json` reproducible) + G4 (Playwright + Lighthouse parity) + G5 (reproducible hydration baseline) + G6 (`cutover-rehearsal.json` dry-run success) MUST all be `passed`. Static export (Approach A) and any other Approach (B / C) remain unselected until those gates close; no consumer is flipped in this planning pass. |
| Provenance (this planning pass) | Manifest authored 2026-08-30 from `design.md::§3.1` (active-consumer inventory) verbatim; every consumer ID was issued from a fresh `mount-` or `search-urls-` namespace; no consumer was collapsed or merged. The Spanish mirror `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md::§3.3.3.1` carries the faithful Spanish translation. |

#### §3.3.4 G4 — behavior parity

| Field | Value |
| --- | --- |
| Producer | Playwright + Lighthouse suite (NOT YET AUTHORED — to land in PR3d); existing `tests/test_smoke.py` (unchanged) |
| Command | `make test && make parity` (proposed) |
| Artifact | `parity-reports/<date>/{navigation,api,search,a11y,browser-state}.json` |
| Threshold | navigation paths match legacy; `/api/*` matches legacy (existing tests green); AC-21 still passes against the post-cut reader location; accessibility ≥ legacy score; browser-state keys (`last-taxon-id`, `tree-source`, `selected-realm`, `version-banner-dismissed`) hydrate the replacement UI identically |

#### §3.3.5 G5 — performance comparability

| Field | Value |
| --- | --- |
| Producer | `scripts/measure_hydration.py` (PR 1b.3a deliverable — **reconstruction pending**, not delivered to `develop`) + Lighthouse |
| Command | `python scripts/measure_hydration.py --baseline docs/baselines/legacy-web-2026-08-26.json --candidate <build-root> --iterations 10` |
| Artifact | `parity-reports/<date>/hydration.json` |
| Threshold | server-shell first-paint within ±10 % of legacy baseline; interaction latency (key tabs / search dropdown) within ±10 % of legacy baseline; bundle size within declared threshold (TBD; recorded at PR3b) |
| **Disposition (2026-08-30 audit)** | **Unreproducible — not accepted for G5.** Legacy baseline artifact `web/dist/evidence-baseline.json` and observed legacy evidence files capture 2026-08-28 only and lack: (a) capture command line; (b) capture stdout/stderr log; (c) capture environment (Node version, chromium SHA256 pin match, FastAPI version, route hash); (d) iteration count; (e) raw Playwright JSON; (f) raw Lighthouse JSON (perf/a11y/best-practices); (g) candidate-vs-baseline delta row; (h) match to current G5 CLI flags (`--baseline`, `--candidate`, `--iterations`) and current schema (`parity-reports/<date>/hydration.json` field names). Until a reproducible legacy baseline AND a reproducible candidate run are both on disk and the two are joined through the G5 command + schema, G5 remains **`blocked — baseline not reproducible; comparison not attempted`**, never `passed`. |
| **Evidence files reviewed (names only; content not accepted)** | (1) `web/dist/evidence-baseline.json` — legacy 2026-08-28 capture; schema-pinned but capture metadata missing; (2) `tests/test_evidence_baseline.py` — schema + chromium-pin contract tests; not a legacy capture; (3) `tools/static-export-probe/scripts/capture.mjs` — disposable probe capture; not a legacy baseline; (4) `tools/static-export-probe/evidence/*.json` if present — probe artifacts; not a legacy baseline. None of these satisfy the missing-proof inventory below. |
| **Missing-proof inventory** | (i) capture command line; (ii) capture stdout/stderr log; (iii) capture environment (Node version, chromium SHA256 pin match, FastAPI version, FastAPI route hash); (iv) iteration count; (v) raw Playwright JSON; (vi) raw Lighthouse JSON (perf/a11y/best-practices); (vii) candidate-vs-baseline delta row; (viii) match to current G5 CLI flags + schema field names. |
| **Closure path** | (1) re-run the legacy capture under the current G5 CLI (`scripts/measure_hydration.py --baseline <new-baseline.json> --candidate <legacy-server-root> --iterations 10`) so the legacy baseline file carries the missing-proof items; (2) re-run the candidate capture once the G2 verifier (per §3.3.2 above) emits a reproducible `<candidate-root>/out/BUILD-INVENTORY.json`; (3) join the two through the G5 command; (4) only then assert the ±10 % thresholds. **Until closure-path step (1) lands, G5 is unreproducible; until closure-path step (2) lands, candidate side is unreproducible; until closure-path step (3) lands, no comparison exists.** |

#### §3.3.6 G6 — cutover rehearsal

| Field | Value |
| --- | --- |
| Producer | `scripts/rehearse_cutover.py` (NOT YET AUTHORED — to land in PR3d) |
| Command | `python scripts/rehearse_cutover.py --manifest openspec/changes/migrate-nextjs-tailwind4/design.md::§3.4 --dry-run` |
| Artifact | `parity-reports/<date>/cutover-rehearsal.json` |
| Threshold | every path listed in §3.4 is verified by the rehearsal: mount path, served-artifact root, fallback behavior, every consumer-update, AC-21 reader path; dry-run matches the manifest exactly; rollback rehearsal restores the previous mount + canonical consumer graph |

---

`status: complete (PR 2a slice; PR3a boundary scope planning with G2–G6 evidence producer/threshold plan appended — no boundary selected, no gate passing, no cutover manifest yet; G2 contract defined in §3.3.2.1 with **four** explicit maintainer corrections applied against the verified Next.js 16.3.3 / Turbopack build output contract: (1) `size:exception` ONLY for `tools/g2-candidate/package-lock.json`, only after `npm ci` exits 0 against the candidate's local `package.json`, no other generated file excepted; (2) atomic post-build manifest staging from `<candidate-root>/.next/` → `<candidate-root>/out/.next/` — `build-manifest.json` required (its absence is a missing-class failure), `app-build-manifest.json` optional and never a missing-class failure (best-effort copy recorded as `staged` / `not_emitted`); (3) `index.html` sole normal application-route HTML entry, `404.html`/`500.html` explicitly permitted error-page exemptions classified under a separate `error_pages` asset class; (4) **Next 16 / Turbopack output-contract correction** — required **CSS** class = one-or-more non-empty `*.css` under `out/_next/static/chunks/**` (not `out/_next/static/css/`); required **JS** class = one-or-more non-empty `*.js` under `out/_next/static/chunks/**` (no `chunks/app/` subdirectory requirement); G2 PASS recorded 2026-08-30 from clean worktree `taxa-worktrees/migrate-nextjs-g2-evidence-capture` off `develop@a74289b` (build finished `2026-08-30T18:11:02Z`, Node `v26.8.1`, inventory at `taxa-worktrees/migrate-nextjs-g2-evidence-capture/tools/g2-candidate/out/BUILD-INVENTORY.json` with `missing_classes[]` empty, all required application-route classes present, `build-manifest.json` staged at 607 bytes / sha256 `f52f7edd901e373a2a24a4ecf8ba61c96ad227093c6440dc4a3a6ca58a92f2a3`, optional `app-build-manifest.json` `not_emitted`, 14 verifier + 34 candidate focused tests pass, build log captured — multi-lockfile warning non-blocking); G5 legacy baseline dispositioned unreproducible per §3.3.5 2026-08-30 audit; G3–G6 remain blocked, static export unselected, no FastAPI activation; G3 contract defined in §3.3.3.1 with canonical machine-readable manifest at `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` authored 2026-08-30 enumerating all 26 §3.1 consumers (21 §3.1.1 FastAPI web mount + 5 §3.1.2 web/search_urls.js) with stable IDs, `current_path`, `ownership_edge`, `replacement`, `verification`, `activation_status`, `rollback`; every consumer `activation_status: unselected` and `replacement.status: unselected`; **fail-closed**: G3 verifier (scripts/verify_consumers.py, NOT YET AUTHORED) emits no valid CONSUMER-READINESS.json while ANY consumer is unselected; §3.3.3.1 also defines the CONSUMER-READINESS.json schema, atomic / failure semantics, and test fixture requirements; G3 stays `blocked — contract defined; manifest authored with every §3.1 consumer unselected; verifier not implemented`, not `passed`; no boundary selected, no gate passing beyond G2, no FastAPI activation)`
