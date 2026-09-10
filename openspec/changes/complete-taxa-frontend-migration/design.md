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
| Evidence gates | **G1, G2, G3 Tier-1, G5 PASS** (G1/G2/G3 Tier-1 carried from predecessor; G5 PASS recorded under the user-approved replacement protocol — DOMContentLoaded; both sides served through controlled HTTP; 1 warm-up + 9 measured runs per side; median aggregation with raw samples/provenance; absolute candidate−baseline tolerance ≤ 10 ms; fresh capture baseline median `3.3 ms`, candidate median `3.2 ms`, delta `−0.1 ms`, threshold `10 ms`). **G3 Tier-2, G4, and G6 are not yet passed**; the user-approved replacement protocol's failure semantics (failure stays blocked, no automatic PASS, no previous PASS carried across a failure) continue to bind every future reattempt of G5. |
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
- The 16-child chain topology (after the PR 3c sub-sequence
  replan that replaced the original single PR 3c with
  `3c-i` / `3c-ii` / `3c-iii` / `3c-iv`) is preserved;
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
| G5 (hydration baseline) | **PASS recorded — fresh capture under the user-approved replacement protocol** (`scripts/g5_close.sh` exit 0; both baseline and candidate served through controlled HTTP — `http://127.0.0.1:64809/` and `http://127.0.0.1:64824/`; observable metric `DOMContentLoaded`; 1 warm-up + 9 retained measured samples per side; per-side median aggregation with raw samples + provenance preserved; absolute (candidate − baseline) ≤ 10 ms tolerance satisfied — baseline median `3.3 ms`, candidate median `3.2 ms`, delta `−0.1 ms`, threshold `10 ms`; `baseline_source: "captured"` in `evidence/g5/status.json` and `source: "captured"` in `out/hydration-candidate.json`; `evidence/g5/status.json` records `status: "ready"`, `regression: false`, no `blocker`; `evidence/g5/regression-report.json` records `pass: true` with the full per-side samples/warmup/origin/median contract and the absolute delta). The previous 5+2 percentage/median rule (baseline 0.0 / 3.0 ms vs candidate 1.0 / 4.0 ms; `initial_paint_delta_pct: Infinity`, `interaction_latency_delta_pct: 33.33%`; comparison exit 4) is **superseded** by this fresh protocol and is retained in `apply-progress.md` change log as audit history only. **G5 is closed** under the user-approved replacement protocol. | Phase 6a — `scripts/reconstruct_hydration_baseline.py` (HTTP-served legacy fixture capture), `scripts/capture_hydration_candidate.py` (HTTP-served candidate `out/` capture), and `scripts/g5_close.sh` (the runtime harness) together produced the fresh protocol evidence recorded in `evidence/g5/{status,regression-report}.json`. The user-approved replacement protocol recorded in §"G5 — hydration baseline" below binds every future reattempt: failure stays blocked, no automatic PASS, no previous PASS carried across a failure. |
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
| `tests/test_tailwind_4_parity.py` | CSS (PR 3c-i, `:root` token slice) | Every legacy `:root` / `[data-theme="dark"]` / `--realm-*` token resolves to non-empty declaration in `globals.css::@theme`; extended in PR 3c-ii / 3c-iii / 3c-iv-keyframes / 3c-iv-viewer / 3c-iv-settings / 3c-iv-colors to cover the taxonomy / browser / Search / Folder / `fex-*` / `@keyframes` / utility-class surfaces |
| `tests/test_tailwind_4_tokens.py` | CSS (PR 3c-i) | Same surface as `test_tailwind_4_parity.py` `:root` token slice — co-located parity guard |
| `tests/test_taxonomy_styles.py` | CSS (PR 3c-ii) | Every taxonomy selector (`.taxa-tree`, `.tree-row`, `.kebab`, `.detail-panel`, `.tab-strip`, `.overview-tab`, `.breadcrumb`, …) resolves to non-empty declaration |
| `tests/test_research_styles.py` | CSS (PR 3c-iii) | Every Search / Folder / global Browser selector (`.search-tab`, `.search-category-section`, `.search-link-list`, `.search-link`, `.folder-tab`, `.header-browser-tab`, `.research-explorer`, …) resolves to non-empty declaration |
| `tests/test_design_system_purity.py` | CSS (PR 3c-iv-barrel) | Grep guard over `src/modules/design-system/`; no hex literals outside the design-system module |
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

    #### Slice 6c.0 — navigation-only sub-slice (landed, non-closing)

    The first G4 sub-slice ships the navigation-only producer. It is **not**
    a G4 PASS — it captures only one of the five reports the
    `scripts/verify_parity.py` aggregator expects, and the gate stays
    blocked until the remaining four reports land.

    - **Producer**: `tools/g4-capture/scripts/parity_navigation.mjs`
      (Playwright driver; dynamic-imported; isolated pinned
      `playwright@1.49.1` alongside the existing `lighthouse@12.2.1`
      + `chrome-launcher@1.2.1`; no root dependency changes).
    - **CLI**: `--legacy-origin`, `--candidate-origin`, `--paths`
      (comma-separated), `--output-root`, optional `--manifest`.
      Production ports are NOT baked in.
    - **Output layout**: `<outputRoot>/<UTC-timestamp>/{legacy,candidate}/
      {navigation.json,manifest.snapshot.json,run.json}`. The run
      timestamp is `YYYY-MM-DDTHH-MM-SSZ` (filename-safe; the colon
      is replaced with a hyphen because Windows rejects `:` in path
      components). The `captured_at` JSON value uses the
      seconds-precision `YYYY-MM-DDTHH:MM:SSZ` form per
      `scripts/verify_parity.py::ISO_FMT`.
    - **Schema**: `navigation.json` matches the versioned common header
      (`schema_version: "1.0.0"`, `captured_at`) plus the navigation
      record list (`paths: [{path: str, status: int}, ...]`) the
      aggregator already validates. The producer-side `schema` field
      names the slice-specific contract (`taxa.g4-parity.navigation/1`).
    - **Transport**: both sides driven through controlled HTTP
      (`http(s)://` only; `file://` and any other scheme explicitly
      rejected). Legacy and candidate MUST differ — equal sides are
      rejected so a broken candidate can never silently "pass"
      against itself.
    - **Fail-closed guards**: missing/invalid origins, origin with
      a path component, equal sides, empty `paths`, manifest path
      mismatch, 5xx or status `0` (network error, navigation
      timeout) on either side, per-path outcome drift between sides,
      and a pre-existing `<outputRoot>/<UTC-timestamp>/` directory
      (output collision guard). Each guard is exercised by a
      hermetic test in `tests/test_capture_parity.py`.
    - **Hermetic tests**: 25 tests inject a synthetic `runFn`
      (canned `(path, status)` results, throws, or drift cases) and
      a fixed `now()` so the producer runs without a real browser
      or live network. The Playwright runner is dynamic-imported
      inside `defaultRunNavigation` so the test harness stays free
      of browser deps until the real path runs.
    - **Rollback**: `git revert <6c-sha>` removes the producer,
      tests, Makefile delta, and lockfile delta. Slice 6c.1–6c.4
      stay untouched. No G4 / G3 Tier-2 / cutover status flip.

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
- **G5 closure under this protocol.** The protocol above was bound by a fresh capture (captured at `2026-09-07T15:41:38Z`; see `apply-progress.md` 2026-09-07 change log entry): `scripts/g5_close.sh` exit `0`; both baseline and candidate served through controlled HTTP (`baseline_origin: "http://127.0.0.1:64809/"`, `candidate_origin: "http://127.0.0.1:64824/"`); 1 warm-up + 9 retained measured samples per side; per-side median aggregation with raw samples + provenance preserved; absolute (candidate − baseline) ≤ 10 ms tolerance satisfied — baseline median `3.3 ms`, candidate median `3.2 ms`, delta `−0.1 ms`, threshold `10 ms`. `evidence/g5/status.json` records `status: "ready"`, `regression: false`, no `blocker`; `evidence/g5/regression-report.json` records `pass: true` with the full per-side samples/warmup/origin/median contract and the absolute delta. **G5 is closed** under this protocol. The previous 5+2 percentage/median rule (the `initial_paint_delta_pct` / `interaction_latency_delta_pct` percentage comparison; baseline medians 0.0 / 3.0 ms vs candidate 1.0 / 4.0 ms; comparison exit 4) is **superseded** by this protocol and the fresh protocol evidence; it is retained in `apply-progress.md` change log as audit history only. The failure-stays-blocked / new-request / no-PASS-carried-across-failure semantics above continue to bind every **future** reattempt of G5 — a subsequent failed run stays blocked, requires a new user request, and never carries the previous PASS across a failure.

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
> 13-child count was preserved at that revision. The full
> per-task file lists and the dependency-correctness
> rationale live in `tasks.md`; this table is the
> executive view.

> **2026-09-02 — PR 3c sub-sequence replan (this entry)**.
> After PR #144 (3a), PR #145 (3b), and PR #146 (3b
> reconcile) landed on the tracker, the original single
> PR 3c at position 3 was diagnosed as unsatisfiable: it
> claimed ~230 LoC while the legacy inline `<style>` block
> in `web/index.html` (lines 14–1972 = **1,963 lines**)
> had to be ported verbatim into Tailwind 4 (`@theme`
> for tokens, `@layer base` for the cascade, plus the
> design-system barrel). The user authorized a chained
> sub-sequence that replaces the single PR 3c with
> **four reviewable children at positions 3–6**
> (`3c-i` tokens/base/dark mode, `3c-ii` taxonomy
> tree/detail styling, `3c-iii` Search/Folder/global
> Browser styling, `3c-iv` animations/utilities + final
> CSS parity + design-system barrel), each ≤ 400 authored
> lines including tests. The remaining children are
> **renumbered** (`3d → 7`, `4a → 8`, `4b → 9`,
> `5a → 10`, `5b → 11`, `5c → 12`, `6a → 13`,
> `6b → 14`, `6c → 15`, `3e → 16`) to keep the dependency
> contract linear. **PR 3c-i bases off the tracker** (the
> `docs/complete-taxa-frontend-migration-plan` branch
> **after** PR #146 reconciliation merges, picking up
> the already-merged 3a + 3b + reconcile without an extra
> reconcile step); every later child targets its
> immediate predecessor branch. Total authored LoC rises
> from ~2,245 to ~3,485 because every legacy CSS rule is
> ported. The largest new sub-PR is **3c-i at ~390 LoC**
> (-10 LoC headroom under 400). PR 3a retains the
> regenerated-`package-lock.json` size:exception
> (generated-resolution-only) as the prior documented
> size:exception; **PR 3c-ii subsequently opens a
> second user-approved size:exception** for the
> complete taxonomy tree / detail CSS slice (actual
> implementation totals **822 insertions + 9 deletions
> = 831 LoC**, overshooting the prior `~380 LoC`
> estimate by +442 LoC and the 400-line per-PR
> review budget by +431 LoC — see the dedicated append-only
> addendum below for the authorization rationale
> and the corrected estimate; the 16-child chain is
> preserved). **Approach A, FastAPI/SQLite, the frozen
> predecessor, and the Feature Branch Chain strategy
> remain unchanged.**

> **2026-09-02 — dependency-defect fix (this revision)**.
> The apply gate's pre-flight re-audit identified a
> second dependency defect inside the corrected topology:
> the PR 3b at position 2 imported `@taxa/app-shell` (a
> module PR 4b ships at position 9/16 — *later* in the
> chain) and `./globals.css` (a file PR 3c-i ships at
> position 3/16 — *later* in the chain). At its
> `next build` witness, neither target file existed yet.
> The same audit flagged PR 3b.5's triangulation
> assertion that the build output references the typed
> store barrel path `@taxa/browser-state` — that barrel
> file does not exist until PR 4a. **PR 3b is rescoped
> to a self-contained App Router static-export
> bootstrap**: minimal semantic placeholders that
> import neither `@taxa/app-shell` nor `./globals.css`;
> the `import "./globals.css";` line moves into PR 3c-i;
> the `<AppShell>` integration into `src/app/{layout,
> page}.tsx` moves into PR 4b. PR 3b.5's unsatisfiable
> `@taxa/browser-state` reference is dropped. **The
> 13-child topology and ordering are preserved**;
> per-PR LoC budgets stay well under 400; **only the
> prior PR 3a `package-lock.json` exception remains**.
> Approach A, FastAPI/SQLite, the frozen predecessor,
> and the per-domain specs stay unchanged.

The predecessor's `tasks.md` enumerated 35 tasks across
14+ sub-PRs. The corrected chain re-slices them under
Approach A within the 400-line review budget per sub-PR.

