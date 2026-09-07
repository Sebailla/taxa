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
| Evidence gates | **G1, G2, G3 Tier-1 PASS** (carried from predecessor). **G3 Tier-2, G4, G5, and G6 are not yet passed**; G5 remains **blocked** until a new capture runs under the user-approved replacement protocol (DOMContentLoaded metric; both sides served through controlled HTTP; one warm-up + 9 measured runs per side; median aggregation with raw samples/provenance; absolute candidate−baseline tolerance ≤ 10 ms; failure stays blocked, never an automatic PASS). |
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
| `taxonomy` | `Taxon` types + invariants | `useTaxonTree()`, `useTaxonDetail()`, parent-chain walker | `fetchTaxon`, `fetchChildren`, `fetchDomains` | `Tree`, `DetailPanel`, `OverviewTab`, `SearchTab`, `FolderTab`, `Breadcrumb`, `DomainList`, `Kebab` |
| `research` | `ResearchFile`, `Engine`, `FileNode` types | `useFileExplorer()`, `useFileViewer()`, format dispatcher | `fetchFiles`, `fetchServe`, `loadScriptOnce` (CDN lazy loader), `search-engines.js` | `FileExplorer`, `FileViewer`, `RawTableTreeTabs`, `MetaStrip`, `BreadcrumbPanel`, `Banners`, `SearchLinkList` |
| `design-system` | Theme tokens (typed) | — | `globals.css` (`@theme` block + `@layer base`), `next/font` wire-up | `<Icon>`, `<Button>`, layout primitives |
| `browser-state` | `LocalStorageKey` types, typed defaults, subscriber type | — | `store.ts` (4 keys × {read, write}), `useSyncExternalStore` adapter | — |
| `app-shell` | — | `AppShell` host composition, route shell state | `src/app/page.tsx`, `src/app/layout.tsx`, `next.config.mjs` | `AppShell`, `<Header>`, `<Tabs>` (Browser / Classification / Settings — Browser is **global Research / file explorer**, NOT taxon-scoped), `<HelpShell>`, `<SettingsView>`, `<BannerHost>` |

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

### UI surface and tab structure (verified current behavior)

The single-screen UI ships with two top-level surfaces (the
header `<Tabs>` and the taxonomic tree plus its detail panel)
and the verified current behavior of each, captured against
`http://127.0.0.1:8765/`:

| Surface | Location | Behavior (binding) |
| --- | --- | --- |
| **Taxonomic tree** | `<main>` left column | Tree rows render `rank / name / source / species-count` plus a per-row kebab menu. Selection of any node — including top-level domains — opens the inline detail panel. |
| **Detail panel** (per selected taxon) | `<main>` right column | Inline contextual panel with an inline header (rank + scientific name) and a tab strip. **Three tabs in this fixed order: `Overview`, `Search`, `Folder`.** All three tabs are reachable from any selection; **`Overview` is always available and always visible** per the user-selected policy (no future state is permitted to gate `Overview` behind a feature flag, a permission, or a taxon-shape check). |
| `Overview` tab | Detail panel body | Renders the taxon's metadata — scientific name, accepted status, authorship, species count. The default tab on fresh selection. |
| `Search` tab | Detail panel body | A categorized outbound-link list. Categories render in this fixed order: `General`, `Taxonomic`, `Academic`, `Multimedia`, `Documents`. Each entry is a single anchor (`<a>`) with `target="_blank"`, `rel="noopener noreferrer"`, and the URL template resolved from `SEARCH_ENGINES`. **`Search` is a primary tab, not a secondary card list** — it sits in the detail-panel tab strip, not below it. |
| `Folder` tab | Detail panel body | Per-taxon folder / materialize indicator; **separate from `Search`**. |
| `Browser` tab (header) | `<Header>` `<Tabs>` | **Global Research / file explorer** — opens the recursive folder tree / file viewer pair **without** a `taxonId` filter; it is the Research surface, not a taxon-scoped surface. Selecting a taxon while in `Browser` does **not** scope the file explorer to that taxon; the explorer continues to show the active research corpus. |
| Kebab actions (per tree row) | Floating popover anchored to the kebab glyph | Includes (a) "Search online", (b) materialize / open-folder affordance, (c) other tree-row affordances preserved from legacy. |

#### Binding tab-behavior contract (applies through apply phase)

- The detail-panel tab strip renders **all three tabs** for every
  selection. `Overview` is never conditionally hidden; the user-selected
  policy that `Overview` is always available / visible is binding and
  overrides any per-source (`col` / `worms` / `freshwater`)
  short-circuit.
- `Search` is a **primary tab** (sibling of `Overview` and `Folder`),
  not a secondary card list nested under `Overview`. The
  categorization of outbound-link entries (`General` /
  `Taxonomic` / `Academic` / `Multimedia` / `Documents`) lives
  inside the `Search` tab body.
- The "Search online" kebab action **forces the `Search` tab active**
  on the selected taxon (it MUST NOT default to `Overview`, even for
  top-level taxa). Current live behavior lands on `Overview` for
  top-level taxa — this is a known regression that the apply phase
  MUST close; the corrected interaction is "Search online" →
  `Search` tab for **every** selection.
- `Browser` (the header tab) is the **global Research / file
  explorer** and is **not** a third detail-panel tab. It is the
  Research surface, taxon-independent; selecting a taxon while
  `Browser` is active MUST NOT scope the explorer to that taxon.
