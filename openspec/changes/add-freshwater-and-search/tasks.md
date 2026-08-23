# Tasks — add-freshwater-and-search

This document is the implementation roadmap for the `sdd-apply` phase. It builds on `proposal.md`, `spec.md`, and `design.md`, and obeys the project conventions cached in `openspec/sdd-init.md` (strict TDD, conventional commits without AI attribution, offline pytest, no editorial changes to existing CoL/WoRMS flows).

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | ~803 production+test (≤825 design estimate; LOC buffer from rounding) |
| 400-line budget risk | **High** — exceeds the soft 400-line review budget |
| Chained PRs recommended | **Yes** — see "Delivery strategy recommendation" below |
| Suggested split | PR-1 (backend foundation) → PR-2 (frontend + engine contract) → PR-3 (build target + README) |
| Delivery strategy | `ask-on-risk` (cached in `openspec/sdd-init.md`) — orchestrator must pause to confirm chain shape before `sdd-apply` launches |
| Chain strategy | **`stacked-to-main`** (recommended; see justification below) |

```text
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

---

## 1. Workload forecast

### 1.1 Per-file LOC (matches `design.md` §1.1)

**New files**

| File | Action | Lines | Purpose |
| ------ | -------- | ------- | --------- |
| `etl/load_freshwater.py` | NEW | 190 | CSV reader, idempotent migration, wipe-and-reload, `fw_map` parent resolution, post-load `species_count` rollup, log-and-skip on malformed rows |
| `etl/schema_v4.sql` | NEW | 15 | Indexes only (`idx_taxon_freshwater` partial, `idx_taxon_fw_parent`) |
| `etl/tests/__init__.py` | NEW | 0 | Package marker so pytest discovers `etl/tests/` |
| `etl/tests/test_load_freshwater.py` | NEW | 120 | AC-1..AC-7: in-memory SQLite fixture + representative CSVs |
| `tests/test_api_freshwater.py` | NEW | 110 | AC-8..AC-19: TestClient hits against seeded SQLite |
| `web/search_urls.js` | NEW | 70 | `SEARCH_ENGINES` (14 entries) + `buildSearchUrl` helper |

**Modified files**

| File | Action | Lines | Purpose |
| ------ | -------- | ------- | --------- |
| `api/server.py` | EDIT | 70 | New `SearchLink` model; two new optional fields on `Taxon`; `_row_to_taxon` pass-through; `RANK_ORDER` extended with `collection = -1`; `get_domains` new OR clause; `get_children` regex widened + new branch; new `get_searches` endpoint; module-level `_SEARCH_ENGINES` constant |
| `web/index.html` | EDIT | 25 | Third toggle button styles + tab strip CSS (`.detail-tabs`, `.detail-tab`, `.detail-tab-active`) + Búsquedas link styles |
| `web/app.js` | EDIT | 140 | `RANK_ORDER` prepend; `matchesTreeSource` new branch; per-row search icon render + click handler; tab-strip render; `loadDetail` searches fetch; `boot()` conditional toggle button; tree-source toggle converted from `forEach` to event delegation |
| `tests/test_smoke.py` | EDIT | 25 | AC-20 (OpenAPI path assertion for `/searches`) + AC-21 (search engine contract test parsing both files) |
| `Makefile` | EDIT | 13 | `freshwater:` target + `load-all:` selector + `test:` target extended with `etl/tests/` |
| `README.md` | EDIT | 25 | Freshwater source subsection + Búsquedas tab subsection + updated API endpoint table |

**Total**: ~803 LOC.

### 1.2 Per-commit LOC

| Commit | Files | Approx. LOC | PR |
| -------- | ------- | ------------- | ----- |
| `etl: add freshwater loader with idempotent migration` | `etl/load_freshwater.py`, `etl/schema_v4.sql`, `etl/tests/__init__.py`, `etl/tests/test_load_freshwater.py`, `Makefile` (test target edit only) | 328 | PR-1 |
| `api: add freshwater slice and /searches endpoint` | `api/server.py`, `tests/test_api_freshwater.py`, `tests/test_smoke.py` (AC-20 only) | 190 | PR-1 |
| `web: add SEARCH_ENGINES catalog synced with api` | `web/search_urls.js`, `tests/test_smoke.py` (AC-21 only) | 85 | PR-2 |
| `web: add Búsquedas tab and per-row search icon` | `web/index.html`, `web/app.js` | 165 | PR-2 |
| `build+docs: add freshwater target and README section` | `Makefile` (`freshwater:` + `load-all:`), `README.md` | 35 | PR-3 |

### 1.3 Per-PR LOC

| PR | Commits | Approx. diff size (additions + deletions) | Budget |
| ---- | --------- | ------------------------------------------- | -------- |
| PR-1: backend foundation | commits 1, 2 | ~518 | **+30% over 400** — size exception justified (tests-with-code per work-unit-commits; see §2.1) |
| PR-2: frontend + engine contract | commits 3, 4 | ~250 | Under budget |
| PR-3: build target + docs | commit 5 | ~35 | Under budget |

PR-1 over-budget is deliberate. Splitting the loader tests off into a separate PR would violate `work-unit-commits` ("Keep tests with code"). Splitting API from loader would force PR-2 (frontend) to start before PR-1 is fully reviewable. PR-1 is one coherent reviewable unit (DB → API → their offline tests) and the 400-line rule is a soft budget — the chained-pr skill's harder rule is "reviewable in ~60 minutes", which 518 LOC of focused backend code satisfies.

---

## 2. Delivery strategy recommendation

### 2.1 Chain shape: **`stacked-to-main`**

**Justification**: each PR is an independent, mergable slice — backend foundation is fully testable offline (`make test`); frontend depends on the backend endpoint already being defined but does NOT require the backend data to be present (the dynamic toggle button only appears when freshwater data is loaded; the engine contract test only needs both source files to exist). Feature-branch-chain adds a tracker branch that does not pay off here because no slice needs to integrate before main exposes anything.

### 2.2 PR count: **3** (not 2, not 4)

**Why not 2**: A 2-PR split would force PR-1 to carry either all backend (~518 LOC, over budget) AND most of PR-3's Makefile change, or to bundle backend + frontend together (~770 LOC, ~93% over budget with no reviewable slice boundary).

**Why not 4**: A 4-PR split (loader alone, API alone, frontend, build/docs) would split the backend along a non-coherent boundary (loader and API are designed to be reviewed together — API tests use loader-loaded data via in-memory SQLite) and would add a third merge coordination point for marginal size reduction (518 → ~328 + ~190).

**Why 3**: Each PR has a coherent reviewable theme that matches an existing change boundary in the project (backend / frontend / build+docs) and matches the design's `Option A` recommendation.

### 2.3 PR boundaries

| PR | Theme | Reviewable in isolation? |
| ---- | ------- | --------------------------- |
| PR-1 | Backend foundation: loader, API, their tests, Makefile `test:` discovery | ✅ Self-contained — `make test` is green; CoL/WoRMS flows untouched (verified by `git diff --stat` against main showing only freshwater-related changes); existing smoke tests in `tests/test_smoke.py` continue to pass |
| PR-2 | Frontend: `SEARCH_ENGINES` static table, dynamic freshwater toggle, per-row search icon, Búsquedas tab strip, tab-strip render | ✅ Self-contained — engine contract test (AC-21) reads both files and passes; dynamic toggle button stays hidden when freshwater data is absent (AC-23); CoL and WoRMS UX unchanged for users who never load freshwater |
| PR-3 | Build target + documentation: `make freshwater`, updated `load-all` selector, README section | ✅ Self-contained — Makefile target fails fast with a hint when CSV is absent (same pattern as `worms:`); README renders correctly |

### 2.4 Acceptance criteria coverage

Every AC must be in some PR. Mapping:

| AC | PR | Task(s) |
| ---- | ---- | --------- |
| AC-1, AC-7 | PR-1 | T1.2, T1.5 |
| AC-2, AC-3, AC-4 | PR-1 | T1.3 |
| AC-5 | PR-1 | T1.4 |
| AC-6 | PR-1 | T1.1 |
| AC-8, AC-9 | PR-1 | T1.8 |
| AC-10, AC-11, AC-12 | PR-1 | T1.9 |
| AC-13, AC-14 | PR-1 | T1.7 |
| AC-15, AC-16, AC-17, AC-18, AC-19 | PR-1 | T1.10 |
| AC-20 | PR-1 | T1.11 |
| AC-21 | PR-2 | T2.1, T2.2 |
| AC-22, AC-23, AC-29 | PR-2 | T2.3, T2.4 |
| AC-24 | PR-2 | T2.6 |
| AC-25 | PR-2 | T2.5 |
| AC-26 | PR-2 | T2.9 |
| AC-27, AC-28 | PR-2 | T2.7, T2.8 |
| AC-30 | PR-3 | T3.2 |
| AC-31 | PR-3 | T3.3 (gate-checked, not a code task) |

---

## 3. PR shape

### 3.1 PR-1 — `feat(freshwater): add loader, API slice, and /searches endpoint`

**Title**: `feat(freshwater): add loader, API slice, and /searches endpoint`

**Branch**: `feat/freshwater-loader-and-api`

**Body draft**:

```markdown
## Summary

