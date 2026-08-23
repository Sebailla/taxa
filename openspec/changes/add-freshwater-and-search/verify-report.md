# verify-report — add-freshwater-and-search

## Summary

- Total ACs: 31
- PASS: 28
- PASS-WITH-NOTE: 3
- FAIL: 0
- N/A: 0
- Test result: **26 passed / 8 skipped** (56 warnings) — baseline was 25 passed; the new test `test_searches_422_on_empty_scientific_name` (AC-18) brings the count to 26.

All 31 ACs were verified by combining pytest execution (`make test`), code-level inspection of the implementation files, git-log audit of the commit messages, and a cross-file contract parse of `api/server.py::_SEARCH_ENGINES` against `web/search_urls.js::SEARCH_ENGINES`. Backend ACs AC-1..AC-19 are backed by green pytest tests; frontend ACs AC-22..AC-29 are not auto-verifiable (per `design.md` §8 — they depend on `scripts/screenshot.py` + manual visual review) and were verified by code-level inspection of `web/app.js` and `web/index.html`. AC-31 was verified by `git log` over the 6 freshwater-related commits.

---

## Per-AC verdict

- `AC-1: PASS — etl/tests/test_load_freshwater.py::test_load_freshwater_inserts_synthetic_root_and_orders PASSES; root has rank='collection', freshwater_parent_id IS NULL, freshwater_id=1, plus 3 child orders with parent_id=NULL.`
- `AC-2: PASS — test_load_freshwater_skips_orphan_parents PASSES; 2 orphan rows skipped, WARNING logged with line number, valid rows inserted.`
- `AC-3: PASS — test_load_freshwater_skips_empty_scientific_name PASSES; row with empty name skipped, WARNING logged, rest loaded.`
- `AC-4: PASS — test_load_freshwater_skips_duplicate_freshwater_id PASSES; first occurrence wins, WARNING logged.`
- `AC-5: PASS — test_load_freshwater_is_idempotent PASSES; CoL-only / WoRMS-only / CoL+WoRMS row counts preserved across two runs of different CSV size.`
- `AC-6: PASS — test_load_freshwater_adds_columns_on_fresh_db PASSES; columns added on first run, second run is a no-op.`
- `AC-7: PASS — test_load_freshwater_rolls_up_species_count PASSES; synthetic root's species_count equals the count of species/subspecies rows in the CSV.`
- `AC-8: PASS — tests/test_api_freshwater.py::test_domains_without_freshwater PASSES; returns 5 roots {Archaea, Bacteria, Biota, Eukaryota, Viruses} with freshwater_id=None.`
- `AC-9: PASS — test_domains_with_freshwater PASSES; 6 roots when Freshwater Fishes row inserted, freshwater_id=1, freshwater_parent_id=NULL.`
- `AC-10: PASS — test_children_source_freshwater PASSES; 2 child orders returned, all have freshwater_id non-null and freshwater_parent_id==root_id.`
- `AC-11: PASS — test_children_source_col_with_freshwater_root PASSES; source=col returns empty list for the synthetic root (parent_id IS NULL).`
- `AC-12: PASS — test_children_source_worms_with_freshwater_root PASSES; source=worms returns empty list for the synthetic root.`
- `AC-13: PASS — test_taxon_includes_freshwater_id PASSES; Astyanax-like row with freshwater_id=42, freshwater_parent_id=<family>, parent_id=None.`
- `AC-14: PASS — test_taxon_without_freshwater_id PASSES; CoL-only taxon returns freshwater_id=None and freshwater_parent_id=None.`
- `AC-15: PASS — test_searches_returns_14_entries PASSES; returns exactly 14 entries in the fixed order [google, imagen, documentos, pdf, wikipedia, bhl, researchgate, plos, academia, scielo, scholar, youtube, zootaxa, scribd].`
- `AC-16: PASS — test_searches_urls_are_well_formed PASSES; all 14 URLs parse with urlparse(...).scheme in {http, https} and contain the encoded scientific_name.`
- `AC-17: PASS-WITH-NOTE — Test name is test_searches_with_authorship (vs. spec's test_searches_authorship_on_bhl_and_scholar_only); behavior is correct (bhl.url contains De+Filippi, scholar.url contains De+Filippi, google.url does NOT).`
- `AC-18: PASS — tests/test_api_freshwater.py::test_searches_422_on_empty_scientific_name PASSES after the orchestrator-applied fix (commit 4d2f35c): api/server.py::get_searches now raises HTTPException(422, detail=f'taxon {id} has no scientific_name; ...') when the fetched row has empty scientific_name, after the existing 404 guard. Test inserts a row with scientific_name="" (SQLite NOT NULL permits empty strings) and asserts status==422 + detail mentions 'scientific_name'.`
- `AC-19: PASS-WITH-NOTE — Test name is test_searches_404_for_unknown_taxon (vs. spec's test_searches_404_on_unknown_id); behavior is correct (999999999 → 404 with detail naming the id).`
- `AC-20: PASS — tests/test_smoke.py::test_openapi_schema_is_valid_json extends expected_paths with "/api/taxon/{taxon_id}/searches"; test PASSES.`
- `AC-21: PASS-WITH-NOTE — Test name is test_search_engine_contract_byte_identical (vs. spec's test_search_engine_contract); cross-file parse passes — 14 entries in identical key/label/with_authorship order between api/server.py::_SEARCH_ENGINES and web/search_urls.js::SEARCH_ENGINES.`
- `AC-22: PASS — web/app.js:1516-1526 dynamically appends <button data-tree-source="freshwater" class="tree-source-btn"> when roots.some(r => r.freshwater_id != null); lines 1472-1476 toggle aria-pressed on click; click handler delegated at line 1455.`
- `AC-23: PASS — Conditional insert at web/app.js:1516:`if (hasFreshwater) { … }`. Without freshwater data the button is never added to the DOM (no display:none fallback).`
- `AC-24: PASS — Per-row icon has data-action="open-searches" (web/app.js:463); delegation handler at line 1264 sets state.activeTab[id]="busquedas" BEFORE selectTaxon(id), forcing the tab on the subsequent render.`
- `AC-25: PASS — Conditional render at web/app.js:451-470:`taxon.scientific_name ? el(…search button…) : null`. Nameless rows render no icon.`
- `AC-26: PASS — loadChildren (line 85) appends &source=freshwater to /api/taxon/{id}/children when state.treeSource === "freshwater"; toggleExpand (line 116) auto-unrolls for freshwater view mirroring WoRMS.`
- `AC-27: PASS — renderDetailPanel (line 982+) builds tabs array in order [busquedas, vernaculars, synonyms, distribution]; each non-busquedas tab is conditional on data presence; tab strip rendered with class="detail-tabs" and tab buttons with class="detail-tab active" (web/index.html:371-411).`
- `AC-28: PASS — renderSearchesTab renders one <a target="_blank" rel="noopener" href=s.url> per state.detail.searches entry using state.detail.searches.map(...). 14 entries when the server response has 14.`
- `AC-29: PASS — Tree-source toggle handler at web/app.js:1455-1476 clears node.children=null for every cache entry, state.expanded.clear(), state.showAll.clear(), and state.activeTab = {} on switch.`
- `AC-30: PASS — README.md has`## Freshwater source` (line ~144) under `## Data source`, with the manual CSV quick-start, counts, and toggle button note;`## Búsquedas tab` and `/api/taxon/{id}/searches`endpoint table entry also present.`
- `AC-31: PASS — git log -1 --format='%B' over the 6 freshwater commits (11d32a4, 211af74, 4dd1b75, 5972ba3, a7b218a, a92aae9) returns 0 matches for "Co-Authored-By", "Signed-off-by", "Anthropic", "Claude", or "GPT". All messages are conventional commits.`

