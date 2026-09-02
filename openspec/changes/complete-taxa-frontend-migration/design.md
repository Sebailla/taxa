# Design: complete-taxa-frontend-migration

> Successor to `migrate-nextjs-tailwind4` (frozen as planning history
> under `openspec/changes/migrate-nextjs-tailwind4/**`). This design
> records the **final** architecture for the React cutover and the
> planned closure of G4 / G5 / G6. Spec phase already locked Approach A
> on **2026-09-02**; this design is the architectural reference for the
> apply phase.

## TL;DR

| Question | Answer |
| --- | --- |
| Approach | **A — FINAL.** `next build` → `out/` served by FastAPI's `StaticFiles` mount at `127.0.0.1:8765`. |
| Origin | FastAPI sole origin; **no** second dev-server port. |
| Cutover unit | **Atomic.** `WEB_DIR` + 26 §3.1 consumers + `Makefile::api` + `out/` change in one release. No subset revert. |
| Rollback unit | **`git revert <cutover-sha>`**. Restores legacy vanilla build atomically. No DB migration required. |
| Evidence gates | **G1, G2, G3 Tier-1 PASS** (carried from predecessor). **G4, G5, G6** close in apply phase; this design plans their closure. |
| Predecessor | **Frozen.** `openspec/changes/migrate-nextjs-tailwind4/**` is byte-identical before and after the apply phase. |

---

## §1 Approach Decision — FINAL

**Approach A is the chosen architecture.** Recorded on **2026-09-02**
(user-locked). Approach B (full Next.js dev server on a second port)
and Approach C (phased hybrid) are rejected. The architectural
authority is `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
rule 7 (cite-back requirement).

| Invariant | Implementation under A | Source |
| --- | --- | --- |
| Sole origin | `127.0.0.1:8765`; FastAPI binds via `uvicorn.run(app, host="127.0.0.1", port=8765, …)` | `api/server.py` end-of-file |
| Sole HTML owner | FastAPI's `app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")` serves `out/index.html` and the SPA fallback | `api/server.py:1815` |
| Sole static-asset owner | Same `StaticFiles` mount serves `out/_next/static/**` | `api/server.py:1815` |
| `WEB_DIR` | `WEB_DIR = Path(__file__).parent.parent / "out"` (was `…/"web"`) | `api/server.py:54` |
| Extension `host_permissions` | `["http://localhost:8765/*"]` — **unchanged** | `extension/manifest.json:13–15` |
| Extension `content_scripts.matches` | `["http://localhost:8765/*"]` — **unchanged** | `extension/manifest.json:21` |
| `/api/*` shapes | Byte-identical to current FastAPI | Functional equivalence rule |
| Build artifact | `out/` produced by `next build`; G2 contract verified clean (Next 16.3.3 / Turbopack) | Predecessor `design.md::§3.3.2.1` |

### Why A (and not B or C)

A honours G1 (single origin) trivially; B breaks G1 by opening a second
port; C preserves G1 via phased rollout but adds review surface and a
two-window dual-build state that the spec explicitly rejects. The
single-edit change to `WEB_DIR` is the minimum-blast-radius path; the
mount signature stays byte-identical; the uvicorn bind stays
byte-identical; no extension manifest change.

### What A forfeits (acceptable)

- Dynamic routes / image optimization (acceptable for v1; switching to
  the full Next.js dev server is a separate change if needed).
- Server-side route handlers / server components (none required; the
  Taxa UI is a single-screen client app).

---

## Module boundaries

