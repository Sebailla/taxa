# Runbook — Freshwater Fishes activation

Operational guide for activating the third taxonomic source (Freshwater
Fishes) on top of an existing CoL + WoRMS `taxa.db`. Covers prerequisites,
step-by-step activation, verification, troubleshooting, and a postmortem
of the issues encountered during the first ship.

## Overview

The freshwater fish cladification lives in the user's Google Sheet
("Freshwater Fishes"). The activation pipeline:

1. **Export** the Sheet to CSV (manual step — Google OAuth is out of scope).
2. **Transform** the spreadsheet CSV (hierarchical: `family`, `subfamily`,
   `genus`, `species`, `scientific_name`, `author`, `year`) into the flat
   format `etl/load_freshwater.py` expects (`freshwater_id`,
   `freshwater_parent_id`, `rank`, `scientific_name`, `authorship`).
3. **Load** the flat CSV into `taxa.db` as an isolated overlay. Adds a
   synthetic root row (`Freshwater Fishes`, `rank='collection'`,
   `freshwater_id=1`, `freshwater_parent_id=NULL`) and inserts every
   family / subfamily / genus / species row with `parent_id=NULL` so
   freshwater rows never pollute the CoL view.
4. **Restart** the API (uvicorn caches the SQLite connection at module
   load — `/api/domains` won't see the new root until restart).
5. **Hard-refresh** the browser so the cached `web/app.js` is replaced
   and the `Freshwater` toggle button renders.

The pieces:

| File | Role |
| --- | --- |
| `data/raw/freshwater.csv` | User-managed: export of the Google Sheet |
| `scripts/transform_freshwater.py` | Spreadsheet (hierarchical) → flat CSV |
| `etl/load_freshwater.py` | Flat CSV → `taxa.db` (wipe-and-reload; idempotent) |
| `etl/schema_v4.sql` | Idempotent `ALTER TABLE taxon ADD COLUMN freshwater_id, freshwater_parent_id` (applied automatically by the loader if missing) |
| `api/server.py` | New `GET /api/taxon/{id}/searches` endpoint + extended `source=` filter; `RANK_ORDER` extended with `collection` |
| `web/app.js` | Boot-time Freshwater toggle append (conditional on `/api/domains` returning a freshwater root) + per-row search icon + tab strip |
| `Makefile` | `freshwater:` target orchestrates transform → load |

## Prerequisites

- Python 3.14 (`python3 --version`)
- `.venv` initialized: `make venv`
- A populated `data/db/taxa.db` with CoL (`make col`) and WoRMS
  (`make worms`) loaded. About 5.7 M taxa / 2.9 GB on disk.
- ~500 MB free for the freshwater rows (~18 K taxa).
- The browser session for verification: anything modern (the project uses
  Material Symbols + Tailwind CDN, no build step).

## One-time setup (per repo clone)

```bash
make venv            # ~30s, creates .venv + installs requirements
make etl             # ~5 min, downloads TextTree + parses into taxa.db
make coldp           # ~5 min, downloads ColDP + adds vernaculars/coldp_id
make worms           # ~30s, downloads WoRMS ColDP + adds worms_id/worms_parent_id
```

After this, `data/db/taxa.db` has ~5.7 M CoL+WoRMS rows and the API
serves the 5 standard roots (`Archaea`, `Bacteria`, `Biota`, `Eukaryota`,
`Viruses`).

## Activate freshwater

### Step 1 — Export the spreadsheet to CSV

In Google Sheets: **File → Download → Comma-separated values (.csv)**.

The spreadsheet has 7 taxonomic columns (`family`, `subfamily`, `genus`,
`species`, `scientific_name`, `author`, `year`) followed by 19 search-engine
reference columns (the user's notes for each engine, ignored by the
loader).

### Step 2 — Drop the CSV in `data/raw/`

```bash
mkdir -p data/raw
cp ~/Downloads/Freshwater\ Fish\ -\ Sheet1.csv data/raw/freshwater.csv
```

The `make freshwater` target fails fast with a hint if
`data/raw/freshwater.csv` is missing:

```
Missing data/raw/freshwater.csv. Export your Freshwater Fishes Google
Sheet to CSV and place it at this path.
make: *** [freshwater] Error 1
```

### Step 3 — Run `make freshwater`

```bash
make freshwater
```

Output:

```
Transformed: 18389 rows (249 families, 255 subfamilies, 3595 genera, 14290 species)
Output: /tmp/freshwater.flat.csv
Clearing 18,390 previously-loaded freshwater rows...
Inserting synthetic root (Freshwater Fishes, rank=collection)...
Reading /tmp/freshwater.flat.csv...
Inserted: 18389
Skipped by validation: 0
Total CSV rows: 18389
Done.
```

What happens under the hood:

1. `scripts/transform_freshwater.py` reads the spreadsheet, deduplicates
   families / subfamilies / genera, and emits the flat CSV.
2. `etl/load_freshwater.py`:
   - Applies `etl/schema_v4.sql` idempotently (adds `freshwater_id` and
     `freshwater_parent_id` columns + partial indexes if missing).
   - Wipes any prior freshwater rows.
   - Inserts the synthetic root.
   - Inserts every CSV row. `parent_id` is always `NULL` — freshwater
     rows live in their own hierarchy under `freshwater_parent_id`,
     never mixing with CoL's `parent_id`.
   - Rolls up `species_count` on the synthetic root via recursive CTE.

The loader is idempotent: re-running clears the previous freshwater rows
and re-inserts from scratch.

### Step 4 — Restart the API

```bash
# Stop the running uvicorn (Ctrl+C in its terminal, or: kill <pid>)
# Then restart:
make api
```

`uvicorn` opens the SQLite connection at module load and keeps it open.
A restart is required so `/api/domains` re-queries with the new
freshwater rows.

### Step 5 — Hard-refresh the browser

`Cmd+Shift+R` (Mac) / `Ctrl+F5` (Linux/Windows).

Without the hard-refresh the browser serves the cached `web/app.js`,
which still has the original 2-button toggle (CoL, WoRMS). The hard-refresh
forces the new `web/app.js` to be fetched, which contains the
event-delegated toggle with the dynamically appended `Freshwater` button.

## Verification

After step 5, the toggle in the header reads
`[CoL] [WoRMS] [Freshwater]`. Click `Freshwater` — the tree drills into
the synthetic root and shows the 249 families under "Freshwater Fishes".

### End-to-end smoke test

`scripts/smoke_freshwater.py` exercises the full chain on a non-default
port (8766) so it doesn't disturb a running dev API:

```bash
$ .venv/bin/python3 scripts/smoke_freshwater.py
/api/health: taxa=5,682,755
/api/domains: 6 roots total, 1 freshwater_root(s)
  -> id=5664378 name='Freshwater Fishes' rank='collection' fw_id=1 fw_parent_id=None
/api/taxon/5664378/children?source=freshwater (first 5):
  -> ACANTHURIFORMES (rank=family, fw_id=3, freshwater_parent_id=5664378)
  -> ACESTRORHYNCHIDAE (rank=family, fw_id=4, freshwater_parent_id=5664378)
  -> ACHEILOGNATHIDAE (rank=family, fw_id=5, freshwater_parent_id=5664378)
  -> ACHIRIDAE (rank=family, fw_id=6, freshwater_parent_id=5664378)
  -> ACIPENSERIDAE (rank=family, fw_id=7, freshwater_parent_id=5664378)
/api/taxon/5664380/children?source=freshwater (first 5):
  -> Lonchogenys (rank=genus)
  (no species under first genus — skipping /searches test)

Smoke test PASSED
```

Exit code 0 = pass, 1 = any check failed.

### Manual API checks

```bash
# The freshwater root should be in the response
curl -s http://127.0.0.1:8765/api/domains | jq '.[] | {name: .scientific_name, fw_id: .freshwater_id}'

# Children of the synthetic root walk the freshwater tree
curl -s "http://127.0.0.1:8765/api/taxon/5664378/children?source=freshwater&limit=10"

# The 14 search-engine links for a freshwater species
curl -s "http://127.0.0.1:8765/api/taxon/<freshwater_species_id>/searches" | jq '.[].engine'
# Expected: google, imagen, documentos, pdf, wikipedia, bhl, researchgate, plos, academia, scielo, scholar, youtube, zootaxa, scribd
```

## Troubleshooting

### "Missing data/raw/freshwater.csv" message

The CSV export isn't at the expected path. Confirm the export and copy:

```bash
ls -la data/raw/freshwater.csv
# Re-export and copy if missing
cp ~/Downloads/*.csv data/raw/freshwater.csv
```

### Freshwater toggle button doesn't appear in the header

The toggle is rendered dynamically in `boot()` when
`/api/domains` returns a row with `freshwater_id != null`. If the button
is missing:

1. Confirm the data is in the DB:

   ```bash
   sqlite3 data/db/taxa.db "SELECT COUNT(*) FROM taxon WHERE freshwater_id IS NOT NULL;"
   # Expected: 18390 (249 families + 255 subfamilies + 3595 genera + 14290 species + 1 synthetic root)
   ```

2. Confirm the API is the new one (PID via `ps aux | grep grep | grep uvicorn`):

   ```bash
   curl -s http://127.0.0.1:8765/api/domains | jq '.[] | select(.freshwater_id == 1)'
   # Should return the "Freshwater Fishes" row
   ```

   If `freshwater_id` doesn't appear in the JSON, the running uvicorn
   has old code. **Restart the API** (`make api`).
3. Hard-refresh the browser (`Cmd+Shift+R` / `Ctrl+F5`). Without
   this, the browser caches the old `web/app.js` and the toggle won't
   render even though the API is correct.

### `/searches` returns empty URLs for a taxon

The endpoint returns 14 `SearchLink` entries; each `url` should be
non-empty. If a URL is empty, the taxon has `scientific_name == ""`,
which the endpoint defends with HTTP 422:

```bash
$ curl -i http://127.0.0.1:8765/api/taxon/<id>/searches
HTTP/1.1 422 Unprocessable Entity
{"detail":"taxon <id> has no scientific_name; cannot compose search URLs"}
```

The client (`web/app.js`) mirrors the server guard and skips the fetch
when the name is empty, so this surfaces only for direct API users. The
DB has zero rows with empty `scientific_name` today; if the loader ever
starts ingesting them (e.g., from a malformed CSV row), tighten the
loader validation or fix the source CSV.

### Smoke test fails: "API failed to start within 10s"

The smoke test boots its own uvicorn on port 8766. If something is
already listening on 8766 (rare — the dev API is on 8765), the test
will time out. Either kill the conflicting process or change `PORT` at
the top of `scripts/smoke_freshwater.py`.

### Loader shows "0 rows loaded"

`etl/load_freshwater.py` prints `WARNING: 0 rows loaded; check input
CSV` when the entire CSV is empty after the header. Common causes:

- The CSV is empty (export failed).
- Every row is a header row (the loader skips rows where the third
  column isn't a known rank — if the spreadsheet's first row has
  Wikipedia/BHL headers instead of `family, subfamily, genus, …`, the
  loader skips everything). Re-export the spreadsheet; the first row
  must be the actual header.

## Re-activation

After every spreadsheet update, the user re-exports and re-runs:

```bash
cp ~/Downloads/Freshwater\ Fish\ -\ Sheet1.csv data/raw/freshwater.csv
make freshwater
make api   # only if API wasn't restarted since the last `make freshwater`
```

The loader is idempotent — re-running wipes the previous freshwater rows
and re-inserts from the new CSV. No need to manually `DELETE FROM taxon`.

## Postmortem — issues encountered during the first ship

### 1. The `Freshwater` toggle button never rendered (PR-2 + PR-8)

**Symptom (caught late, after merge):** even with `make freshwater`
running and the DB populated, the toggle in the header still showed only
`[CoL] [WoRMS]`. No `Freshwater` button.

**Root cause:** the PR-2 frontend commit
(`feat(web): add Búsquedas tab, per-row search icon, and Freshwater
toggle`, `a7b218a`) was supposed to add two pieces of logic in
`boot()`:

1. Replace the static `forEach` click binding on `#tree-source-toggle`
   with `document.addEventListener('click', …)` delegation, so
   dynamically appended buttons work.
2. Append a `<button data-tree-source="freshwater">Freshwater</button>`
   to the toggle when `/api/domains` returns a freshwater root.

Neither was written. The sdd-apply subagent that authored `a7b218a`
appears to have shipped the icon, tab strip, and toggle-button
*visibility* (the CSS) but not the *append logic*. The toggle was always
unrendered.

The verify-report for PR-2 (`openspec/changes/add-freshwater-and-search/
verify-report.md`) marked AC-26 ("Freshwater toggle button appears only
when `/api/domains` returns a `freshwater_id` row") as PASS based on
code-level inspection — but the actual code to *create* the button
was never there. Inspection missed the regression because there was
nothing to find.

**Detection:** only when the user opened the merged app in a real
browser and reported "no veo freshwater en la ui". The 26 pytest tests
were green; the API was correct; only the JS wasn't.

**Fix:** PR-8 (`fix(freshwater-toggle-rendering)`, `28c0c40`) — both
the event-delegation replacement and the append logic. Manual
verification: with the new `web/app.js` and a hard-refresh, the
toggle renders all three buttons.

**Lesson for future sdd-apply subagents:**

- **Always actually run the JS in a real browser** before claiming
  frontend ACs are PASS. Code-level inspection catches *absence of
  obviously wrong code*; it does not catch *absence of required code*.
- For frontend slices, set up a Playwright smoke test (the project
  has none today — R-2 from the original verify-report). Even a
  one-test "does the toggle button exist after boot?" would have
  caught this.

### 2. The activation scripts never landed in main (PR-7)

**Symptom:** `make freshwater` runs but the target recipe still calls
`etl/load_freshwater.py data/raw/freshwater.csv` directly. No
`scripts/transform_freshwater.py`. No smoke test.

**Root cause:** the activation tooling (`scripts/transform_freshwater.py`,
`scripts/smoke_freshwater.py`, the `freshwater:` Makefile target) was
authored in commit `50ac825` ("feat(etl): wire make freshwater to
transform-then-load"), which was made on `pr-3-freshwater-docs` *after*
PR-7 had already been opened with its final commit list. The user
merged PR-7 before `50ac825` existed; `50ac825` later landed on
`fix/freshwater-toggle-rendering` and was rolled into PR-9
(`feat(etl): add freshwater transform script + smoke test + Makefile
orchestration`, `570a29c`).

**Detection:** when the user reported `no veo freshwater en la ui`,
the diagnosis path tried to run `make freshwater` and found the target
called the loader with the spreadsheet CSV directly — which
crashed because the loader expects flat format. The transform
script existed only in `/tmp/` from a one-off run, never in the
repo.

**Fix:** PR-9 (`570a29c`) restored the scripts to `scripts/` and
updated the Makefile.

**Lesson for future sdd-apply subagents:**

- **If a commit is task description says "scripts/transform_*.py" will
  be added, make sure it's added before opening the PR**, or open a
  follow-up PR. Don't author the commit *after* the PR is already
  opened — it won't be in the merge.
- For multi-commit changes that span loader + API + frontend + docs
  - scripts, plan the commit boundaries **before** opening the PR.
  A late commit sitting on a branch without its target PR is a
  silent loss.

### 3. The persistent stale-cache warning from `pi-lens` on `tests/test_smoke.py`

**Symptom:** every time a commit touched `tests/test_smoke.py` (or
nearby), `pi-lens` flagged 16 issues — including "L108: `re` is not
defined" and "L131: Un indent is unindent" — that didn't exist in the
file. `python -m py_compile tests/test_smoke.py` exited 0; `make test`
reported `26 passed, 8 skipped`. The lint warnings were stale.

**Root cause:** the bundled linter inside `pi-lens` caches lint state
per-file and doesn't refresh on every read. A transient edit mishap
mid-session (a `re` import line lost its indentation during a
large `edit` operation; I fixed it with `python3 -c` and a manual
`s/\njs_entries/\n    js_entries/`) left a stale lint snapshot that
never cleared.

**Lesson:** treat `pi-lens` blockers on `tests/test_smoke.py` as
"stale until proven otherwise" — verify with `py_compile` and a
fresh `make test` before touching the file. The file is fine in
practice and the persistent warning is a tooling artifact, not a
code defect.

## References

- Spec: `openspec/changes/add-freshwater-and-search/spec.md`
- Design: `openspec/changes/add-freshwater-and-search/design.md`
- Verify report: `openspec/changes/add-freshwater-and-search/verify-report.md`
- Archive report: `openspec/changes/add-freshwater-and-search/archive-report.md`
- Loader source: `etl/load_freshwater.py`
- Transform script: `scripts/transform_freshwater.py`
- Smoke test: `scripts/smoke_freshwater.py`
- Frontend toggle logic: `web/app.js` (`boot()` + event delegation around
  the `#tree-source-toggle` selector)