---

## Findings (FAILs only)

### AC-18: Server does NOT return 422 when scientific_name is empty

**What's wrong (concrete)**

- `api/server.py` lines 363-372 (`get_searches`):

  ```python
  @app.get("/api/taxon/{taxon_id}/searches", response_model=list[SearchLink])
  def get_searches(taxon_id: int):
      with db() as conn:
          row = conn.execute(
              "SELECT scientific_name, authorship FROM taxon WHERE id = ?",
              (taxon_id,),
          ).fetchone()
          if row is None:
              raise HTTPException(
                  status_code=404,
                  detail=f"taxon {taxon_id} not found",
              )
      return _build_search(row["scientific_name"], row["authorship"])
  ```

  The endpoint returns `_build_search(...)` unconditionally, even when `row["scientific_name"]` is `""` or `None`.

- `api/server.py` lines 333-352 (`_build_search`):

  ```python
  def _build_search(scientific_name: str, authorship: Optional[str]) -> list[SearchLink]:
      from urllib.parse import quote_plus
      name_q = quote_plus(scientific_name or "")
      ...
  ```

  No `HTTPException(422)` is raised for empty input — the helper silently produces 14 URLs containing the empty encoded string.

- `tests/test_api_freshwater.py` has 12 tests but no `test_searches_422_on_empty_scientific_name`. The slot labelled `AC-18` in the file's section header (line with comment `# AC-15 / AC-16 / AC-17 / AC-18 / AC-19`) is filled by `test_searches_url_encoding`, which tests URL encoding on a taxon with `"Homo sapiens subsp. typicus"` (non-empty name). The spec's AC-18 — defensive 422 when `scientific_name` is empty/null — has no test at all.

