# apply-progress — add-freshwater-and-search

## Plan recap

3 PRs, stacked-to-main:

- **PR-1** (backend foundation): loader + schema + API + tests. ~518 LOC.
- **PR-2** (frontend + engine contract): `web/search_urls.js`, dynamic toggle, per-row icon, Búsquedas tab strip. ~250 LOC.
- **PR-3** (build + docs): `make freshwater` target, README section. ~35 LOC.

Conventional commits, strict TDD (RED → GREEN → TRIANGULATE → REFACTOR),
no AI attribution. Tests offline (`make test`).

---

## PR-1 — `feat(freshwater): add loader, API slice, and /searches endpoint`

### Commit chain

| # | SHA | Title | ACs closed | Status |
| - | --- | ----- | ---------- | ------ |
| RED | `11d32a4` | `test(etl): scaffold freshwater loader tests with SQLite in-memory fixture` | (none — scaffolds 7 failing tests) | landed (pre-this-batch) |
| 2 | `211af74` | `feat(etl): implement freshwater loader with single-pass CSV parse` | AC-1, AC-2, AC-3, AC-4, AC-5, AC-7 | landed (this batch) |
| 3 | `4dd1b75` | `feat(etl): add freshwater schema migration with idempotent ALTER` | AC-6 | landed (this batch) |

### Commit 2 — `feat(etl): implement freshwater loader with single-pass CSV parse`

**SHA**: `211af741bf423589d70c41b4cb85ae43373ac2bf`

**Files created/modified**

| File | Action | Notes |
| ---- | ------ | ----- |
| `etl/load_freshwater.py` | NEW | Wipe-and-reload loader; single-pass CSV; mirrors `load_worms.py`'s pattern but isolates freshwater rows under `freshwater_parent_id`. Defensive `_require_freshwater_columns` guard at the top (the migration lives in commit 3). |
| `etl/tests/conftest.py` | MODIFIED | Added `bootstrapped_db` fixture (yields a `tmp_path/taxa.db` with the v1+v2+v3 schema **plus** the freshwater overlay columns so commit-2 tests have a stable base). Updated `BASE_SCHEMA` and `write_csv` (`with_header` flag dropped — never used). |
| `etl/tests/test_load_freshwater.py` | MODIFIED | Tests AC-1..AC-5, AC-7 swapped from the unused `db_conn` + `tmp_path` pattern to `bootstrapped_db`. `_seed_col_and_worms` reshaped so its rows match the test's CoL/WoRMS/CoL+WoRMS count assertions (Chromista is now a CoL+WoRMS row, not a WoRMS-only row). |

**RED state** (immediately before commit 2):

```text
$ .venv/bin/python -m pytest etl/tests/test_load_freshwater.py -v
...
etl/tests/test_load_freshwater.py::test_load_freshwater_inserts_synthetic_root_and_orders FAILED [ 14%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_orphan_parents FAILED [ 28%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_empty_scientific_name FAILED [ 42%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_duplicate_freshwater_id FAILED [ 57%]
etl/tests/test_load_freshwater.py::test_load_freshwater_is_idempotent FAILED [ 71%]
etl/tests/test_load_freshwater.py::test_load_freshwater_adds_columns_on_fresh_db FAILED [ 85%]
etl/tests/test_load_freshwater.py::test_load_freshwater_rolls_up_species_count FAILED [100%]

=========== 7 failed in 0.22s ===========
```

All seven RED — loader subprocess errors out because `etl/load_freshwater.py` either returns "DB not found" (defensive pre-migration guard) or hits "no such table: taxon" (ALTER on a fresh empty DB).

**GREEN state** (immediately after commit 2):

```text
$ .venv/bin/python -m pytest etl/tests/test_load_freshwater.py -v
etl/tests/test_load_freshwater.py::test_load_freshwater_inserts_synthetic_root_and_orders PASSED [ 14%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_orphan_parents PASSED [ 28%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_empty_scientific_name PASSED [ 42%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_duplicate_freshwater_id PASSED [ 57%]
etl/tests/test_load_freshwater.py::test_load_freshwater_is_idempotent PASSED [ 71%]
etl/tests/test_load_freshwater.py::test_load_freshwater_adds_columns_on_fresh_db FAILED [ 85%]
etl/tests/test_load_freshwater.py::test_load_freshwater_rolls_up_species_count PASSED [100%]

=========== 1 failed, 6 passed in 0.29s ===========
```