- The 16-child chain topology (after the CSS re-split) is preserved;
  the tab structure and Search-force behavior land inside the
  existing PR 5a (taxonomy port) and PR 5b (research port) sub-PRs
  without changing
  positions, dependencies, or LoC envelopes that would push the
  chain over the 400-line per-PR budget.

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
      replaced in apply phase under the **user-approved replacement
      protocol** recorded in §"G5 — hydration baseline" below
      (DOMContentLoaded; both sides served through controlled HTTP;
      one warm-up + 9 measured runs per side; median aggregation with
      raw samples/provenance; absolute candidate−baseline tolerance
      ≤ 10 ms; failure stays blocked and requires a new capture).
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
- `tsconfig.json` reverts to the predecessor's strict-mode +
  `@taxa/<capability>` path-alias scaffold (the file already
  existed at repo root before PR 3a; the full Next.js / JSX /
  plugin config is removed on rollback).
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
| G5 (hydration baseline) | **blocked — real-capture verdicts ready / blocked / blocked; ±1 ms variance at 0–4 ms** under the previous percentage/median rule; no PASS authorized | Phase 6a disposition recorded below; reattempt runs under the user-approved replacement protocol (see §"G5 — hydration baseline" below) and requires a fresh capture — the protocol alone does not flip the gate |
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
| `tests/test_tailwind_4_tokens.py` | CSS (PR 3c-a) | Every legacy `:root` / `[data-theme="dark"]` / `--realm-*` token resolves to non-empty declaration in `globals.css::@theme` |
| `tests/test_taxonomy_styles.py` | CSS (PR 3c-b) | Every taxonomy `@layer components` selector (`.taxa-tree`, `.tree-row`, `.kebab`, `.detail-panel`, `.tab-strip`, `.overview-tab`, `.breadcrumb`, …) resolves to non-empty declaration |
| `tests/test_research_styles.py` | CSS (PR 3c-c) | Every research / chrome `@layer components` selector (`.search-tab`, `.search-category-section`, `.search-link-list`, `.search-link`, `.folder-tab`, `.header-browser-tab`, `.research-explorer`, …) resolves to non-empty declaration |
| `tests/test_tailwind_4_parity.py` | CSS (PR 3c-d) | Consolidated parametrized final parity test — every legacy `:root` token, every `var(--token)` reference, every legacy utility class, every `@keyframes` / `color-mix()` selector resolves to non-empty declaration; covers the 1,963-line legacy inline CSS end-to-end |
| `tests/test_design_system_purity.py` | CSS (PR 3c-a) | Grep guard over `src/modules/design-system/`; no hex literals outside the design-system module |
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
| G5 (hydration baseline) | `scripts/measure_hydration.py` (already authored) re-run under the user-approved replacement protocol | hydration baseline JSON + raw samples/provenance | Observable metric = `DOMContentLoaded`; both baseline and candidate served through controlled HTTP (no `file://`); one warm-up + 9 measured runs per side; aggregation = per-side median with raw samples + provenance preserved; **absolute (candidate − baseline) ≤ 10 ms**; failure stays blocked, no automatic PASS |
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
| Audit `web/dist/evidence-baseline.json` and capture provenance; Phase 6a real captures exist, but the current 0–4 ms comparison is unstable (**ready / blocked / blocked**, ±1 ms variance) under the previous percentage/median rule. | Apply | Audit report |
| Capture the legacy baseline via `scripts/measure_hydration.py` against the legacy chromium fixture | Apply | legacy hydration JSON |
| The previous methodological-exception **request** (Phase 6a, 2026-09-06) is **superseded** by the user-approved replacement protocol below; do not tune 6a or force a pass against the previous rule. | Apply | risk-register update |
| Re-run `scripts/measure_hydration.py` against the new build under the user-approved replacement protocol | Apply | new hydration JSON |
| Under the user-approved replacement protocol: `median(candidate) − median(baseline) ≤ 10 ms`; failure stays blocked and requires a new capture (no automatic PASS, no closure, no cutover activation). | Apply | blocked/status update |

**User-approved replacement G5 protocol (recorded here as the canonical design record; approved after G5 instability on the previous rule, but not a G5 capture or PASS authorization).** Comparable real-capture runs under the previous empirical-median percentage rule produced verdicts `ready`, `blocked`, and `blocked`: at 0–4 ms, each run's measurements can move by ±1 ms, so the previous rule is not reproducible. The user-approved replacement protocol below supersedes that rule and binds every reattempt of G5.

- **Transport — both sides served through controlled HTTP.** The legacy baseline fixture and the candidate build are served through an in-process local static HTTP server (no `file://` URIs). The HTTP serve is the same controlled HTTP transport for both sides; the only difference is the served directory (legacy fixture vs. candidate `out/`). This removes `file://` clock-origin drift from the comparison.
- **Observable metric — `DOMContentLoaded`.** The named observable event is the browser's `DOMContentLoaded` timestamp, captured via the PerformanceNavigationTiming API over the controlled HTTP serve. `DOMContentLoaded` replaces the previous initial-paint + interaction-latency pair, which was dominated by sub-millisecond noise at the 0–4 ms scale.
- **Sampling — one warm-up plus 9 measured runs per side.** Each side (legacy baseline, candidate) executes exactly **1 warm-up run** followed by **9 measured runs**. The warm-up primes the browser cache and JIT; only the 9 measured runs contribute to aggregation. Total per side: 10 navigations (1 warm-up + 9 measured). Sample counts are pinned in the measurement script and asserted in the validator.
- **Aggregation — per-side median, raw samples + provenance preserved.** For each side, the per-run `DOMContentLoaded` value across the 9 measured runs is aggregated as the **median** (not the mean), because median is robust to a single outlier and matches the previous rule's stated intent. The artifact must persist **every raw sample** plus the **per-run provenance** (browser version, build SHA, route, capture timestamp, capture environment) alongside the computed median. No down-sampling, no summarization without raw samples.
- **Tolerance — absolute (candidate − baseline) ≤ 10 ms.** The pass/fail rule is a single absolute millisecond tolerance: `median(candidate) − median(baseline) ≤ 10 ms`. There is no percentage threshold and no negative-direction slack: any positive median regression greater than 10 ms is a fail. The 10 ms ceiling is the absolute bound; smaller absolute deltas pass.
- **Failure semantics — stays blocked, never an automatic PASS.** A failed run under this protocol does **not** flip G5 to PASS, does **not** grant closure, does **not** waive the tolerance, and does **not** authorize cutover activation. The status-footer stays `blocked`. A subsequent reattempt requires a **new user request** (a new capture is initiated only on explicit request); the approved protocol does not auto-rerun, and a previous PASS is never carried forward across a failure.
- **Predecessor frozen.** This protocol supersedes the previous methodological-exception **request**; it does **not** modify `openspec/changes/migrate-nextjs-tailwind4/**`. Scripts under `scripts/` (already authored: `scripts/reconstruct_hydration_baseline.py`, `scripts/capture_hydration_candidate.py`, `scripts/measure_hydration.py`, `scripts/g5_close.sh`) and `tests/test_hydration_timing.py` are extended in apply phase to bind the protocol above; this design records the protocol, the apply worker extends the harness.
- **G5 remains blocked.** Recording this protocol is **not** a capture and is **not** a PASS authorization. G5 stays `blocked` in `evidence/g5/status.json` and in the status-footer until a fresh capture under this protocol runs and exits within the 10 ms absolute tolerance. A PASS is recorded only when that fresh capture succeeds.

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

> **2026-09-02 — corrective plan revision**: the slice
> table below replaces the original ordering after the
> apply gate identified a dependency-order defect
> (original PR 3a required `next build`/`out/index.html`
> before the Next/React/Tailwind/TypeScript toolchain and
> Node runtime contract existed; those landed in original
> PR 3c). The corrected order installs the toolchain
> first (position 1), demotes the App Router static
> export to position 2 (now satisfiable), keeps
> Tailwind/tokens at position 3, fuses the Makefile
> rewrite with the `WEB_DIR` repoint + AC-21 into a
> single sub-PR at position 4, and follows with state,
> ports, e2e, validation, and the atomic cutover. The
> 13-child count is preserved. The full per-task file
> lists and the dependency-correctness rationale live in
> `tasks.md`; this table is the executive view.