- `web/app.js::loadDetail` (line 786) does guard client-side with `taxon.scientific_name ? api(...) : Promise.resolve([])`; the frontend is safe. The server-side defensive layer the spec mandated is absent.

- Spec reference: `proposal.md` (open decisions §11), `spec.md` §3.5 / §7 AC-18, `design.md` §7 ("`scientific_name` empty/null on a tree row | API `get_searches` | 422 with detail mentioning `scientific_name`").

**Severity**: Medium — defensive contract gap. The endpoint never returns a meaningful response when `scientific_name` is empty, but the row is, by spec design, unlikely in production (`load_freshwater.py` drops empty-name rows; CoL TextTree requires non-empty names). However, an out-of-band SQLite write, a legacy CoL row, or a future loader bug could surface the broken state silently (14 URLs pointing at root search pages with no query string).

**Suggested fix (concrete)**

1. In `api/server.py::_build_search`, raise immediately on empty input:

   ```python
   def _build_search(scientific_name: str, authorship: Optional[str]) -> list[SearchLink]:
       from urllib.parse import quote_plus
       if not (scientific_name or "").strip():
           raise HTTPException(
               status_code=422,
               detail="taxon has no scientific_name; cannot build search links",
           )
       ...
   ```

   The exact message format matches `spec.md` §3.6 (uses `{id}` in the message — the helper has no id, so the literal message is acceptable).

2. In `tests/test_api_freshwater.py`, add the spec's test as AC-18:

   ```python
   def test_searches_422_on_empty_scientific_name(db_and_client):
       """AC-18: GET /api/taxon/{id}/searches for a taxon with
       scientific_name == "" returns 422."""
       conn, client = db_and_client
       tid = _insert(conn, scientific_name="", rank="species", coldp_id="col-x")
       resp = client.get(f"/api/taxon/{tid}/searches")
       assert resp.status_code == 422
       assert "scientific_name" in resp.json().get("detail", "")
   ```

3. The existing `test_searches_url_encoding` (which uses a non-empty name) can stay as additional coverage (rename it to make room for AC-18, or simply add the AC-18 test alongside).

---

## Cross-file contract verification (AC-21)

Parse of both source tables confirms 14 entries each, in identical order, with identical `key`, `label`, and `with_authorship` values. The engine contract test (`tests/test_smoke.py::test_search_engine_contract_byte_identical`) parses both files via regex + `ast.literal_eval` and PASSES.

```text
   # | key          | label          | with_authorship
   --+--------------+----------------+----------------
   1 | google       | Google         | False
   2 | imagen       | Imágenes       | False
   3 | documentos   | Documentos     | False
   4 | pdf          | PDF            | False
   5 | wikipedia    | Wikipedia      | False
   6 | bhl          | BHL            | True   <- only these two
   7 | researchgate | ResearchGate   | False
   8 | plos         | PLOS           | False
   9 | academia     | Academia.edu   | False
  10 | scielo       | Scielo         | False
  11 | scholar      | Scholar        | True   <- carry authorship
  12 | youtube      | YouTube        | False
  13 | zootaxa      | Zootaxa        | False
  14 | scribd       | Scribd         | False
```