| Position | Sub-PR | Predecessor task mapping | Scope | New / preserved | LoC budget |
| --- | --- | --- | --- | --- | --- |
| 1 / 22 | PR 3a (toolchain bootstrap) | NEW (absorbs part of original task 3.4 — `package.json` rewrite + `scripts/check-runtime.mjs`) | `package.json` dep pins (`next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, TS toolchain, `engines.node ">=20.9.0"`; legacy `autoprefixer` / `postcss` / `@tailwindcss/forms` removed; scripts `check-runtime` and `build:web`) + regenerated `package-lock.json` (the sole user-approved size exception **for this PR's regenerated lockfile**; generated-resolution-only — contains only the resolution changes required by this manifest; reviewed together with `package.json`; no unrelated lockfile churn; **PR 3c-ii is the second user-approved size:exception** for the authored LoC overshoot — see the dedicated append-only addendum below) + `scripts/check-runtime.mjs` (new, Node ≥ 20.9.0 enforcement) + `tsconfig.json` (modified in place; the predecessor already created the file at repo root in PR 2a — PR 3a extends it with the full Next.js / JSX / plugin config and the `@taxa/<capability>` path aliases; restored to its predecessor state on rollback) + `.nvmrc` (new, pin `20`) + `tests/test_toolchain_bootstrap.py` (new) + `tests/test_check_runtime.py` (new) | New | ~210 authored (≤ 400; the sole `size:exception` **for this PR's regenerated lockfile** is the regenerated `package-lock.json`; authored source/test/config work stays ≤400 — **PR 3c-ii is the second user-approved size:exception** for the authored LoC overshoot, see addendum below). **Merged as PR #144 on the tracker.** |
| 2 / 22 | PR 3b (App Router static export) | task 3.1 (rescoped) | `src/app/{layout,page}.tsx` + `next.config.mjs` + `tests/test_app_shell_render.py` (the `out/index.html` witness is satisfiable here because the toolchain is live) | New (rescoped) | ~175 (≤ 400). **Merged as PR #145 on the tracker, with PR #146 reconciliation also merged.** |
| 3 / 22 | PR 3c-i (tokens / base / dark mode) | task 3.2 (slice 1) | `src/app/globals.css` (new, `@import "tailwindcss"` + `@theme` block with every legacy `:root` token + `[data-theme="dark"]` cascade + `--realm-*` family) + `@layer base` (body / html / `main > :first-child` resets + global focus-visible selectors) + `tests/test_tailwind_4_parity.py` (`:root` token slice) | New | ~390 (≤ 400; -10 LoC headroom) |
| 4 / 22 | PR 3c-ii (taxonomy tree / detail styling) | task 3.2 (slice 2) | `src/app/globals.css` (extended, taxonomy selectors: `.tier-header`, `.tree-row`, `.rank-badge`, `.scientific-name`, `.tree-source-toggle`, `#detail-panel`, `.detail-card`, `.detail-section`, `.overview-section`, `.detail-item`, `.search-pulse`, `.detail-tabs`, `.search-icon-btn`, `.materialize-btn`, kebab, materialize modal, realm-tinted `.tree-row[data-realm="…"]` variants) + `tests/test_tailwind_4_parity.py` (taxonomy selector slice) | New | **831 actual (822 insertions + 9 deletions)** — **user-approved size:exception** (overshoot +431 LoC against the 400-line budget); prior `~380 LoC` estimate under-counted the realm-tinted variants + kebab/modal selectors + parity-test enumeration. See addendum below for authorization rationale; the 16-child chain is preserved. |
| 5 / 22 | PR 3c-iii (Search / Folder / global Browser styling) | task 3.2 (slice 3) | `src/app/globals.css` (extended, browser / search / folder selectors: `.toast`, `.search-engines-grid`, `.search-category-header`, `.search-engine-btn`, `.fex-meta-strip`, `.fex-tab-strip`, `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`, `.fex-splitter`, `.fex-row`, `.fex-tree-header`, `.fex-children`, `.fex-banner`, `.fex-empty-state`, `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`, `.fex-tree-truncated`) + `tests/test_tailwind_4_parity.py` (browser selector slice) | New | ~390 (≤ 400; -10 LoC headroom) |
| 5.5 / 22 | PR 5.5 (Tailwind 4 / PostCSS pipeline repair; landed) | NEW (post-3c-iii repair; depends on PR 3c-iii; branch `feat/complete-taxa-frontend-migration-05-5-3c-iv-predecessor`, base `feat/complete-taxa-frontend-migration-05-3c-iii`) | `package.json` (+2 deps: `@tailwindcss/postcss@^4.3.3` + `postcss@^8.5.0`) + `postcss.config.mjs` (new; ESM; registers `@tailwindcss/postcss`) + regenerated `package-lock.json` (user-approved `size:exception`; 16 new tailwind/postcss entries; total 121 packages) + `tests/test_toolchain_bootstrap.py` (updated: `REQUIRED_DEPS_PRODUCTION` expanded; `FORBIDDEN_LEGACY_DEPS` shrunk) + `tests/test_tailwind_build_pipeline.py` (new; 7 cases; real `next build` + compiled-CSS artifact assertions) | New | ~259 authored (≤ 400; −141 LoC headroom); user-approved regenerated-lockfile exception |
| 5.6 / 22 | PR 5.6 (DOM↔CSS structural parity repair; landed) | NEW (post-3c-iv-predecessor repair; depends on PR 5.5 + PR 5a + PR 5b; branch `feat/complete-taxa-frontend-migration-05-6-3c-iv-predecessor`, base `feat/complete-taxa-frontend-migration-05-5-3c-iv-predecessor`) | `src/app/globals.css` (CSS-only repair: 15 React-emitted structural hooks + 9 state selectors + 2 collapsed descendant rules + 1 kebab selector bridge + 5 visible-state / chainable / scrollable triangulation declarations; legacy `data-realm` realm-tinted + dead `.kebab-trigger` + dead `.detail-item .authorship` rules REMOVED; `.scientific-name` MOVED to `@layer components`) + `tests/test_tailwind_4_parity.py` (+37 PR 5.6 test cases; 3 pre-existing PR 3c-ii realm-tinted tests REPURPOSED to assert dead-code absence; `TAXONOMY_SELECTORS` constant updated) | New | ~1,147 across two files (491 insertions + 64 deletions in `src/app/globals.css` + 539 insertions + 53 deletions in `tests/test_tailwind_4_parity.py`); user-approved CSS-only authored-LoC exception |
| 6 / 22 | PR 3c-iv-barrel (design-system barrel + Icon/Button + purity test) | task 3.2 (slice 4-barrel) + predecessor task 3.3 design-system barrel | `src/modules/design-system/infrastructure/index.ts` (barrel + typed theme tokens) + `src/modules/design-system/presentation/{Icon.tsx,Button.tsx}` + `tests/test_design_system_purity.py` | New | ~120 (≤ 400; -280 LoC headroom) |
| 7 / 22 | PR 3c-iv-keyframes (five legacy `@keyframes` + `.animate-spin` parity) | task 3.2 (slice 4-keyframes) | `src/app/globals.css` (extended, `@keyframes detail-card-enter` / `detail-card-leave` / `search-pulse-anim` / `materialize-spin` / `toast-slide-in` rules + `.animate-spin` utility) + `tests/test_tailwind_4_parity.py` (`@keyframes` slice) | New | ~80 (≤ 400; -320 LoC headroom) |
| 8 / 22 | PR 3c-iv-viewer (image / video viewer CSS parity) | task 3.2 (slice 4-viewer) | `src/app/globals.css` (extended, `.fex-image-frame` / `.fex-image` / `.fex-image-advisory` / `.fex-video-frame` / `.fex-video-el`) + `tests/test_tailwind_4_parity.py` (viewer slice) | New | ~50 (≤ 400; -350 LoC headroom) |
| 9 / 22 | PR 3c-iv-settings (Settings view CSS parity) | task 3.2 (slice 4-settings) | `src/app/globals.css` (extended, `.settings-shell` / `.settings-header` / `.settings-list` / `.settings-row*` / `.settings-theme-toggle` / `.settings-action-btn` / `.settings-link-btn`) + `tests/test_tailwind_4_parity.py` (Settings slice) | New | ~50 (≤ 400; -350 LoC headroom) |
| 10 / 22 | PR 3c-iv-colors (Tailwind `--color-*` namespace aliases + utility parity) | task 3.2 (slice 4-colors) | `src/app/globals.css` (extended, Tailwind `--color-*` namespace aliases + legacy utility class parity) + `tests/test_tailwind_4_parity.py` (utility slice) | New | ~80 (≤ 400; -320 LoC headroom) |
| 11 / 22 | PR 3d (Makefile/mount) | task 3.4 (Makefile portion) + task 3.6 + 3.7 (WEB_DIR repoint + AC-21) | `Makefile::api` rewrite (runs `check-runtime.mjs` → `npm run build:web` → `uvicorn … --port 8765`; legacy `make css` becomes no-op shim) + `api/server.py:54` WEB_DIR repoint + `web/search_urls.js` → `src/data/search-engines.js` + AC-21 `open()` update + `tests/test_make_api_build.py` + `tests/test_static_mount.py` | New (fused) | ~240 (≤ 400) |
| 12 / 22 | PR 4a | task 4.1 + 4.2 | `src/modules/browser-state/{domain/keys.ts, infrastructure/store.ts, index.ts}` + 4 read + 4 write sites inside `useEffect` | New | ~180 (≤ 400) |
| 13 / 22 | PR 4b | task 4.3 + 4.4 | `useSyncExternalStore` behind `mounted` flag + Playwright zero-hydration-warnings assertion | New | ~90 (≤ 400) |
| 14 / 22 | PR 5a | task 5.1 + 5.2 + 5.3 | `src/modules/taxonomy/{domain,application,infrastructure,presentation}` + port `web/{tree,detail,breadcrumb}.js` | New | ~280 (≤ 400) |
| 15 / 22 | PR 5b | task 5.4 + 5.5 + 5.6 | `src/modules/research/{domain,application,infrastructure,presentation}` + port `web/{file_explorer,file_viewer,format,keymap}.js` + CDN pin | New | ~360 (≤ 400) |
| 16 / 22 | PR 5c | task 5.7 + 5.8 + 5.9 | Playwright + e2e selector updates + `data-*` contract preservation + delete `web/*.{html,js,css}` + `tailwind.config.js` | New | ~200 (≤ 400) |
| 17–19 / 22 | Phase 6a / 6b / 6c (validation) | NEW | G5 baseline reconstruction / G6 cutover rehearsal / G4 Playwright + Lighthouse parity measurement (validation work; no new `web/**` or `api/server.py` route handlers or `extension/**`) | New (measurement) | ~190 + ~120 measurement (≤ 400 each) |
| 20 / 22 | PR 3e (cutover) | atomic cutover unit | The four-set release + cutover-manifest Tier-2 flip + G3 Tier-2 verifier rerun + status-footer flips for G4 / G5 / G6 closure | Atomic | ~120 (≤ 400) |

> **2026-09-10 — 4a / 4b marker cross-reference (append-only
> reconciliation addendum, kept from upstream tracker
> `3a2e32a`)**. The 22-child slice table above is preserved
> verbatim as this branch's authoritative sub-PR plan (the
> 5.5 / 5.6 fractional repair children + the 3c-iv
> five-slice replan that this branch owns). In parallel,
> **PR #208** =
> `feat/complete-taxa-frontend-migration-12-4a-marker`
> and **PR #209** =
> `feat/complete-taxa-frontend-migration-13-4b-marker`
> merged into the upstream tracker as **documentation /
> verification markers**, not as the PR 4a / PR 4b
> candidate work units. The marker branches ship one
> spec-subset / spec-superset triangulation test each
> (238 LoC for #208, 399 LoC for #209); the PR 4a / PR
> 4b candidate branches
> (`feat/complete-taxa-frontend-migration-08-4a` /
> `feat/complete-taxa-frontend-migration-09-4b`)
> remain reconstruction pending, with all Phase 4a /
> Phase 4b source files (`src/modules/browser-state/**`
> for 4a; `src/modules/app-shell/**` +
> `src/app/{layout,page}.tsx` AppShell integration
> delta for 4b) NOT authored by the marker PRs and
> NOT delivered to `develop`. The marker branch
> position numbers (12 / 13) belong to the marker
> chain; on this branch the same positions (12 / 22
> and 13 / 22 in the 22-child plan above) are owned by
> the PR 4a / PR 4b **candidate** branches. The
> candidate-chain positions (8/16 / 9/16) referenced
> in the upstream tracker's 16-child predecessor view
> are preserved verbatim. LoC budgets, the
> dependency-defect-fix contract, the chain topology,
> and the sub-PR slicing on this branch are unchanged.

### Dependency order (corrective plan revision + PR 3c sub-sequence replan contract)

- **PR 3a — toolchain bootstrap**. Self-contained.
- **PR 3b — App Router static export** depends on 3a
  (deps installed + Node ≥ 20.9.0 contract).
- **PR 3c-i — tokens / base / dark mode** depends on
  3a (`tailwindcss@^4` installed). **Bases off the
  tracker after PR #146 lands**, picking up the
  already-merged 3a + 3b + reconcile.
- **PR 3c-ii — taxonomy tree / detail styling** depends
  on 3c-i (token + base layer live, so every selector
  in this slice resolves `var(--token)` references).
- **PR 3c-iii — Search / Folder / global Browser styling**
  depends on 3c-ii (taxonomy selectors live; browser
  selectors resolve).
- **PR 3c-iv-barrel — design-system barrel + Icon/Button + purity test** depends on the **PR 5.6 DOM↔CSS structural parity repair predecessor** (the `@tailwindcss/postcss` expansion + the React-emitted structural hooks are in place so the design-system module can land cleanly). **First child of the 3c-iv sub-sequence** (per the 3c-iv five-slice replan addendum).
- **PR 3c-iv-keyframes — five legacy `@keyframes` + `.animate-spin` parity** depends on 3c-iv-barrel (design-system module + Icon/Button primitives loaded so the keyframe rules reference the live design-system surface).
- **PR 3c-iv-viewer — image / video viewer CSS parity** depends on 3c-iv-keyframes (`@keyframes` + `.animate-spin` live so the viewer-frame `animation:` references resolve).
- **PR 3c-iv-settings — Settings view CSS parity** depends on 3c-iv-viewer (viewer frames live so the Settings view reuses the same token surface).
- **PR 3c-iv-colors — Tailwind `--color-*` namespace aliases + utility parity** depends on 3c-iv-settings (Settings selectors live, sharing the `--color-*` consumer surface). **Terminal child of the 3c-iv sub-sequence** — every downstream consumer depends on the colors child (the complete Tailwind 4 cascade).
- **PR 3d — Makefile/mount** depends on 3c-iv-colors (full Tailwind 4 cascade ported so `next build` produces a complete CSS payload with every `--color-*` alias resolving) and 3b (App Router produces `out/index.html` when `next build` runs). **Per the 3c-iv five-slice replan, final CSS consumers depend on colors.**
- **PR 4a — typed store** depends on 3c-iv-barrel (design-system module + Icon/Button primitives loaded). **Per the 3c-iv five-slice replan, design-system consumers depend on barrel — not on the former single PR 3c-iv.**

  > **2026-09-10 — 4a marker cross-reference (append-only
  > reconciliation addendum, kept from upstream tracker
  > `3a2e32a`)**. PR **#208** =
  > `feat/complete-taxa-frontend-migration-12-4a-marker`
  > merged into the upstream tracker as a **documentation /
  > verification marker** for PR 4a. PR #208 ships a
  > single spec-subset triangulation test
  > (`tests/test_browser_state_keys_4a_spec_subset.py`,
  > 238 LoC); it does NOT author the typed store, the
  > 4 read + 4 write sites, or the store barrel, and
  > it does NOT consume the 8/16 candidate-chain
  > position in the upstream tracker's 16-child
  > predecessor view. The candidate PR 4a branch
  > (`feat/complete-taxa-frontend-migration-08-4a`)
  > stays reconstruction pending. On this branch the
  > same position (12 / 22 in the 22-child plan above)
  > is owned by the PR 4a candidate branch (typed
  > store + 4 read + 4 write sites + store barrel).
  > The marker branch and the candidate branch are
  > different branches with different scopes; both
  > reconciliation facts are preserved verbatim.

- **PR 4b — hydration guard** depends on 4a (store
  available) and 3b (AppShell host + `mounted` flag
  slot).

  > **2026-09-10 — 4b marker cross-reference (append-only
  > reconciliation addendum, kept from upstream tracker
  > `3a2e32a`)**. PR **#209** =
  > `feat/complete-taxa-frontend-migration-13-4b-marker`
  > merged into the upstream tracker as a **documentation /
  > verification marker** for PR 4b. PR #209 ships a
  > single spec-superset triangulation test
  > (`tests/test_hydration_app_shell_superset_4b_spec_subset.py`,
  > 399 LoC); it does NOT author the AppShell module,
  > the page-chrome module, the hydration guard, or
  > the `<AppShell>` integration into
  > `src/app/{layout,page}.tsx`, and it does NOT
  > consume the 9/16 candidate-chain position in the
  > upstream tracker's 16-child predecessor view. The
  > candidate PR 4b branch
  > (`feat/complete-taxa-frontend-migration-09-4b`)
  > stays reconstruction pending. On this branch the
  > same position (13 / 22 in the 22-child plan above)
  > is owned by the PR 4b candidate branch
  > (`useSyncExternalStore` + `mounted` flag +
  > Playwright zero-hydration-warnings assertion).
  > The dependency-defect-fix contract (PR 4b owns
  > both the `app-shell` module **and** the App Router
  > host integration) is preserved verbatim on both
  > the upstream tracker and this branch.
- **PR 5a — taxonomy port** depends on 4b
  (hydration-safe state read) and 3c-ii (the taxonomy
  selectors are in place — the taxonomy
  presentation layer rides on PR 3c-ii's CSS).
- **PR 5b — research port + CDN pin** depends on 5a
  (taxonomy state read shared), 3d
  (`src/data/search-engines.js` for the `Engine` named
  export), and 3c-iii (the Search / Folder / global
  Browser selectors are in place — the research
  presentation layer rides on PR 3c-iii's CSS).
- **PR 5c — e2e + delete legacy** depends on 5b (all UI
  components live) and 3c-iv-colors (the final Tailwind 4
  parity test is on disk; the 1,963-line legacy inline
  CSS has been migrated into `src/app/globals.css`
  end-to-end via the five-child 3c-iv sub-sequence and
  is ready to be retired at PR 5c; **per the 3c-iv
  five-slice replan, final CSS consumers depend on
  colors, NOT on the former single PR 3c-iv**).
- **PR 6a / 6b / 6c — validation** depends on 5c.
- **PR 3e — atomic cutover** depends on all six gates
  green.

The PR 3e cutover sub-PR ships **only when** all six
gates are green; the apply worker is gated on the G4 / G5
/ G6 closure sub-PRs (3e itself lands after the closure
verifications).

---

## Affected files (executive view)

> **Corrective plan revision of 2026-09-02 + PR 3c
> sub-sequence replan**: the PR labels in this table
> reflect the reordered chain (toolchain bootstrap at
> position 1, App Router static export at position 2,
> **3c-i tokens/base/dark mode at position 3, 3c-ii
> taxonomy tree/detail styling at position 4, 3c-iii
> Search/Folder/global Browser styling at position 5,
> 3c-iv animations/utilities + final CSS parity + design-
> system barrel at position 6**, fused Makefile/mount at
> position 7, with the later children renumbered through
> 16).

| Area | Action | Files |
| --- | --- | --- |
| `web/index.html` | Deleted at activation (PR 5c) | `web/index.html` |
| `web/*.js` (18 modules) | Deleted at activation (PR 5c) | `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` |
| `web/index.css` | Deleted at activation (PR 5c) | `web/index.css` |
| `web/dist/tailwind.css` | Regenerated by reverted `make css` after rollback; not part of new build | `web/dist/tailwind.css` |
| `tailwind.config.js` | Deleted at activation (PR 5c) | `tailwind.config.js` |
| `package.json` | Modified (PR 3a, toolchain bootstrap) — `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, TS toolchain, `engines.node ">=20.9.0"`; removes `autoprefixer`, `postcss`, `@tailwindcss/forms`; adds `scripts.check-runtime` and `scripts.build:web` | `package.json` |
| `package-lock.json` | Regenerated (PR 3a, toolchain bootstrap) — sole user-approved size exception **for the regenerated lockfile**; generated-resolution-only (no hand-authored content); contains only the resolution changes required by this manifest; reviewed together with `package.json`; no unrelated lockfile churn. **The change carries a second user-approved size:exception on PR 3c-ii** (831 actual vs. ~380 LoC estimate; overshoot +431 against the 400-line budget; see the dedicated append-only addendum below for authorization rationale) | `package-lock.json` |
| `tsconfig.json` | Modified in place (PR 3a, toolchain bootstrap) — full Next.js / JSX / plugin config layered on top of the predecessor's strict-mode + `@taxa/<capability>` path-alias scaffold (the predecessor already created the file at repo root in PR 2a; restored to its predecessor state on rollback) | `tsconfig.json` |
| `.nvmrc` | Created (PR 3a, toolchain bootstrap) — pin `20` | `.nvmrc` |
| `scripts/check-runtime.mjs` | Created (PR 3a, toolchain bootstrap) — Node ≥ 20.9.0 enforcement | new |
| `tests/test_toolchain_bootstrap.py` | Created (PR 3a, toolchain bootstrap) — verifies deps, engines.node, scripts, path aliases, .nvmrc | new |
| `tests/test_check_runtime.py` | Created (PR 3a, toolchain bootstrap) — verifies the Node ≥ 20.9.0 floor exit codes | new |
| `src/app/{layout,page}.tsx` | Created (PR 3b, App Router self-contained static-export bootstrap) — **minimal semantic placeholder body**; **does NOT mount `<AppShell>`** (lands in PR 4b) **and does NOT import `./globals.css`** (lands in PR 3c-i). PR 4b later modifies these to integrate `<AppShell>` from `@taxa/app-shell` | new (3b) + modified (4b) |
| `next.config.mjs` | Created (PR 3b, App Router static export) — `output: "export"`, `images.unoptimized: true`, `trailingSlash: false`, `reactStrictMode: true` | new |
| `tests/test_app_shell_render.py` | Created (PR 3b, App Router static export) — reads `out/index.html` after `next build` | new |
| `src/app/globals.css` | Created + extended across the 3c sub-sequence: **PR 3c-i** (new, ~250 LoC for `:root` tokens + `[data-theme="dark"]` cascade + `--realm-*` family + body / html resets + global focus-visible selectors), **PR 3c-ii** (extended, **overshoots the prior `~280 LoC` estimate — actual implementation totals 822 insertions + 9 deletions (831 LoC) across this PR's `globals.css` slice + the `tests/test_tailwind_4_parity.py` taxonomy selector slice combined; user-approved size:exception for the complete taxonomy tree / detail CSS slice, see the dedicated addendum below for the authorization rationale**), **PR 3c-iii** (extended, ~330 LoC for Search / Folder / global Browser / file explorer / CSV / JSON selectors), **PR 3c-iv-keyframes** (extended, ~50 LoC for five `@keyframes` rules + `.animate-spin` utility), **PR 3c-iv-viewer** (extended, ~30 LoC for image / video viewer frames), **PR 3c-iv-settings** (extended, ~30 LoC for Settings view selectors), **PR 3c-iv-colors** (extended, ~60 LoC for Tailwind `--color-*` namespace aliases). Total ~1,510 LoC; the file is the receiver of the full 1,963-line legacy inline `<style>` port. | new (file), extended (3c-ii / 3c-iii / 3c-iv-keyframes / 3c-iv-viewer / 3c-iv-settings / 3c-iv-colors) |
| `src/modules/design-system/{infrastructure/index.ts, presentation/Icon.tsx, presentation/Button.tsx}` | Created (PR 3c-iv-barrel, design-system barrel + Icon/Button primitives + purity test) — design-system barrel `<Icon>` (Material Symbols Outlined glyph wrapper) + `<Button>` layout primitive | new |
| `tests/test_tailwind_4_parity.py` | Created (PR 3c-i) + extended in PR 3c-ii / 3c-iii / 3c-iv-keyframes / 3c-iv-viewer / 3c-iv-settings / 3c-iv-colors. The test enumerates every legacy `:root` token, every `var(--name)` reference, every `--realm-*` selector, every `@keyframes` rule, every legacy utility class, every taxonomy / browser / search / folder / viewer selector, and every Settings / viewer frame selector, asserting non-empty declarations in `src/app/globals.css` and `out/_next/static/chunks/*.css`. | new (file), extended (3c-ii / 3c-iii / 3c-iv-keyframes / 3c-iv-viewer / 3c-iv-settings / 3c-iv-colors) |
| `tests/test_design_system_purity.py` | Created (PR 3c-iv-barrel, design-system barrel + Icon/Button primitives + purity test) — hex literal grep guard across `src/` | new |
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
| `tests/test_browser_state_keys_4a_spec_subset.py` | Created (PR **#208**, **4a marker** — documentation / verification marker, NOT the candidate PR 4a) — spec-subset triangulation pinning the planned 4a contract | new |
| `tests/test_hydration_app_shell_superset_4b_spec_subset.py` | Created (PR **#209**, **4b marker** — documentation / verification marker, NOT the candidate PR 4b) — spec-superset triangulation pinning the planned 4b contract | new |
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
| G5 current median/percentage protocol is unstable at 0–4 ms; comparable real captures produced **ready / blocked / blocked** verdicts with ±1 ms movement. | **Retired / superseded** | The Phase 6a risk disposition was a methodological-exception request that has been **superseded by the user-approved replacement G5 protocol** recorded in §"G5 — hydration baseline" below AND bound by the fresh capture under that protocol. The fresh protocol evidence (`DOMContentLoaded` observable; both sides served through controlled HTTP — `http://127.0.0.1:64809/` and `http://127.0.0.1:64824/`; 1 warm-up + 9 retained measured samples per side; per-side median aggregation with raw samples + provenance preserved; absolute (candidate − baseline) ≤ 10 ms tolerance satisfied; baseline median `3.3 ms`, candidate median `3.2 ms`, delta `−0.1 ms`, threshold `10 ms`) is recorded in `openspec/changes/complete-taxa-frontend-migration/evidence/g5/{status,regression-report}.json`. G5 is **PASS recorded / closed** under the user-approved replacement protocol; the legacy 5+2 percentage/median rule is retained in `apply-progress.md` change log as audit history only. |
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
baseline) **PASS recorded / closed — fresh capture under the
user-approved replacement protocol** (`scripts/g5_close.sh` exit 0;
both baseline and candidate served through controlled HTTP —
`http://127.0.0.1:64809/` and `http://127.0.0.1:64824/`; observable
metric `DOMContentLoaded`; 1 warm-up + 9 retained measured samples per
side; per-side median aggregation with raw samples + provenance
preserved; absolute (candidate − baseline) ≤ 10 ms tolerance
satisfied — baseline median `3.3 ms`, candidate median `3.2 ms`,
delta `−0.1 ms`, threshold `10 ms`; `baseline_source: "captured"` in
`evidence/g5/status.json` and `source: "captured"` in
`out/hydration-candidate.json`; `evidence/g5/status.json`
records `status: "ready"`, `regression: false`, no `blocker`;
`evidence/g5/regression-report.json` records `pass: true` with the
full per-side samples/warmup/origin/median contract and the absolute
delta). The legacy 5+2 percentage/median rule (the previous baseline
0.0 / 3.0 ms vs candidate 1.0 / 4.0 ms; regression on both axes;
comparison exit 4) is **superseded** by this fresh protocol and is
retained in `apply-progress.md` change log as audit history only. The
methodological-exception **request** recorded in prior change log
entries is superseded by the user-approved replacement protocol and
the fresh protocol evidence. G5 remains subject to the user-approved
replacement protocol: failure stays blocked, no automatic PASS, no
previous PASS carried across a failure. G6 (cutover
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
  5a.4); rides on PR 3c-ii's taxonomy selectors. No `DetailPanel`,
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
  reset on taxon switch. Rides on PR 3c-iii's Search / Folder / global Browser selectors
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

---

## Addendum — 2026-09-07: PR 5c.1a typed browser-state foundation (landed); 5c.1b + 5c.2 deferred (append-only)

- **PR 5c.1a landed (this entry, supersedes prior Phase 5c sub-PR enumeration for the next code worktree)**. The seven-PR Phase 5c enumeration (`5c.1 R / 5c.2 R / 5c.3 G / 5c.4 G / 5c.5 T / 5c.6 G / 5c.7 Refactor`) collapses into a single **`5c.1b` (deferred)** UI slice and the typed foundation slice `5c.1a` (recorded as **landed**). `5c.1a` adds the `versionBannerDismissed: "taxa.settings.versionBannerDismissed"` boolean key + `col | worms | freshwater` TreeSource to `domain/keys.ts` and restores the **5 + 5** `getItem(` / `setItem(` storage-call contract in `infrastructure/store.ts`. Full evidence lives in `apply-progress.md` §Change log entry "2026-09-07 — PR 5c.1a: typed browser-state foundation landed"; `5c.1b` and `5c.2` are deferred. **G4 remains blocked.** Spanish mirror carries the same semantics; any drift is resolved in favour of the English. No React, no E2E tests, no source selectors, no research features, no build outputs, no commit/push.

## Addendum — 2026-09-07: PR 5c.1b-A tree-source UI + nav/breadcrumb ids (landed); 5c.1b-B + 5c.2 deferred (append-only)

- **PR 5c.1b-A landed (this entry, splits the prior deferred `5c.1b` into A landed + B deferred)**. The `5c.1b` UI slice splits into **`5c.1b-A` (landed)** + **`5c.1b-B` (deferred)** + **`5c.2` (deferred)**. `5c.1b-A` lands the tree-source UI in `page-chrome.tsx` (`#tree-source-toggle` with three `data-tree-source="col|worms|freshwater"` buttons, `aria-pressed` per button, `setTreeSource` on click), the React ids on existing nav buttons (`nav-browser` / `nav-classification` / `nav-settings`) and Breadcrumb (`id="breadcrumb"`), and the single-store context wire (`useBrowserStateStore` exported from `@taxa/app-shell`; `page.tsx` subscribes via `useSyncExternalStore`; `source: "col"` is no longer hard-coded). No `domain/keys.ts` / `infrastructure/store.ts` change. `5c.1b-B` (VersionBanner render + panel close/sticky work + tree-source hydration polish) and `5c.2` (research / search / folder wiring) are deferred. **G4 / G3 Tier-2 / cutover remain blocked.** Spanish mirror carries the same semantics; any drift is resolved in favour of the English. No VersionBanner render, no panel close/sticky work, no Folder/Search research behaviour change, no G4 tests, no browser capture, no commit/push.

## Addendum — 2026-09-07: PR 5c.1b-B VersionBanner render + panel close/sticky work (landed); 5c.2 deferred (append-only)

- **PR 5c.1b-B landed (this entry, splits the prior deferred `5c.1b-B` into a landed slice, `5c.2` still deferred)**. `5c.1b-B` lands (a) the mounted-gated `VersionBanner` in `src/modules/app-shell/presentation/VersionBanner.tsx` — reads `/api/health` only AFTER `useMounted()` flips, fails closed on unavailable/malformed health data (`typeof X !== "number"` guards), preserves the legacy DOM ids `version-banner` / `version-banner-actual` / `version-banner-expected`, persists dismissals via the typed `store.setVersionBannerDismissed(true)`, and reuses the existing `data-slot="banner-host"` slot without duplicating `createBrowserStateStore()`; (b) the `DetailPanel` close/sticky contract in `src/modules/taxonomy/presentation/DetailPanel.tsx` — `id="detail-panel"` on the root aside, the `data-action="close-detail"` close button wired to a new `detailOpen` state that the next `forceOpenSearch` bump resets to `true` (closes the legacy silent-no-op regression), and the `.detail-header` / `.detail-tabs` structural hooks; (c) the minimal sticky-CSS contract in `src/app/globals.css` — `position: sticky` + `top:` + `z-index` on both `.detail-header` and `.detail-tabs` inside the existing `.detail-panel` scroll viewport, plus a minimal `#version-banner` rule (all colors route through `var(--…)` tokens; no raw hex literals). `page-chrome.tsx` mounts `<VersionBanner />` in place of the prior static banner host (consumed via a sibling-module import, not a barrel re-export — the public `app-shell` barrel stays untouched in this slice). No `domain/keys.ts` / `infrastructure/store.ts` change. `5c.2` (research / search / folder wiring) is deferred. **G4 / G3 Tier-2 / cutover remain blocked.** Spanish mirror carries the same semantics; any drift is resolved in favour of the English. No Folder/Search research behaviour change, no G4 tests, no browser capture, no build outputs, no commit/push.

## Addendum — 2026-09-07: PR 5c.2-A search-engine contract alignment (landed); FileExplorer global mount + selector/harness updates + legacy deletion + G4 / G3 Tier-2 / cutover still deferred (append-only)

- **PR 5c.2-A landed (this entry, splits the prior deferred `5c.2` into A landed + remainder deferred)**. `5c.2-A` aligns `api/server.py::_SEARCH_ENGINES` and `src/data/search-engines.js::SEARCH_ENGINES` to the canonical 14-engine roster (google, imagen, documentos, pdf, wikipedia, bhl, researchgate, plos, academia, scielo, scholar, youtube, zootaxa, scribd) in the same ordered fields; the three retired `general` social/share entries (`threads_acipenser`, `facebook_acipenser_baerii`, `threads_shared_post`) are removed from both mirrors. `tests/test_smoke.py::test_search_engine_contract` is extended (strict TDD) to pin the exact count (14) and the ordered key list in addition to the existing key/label/with_authorship parity check; `tests/test_smoke.py::test_fixed_search_destinations_are_returned_unchanged` is retired (its three assertions target engines no longer in the roster). `5c.2` (FileExplorer global mount, e2e selector/harness updates, `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion) is still deferred. **G4 / G3 Tier-2 / cutover remain blocked.** Spanish mirror carries the same semantics; any drift is resolved in favour of the English. No Folder/Search research behaviour change, no `domain/keys.ts` / `infrastructure/store.ts` change, no e2e selector updates, no legacy deletion, no G4 tests, no browser capture, no build outputs, no commit/push.

## Addendum — 2026-09-07: PR 5c.2-B.1a React E2E harness scaffold (landed, isolated workspace only); capture driver + fixture/export servers + hermetic harness tests + selector modernization + legacy deletion + G4 / G3 Tier-2 / cutover still deferred (append-only)

- **PR 5c.2-B.1a landed (this entry, splits the prior deferred `5c.2` into A landed + B.1a landed + remainder deferred)**. `5c.2-B.1a` lands an **isolated private workspace** at `tools/react-e2e-harness/` (no edit surface in `src/`, no API changes, no FastAPI/SQLite/extension changes, no `domain/keys.ts` / `infrastructure/store.ts` change, no production `next.config.mjs` / `package.json` change, no G4 capture, no legacy deletion). The workspace pins Next 16.3.3, React 19.2.8, ReactDOM 19.2.8, `@playwright/test` 1.56.0, and Node ≥ 20.9.0; `npm install` generates `tools/react-e2e-harness/package-lock.json` (the user-approved generated-lockfile size exception for this isolated workspace only — authored source/docs remain ≤ 400 diff lines; total authored = 245 LoC across `package.json` + `next.config.mjs` + `tsconfig.json` + `app/layout.tsx` + `app/page.tsx`). `next.config.mjs` mirrors the G2 static-export flags (`output: "export"`, `images.unoptimized: true`, `trailingSlash: false`, `reactStrictMode: true`); `app/layout.tsx` is a minimal semantic harness title (no AppShell / chrome replica; no `import "./globals.css"`; no Raleway preload); `app/page.tsx` mounts `FileExplorer` directly from `@taxa/research` against a deterministic synthetic non-null taxon id (`1`) and a `baseUrl` read only from the public harness env var `NEXT_PUBLIC_HARNESS_BASE_URL` (default `http://127.0.0.1:8765`). `tsconfig.json` declares safe `@taxa/*` path aliases that resolve to `../../src/modules/*/index.ts` so the live research barrel compiles against the harness without a barrel re-export. **No test surface** in this sub-slice — the strict-TDD contract for `5c.2-B.1a` is satisfied by (a) a RED pre-build negative source-contract check proving the harness app does not yet exist, then (b) a GREEN `npm ci` (exit `0`, 32 packages) + `npm run build` (exit `0`, `out/index.html` rendered with `<title>Taxa React E2E Harness — FileExplorer mount</title>`, `data-harness-surface="file-explorer"`, `data-harness-taxon-id="1"`, and the live `FileExplorer` mount rendering its `data-explorer="loading"` initial state with `aria-busy="true"`). The remainder of `5c.2-B` (capture driver, fixture/export servers, hermetic harness tests, e2e selector modernization on the new component tree, `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion) is still deferred. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by this scaffold landing** (no Playwright + Lighthouse verifier authored; only the isolated workspace + static-export green-path landed). Spanish mirror carries the same semantics; any drift is resolved in favour of the English.

## Addendum — 2026-09-08: PR 5c.2-B.1b-i React export capture CLI + Chromium runner (landed, isolated workspace only); fixture/export servers + hermetic tests + selector modernization + legacy deletion + G4 / G3 Tier-2 / cutover still deferred (append-only)

- **PR 5c.2-B.1b-i landed (this entry, splits the prior deferred `5c.2-B` remainder into B.1b-i landed + narrower remainder deferred)**. `5c.2-B.1b-i` lands the **capture CLI + Chromium navigation runner** in the isolated `tools/react-e2e-harness/` workspace only (no edit surface in `src/`, no API/FastAPI/SQLite/extension changes, no `domain/keys.ts` / `infrastructure/store.ts` change, no production `next.config.mjs` / `package.json` change, no G4 capture, no legacy deletion). Files: `tools/react-e2e-harness/scripts/run.mjs` (CLI; requires `--origin` + `--output-root`; rejects `file://` / non-http(s) / origin paths / missing flags / output collisions; dynamic-injects `runFn` from `./chromium-driver.mjs`; writes atomic timestamped `evidence.json` only on successful capture — fail-closed) + `tools/react-e2e-harness/scripts/chromium-driver.mjs` (Chromium navigation; dynamic-imports `playwright` from the local `node_modules/`; asserts the locked React data contracts `data-harness-root` + `data-harness-surface` + non-null `data-harness-taxon-id` + `[data-explorer="ready"]` + both `[data-pane]` slots + `input[data-search-input]` + ≥1 `[data-file-path]`; captures concise `pageerror` / `console.error` / navigation / assertions trace; closes the browser reliably via `finally`) + `tools/react-e2e-harness/package.json` (+3 lines; `scripts.capture = "node scripts/run.mjs"`) + `tools/react-e2e-harness/README.md` (concise caller-provided-origin usage + fail-closed list + deferral list). **No hard-coded default port** baked into the CLI; caller provides both flags. **No test surface** in this sub-slice — strict-TDD contract satisfied by (a) RED pre-implementation source-contract check (`scripts/run.mjs` + `scripts/chromium-driver.mjs` + `scripts/` directory absent), then (b) GREEN `node --check` on both modules + CLI `missing --origin` / `missing --output-root` / `file://` / origin-path rejection exits `1`. Dynamic `runFn` + `now()` injection on `capture()` keeps the surface suitable for a later hermetic test slice; no browser runtime success is claimed (fixture/export servers are deferred). The remainder of `5c.2-B` (fixture API server + export HTTP server orchestration + Makefile target + hermetic driver tests + e2e selector modernization on the new component tree + `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion) is still deferred. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by the capture CLI landing** (only the CLI + Chromium runner shipped; no G4 aggregation; no `scripts/verify_parity.py` end-to-end flip). Spanish mirror carries the same semantics; any drift is resolved in favour of the English.

## Addendum — 2026-09-09: PR 5c.2-B.1b-ii-a hermetic React FileExplorer fixture API (landed, isolated workspace only); static export HTTP server + composition slice + hermetic driver tests + selector modernization + legacy deletion + G4 / G3 Tier-2 / cutover still deferred (append-only)

- **PR 5c.2-B.1b-ii-a landed (this entry, splits the prior deferred `5c.2-B` remainder into B.1b-i landed + B.1b-ii-a landed + narrower remainder deferred)**. `5c.2-B.1b-ii-a` lands the **hermetic in-process Node fixture API** in the isolated `tools/react-e2e-harness/` workspace only (no edit surface in `src/`, no API/FastAPI/SQLite/extension changes, no `domain/keys.ts` / `infrastructure/store.ts` change, no production `next.config.mjs` / `package.json` change, no G4 capture, no legacy deletion). File: `tools/react-e2e-harness/scripts/fixture-server.mjs` (pure Node built-ins `node:http` + `node:buffer`; zero npm deps; zero harness `package.json` delta; CLI `--port N` / `--host H` OR `--port 0` OS-assigned; never hard-coded 8765). Mirrors the production FastAPI shape: `GET /api/taxon/1/files` returns the typed `FilesEnvelope` (`exists`, `taxon_id`, `taxon_name`, `taxon_path`, `filesystem_path`, `subpath`, `root: WireFileNode`); `GET /api/taxon/1/files/serve?path=<encoded>` returns the file body + matching `Content-Type` (mirrors `api/server.py::_CONTENT_TYPE_BY_EXT`) + `Content-Disposition: inline; filename="<basename>"`. Deterministic in-memory fixture corpus: `index.html`, `notes.md`, `readme.txt`, `paper.pdf` (each format with the matching production Content-Type), and a recursive `Papers/lynx.pdf` to exercise `_walk_tree` recursion. `safeResolve()` mirrors `api/server.py::_safe_resolve()` step-for-step: reject empty / NUL / malformed-percent / absolute / `..` / `.`; explicit segment join so mixed separators cannot escape; strict-parent check. Only taxon id `1` is served; unknown routes / unknown taxon / wrong method / URL-decoded traversal all rejected fail-closed (400 / 404 / 405). Importable via `startServer({port, host}) → {schema, taxonId, host, port, baseUrl, server, close}` so the composition slice (5c.2-B.1b-ii-b) can spawn/teardown in-process. Test surface: `tests/test_5c_2_b_react_harness.py` (21 hermetic tests; `subprocess` Node + Python `urllib`; no Playwright / Chromium / FastAPI / SQLite / network). Covers source contract (file exists, exports `startServer`, `node --check`, zero `npm:` deps); start/stop lifecycle (caller-chosen port honoured, OS-assigned ports unique, `SIGTERM` frees the listener); envelope shape (every `FilesEnvelope` field, folders-before-files sort, all four fixture extensions, recursive subfolder, wire-shape on every file); four-format content types + `Content-Disposition` + `%PDF-` magic; traversal fail-closed (`..`, `../../etc/passwd`, `/etc/passwd`, URL-encoded `%2E%2E%2Fpasswd`); unknown-file 404 inside the root; unknown-taxon 404; unknown-route 404; non-GET 405. **Strict-TDD**: **RED** = pre-implementation source-contract check (`fixture-server.mjs` absent) FAILED on pre-`5c.2-B.1b-ii-a` source. **GREEN** = `node --check` exits `0` + all 21 hermetic tests pass. No production source/API change; no `domain/keys.ts` / `infrastructure/store.ts` change; no `web/*.{html,js,css}` legacy deletion; no G4 aggregation; no `tools/g4-capture/**` change; no FastAPI/SQLite/extension change. The remainder of `5c.2-B` (static export HTTP server orchestration + composition slice + Makefile target + hermetic capture-driver tests + e2e selector modernization on the new component tree + `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion) is still deferred. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by the fixture API landing** (no `scripts/verify_parity.py` end-to-end flip; no production build artifact; no browser runtime success). Spanish mirror carries the same semantics; any drift is resolved in favour of the English.

## Addendum — 2026-09-09: PR 5c.2-B.1b-ii-b hermetic static-export HTTP server (landed, isolated workspace only); composition slice + hermetic driver tests + selector modernization + legacy deletion + G4 / G3 Tier-2 / cutover still deferred (append-only)

- **PR 5c.2-B.1b-ii-b landed (this entry, splits the prior deferred `5c.2-B` remainder into B.1b-i landed + B.1b-ii-a landed + B.1b-ii-b landed + narrower remainder deferred)**. `5c.2-B.1b-ii-b` lands the **hermetic in-process Node static-export HTTP server** in the isolated `tools/react-e2e-harness/` workspace only (no edit surface in `src/`, no API/FastAPI/SQLite/extension changes, no `domain/keys.ts` / `infrastructure/store.ts` change, no production `next.config.mjs` / `package.json` change, no G4 capture, no legacy deletion). File: `tools/react-e2e-harness/scripts/export-server.mjs` (pure Node built-ins `node:http` + `node:fs/promises` + `node:path` + `node:url`; zero npm deps; zero harness `package.json` delta; CLI `--port N` / `--host H` OR `--port 0` OS-assigned; never hard-coded 8765; loopback default `127.0.0.1`). **--root is mandatory, absolute, and must point at an existing directory** — any other shape exits non-zero BEFORE binding a listener (fail-closed). `/` maps to `index.html` inside the root; exact files below root are served recursively with the matching Content-Type (HTML / HTM / JS / MJS / CSS / JSON / MAP / XML / TXT / SVG / PNG / JPG / JPEG / GIF / WEBP / ICO / WOFF / WOFF2 / TTF / OTF — unknown extensions fall back to `application/octet-stream`). HEAD mirrors GET's Content-Type + Content-Length (no body). `safeJoin()` mirrors the same defensive posture as `fixture-server.mjs`: reject `..` / `.` segments BEFORE any join; explicit segment split so mixed separators cannot escape; strict-parent check after join. Traversal / directory leakage / unknown paths / non-GET methods all fail-closed (404 / 405 with `Allow: GET, HEAD`). Importable via `startServer({port, host, root}) → {schema, root, host, port, baseUrl, server, close}` so the composition slice can spawn/teardown in-process. CLI parses `--root` / `--port` / `--host` / `--help` and exits non-zero on unknown flags. **Strict-TDD**: **RED** = pre-implementation source-contract check (`export-server.mjs` absent) FAILED on pre-`5c.2-B.1b-ii-b` source. **GREEN** = `node --check` exits `0` + all 39 hermetic tests pass (21 fixture + 18 export-server); lifecycle probe confirms caller-chosen port honoured, OS-assigned ports unique, `SIGTERM` releases the listener; CLI gating probe confirms `--root` missing / relative / non-existent each exit non-zero; `/` → `index.html` probe confirms the React entry document is served at the origin root; content-type probe confirms seven MIME families (HTML / JS / MJS / CSS / JSON / PNG / WOFF2) + `application/octet-stream` fallback for `.bin`; nested-file probe confirms recursive exact-file serving; HEAD-mirror probe confirms Content-Type + Content-Length match GET and no body; traversal probe confirms `..` / `../../etc/passwd` / `%2Fetc%2Fpasswd` / `%2E%2E%2Fpasswd` all 404; directory-leakage probe confirms `/sub/` 404 (no listing, no auto-append of `index.html`); unknown-route probe confirms `/no-such-file.html` 404; non-GET probe confirms POST returns exactly 405 with `Allow: GET, HEAD`. No production source/API change; no `domain/keys.ts` / `infrastructure/store.ts` change; no `web/*.{html,js,css}` legacy deletion; no G4 aggregation; no `tools/g4-capture/**` change; no FastAPI/SQLite/extension change. The narrower remainder of `5c.2-B` (composition slice wiring + Makefile target + hermetic capture-driver tests + e2e selector modernization on the new component tree + `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion) is still deferred. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by the static-export server landing** (no `scripts/verify_parity.py` end-to-end flip; no production build artifact; no browser runtime success; only the export HTTP server shipped). Spanish mirror carries the same semantics; any drift is resolved in favour of the English.

## Addendum — 2026-09-09: PR 5c.2-B.1b-ii-c composition orchestrator (landed, isolated workspace only); hermetic capture-driver tests + selector modernization + legacy deletion + G4 / G3 Tier-2 / cutover still deferred (append-only)

- **PR 5c.2-B.1b-ii-c landed (this entry, splits the prior deferred `5c.2-B` remainder into B.1b-i + B.1b-ii-a + B.1b-ii-b + B.1b-ii-c landed + narrower remainder deferred)**. `5c.2-B.1b-ii-c` lands the **composition orchestrator + CLI driver + Makefile target + `capture:composed` package-script + hermetic composition test slice** in the isolated `tools/react-e2e-harness/` workspace only (no edit surface in `src/`, no API/FastAPI/SQLite/extension changes, no `domain/keys.ts` / `infrastructure/store.ts` change, no production `next.config.mjs` / `package.json` change, no G4 capture, no legacy deletion). File: `tools/react-e2e-harness/scripts/composed-capture.mjs` (pure Node built-ins; zero npm deps; zero harness `package.json` delta). Wires `fixture-server.mjs` (5c.2-B.1b-ii-a) → injected `buildFn` (default `npm run build` with `NEXT_PUBLIC_HARNESS_BASE_URL` pinned to the fixture origin) → `out/index.html` access probe (fail-closed) → `export-server.mjs` (5c.2-B.1b-ii-b) → injected `captureFn` (default `run.mjs::capture`) into one `composeCapture({harnessDir, outputRoot, taxonId, host, buildFn, captureFn, startFixtureFn, startExportFn, now})` orchestrator. **CLI requires `--output-root`** (no default, exits non-zero with `missing --output-root`); **rejects non-loopback host** (`127.0.0.1` / `::1` / `localhost` are the only acceptable shapes, in line with the `fixture-server.mjs` / `export-server.mjs` defaults); **rejects any `--taxon-id` other than the synthetic `1`** the harness app + fixture serve (tightens the prior partial validator which accepted any positive integer — observed RED: with the tightening disabled, `test_composed_capture_cli_rejects_other_taxon_id` and `test_composed_capture_validate_taxon_id_accepts_one_only` fail with a clear "taxon" assertion miss and the CLI falls through to a real `npm run build` invocation that surfaces the missing validation). **No port is hard-coded** (`--port 0` for both servers, OS-assigned, distinct). **Reverse-order cleanup under nested `finally`** (export closed before fixture; verified in-process via injected `startFixtureFn` / `startExportFn` spies — observed `exportCloseSeq=1`, `fixtureCloseSeq=2` on `captureFn` failure). Both validation primitives (`validateTaxonId`, `validateHost`) are exported for the hermetic test slice. **No browser runtime success claimed** — `chromium-driver.mjs` is reachable via the default `captureFn`, but the composition test slice never invokes it (the in-process test fixture uses an injected capture stub that returns synthetic evidence). `Makefile::capture-react-e2e` requires `OUTPUT_ROOT` (no default; no production ports baked in; forwards `HARNESS_DIR`); `tools/react-e2e-harness/package.json` adds `scripts.capture:composed = "node scripts/composed-capture.mjs"`. Test surface: `tests/test_5c_2_b_react_harness.py` gains a composition block (11 hermetic cases; `subprocess` Node + Python `urllib`; no Playwright / Chromium / FastAPI / SQLite / network; total file now 65 hermetic cases including parametrized expansions). Covers source contract (file exists + `node --check` + zero-dep), CLI gating (`--output-root` mandatory; `--host 0.0.0.0` rejected; `--taxon-id 2` rejected), validation primitives (`validateTaxonId("1") → 1`; every other positive integer / zero / negative / non-numeric throws; `validateHost` accepts `127.0.0.1` / `::1` / `localhost` and rejects everything else), in-process orchestration with synthetic `out/index.html` + injected `buildFn` + injected `captureFn` (returns structured `taxa.react-e2e-composed-capture/1` envelope with OS-assigned loopback baseUrls), build bypass → fail-closed (`buildFn` claims success but no `out/index.html` → `composeCapture` throws BEFORE starting the export server or invoking `captureFn`), and reverse-order cleanup on capture failure (spy-tracked close sequence). **Strict-TDD**: **RED** = pre-`5c.2-B.1b-ii-c` source-contract check (composition module absent) FAILED on pre-`5c.2-B.1b-ii-c` source; the validation-tightening sub-cycle ran live (disabling the `n !== HARNESS_TAXON_ID` check sent the relevant tests RED with clear failures). **GREEN** = `node --check` exits `0` on `composed-capture.mjs` + all 65 hermetic tests pass. The narrower remainder of `5c.2-B` (hermetic capture-driver tests that drive `chromium-driver.mjs` end-to-end against a real fixture + export server; e2e selector modernization on the new component tree; `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion) is still deferred. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by the composition landing** (no `scripts/verify_parity.py` end-to-end flip; no production build artifact; no browser runtime success; only the orchestrator + CLI + Makefile target + package script + hermetic test slice shipped). Spanish mirror carries the same semantics; any drift is resolved in favour of the English.

## Addendum — 2026-09-09: PR 3c-ii size:exception authorization (documentation-only; not merged or verified) (append-only)

- **PR 3c-ii size:exception authorized (this entry, opens a second user-approved size:exception alongside the prior PR 3a regenerated-`package-lock.json` exception; 16-child chain preserved; no other scope changes; the PR is NOT claimed merged or verified by this addendum)**. The user authorized a size:exception for PR 3c-ii because the actual implementation of the complete taxonomy tree / detail CSS slice required **822 insertions + 9 deletions = 831 LoC**, against the prior `~380 LoC` estimate recorded in this design's "PR 3c sub-sequence replan" callout, the inline `~380 (≤ 400; -20 LoC headroom)` budget in the "Sub-PR slice under Approach A" table, the `~280 LoC for taxonomy tree / detail / kebab / materialize modal selectors` figure in the "Affected files" entry for `src/app/globals.css`, the `Largest new sub-PR is 3c-i at ~390 LoC` line in the `tasks.md` "Review Workload Forecast", the `the other 3c children are 3c-ii ~380, 3c-iii ~390, 3c-iv ~280` line in the same forecast, the **All 16 sub-PRs ≤ 400 LoC authored** assertion, and the `no new size:exception is opened for the 3c sub-sequence` clause — i.e. the actual implementation overshoots the 400-line per-PR review budget that Approach A locked on 2026-09-02 by +431 LoC. **Authorization rationale** (why a single reviewable PR is preferred over further slicing): (a) the taxonomy tree / detail selectors, the realm-tinted `.tree-row[data-realm="…"]` variants, the kebab menu / materialize modal selectors, the `#detail-panel` / `.detail-card` / `.detail-section` / `.overview-section` / `.detail-item` / `.search-pulse` / `.detail-tabs` / `.search-icon-btn` / `.materialize-btn` surface, and the parity-test slice in `tests/test_tailwind_4_parity.py` are inseparable from the 3c-i base layer (they must ship together so every selector resolves its `var(--token)` references against the live `:root` token slice); (b) splitting PR 3c-ii further into a 4c-i / 4c-ii pair would duplicate the `var(--token)` consumer surface across two PRs and force the later child to re-touch selectors the earlier child already locked; (c) the four-child 3c sub-sequence already minimised blast radius by splitting the 1,963-line legacy inline `<style>` into four reviewable siblings (3c-i / 3c-ii / 3c-iii / 3c-iv), so the present overshoot reflects the realistic CSS-port surface for the taxonomy tree / detail concern rather than a planning defect; (d) the `tests/test_tailwind_4_parity.py` enumeration of every taxonomy selector — the dominant contributor to the 831 LoC count — is itself an inseparable slice (splitting the enumerator across two PRs would leave a half-coherent test that nobody can review coherently and would still need to be re-merged at PR 5c). **The 16-child chain is preserved**: PR 3c-ii stays at position 4/16 with the same predecessor (`feat/complete-taxa-frontend-migration-03-3c-i`) and the same successor (`feat/complete-taxa-frontend-migration-05-3c-iii`); the per-PR dependency description, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c), and the user-approved replacement G5 protocol recorded above are unchanged. **The PR is not claimed merged or verified by this addendum** — the size:exception only authorises a single reviewable PR against the established budget; review, CI, and merge follow the ordinary feature-branch-chain process. The corrected estimates (`831 LoC total: 822 insertions, 9 deletions`) supersede the prior `~380 LoC` figure in the four tables above; the inline `~380 (≤ 400; -20 LoC headroom)` budget becomes `831 (overshoot +431 LoC against the 400-line budget; user-approved size:exception for this PR)`; the `~280 LoC for taxonomy tree / detail / kebab / materialize modal selectors` figure in the affected-files entry is annotated with the user-approved size:exception; the affected-files total rises from `~980 LoC` to `~1,510 LoC`; the Review Workload Forecast's `Largest new sub-PR is 3c-i at ~390 LoC` becomes `Largest new sub-PR by actual diff is PR 3c-ii at 831 LoC`; the `All 16 sub-PRs ≤ 400 LoC authored` line is annotated with `except PR 3c-ii, which carries a user-approved size:exception`; the `no new size:exception is opened` clause is annotated with `except for PR 3c-ii, which is now the second user-approved size:exception alongside PR 3a`. Spanish mirror (`documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md`) carries the same semantics; any drift is resolved in favour of the English. No code change; no rebase; no new branch; no commit/push; no PR open.

## Addendum — 2026-09-09: PR 3c-iii size:exception authorization (documentation-only; not merged or verified) (append-only)

- **PR 3c-iii size:exception authorized (this entry, opens a third user-approved size:exception alongside the prior PR 3a regenerated-`package-lock.json` exception AND the previously authorized PR 3c-ii taxonomy-tree CSS exception; 16-child chain preserved; PR 3c-iv surfaces deferred to the next child in the chain with unchanged scope; the PR is NOT claimed merged or verified by this addendum)**. The user authorized a size:exception for PR 3c-iii because the actual implementation of the complete Search / Folder / global Browser CSS slice required **1669 insertions and 66 deletions = 1735 review lines (net +1603)**, against the prior `~390 LoC` estimate recorded in this design's "PR 3c sub-sequence replan" callout, the inline `~390 (≤ 400; -10 LoC headroom)` budget in the "Sub-PR slice under Approach A" table, the `~330 LoC for Search / Folder / global Browser / file explorer / CSV / JSON selectors` figure in the "Affected files" entry for `src/app/globals.css`, the `Largest new sub-PR is 3c-i at ~390 LoC` line in the `tasks.md` "Review Workload Forecast", the `the other 3c children are 3c-i ~390, 3c-iii ~390, 3c-iv ~280` line in the same forecast (post 3c-ii exception), the **All 16 sub-PRs ≤ 400 LoC authored** assertion, and the `no new size:exception is opened for the 3c sub-sequence` clause — i.e. the actual implementation overshoots the 400-line per-PR review budget that Approach A locked on 2026-09-02 by **+1335 LoC** and the prior `~390 LoC` estimate by **+1345 LoC**. **What the PR actually preserves**: the **complete Search / Folder / global Browser selector catalogue** (`.toast` / `.toast-error`, `.search-engines-grid`, `.search-category-header`, `.search-engine-btn`, `.fex-meta-strip`, `.fex-tab-strip`, `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`, `.fex-splitter`, `.fex-row` + `.selected` / `.file` / `.folder` variants, `.fex-tree-header`, `.fex-children`, `.fex-banner`, `.fex-empty-state`, `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`, `.fex-tree-truncated`, per the 3c-iii scope enumeration in the "Sub-PR slice under Approach A" table) and its **canonical parity contract** (`tests/test_research_styles.py` enumerates every Search / Folder / global Browser selector; `tests/test_tailwind_4_parity.py` is extended with the browser selector slice; every selector resolves to a non-empty declaration in `src/app/globals.css` and `out/_next/static/chunks/*.css`). **3c-iv surfaces deferred**: the `@keyframes` rules + `.animate-spin` + the image / video viewer frames (`.fex-image-frame`, `.fex-image`, `.fex-image-advisory`, `.fex-video-frame`, `.fex-video-el`) + the Settings view selectors (`.settings-shell`, `.settings-header`, `.settings-list`, `.settings-row`, `.settings-theme-toggle`, `.settings-action-btn`, `.settings-link-btn`) + the design-system barrel (`src/modules/design-system/{infrastructure/index.ts, presentation/Icon.tsx, presentation/Button.tsx}`) remain deferred to PR 3c-iv at position 6/16 with no scope change; PR 3c-iv's `~280 LoC` estimate, the `~120 LoC for @keyframes + image / video viewer + Settings view` figure in the affected-files entry, and the `tests/test_design_system_purity.py` scope are unchanged. **Authorization rationale** (why a single reviewable PR is preferred over further slicing): (a) the Search / Folder / global Browser selectors are inseparable from the 3c-i base layer (tokens + dark-mode cascade) AND from the 3c-ii taxonomy selectors (the research selectors `.search-tab` / `.folder-tab` / `.header-browser-tab` ride on the live `var(--token)` references that 3c-ii just shipped); they must ship together as a single CSS slice so every browser / research selector resolves its `var(--token)` references against the live base layer; (b) splitting PR 3c-iii further into a 4c-i / 4c-ii pair would duplicate the `var(--token)` consumer surface across two PRs and force the later child to re-touch selectors the earlier child already locked — duplicating the planning defect the four-child 3c sub-sequence already closed; (c) the four-child 3c sub-sequence already minimised blast radius by splitting the 1,963-line legacy inline `<style>` into four reviewable siblings (3c-i / 3c-ii / 3c-iii / 3c-iv), so the present overshoot reflects the realistic CSS-port surface for the Search / Folder / global Browser concern rather than a planning defect (the `~390 LoC` estimate under-counted the canonical parity-test enumeration of every browser selector, the `.fex-search-*` / `.fex-csv-*` / `.fex-json-*` family depth, and the `.fex-tree-pane` / `.fex-viewer-pane` / `.fex-splitter` / `.fex-banner` chrome dimensions); (d) the `tests/test_tailwind_4_parity.py` + `tests/test_research_styles.py` enumeration of every Search / Folder / global Browser selector — the dominant contributor to the 1735 review-line count — is itself an inseparable slice (splitting the enumerator across two PRs would leave a half-coherent test that nobody can review coherently and would still need to be re-merged at PR 5c). **The 16-child chain is preserved**: PR 3c-iii stays at position 5/16 with the same predecessor (`feat/complete-taxa-frontend-migration-04-3c-ii`) and the same successor (`feat/complete-taxa-frontend-migration-06-3c-iv`); PR 3c-iv stays at position 6/16 with the same `~280 LoC` estimate and unchanged scope; the per-PR dependency description, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, **the existing PR 3c-ii size:exception stays open** (PR 3c-ii's 831 LoC overshoot is unchanged; this addendum does NOT modify, replace, or supersede the PR 3c-ii exception — both exceptions coexist on the same chain), every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii), and the user-approved replacement G5 protocol recorded above are unchanged. **The PR is not claimed merged or verified by this addendum** — the size:exception only authorises a single reviewable PR against the established budget; review, CI, and merge follow the ordinary feature-branch-chain process. The corrected estimates (`1735 review-line total: 1669 insertions, 66 deletions; net +1603; overshoot +1335 LoC against the 400-line budget and +1345 LoC against the prior ~390 LoC estimate; user-approved size:exception for this PR`) supersede the prior `~390 LoC` figure; the inline `~390 (≤ 400; -10 LoC headroom)` budget in the sub-PR slice table becomes `1735 review lines (overshoot +1335 LoC against the 400-line budget and +1345 LoC against the prior ~390 LoC estimate; user-approved size:exception for this PR)`; the `~330 LoC for Search / Folder / global Browser / file explorer / CSV / JSON selectors` figure in the affected-files entry is annotated with the user-approved size:exception; the cumulative `src/app/globals.css` total (3c-i `~250` + 3c-ii 831 + 3c-iii 1735 review lines + 3c-iv `~120`) rises from the post-3c-ii `~1,510 LoC` (with the 3c-ii exception only) to `~2,936 LoC` (with both exceptions); the Review Workload Forecast's `Largest new sub-PR by actual diff is PR 3c-ii at 831 LoC` becomes `Largest new sub-PR by actual diff is PR 3c-iii at 1735 review lines (net +1603; overshoot +1335 LoC against the 400-line budget and +1345 LoC against the prior ~390 LoC estimate; user-approved size:exception), with PR 3c-ii second at 831 LoC (user-approved size:exception) and PR 3c-i third at ~390 LoC`; the `All 16 sub-PRs ≤ 400 LoC authored` line is annotated with `except PR 3c-ii (831 LoC) AND PR 3c-iii (1735 review lines), both of which carry user-approved size:exceptions`; the `no new size:exception is opened` clause is annotated with `except for PR 3c-ii (already authorized) AND PR 3c-iii (authorized by this entry), which are the second and third user-approved size:exceptions alongside PR 3a`. Spanish mirror (`documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md`) carries the same semantics; any drift is resolved in favour of the English. No code change; no rebase; no new branch; no commit/push; no PR open.

## Addendum — 2026-09-09: PR 5.5 Tailwind 4 / PostCSS pipeline repair (landed; the first post-3c sub-sequence repair child; 17-child chain; the fourth user-approved size:exception for the regenerated package-lock.json alongside PR 3a + PR 3c-ii + PR 3c-iii) (append-only)

- **PR 5.5 Tailwind 4 / PostCSS pipeline repair landed (this entry, inserts a new repair child between PR 3c-iii and PR 3c-iv, expands the chain from 16 children to 17 children, opens a fourth user-approved size:exception for this PR's regenerated `package-lock.json` alongside the existing PR 3a + PR 3c-ii + PR 3c-iii exceptions, and surfaces the G2 production-candidate evidence gap that the prior chain left open; the PR is implemented in this worktree but is NOT claimed merged, NOT claimed G2-PASS, and NOT claimed browser-verified by this addendum)**. **Confirmed defect (root cause + observable signature at artifact level)**: PR 3c-i (position 3/16) shipped `src/app/globals.css` with the canonical Tailwind 4 surface — `@import "tailwindcss";` followed by an `@theme { --primary: #1d7ea9; --accent: #176587; --surface: #ffffff; … --realm-bacteria: #5ebd9b; … }` block carrying every legacy `:root` / `[data-theme="dark"]` / `--realm-*` token. PR 3c-ii (position 4/16), PR 3c-iii (position 5/16), and the prior toolchain bootstrap PR 3a (position 1/16) all consumed that surface under the assumption that `next build`'s default PostCSS pipeline would process `@import "tailwindcss"` and expand the `@theme { … }` block. **The assumption was wrong**: PR 3a added `tailwindcss@^4` as a top-level dep, but the project never registered a PostCSS plugin for it (no `postcss.config.mjs` at the repo root, no `@tailwindcss/postcss` dep). Turbopack's default PostCSS pipeline does NOT recognize `@import "tailwindcss";` as a Tailwind 4 directive and does NOT recognize `@theme { … }` as a CSS at-rule — the build emits a non-fatal `Unknown at rule: @theme` warning, leaves the `@theme { … }` block as a literal at-rule in the compiled CSS (the browser silently drops it because `@theme` is not a real CSS at-rule), and ships zero Tailwind preflight + zero `@tailwindcss/postcss`-expanded `:root` tokens. **Observed consequence (this worktree, base commit `6375927`, before PR 5.5)**: `next build` exits `0`, the legacy `.research-explorer` / `.fex-row` / `.tree-row` / `.tier-header` / `.load-all` / `.kebab` / `.search-tab` / `.folder-tab` / `.header-browser-tab` / `.fex-meta-strip` / `.fex-tab-strip` / `.fex-snippet-frame` / `.fex-csv-table` / `.fex-json-tree` / `.fex-tree-leaf` selectors ship (because they are plain CSS that does not need Tailwind processing), but **every `var(--primary)` / `var(--accent)` / `var(--surface)` / `var(--on-surface)` / `var(--realm-bacteria)` / `var(--realm-archaea)` / `var(--realm-viruses)` / `var(--realm-animalia)` / `var(--realm-fungi)` / `var(--realm-plantae)` / `var(--realm-chromista)` / `var(--realm-other)` reference inside those selectors resolves to `unset` at runtime** — the entire visual cascade is broken. The Tailwind 4 preflight (`*,:after,:before,::backdrop { box-sizing: border-box; border: 0 solid; margin: 0; padding: 0 }`) is absent; the Tailwind 4 utility class surface is absent; the `@keyframes spin { to { transform: rotate(360deg) } }` animation is absent. The compiled CSS bundle at `out/_next/static/chunks/391guka-hdllv.css` (Turbopack's chunked pipeline hash; this is the only CSS bundle `next build` emits for this repo) shrinks from **50,891 bytes** (with `@tailwindcss/postcss` running) to **35,093 bytes** (without it) — a ~31% shrink that is the defect's byte-level fingerprint. **What PR 5.5 ships (this worktree's edit surface)**: (1) `package.json` adds **two new top-level `dependencies` entries**: `"@tailwindcss/postcss": "^4.3.3"` (the official Tailwind 4 PostCSS plugin, resolved against the same `^4` major as the existing `tailwindcss` dep) and `"postcss": "^8.5.0"` (the runtime that `@tailwindcss/postcss` depends on — explicitly required now because PR 3a removed the legacy `postcss` top-level dep along with `autoprefixer` / `@tailwindcss/forms`, and the Tailwind 4 plugin needs a peer `postcss` to run). The Tailwind 3-era plugins (`autoprefixer`, `@tailwindcss/forms`) stay banned. (2) New file `postcss.config.mjs` at the repo root, `export default { plugins: { "@tailwindcss/postcss": {} } }` — a minimal ESM PostCSS config registering only the official Tailwind 4 plugin (no `autoprefixer`, no `@tailwindcss/forms`, no other legacy plugins). (3) Regenerated `package-lock.json` (this PR's regenerated lockfile is the **fourth user-approved size:exception** for this project, alongside the existing PR 3a + PR 3c-ii + PR 3c-iii exceptions — see the lockfile-exception paragraph below for the authorization rationale and the lockfile delta). (4) `tests/test_toolchain_bootstrap.py` is updated: `REQUIRED_DEPS_PRODUCTION` is expanded from `(("tailwindcss", "4"),)` to `(("tailwindcss", "4"), ("postcss", None), ("@tailwindcss/postcss", None))` so `postcss` and `@tailwindcss/postcss` are pinned as required production deps (major unconstrained because Tailwind 4 keeps them aligned with its own release cadence); `FORBIDDEN_LEGACY_DEPS` shrinks from `("autoprefixer", "postcss", "@tailwindcss/forms")` to `("autoprefixer", "@tailwindcss/forms")` so the Tailwind 3-era `autoprefixer` + `@tailwindcss/forms` ban stays open while `postcss` is now required (not banned). (5) New test surface `tests/test_tailwind_build_pipeline.py` — a focused regression test that performs a REAL `next build` against the repo, reads the compiled CSS bundle under `out/_next/static/{css,chunks}/*.css`, and asserts: (a) `next build` exits `0`; (b) at least one CSS bundle exists under the static-export path; (c) the Tailwind 4 preflight universal-selector rule (`*,:after,:before,::backdrop { box-sizing: border-box; … }`) is present in the compiled CSS — this is the canonical witness that `@tailwindcss/postcss` actually ran; (d) the literal at-rule `@theme {` is NOT present in the compiled CSS — a literal `@theme {` surviving is the signature defect that proves the plugin never expanded the `@theme` block into the `@layer theme { :root, :host { … } }` declaration the browser actually reads; (e) the literal substring `@import "tailwindcss"` is NOT present in the compiled CSS — a literal import surviving is the signature that the plugin never resolved the directive; (f) every CSS bundle contains the preflight (no subset leakage — the plugin ran on all bundles, not just one); (g) the legacy `:root` palette token `--primary: #1d7ea9` lives inside a `@layer theme { :root, :host { … } }` declaration (the canonical Tailwind 4 expansion shape, NOT inside a literal `@theme` block). The fixture cleans `out/` and `.next/` on teardown IF they did not exist before the test entered (so a developer who already has an `out/` from a prior build keeps theirs; the test owns its own artifact lifecycle). **Strict-TDD evidence observed in this worktree (RED → GREEN → TRIANGULATE)**: **RED** = pre-implementation, both the new test file's 7 cases AND the updated toolchain test's 2 new dep cases FAIL with the post-3c-iii base — `tests/test_tailwind_build_pipeline.py::test_next_build_emits_css_bundle_under_out_static` and 5 sibling tests ERROR with `postcss.config.mjs missing at … PR 5.5 ships @tailwindcss/postcss as the registered plugin`; `tests/test_tailwind_build_pipeline.py::test_triangulate_postcss_config_registers_tailwind_plugin_only` FAILS with `postcss.config.mjs missing at … PR 5.5 ships the root postcss.config.mjs registering @tailwindcss/postcss`; `tests/test_toolchain_bootstrap.py::test_required_dep_present_in_dependencies[postcss-None]` and `[postcss-None]` and `[@tailwindcss/postcss-None]` FAIL with `production dep 'postcss' missing from dependencies` and `production dep '@tailwindcss/postcss' missing from dependencies`. **GREEN** = after adding the two deps to `package.json`, creating `postcss.config.mjs`, and running `npm install` to regenerate `package-lock.json`, the full toolchain test file passes (`30 passed in 0.02s`) and the full build-pipeline test file passes (`7 passed in 3.83s`); repeatability confirmed by a second consecutive run (`7 passed in 3.83s`) with no flakiness; the compiled CSS bundle is byte-identical between the two runs (`50,891 bytes`, hash-stable under Turbopack's chunked pipeline). **TRIANGULATE** = the test pair covers both the package.json dep side (toolchain test) AND the postcss.config.mjs config side (build-pipeline test) AND the compiled-CSS artifact side (Tailwind preflight + `@theme` at-rule absence + `@import "tailwindcss"` absence + theme token expansion into `:root, :host`); a future regression that drops the dep, removes the config, or leaves the directive unprocessed in the compiled CSS is caught at the artifact level. **Visual-defect fix proof at artifact level**: on this worktree after PR 5.5, a clean `node node_modules/.bin/next build` produces `out/_next/static/chunks/391guka-hdllv.css` (50,891 bytes) that contains **204 occurrences of `--tw-`** (Tailwind utility variables — proof the plugin generated utility classes), **1 occurrence of `@keyframes spin`** (the Tailwind animation), **1 occurrence of `.animate-spin`** (a Tailwind utility class generated for the React source), **1 occurrence of `@layer theme { :root, :host { … --primary: #1d7ea9; … } }`** (the Tailwind 4 expansion of the legacy `@theme` block), **5 occurrences of `#1d7ea9`** (the legacy `:root` palette hex value, now correctly hoisted into the compiled `:root` cascade), **zero occurrences of the literal `@theme {` at-rule**, and **zero occurrences of the literal `@import "tailwindcss"` substring**. `node scripts/check-runtime.mjs` exits `0` with `[check-runtime] Node 26.8.1 >= 20.9.0 OK (engines.node = ">=20.9.0")` — the runtime guard is unaffected. `npm ci` reproduces a 121-package install with the same 18 tailwind/postcss lockfile entries (`node_modules/@tailwindcss/{node,oxide,oxide-*,postcss}` + `node_modules/postcss` + `node_modules/tailwindcss`) on a fresh clone. **Topology / count implications (accurate, append-only)**: the chain expands from **16 children to 17 children**. The new repair child is named **PR 5.5 (Tailwind 4 / PostCSS pipeline repair)** and sits at **position 5.5/17** — interpolated between **position 5/17 (PR 3c-iii, Search / Folder / global Browser styling)** and **position 7/17 (PR 3c-iv, animations / utilities + final CSS parity + design-system barrel)**. Every child that was previously at position `n/16` (for `n ∈ {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}`) is renumbered to `n+1/17` (so `6/16 → 7/17`, `7/16 → 8/17`, `8/16 → 9/17`, `9/16 → 10/17`, `10/16 → 11/17`, `11/16 → 12/17`, `12/16 → 13/17`, `13–15/16 → 14–16/17`, `16/16 → 17/17`). PR 3a stays at `1/17`, PR 3b stays at `2/17`, PR 3c-i stays at `3/17`, PR 3c-ii stays at `4/17`, PR 3c-iii stays at `5/17`. The sub-PR scope, the predecessor / successor branch mapping, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii, 3c-iii), and the user-approved replacement G5 protocol recorded above are unchanged in their substantive content; only their position labels shift up by 1 (or stay where they are if they were before position 5). PR 5.5's **dependency position**: depends on **PR 3c-iii** (the `@theme` block + the legacy `var(--token)` consumers are in place so a working `@tailwindcss/postcss` expansion has tokens to expand and selectors to serve); **does NOT depend on PR 3c-iv** (the `@keyframes` + utilities + design-system barrel are not yet shipped, but the build pipeline repair does not need them — the preflight + `@theme` expansion + `--tw-*` utility generation are all that PR 5.5 needs to be self-contained). The new repair child itself is self-contained: it does not touch `src/app/globals.css` content (3c-i / 3c-ii / 3c-iii own that file), does not touch `tsconfig.json`, does not touch `.nvmrc`, does not touch `scripts/check-runtime.mjs`, does not touch the Makefile, does not touch `next.config.mjs`, does not touch `api/server.py`, does not touch any `src/modules/**` barrel, does not touch `web/**` (the legacy vanilla bundle), does not touch `extension/**`, and does not delete `web/*.{html,js,css}` or `tailwind.config.js` (those deletions land with PR 5c). **LoC budget**: PR 5.5's authored diff is well under the 400-line budget (1 new config file `postcss.config.mjs` ≈ 25 LoC, 1 new test file `tests/test_tailwind_build_pipeline.py` ≈ 220 LoC, 1 modified test file `tests/test_toolchain_bootstrap.py` ≈ +12 LoC delta, 1 modified `package.json` ≈ +2 LoC delta — total **≈ 259 authored LoC**, ≤ 400 with **−141 LoC headroom**). The **lockfile exception is the only size:exception PR 5.5 opens** — see the lockfile-exception paragraph below. **The 17-child chain is preserved** (the chain grew by exactly one child, in the only safe insertion point: between PR 3c-iii's `src/app/globals.css` slice and PR 3c-iv's `@keyframes` + utilities + design-system barrel slice — both of which sit downstream of the `@tailwindcss/postcss` expansion that PR 5.5 finally provides). **The fourth user-approved size:exception for the regenerated `package-lock.json` (this entry, opens a fourth lockfile size:exception alongside the existing PR 3a + PR 3c-ii + PR 3c-iii exceptions; PR 3a is generated-resolution-only and stays open as the prior documented lockfile size:exception; PR 3c-ii is an authored-LoC exception, not a lockfile exception, and stays open unchanged; PR 3c-iii is an authored-LoC exception, not a lockfile exception, and stays open unchanged; the present PR 5.5 exception is a generated-lockfile exception for the `@tailwindcss/postcss` + `postcss` resolution additions)**: the regenerated `package-lock.json` adds **16 new tailwind/postcss-related lockfile entries** (of the **18 tailwind/postcss-related lockfile entries** in the post-fix lockfile; `tailwindcss` itself predates this repair because PR 3a added it) (`node_modules/@tailwindcss/{node, oxide, oxide-android-arm64, oxide-darwin-arm64, oxide-darwin-x64, oxide-freebsd-x64, oxide-linux-arm-gnueabihf, oxide-linux-arm64-gnu, oxide-linux-arm64-musl, oxide-linux-x64-gnu, oxide-linux-x64-musl, oxide-wasm32-wasi, oxide-win32-arm64-msvc, oxide-win32-x64-msvc, postcss}` + `node_modules/postcss` + `node_modules/tailwindcss`) bringing the total `packages` object from the pre-3c-iii baseline to **121 packages** and the lockfile line count to **2,112 lines**. The lockfile change is **generated-resolution-only** (no hand-authored content); it contains **only the resolution changes required by the two new top-level deps** in `package.json` (i.e. `@tailwindcss/postcss` + `postcss`, plus the transitive `@tailwindcss/node` + `@tailwindcss/oxide*` tree that `@tailwindcss/postcss` depends on); it is reviewed together with `package.json`; it carries no unrelated lockfile churn. The two new `package.json` entries are caret-pinned (`^4.3.3` for `@tailwindcss/postcss` against the same Tailwind 4 major as `tailwindcss`, `^8.5.0` for `postcss` against the standard PostCSS 8 line) so the lockfile delta is deterministic under re-`npm install`. **Authorization rationale** (why a single reviewable PR is preferred over splitting the postcss.config.mjs away from the dep + lockfile change): (a) the PostCSS plugin registration, the two new top-level deps, and the regenerated lockfile are inseparable — without `@tailwindcss/postcss` installed, `postcss.config.mjs` cannot register it; without `postcss` as a peer dep, `@tailwindcss/postcss` cannot run; without the regenerated lockfile, `npm ci` will not reproduce the install on a fresh clone; (b) the build-pipeline regression test is inseparable from the fix (it reads the compiled CSS output that the fix produces); (c) splitting PR 5.5 further into a 5.5-a / 5.5-b pair would leave a half-broken build pipeline (deps installed but no plugin registered, OR plugin registered but no regression test) that nobody can review coherently and would still need to be re-merged at PR 5c; (d) PR 5.5's authored diff is ~259 LoC (well under the 400-line budget) so no further authored-LoC exception is needed. **G2 production-candidate evidence gap (this entry surfaces a gap the prior chain left open; PR 5.5 closes one witness but does NOT flip G2; G2 remains pending the full Phase 6 capture)**: the prior chain recorded G2 as a **PASS** carried from the predecessor (`migrate-nextjs-tailwind4/`) per `design.md::§TL;DR` and `tasks.md::Phase 1.1` (G2 = clean static-export build at `out/`). The G2 predecessor PASS was captured against the **`tools/g2-candidate/` isolated workspace** with `tools/g2-candidate/app/globals.css` containing ONLY `:root { color-scheme: light; }` + a body reset — i.e. a 4-line CSS file with no `@import "tailwindcss"`, no `@theme`, and no Tailwind dependency. **That G2 PASS does not transfer to the production repo**, because the production repo's `src/app/globals.css` (post-PR-3c-iii) ships the canonical `@import "tailwindcss";` + `@theme { … }` surface that the `@tailwindcss/postcss` plugin must process, and the prior chain never registered that plugin. Concretely: a clean `next build` against the pre-PR-5.5 repo produces a `out/_next/static/chunks/391guka-hdllv.css` of **35,093 bytes** with the `@theme { … }` block as a literal at-rule and zero Tailwind preflight — the artifact the FastAPI `StaticFiles` mount serves at `127.0.0.1:8765/_next/static/chunks/391guka-hdllv.css` is the production-candidate G2 evidence; that evidence was BROKEN before PR 5.5 and is now COMPLETE after PR 5.5 (the bundle is **50,891 bytes** with the `@theme` block expanded into `@layer theme { :root, :host { … } }` and the Tailwind preflight present). **PR 5.5 closes the BUILD-PIPELINE half of the G2 production-candidate evidence gap** by adding the artifact-level regression test `tests/test_tailwind_build_pipeline.py` (which performs a real `next build` and asserts on the compiled CSS); the BROWSER half of the G2 gap (a real Chromium / Playwright capture against `127.0.0.1:8765` proving every `var(--token)` reference resolves and the Tailwind preflight takes effect at runtime) **remains deferred to the Phase 6a validation work** and is NOT claimed by this addendum. G2 production-candidate remains **PASS-pending-Phase-6-capture**, NOT flipped by PR 5.5 alone. **What PR 5.5 explicitly does NOT claim**: (i) PR is NOT claimed merged into the tracker (`docs/complete-taxa-frontend-migration-plan`) or into `develop` — this addendum documents the worktree's authored state only; (ii) PR is NOT claimed CI-green on the full repo test suite — the 31 pre-existing failures in `tests/test_tailwind_4_{parity,base_resets,utilities}.py` + the 52 pre-existing failures in `tests/test_tailwind_tokens_base.py` (all of which are PR 3c-iv-deferred surfaces — `--color-*` Tailwind 4 utility namespace aliases, `@keyframes spin` + `.animate-spin` in `@layer base`, byte-size budget against the yet-to-land 3c-iv PR) are documented pre-existing failures, unchanged by PR 5.5, and the regression test for them lands with PR 3c-iv per the prior addendum; (iii) PR is NOT claimed browser-verified (no real Chromium / Playwright capture against `127.0.0.1:8765`); (iv) PR is NOT claimed G2-PASS (G2 remains PASS-pending-Phase-6-capture, see above); (v) PR does NOT enable `gentle-ai review mode` and does NOT open a PR — review / CI / merge follow the ordinary feature-branch-chain process once the user-authorized parent task completes. **Spanish mirror** (`documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md`) carries the same semantics; any drift is resolved in favour of the English.

## Addendum — 2026-09-09: PR 5.6 DOM↔CSS structural parity repair (landed; the second post-3c sub-sequence repair child; chain expands from 17 children to 18 children; the fifth user-approved size:exception) (append-only)

- **PR 5.6 DOM↔CSS structural parity repair landed (this entry, inserts a new repair child between PR 5.5 and the former 3c-iv, expands the chain from 17 children to 18 children, opens a fifth user-approved size:exception alongside the existing PR 3a + PR 3c-ii + PR 3c-iii + PR 5.5 exceptions, and ships the CSS-only repair for the React-emitted taxonomy / detail structural hooks that the prior chain emitted via React but did not paint; the PR is implemented in this worktree but is NOT claimed merged, NOT claimed G2-PASS, and NOT claimed browser-verified by this addendum)**. **Confirmed defect (root cause + observable signature at artifact level)**: PR 5a.2 + PR 5a.3 + PR 5a.4 + PR 5b.4 + PR 5c.1b-B all emitted the React `<Tree>` / `<Breadcrumb>` / `<DetailPanel>` / `<OverviewTab>` / `<TabStrip>` / `<Kebab>` components with the canonical structural classNames (`.taxa-tree` / `.tree-row` + `[data-selected]` / `.tab-strip` / `.tab-button` / `.overview-tab` / `.breadcrumb` + `.breadcrumb-segment` + `.breadcrumb-link` / `.detail-panel` + `.detail-body` + `.detail-close` / `.species-count` / `.authorship` / `.materialize-indicator` / `button[data-action="toggle-kebab"]`), but `src/app/globals.css` only carried the legacy `@layer base` taxonomy selectors (which used dead `data-realm` / `.selected` / `.kebab-trigger` className selectors that the React components never emit) + the kebab base selectors in `@layer components` (`.kebab` + `.kebab-menu` + `.kebab-menu.open` only). The DOM↔CSS gap is a CLASS-NAME MISMATCH — the React components emit the new classNames, the CSS carries the legacy classNames, and the visual cascade is silent. **What PR 5.6 ships (this worktree's edit surface)**: (1) `src/app/globals.css` — CSS-only repair, no React changes, no dependency changes, no layout / image / icon / gradient additions. The 15 React-emitted structural hooks + the 9 state selectors + the 2 collapsed descendant rules (`.kebab > .kebab-menu` + `.tab-strip > .tab-button` per the 3c-b.4 refactor contract) + the 1 kebab selector bridge (`.kebab > button[data-action="toggle-kebab"]`) + the 5 visible-state / chainable / scrollable triangulation declarations. (2) `src/app/globals.css` cleanup — stale/dead CSS selectors resolved safely per the user's directive: (a) the legacy `data-realm`-tinted `.tree-row[data-realm="..."] .scientific-name { color: var(--realm-*) }` rules REMOVED from `@layer base` (the React `<Tree>` does not stamp `data-realm` on taxonomy rows); (b) the dead `.tree-row:hover/selected/focus-within .kebab-trigger` + `.kebab-trigger:hover` + `.kebab-trigger:focus-visible` rules REMOVED from `@layer base` (the React `<Kebab>` component stamps `data-action="toggle-kebab"` instead of a className); (c) the `.kebab-trigger:focus-visible` global focus-visible selector in `@layer base` REPLACED with `.kebab > button[data-action="toggle-kebab"]:focus-visible` (the new CSS-only contract for the React <Kebab> trigger); (d) the `.detail-item .authorship` rule REMOVED from `@layer base` (the chain-topology guard required `.authorship` to be a top-level selector); (e) the `.scientific-name { font-style: italic }` + `.scientific-name--roman { font-style: normal }` rules MOVED from `@layer base` to `@layer components` (the React component CSS layer owns the emitted hook; the modifier rides the compound `.scientific-name.scientific-name--roman` selector to keep the chain-topology whitelist intact). (3) `tests/test_tailwind_4_parity.py` — 37 new test cases (PR 5.6 catalogue) added under the `## 5.6` section + 3 pre-existing PR 3c-ii realm-tinted tests REPURPOSED to assert the dead-code absence + `TAXONOMY_SELECTORS` constant updated to remove `.scientific-name` / `.scientific-name--roman` / `.kebab-trigger`. **Strict-TDD evidence observed in this worktree (RED → GREEN → TRIANGULATE)**: 35 of 37 new PR 5.6 test cases FAIL on the post-5.5 base; all 37 pass after the CSS-only repair; repeatability confirmed by a second consecutive run; the full `tests/test_tailwind_4_parity.py` + `tests/test_taxonomy_overview_styles.py` suite passes (`348 passed in 0.55s`). **Topology / count implications (accurate, append-only)**: the chain expands from **17 children to 18 children**. The new repair child is named **PR 5.6 (DOM↔CSS structural parity repair)** and sits at **position 5.6/18** — interpolated between **position 5.5/18 (PR 5.5, Tailwind 4 / PostCSS pipeline repair)** and the former 3c-iv (renumbered to **position 8/18 (PR 3c-iv, animations / utilities + final CSS parity + design-system barrel)**). Every child that was previously at position `n/17` (for `n ∈ {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}`) is renumbered to `n+1/18` (so `7/17 → 8/18` PR 3c-iv; `8/17 → 9/18` PR 3d; `9/17 → 10/18` PR 4a; `10/17 → 11/18` PR 4b; `11/17 → 12/18` PR 5a; `12/17 → 13/18` PR 5b; `13/17 → 14/18` PR 5c; `14/17 → 15/18` PR 6a; `15/17 → 16/18` PR 6b; `16/17 → 17/18` PR 6c; `17/17 → 18/18` PR 3e). PR 3a stays at `1/18`, PR 3b stays at `2/18`, PR 3c-i stays at `3/18`, PR 3c-ii stays at `4/18`, PR 3c-iii stays at `5/18`, PR 5.5 stays at `5.5/18`. The sub-PR scope, the predecessor / successor branch mapping, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii, 3c-iii, 5.5), and the user-approved replacement G5 protocol recorded above are unchanged in their substantive content; only their position labels shift up by 1 (or stay where they are if they were before position 5.5). PR 5.6's **dependency position**: depends on **PR 5.5** (the `@tailwindcss/postcss` expansion is in place so the CSS-only repair's new selectors expand correctly into the compiled CSS bundle) AND on **PR 5a + PR 5b** (the React `<Tree>` / `<Breadcrumb>` / `<DetailPanel>` / `<OverviewTab>` / `<TabStrip>` / `<Kebab>` components are in place so the React-emitted classNames the CSS rules target exist in the DOM); **does NOT depend on PR 3c-iv** (the `@keyframes` + utilities + design-system barrel are not yet shipped, but the CSS-only structural repair does not need them). The new repair child is self-contained: it does not touch `package.json` / `package-lock.json` / `postcss.config.mjs` / `tsconfig.json` / `.nvmrc` / `scripts/check-runtime.mjs` / `Makefile` / `next.config.mjs` / `api/server.py` / any `src/modules/**` barrel / `web/**` (the legacy vanilla bundle) / `extension/**`; the only `src/` file PR 5.6 edits is `src/app/globals.css` (CSS-only repair); the only test file PR 5.6 edits is `tests/test_tailwind_4_parity.py` (parity test extension + dead-selector resolution repurpose). **The fifth user-approved size:exception for the CSS-only repair authored-LoC delta (this entry, opens a fifth size:exception alongside the existing PR 3a + PR 3c-ii + PR 3c-iii + PR 5.5 exceptions; PR 3a is a generated-resolution-only lockfile exception and stays open; PR 3c-ii is an authored-LoC exception for the taxonomy-tree CSS slice and stays open; PR 3c-iii is an authored-LoC exception for the Search/Folder/global Browser CSS slice and stays open; PR 5.5 is a generated-resolution-only lockfile exception and stays open; the present PR 5.6 exception is an authored-LoC exception for the CSS-only DOM↔CSS structural parity repair)**: the actual implementation required **491 insertions and 64 deletions in `src/app/globals.css` (net +427) + 539 insertions and 53 deletions in `tests/test_tailwind_4_parity.py` (net +486) — total authored LoC delta ≈ 1,147 across the two files**, against the prior `~120 LoC` estimate for the CSS-only repair alone. The implementation overshoots the 400-line per-PR review budget that Approach A locked on 2026-09-02 by **+747 LoC** and the prior `~120 LoC` estimate by **+1,027 LoC**. **Authorization rationale** (why a single reviewable PR is preferred over further slicing): (a) the 15 React-emitted structural hooks + the 9 state selectors + the 2 collapsed descendant rules + the 1 kebab selector bridge + the 5 visible-state / chainable / scrollable triangulation declarations are INSEPARABLE from the 3 React components they target — the `.taxa-tree` + `.tree-row` + `[data-selected="true"]` selectors only make sense together (the React `<Tree>` emits them as a unit), the `.tab-strip > .tab-button` + `.active` + `[data-tab="..."]` selectors only make sense together (the React `<TabStrip>` emits them as a unit), and the `.kebab` + `.kebab > button[data-action="toggle-kebab"]` + `.kebab > .kebab-menu` + `.kebab > .kebab-menu.open` selectors only make sense together (the React `<Kebab>` emits them as a unit); (b) splitting PR 5.6 further into a 5.6-a / 5.6-b / 5.6-c triple (tree / detail / kebab) would duplicate the source-CSS + test-enumeration surface across three PRs and force the later children to re-touch selectors the earlier children already locked; (c) the 37 test cases are themselves an inseparable slice; (d) the CSS-only repair lives entirely in `src/app/globals.css` + `tests/test_tailwind_4_parity.py` — a single reviewable diff surface (two files) without any cross-cutting concern. **G2 production-candidate evidence gap (PR 5.6 closes the BROWSER-LAYER half but does NOT flip G2; G2 remains pending the full Phase 6 capture)**. The prior chain (PR 5.5) closed the BUILD-PIPELINE half of the G2 evidence gap (the `@tailwindcss/postcss` expansion makes every `var(--token)` reference resolve at runtime, the Tailwind preflight paints, the compiled CSS bundle carries every React-emitted className the CSS rules target). PR 5.6 closes the BROWSER-LAYER half: the React-emitted structural hooks now have non-empty CSS rules in `src/app/globals.css` AND the compiled CSS bundle at `out/_next/static/chunks/2c4tn6w2gxss3.css` post-PR-5.6 contains those rules (the rule shapes survive the Turbopack minification intact — verified via the new `tests/test_5_6_*` parametrized tests, every selector appears in the source CSS and is asserted to resolve under `@layer components`). **What PR 5.6 does NOT close**: the actual visual rendering against `127.0.0.1:8765` — a real Chromium / Playwright capture is still required to prove that the static-export bundle paints the React-emitted structural hooks as visibly structural + interactive. G2 production-candidate remains **PASS-pending-Phase-6-capture**, NOT flipped by PR 5.6 alone. The browser capture is the Phase 6a validation work, not PR 5.6. **Spanish mirror** (`documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md`) carries the same semantics; any drift is resolved in favour of the English. No rebase; no new branch; no commit/push; no PR open.

## Addendum — 2026-09-09: PR 3c-iv five-slice replan (documentation-only; chain expands from 18 children to 22 children; user-approved documentation size exception to keep all six OpenSpec files internally coherent) (append-only)

- **PR 3c-iv five-slice replan authorized (this entry, replaces the former single PR 3c-iv with five linear reviewable children at positions 6/22 through 10/22, renumbers the downstream 3d → 4a → 4b → 5a → 5b → 5c → 6a → 6b → 6c → 3e children to keep the dependency contract linear, expands the chain from 18 children to 22 children including the existing PR 5.5 + PR 5.6 fractional repairs, opens the user-approved documentation size exception necessary to keep all six OpenSpec files — the three EN/ES `tasks` + `design` + `apply-progress` mirrors — internally coherent under this single planning revision; this is a planning-only change; no code slice is implemented, verified, merged, or approved for delivery by this addendum)**. The user authorized splitting the existing single `PR 3c-iv` (former `feat/complete-taxa-frontend-migration-06-3c-iv`, then `…-08-3c-iv` after PR 5.5 + PR 5.6 renumbering) into **five linear ≤ 400 authored-line children** (`3c-iv-barrel`, `3c-iv-keyframes`, `3c-iv-viewer`, `3c-iv-settings`, `3c-iv-colors`) because the former single PR's surface was heterogeneous — it bundled the design-system barrel + the legacy `@keyframes` rules + the image / video viewer frames + the Settings view + the Tailwind `--color-*` namespace aliases — which is unsatisfiable as a single ≤ 400 LoC PR while preserving the binding dependency contract. The five-slice replan replaces the single branch with five new branches, each ≤ 400 authored LoC and each carrying exactly one of the five concerns the former single PR bundled together. **Required target topology (replaces the former single PR 3c-iv with five children, in linear dependency order)**: (1) `3c-iv-barrel`, branch `feat/complete-taxa-frontend-migration-06-3c-iv-barrel`, **based on the existing PR 5.6 DOM↔CSS structural parity repair predecessor** (`feat/complete-taxa-frontend-migration-18-3c-iv-barrel` predecessor slot; the predecessor is the prior 5.6 base commit): ships the design-system barrel (`src/modules/design-system/infrastructure/index.ts`) + the `<Icon>` Material Symbols Outlined glyph wrapper + the `<Button>` layout primitive + the design-system purity test (`tests/test_design_system_purity.py`). (2) `3c-iv-keyframes`, branch `feat/complete-taxa-frontend-migration-07-3c-iv-keyframes`, based on `…-06-3c-iv-barrel`: ships the five legacy `@keyframes` rules (`detail-card-enter`, `detail-card-leave`, `search-pulse-anim`, `materialize-spin`, `toast-slide-in`) + the `.animate-spin` utility class parity contract. (3) `3c-iv-viewer`, branch `feat/complete-taxa-frontend-migration-08-3c-iv-viewer`, based on `…-07-3c-iv-keyframes`: ships the image + video viewer CSS parity selectors (`.fex-image-frame`, `.fex-image`, `.fex-image-advisory`, `.fex-video-frame`, `.fex-video-el`). (4) `3c-iv-settings`, branch `feat/complete-taxa-frontend-migration-09-3c-iv-settings`, based on `…-08-3c-iv-viewer`: ships the Settings view CSS parity selectors (`.settings-shell`, `.settings-header`, `.settings-list`, `.settings-row`, `.settings-row-text`, `.settings-row-title`, `.settings-row-description`, `.settings-row-control`, `.settings-theme-toggle`, `.settings-theme-btn`, `.settings-theme-btn-active`, `.settings-action-btn`, `.settings-link-btn`). (5) `3c-iv-colors`, branch `feat/complete-taxa-frontend-migration-10-3c-iv-colors`, based on `…-09-3c-iv-settings`: ships the Tailwind `--color-*` namespace aliases + the legacy utility class parity contract (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `bg-primary-fixed`, `text-on-primary-fixed`, `bg-surface`, `text-outline`, `text-on-surface-variant`, `hover:text-on-surface`, `focus:border-primary`, `focus:ring-primary/20`, `transition-all`, `transition-colors`, `font-h1`, `text-h1`, `font-body-md`, `text-body-sm`, `fixed`, `top-0`, `w-full`, `z-50`, `bg-surface/95`, `backdrop-blur-md`, `shadow-[0_1px_8px_rgba(0,0,0,0.04)]`, `h-16`, `px-row-padding-x`, `flex`, `items-center`, `justify-between`, `gap-gutter`, `min-w-0`, `whitespace-nowrap`, `relative`, `w-64`, `lg:w-96`, `absolute`, `left-3`, `top-1/2`, `-translate-y-1/2`, `text-[18px]`, `py-2`, `pl-10`, `pr-4`, `rounded-xl`, `focus:outline-none`, `focus:ring-2`, `shrink-0`, `aria-pressed`). **Downstream renumbering (chain expands from 18 children to 22 children; PR 5.5 stays at 5.5/22, PR 5.6 stays at 5.6/22)**: PR 3d (Makefile/mount) renumbers `7/16 → 8/18 → 11/22`; PR 4a (typed store) renumbers `8/16 → 9/18 → 12/22`; PR 4b (hydration guard) renumbers `9/16 → 10/18 → 13/22`; PR 5a (taxonomy port) renumbers `10/16 → 11/18 → 14/22`; PR 5b (research port + CDN pin) renumbers `11/16 → 12/18 → 15/22`; PR 5c (e2e + delete legacy) renumbers `12/16 → 13/18 → 16/22`; PR 6a (G5) renumbers `13/16 → 14/18 → 17/22`; PR 6b (G6) renumbers `14/16 → 15/18 → 18/22`; PR 6c (G4 measurement) renumbers `15/16 → 16/18 → 19/22`; PR 3e (atomic cutover) renumbers `16/16 → 17/18 → 20/22`. **Downstream dependency corrections (binding under this replan, replaces the prior 3c-iv dependency statements throughout this file)**: (a) **PR 3d (Makefile/mount) and PR 5c (delete legacy) now depend on PR 3c-iv-colors** — these are the consumers of the complete Tailwind 4 cascade (`next build` produces a complete CSS payload because every `--color-*` alias resolves at the colors step). (b) **PR 4a (typed store) now depends on PR 3c-iv-barrel** — PR 4a's typed store consumes the design-system `<Icon>` + `<Button>` primitives only (it does not need keyframes / viewer / settings / colors to be in place). (c) **The 3c-iv sub-sequence forms a five-link linear chain**: barrel → keyframes → viewer → settings → colors; each child targets its immediate predecessor branch; no downstream consumer reaches across the sub-sequence to a non-terminal child (design-system consumers depend on barrel; final CSS consumers depend on colors; intermediate children carry their respective parity contracts but no other child depends on them). **No active reference to the old single branch** (`feat/complete-taxa-frontend-migration-06-3c-iv` or its post-5.5/5.6 renumbered `…-08-3c-iv`) **remains in the active topology after this addendum** — every prior inline reference to the single `3c-iv` (the `Corrective plan revision` callout, the `PR 3c sub-sequence replan rationale` callout, the `Sub-PR slice under Approach A` table, the `Dependency order` section, the `Affected files` entry for `src/app/globals.css` + the design-system module, the `Test seams` section entries, the `Module ownership` table, the binding tab-behavior contract, the `5.5` + `5.6` addenda's "3c-iv renumbered to 8/18" cross-references) is updated by this replan to reflect the five-slice structure: the single PR 3c-iv is decomposed into five children at positions 6/22 through 10/22; the former single `~280 LoC` aggregate budget is decomposed into five per-child budgets (barrel ~120, keyframes ~80, viewer ~50, settings ~50, colors ~80 — sum ~380 LoC, ≤ 400 with −20 LoC headroom across the five children); the `Sub-PR slice under Approach A` table is expanded from a single row to five rows; the affected-files entries for `src/app/globals.css` + the design-system module are split across the five children. **What this replan explicitly does NOT claim**: (i) **No code slice is implemented, verified, merged, or approved for delivery by this addendum** — this is a planning-only revision; (ii) **No new `size:exception` is opened for the 3c-iv five-slice replan itself** — the existing PR 3a (generated-lockfile-only) + PR 3c-ii (taxonomy CSS slice authored-LoC) + PR 3c-iii (Search/Folder/global Browser CSS slice authored-LoC) + PR 5.5 (regenerated-lockfile) + PR 5.6 (CSS-only DOM↔CSS authored-LoC) exceptions stay open unchanged; the present replan opens the user-approved **documentation** size exception necessary to keep all six OpenSpec files internally coherent under a single planning revision, not a code slice exception; (iii) No `gentle-ai review mode` is enabled; no branch is created; no commit is authored; no push happens; no PR opens; review / CI / merge follow the ordinary feature-branch-chain process once the user-authorized parent task completes. **Preserved (binding, this entry)**: every prior addendum (`5c.1a`, `5c.1b-A`, `5c.1b-B`, `5c.2-A`, `5c.2-B.1a`, `5c.2-B.1b-i`, `5c.2-B.1b-ii-a`, `5c.2-B.1b-ii-b`, `5c.2-B.1b-ii-c`, `3c-ii`, `3c-iii`, `5.5`, `5.6`) remains in the change log as historical audit record; the **frozen predecessor restriction** on `openspec/changes/migrate-nextjs-tailwind4/**` stays binding; **G4 / G5 / G6 status stays unchanged** — G5 remains PASS-pending-Phase-6-capture (recorded PASS from the user-approved replacement protocol), G4 stays blocked (verifier not authored), G6 stays blocked, PR 3e (atomic cutover) stays gated on G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 closure; the **Approach A lock** stays FINAL; the **FastAPI/SQLite foundation** stays unchanged; the **Feature Branch Chain strategy** stays unchanged; the **per-domain specs** stay unchanged; the **EN/ES mirror fidelity** stays binding (any drift is resolved in favour of the English). **Spanish mirror** (`documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md` + the four other ES mirrors) carries the same semantics; any drift is resolved in favour of the English. No rebase; no new branch; no commit/push; no PR open.