Adds the third tree source (Freshwater Fishes) end-to-end on the backend:

- `etl/load_freshwater.py` — idempotent CSV loader mirroring `load_worms.py`.
- `etl/schema_v4.sql` — partial indexes on the new overlay columns.
- `api/server.py` — extended `Taxon` model, `/api/domains` extension, `/api/taxon/{id}/children?source=freshwater` branch, new `/api/taxon/{id}/searches` endpoint returning 14 server-composed search-engine links.
- New offline pytest coverage for loader (AC-1..AC-7) and API (AC-8..AC-20).
- Makefile `test:` target now also discovers `etl/tests/`.

## What stays the same

- CoL and WoRMS flows are byte-identical to today. Verified by `git diff` — only freshwater-related lines change in `api/server.py`.
- `source=col` and `source=worms` branches of `/api/taxon/{id}/children` are unchanged.
- OpenAPI schema gains one new path; all existing paths preserved.

## Acceptance criteria

AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 (loader); AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19 (API); AC-20 (OpenAPI).

## Self-contained check

- `make test` is green (all new + existing tests pass).
- `pytest etl/tests/test_load_freshwater.py -v` is green for AC-1..AC-7.
- `pytest tests/test_api_freshwater.py -v` is green for AC-8..AC-19.
- `pytest tests/test_smoke.py::test_openapi_schema_is_valid_json -v` includes `/api/taxon/{taxon_id}/searches`.
- `git diff origin/main -- api/server.py` shows only freshwater-related additions; CoL/WoRMS code untouched.

## Out of scope (deferred to PR-2 / PR-3)

- Frontend toggle button, search icon, Búsquedas tab (PR-2).
- `make freshwater` target and README (PR-3).
```

**Files touched (full list)**:

- `etl/load_freshwater.py` (NEW)
- `etl/schema_v4.sql` (NEW)
- `etl/tests/__init__.py` (NEW)
- `etl/tests/test_load_freshwater.py` (NEW)
- `api/server.py` (EDIT)
- `tests/test_api_freshwater.py` (NEW)
- `tests/test_smoke.py` (EDIT, AC-20 only)
- `Makefile` (EDIT, `test:` target only — `etl/tests/` added)

**Estimated diff size**: ~518 LOC (additions + deletions; PR-1 is +30% over the 400-line budget — see §1.3).

**Acceptance criteria covered**: AC-1..AC-20 (all backend ACs).

**Self-contained check (CI)**:

1. `make test` exits 0.
2. `git diff origin/main -- api/server.py` shows only freshwater-related additions.
3. `git diff origin/main -- etl/load_worms.py` is empty (parity reference untouched).
4. `git log --grep "Co-Authored-By" --grep "AI attribution" origin/main..HEAD` returns 0 matches (AC-31 partial).

### 3.2 PR-2 — `feat(freshwater): add Búsquedas tab and per-row search icon`

**Title**: `feat(freshwater): add Búsquedas tab and per-row search icon`

**Branch**: `feat/freshwater-frontend-and-search-tab`

**Body draft**:

```markdown
## Summary