URL template strings are not compared by AC-21 (per design.md §6.4: `template` is server-only) but spot-checking confirms `https://www.google.com/search?q={name}` in both files for `google`, and the `template_with_auth` exists for `bhl` and `scholar` only. The server uses `urllib.parse.quote_plus`; the JS file uses `encodeURIComponent` — both pass a server-composed URL field to the anchor element, so the dual encoding is harmless (frontend trusts `s.url` directly).

---

## TDD evidence review

Strict TDD mode is on. The apply-progress.md RED/GREEN transcripts document the test-first loop for AC-1..AC-6 on commits 2 and 3 (loader slice). AC-7..AC-20 (API slice, commit 4 pre-this-batch) do not have RED/GREEN snapshots in the apply-progress because they landed in the pre-this-batch scaffold commit (`5972ba3`), but the pytest results below show 12 green tests covering AC-8..AC-19 + AC-20. The contract test (AC-21) is green on its first build per commit 3 of PR-2. Frontend ACs (AC-22..AC-29) have no pytest coverage by design (per `design.md` §8 — frontend ACs are enforced via `scripts/screenshot.py` DOM assertions + manual visual review; the project does not yet have a Playwright/Jest runner).

### Assertion quality audit

Spot-checked each AC-1..AC-19 test for tautologies, ghost loops, smoke-only assertions, and implementation-detail leaks:

- **AC-1..AC-7 (loader):** tests run the loader as a subprocess (`subprocess.run(...)`) and open a fresh `sqlite3.Connection` to read back the persisted DB. The assertions inspect real rows (`SELECT ... FROM taxon WHERE freshwater_id IS NOT NULL`), check `freshwater_parent_id IS NULL`, count exact rows, and verify the rollup's `species_count`. No ghost loops; no implementation-detail assertions (e.g., the test does not assert on the loader's stderr beyond ensuring WARNING lines appear). Each test has multiple concrete assertions on observable state.
- **AC-8..AC-14:** use `TestClient(app)` against a shared in-memory SQLite (URI + cache=shared). Each test seeds a small fixture row, hits the API endpoint, and asserts exact fields on the response. No tautologies; no type-only checks.
- **AC-15..AC-19:** all inspect real response shape — list length, exact key order (AC-15), parsed URL scheme + netloc + name presence (AC-16), substring containment of encoded authorship (AC-17, AC-18-as-implemented). AC-19 asserts status code 422 + 404 paths. All concrete.
- **AC-20:** asserts the OpenAPI path set is a superset of the documented expected paths (real JSON parse + set comparison).
- **AC-21:** a regex/AST parse + per-field byte-equality comparison. Concrete and direct.

No CRITICAL findings on assertion quality. **AC-17, AC-19, AC-21 are PASS-WITH-NOTE solely because of test-name drift (sub-`spec.md` literal); the assertion strength itself is fine.**

---

## Test execution log

`make test` (run from `/Users/sebailla/Developer/taxa`):

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.7, pytest-8.3.4, pluggy-1.6.0
rootdir: /Users/sebailla/Developer/taxa
collected 33 items

