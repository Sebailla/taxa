# Spec: complete-taxa-frontend-migration

> Successor to `migrate-nextjs-tailwind4` (frozen as planning
> history). The proposal, predecessor artifacts (`proposal.md`,
> `design.md`, `apply-progress.md`, `cutover-manifest.json`,
> `specs/modular-architecture/spec.md`), and the canonical
> `openspec/specs/research/spec.md` are upstream context. This
> spec does **not** re-derive evidence the predecessor already
> produced.

## TL;DR

- **Approach A is FINAL** (user decision, 2026-09-02). Next.js 16
  + React 19 + Tailwind 4 static export (`out/`) served by
  FastAPI's existing `StaticFiles` mount at `127.0.0.1:8765`.
  Single origin, single port. No SSR, no route handlers, no
  server components. No second dev-server port. Extension
  `host_permissions` unchanged.
- **Atomic cutover unit** (PR3e in the predecessor's vocabulary,
  re-sliced under Approach A): a single release unit changes the
  `WEB_DIR` constant, every active consumer in the predecessor's
  `design.md::§3.1`, the `make api` build pipeline, and the `out/`
  build artifact together. **No subset revert is supported.**
- **Rollback unit**: `git revert <cutover-sha>` restores the legacy
  vanilla build atomically with green smoke + Playwright. No DB
  schema change ships in this change, so no data migration is
  required.
- **Backend is non-negotiable**: FastAPI + SQLite (WAL); `/api/*`
  byte-identical; `save-url` SSRF defence; ETL pipeline;
  `extension/manifest.json::host_permissions` stays at
  `["http://localhost:8765/*"]`.
- **Evidence gates carried verbatim**:
  - G1 (single origin) — **PASS recorded**.
  - G2 (foundation build) — **PASS recorded** against the
    verified Next.js 16.3.3 / Turbopack clean build.
  - G3 Tier-1 (consumer readiness, legacy pre-cut) — **PASS
    recorded** (all 26 §3.1 consumers green via the controlled
    fixture, `scripts/verify_consumers.py`).
  - G3 Tier-2 (atomic-cut selection) — **NOT PASSED**;
    requires G2 + G4 + G5 + G6 closure.
  - G4 (Playwright + Lighthouse parity) — **blocked — verifier
    not authored**; must close in the apply phase.
  - G5 (hydration baseline) — **unreproducible — legacy
    baseline not on disk**; must be reconstructed or replaced
    during the apply phase.
  - G6 (cutover rehearsal) — **blocked — verifier not
    authored**; must close in the apply phase.
- **Predecessor frozen**: `openspec/changes/migrate-nextjs-tailwind4/**`
  is byte-identical before and after this change's apply phase.
  CI / branch-protection rejects any PR that modifies it.

## Approach A — final

The proposal documented Approach A as the evidence-gated default
with an explicit override path (cite G2 + G5 numbers from the
predecessor's `apply-progress.md`, record the override in
`design.md::§1`). On **2026-09-02** the user locked Approach A as
the final selection. B and C are not under consideration. The
evidence that supports the lock-in is the same evidence the
predecessor already produced:

| Gate | Status | Why A is supported |
| --- | --- | --- |
| G1 (single origin) | PASS recorded | A honours G1 trivially; no second port, no second container. |
| G2 (foundation build) | PASS recorded | The clean Next 16.3.3 / Turbopack build produced `BUILD-INVENTORY.json` with all required application-route classes (sole `out/index.html`, JS + CSS under `out/_next/static/chunks/**`, staged `build-manifest.json`, optional `app-build-manifest.json` recorded as `not_emitted`) plus the `out/404.html` error-page classification. |
| G3 Tier-1 (consumer readiness, legacy pre-cut) | PASS recorded | All 26 §3.1 consumers green against the legacy pre-cut runtime via the controlled fixture and `scripts/verify_consumers.py` (PR #109 + PR #111 + PR #115 + PR #116). |
| G4 (Playwright + Lighthouse parity) | Blocked — verifier not authored | Must close in the apply phase. |
| G5 (hydration baseline) | Unreproducible — legacy baseline not on disk | Must be reconstructed or replaced by an equivalent during the apply phase. |
| G6 (cutover rehearsal) | Blocked — verifier not authored | Must close in the apply phase. |

The cutover is gated by **G1 PASS + G2 PASS + G3 Tier-1 PASS**
plus **G4 + G5 + G6 closure** before the atomic release ships.
The apply phase owns G4 / G5 / G6; the design phase records
the final decision (A, no override) in
`design.md::§1` (final, not deferred).

## Scope

### In scope

- Total frontend migration to Next.js 16 + React 19 + Tailwind 4,
  replacing the on-disk `web/` vanilla-JS app under Approach A.
- One shipping frontend. The parallel pre-cut legacy build is
  retired at activation — no dual-build state in this change's
  apply phase.
- FastAPI origin preserved on `127.0.0.1:8765`. Minimal
  `api/server.py` edits are allowed only for the `WEB_DIR`
  repoint and any middleware strictly required to mount the new
  frontend output. Route handlers are not rewritten.
- AC-21 search-engine contract test preserved (`web/search_urls.js`
  may move under `src/data/`; byte shape preserved unless this
  spec phase explicitly revises — it does not).
- Browser-local state (`theme`, `tree-source`, `last-taxon-id`,
  `kebab-open-id`) migrated deterministically into a typed store
  with one read site + one write site per key.
- Modular-architecture constraints from the predecessor's
  `specs/modular-architecture/spec.md` apply unchanged.

### Out of scope

- Backend rewrite: `api/server.py` route handlers, SQLite/WAL
  logic, materialize flow, SSRF defence in `save-url`.
- ETL pipeline: `etl/parse_textree`, `etl/load_coldp`,
  `etl/load_worms`, `etl/load_freshwater`, migrations.
- Chrome extension parity work — a separate change tracks any
  React-aware extension adaptation.
- SEO / metadata / sitemap / robots work.
- New routes (Settings, About, Help) beyond what the legacy UI
  exposes today.
- Coverage tooling (`coverage.available: false` is the current
  state).
- Visual redesign (impeccable / Stitch follow-up, not a blocker).
- Editing or "completing" the predecessor's change directory.
  The predecessor is **frozen**, not finalized.
- Re-running the predecessor's G2 / G4 / G5 / G6 probes — their
  outputs are imported as-is.

## Backend contract (non-negotiable)

Any change that violates a row in this table is out of scope and
must be raised in a separate change.

| Surface | Constraint | Source |
| --- | --- | --- |
| Origin | `http://127.0.0.1:8765` only | G1 (single-origin) |
| Port | 8765 only; no second dev-server port | G1 |
| `/api/*` shapes | Byte-identical to current FastAPI | Functional equivalence rule |
| Extension `host_permissions` | `["http://localhost:8765/*"]` unchanged | Continuity rule |
| SQLite mode | WAL; read-only API connections | Repo convention (`openspec/sdd-init.md`) |
| ETL pipeline | Unchanged in this change | Predecessor out-of-scope |
| Materialize flow, `save-url` SSRF defence | Unchanged in this change | Predecessor out-of-scope |

## Per-domain specs

The per-domain specs are the canonical contract; this `spec.md`
is the synthesised executive view.

- `specs/frontend-runtime/spec.md` — Next.js static-export
  single-screen app under FastAPI's `StaticFiles` mount; full
  UI surface + parity + performance + accessibility.
- `specs/design-tokens/spec.md` — Tailwind 4 `@theme` block +
  CSS variables preserved from the legacy inline `<style>` and
  `tailwind.config.js`; token parity test.
- `specs/browser-state-hydration/spec.md` — typed store with
  four `localStorage` keys, one read site + one write site per
  key, hydration guard.
- `specs/frontend-bootstrap/spec.md` — `WEB_DIR` repoint,
  single-mount contract, `make api` build pipeline, runtime
  version check, atomic cutover + rollback unit.
- `specs/research/spec.md` — **delta** against the canonical
  `openspec/specs/research/spec.md`. Captures the migration
  contract without changing request/response shapes or AC-21
  byte parity.
- **No spec authored** for `modular-architecture`. The canonical
  spec lives under
  `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
  (frozen). The successor inherits rule 1–7 unchanged per the
  proposal §Capabilities §"Unchanged capabilities (imported from
  predecessor)".

## Acceptance criteria

The per-domain specs enumerate the testable scenarios. The list
below is the executive summary; per-domain specs are
authoritative.

### Functional parity

- [ ] **Browse flow** — domain → sub-tree → species row;
  breadcrumb updates; detail panel loads; URL reflects
  `<root>/<taxon>` per the legacy shape.
- [ ] **Detail panel tab strip** — selecting any node (including
  top-level domains) opens an inline contextual detail panel
  with **three tabs in fixed order: `Overview`, `Search`,
  `Folder`**. All three tabs are reachable from every selection;
  `Overview` is **always available and always visible** per the
  user-selected policy (no future state may gate `Overview`
  behind a feature flag, a permission, or a taxon-shape check).
- [ ] **`Overview` tab** — renders the selected taxon's metadata:
  scientific name, accepted status, authorship, species count.
  `Overview` is the default tab on a fresh selection.
- [ ] **`Search` tab** — renders a categorized outbound-link list.
  Categories render in fixed order: `General`, `Taxonomic`,
  `Academic`, `Multimedia`, `Documents`. Each entry is an anchor
  with `target="_blank"`, `rel="noopener noreferrer"`, and the
  URL template resolved from the `SEARCH_ENGINES` literal.
  **`Search` is a primary tab** (sibling of `Overview` and
  `Folder`), NOT a secondary card list nested under
  `Overview`.
- [ ] **`Folder` tab** — per-taxon folder / materialize indicator;
  separate from `Search`.
- [ ] **`Search online` kebab action forces `Search` tab** —
  invoking the `Search online` action from the per-row kebab
  menu on **any** selection (including top-level taxa) MUST
  activate the `Search` tab on the selected taxon, NOT
  `Overview`. Current live behavior lands on `Overview` for
  top-level taxa; this regression MUST be closed by the
  apply phase.
- [ ] **Header `Browser` tab is global** — `Browser` is the
  **global Research / file explorer** surface; it is NOT a
  detail-panel tab and is NOT taxon-scoped. Selecting a
  taxon while `Browser` is active MUST NOT scope the file
  explorer to that taxon; the explorer continues to show the
  active research corpus.
- [ ] **Search flow** — header search modal fires
  `GET /api/search?q=<q>`; results from all three sources (`col`,
  `worms`, `freshwater`) appear in the legacy result grouping.
- [ ] **Materialize flow** — `POST /api/taxon/{id}/materialize`;
  modal callback merges returned ids into `state.materialized`;
  per-row indicator turns saturated green for the new ids and
  their visible descendants.
- [ ] **Save URL flow** — extension POSTs to
  `/api/taxon/{id}/save-url`; SSRF defence unchanged; React
  rendering layer refreshes without code changes to the extension.
- [ ] **File viewer** — every supported format dispatches to the
  matching legacy renderer (PDF, HTML, TXT, MD, DOCX, XLS, XLSX,
  EPUB) with the meta strip `FORMAT | SIZE | ENCODING`. Legacy
  DOC and unsupported formats show the download fallback.
- [ ] **CDN failure** — viewer renders the
  `"Viewer offline — raw download unavailable"` banner and keeps
  the tree interactive.
- [ ] **Tree search** — 200 ms debounce, filter / highlight modes,
  `state.explorer.search.{query, mode, hideEmpty}` persisted.
- [ ] **Switching taxon clears explorer state** —
  `state.explorer.{rootTaxonId, tree, openFilePath,
  openFileFormat, viewerTab}` resets; re-opening Browser re-fires
  `GET /api/taxon/{B}/files`.

### Performance

- [ ] **≤ 0 % regression** in initial paint on the chromium
  fixture the predecessor captured.
- [ ] **≤ 0 % regression** in interaction latency.
- [ ] **≤ 0 % regression** in `out/BUILD-INVENTORY.json`
  (`chunks`, `total_bytes`, `per_route_bytes`) vs. the legacy
  evidence baseline, without a documented exemption.

### Single origin

- [ ] **`make api` binds only 8765**; no second listener.
- [ ] **`extension/manifest.json::host_permissions`** stays at
  `["http://localhost:8765/*"]`.
- [ ] **`content_scripts.matches`** stays at
  `["http://localhost:8765/*"]`.

### Backend

- [ ] **63 passed, 8 skipped** baseline preserved
  (`make test` against the `.venv`).
- [ ] **`make smoke`** passes (live API on `127.0.0.1:8765`).

### AC-21 contract

- [ ] **`tests/test_smoke.py::test_search_engine_contract`**
  passes. If the literal moved to `src/data/search-engines.js`,
  the test's `open()` path updates in the same release; the
  byte shape (key, label, with_authorship, ordering) is
  unchanged; `api/server.py::_SEARCH_ENGINES` is unchanged.

### Browser-state hydration

- [ ] **`theme`, `tree-source`, `last-taxon-id`, `kebab-open-id`**
  each have exactly one read site + one write site inside
  `src/modules/browser-state/`.
- [ ] **No hydration warning** in the browser console after the
  first paint + rehydration cycle.
- [ ] **`localStorage` exceptions** (private mode, quota
  exceeded) are swallowed; the typed default is returned.

### Tailwind 4 parity

- [ ] **Every `:root` token** resolves to a non-empty
  declaration in `globals.css`.
- [ ] **Every `var(--name)` reference** in the legacy build's
  bespoke CSS resolves.
- [ ] **Every utility class** the legacy build emits resolves
  to a non-empty CSS declaration in the new build.

### Accessibility

- [ ] **Every ARIA role, label, and keyboard handler** from the
  legacy build is preserved.
- [ ] **Axe scan** reports no new `serious` / `critical`
  violations vs. the legacy baseline.

### Predecessor frozen

- [ ] **`openspec/changes/migrate-nextjs-tailwind4/**`** is
  byte-identical before and after this change's apply phase.
- [ ] **CI / branch-protection** rejects any PR that modifies
  the predecessor's directory.

### Rollback

- [ ] **`git revert <cutover-sha>`** restores the legacy
  vanilla build atomically.
- [ ] **`make smoke`** returns to the pre-migration baseline
  (63 passed, 8 skipped).
- [ ] **No data migration** is required to roll back.

## Validation gates

Every gate has a named producer, an invocation command, an
artifact path, and an acceptance threshold. The apply phase owns
G4 / G5 / G6 closure; the spec phase records the carried status
verbatim.

| Gate | Producer | Command | Artifact | Threshold | Status (carried) |
| --- | --- | --- | --- | --- | --- |
| G1 (single origin) | predecessor `design.md::§1` | n/a (boundary decision) | `design.md::§1` block | FastAPI sole-origin invariants recorded; `/api/*` + extension manifest unchanged. | **PASS recorded** |
| G2 (foundation build) | `scripts/verify_build.py` | `python scripts/verify_build.py --out <build-root> --node-min 20.9.0` | `<build-root>/BUILD-INVENTORY.json` | Build exits 0; inventory lists every required asset class; Node ≥ 20.9.0; no missing-classes; required `build-manifest.json` staged atomically; optional `app-build-manifest.json` recorded as `staged` or `not_emitted`; error-page exemptions classified separately. | **PASS recorded** |
| G3 Tier-1 (consumer readiness, legacy pre-cut) | `scripts/verify_consumers.py` | `python scripts/verify_consumers.py --manifest … --out <build-root> --serve --venv <repo-root>/.venv/bin/python --fixture-web-root <repo-root>/tools/g3-legacy-fixture/web --repo-root <repo-root>` | `<build-root>/CONSUMER-READINESS.json` | Verifier exits 0; every §3.1 consumer PASS; `manifest_sha256` stable; `activation_complete = true`; `unselected_count = 0`; HTTP-shape expectations routed through `tools/g3-legacy-fixture/scripts/check_http_status.py` (PR #115); venv symlinks preserved (PR #116). | **PASS recorded** |
| G3 Tier-2 (atomic-cut selection) | same verifier, atomic-cut pass | same | same | Same as Tier-1 plus the §3.1 consumers flip from `selected` (legacy pre-cut) to the post-cut activation record. | **NOT PASSED** — gated by G4 + G5 + G6 |
| G4 (Playwright + Lighthouse parity) | `tests/test_e2e_file_explorer.py`, `tests/test_web_toggle.py`, Playwright + Lighthouse harness | `.venv/bin/python3 -m pytest tests/ -v` + Playwright + Lighthouse run | `tests/test_web_toggle.py`, Playwright trace, Lighthouse JSON | Every legacy scenario passes against the new component tree; Δ ≤ 0 % on initial paint and interaction latency. | **blocked — verifier not authored** |
| G5 (hydration baseline) | `scripts/measure_hydration.py` | `python scripts/measure_hydration.py --baseline <path>` | hydration baseline JSON | Δ ≤ 0 % vs. the legacy baseline; legacy baseline reproducible. | **unreproducible — legacy baseline not on disk** |
| G6 (cutover rehearsal) | `scripts/rehearse_cutover.py` | `python scripts/rehearse_cutover.py --manifest …` | `cutover-rehearsal.json` | Rehearsal exits 0; no silent fallback paths; atomic cutover unit + rollback unit consistent. | **blocked — verifier not authored** |

The cutover unit ships **only** when G1 + G2 + G3 Tier-1 PASS
plus G4 + G5 + G6 closure are all on disk. Absent, failed, stale
(> 7 days), or incomparable evidence is **blocked**, never
success.

## Atomic cutover unit

The atomic cutover unit (PR3e-equivalent, re-sliced under
Approach A) changes **exactly the following** in a single release:

1. **`WEB_DIR` constant** in `api/server.py:54` (repoint at
   `out/`).
2. **Every active-consumer update** enumerated in the
   predecessor's `design.md::§3.1` (imports, the AC-21 reader
   path, every test consumer). The 21 web-mount consumers and
   the 5 `web/search_urls.js` consumers are named verbatim in the
   predecessor's `cutover-manifest.json`.
3. **The `Makefile::api` and `Makefile::web` targets.**
4. **The build artifact** — the `out/` directory itself
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, the error-page classification
   if `404.html` / `500.html` is emitted).

**No subset revert is supported.** Partial reverts leave
consumers referencing deleted paths and break the SPA shell or
the AC-21 contract test.

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

After revert:

- `make api` regenerates `web/dist/tailwind.css` from the
  reverted source.
- `make smoke` returns to the pre-migration baseline (63 passed,
  8 skipped).
- `curl http://127.0.0.1:8765/index.html` returns the vanilla
  shell.
- `extension/manifest.json` is unchanged through the cutover
  and the rollback (no manifest update is required to revert).
- No DB schema change ships, so no data migration is required
  to roll back.
- `openspec/changes/migrate-nextjs-tailwind4/**` stays byte-
  identical through the cutover and the rollback — the
  predecessor is frozen.

## Evidence reuse

This spec does **not** re-derive the predecessor's evidence. The
following artifacts are imported as planning history:

- `openspec/changes/migrate-nextjs-tailwind4/proposal.md`
- `openspec/changes/migrate-nextjs-tailwind4/design.md` (incl.
  `§1` boundary decision, `§3.1` active-consumer inventory,
  `§3.3.2.1` G2 contract, `§3.3.3` / `§3.3.3.1` G3 contract,
  `§3.3.5` G5 disposition)
- `openspec/changes/migrate-nextjs-tailwind4/apply-progress.md`
  (incl. the change log that records G2 PASS, G3 Tier-1 PASS,
  G5 unreproducible)
- `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
- `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
- `openspec/specs/research/spec.md` (canonical; preserved
  unchanged; the delta lives at
  `specs/research/spec.md` of this change)

## Next step

The **design phase** records the final approach decision (already
locked at A, no override) in
`openspec/changes/complete-taxa-frontend-migration/design.md::§1`
(final, not deferred), slices the predecessor's 35 tasks under
Approach A within the 400-line review budget per sub-PR, and
produces the per-task file lists that the apply worker follows
in `tasks.md`. The **apply phase** owns G4 / G5 / G6 closure
before the atomic cutover lands. The **archive phase** copies
each per-domain spec verbatim into
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
and promotes the modular-architecture spec into the canonical
specs tree.