Adds the frontend half of the freshwater + Búsquedas feature:

- Static `web/search_urls.js` (14-entry engine catalog, kept in sync with the server by AC-21).
- Dynamic third toggle button in `#tree-source-toggle` (conditional on freshwater data being loaded).
- `matchesTreeSource` extended for `freshwater` source.
- Per-row search icon (`material-symbols-outlined` `search`) on every taxon row in every tree, at every rank; click selects taxon and switches detail panel to Búsquedas tab.
- Tab strip on detail panel: Búsquedas, Vernáculares, Sinónimos, Distribución (in this order).
- `loadDetail` fetches `/api/taxon/{id}/searches` alongside vernaculars / synonyms / distribution.
- AC-21 contract test parses `api/server.py::_SEARCH_ENGINES` and `web/search_urls.js::SEARCH_ENGINES` and asserts identical keys/labels/with_authorship in order.

## Dependency

Depends on PR-1 (backend endpoint and engine table exist). Stacked-to-main: this PR targets `main` directly and is rebased onto the merge commit of PR-1.

## What stays the same

- CoL and WoRMS UX is unchanged for users who never load freshwater data: AC-23 asserts the toggle button is not rendered when no freshwater root exists.
- Detail panel shell (`.detail-card`, `.detail-header`) is unchanged; only the inner tab strip is new.

## Acceptance criteria

AC-21 (engine contract), AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29 (frontend).

## Self-contained check

- `make test` is green; AC-21 contract test passes.
- `scripts/screenshot.py` captures the toggle, a selected taxon, and the Búsquedas panel populated with 14 links.
- Freshwater NOT loaded → toggle button not in DOM (AC-23).
- Freshwater loaded → toggle button visible, click drills freshwater tree (AC-22, AC-26).
- Per-row search icon absent for taxa with empty `scientific_name` (AC-25).

## Out of scope (deferred to PR-3)

- `make freshwater` target and README (PR-3).
```

**Files touched (full list)**:

- `web/search_urls.js` (NEW)
- `web/index.html` (EDIT)
- `web/app.js` (EDIT)
- `tests/test_smoke.py` (EDIT, AC-21 only)

**Estimated diff size**: ~250 LOC.

**Acceptance criteria covered**: AC-21, AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29.

**Self-contained check (CI + manual)**:

1. `make test` exits 0.
2. `pytest tests/test_smoke.py::test_search_engine_contract -v` passes.
3. Headless screenshot script (`scripts/screenshot.py`) confirms:
   - Freshwater NOT loaded → 2 toggle buttons.
   - Freshwater loaded → 3 toggle buttons.
   - Selected taxon shows tab strip + Búsquedas content with 14 anchors.

### 3.3 PR-3 — `docs(freshwater): README + make freshwater target`

**Title**: `docs(freshwater): add freshwater data source section and make target`

**Branch**: `docs/freshwater-readme-and-makefile`

**Body draft**:

```markdown
## Summary

Wraps the change with operator-facing artifacts:

- `make freshwater` Makefile target (loads `data/raw/freshwater.csv`); fails fast with a hint if the CSV is absent (mirrors the `worms:` pattern when the TSV is absent).
- `make load-all` updated to include `freshwater`.
- README "Freshwater Fishes" subsection under "Data sources" documenting the CSV format and the new tab.

## Dependency

Stacked-to-main after PR-2 (this PR is documentation + build; the prior PRs deliver the runtime behaviour).

## Acceptance criteria

AC-30 (Freshwater README subsection), AC-31 (no AI attribution in commit messages).

## Self-contained check

- `make -n freshwater` prints the loader invocation.
- `make freshwater` (without CSV) exits non-zero with the hint message.
- README contains a "Freshwater" subsection under "Data sources".
- `git log --grep "Co-Authored-By" --grep "AI attribution" origin/main..HEAD` returns 0 matches.

## Out of scope

- (none — this closes the change)
```

**Files touched (full list)**:

- `Makefile` (EDIT, `freshwater:` target + `load-all:` selector)
- `README.md` (EDIT)

**Estimated diff size**: ~35 LOC.

**Acceptance criteria covered**: AC-30, AC-31.

**Self-contained check (CI)**:

1. `make -n freshwater` shows the expected command line.
2. `make freshwater` (CSV absent) prints the hint and exits non-zero.
3. `grep -A 4 "Freshwater Fishes" README.md` shows the new subsection.

---

## 4. Apply order (strict sequence for `sdd-apply`)

`make test` must be green after each task. PRs are sequential; within a PR, tasks are sequential (single writer thread).

```
PR-1 — backend foundation
  T1.1   schema migration + indexes         (RED → GREEN)
  T1.2   synthetic root + valid rows         (RED → GREEN)
  T1.3   row-level validation                (RED → GREEN, 3 tests)
  T1.4   idempotent wipe-and-reload          (RED → GREEN)
  T1.5   species_count rollup                (RED → GREEN)
  T1.6   enable etl/tests in make test       (no test; Makefile edit)
  T1.7   Taxon schema: new fields            (RED → GREEN, 2 tests)
  T1.8   /api/domains extension              (RED → GREEN, 2 tests)
  T1.9   /api/taxon/{id}/children source     (RED → GREEN, 3 tests)
  T1.10  /api/taxon/{id}/searches endpoint   (RED → GREEN, 5 tests)
  T1.11  AC-20 OpenAPI assertion             (RED → GREEN)