> **2026-09-02 — dependency-defect fix (this revision)**.
> The apply gate's pre-flight re-audit identified a
> second dependency defect inside the corrected topology:
> the PR 3b at position 2 imported `@taxa/app-shell` (a
> module PR 4b ships at position 9/16 — *later* in the
> chain) and `./globals.css` (a file PR 3c-a ships at
> position 3/16 — *later* in the chain). At its
> `next build` witness, neither target file existed yet.
> The same audit flagged PR 3b.5's triangulation
> assertion that the build output references the typed
> store barrel path `@taxa/browser-state` — that barrel
> file does not exist until PR 4a. **PR 3b is rescoped
> to a self-contained App Router static-export
> bootstrap**: minimal semantic placeholders that
> import neither `@taxa/app-shell` nor `./globals.css`;
> the `import "./globals.css";` line moves into PR 3c-a;
> the `<AppShell>` integration into `src/app/{layout,
> page}.tsx` moves into PR 4b. PR 3b.5's unsatisfiable
> `@taxa/browser-state` reference is dropped. **The
> 13-child topology and ordering are preserved**;
> per-PR LoC budgets stay well under 400; **only the
> prior PR 3a `package-lock.json` exception remains**.
> Approach A, FastAPI/SQLite, the frozen predecessor,
> and the per-domain specs stay unchanged.

> **2026-09-02 — CSS re-split (this revision)**. The
> apply gate's pre-flight re-audit identified that PR 3c
> (position 3/13 in the prior topology), as scoped at the
> previous corrective revision, was **unsatisfiable**:
> it was tasked with migrating the legacy
> `web/index.html` inline `<style>` block of **1,963
> lines** in a single sub-PR while staying under the
> 400-line per-PR review budget — the migration cannot
> fit. The CSS portion of the migration is therefore
> **re-split into four chained children**, each ≤ 400
> author lines: PR 3c-a (tokens / base / dark mode,
> position 3/16), PR 3c-b (tree + inline Overview
> styles, position 4/16), PR 3c-c (Search / Folder /
> global Browser styles, position 5/16), PR 3c-d
> (animations / utilities + final parity, position
> 6/16). Tracker **PR #146** is the merged starting
> point for the first new CSS child (PR 3c-a). Every
> later child shifts position by +3 to accommodate the
> four CSS children: PR 3d 4→7; PR 4a 5→8; PR 4b 6→9;
> PR 5a 7→10; PR 5b 8→11; PR 5c 9→12; PR 6a 10→13; PR 6b
> 11→14; PR 6c 12→15; PR 3e 13→16. The semantic labels
> (3a, 3b, 3c-a, 3c-b, 3c-c, 3c-d, 3d, 4a, 4b, 5a,
> 5b, 5c, 6a, 6b, 6c, 3e) are preserved; only the
> position counter (NN in
> `feat/complete-taxa-frontend-migration-NN-XXX`) and
> base-branch references change. The four CSS children
> collectively migrate the 1,963 legacy inline CSS lines
> into `src/app/globals.css` (≤ 1,500 authored lines
> plus Tailwind 4 base reset, well under the predecessor
> `out/_next/static/chunks/*.css` budget); the legacy
> `<style>` block is retired at PR 5c. **16-child count**
> replaces the prior 13-child count. Per-sub-PR LoC
> budgets stay well under the 400-line review budget;
> **only the prior PR 3a `package-lock.json` exception
> remains**. Approach A, FastAPI/SQLite, the frozen
> predecessor, and the per-domain specs stay unchanged.

