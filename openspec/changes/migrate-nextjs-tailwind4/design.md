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

**Status: Open / Evidence-gated.**

The decision between Approach A (`next build` static export under
FastAPI), Approach B (full Next.js dev server on a second port), and
Approach C (phased hybrid) is **not** finalised in this PR 2a slice.
Per `specs/modular-architecture/spec.md` rule 7:

> the chosen approach is recorded in `design.md::§1 Decision`
> THEN the entry cites this spec by path as the architectural
> authority
> AND if design sees a conflict with any rule here, it is raised back
> to the proposal before implementation

This entry **cites `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md` as the architectural authority**
for the modular-monolith constraints (rules 1–5) and confirms that
**no conflict** between the §1 candidates and any spec rule has been
identified at this point. Rules 1, 2, 3, 5 are framework-neutral and
constrain all three approaches equally; rule 4 (domain stays free of
framework / I/O) constrains all three approaches equally; rule 6
explicitly requires every approach to honour rules 1–5; rule 7 is
this very entry.

### Evidence required to close §1

The §1 Decision will be updated once **all** of the following
evidence is on disk:

1. `web/dist/build-profile.json` from PR 1a.1 + PR 1a.2
   (`scripts/emit_build_profile.mjs` + the schema test). The
   `total_bytes` and `per_route_bytes` numbers are the §1 input.
2. Playwright + Lighthouse delta vs the legacy baseline on the
   chromium fixture from PR 1b.1 (`scripts/verify_chromium.py`) +
   PR 1b.2 (`tests/test_evidence_baseline.py`).
3. Hydration-cost measurement from PR 1b.3a +
   `tests/test_hydration_timing.py` (PR 1b.3b): the
   `delta_server_to_tree_first_paint_ms` and `console_warnings`
   numbers are the §1 input.

### Default fail-safe (if evidence supports it)

If the three measurements above show that the `next build` static
export (Approach A) achieves ≤ 0 % regression on the perf budget and
satisfies every rule in `specs/modular-architecture/spec.md`, then
**Approach A is the default §1 decision** because it preserves the
single-port contract (proposal §In Scope) and has the smallest blast
radius. Any other outcome must escalate back to the proposal before
any code lands.

### Why §1 is open in PR 2a

PR 2a only adds the modular-monolith **layout**; it does not run
`next build`, does not emit `web/dist/build-profile.json`, does not
measure hydration timing, and does not change FastAPI's
`app.mount("/", StaticFiles(...))` call site. The decision is
deliberately deferred to PR 3, which is the first slice where the
Next.js tooling is on disk and `next build` can run. PR 2a leaves
§1 in the **Open / Evidence-gated** state recorded here so the
spec rule 7 reference target exists from the day PR 2a lands, even
though the decision content arrives later.

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

- [ ] **§1 evidence**: see §1 above. Closed when the three
      measurements (build profile, Playwright + Lighthouse delta,
      hydration timing) are produced by PR 1 sub-PRs and the chosen
      Approach is recorded here as `## §1 Decision: <A | B | C>`
      with a cite back to
      `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
      per rule 7.
- [ ] **Hydration cost on `taxonomy/tree`**: RED test in
      `tests/test_hydration_timing.py` (no console `hydration`
      warnings under Playwright). Closes when PR 5 task 5.8 lands
      and the delta is `≤ 0 %`.
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

#### §3.3.3 G3 — consumer readiness

| Field | Value |
| --- | --- |
| Producer | `scripts/verify_consumers.py` (NOT YET AUTHORED — to land in PR3d) |
| Command | `python scripts/verify_consumers.py --map openspec/changes/migrate-nextjs-tailwind4/design.md::§3.1 --cut-manifest design.md::§3.4` |
| Artifact | `<build-root>/CONSUMER-READINESS.json` |
| Threshold | for every consumer listed in §3.1, the §3.4 manifest names the replacement path and a verification path; no §3.1 consumer remains "active" against a path that PR3e intends to delete |

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

#### §3.3.6 G6 — cutover rehearsal

| Field | Value |
| --- | --- |
| Producer | `scripts/rehearse_cutover.py` (NOT YET AUTHORED — to land in PR3d) |
| Command | `python scripts/rehearse_cutover.py --manifest openspec/changes/migrate-nextjs-tailwind4/design.md::§3.4 --dry-run` |
| Artifact | `parity-reports/<date>/cutover-rehearsal.json` |
| Threshold | every path listed in §3.4 is verified by the rehearsal: mount path, served-artifact root, fallback behavior, every consumer-update, AC-21 reader path; dry-run matches the manifest exactly; rollback rehearsal restores the previous mount + canonical consumer graph |

---

`status: complete (PR 2a slice; PR3a boundary scope planning with G2–G6 evidence producer/threshold plan appended — no boundary selected, no gate passing, no cutover manifest yet)`