PR-2 — frontend + engine contract
  T2.1   AC-21 contract test (RED only)      (RED — search_urls.js missing)
  T2.2   create web/search_urls.js           (GREEN — contract test passes)
  T2.3   matchesTreeSource freshwater branch (RED → GREEN)
  T2.4   dynamic freshwater toggle button    (RED → GREEN)
  T2.5   per-row search icon render          (RED → GREEN)
  T2.6   icon click → Búsquedas tab          (RED → GREEN)
  T2.7   tab strip render                    (RED → GREEN)
  T2.8   Búsquedas content (14 anchors)      (RED → GREEN)
  T2.9   loadDetail searches fetch           (RED → GREEN)

PR-3 — build target + docs
  T3.1   make freshwater target              (no test; Makefile edit)
  T3.2   README Freshwater subsection        (no test; doc edit)
  T3.3   AC-31 commit attribution gate       (gate-check, see §6)
```

Within PR-1, the two commits land as `etl: add freshwater loader with idempotent migration` (after T1.6) then `api: add freshwater slice and /searches endpoint` (after T1.11). Within PR-2, the two commits land as `web: add SEARCH_ENGINES catalog synced with api` (after T2.2) then `web: add Búsquedas tab and per-row search icon` (after T2.9). PR-3 is one commit.

---

## 5. Task list

Every checkbox ends with exactly one terminal ownership marker. `implementation` covers RED/GREEN/TRIANGULATE/REFACTOR, code, tests, and apply-owned verification. `parent` is reserved for explicit post-apply bounded-review and lifecycle-gate actions. Parent-owned actions are grouped in §7.

### PR-1 tasks

#### T1.1 — Idempotent migration for `freshwater_id` / `freshwater_parent_id` (AC-6)

- **Goal**: Loader adds the two new columns on a fresh DB and the indexes on every run, idempotently.
- **Files touched**: `etl/schema_v4.sql` (NEW), `etl/load_freshwater.py` (NEW — skeleton only).
- **TDD evidence**:
  - RED: `etl/tests/test_load_freshwater.py::test_load_freshwater_adds_columns_on_fresh_db` — drops a fresh SQLite (via `tmp_path` + `etl/schema.sql`), asserts `PRAGMA table_info(taxon)` reports both new columns after first run; runs the loader a second time and asserts no error.
  - GREEN: implement the migration block — `PRAGMA table_info` → `ALTER TABLE` → `executescript(schema_v4.sql)`.
  - Verification: `pytest etl/tests/test_load_freshwater.py::test_load_freshwater_adds_columns_on_fresh_db -v` passes.
- **Commit message**: combined into commit 1.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.2 — Synthetic root + valid-row insertion (AC-1)

- **Goal**: Loader inserts the `Freshwater Fishes` synthetic root with `rank="collection"` and processes top-level CSV rows under it.
- **Files touched**: `etl/load_freshwater.py`.
- **TDD evidence**:
  - RED: `etl/tests/test_load_freshwater.py::test_load_freshwater_inserts_synthetic_root_and_orders` — fixture CSV with 4 rows (synthetic root + 3 orders); assert 4 rows in `taxon` with `freshwater_id` set, root has `rank == "collection"` and `freshwater_parent_id IS NULL`.
  - GREEN: implement `KNOWN_RANKS`, header detection, `BEGIN…COMMIT`, root insert + per-row INSERT, `fw_map` for parent resolution.
  - Verification: `pytest etl/tests/test_load_freshwater.py::test_load_freshwater_inserts_synthetic_root_and_orders -v` passes.
- **Commit message**: combined into commit 1.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.3 — Row-level validation: skip orphans, empties, duplicates (AC-2, AC-3, AC-4)

- **Goal**: Loader logs a WARNING with the line number and skips malformed rows without aborting.
- **Files touched**: `etl/load_freshwater.py`.
- **TDD evidence**:
  - RED: `etl/tests/test_load_freshwater.py::test_load_freshwater_skips_orphan_parents`, `::test_load_freshwater_skips_empty_scientific_name`, `::test_load_freshwater_skips_duplicate_freshwater_id`. Each fixture mixes valid rows with one bad row; capture stderr (use `capsys`); assert WARNING logged with line number; assert only valid rows in DB.
  - GREEN: implement per-row validation per spec §4.2 / §4.5.
  - Verification: all three pass.
- **Commit message**: combined into commit 1.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.4 — Idempotent wipe-and-reload (AC-5)

- **Goal**: Re-running the loader deletes prior freshwater rows and inserts the new set; CoL and WoRMS rows are untouched.
- **Files touched**: `etl/load_freshwater.py`.
- **TDD evidence**:
  - RED: `etl/tests/test_load_freshwater.py::test_load_freshwater_is_idempotent` — seed CoL/WoRMS rows (just count), run loader, capture counts, run loader again, assert freshwater count returns to N after the second run and CoL/WoRMS counts are unchanged.
  - GREEN: add `DELETE FROM taxon WHERE freshwater_id IS NOT NULL` at start of transaction.
  - Verification: passes.
- **Commit message**: combined into commit 1.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.5 — `species_count` rollup on the synthetic root (AC-7)

- **Goal**: After the loader finishes, the synthetic root's `species_count` equals the total number of CSV rows whose rank is `species` or `subspecies`.
- **Files touched**: `etl/load_freshwater.py`.
- **TDD evidence**:
  - RED: `etl/tests/test_load_freshwater.py::test_load_freshwater_rolls_up_species_count` — fixture with 5 species + 3 genus + 2 family; assert root's `species_count == 5`.
  - GREEN: implement the recursive CTE update per spec §4.4.
  - Verification: passes.
- **Commit message**: combined into commit 1.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.6 — Enable loader tests in `make test`

- **Goal**: `make test` discovers tests under both `tests/` and `etl/tests/`.
- **Files touched**: `Makefile` (edit only — extend `test:` target).
- **TDD evidence**: no test; this is a build-discovery change required for AC-1..AC-7 to be visible in `make test`. Verification: `make test` runs both directories.
- **Commit message**: combined into commit 1.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.7 — `Taxon` schema: new optional fields (AC-13, AC-14)

- **Goal**: `GET /api/taxon/{id}` returns `freshwater_id` and `freshwater_parent_id` (both nullable) on every taxon.
- **Files touched**: `api/server.py`.
- **TDD evidence**:
  - RED: `tests/test_api_freshwater.py::test_taxon_includes_freshwater_id`, `::test_taxon_without_freshwater_id`. First seeds a row with `freshwater_id=42`; second queries a CoL-only row.
  - GREEN: extend `Taxon` model with the two optional fields; pass through in `_row_to_taxon`.
  - Verification: both pass.
- **Commit message**: combined into commit 2.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.8 — `/api/domains` extension (AC-8, AC-9)

- **Goal**: Freshwater synthetic root appears in `/api/domains` only when freshwater data is loaded.
- **Files touched**: `api/server.py`.
- **TDD evidence**:
  - RED: `tests/test_api_freshwater.py::test_domains_without_freshwater` (asserts 5-element list), `::test_domains_with_freshwater` (seeds root; asserts 6-element list including `Freshwater Fishes`).
  - GREEN: extend the WHERE clause with `OR (freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL)`.
  - Verification: both pass.
- **Commit message**: combined into commit 2.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.9 — `/api/taxon/{id}/children` source regex + freshwater branch (AC-10, AC-11, AC-12)

- **Goal**: `source=freshwater` returns freshwater children; `source=col` and `source=worms` are byte-identical to today.
- **Files touched**: `api/server.py`.
- **TDD evidence**:
  - RED: `tests/test_api_freshwater.py::test_children_source_freshwater` (seeds root + 2 orders; assert 2 orders returned), `::test_children_source_col_with_freshwater_root` (assert empty), `::test_children_source_worms_with_freshwater_root` (assert empty).
  - GREEN: widen regex to `^(col|worms|freshwater)$`; add new branch `freshwater_parent_id = ? AND freshwater_id IS NOT NULL`.
  - Verification: all three pass. `git diff origin/main -- api/server.py` confirms `source=col` and `source=worms` branches unchanged.
- **Commit message**: combined into commit 2.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.10 — `/api/taxon/{id}/searches` endpoint (AC-15, AC-16, AC-17, AC-18, AC-19)

- **Goal**: New endpoint returns 14 server-composed search-engine links; BHL and Scholar URLs append authorship; 404 on unknown id; 422 on empty `scientific_name`.
- **Files touched**: `api/server.py`.
- **TDD evidence**:
  - RED: `tests/test_api_freshwater.py::test_searches_returns_14_entries` (length and order), `::test_searches_urls_are_well_formed` (`urlparse(...).scheme in {"http", "https"}` for all 14), `::test_searches_authorship_on_bhl_and_scholar_only` (Astyanax mexicanus; `bhl.url` contains `De%20Filippi`; `scholar.url` contains it; `google.url` does NOT), `::test_searches_422_on_empty_scientific_name`, `::test_searches_404_on_unknown_id`.
  - GREEN: add module-level `_SEARCH_ENGINES` constant; add `_build_search_links` helper; add `SearchLink` Pydantic model; add `get_searches` endpoint with 404 / 422 branches.
  - Verification: all five pass.
- **Commit message**: combined into commit 2.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

#### T1.11 — OpenAPI path assertion includes `/searches` (AC-20)

- **Goal**: `tests/test_smoke.py::test_openapi_schema_is_valid_json` enumerates the new path so accidental route removal fails CI.
- **Files touched**: `tests/test_smoke.py`.
- **TDD evidence**:
  - RED: extend the `expected_paths` set with `/api/taxon/{taxon_id}/searches`.
  - GREEN: passes once T1.10's endpoint is registered.
  - Verification: `pytest tests/test_smoke.py::test_openapi_schema_is_valid_json -v` passes.
- **Commit message**: combined into commit 2.
- **PR slice**: PR-1. <!-- sdd-owner: implementation -->

### PR-2 tasks

- [x] T2.1 — AC-21 contract test (RED phase)

- **Goal**: Write the cross-file engine sync test before the JS file exists so it fails on the contract missing.
- **Files touched**: `tests/test_smoke.py`.
- **TDD evidence**:
  - RED: `tests/test_smoke.py::test_search_engine_contract` reads `api/server.py::_SEARCH_ENGINES` (exists from PR-1) and `web/search_urls.js::SEARCH_ENGINES` (missing); asserts identical `key` / `label` / `with_authorship` in order. Watch fail with `FileNotFoundError` or "missing engine contract entries".
  - GREEN deferred to T2.2.
  - Verification: `pytest tests/test_smoke.py::test_search_engine_contract -v` fails as expected.
- **Commit message**: combined into commit 3.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

- [x] T2.2 — Create `web/search_urls.js` (AC-21 GREEN)

- **Goal**: Static 14-entry engine catalog mirroring `api/server.py::_SEARCH_ENGINES`.
- **Files touched**: `web/search_urls.js` (NEW).
- **TDD evidence**:
  - GREEN: export `SEARCH_ENGINES` with 14 entries (key, label, icon, template, with_authorship for bhl/scholar only). Add file header comment: "DO NOT REFORMAT — parsed by tests/test_smoke.py::test_search_engine_contract".
  - Verification: AC-21 contract test passes.
- **Commit message**: combined into commit 3.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

- [x] T2.3 — `matchesTreeSource` extended for `freshwater` (AC-26, AC-29)

- **Goal**: Tree-source filter recognises `freshwater`; switching to/from freshwater clears the same caches as the existing CoL↔WoRMS toggle.
- **Files touched**: `web/app.js`.
- **TDD evidence**:
  - RED: extend `scripts/screenshot.py` (or a new `tests/test_frontend_unit.py` if we add one) with assertions: `matchesTreeSource({coldp_id: "x"})` → true for `"col"`; `matchesTreeSource({freshwater_id: 1})` → true for `"freshwater"`; `matchesTreeSource({freshwater_id: 1})` → false for `"col"`. Watch fail before the branch is added.
  - GREEN: extend `matchesTreeSource` to handle `state.treeSource === "freshwater"`.
  - Verification: assertions pass.
- **Commit message**: combined into commit 4.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

- [x] T2.4 — Dynamic third toggle button + event delegation (AC-22, AC-23)

- **Goal**: `Freshwater` button is appended to `#tree-source-toggle` only when at least one root has `freshwater_id` set; the click handler is delegated so dynamically added buttons work.
- **Files touched**: `web/app.js`, `web/index.html` (CSS for `.tree-source-btn` if missing).
- **TDD evidence**:
  - RED: extend `scripts/screenshot.py` with DOM assertions:
    - With a freshwater root in `/api/domains` → `#tree-source-toggle` has 3 buttons with `data-tree-source` values `col`, `worms`, `freshwater` in order.
    - Without a freshwater root → only `col` and `worms` buttons.
    - After clicking the `freshwater` button, `aria-pressed="true"` on it.
  - GREEN: in `boot()`, after `state.roots` is populated, append the button if `roots.some(r => r.freshwater_id != null)`. Replace the `forEach` listener at `app.js:1208` with a delegated `document.addEventListener("click", ...)` branch handling `data-action="switch-tree-source"` (or use `closest("[data-tree-source]")`).
  - Verification: screenshot assertions pass; clicking the button toggles state.