> **2026-09-03 — PR 3c-d re-split supersession (PR #150
> task replan is authoritative; this document still
> reflects the pre-#150 16-child CSS re-split only)**.
> PR #150 (`tasks.md` / `tasks-es.md` "3c-d
> unsatisfiability split") re-plans the previous
> monolithic PR 3c-d (animations / utilities + final
> parity) into three sequential children, each ≤ 400
> authored lines. The sub-PR slice table and dependency
> order above remain the **pre-#150 view**; the
> **authoritative re-split lives in `tasks.md` /
> `tasks-es.md`**, which the apply phase reads. The new
> partition:
>
> - **PR 3c-d (6/18; narrowed, stays at 6/18)** —
>   base / reset / global state affordances. Extends
>   `globals.css::@layer base` with the **global state
>   affordances only**: `@keyframes` (`spin`), the
>   **global `@layer base` `color-mix()` selectors**,
>   `body { overscroll-behavior: none; … }`, and
>   `main > :first-child { margin-top: 0 !important; }`.
>   **No utility classes, no parity test.** Allowed
>   production: `src/app/globals.css`; allowed test:
>   `tests/test_tailwind_4_base_resets.py`.
> - **PR 3c-e (7/18; new)** — utility-class + remaining
>   animation parity. Extends `globals.css::@layer
>   base` with the utility-class surface
>   (`bg-primary`, `text-on-surface`,
>   `border-outline-variant`,
>   `bg-surface-container-lowest`, `shadow-sm`,
>   `rounded-r-md`, `bg-primary-fixed`,
>   `text-on-primary-fixed`, …) **plus any remaining
>   `@keyframes` / `color-mix()` (component-scoped
>   color-mix, utility-paired rules)** — the global
>   `@layer base` state affordances stay in 3c-d.
>   **No parity test.** Allowed production:
>   `src/app/globals.css`; allowed test:
>   `tests/test_tailwind_4_utilities.py`.
> - **PR 3c-f (8/18; new; sole full-parity test
>   only)** — **no new `globals.css` code**. Final
>   parametrized parity test
>   `tests/test_tailwind_4_parity.py` consolidates the
>   five prior focused tests (3c-a tokens / 3c-b
>   taxonomy / 3c-c research / 3c-d base-resets / 3c-e
>   utilities). Final parity contract is unchanged; it
>   belongs only to PR 3c-f.
>
> Renumbering: 3d 7→**9/18**; 4a 8→**10/18**;
> 4b 9→**11/18**; 5a 10→**12/18**; 5b 11→**13/18**;
> 5c 12→**14/18**; 6a (G5) 13→**15/18**;
> 6b (G6) 14→**16/18**; 6c (G4) 15→**17/18**;
> 3e 16→**18/18**. **3c-d stays at 6/18** (same
> branch, narrowed). New branches:
> `…-07-3c-e` (base `…-06-3c-d`),
> `…-08-3c-f` (base `…-07-3c-e`). **18-child count**
> replaces 16; `feature-branch-chain` strategy and
> "tracker-only targets `develop`" contract hold.
> Per-sub-PR LoC budgets stay well under 400; only the
> prior PR 3a `package-lock.json` exception remains.
> **G4 / G5 / G6 (now 17/18 / 15/18 / 16/18), the
> frozen predecessor, Approach A, FastAPI/SQLite, and
> the per-domain specs stay unchanged**. Merged PRs
> 3c-a/#147, 3c-b/#148, 3c-c/#149 preserved. The five
> CSS children (3c-a / 3c-b / 3c-c / 3c-d / 3c-e) plus
> PR 3c-f cannot collapse without violating the
> 400-line per-PR review budget. **Documentation-only
> supersession note**: no source-code edit, no rebase,
> no new branch creation in this revision; the next
> code worktree picks up the authoritative scope from
> `tasks.md`.

The predecessor's `tasks.md` enumerated 35 tasks across
14+ sub-PRs. The corrected chain re-slices them under
Approach A within the 400-line review budget per sub-PR.

| Position | Sub-PR | Predecessor task mapping | Scope | New / preserved | LoC budget |
| --- | --- | --- | --- | --- | --- |
| 1 / 13 | PR 3a (toolchain bootstrap) | NEW (absorbs part of original task 3.4 — `package.json` rewrite + `scripts/check-runtime.mjs`) | `package.json` dep pins (`next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, TS toolchain, `engines.node ">=20.9.0"`; legacy `autoprefixer` / `postcss` / `@tailwindcss/forms` removed; scripts `check-runtime` and `build:web`) + regenerated `package-lock.json` (the sole user-approved size exception; generated-resolution-only — contains only the resolution changes required by this manifest; reviewed together with `package.json`; no unrelated lockfile churn) + `scripts/check-runtime.mjs` (new, Node ≥ 20.9.0 enforcement) + `tsconfig.json` (modified in place; the predecessor already created the file at repo root in PR 2a — PR 3a extends it with the full Next.js / JSX / plugin config and the `@taxa/<capability>` path aliases; restored to its predecessor state on rollback) + `.nvmrc` (new, pin `20`) + `tests/test_toolchain_bootstrap.py` (new) + `tests/test_check_runtime.py` (new) | New | ~210 authored (≤ 400; the sole `size:exception` is the regenerated `package-lock.json`; authored source/test/config work stays ≤400) |
| 2 / 13 | PR 3b (App Router static-export bootstrap, self-contained) | task 3.1 (rescoped) | `src/app/{layout,page}.tsx` (minimal semantic placeholder; **no AppShell, no globals.css import**) + `next.config.mjs` + `tests/test_app_shell_render.py` (the `out/index.html` / viewport / Raleway preload witness is satisfiable here because the toolchain is live **and** PR 3b imports nothing that 3c or 4b produce) | New (rescoped) | ~150 (≤ 400) |
| 3 / 16 | PR 3c-a (tokens / base / dark mode) | task 3.2 + 1-line integration | `src/app/globals.css` (initial scaffold: `@import "tailwindcss"` + `@theme` mirroring every legacy `:root` / `[data-theme="dark"]` / `--realm-*` token + empty `@layer base` placeholder for later children) + `import "./globals.css";` added to `src/app/layout.tsx` (the dependency-defect fix — 3c-a owns the file it imports) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` + `tests/test_tailwind_4_tokens.py` + `tests/test_design_system_purity.py` | New | ~400 (≤ 400) |
| 4 / 16 | PR 3c-b (tree + inline Overview styles) | task 3.2 (taxonomy selectors partition) | `src/app/globals.css` extended with `@layer components` rules for the taxonomy module: `.taxa-tree`, `.tree-row`, `.kebab`, `.kebab-menu`, `.tree-search-icon`, `.materialize-indicator`, `.detail-panel`, `.tab-strip`, `.tab-button`, `.overview-tab`, `.breadcrumb` (per-row kebab, per-row search icon, per-row materialize indicator, breadcrumb monospace family, 3-tab strip styling) + `tests/test_taxonomy_styles.py` | New | ~400 (≤ 400) |
| 5 / 16 | PR 3c-c (Search / Folder / global Browser styles) | task 3.2 (research / chrome selectors partition) | `src/app/globals.css` extended with `@layer components` rules for the research module and chrome shell: `.search-tab`, `.search-category-section`, `.search-link-list`, `.search-link` (anchor `target="_blank"` / `rel="noopener noreferrer"`), `.folder-tab`, `.header-browser-tab` (global Research / file explorer, NOT taxon-scoped), `.research-explorer`, `.file-explorer-pane`, `.file-viewer-pane` + `tests/test_research_styles.py` | New | ~400 (≤ 400) |
| 6 / 16 | PR 3c-d (animations / utilities + final parity) | task 3.2 (animations / utilities / final parity partition) | `src/app/globals.css` extended with `@keyframes` (`spin`), `color-mix()` selectors, utility-class surface (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`, `text-on-primary-fixed`, …), `body { overscroll-behavior: none; … }` rule, `main > :first-child { margin-top: 0 !important; }` reset — all under `@layer base` in source order + `tests/test_tailwind_4_parity.py` (consolidated parametrized parity test) | New | ~300 (≤ 400) |
| 7 / 16 | PR 3d (Makefile/mount) | task 3.4 (Makefile portion) + task 3.6 + 3.7 (WEB_DIR repoint + AC-21) | `Makefile::api` rewrite (runs `check-runtime.mjs` → `npm run build:web` → `uvicorn … --port 8765`; legacy `make css` becomes no-op shim) + `api/server.py:54` WEB_DIR repoint + `web/search_urls.js` → `src/data/search-engines.js` + AC-21 `open()` update + `tests/test_make_api_build.py` + `tests/test_static_mount.py` | New (fused) | ~240 (≤ 400) |
| 8 / 16 | PR 4a | task 4.1 + 4.2 | `src/modules/browser-state/{domain/keys.ts, infrastructure/store.ts, index.ts}` + 4 read + 4 write sites inside `useEffect` | New | ~180 (≤ 400) |
| 9 / 16 | PR 4b (hydration guard + AppShell integration) | task 4.3 + 4.4 + AppShell integration seam | `useSyncExternalStore` behind `mounted` flag + Playwright zero-hydration-warnings assertion + `src/app/{layout,page}.tsx` modified to integrate `<AppShell>` from `@taxa/app-shell` (the dependency-defect fix — 4b owns both the AppShell module **and** the App Router host integration) | New | ~120 (≤ 400) |
| 10 / 16 | PR 5a | task 5.1 + 5.2 + 5.3 | `src/modules/taxonomy/{domain,application,infrastructure,presentation}` + port `web/{tree,detail,breadcrumb}.js` + **DetailPanel tab strip** (`Overview` / `Search` / `Folder`, all three always reachable; `Overview` always available per user policy) + **`OverviewTab`** (scientific name, accepted status, authorship, species count) + **`Kebab`** menu including `Search online` action that **forces the `Search` tab** (closes the current live regression where `Search online` lands on `Overview` for top-level taxa); the taxonomy presentation layer rides on PR 3c-b's `@layer components` selectors | New | ~310 (≤ 400) |
| 11 / 16 | PR 5b | task 5.4 + 5.5 + 5.6 | `src/modules/research/{domain,application,infrastructure,presentation}` + port `web/{file_explorer,file_viewer,format,keymap}.js` + CDN pin + **`SearchTab`** with categorized outbound-link list (`General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents`, fixed order) + **`FolderTab`** (per-taxon materialize indicator; **separate** from `SearchTab`) + **`SearchLinkList`** presenter that maps each `Engine` to an anchor with `target="_blank"`, `rel="noopener noreferrer"` + **header `Browser` tab re-anchored as global Research / file explorer** (NOT taxon-scoped; selecting a taxon while `Browser` is active MUST NOT scope the explorer); the research presentation layer rides on PR 3c-c's `@layer components` selectors | New | ~395 (≤ 400, tight headroom; maintainability tracked) |
| 12 / 16 | PR 5c | task 5.7 + 5.8 + 5.9 | Playwright + e2e selector updates + `data-*` contract preservation + delete `web/*.{html,js,css}` (the legacy `web/index.html` deletion retires the 1,963-line legacy inline CSS the four CSS children migrated into `src/app/globals.css`) + `tailwind.config.js` | New | ~200 (≤ 400) |
| 13–15 / 16 | Phase 6a / 6b / 6c (validation) | NEW | G5 baseline reconstruction / G6 cutover rehearsal / G4 Playwright + Lighthouse parity measurement (validation work; no new `web/**` or `api/server.py` route handlers or `extension/**`) | New (measurement) | ~190 + ~120 measurement (≤ 400 each) |
| 16 / 16 | PR 3e (cutover) | atomic cutover unit | The four-set release + cutover-manifest Tier-2 flip + G3 Tier-2 verifier rerun + status-footer flips for G4 / G5 / G6 closure | Atomic | ~120 (≤ 400) |

### Dependency order (corrective plan revision + dependency-defect fix contract)

- **PR 3a — toolchain bootstrap**. Self-contained.
- **PR 3b — App Router static-export bootstrap (self-contained)**
  depends on 3a (deps installed + Node ≥ 20.9.0 contract).
  Imports nothing that 3c-a or 4b produce.
- **PR 3c-a — tokens / base / dark mode** depends on 3a
  (`tailwindcss@^4` installed) and **3b** (the
  `src/app/layout.tsx` placeholder that PR 3c-a imports
  `./globals.css` into — the dependency-defect fix moves
  the import into the sub-PR that owns the file). Creates
  `src/app/globals.css` (initial scaffold with `@theme`
  + empty `@layer base` placeholder) and ships the
  design-system barrel.
- **PR 3c-b — tree + inline Overview styles** depends on
  3c-a (the `globals.css` scaffold + `@layer base`
  placeholder exist). Extends `globals.css` with the
  `@layer components` rules for the taxonomy module.
- **PR 3c-c — Search / Folder / global Browser styles**
  depends on 3c-b (the taxonomy `@layer components`
  block is in place). Extends `globals.css` with the
  `@layer components` rules for the research module and
  chrome shell.
- **PR 3c-d — animations / utilities + final parity**
  depends on 3c-c (the research / chrome `@layer
  components` block is in place). Finalizes
  `globals.css` with the `@layer base` `@keyframes`,
  `color-mix()`, utility classes, body reset, and
  first-child reset; ships the consolidated
  `tests/test_tailwind_4_parity.py` final parity test.
- **PR 3d — Makefile/mount** depends on 3b
  (`next build` produces `out/index.html`) and 3c-d
  (Tailwind 4 tokens + `@layer base` + `@layer
  components` flow through `next build`; the final
  Tailwind 4 parity test is on disk).
- **PR 4a — typed store** depends on 3c-a
  (design-system barrel loaded).
- **PR 4b — hydration guard + AppShell integration** depends
  on 4a (store available), **3b** (the
  `src/app/{layout,page}.tsx` placeholders that PR 4b
  integrates `<AppShell>` into — the dependency-defect fix
  moves the AppShell integration into the sub-PR that owns the
  `app-shell` module), and 3c-a (Tailwind 4 `@theme`
  tokens + design-system barrel loaded for `next build`).
- **PR 5a — taxonomy port** depends on 4b
  (hydration-safe state read) and 3c-b (the taxonomy
  `@layer components` block is in place — the taxonomy
  presentation layer rides on PR 3c-b's CSS).
- **PR 5b — research port + CDN pin** depends on 5a
  (taxonomy state read shared), 3d
  (`src/data/search-engines.js` for the `Engine` named
  export), and 3c-c (the research / chrome `@layer
  components` block is in place — the research
  presentation layer rides on PR 3c-c's CSS).
- **PR 5c — e2e + delete legacy** depends on 5b (all UI
  components live) and 3c-d (the final Tailwind 4
  parity test is on disk; the 1,963-line legacy inline
  CSS has been migrated into `src/app/globals.css`
  end-to-end and is ready to be retired at PR 5c).
- **PR 6a / 6b / 6c — validation** depends on 5c.
- **PR 3e — atomic cutover** depends on all six gates
  green.

The PR 3e cutover sub-PR ships **only when** all six
gates are green; the apply worker is gated on the G4 / G5
/ G6 closure sub-PRs (3e itself lands after the closure
verifications).

---

## Affected files (executive view)

> **Corrective plan revision of 2026-09-02**: the PR
> labels in this table reflect the reordered chain
> (toolchain bootstrap at position 1, App Router static
> export at position 2, Tailwind/tokens at position 3,
> fused Makefile/mount at position 4).

| Area | Action | Files |
| --- | --- | --- |
| `web/index.html` | Deleted at activation (PR 5c) | `web/index.html` |
| `web/*.js` (18 modules) | Deleted at activation (PR 5c) | `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` |
| `web/index.css` | Deleted at activation (PR 5c) | `web/index.css` |
| `web/dist/tailwind.css` | Regenerated by reverted `make css` after rollback; not part of new build | `web/dist/tailwind.css` |
| `tailwind.config.js` | Deleted at activation (PR 5c) | `tailwind.config.js` |
| `package.json` | Modified (PR 3a, toolchain bootstrap) — `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, TS toolchain, `engines.node ">=20.9.0"`; removes `autoprefixer`, `postcss`, `@tailwindcss/forms`; adds `scripts.check-runtime` and `scripts.build:web` | `package.json` |
| `package-lock.json` | Regenerated (PR 3a, toolchain bootstrap) — sole user-approved size exception; generated-resolution-only (no hand-authored content); contains only the resolution changes required by this manifest; reviewed together with `package.json`; no unrelated lockfile churn | `package-lock.json` |
| `tsconfig.json` | Modified in place (PR 3a, toolchain bootstrap) — full Next.js / JSX / plugin config layered on top of the predecessor's strict-mode + `@taxa/<capability>` path-alias scaffold (the predecessor already created the file at repo root in PR 2a; restored to its predecessor state on rollback) | `tsconfig.json` |
| `.nvmrc` | Created (PR 3a, toolchain bootstrap) — pin `20` | `.nvmrc` |
| `scripts/check-runtime.mjs` | Created (PR 3a, toolchain bootstrap) — Node ≥ 20.9.0 enforcement | new |
| `tests/test_toolchain_bootstrap.py` | Created (PR 3a, toolchain bootstrap) — verifies deps, engines.node, scripts, path aliases, .nvmrc | new |
| `tests/test_check_runtime.py` | Created (PR 3a, toolchain bootstrap) — verifies the Node ≥ 20.9.0 floor exit codes | new |
| `src/app/{layout,page}.tsx` | Created (PR 3b, App Router self-contained static-export bootstrap) — **minimal semantic placeholder body**; **does NOT mount `<AppShell>`** (lands in PR 4b) **and does NOT import `./globals.css`** (lands in PR 3c-a). PR 4b later modifies these to integrate `<AppShell>` from `@taxa/app-shell` | new (3b) + modified (4b) |
| `next.config.mjs` | Created (PR 3b, App Router static export) — `output: "export"`, `images.unoptimized: true`, `trailingSlash: false`, `reactStrictMode: true` | new |
| `tests/test_app_shell_render.py` | Created (PR 3b, App Router static export) — reads `out/index.html` after `next build`; asserts viewport meta + Raleway preload + Raleway `.woff2` file in `out/_next/static/media/` | new |
| `src/app/globals.css` | Created (PR 3c-a, tokens / base / dark mode) — Tailwind 4 `@import "tailwindcss"` + `@theme` mirroring every legacy `:root` / `[data-theme="dark"]` / `--realm-*` token + empty `@layer base` placeholder. PR 3c-a **also** adds `import "./globals.css";` to `src/app/layout.tsx` (the dependency-defect fix — the import lives with the file it imports). PR 3c-b extends the file with `@layer components` taxonomy rules; PR 3c-c extends with `@layer components` research / chrome rules; PR 3c-d finalises with `@layer base` `@keyframes` / `color-mix()` / utility / body reset / first-child reset | new (3c-a) + extended (3c-b / 3c-c / 3c-d) |
| `src/modules/design-system/{infrastructure/index.ts, presentation/Icon.tsx, presentation/Button.tsx}` | Created (PR 3c-a, tokens / base / dark mode) — design-system barrel | new |
| `tests/test_tailwind_4_tokens.py` | Created (PR 3c-a, tokens / base / dark mode) — enumerates legacy `:root` / `[data-theme="dark"]` / `--realm-*` tokens against `globals.css::@theme` | new |
| `tests/test_design_system_purity.py` | Created (PR 3c-a, tokens / base / dark mode) | new |
| `tests/test_taxonomy_styles.py` | Created (PR 3c-b, tree + inline Overview styles) — enumerates taxonomy `@layer components` selectors against `globals.css` | new |
| `tests/test_research_styles.py` | Created (PR 3c-c, Search / Folder / global Browser styles) — enumerates research / chrome `@layer components` selectors against `globals.css` | new |
| `tests/test_tailwind_4_parity.py` | Created (PR 3c-d, animations / utilities + final parity) — consolidated parametrized parity test (every legacy `:root` token, every `var(--token)` reference, every legacy utility class, every `@keyframes` / `color-mix()` selector) | new |
| `Makefile` | Modified (PR 3d, Makefile/mount) — `api` target runs `check-runtime.mjs` → `npm run build:web` → uvicorn; legacy `make css` retired to no-op shim | `Makefile` |
| `api/server.py` | Modified (PR 3d, Makefile/mount) — `WEB_DIR` repoint at line 54 only; mount signature unchanged | `api/server.py` |
| `src/data/search-engines.js` | Created (PR 3d, Makefile/mount) — replaces `web/search_urls.js` with `SEARCH_ENGINES` named export | new |
| `tests/test_make_api_build.py` | Created (PR 3d, Makefile/mount) — verifies Makefile run order and Node floor | new |
| `tests/test_static_mount.py` | Created (PR 3d, Makefile/mount) — verifies `WEB_DIR` repoint and single-origin contract | new |
| `tests/test_smoke.py::test_search_engine_contract` | Modified (PR 3d, Makefile/mount) — `open()` path updated if literal moved; byte shape preserved | `tests/test_smoke.py` |
| `src/modules/browser-state/**` | Created (PR 4a) — typed store + 4 read + 4 write sites | new |
| `tests/test_browser_state_keys.py` | Created (PR 4a) | new |
| `src/modules/app-shell/**` | Created (PR 4b) — AppShell + page-chrome + hydration guard. PR 4b **also** integrates `<AppShell>` from this module into `src/app/{layout,page}.tsx` (the dependency-defect fix — PR 4b owns both the AppShell module **and** the App Router host integration; PR 3b's placeholder layout/page is replaced by the integrated AppShell composition in 4b) | new |
| `tests/test_hydration_console.py` | Created (PR 4b) | new |
| `src/modules/taxonomy/**` | Ported (PR 5a) — port of `web/{tree,detail,breadcrumb}.js` to React + `DetailPanel` tab strip (`Overview` / `Search` / `Folder`, all three always reachable; `Overview` always available per user policy) + `OverviewTab` + `Kebab` menu with `Search online` action forcing the `Search` tab | new |
| `tests/test_taxonomy_infra.py` | Created (PR 5a) — plus assertions for the three-tab strip, the `Overview`-always-visible contract, and the `Search online` → `Search` tab force (closes the current live regression where top-level taxa land on `Overview`) | new |
| `src/modules/research/**` | Ported (PR 5b) — port of `web/{file_explorer,file_viewer,format,keymap}.js` + CDN pin + `SearchTab` with categorized outbound-link list (`General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents`) + `FolderTab` (separate) + `SearchLinkList` presenter + header `Browser` tab re-anchored as global Research / file explorer (NOT taxon-scoped) | new |
| `tests/test_research_infra.py` | Created (PR 5b) | new |
| `tests/test_e2e_file_explorer.py` | Modified (PR 5c) — DOM selectors updated; `data-*` contract preserved | `tests/test_e2e_file_explorer.py` |
| `tests/test_web_toggle.py` | Modified (PR 5c) — theme toggle persists via typed store | `tests/test_web_toggle.py` |
| `tests/test_evidence_baseline.py` | Modified (PR 5c) — legacy `web/*.js` roster assertion flips to "absent" | `tests/test_evidence_baseline.py` |
| `scripts/reconstruct_hydration_baseline.py` + `scripts/g5_close.sh` | Created (Phase 6a) — G5 baseline closure | new |
| `scripts/rehearse_cutover.py` + `tests/test_rehearse_cutover.py` | Created (Phase 6b) — G6 cutover rehearsal + parametrized fail-closed invariant | new |
| `scripts/g4_measure.sh` + `out/g4-parity-report.json` | Created (Phase 6c) — G4 Playwright + Lighthouse parity measurement | new |
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
| G5 current median/percentage protocol is unstable at 0–4 ms; comparable real captures produced **ready / blocked / blocked** verdicts with ±1 ms movement. | High | The Phase 6a risk disposition was a methodological-exception request that has been **superseded by the user-approved replacement G5 protocol** recorded in §"G5 — hydration baseline": DOMContentLoaded observable, both sides served through controlled HTTP, 1 warm-up + 9 measured runs per side, median aggregation with raw samples/provenance, absolute (candidate − baseline) ≤ 10 ms, and failure-stays-blocked / new-request semantics. G5 remains blocked; no PASS, closure, or cutover activation is granted by recording the protocol — a fresh capture under the protocol is required. |
| Static export forfeits dynamic routes / image optimization used by future work | Low | Acceptable for v1; switching to full Next.js dev server (Approach B) is the next-change cost if needed |
| Next.js + React dependency bundle size regresses initial paint | Low | `next build` profile captured before/after; Playwright + Lighthouse sample on the existing chromium fixture; ≤ 0 % regression is the success criterion |
| Single-port contract breaks if extension's `host_permissions` change accidentally | Low | Hard rule in Makefile + CI smoke check: `make api` only binds 8765; no second origin added; `manifest.json` is unchanged in this change |
| Predecessor artifacts drift during apply phase | Low | CI / branch-protection rule: this change's PRs MUST NOT modify `openspec/changes/migrate-nextjs-tailwind4/**`; lint hook rejects |
| **Detail-panel tab structure regresses** (current live behavior): the `Search online` kebab action lands on `Overview` instead of forcing `Search`, and `Browser` is scoped to the selected taxon. | Medium | Design §"UI surface and tab structure" pins the contract (Overview always available/visible; Search is a primary tab; Search online → Search; Browser is global Research). PR 5a / PR 5b tasks assert the behavior; Playwright witness in PR 5c covers regression. The corrected interaction closes the current regression in the same apply phase that lands the React cutover. |
| `Search` degrades from primary tab to secondary card list. | Medium | Design binds `Search` as a sibling of `Overview` / `Folder` inside the detail-panel tab strip; the per-domain spec narrative is updated through this design revision (high-level only — per-domain specs are not in scope of this revision). The tab-strip Playwright witness in PR 5c asserts three siblings in the legacy order. |

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
baseline) **blocked — real-capture verdicts were ready / blocked /
blocked with ±1 ms variance at 0–4 ms** under the previous
percentage/median rule; the user-approved replacement protocol
(DOMContentLoaded observable; both sides served through controlled
HTTP; 1 warm-up + 9 measured runs per side; median aggregation with
raw samples/provenance; absolute candidate−baseline tolerance ≤ 10 ms;
failure stays blocked, requires a new request) is recorded in §"G5 —
hydration baseline", but G5 remains blocked until a fresh capture
under that protocol runs and exits within tolerance. G6 (cutover
rehearsal) **blocked — verifier not authored**; must close in apply
phase. Predecessor
`openspec/changes/migrate-nextjs-tailwind4/**` is frozen.
No FastAPI activation in this design pass; the atomic cutover PR3e
ships only when all six gates are green.

---

## Next step

The **tasks phase** (sdd-tasks) reads this design plus the
predecessor's `tasks.md`, `apply-progress.md`, and
`cutover-manifest.json`, then authors the per-sub-PR file
lists for the 13 sub-PRs above under Approach A within the
400-line review budget per sub-PR (the corrective plan
revision of 2026-09-02 reordered the slice and rescoped
PRs 3a–3d so the toolchain bootstrap lands first). The
**apply phase** owns the G4 / G5 / G6 closure sub-PRs and
the atomic cutover PR3e. The **archive phase** copies each
per-domain spec verbatim into
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
and promotes the modular-architecture spec into the
canonical specs tree.

---

## Addendum — 2026-09-04: Phase 5a four-slice replan (append-only)

This is a deliberate **append-only** decision addendum; the prose above for
Phase 5a (taxonomy port, PR 5a at the chain position it currently holds)
is preserved verbatim. It records a docs-only supersession that governs
how the **next** code worktree re-slices PR 5a into four reviewable
sub-PRs. The oversized PR-5a WIP (5a.1–5a.9 + `DetailPanel` tab-strip +
`Kebab` force-Search + Playwright witness in a single slice, well past
the 400-line per-PR review budget) is **discarded**.

- **Discarded oversized 5a WIP.** The previous monolithic Phase 5a
  enumeration (5a.1 R, 5a.2 G, 5a.3 G, 5a.4 G, 5a.5 G, 5a.6 G, 5a.7 T,
  5a.8 T, 5a.9 Refactor, all in one PR at the prior position) is replaced
  by the four-slice replan below. The discarded enumeration is retained
  only as historical context; it is **not** authoritative for the next
  code worktree.
- **5a.1 — foundation.** `src/modules/taxonomy/{domain,application,
  infrastructure}/**` only: type surface, invariants, `fetch*` functions,
  `useTaxonTree` hook; the application layer emits view-models only. No
  `Tree.tsx`, no `DetailPanel.tsx`, no `Kebab.tsx`, no `TabStrip`.
- **5a.2 — mounted `Tree` + `Breadcrumb`.** `src/modules/taxonomy/
  presentation/{Tree,Breadcrumb}.tsx`; ports the legacy
  `web/{tree,breadcrumb}.js` row layout (per-row kebab glyph reserved,
  but the menu body is **not** yet authored — the glyph is a no-op until
  5a.4); rides on PR 3c-b's `@layer components` selectors. No `DetailPanel`,
  no `Overview`, no `TabStrip`, no global activation.
- **5a.3 — `DetailPanel` + `Overview` body + local `TabStrip`.**
  `src/modules/taxonomy/presentation/{DetailPanel,OverviewTab}.tsx` plus
  a **local** `TabStrip` (`["Overview", "Search", "Folder"]`, fixed
  order, three siblings always reachable, `Overview` always visible per
  the user-selected policy); no global activation contract yet — the
  `Kebab`'s force-Search callback is wired only against this local
  component.
- **5a.4 — `Kebab` `Search online` force-Search + Chromium witness.**
  `src/modules/taxonomy/presentation/Kebab.tsx` plus the
  `tests/test_taxonomy_infra.py` extension: the per-row kebab menu gains
  the `Search online` action; the action dispatches the tab-activation
  callback that **forces the `Search` tab active** on the selected taxon
  (it MUST NOT default to `Overview`, even for top-level taxa); the
  Chromium witness is the canonical regression guard. **Regression
  assignment** (per request):
  `Archaea → Search online → Search` (top-level taxon; the current live
  regression lands on `Overview`; 5a.4 closes it).
- **Per-slice ≤ 400 lines (authored LoC, excluding regenerated
  `package-lock.json`).** Each of 5a.1, 5a.2, 5a.3, 5a.4 is sized to
  leave headroom under the 400-line per-PR review budget that Approach A
  locked 2026-09-02. The discarded WIP violated the budget; the
  four-slice replan restores it.
- **Chain positions for the next code worktree (22-child topology).** The
  next code worktree MUST use this mapping and nothing else:
  `5a.1 → 13`, `5a.2 → 14`, `5a.3 → 15`, `5a.4 → 16`, `5b → 17`,
  `5c → 18`, `6a → 19`, `6b → 20`, `6c → 21`, `3e → 22` (atomic cutover,
  still gated on G1–G6 closure). Positions 13–16 hold the 5a.1–5a.4 split;
  positions 17–22 hold every later sub-PR; the 22-child count replaces
  16. PR 4b at position 12/22 is the merge base for 5a.1. Chain topology,
  `feature-branch-chain` strategy, "tracker-only targets `develop`"
  contract, predecessor frozen status, Approach A, FastAPI/SQLite, and
  per-domain specs are unchanged.
- **`TabStrip` promotion deferred to design-system — at PR 5b.** The
  `TabStrip` primitive authored in 5a.3 stays **local** to
  `src/modules/taxonomy/presentation/` for the 5a slice. Its promotion
  to `src/modules/design-system/` (so 5b's `SearchTab` / `FolderTab` can
  consume it as a sibling primitive) is **deferred to PR 5b**, along
  with the regression guard that no taxonomy import path regresses.
- **Authoring contract.** No code edit, no rebase, no new branch in this
  addendum; the next code worktree reads this addendum as authoritative
  and re-slices 5a.1–5a.4 per the rules above. The Spanish mirror lives
  at `documents-es/.../{tasks-es.md,apply-progress-es.md,design-es.md}`
  and carries the same semantics; any drift is resolved in favour of the
  English.

---

## Addendum — 2026-09-04: Phase 5b four-slice replan (append-only)

This is a deliberate **append-only** decision addendum; the prose above for
Phase 5b (research module port + CDN pin, PR 5b at the chain position it
currently holds) is preserved verbatim. It records a docs-only supersession
that governs how the **next** code worktree re-slices PR 5b into four
reviewable sub-PRs. The previous in-line 5b enumeration (5b.1 R + 5b.2–5b.7
G + 5b.8 T + 5b.9 Refactor — nine steps inside a single ~395 LoC slice
already at the 400-line per-PR budget) is **discarded** and retained only
as historical context.

- **Discarded in-line 5b enumeration.** The previous monolithic Phase 5b
  enumeration (5b.1 R tests, 5b.2 G domain, 5b.3 G `infrastructure/api.ts`,
  5b.4 G `search-engines.js` re-export, 5b.5 G application hooks,
  5b.6 G presentation ~290 LoC, 5b.7 G app-shell `Browser` re-anchor,
  5b.8 T triangulation, 5b.9 Refactor — all in one PR at the prior
  position 17/22) is replaced by the four-slice replan below. The
  discarded enumeration is retained only as historical context; it is
  **not** authoritative for the next code worktree.
- **5b.1 — foundation (research domain + infrastructure + search-engines
  re-export).** `src/modules/research/{domain,infrastructure}/**`: typed
  `ResearchFile` / `Engine` / `FileNode` (domain); `fetchFiles(id)`,
  `fetchServe(id, rel)`, idempotent CDN `loadScriptOnce(name, src)` loader
  (`infrastructure/api.ts`); plus `search-engines.js` re-exporting
  `SEARCH_ENGINES` from PR 3d's `src/data/search-engines.js` (named export
  unchanged). No application hooks, no `FileExplorer.tsx`, no
  `FileViewer.tsx`, no `SearchTab` / `FolderTab` / `SearchLinkList`, no
  app-shell delta.
- **5b.2 — application hooks.** `src/modules/research/application/
  {useFileExplorer,useFileViewer}.ts`: the two hooks consume the typed
  `fetch*` functions from 5b.1 and emit view-models. Persisted-state keys
  (`state.explorer.search.{query, mode, hideEmpty}`) and the **200 ms
  debounce** contract are **declared here** as hook-level contracts so
  5b.3 can consume them; the `FileExplorer.tsx` / `FileViewer.tsx`
  wiring stays in 5b.3. No presentation, no `SearchTab` / `FolderTab`,
  no app-shell delta.
- **5b.3 — `FileExplorer` + `FileViewer` presentation + CDN / debounce /
  persisted-state behaviour.** `src/modules/research/presentation/
  {FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,BreadcrumbPanel,
  Banners}.tsx`: ports the legacy
  `web/{file_explorer,file_viewer,format,keymap}.js` two-pane layout;
  nine-format dispatcher with CDN-pin lazy loading (`mammoth@1.8.0`,
  `xlsx@0.18.5`, `epubjs@0.3.93`); legacy DOC + unsupported fallbacks;
  CDN failure banner `"Viewer offline — raw download unavailable"`;
  tree search with **200 ms debounce**, filter / highlight modes, and
  `state.explorer.search.{query, mode, hideEmpty}` **persisted** across
  taxon switches; meta strip `FORMAT | SIZE | ENCODING`; explorer state
  reset on taxon switch. Rides on PR 3c-c's `@layer components`
  selectors. No `SearchTab` / `FolderTab` / `SearchLinkList`, no
  app-shell delta, no `TabStrip` promotion yet.
- **5b.4 — `SearchTab` + `FolderTab` + `SearchLinkList` + global `Browser`
  re-anchor + `TabStrip` design-system promotion.**
  `src/modules/research/presentation/{SearchTab,FolderTab,
  SearchLinkList}.tsx`: `SearchTab` renders the five category sections
  (`General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents`) in
  fixed order; `FolderTab` is **separate** (per-taxon materialize
  indicator; MUST NOT be a subset of `SearchTab`); `SearchLinkList` maps
  each `Engine` to an anchor with `target="_blank"` and `rel="noopener
  noreferrer"`, resolving the URL template from `SEARCH_ENGINES`. Plus
  `src/modules/app-shell/infrastructure/page-chrome.tsx` (~30 LoC
  delta): the header `Browser` tab is re-anchored as the **global
  Research / file explorer** — opens without a `taxonId` filter;
  selecting a taxon while `Browser` is active MUST NOT scope the
  explorer to that taxon (the `data-path="browser"` /
  `data-action="nav-tab"` attribute contract is preserved). Plus the
  deferred `TabStrip` promotion from 5a.3 lands here: the local
  `TabStrip` primitive moves to `src/modules/design-system/` (sibling
  primitive), **with the regression guard** that no taxonomy import
  path regresses.
- **Per-slice ≤ 400 lines (authored LoC, excluding regenerated
  `package-lock.json`).** Each of 5b.1, 5b.2, 5b.3, 5b.4 is sized to
  leave headroom under the 400-line per-PR review budget that
  Approach A locked 2026-09-02. The discarded in-line 9-step
  enumeration violated the budget; the four-slice replan restores it.
- **Chain positions for the next code worktree (tracker + 25 children =
  26 total PRs).** The next code worktree MUST use this mapping and
  nothing else: `5b.1 → 17`, `5b.2 → 18`, `5b.3 → 19`, `5b.4 → 20`,
  `5c → 21`, `6a → 22`, `6b → 23`, `6c → 24`, `3e → 25` (atomic
  cutover, still gated on G1–G6 closure). The 25-child count replaces
  the prior 22-child count; positions 17–20 hold the 5b.1–5b.4 split,
  positions 21–25 hold every later sub-PR. PR 4b at position 12/22
  stays the merge base for 5a.1; 5b.1's merge base is the PR that
  lands immediately before position 17 in the corrected topology
  (per the next code worktree's audit). Chain topology,
  `feature-branch-chain` strategy, "tracker-only targets `develop`"
  contract, predecessor frozen status, Approach A, FastAPI/SQLite,
  and per-domain specs are unchanged.
- **`TabStrip` promotional close-out at 5b.4.** The `TabStrip`
  promotion that 5a.3's addendum deferred to PR 5b now closes at
  PR 5b.4 (not at the end of PR 5b as a whole): the local `TabStrip`
  primitive moves to `src/modules/design-system/`, and 5b.4's
  regression guard ensures no taxonomy import path regresses. After
  5b.4 lands, no further `TabStrip` work is owed from the 5a / 5b
  slices.
- **Authoring contract.** No code edit, no rebase, no new branch in
  this addendum; the next code worktree reads this addendum as
  authoritative and re-slices 5b.1–5b.4 per the rules above. The
  Spanish mirror lives at
  `documents-es/.../{tasks-es.md,apply-progress-es.md,design-es.md}`
  and carries the same semantics; any drift is resolved in favour of
  the English.