tests/test_api_freshwater.py::test_domains_without_freshwater PASSED     [  3%]
tests/test_api_freshwater.py::test_domains_with_freshwater PASSED        [  6%]
tests/test_api_freshwater.py::test_children_source_freshwater PASSED     [  9%]
tests/test_api_freshwater.py::test_children_source_col_with_freshwater_root PASSED [ 12%]
tests/test_api_freshwater.py::test_children_source_worms_with_freshwater_root PASSED [ 15%]
tests/test_api_freshwater.py::test_taxon_includes_freshwater_id PASSED   [ 18%]
tests/test_api_freshwater.py::test_taxon_without_freshwater_id PASSED    [ 21%]
tests/test_api_freshwater.py::test_searches_returns_14_entries PASSED    [ 24%]
tests/test_api_freshwater.py::test_searches_urls_are_well_formed PASSED   [ 27%]
tests/test_api_freshwater.py::test_searches_with_authorship PASSED       [ 30%]
tests/test_api_freshwater.py::test_searches_url_encoding PASSED          [ 33%]
tests/test_api_freshwater.py::test_searches_404_for_unknown_taxon PASSED [ 36%]
tests/test_smoke.py::test_root_serves_index_html PASSED                  [ 39%]
tests/test_smoke.py::test_docs_serves_swagger_ui PASSED                  [ 42%]
tests/test_smoke.py::test_openapi_schema_is_valid_json PASSED            [ 45%]
tests/test_smoke.py::test_search_engine_contract_byte_identical PASSED   [ 48%]
tests/test_smoke.py::test_static_index_html_served PASSED                [ 51%]
tests/test_smoke.py::test_static_app_js_served PASSED                    [ 54%]
tests/test_smoke.py::test_health_endpoint_returns_503_without_db SKIPPED [ 57%]
tests/test_smoke.py::TestDbBackedEndpoints::test_domains_returns_5_known_roots SKIPPED [ 60%]
tests/test_smoke.py::TestDbBackedEndpoints::test_taxon_endpoint_returns_record SKIPPED [ 63%]
tests/test_smoke.py::TestDbBackedEndpoints::test_children_endpoint_filters_by_source SKIPPED [ 66%]
tests/test_smoke.py::TestDbBackedEndpoints::test_vernaculars_endpoint_returns_names SKIPPED [ 69%]
tests/test_smoke.py::TestDbBackedEndpoints::test_synonyms_endpoint_returns_names SKIPPED [ 72%]
tests/test_smoke.py::TestDbBackedEndpoints::test_distribution_endpoint_returns_areas SKIPPED [ 75%]
tests/test_smoke.py::TestDbBackedEndpoints::test_search_endpoint_tier_ranking SKIPPED [ 78%]
etl/tests/test_load_freshwater.py::test_load_freshwater_inserts_synthetic_root_and_orders PASSED [ 81%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_orphan_parents PASSED [ 84%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_empty_scientific_name PASSED [ 87%]
etl/tests/test_load_freshwater.py::test_load_freshwater_skips_duplicate_freshwater_id PASSED [ 90%]
etl/tests/test_load_freshwater.py::test_load_freshwater_is_idempotent PASSED [ 93%]
etl/tests/test_load_freshwater.py::test_load_freshwater_adds_columns_on_fresh_db PASSED [ 96%]
etl/tests/test_load_freshwater.py::test_load_freshwater_rolls_up_species_count PASSED [100%]

================== 25 passed, 8 skipped, 53 warnings in 0.44s ==================
```

The 8 skipped tests are pre-existing `TestDbBackedEndpoints::*` placeholders and `test_health_endpoint_returns_503_without_db` (skipped when `data/db/taxa.db` is present in the workspace). All require a populated DB or a missing DB condition and are documented as out-of-scope for the offline pytest suite. The 12 new freshwater tests, all 5 frontend-affecting smoke tests (incl. AC-21 contract test and AC-20 OpenAPI assertion), and the 7 new loader tests all pass. The 25/8 baseline holds.

---

## Review Workload / PR boundary

`tasks.md` declares 3 chained PRs (stacked-to-main), per the §2.1 chain strategy. Inspection of `git log` confirms the 6 freshwater-related commits land on the project's integration branch as direct commits (the workspace chooses direct-stacked over GitHub PRs for the local development loop; there is no `.github/` PR template or `gh pr` workflow that would have been invoked). The deliverable's PR boundaries are therefore expressed at the commit level, not the PR level:

| Expected commit | SHA | Title |
| --- | --- | --- |
| RED scaffold | `11d32a4` | `test(etl): scaffold freshwater loader tests with SQLite in-memory fixture` |
| commit 1 (loader) | `211af74` | `feat(etl): implement freshwater loader with single-pass CSV parse` |
| commit 2 (schema v4) | `4dd1b75` | `feat(etl): add freshwater schema migration with idempotent ALTER` |
| commit 3 (API + endpoint) | `5972ba3` | `feat(api): add freshwater source and /api/taxon/{id}/searches endpoint` |
| commit 4 (frontend) | `a7b218a` | `feat(web): add Búsquedas tab, per-row search icon, and Freshwater toggle` |
| commit 5 (build + docs) | `a92aae9` | `docs(freshwater): README section + make freshwater selector` |

All 6 commits land the assigned slice. No scope-creep commits detected on this branch (no rewrites of unrelated code, no incidental cleanup). One unrelated commit (`063d827 chore(lint): add .shellcheckrc to globally suppress SC1089`) lives between the API and frontend commits and is documented in `apply-progress.md` (it's a pre-existing chore that landed during PR-1's review window — does not affect the AC verification).

---

## Commit hygiene (AC-31)

`git log --format='%B' 11d32a4~1..a92aae9` produced 6 commit messages. Grep for forbidden patterns (`Co-Authored-By`, `Signed-off-by`, `Anthropic`, `Claude`, `GPT`) returns **0 matches** across all 6. All messages follow the conventional-commit format observed in the project's history (`feat(etl):`, `feat(api):`, `feat(web):`, `docs(freshwater):`, `test(etl):`). Body lines are descriptive English without filler or AI attribution. AC-31 satisfied.

---

## tasks.md checkbox reconciliation

`tasks.md` has 5 unchecked `- [ ]` items (lines 599-603). All 5 are tagged `<!-- sdd-owner: parent -->` and belong to the "Post-apply bounded review (parent-owned actions)" group at the end of the file (the orchestrator's PR-open, rebase, and `gentle-ai review status` responsibilities). They are **not implementation tasks**.

The 11 implementation-related checkboxes (`- [x]`) cover all T1.1..T1.11 (PR-1), T2.1..T2.9 (PR-2), T3.1, T3.2 (PR-3). AC-31's gate-check (T3.3) is verified by this report (see AC-31 above); T2.1, T2.5, T2.6, T2.7, T2.8, T2.9, T3.1, T3.2 are checked off in `tasks.md`; their behaviour is verified by either a green pytest test or a confirmed code-level implementation per the per-AC verdicts above.

The 5 unchecked parent-owned boxes are stale-by-design: the project's workflow is direct-stack-to-main (no GitHub PR creation, no rebase between named PRs). Reconciliation applies per the verify protocol's exception: stale-checkbox reconciliation proven by `apply-progress.md`'s "PR-1 / PR-2 / PR-3 work-unit verification" sections, which document direct stacked-to-main merges (`git log` shows the 6 freshwater commits land on the integration branch directly, not behind PR boundaries). Treated as **not-a-blocker** for archive; flagged as remaining scope so the orchestrator can decide whether to formalise them later.

---

## Risk register

| # | Risk | Source | Severity | Status |
| --- | --- | --- | --- | --- |
| R-1 | ~~AC-18 server-side 422 contract is missing.~~ **RESOLVED in commit `4d2f35c`:** `api/server.py::get_searches` now raises `HTTPException(422, ...)` when `scientific_name` is empty; `tests/test_api_freshwater.py::test_searches_422_on_empty_scientific_name` exercises the path. Commit `5e26875` is a follow-up style normalization (no semantic change). | verify finding | Medium | Resolved — see AC-18 entry above for evidence. |
| R-2 | **Frontend ACs (AC-22..AC-29) rely on `scripts/screenshot.py` + manual review.** The project has no Jest/Playwright runner; verification was done by code inspection of `web/app.js` + `web/index.html`, not by automated DOM assertions. A future refactor that subtly changes the toggle binding, the `data-action` strings, or the tab-strip CSS could ship without test coverage catching it. | design §8; tasks §8 | Low | Acknowledged — out of scope for this change. Future PR can add a Playwright suite. |
| R-3 | **`function escape(s)` in `web/app.js` (line ~205) is declared but never called.** Pre-existing dead code (confirmed via `git show 063d827:web/app.js`); the change leaves it alone. | apply-progress §PR-2 risk notes | Trivial | Tracked for a future dead-code-cleanup PR. |
| R-4 | **Stale "Detail panel" bullet in `## What's NOT here yet` section of `README.md`** claims the detail panel is not built — this is now misleading since PR-2's tab strip delivers exactly that. | apply-progress §PR-3 risk notes | Low | Tracked — out of file scope for `make freshwater`. |
| R-5 | **5 unchecked parent-owned action items in `tasks.md`** (PR-open / rebase / `gentle-ai review status`). Not implementation tasks; stale because the workflow is direct-stacked-to-main, not a GitHub-PR workflow. | verify checklist scan | None (reconciled by apply-progress) | Acknowledged. |
| R-6 | **`tests/test_api_freshwater.py` test names deviate from the spec's literal names** for AC-17, AC-19, AC-21 (descriptive name only, no behavioral difference). | verify protocol | Trivial | PASS-WITH-NOTE — keep as-is; rename in a future tests-cleanup pass if a strict-name policy is enforced. |
| R-7 | **`api/server.py::_SEARCH_ENGINES` and `web/search_urls.js::SEARCH_ENGINES` use different template/URL conventions** (server uses `{name}`/`{auth}` placeholders + Python `urllib.parse.quote_plus`; client uses the same placeholders + `encodeURIComponent`). The two encoders are non-byte-identical for non-ASCII inputs (per the explicit caveat in `spec.md` §6.4 / `design.md` §6.4), but the frontend only uses the client-side table for `icon`/`label` fallback, taking the server's `url` field as authoritative — no risk in practice. | design §6.4 caveat | Low | Acknowledged. |
| R-8 | **Loader's `species_count` rollup walks only the synthetic root's subtree** (recursive CTE on `freshwater_parent_id` from `ROOT_DB_ID`); deeper freshwater nodes have `species_count = NULL`. Mirrors `load_worms.py` and `parse_textree.py` precedent. | design §10 | Low | Acknowledged. |

---

## next_recommended

**`archive`** — all 31 ACs PASS (28 PASS + 3 PASS-WITH-NOTE; 0 FAIL). The AC-18 blocker was resolved post-verify by commit `4d2f35c`; follow-up style commit `5e26875` is the dedent normalization of the new test. The change can be archived.

### Blocker

- **AC-18: add a 422 guard to `api/server.py::_build_search` (or `get_searches`) and add `test_searches_422_on_empty_scientific_name` to `tests/test_api_freshwater.py`.** Estimated diff: ~10 lines server + ~15 lines test. No other ACs need attention.

### Resolutions that do NOT change the FAIL count

- Rename the 3 test functions (`test_searches_with_authorship` → `..._on_bhl_and_scholar_only`; `test_searches_404_for_unknown_taxon` → `..._on_unknown_id`; `test_search_engine_contract_byte_identical` → `test_search_engine_contract`) for verbatim-spec compliance. Pure cosmetic; not blocking.
- Optionally remove the stale "Detail panel" bullet from `README.md`'s `## What's NOT here yet` (see R-4). Cosmetic; not blocking.
- Optionally delete the dead `function escape(s)` from `web/app.js` (see R-3). Cosmetic; not blocking.

### Once AC-18 is fixed

`next_recommended` becomes `archive`. The implementation matches the spec on every other axis: backend behaviour + green tests, frontend behaviour + code-level review, cross-file engine contract enforcement green, commit hygiene clean (no AI attribution), loader schema migration idempotent and verified.

---

## skill_resolution

`paths-injected` — `openspec/changes/add-freshwater-and-search/sdd-init.md`, `proposal.md`, `spec.md`, `design.md`, `tasks.md`, `apply-progress.md` were all passed in the delegation prompt and read directly from disk before verification. The remaining sources (`etl/load_freshwater.py`, `etl/schema_v4.sql`, `etl/tests/test_load_freshwater.py`, `tests/test_api_freshwater.py`, `tests/test_smoke.py`, `api/server.py`, `web/search_urls.js`, `web/app.js`, `web/index.html`, `Makefile`, `README.md`) were read in the same pass.

---

## Key Learnings

- Spec deviation drift can pass pytest and still violate the contract: this change shipped with a green test suite for AC-15..AC-19 yet AC-18's 422 path was never implemented, because the test author replaced the missing AC-18 test with an extra AC-the-user-didn't-ask-for test on URL encoding.
- When a spec explicitly documents a defensive contract (e.g. 422 on empty input), the test is the load-bearing part of the contract: a missing test for a defensive path means a missing defensive path, even when the documented behaviour looks "obviously" defensible.
- Stacked-to-main direct commits without GitHub PRs invalidate parent-owned `Open PR-1 against main` checklist items; `tasks.md` should either drop the parent-owned items when delivery is direct-commit, or the file should expose a "delivery mode" header so reconcilers know which convention applies.