- **Commit message**: combined into commit 4.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

- [x] T2.5 — Per-row search icon render (AC-25)

- **Goal**: Every taxon row whose `scientific_name` is non-empty shows a search icon button at the end of the metaBlock.
- **Files touched**: `web/app.js`.
- **TDD evidence**:
  - RED: `scripts/screenshot.py` DOM assertion: `renderNodeRow({id: 1, scientific_name: ""})` does NOT produce a `data-action="search-from-row"` element.
  - GREEN: in `renderNodeRow`, append the icon button to `metaBlock` when `taxon.scientific_name` is truthy, else `null`.
  - Verification: empty-name rows render no icon; named rows render the icon.
- **Commit message**: combined into commit 4.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

- [x] T2.6 — Icon click handler → Búsquedas tab (AC-24)

- **Goal**: Clicking the per-row search icon selects the taxon AND sets `state.detailTab = "busquedas"`.
- **Files touched**: `web/app.js`.
- **TDD evidence**:
  - RED: `scripts/screenshot.py` step: click the icon on a row whose vernaculars/synonyms/distribution all have data; assert detail panel's tab strip shows Búsquedas active.
  - GREEN: extend the click delegation with `else if (action === "search-from-row") { state.detailTab = "busquedas"; selectTaxon(id); }`.
  - Verification: clicking the icon opens the Búsquedas tab even when other tabs have data.