The modular monolith (5 modules × 4 layers) was established by
predecessor PR 2a (origin/develop #78). This change **does not
re-scaffold** the layout; it populates the layers that predecessor
PRs 3 / 4 / 5 left as `.gitkeep` placeholders. The modular-architecture
spec (rules 1–7) applies unchanged; the predecessor spec is frozen.

### Module ownership under A

| Module | Domain | Application | Infrastructure | Presentation |
| --- | --- | --- | --- | --- |
| `taxonomy` | `Taxon` types + invariants | `useTaxonTree()`, `useTaxonDetail()`, parent-chain walker | `fetchTaxon`, `fetchChildren`, `fetchDomains` | `Tree`, `DetailPanel`, `Breadcrumb`, `DomainList` |
| `research` | `ResearchFile`, `Engine`, `FileNode` types | `useFileExplorer()`, `useFileViewer()`, format dispatcher | `fetchFiles`, `fetchServe`, `loadScriptOnce` (CDN lazy loader), `search-engines.js` | `FileExplorer`, `FileViewer`, `RawTableTreeTabs`, `MetaStrip`, `BreadcrumbPanel`, `Banners` |
| `design-system` | Theme tokens (typed) | — | `globals.css` (`@theme` block + `@layer base`), `next/font` wire-up | `<Icon>`, `<Button>`, layout primitives |
| `browser-state` | `LocalStorageKey` types, typed defaults, subscriber type | — | `store.ts` (4 keys × {read, write}), `useSyncExternalStore` adapter | — |
| `app-shell` | — | `AppShell` host composition, route shell state | `src/app/page.tsx`, `src/app/layout.tsx`, `next.config.mjs` | `AppShell`, `<Header>`, `<Tabs>`, `<HelpShell>`, `<SettingsView>`, `<BannerHost>` |

### Cross-module import contract (binding)

- Public barrel (`src/modules/<capability>/index.ts`) is the only legal
  cross-module access point. Predecessor PR 2b + 2c shipped the ESLint
  `no-restricted-imports` patterns + 40-fixture triangulation on
  `origin/develop` (PR #80 + #82).
- `domain` layer compiles without React, Next, FastAPI, or any I/O
  subsystem (predecessor PR 2e domain-purity guard ships on
  `origin/develop`).
- `browser-state::domain` is plain TS types; `browser-state::infrastructure`
  owns the `localStorage` calls.

### Files NOT in scope of this change's module edits

- `api/server.py` route handlers (backend rewrite is out of scope).
- `etl/**` (ETL pipeline out of scope).
- `extension/**` (Chrome extension parity is a separate change).
- `tests/test_module_layers.py` (predecessor PR 2a ships; this change
  does not edit it).

---

## Static build / start lifecycle

### Build pipeline (executed by `Makefile::api`)

```
make api
  ├── scripts/check-runtime.mjs      # Node ≥ 20.9.0; exits non-zero otherwise
  ├── npm run build:web               # next build → out/
  │     ├── out/index.html
  │     ├── out/_next/static/chunks/*.js
  │     ├── out/_next/static/chunks/*.css
  │     ├── out/_next/static/media/*  (next/font)
  │     └── out/.next/build-manifest.json  (staged atomically by Next 16)
  └── uvicorn api.server:app          # binds 127.0.0.1:8765
```

| Knob | Value | Authority |
| --- | --- | --- |
| `package.json::engines.node` | `">=20.9.0"` (Next 16 hard requirement) | Predecessor `design.md::§3.3.2.1` |
| `next.config.mjs::output` | `"export"` | Predecessor `design.md::§3.3.2.1` |
| `next.config.mjs::images.unoptimized` | `true` (static export requirement) | Predecessor `design.md::§3.3.2.1` |
| `next.config.mjs::trailingSlash` | `false` | Predecessor `design.md::§3.3.2.1` |
| Runtime check script | `scripts/check-runtime.mjs` | Predecessor task 3.4 |
| Makefile target | `make api` runs `npm install && npm run build:web && uvicorn …` | Predecessor task 3.4 |

### Start contract (failure semantics)

| Condition | Behavior | Source |
| --- | --- | --- |
| Node `< 20.9.0` | `scripts/check-runtime.mjs` exits non-zero; `make api` exits non-zero **before** uvicorn binds | Predecessor `design.md::§3.3.2.1` |
| `next build` exits non-zero | `make api` exits non-zero **before** uvicorn binds; legacy `web/` is **not** a fallback | Predecessor `design.md::§3.3.2.1` |
| Missing `out/index.html` | `make api` exits non-zero; uvicorn does not bind | Predecessor `design.md::§3.3.2.1` |
| Empty `out/_next/static/chunks/` | Build emitted nothing useful; uvicorn does not bind | Predecessor `design.md::§3.3.2.1` |

There is **no** silent fallback to legacy files. The legacy vanilla
build is reachable only via an explicit `git revert <cutover-sha>`,
never via a quiet degraded mode.

### Mount contract (`api/server.py:1815` — unchanged signature)

```python
# The mount signature stays byte-identical to the legacy build.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

Only the **`WEB_DIR` constant declaration** at `api/server.py:54` is
repointed (one-line change). No middleware, no second mount, no SPA
fallback mechanism is introduced — FastAPI's `StaticFiles` `html=True`
is the only fallback for direct navigation to deep paths
(`/taxon/123`, `/help`, `/settings`); the client-side router inside
the SPA decides the final route.

---

## Atomic cutover unit

The cutover unit (PR3e-equivalent, re-sliced under A) changes
**exactly the following** in a single release:

1. **`WEB_DIR` constant** in `api/server.py:54` (repoint at `out/`).
2. **Every active-consumer update** enumerated in the predecessor's
   `design.md::§3.1` (imports, the AC-21 reader path, every test
   consumer). The 21 web-mount consumers and the 5
   `web/search_urls.js` consumers are named verbatim in the
   predecessor's `cutover-manifest.json`.
3. **The `Makefile::api` and `Makefile::web` targets** — the
   `api` target runs `next build` before uvicorn; the legacy
   `make css` Tailwind-3.4 step is retired.
4. **The build artifact** — the `out/` directory itself
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, the error-page classification if
   `404.html` / `500.html` is emitted).

**No subset revert is supported.** Partial reverts leave consumers
referencing deleted paths and break the SPA shell or the AC-21
contract test.

### Cutover-manifest activation (during apply)

`openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` flips
`activation_status` and `replacement.status` from `selected` (legacy
pre-cut, Tier-1) to the **post-cut activation record** (Tier-2) for
every one of the 26 §3.1 consumers. The flip is a planning artifact
authored by the apply worker in the same release as the code; the
G3 Tier-2 verifier (already authored, PR #109 + #111) re-runs against
the atomic-cut selection and emits a fresh `CONSUMER-READINESS.json`.

### Pre-flight gate (the cutover cannot ship until all green)

- [ ] **G1 PASS** — recorded (predecessor `design.md::§1`).
- [ ] **G2 PASS** — recorded against the verified Next 16.3.3 /
      Turbopack clean build (predecessor `apply-progress.md`
      2026-08-30 entry).
- [ ] **G3 Tier-1 PASS** — recorded: all 26 §3.1 consumers green
      against the legacy pre-cut runtime via the controlled fixture
      and `scripts/verify_consumers.py` (PR #109 + #111 + #115 + #116).
- [ ] **G4 PASS** — Playwright + Lighthouse parity harness closes
      in apply phase (planned §G4 closure below).
- [ ] **G5 reproducible** — legacy baseline reconstructed or
      replaced in apply phase (planned §G5 closure below).
- [ ] **G6 PASS** — `scripts/rehearse_cutover.py` exits 0 against
      the activated manifest (planned §G6 closure below).

Absent, failed, stale (> 7 days), or incomparable evidence is
**blocked**, never success.

---

## Rollback unit

The rollback unit is **`git revert <cutover-sha>`**. It restores
**all four sets** together:

- `web/index.html`, `web/app.js`, the 18 `web/*.js` modules,
  `web/dist/tailwind.css`, `tailwind.config.js`.
- The legacy `package.json` + `package-lock.json`; `npm ci`
  reproduces the lock.
- `api/server.py:54` reverts to
  `WEB_DIR = Path(__file__).parent.parent / "web"`.
- The `Makefile::api` reverts to invoking `make css` before
  uvicorn.

### After-revert state

| Check | Expectation |
| --- | --- |
| `make api` | Regenerates `web/dist/tailwind.css` from reverted `tailwind.config.js` |
| `make smoke` | 63 passed, 8 skipped (pre-migration baseline) |
| `make test` | All backend tests green |
| `curl http://127.0.0.1:8765/index.html` | Returns the vanilla shell |
| `extension/manifest.json` | Unchanged through the cutover and the rollback |
| `data/db/taxa.db` | Unchanged (no DB schema ships in this change) |
| `openspec/changes/migrate-nextjs-tailwind4/**` | Byte-identical (predecessor frozen) |

No data migration is required to roll back. No AC-21 regression
path is left open. No extension manifest update is required.

---

## Parity / evidence plan

### Carried evidence (imported, not re-derived)

| Gate | Status | Source |
| --- | --- | --- |
| G1 (single origin) | **PASS recorded** | Predecessor `design.md::§1` |
| G2 (foundation build) | **PASS recorded** against Next 16.3.3 / Turbopack clean build | Predecessor `apply-progress.md` (2026-08-30 evidence capture) |
| G3 Tier-1 (consumer readiness, legacy pre-cut) | **PASS recorded** — all 26 §3.1 consumers green via the controlled fixture, `scripts/verify_consumers.py` | Predecessor `apply-progress.md` (PR #109 + #111 + #115 + #116) |
| G3 Tier-2 (atomic-cut selection) | **NOT PASSED** — requires G4 + G5 + G6 closure | This change's apply phase |
| G4 (Playwright + Lighthouse parity) | **blocked — verifier not authored** | This change's apply phase (planned below) |
| G5 (hydration baseline) | **unreproducible — legacy baseline not on disk** | This change's apply phase (planned below) |
| G6 (cutover rehearsal) | **blocked — verifier not authored** | This change's apply phase (planned below) |

### Carried planning artifacts (frozen inputs)

- `openspec/changes/migrate-nextjs-tailwind4/proposal.md`
- `openspec/changes/migrate-nextjs-tailwind4/design.md` (incl.
  `§1` boundary decision, `§3.1` active-consumer inventory,
  `§3.3.2.1` G2 contract, `§3.3.3` / `§3.3.3.1` G3 contract,
  `§3.3.5` G5 disposition)
- `openspec/changes/migrate-nextjs-tailwind4/apply-progress.md`
  (incl. the change log recording G2 PASS, G3 Tier-1 PASS,
  G5 unreproducible)
- `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
- `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
- `openspec/specs/research/spec.md` (canonical; preserved unchanged)

### Parity checklist (apply phase must satisfy every row)

- [ ] **Functional parity** — every user flow (browse, search,
      materialize, preview, open folder, save URL, view files across
      all supported formats) behaves identically to the legacy build.
- [ ] **Performance** — ≤ 0 % regression in initial paint or
      interaction latency on the chromium fixture the predecessor
      captured.
- [ ] **Single local origin** — `make api` binds only 8765; no second
      dev-server port; extension `host_permissions` unchanged.
- [ ] **Backend pytest** — 63 passed, 8 skipped baseline preserved.
- [ ] **Playwright suite** — updated DOM selectors; `data-*` attribute
      contract preserved; still green.
- [ ] **AC-21 contract** — `tests/test_smoke.py::test_search_engine_contract`
      passes; literal may move under `src/data/search-engines.js`;
      byte shape unchanged.
- [ ] **Browser-local state** — `theme`, `tree-source`, `last-taxon-id`,
      `kebab-open-id` each have one read + one write site inside
      `src/modules/browser-state/`; no hydration warning.
- [ ] **Tailwind 4 parity** — every `:root` token resolves; every
      `var(--token)` reference resolves; every utility class resolves.
- [ ] **Accessibility** — every ARIA role, label, keyboard handler
      preserved; axe scan no new serious/critical violations.
- [ ] **Predecessor frozen** — `openspec/changes/migrate-nextjs-tailwind4/**`
      byte-identical before and after apply.
- [ ] **Rollback** — `git revert` restores legacy with green smoke
      + Playwright.

---

## Test seams

The test surface is layered so the apply worker can drive RED → GREEN
→ TRIANGULATE without re-deriving evidence the predecessor already
produced.

### Preserved (predecessor delivers; this change does not edit)

| Test | Owner | Purpose |
| --- | --- | --- |
| `tests/test_module_layers.py` | Predecessor PR 2a (#78) | 40 layout assertions; pins `CAPABILITIES`, `LAYERS`, `BARREL_NAME` |
| `tests/test_no_restricted_imports.py` | Predecessor PR 2b + 2c (#80, #82) | 102 barrel-only import assertions + 40-fixture triangulation |
| `tests/test_taxonomy_domain.py` | Predecessor PR 2d (#84) | Domain types + invariants compile without framework |
| `tests/test_domain_purity.py` | Predecessor PR 2e (#86) | Framework-token grep guard over the domain layer |
| `tests/test_verify_consumers.py` | Predecessor PR #109 + #111 + #115 + #116 | G3 verifier triangulation; controlled runtime / fixture-serve / HTTP-shape / symlink-preservation |
| `tests/test_g3_legacy_fixture.py` | Predecessor PR #113 + #114 + #115 + #116 | Fixture DB + served-fixture asset coverage |
| `tests/test_verify_build.py` | Predecessor G2 evidence | 14 G2 contract assertions |
| `tests/test_g2_candidate.py` | Predecessor G2 evidence | 34 G2 candidate build assertions |
| `tests/test_smoke.py` | Repo baseline | 63 passed, 8 skipped (AC-21 contract preserved) |
| `tests/test_search_categories.py` | Repo baseline | `CATEGORIES` grouping test (general / taxonomic / academic / multimedia / documents) |
| `tests/test_evidence_baseline.py` | Predecessor PR 1b.1 + 1b.2 | Chromium pin + legacy evidence baseline |
| `tests/test_build_profile.py` | Predecessor PR 1a.1 + 1a.2 | Build-profile emitter + schema |
| `tests/test_hydration_timing.py` | Predecessor PR 1b.3a + 1b.3b | Hydration measurement + schema |

### New (this change ships)

| Test | Slice | Purpose |
| --- | --- | --- |
| `tests/test_tailwind_4_parity.py` | Bootstrap | Every legacy `:root` token + `var(--name)` reference resolves to non-empty declaration |
| `tests/test_make_api_build.py` | Bootstrap | `Makefile::api` runs Next build before uvicorn; fails fast on Node < 20.9.0 |
| `tests/test_static_mount.py` | Bootstrap | `GET /` returns Next HTML; `GET /_next/static/<h>.js` returns 200; no second listener on 8765 |
| `tests/test_browser_state_keys.py` | Browser-state | Greps `src/`; asserts exactly 4 `localStorage.getItem` + 4 `localStorage.setItem` call sites |
| `tests/test_hydration_console.py` | Browser-state | Playwright: zero React hydration warnings after first paint + rehydration cycle |
| `tests/test_taxonomy_infra.py` | Capability ports | Mocks `fetchTaxon` / `fetchChildren`; shape asserts |
| `tests/test_research_infra.py` | Capability ports | Mocks `/api/taxon/{id}/files{,/serve}`; shape asserts |
| `tests/test_e2e_file_explorer.py` | Capability ports | Playwright; DOM selectors updated; `data-*` contract preserved |
| `tests/test_web_toggle.py` | Capability ports | Playwright; theme toggle persists via typed store; `data-theme` stamp |

### Backstop gates (apply phase closes)

| Gate | Verifier | Artifact | Threshold |
| --- | --- | --- | --- |
| G4 (Playwright + Lighthouse parity) | Authored in apply | `tests/test_e2e_file_explorer.py` + Playwright trace + Lighthouse JSON | Δ ≤ 0 % on initial paint + interaction latency vs. legacy chromium fixture |
| G5 (hydration baseline) | `scripts/measure_hydration.py` (already authored) re-run against reconstructed baseline | hydration baseline JSON | Δ ≤ 0 % vs. reconstructed legacy baseline |
| G6 (cutover rehearsal) | `scripts/rehearse_cutover.py` (to be authored) | `cutover-rehearsal.json` | Exits 0; no silent fallback paths; atomic cutover unit + rollback unit consistent |

---

## Planned G4 / G5 / G6 closure

The apply phase owns the three blockers. The design plans the closure;
the implementation happens during apply.

### G4 — Playwright + Lighthouse parity harness

| Step | Owner | Output |
| --- | --- | --- |
| Update `tests/test_e2e_file_explorer.py` selectors for the React component tree (`data-*` attributes preserved per canonical research spec) | Apply | `tests/test_e2e_file_explorer.py` |
| Update `tests/test_web_toggle.py` selectors; assert theme toggle persists via `localStorage.taxa.settings.theme` and stamps `data-theme` on `<html>` | Apply | `tests/test_web_toggle.py` |
| Re-run the predecessor chromium fixture against the new build; capture initial paint + interaction latency under Playwright + Lighthouse | Apply | Playwright trace + Lighthouse JSON |
| Compare against the predecessor's `web/dist/evidence-baseline.json` | Apply | Δ report |
| Δ ≤ 0 % on initial paint + interaction latency without documented exemption → **G4 PASS** | Apply | Status flip |

### G5 — hydration baseline

| Step | Owner | Output |
| --- | --- | --- |
| Audit `web/dist/evidence-baseline.json` to confirm whether the legacy baseline is on disk (predecessor §3.3.5 audit lists it as **unreproducible**) | Apply | Audit report |
| If reproducible: capture the legacy baseline via `scripts/measure_hydration.py` against the legacy chromium fixture | Apply | legacy hydration JSON |
| If unreproducible: reconstruct from `web/index.html` first-paint + the legacy `delta_server_to_tree_first_paint_ms` documented in `design.md::§"Migration Evidence Baseline"` | Apply | reconstructed baseline JSON |
| Re-run `scripts/measure_hydration.py` against the new build | Apply | new hydration JSON |
| Δ ≤ 0 % vs. reconstructed baseline → **G5 reproducible** | Apply | Status flip |

### G6 — cutover rehearsal

| Step | Owner | Output |
| --- | --- | --- |
| Author `scripts/rehearse_cutover.py` that dry-runs the atomic cutover unit: WEB_DIR repoint + 26 consumer updates + Makefile rewrite + out/ build artifact, then runs the G3 verifier (PR #109 + #111) against the activated manifest | Apply | `scripts/rehearse_cutover.py` |
| Author `tests/test_rehearse_cutover.py` (parametrized over the 4 cutover-unit subsets, asserting the fail-closed invariant) | Apply | `tests/test_rehearse_cutover.py` |
| Run the rehearsal end-to-end; capture `cutover-rehearsal.json` | Apply | `cutover-rehearsal.json` |
| Rehearsal exits 0; no silent fallback paths; atomic cutover + rollback units consistent → **G6 PASS** | Apply | Status flip |

### Cutover activation sequence (when all six gates green)

1. Author the **post-cut activation record** in the predecessor's
   `cutover-manifest.json` (flip `activation_status` + `replacement.status`
   to Tier-2 for all 26 §3.1 consumers).
2. Apply the **atomic cutover unit** — the four-set change in one
   release (see §"Atomic cutover unit" above).
3. Run the G3 Tier-2 verifier against the activated selection;
   `CONSUMER-READINESS.json` exits 0 with `activation_complete = true`,
   `unselected_count = 0`.
4. Run `make smoke` + Playwright + Lighthouse; verify the parity
   checklist.
5. Mark the cutover PR ready for review.

---

## Sub-PR slice under Approach A

The predecessor's `tasks.md` enumerates 35 tasks across 14+ sub-PRs.
This change re-slices them under Approach A within the 400-line
review budget per sub-PR. The full per-task file lists live in
`tasks.md`; the table below is the executive view.

| Sub-PR | Predecessor task | Scope | New / preserved | LoC budget |
| --- | --- | --- | --- | --- |
| PR 3a | task 3.1 | `src/app/{layout,page}.tsx` + `next.config.mjs` + TS / Next plugin config in `tsconfig.json` | New | ≤ 400 |
| PR 3b | task 3.2 | `src/modules/design-system/infrastructure/globals.css` (`@import "tailwindcss"` + `@theme` + `@layer base`) | New | ≤ 400 |
| PR 3c | task 3.4 | `Makefile::api` rewrite + `scripts/check-runtime.mjs` + `package.json` rewrite (deps + `engines.node`) | New | ≤ 400 |
| PR 3d | task 3.6 + 3.7 | `api/server.py:54` WEB_DIR repoint + `web/search_urls.js` → `src/data/search-engines.js` + AC-21 `open()` update | New | ≤ 400 |
| PR 4a | task 4.1 + 4.2 | `src/modules/browser-state/{store,keys,defaults}.ts` + 4 read + 4 write sites inside `useEffect` | New | ≤ 400 |
| PR 4b | task 4.3 + 4.4 | `useSyncExternalStore` behind `mounted` flag + Playwright zero-hydration-warnings assertion | New | ≤ 400 |
| PR 5a | task 5.1 + 5.2 + 5.3 | `src/modules/taxonomy/{domain,application,infrastructure,presentation}` + port `web/{tree,detail,breadcrumb}.js` | New | ≤ 400 |
| PR 5b | task 5.4 + 5.5 + 5.6 | `src/modules/research/{domain,application,infrastructure,presentation}` + port `web/{file_explorer,file_viewer,format,keymap}.js` + CDN pin | New | ≤ 400 |
| PR 5c | task 5.7 + 5.8 + 5.9 | Playwright + e2e selector updates + `data-*` contract preservation + delete `web/*.{html,js,css}` + `tailwind.config.js` | New | ≤ 400 |
| PR 3e (cutover) | atomic cutover unit | The four-set release + cutover-manifest Tier-2 flip + G3 Tier-2 verifier rerun + status-footer flips for G4 / G5 / G6 closure | Atomic | ≤ 400 |

The PR 3e cutover sub-PR ships **only when** all six gates are green;
the apply worker is gated on the G4 / G5 / G6 closure sub-PRs (3e
itself lands after the closure verifications).

---

## Affected files (executive view)

| Area | Action | Files |
| --- | --- | --- |
| `web/index.html` | Deleted at activation (PR 5c) | `web/index.html` |
| `web/*.js` (18 modules) | Deleted at activation (PR 5c) | `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` |
| `web/index.css` | Deleted at activation (PR 5c) | `web/index.css` |
| `web/dist/tailwind.css` | Regenerated by reverted `make css` after rollback; not part of new build | `web/dist/tailwind.css` |
| `tailwind.config.js` | Deleted at activation (PR 5c) | `tailwind.config.js` |
| `src/app/{layout,page}.tsx` | Created (PR 3a) | new |
| `src/modules/**` | Populated (PR 3b + 4a/4b + 5a/5b) | new |
| `src/data/search-engines.js` | Created (PR 3d) — replaces `web/search_urls.js` | new |
| `src/app/globals.css` | Created (PR 3b) — Tailwind 4 `@theme` + `@layer base` | new |
| `package.json` | Modified (PR 3c) — `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, TS toolchain, `engines.node ">=20.9.0"`; removes `autoprefixer`, `postcss`, `@tailwindcss/forms` | `package.json` |
| `api/server.py` | Modified (PR 3d) — `WEB_DIR` repoint at line 54 only; mount signature unchanged | `api/server.py` |
| `Makefile` | Modified (PR 3c) — `api` target runs `npm run build:web` before uvicorn; legacy `make css` retired | `Makefile` |
| `tests/test_tailwind_4_parity.py` | Created (PR 3b) | new |
| `tests/test_make_api_build.py` | Created (PR 3c) | new |
| `tests/test_static_mount.py` | Created (PR 3d) | new |
| `tests/test_browser_state_keys.py` | Created (PR 4a) | new |
| `tests/test_hydration_console.py` | Created (PR 4b) | new |
| `tests/test_taxonomy_infra.py` | Created (PR 5a) | new |
| `tests/test_research_infra.py` | Created (PR 5b) | new |
| `tests/test_e2e_file_explorer.py` | Modified (PR 5c) — DOM selectors updated; `data-*` contract preserved | `tests/test_e2e_file_explorer.py` |
| `tests/test_web_toggle.py` | Modified (PR 5c) — theme toggle persists via typed store | `tests/test_web_toggle.py` |
| `tests/test_smoke.py::test_search_engine_contract` | Modified (PR 3d) — `open()` path updated if literal moved; byte shape preserved | `tests/test_smoke.py` |
| `scripts/check-runtime.mjs` | Created (PR 3c) — Node ≥ 20.9.0 enforcement | new |
| `scripts/rehearse_cutover.py` | Created (PR 3e) — G6 dry-run | new |
| `tests/test_rehearse_cutover.py` | Created (PR 3e) — parametrized fail-closed invariant | new |
| `extension/manifest.json` | **Unchanged** | `extension/manifest.json` |
| `openspec/changes/migrate-nextjs-tailwind4/**` | **Unchanged (frozen)** | (frozen) |
| `documents-es/openspec/changes/complete-taxa-frontend-migration/**` | Spanish mirror (this change) | `documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md` |

---

## Out of scope (binding, preserved from spec)

- Backend rewrite: `api/server.py` route handlers, SQLite/WAL logic,
  materialize flow, SSRF defence in `save-url`.
- ETL pipeline: `etl/parse_textree`, `etl/load_coldp`,
  `etl/load_worms`, `etl/load_freshwater`, migrations.
- Chrome extension parity work — a separate change tracks any
  React-aware extension adaptation.
- SEO / metadata / sitemap / robots work.
- New routes (Settings, About, Help) beyond what the legacy UI
  exposes today.
- Coverage tooling (`coverage.available: false` is the current state).
- Visual redesign (impeccable / Stitch follow-up, not a blocker).
- Editing or "completing" the predecessor's change directory. The
  predecessor is **frozen**, not finalized.
- Re-running the predecessor's G2 / G3 / G4 / G5 / G6 probes —
  their outputs are imported as-is.

---

## Risks (preserved from proposal + spec, with apply-phase mitigation)

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Approach A default is overridden by spec/design without fresh evidence | Low (A is FINAL) | Spec already locked A on 2026-09-02; this design records the lock in §1 |
| Tailwind 4 token namespace shift (`--color-primary` vs `--primary`) breaks plain-CSS `var(--token)` references | Medium | Alias names in `@theme` so legacy `--primary`, `--bg-surface`, `--realm-*` tokens resolve unchanged; parity test enumerates every `var(--token)` reference and asserts a non-empty declaration |
| `color-mix()` cascade reordering in the 80 KB inline `<style>` block causes visual drift | Medium | Migrate bespoke rules into `globals.css` inside `@layer base` so source order matches; Playwright visual regression on the existing chromium fixture |
| AC-21 search-engine contract test fails because `web/search_urls.js` location moved | Medium | Keep the literal under `src/data/search-engines.js` with the same shape; test's `open()` path updates in the same release |
| Hydration mismatch from `localStorage` reads on server vs client | Medium | Initial render uses a `mounted` flag; storage reads happen inside `useEffect`; tree structure defaults to the empty state on first paint |
| Static export forfeits dynamic routes / image optimization used by future work | Low | Acceptable for v1; switching to full Next.js dev server (Approach B) is the next-change cost if needed |
| Next.js + React dependency bundle size regresses initial paint | Low | `next build` profile captured before/after; Playwright + Lighthouse sample on the existing chromium fixture; ≤ 0 % regression is the success criterion |
| Single-port contract breaks if extension's `host_permissions` change accidentally | Low | Hard rule in Makefile + CI smoke check: `make api` only binds 8765; no second origin added; `manifest.json` is unchanged in this change |
| Predecessor artifacts drift during apply phase | Low | CI / branch-protection rule: this change's PRs MUST NOT modify `openspec/changes/migrate-nextjs-tailwind4/**`; lint hook rejects |

---

## Status

**Approach A is FINAL** (locked 2026-09-02; recorded in §1 of this
design). G1 PASS recorded; G2 PASS recorded against the verified
Next 16.3.3 / Turbopack clean build; G3 Tier-1 PASS recorded (all
26 §3.1 consumers green against the legacy pre-cut runtime via the
controlled fixture, `scripts/verify_consumers.py`, PR #109 + #111 +
#115 + #116). G3 Tier-2 (atomic-cut selection) NOT PASSED — gated
by G4 + G5 + G6 closure. G4 (Playwright + Lighthouse parity) **blocked —
verifier not authored**; must close in apply phase. G5 (hydration
baseline) **unreproducible — legacy baseline not on disk**; must be
reconstructed or replaced during apply phase. G6 (cutover rehearsal)
**blocked — verifier not authored**; must close in apply phase.
Predecessor `openspec/changes/migrate-nextjs-tailwind4/**` is frozen.
No FastAPI activation in this design pass; the atomic cutover PR3e
ships only when all six gates are green.

---

## Next step

The **tasks phase** (sdd-tasks) reads this design plus the predecessor's
`tasks.md`, `apply-progress.md`, and `cutover-manifest.json`, then
authors the per-sub-PR file lists for the 10 sub-PRs above under
Approach A within the 400-line review budget per sub-PR. The
**apply phase** owns the G4 / G5 / G6 closure sub-PRs and the atomic
cutover PR3e. The **archive phase** copies each per-domain spec
verbatim into
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
and promotes the modular-architecture spec into the canonical specs
tree.