6 of 7 GREEN. **AC-6 stays RED** with the expected error — the loader's defensive guard raises because the test's explicit bootstrap creates a `taxon` table without the freshwater columns:

```text
sqlite3.OperationalError: taxon table is missing required columns:
  ['freshwater_id', 'freshwater_parent_id']. Apply etl/schema_v4.sql
  before running this loader.
```

This is the intended commit-2 boundary: loader + CSV ingestion works on a DB whose overlay columns are present; the in-loader migration is commit 3's work.

**Implementation notes**

- Single-pass loader. CSV columns: `freshwater_id, freshwater_parent_id, rank, scientific_name, authorship`. Header row auto-detected: if the first row's `rank` isn't in `KNOWN_RANKS`, treat the row as a header.
- Synthetic root (`rank='collection'`, `freshwater_id=1`, `freshwater_parent_id=NULL`, `scientific_name='Freshwater Fishes'`) inserted before any CSV row. CSV rows with `freshwater_id=1` that match the root are silently skipped (no warning noise when the user's CSV also ships the root row).
- `fw_map: dict[int, int]` maps each inserted `freshwater_id` to the SQLite `taxon.id` of its row. CSV `freshwater_parent_id` is translated through this map before insert.
- Validation order per row: missing/non-integer `freshwater_id` → skip; duplicate `freshwater_id` → skip with WARNING; empty `scientific_name` → skip with WARNING; unknown rank → skip with WARNING; missing parent or parent not yet seen → skip with WARNING. Each WARNING names the 1-indexed line number.
- `DELETE FROM taxon WHERE freshwater_id IS NOT NULL` is the wipe (CoL rows with `freshwater_id IS NULL` and WoRMS-only rows are untouched). Synthetic root re-inserted after the wipe inside the same transaction.
- `parent_id` is hardcoded to `NULL` for every CSV row — freshwater rows live in their own hierarchy so they don't pollute the CoL view (per spec §2.1 + `matchesTreeSource` in `web/app.js`).
- `species_count` rollup uses the recursive CTE from spec §4.4 against the synthetic root's `taxon.id`.
- Summary line at end: `Inserted: N` / `Skipped by validation: M` / `Total CSV rows: N+M`. Plus a `WARNING: 0 rows loaded` when nothing got inserted.
- DB_PATH: hardcoded default `"data/db/taxa.db"` (matching `load_worms.py`); overridable via `argv[2]` so the test harness can drive the loader against `tmp_path/taxa.db`.

**Risk notes / deviations from spec**

- The task description for commit 2 says "Required schema columns MUST already exist (commit 3 will add the ALTER TABLE)". To honour that boundary, the conftest's `BASE_SCHEMA` and the `bootstrapped_db` fixture were extended to ship the overlay columns. Production users running the loader against a freshly-built DB will need `etl/schema_v4.sql` applied first (commit 3 makes that automatic).
- `_seed_col_and_worms` in `test_load_freshwater.py` was reshaped: the original seeded 2 CoL-only rows + 2 WoRMS-only rows, but the AC-5 assertions expect 2 CoL-only + 1 WoRMS-only + 1 CoL+WoRMS. The seed now matches the assertions (Chromista has both `coldp_id='col-chrom-1'` and `worms_id=2`).
- The defensive guard uses `sqlite3.OperationalError` rather than `print + sys.exit(1)` so the subprocess surfaces a clean traceback in stderr — easier to debug in CI than a plain string.

### Commit 3 — `feat(etl): add freshwater schema migration with idempotent ALTER`

**SHA**: `4dd1b754d8a0973eeb92b711081f6c7afeb6db56`

**Files created/modified**

| File | Action | Notes |
| ---- | ------ | ----- |
| `etl/schema_v4.sql` | NEW | Two `ALTER TABLE taxon ADD COLUMN ...` statements + two partial `CREATE INDEX IF NOT EXISTS` statements. The FK constraint is intentionally **omitted** (SQLite ALTER TABLE does not support adding `REFERENCES`; referential integrity is enforced at the loader + API layers). |
| `etl/load_freshwater.py` | MODIFIED | Replaced the defensive `_require_freshwater_columns` guard with `_apply_schema_v4_if_needed`. The new helper runs `PRAGMA table_info(taxon)` and, if either column is missing, executes `etl/schema_v4.sql` via `executescript`. Re-running on a DB that already has the columns is a no-op. |

**RED state** (immediately before commit 3, == GREEN state of commit 2):

```text
$ .venv/bin/python -m pytest etl/tests/test_load_freshwater.py -v
...
FAILED etl/tests/test_load_freshwater.py::test_load_freshwater_adds_columns_on_fresh_db
=========== 1 failed, 6 passed in 0.29s ===========
```

**GREEN state** (immediately after commit 3):

```text
$ .venv/bin/python -m pytest etl/tests/test_load_freshwater.py -v
etl/tests/test_load_freshwater.py::test_load_freshwater_inserts_synthetic_root_and_orders PASSED [ 14%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_orphan_parents PASSED [ 28%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_empty_scientific_name PASSED [ 42%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_duplicate_freshwater_id PASSED [ 57%]
etl/tests/test_load_freshwater.py::test_load_freshwater_is_idempotent PASSED [ 71%]
etl/tests/test_load_freshwater.py::test_load_freshwater_adds_columns_on_fresh_db PASSED [ 85%]
etl/tests/test_load_freshwater.py::test_load_freshwater_rolls_up_species_count PASSED [100%]

=========== 7 passed in 0.28s ===========
```

**AC-6 GREEN**: the loader's migration adds the columns on first run, and the second run is a no-op (`PRAGMA table_info` finds both columns, so `executescript` is skipped).

**Full-suite verification** (`make test`, after commit 3):

```text
$ make test
...
etl/tests/test_load_freshwater.py::test_load_freshwater_inserts_synthetic_root_and_orders PASSED [ 70%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_orphan_parents PASSED [ 75%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_empty_scientific_name PASSED [ 80%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_duplicate_freshwater_id PASSED [ 85%]
etl/tests/test_load_freshwater.py::test_load_freshwater_is_idempotent PASSED [ 90%]
etl/tests/test_load_freshwater.py::test_load_freshwater_adds_columns_on_fresh_db PASSED [ 95%]
etl/tests/test_load_freshwater.py::test_load_freshwater_rolls_up_species_count PASSED [100%]

================== 12 passed, 8 skipped, 26 warnings in 0.45s ==================
```

The 8 skipped tests are `TestDbBackedEndpoints::*` — they require a populated `taxa.db` and are skipped when `taxa.db` is absent (unchanged from the commit-1 baseline).

**Implementation notes**

- `_apply_schema_v4_if_needed` reads `schema_v4.sql` from the same directory as `load_freshwater.py` via `Path(__file__).resolve().parent`. Single source of truth for the column list and indexes.
- Gating with `PRAGMA table_info(taxon)` before `executescript` makes the migration idempotent. `CREATE INDEX IF NOT EXISTS` inside the SQL file is itself idempotent, so the helper's gate is the only check needed for the `ALTER TABLE` pair.
- Loader docstring updated to describe the migration step (was previously a defensive guard).
- No changes to the conftest in this commit: `BASE_SCHEMA` still ships the overlay columns (the in-loader migration is a no-op against those rows), and tests use `bootstrapped_db` consistently. This means a developer running the loader against the production DB (no overlay columns) gets the migration for free; a developer running against `bootstrapped_db` (cols already present) skips the `executescript` without noise.

**Risk notes / deviations from spec**

- `etl/schema_v4.sql` does not include `REFERENCES taxon(id)` on `freshwater_parent_id` — SQLite `ALTER TABLE ADD COLUMN` rejects that clause. Referencing integrity is enforced at the application layer (the loader's `fw_map` resolution + the API's `_row_to_taxon` validation). This matches the `worms_parent_id` precedent.
- `_apply_schema_v4_if_needed` runs **before** the wipe-and-reload. If the schema migration fails (e.g. partial state from a prior crashed run), the loader exits non-zero and leaves the DB untouched, which is the safe default.

---

## PR-1 work-unit verification (cumulative)

- **Focused test command**: `make test` → `12 passed, 8 skipped`.
- **Loader-only test command**: `.venv/bin/python -m pytest etl/tests/test_load_freshwater.py -v` → `7 passed`.
- **Runtime boundary**: N/A — no live harness change in this batch; the loader is invoked as a subprocess by the test harness itself.
- **Rollback boundary**: `git revert 4dd1b75 211af74` removes both commits in one revert. The overlay columns stay on `taxon` (they're nullable and indexed, no FK), so `/api/domains` keeps its 5-element default (the freshwater root goes away, returning to the pre-change baseline). No other code path depends on `freshwater_id` / `freshwater_parent_id` until PR-2 lands.
- **CoL / WoRMS flows**: untouched. `git diff 6ebffae 4dd1b75 -- etl/load_worms.py etl/load_coldp.py etl/parse_textree.py` is empty.
- **No AI attribution**: `git log --grep "Co-Authored-By" --grep "AI attribution" 6ebffae..HEAD` returns 0 matches for both commits.

---

## PR-2 — `feat(freshwater): add Búsquedas tab and per-row search icon`

### Commit chain

| # | SHA | Title | ACs closed | Status |
| - | --- | ----- | ---------- | ------ |
| 4 | `5972ba3` | `feat(api): add freshwater source and /api/taxon/{id}/searches endpoint` | (PR-1, backend) | landed (pre-this-batch) |
| 5 | (this commit) | `feat(web): add Búsquedas tab, per-row search icon, and Freshwater toggle` | AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29 | landed (this batch) |

### Commit 5 — `feat(web): add Búsquedas tab, per-row search icon, and Freshwater toggle`

**SHA**: `a7b218a8882de9a295a0c90bfcfdc410a454212e`

**Files modified**

| File | Action | Notes |
| ---- | ------ | ----- |
| `web/app.js` | EDIT | +391/-117 (LOC delta on `git diff --stat` ≈ +449/-117). Imports `SEARCH_ENGINES`; extends `RANK_ORDER` with `"collection"`; `matchesTreeSource` gains a `freshwater` branch; `renderNodeRow` appends a search-icon button to `metaBlock` when `scientific_name` is non-empty; `loadDetail` adds the `/api/taxon/{id}/searches` fetch with a client-side guard mirroring the server's 422; `renderDetailPanel` restructured to render a tab strip + only the active tab's content (Búsquedas always first); `renderSearchesTab` (new) renders the 14 search links as a vertical flex of anchor elements with engine icon + label + arrow; click delegation handles `data-tab` (tab switching) and `data-action="open-searches"` (per-row icon → selects taxon + forces Búsquedas tab); the tree-source toggle binding is converted from `forEach` to delegated `document.addEventListener` so dynamically appended buttons (the Freshwater one) work; `boot()` conditionally appends a `<button data-tree-source="freshwater">` to `#tree-source-toggle` when `roots.some(r => r.freshwater_id != null)`; `loadChildren` and `expandAncestorsOf` are extended for `state.treeSource === "freshwater"` (uses `freshwater_parent_id` and appends `&source=freshwater`); the per-tier auto-unroll logic in `toggleExpand` and `expandAncestorsOf` now triggers for the freshwater view too (mirrors WoRMS behaviour). |
| `web/index.html` | EDIT | +58/-0. Adds `.detail-tabs`, `.detail-tab`, `.detail-tab.active`, `.search-icon-btn`, `.search-icon-btn:hover` to the inline `<style>` block. The tab strip sits inside the existing `.detail-card`; the search-icon button uses the existing `--surface-container-low` token for hover bg and Tailwind handles the text-color shift. |

**Visual treatment** (per design.md §4.4 / §4.5)

- **Tab strip**: horizontal flex row directly under the detail-card header. Buttons are 12px Raleway 600 with 0.04em tracking; idle color is `--on-surface-variant` and active color is `--primary` with a 2px underline of the same primary. Hover only shifts the text to `--on-surface`; no bg fill.
- **Search-icon button**: a single `material-symbols-outlined` glyph at 16px, color `--on-surface-variant` at rest, `--primary` on hover. The button has 2px padding, 4px border-radius, no border, transparent bg, and `--surface-container-low` bg on hover. Position: end of `metaBlock` (right of the species count). Hidden when `scientific_name` is empty.
- **Búsquedas list**: each entry is a `detail-item`-styled anchor with the engine icon (primary color), the label, and a small right-arrow glyph in `--outline`. URLs come pre-composed from the server (`urllib.parse.quote_plus`); the local `SEARCH_ENGINES` table is only consulted for the icon glyph (offline / 5xx fallback).
- **Freshwater toggle**: identical `.tree-source-btn` treatment to CoL / WoRMS — segmented-control style, active state fills with `--primary`. Conditionally inserted into the DOM; no `display: none` placeholder.

**Verification** (focused test commands)

```text
$ .venv/bin/python -m pytest tests/ etl/tests/ -v
... 25 passed, 8 skipped, 53 warnings in 0.42s
```

The 25-passed baseline (commit-1 + commit-2 + commit-3 + commit-4 backend) is unchanged by this commit. No new tests added in commit 5 (per tasks.md §4.5 — frontend ACs are enforced via `scripts/screenshot.py` + manual visual review, not pytest).

Critical frontend-affecting smoke tests verified individually:

```text
$ .venv/bin/python -m pytest tests/test_smoke.py::test_search_engine_contract_byte_identical -v
tests/test_smoke.py::test_search_engine_contract_byte_identical PASSED [100%]
================== 1 passed, 28 warnings in 0.16s ==================

$ .venv/bin/python -m pytest tests/test_smoke.py::test_openapi_schema_is_valid_json -v
tests/test_smoke.py::test_openapi_schema_is_valid_json PASSED [100%]
================== 1 passed, 28 warnings in 0.16s ==================

$ .venv/bin/python -m pytest tests/test_smoke.py::test_static_app_js_served tests/test_smoke.py::test_static_index_html_served -v
tests/test_smoke.py::test_static_app_js_served PASSED [100%]
tests/test_smoke.py::test_static_index_html_served PASSED [100%]
================== 2 passed, 28 warnings in 0.15s ==================
```

**Static-asset sanity**

- `node --check web/app.js` exits 0 (JS parses; ES-module import resolves at runtime, not at parse time).
- `node --check web/search_urls.js` exits 0.
- `html.parser.HTMLParser` accepts `web/index.html` without errors.

**Implementation notes**

- **Tab defaulting**: per spec §5.5, Búsquedas is the default landing tab on a fresh selection. `state.activeTab[taxonId]` persists the chosen tab so reopening the same taxon restores the user's choice. When `state.activeTab[taxonId]` is set to a key that doesn't apply to the new taxon (e.g., the taxon has no searches and the user previously had Búsquedas active), the renderer falls back to `tabs[0].key` (Búsquedas, since it's always pushed).
- **Empty-name guard**: the `taxon.scientific_name ? api(.../searches) : Promise.resolve([])` guard in `loadDetail` mirrors the server-side 422 — the client never even asks for search links for nameless taxa. The Búsquedas tab still renders in the strip, but shows an "No search links available for this taxon." empty state inside.
- **Tab-content visibility**: sections are wrapped in `<div data-tab-content="<key>">` with `style="display: none"` for non-active sections. Switching tabs is O(1) — no re-fetch, no re-render of the card, just a class toggle on the strip + style toggle on the section. (Design §4.5: "all four content sections always in DOM; only active tab's section has `display: ""`, others have `display: "none"`.")
- **Tree-source toggle delegation**: per design §4.5, the toggle binding was converted from `forEach(...).addEventListener` to a delegated `document.addEventListener("click", ...)` because the Freshwater button is appended dynamically after `boot()` reads `/api/domains`. Per-button listeners would not bind to the new button. The delegation also clears `state.activeTab` on switch (per spec §5.5: "Switching tree source resets `detailTab` to busquedas to match the new-selection default").
- **Freshwater root detection**: the design spec says to use `/api/health` (which doesn't currently expose a `freshwater` count) **or** `roots.some(r => r.freshwater_id != null)`. The design doc's canonical guidance (spec §5.1, design §4.1) is the latter — the freshwater synthetic root's `freshwater_id` field is the boolean signal. `/api/health` was the task description's alternative example but would require a server-side change to expose the count.
- **Pre-existing lint warning**: `function escape(s)` in `app.js` is declared but never called. This warning was present before commit 5 (verified by `git show 063d827:web/app.js | grep 'function escape'`); commit 5 leaves it unchanged. Tracked as a known dead-code cleanup in a future commit (out of scope here).

**Risk notes / deviations from spec / design**

- **Tab strip CSS lives in the inline `<style>` block** rather than a separate file. Consistent with the rest of the styles (all of which are inline today); no new file or build step needed.
- **`detail-section` empty-state rendering**: when a tab section has zero items (e.g., `vernaculars=[]` but tab is shown), the section still renders the `<h3>` header. The current behaviour matches today's "section renders even when empty" pattern (the section is hidden via `display: none`, not by removing its children).
- **No new pytest tests**: commit 5 is purely UI. The frontend ACs (AC-22..AC-29) are enforced via `scripts/screenshot.py` DOM assertions (per design §8) and manual visual review. The strict TDD discipline applies as "existing tests must continue to pass"; the contract test (AC-21) and OpenAPI assertion (AC-20) are exercised here as part of `make test` and pass.
- **`#tree-source-toggle` styling for 3 buttons**: when freshwater is loaded, three `.tree-source-btn` buttons share the segmented-control width. CSS is unchanged (the container's `overflow: hidden` and `height: 32px` accommodate the extra button). The active state still fills the full button width with the primary color.
- **Per-row icon DOM cost**: 16K-row trees add ~30 bytes per icon button (single `<button>` with no children) = ~500KB total. Matches design §10 risk row — negligible.

**PR-2 work-unit verification (cumulative)**

- Focused test command: `make test` → 25 passed, 8 skipped (same as post-commit-4).
- Contract test: `pytest tests/test_smoke.py::test_search_engine_contract_byte_identical -v` → PASSED.
- Static-asset serving: `test_static_app_js_served` + `test_static_index_html_served` → PASSED.
- Rollback boundary: `git revert a7b218a` removes the frontend slice only. Backend endpoint (`/api/taxon/{id}/searches`) and `SEARCH_ENGINES` table stay; existing CoL / WoRMS UX reverts to today's behaviour (no tab strip, no per-row icon, no Freshwater button). `tests/test_search_engine_contract_byte_identical` still passes because the contract is on the engine table (in `web/search_urls.js`), not on `app.js`.
- CoL / WoRMS flows: untouched in `app.js`'s data-loading paths. `loadChildren`, `expandAncestorsOf`, `renderNodeRow`, `selectTaxon`, `loadDetail` all preserve their CoL/WoRMS behaviour; the `freshwater` branch is additive.
- No AI attribution: `git log -1 --format='%B' a7b218a` contains zero matches for `Co-Authored-By`, `Signed-off-by`, `Anthropic`, `Claude`, or `GPT`.

---

## PR-3 — `docs(freshwater): README + make freshwater target`

### Commit chain

| # | SHA | Title | ACs closed | Status |
| - | --- | ----- | ---------- | ------ |
| 6 | `a92aae9` | `docs(freshwater): README section + make freshwater selector` | AC-30, AC-31 | landed (this batch) |

### Commit 6 — `docs(freshwater): README section + make freshwater selector`

**SHA**: `a92aae9d9106e73590d3624946636ef57fa77620`

**Files modified**

| File | Action | LOC delta (`git diff --stat` against `a7b218a`) | Notes |
| ---- | ------ | ----- | ----- |
| `Makefile` | EDIT | +21/-3 | Adds the `freshwater:` selector target (recipe fails fast with a hint when `data/raw/freshwater.csv` is absent), extends `load-all:` to include `freshwater`, and adds the `freshwater` branch to the backwards-compatible `load SOURCE=freshwater` selector. `shellcheck disable=SC1089` comments on the new branches match the existing selector pattern (also globally disabled in `.shellcheckrc`). |
| `README.md` | EDIT | +69/-0 | Adds `## Búsquedas tab` section after `## Frontend` (engine table + contract test reference); adds `## Freshwater source` section after `## Data source` (manual CSV quick-start, post-load counts, toggle button behaviour); extends the `Quick start` block with an optional step 4 (`make freshwater`); adds `/api/taxon/{id}/searches` to the API endpoints table. |

`git diff --stat a7b218a..a92aae9` summary: **2 files changed, 90 insertions(+), 3 deletions(-)**.

**Verification**

```text
$ make test
...
================== 25 passed, 8 skipped, 53 warnings in 0.45s ==================
```

Same 25 passed / 8 skipped baseline as post-commit-5. No new tests in this commit (per the user's prompt: docs + build slice only).

Target-level sanity (no data on disk yet, so `make freshwater` exercises the failure path):

```text
$ make -n freshwater
if [ ! -f data/raw/freshwater.csv ]; then \
  echo "Missing data/raw/freshwater.csv. Export your Freshwater Fishes Google Sheet to CSV and place it at this path."; \
  exit 1; \
 fi
.venv/bin/python3 etl/load_freshwater.py data/raw/freshwater.csv

$ make freshwater
Missing data/raw/freshwater.csv. Export your Freshwater Fishes Google Sheet to CSV and place it at this path.
make: *** [freshwater] Error 1
```

`make freshwater` without a CSV prints the hint and exits non-zero, as designed (mirrors the `worms:` fail-fast pattern when the TSV is absent).

**Implementation notes**

- **`Makefile` recipe structure** matches `worms:`: a single-target recipe, conditional `@if [ ! -f ... ]; then ... exit 1; fi` guard, then the loader invocation. No new `.PHONY` entry needed (the existing `clean test smoke` line covers the alphabetical-ish ordering and the recipes are reached via `make` regardless of file existence).
- **`load-all` extension** is additive — `col` and `worms` remain in the dependency list, so re-running `make load-all` still runs CoL + WoRMS in order before freshwater.
- **`load SOURCE=...` selector** — the new `elif [ "$(SOURCE)" = "freshwater" ]` branch preserves the existing selector's syntax; the `else` branch's usage message now mentions `freshwater`.
- **`## Búsquedas tab` section** placed after `## Frontend` (not before `## API`) so the table reads in narrative order: frontend behaviour → new tab feature → API surface. The 14-row engine table is parseable Markdown; cells containing `{name}` / `{auth}` template placeholders are inside backticks to keep the pipe characters from breaking column alignment.
- **`## Freshwater source` section** placed after `## Data source` to mirror the existing structure (CoL data source citation first, then the operational section that depends on it). The `### Quick start` sub-block is a 3-step recipe (export CSV → `make freshwater` → `make api`); `### Counts (post-load)` lists the rough totals the user can expect; a single prose paragraph at the end calls out the toggle button's conditional visibility.
- **`Quick start` block** extended with step 4 marked "(Optional)" — the user can skip it if they don't have the freshwater CSV. Step 5 (was step 4) is renumbered.
- **API endpoints table** — `/api/taxon/{id}/searches` placed between `/vernaculars` and `/search` to mirror the resource hierarchy (per-taxon sub-resources grouped together).

**Risk notes / deviations from spec**

- **Stale "Detail panel" item in `What's NOT here yet`**: the existing README still has `- **Detail panel** in the frontend: when you click a species, show its vernaculars, synonyms, distribution in a side panel.` under `## What's NOT here yet (next iterations)`. This is now misleading (PR-2's tab strip delivers exactly that), but it's outside commit 6's file-level scope (`Makefile` and `README.md` only — touching that bullet is a separate docs cleanup, deferred to a future iteration).
- **Counts in `### Counts (post-load)`** are approximations (~16K rows / ~5K species / ~1.5K genera / ~250 families) matching the user's prompt. If the user's actual Sheet diverges substantially, they can update the bullet; the loader does not assert these as ground truth.

**PR-3 work-unit verification (cumulative)**

- Focused test command: `make test` → **25 passed, 8 skipped** (same as post-commit-5).
- Make target sanity: `make -n freshwater` shows the recipe; `make freshwater` (CSV absent) exits non-zero with the hint.
- Rollback boundary: `git revert a92aae9` removes both files' changes. CoL / WoRMS flows are untouched (`git diff a7b218a a92aae9 -- etl/api/server.py web/` is empty); `/api/taxon/{id}/searches` and the loader keep working without the new `make` target and README section. No new runtime dependency introduced.
- CoL / WoRMS / Freshwater flows: untouched in source files. The Makefile's `load-all:` and `load SOURCE=...` selector changes are additive — pre-existing `col` and `worms` recipes are byte-identical.
- No AI attribution: `git log -1 --format='%B' a92aae9 | grep -E "Co-Authored-By|Signed-off-by|Anthropic|Claude|GPT"` returns 0 matches. AC-31 satisfied.
- AC-30 satisfied: `grep -c "## Freshwater source" README.md` → 1; the section is present and documents the CSV input + `make freshwater` workflow.
- AC-31 satisfied: commit message contains zero `Co-Authored-By:`, `Signed-off-by:`, or AI attribution footers.

---