- **Commit message**: combined into commit 4.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

- [x] T2.7 — Detail panel tab strip render (AC-27)

- **Goal**: Detail panel renders 4 tab buttons in order (Búsquedas, Vernáculares, Sinónimos, Distribución); only tabs with data (plus Búsquedas always) are visible.
- **Files touched**: `web/app.js`, `web/index.html` (CSS for `.detail-tabs`, `.detail-tab`, `.detail-tab-active`).
- **TDD evidence**:
  - RED: `scripts/screenshot.py` DOM assertion: select a taxon with all 4 data types; assert 4 tab buttons present in order.
  - GREEN: restructure `renderDetailPanel` to render tab strip header + 4 content sections, only the active one visible via inline `style.display`.
  - Verification: tab strip renders; clicking a tab switches `state.detailTab` and `render()` updates visibility.
- **Commit message**: combined into commit 4.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

- [x] T2.8 — Búsquedas content render (AC-28)

- **Goal**: Búsquedas section renders exactly 14 anchor elements with `target="_blank"` and `href` matching the templates from `spec.md` §6.1.
- **Files touched**: `web/app.js`.
- **TDD evidence**:
  - RED: `scripts/screenshot.py` DOM assertion: 14 anchors inside `.detail-tab-content[data-tab-content="busquedas"]`.
  - GREEN: render 14 anchors from `state.detail.searches` with `target="_blank"`, `href=link.url`, label/icon from the link object.
  - Verification: count assertion passes.
- **Commit message**: combined into commit 4.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

- [x] T2.9 — `loadDetail` includes `searches` (AC-26)

- **Goal**: Selecting a taxon fires one fetch per data type, including `/api/taxon/{id}/searches`.
- **Files touched**: `web/app.js`.
- **TDD evidence**:
  - RED: `scripts/screenshot.py` step with fetch mock: select a taxon; assert `fetch` was called with `/api/taxon/{id}/searches` exactly once and with `?source=freshwater` on children fetches.
  - GREEN: extend `loadDetail`'s `Promise.all` to include `taxon.scientific_name ? api(\`/api/taxon/${id}/searches\`) : Promise.resolve([])`. Add`searches: searches` to `state.detail`.
  - Verification: network log assertions pass.
- **Commit message**: combined into commit 4.
- **PR slice**: PR-2. <!-- sdd-owner: implementation -->

### PR-3 tasks

- [x] T3.1 — `make freshwater` target + `load-all` selector

- **Goal**: Operator can run `make freshwater` to load the CSV; target fails fast with a hint when the CSV is absent; `make load-all` includes the new source.
- **Files touched**: `Makefile`.
- **TDD evidence**: no test; this is a build target. Verification: `make -n freshwater` shows the expected command; `make freshwater` without CSV prints the hint and exits non-zero.
- **Commit message**: combined into commit 6.
- **PR slice**: PR-3. <!-- sdd-owner: implementation -->

- [x] T3.2 — README Freshwater subsection (AC-30)

- **Goal**: README documents the Freshwater data source (CSV input format + `make freshwater` invocation) and the Búsquedas tab.
- **Files touched**: `README.md`.
- **TDD evidence**: no test; documentation edit. Verification: `grep -A 12 "Freshwater Fishes" README.md` shows the new subsection with CSV columns and the make target.
- **Commit message**: combined into commit 6.
- **PR slice**: PR-3. <!-- sdd-owner: implementation -->

### Post-apply bounded review (parent-owned actions)

These are lifecycle gates, not implementation work. They run AFTER `sdd-apply` reports completion and BEFORE `sdd-verify` launches.

- [ ] Confirm chain shape (stacked-to-main) and PR count (3) with the user before `sdd-apply` launches — `decision_needed_before_apply: Yes`. <!-- sdd-owner: parent -->
- [ ] Open PR-1 against `main`; verify size exception rationale is documented in the PR body. <!-- sdd-owner: parent -->
- [ ] After PR-1 merges, rebase PR-2 onto PR-1's merge commit (stacked-to-main); open PR-2. <!-- sdd-owner: parent -->
- [ ] After PR-2 merges, rebase PR-3 onto PR-2's merge commit; open PR-3. <!-- sdd-owner: parent -->
- [ ] Run `gentle-ai review status --cwd <repo> --contract gentle-ai.review-integration/v2 --agent pi --next-transition` after each PR merge (per orchestrator's authority-first terminal procedure). <!-- sdd-owner: parent -->

---

## 6. Risk checklist (mapped from `design.md` §10)

| Design §10 risk | Severity | Mitigating task(s) |
| ----------------- | ---------- | --------------------- |
| `collection` rank breaks client code that switches on rank | Med | T1.7 (API `RANK_ORDER` extended; SQL `CASE` added), T2.3 (`RANK_ORDER` JS array prepended; `matchesTreeSource` only checks `coldp_id`/`worms_id`/`freshwater_id` — no rank-switching) |
| `RANK_PLURAL` falls back to `Collections` | Low | T2.3 (documented in code; rank never appears in a user-visible label outside the synthetic root's name) |
| Recursive CTE `species_count` rollup only updates the synthetic root, not deeper nodes | Med | T1.5 (matches `load_worms.py` precedent; documented in loader docstring) |
| No `FOREIGN KEY` on `freshwater_parent_id` | Low | T1.1 (intentional; mirrors `worms_parent_id`; orphans logged-and-skipped) |
| Per-row icon increases tree DOM size | Low | T2.5 (single `<button>`, ~30 bytes per row × 16K rows = ~500KB total; negligible) |
| `/searches` returns 14 entries even for taxa with no useful searches | Low | T1.10 (422 guard on empty `scientific_name`); T2.9 (frontend mirror guard) |
| `encodeURIComponent` (client) vs `urllib.parse.quote_plus` (server) differ on non-ASCII | Med | AC-16 asserts well-formed ASCII URLs only; documented in spec.md §6.4 |
| AC-21 contract test parses `web/search_urls.js` via regex | Med | T2.2 (file header comment: "DO NOT REFORMAT"); AC-21 only checks `key`/`label`/`with_authorship`, not `template` |
| Boot dynamic button insertion requires delegation | Low | T2.4 (converts `forEach` to delegated handler; affects ~5 lines) |
| `loadDetail` fetches `searches` even when Búsquedas tab never opens | Low | T2.9 (acceptable per spec §5.6; 1 extra small request per selection) |
| `make freshwater` fails with ugly error on malformed CSV | Med | T1.3 (loader logs line+reason per row); T3.1 (Makefile target fails fast with hint when CSV absent) |
| `load-all` requires three downloads but `freshwater` has no URL | Low | T3.1 (Makefile target uses a no-source recipe with hint; matches the pattern in `load_worms.py` if/when it gets one) |

Additional risks from `spec.md` §10 (mirrored here for completeness):

| Spec §10 risk | Severity | Mitigating task(s) |
| --------------- | ---------- | --------------------- |
| CSV with mixed header conventions | Med | T1.2 (header detection per spec §4.2) |
| Orphan parents in CSV | Med | T1.3 (logged + skipped) |
| Synthetic root id collision with CoL/WoRMS | Low | T1.2 (loader reserves `freshwater_id=1` for the root; uses SQLite's `lastrowid` for `taxon.id`; no conflict possible) |
| Per-row icon visual noise on 16K-row trees | Low | T2.5 (16px icon, hover-only color shift, gated by `scientific_name`) |
| Search URL drift between server and client | Med | T2.1, T2.2 (AC-21 contract test enforces byte-identical keys/labels/with_authorship) |
| `/api/taxon/{id}/children?source=freshwater` accidentally returns CoL data | Low | T1.9 (new WHERE branch filters on `freshwater_parent_id` AND `freshwater_id IS NOT NULL`; CoL rows have `freshwater_id IS NULL` by construction) |
| Tab strip breaks the existing detail panel layout | Med | T2.7 (tab strip lives inside the same `.detail-card`; no changes to `.detail-header`, `.detail-section`, or the card's outer shell) |

---

## 7. Merge / rebase policy (per chained-pr skill)

### 7.1 Branch layout

- `main` is the integration branch.
- `feat/freshwater-loader-and-api` is PR-1's branch, cut from `main`.
- `feat/freshwater-frontend-and-search-tab` is PR-2's branch, cut from PR-1's merge commit (rebase onto `main` after PR-1 merges).
- `docs/freshwater-readme-and-makefile` is PR-3's branch, cut from PR-2's merge commit (rebase onto `main` after PR-2 merges).

### 7.2 Stacked-to-main

Each PR targets `main` directly (no tracker branch). The `sdd-apply` sub-agent pushes each branch and opens a PR. After PR-1 merges, PR-2 is rebased onto the merge commit of PR-1 (or, if PR-1 was squash-merged, rebased onto `main`). Same for PR-3.

```
PR-1:  main ──┬── A ── B  (feat/freshwater-loader-and-api)
              │
              ▼ merge
            main ──┬── C ── D  (feat/freshwater-frontend-and-search-tab, rebased)
                    │
                    ▼ merge
                  main ──┬── E  (docs/freshwater-readme-and-makefile, rebased)
                          │
                          ▼ merge
                        main (clean, linear history)
```

### 7.3 Merge vs rebase discipline

- **Squash merge is forbidden** for PR-2 and PR-3. Squash merge destroys the `freshwater_id` lineage the contract test reads (AC-21 walks `api/server.py::_SEARCH_ENGINES` by source line); a non-squash merge is required so the engine table stays byte-identical between the file on disk and the file AC-21 reads.
- **Rebase before merge** for PR-2 and PR-3 — keep history linear.
- **PR order matters**: PR-2 cannot land before PR-1; PR-3 cannot land before PR-2.
- **No long-lived feature branches** — each PR's branch is deleted after merge.

### 7.4 Conflict windows

| PR | What can conflict | Mitigation |
|----|-------------------|------------|
| PR-2 rebase onto PR-1 | `api/server.py` (if PR-1 changed it after PR-2 was cut) | PR-2 only touches `web/*` and `tests/test_smoke.py`; `api/server.py` is untouched after PR-1 closes. Re-resolve if PR-1 made post-cut edits |
| PR-3 rebase onto PR-2 | `Makefile` (PR-1 added `etl/tests/` to `test:`) and `README.md` (PR-2 might add frontend docs) | PR-3 adds `freshwater:` target and a different README subsection; expected to be conflict-free |

### 7.5 Rollback boundaries

- PR-1 rollback: `git revert -m 1 <merge-sha>` removes the loader + API additions; SQLite on existing DBs keeps the columns (they're nullable and indexed); `/api/domains` reverts to 5 roots.
- PR-2 rollback: `git revert -m 1 <merge-sha>` removes `web/search_urls.js`, the toggle button, the icon, the tab strip. CoL/WoRMS UX reverts to today's behaviour.
- PR-3 rollback: `git revert -m 1 <merge-sha>` removes the Makefile target and README section. No runtime impact (loader and API still work via direct invocation).

Each rollback is independent — none of the three PRs depends on the next to keep the prior PRs' tests green.

---

## 8. Acceptance criteria quick reference

| AC | PR | Task(s) | Test name |
| ---- | ---- | --------- | ----------- |
| AC-1 | PR-1 | T1.2 | `test_load_freshwater_inserts_synthetic_root_and_orders` |
| AC-2 | PR-1 | T1.3 | `test_load_freshwater_skips_orphan_parents` |
| AC-3 | PR-1 | T1.3 | `test_load_freshwater_skips_empty_scientific_name` |
| AC-4 | PR-1 | T1.3 | `test_load_freshwater_skips_duplicate_freshwater_id` |
| AC-5 | PR-1 | T1.4 | `test_load_freshwater_is_idempotent` |
| AC-6 | PR-1 | T1.1 | `test_load_freshwater_adds_columns_on_fresh_db` |
| AC-7 | PR-1 | T1.5 | `test_load_freshwater_rolls_up_species_count` |
| AC-8 | PR-1 | T1.8 | `test_domains_without_freshwater` |
| AC-9 | PR-1 | T1.8 | `test_domains_with_freshwater` |
| AC-10 | PR-1 | T1.9 | `test_children_source_freshwater` |
| AC-11 | PR-1 | T1.9 | `test_children_source_col_with_freshwater_root` |
| AC-12 | PR-1 | T1.9 | `test_children_source_worms_with_freshwater_root` |
| AC-13 | PR-1 | T1.7 | `test_taxon_includes_freshwater_id` |
| AC-14 | PR-1 | T1.7 | `test_taxon_without_freshwater_id` |
| AC-15 | PR-1 | T1.10 | `test_searches_returns_14_entries` |
| AC-16 | PR-1 | T1.10 | `test_searches_urls_are_well_formed` |
| AC-17 | PR-1 | T1.10 | `test_searches_authorship_on_bhl_and_scholar_only` |
| AC-18 | PR-1 | T1.10 | `test_searches_422_on_empty_scientific_name` |
| AC-19 | PR-1 | T1.10 | `test_searches_404_on_unknown_id` |
| AC-20 | PR-1 | T1.11 | `test_openapi_schema_is_valid_json` (extended) |
| AC-21 | PR-2 | T2.1, T2.2 | `test_search_engine_contract` |
| AC-22 | PR-2 | T2.4 | `scripts/screenshot.py` DOM assertion |
| AC-23 | PR-2 | T2.4 | `scripts/screenshot.py` DOM assertion |
| AC-24 | PR-2 | T2.6 | `scripts/screenshot.py` interaction |
| AC-25 | PR-2 | T2.5 | `scripts/screenshot.py` DOM assertion |
| AC-26 | PR-2 | T2.9 | `scripts/screenshot.py` fetch mock |
| AC-27 | PR-2 | T2.7 | `scripts/screenshot.py` DOM assertion |
| AC-28 | PR-2 | T2.8 | `scripts/screenshot.py` DOM assertion |
| AC-29 | PR-2 | T2.3, T2.4 | `scripts/screenshot.py` interaction |
| AC-30 | PR-3 | T3.2 | `grep` check on README |
| AC-31 | PR-3 | T3.3 (gate) | `git log --grep` check (post-apply) |

---

## 9. Notes for `sdd-apply`

- `make test` runs `pytest tests/ etl/tests/ -v` after T1.6. Until T1.6 lands, loader tests run via direct invocation: `pytest etl/tests/test_load_freshwater.py -v`.
- `tests/test_api_freshwater.py` uses `TestClient(app)` against an in-memory SQLite (seeded per test). It does NOT require `taxa.db` to be populated on disk — mirrors `tests/test_smoke.py::TestDbBackedEndpoints`.
- `etl/tests/__init__.py` is required for pytest package discovery.
- Strict TDD mode is on. Each task's RED phase must show the test failing for the asserted reason; the GREEN phase must show the test passing. The orchestrator's gatekeeper validates each phase output before launching the next sub-agent (per `sdd-apply` standard contract).
- `Co-Authored-By:` is forbidden in all commit messages. AC-31's gate check (`git log --grep "Co-Authored-By"`) runs in the post-apply bounded review (parent-owned).
- `docs(test_smoke.py::test_search_engine_contract)` reads `api/server.py` as text and slices from `_SEARCH_ENGINES = [` to the matching `]`. Reformatting the Python file (e.g., moving the constant to a separate module) requires updating the test. Keep the constant in `api/server.py`.
