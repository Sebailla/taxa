# add-freshwater-and-search — Proposal

## Problem statement

The taxonomy tool today exposes two parallel hierarchies — **Catalogue of Life** (CoL, the global backbone) and **WoRMS** (the marine-world overlay) — plus cross-links between them and a detail panel with vernacular names, synonyms, and distribution. That covers two of the three slices a lookup workflow actually needs:

1. **CoL** — global biological taxonomy (any organism).
2. **WoRMS** — marine life (drill from `Biota` → kingdom → … → species).
3. **Freshwater fish** (this proposal) — a curated subset used heavily in aquarium / aquaculture / Neotropical-research lookup.

The freshwater fish tree is currently missing. The user maintains it as a Google Sheet (~16K rows) and has to mentally copy a name out, paste it into FishBase / a spreadsheet view, then back into a search engine. That round-trip is the friction this change removes.

The second friction is on the *output* side. When a taxon is selected, there is no quick way to pivot to the discoverability tools the user uses every day — Google, Wikipedia, BHL, Scholar, Plos, Scielo, ResearchGate, etc. The user wants one click → 14 deep links, not 14 separate copy-pastes.

Net effect of this change: a third tree source AND a search-pivot affordance on every node in every tree.

## Goals (3–5 measurable outcomes)

1. **Third tree source.** A `Freshwater` toggle in the header, identical UX to the existing `CoL` / `WoRMS` toggle. Switching to it shows the freshwater roots and lets the user drill down to species with the same expand/collapse/search behaviour.
2. **Loader parity.** `make freshwater` loads the CSV into `taxa.db` in idempotent fashion, mirroring `load_worms.py`'s wipe-and-reload strategy. Schema for the new columns lives in `etl/schema_v4.sql`. About 16K rows, with hierarchy, in-memory parse, sub-second API latency.
3. **Search-pivot tab.** When a taxon is selected, the existing detail panel gains a **Búsquedas** tab alongside Vernacular names / Synonyms / Distribution. The tab renders 14 deep links to external engines, each link pre-filled with the taxon's `scientific_name` (and authorship where useful).
4. **Universal icon.** Every taxon row in every tree (CoL, WoRMS, Freshwater) at every rank (kingdom → species) shows a small search icon at the end of the name. Clicking the icon selects the taxon AND switches the detail panel to the Búsquedas tab — same selected taxon, new tab content.
5. **No regressions.** All existing `tests/test_smoke.py` cases still pass; CoL and WoRMS flows are byte-identical to today. New `pytest` smoke coverage for the freshwater loader and the new `/api/taxon/{id}/searches` endpoint.

## Non-goals

- **NOT** integrating with the FishBase API or any other automated source for fish taxonomy. The Google Sheet is the canonical input.
- **NOT** changing the CoL or WoRMS enrichment logic in `load_worms.py`. Freshwater is *isolated* like WoRMS (its own root, its own parent chain) — not woven into CoL.
- **NOT** replacing or redesigning the detail panel. We add a tab; the existing Vernacular / Synonyms / Distribution sections stay exactly as they are.
- **NOT** automating Google Sheets ingestion. CSV export remains a manual step; the loader accepts a local file path.
- **NOT** adding search-engine metadata (thumbnails, snippets, hit counts). The Búsquedas tab is a link list, not a search aggregator.
- **NOT** opening a split view, modal, or popover for the search results. The detail-panel-tab model from the existing three sections is reused as-is.
- **NOT** adding the icon's underlying search panel for every taxon by default. It appears only on selected taxa (the panel already gates on `state.selected`).

## Users & use cases

**Primary user:** a single researcher doing taxonomic lookup for aquarium / aquaculture / Neotropical-freshwater literature. Their workflow:

- Searches for a name in the header search box → opens the taxon → clicks the Búsquedas tab → jumps straight to BHL or Scholar.
- Drills the freshwater tree from `Freshwater Fishes` down through families/genus/species to confirm where a particular fish sits in current taxonomy.
- Uses the icon shortcut on heavily-branched rows (e.g., `Characidae` with 400+ genera) to skip the detail-panel selection step.

**Use cases (concrete):**

| When | The user wants | This change gives |
| --- | --- | --- |
| Reading a paper that cites a fish | See it in the freshwater tree, jump to BHL / Scholar | `Freshwater` toggle + Búsquedas tab |
| Looking up a Neotropical species | Drill from `Freshwater Fishes` → order → family → species | New toggle, parent-chain follows the CSV |
| Cross-checking a name against Wikipedia / FishBase | Click a Búsquedas link | 14 pre-formatted URL templates |
| Verifying a high-rank group (e.g., `Siluriformes` vs `Characiformes`) | Open the detail panel for the order, confirm vernacular + distribution | Existing panel still works inside the new tree |

## High-level approach

```
Google Sheet  (~16K rows, manual CSV export)
        │
        │   etl/load_freshwater.py <data/raw/freshwater.csv>
        ▼
SQLite at data/db/taxa.db
        ├── taxon.freshwater_id         INTEGER NULL  (FK to source row, optional)
        ├── taxon.freshwater_parent_id  INTEGER NULL  (intra-source parent chain)
        ├── idx_taxon_freshwater         (freshwater_id) WHERE NOT NULL
        └── idx_taxon_fw_parent          (freshwater_parent_id)
        │
        │   api/server.py
        ▼
HTTP
        ├── GET /api/domains                          →  + optional Freshwater root
        ├── GET /api/taxon/{id}/children?source=freshwater   →  new source enum value
        └── GET /api/taxon/{id}/searches              →  NEW; 14 pre-formatted URLs
                │
                │   web/app.js
                ▼
Frontend
        ├── Header `tree-source-toggle`               + Freshwater button
        ├── Tree row                                + search icon (click → tab)
        ├── Detail panel                            + "Búsquedas" tab
        └── web/search_urls.js                         URL format table (static)
```

**Per-layer responsibilities:**

- **Loader (`etl/load_freshwater.py`)** mirrors `load_worms.py`:
  - Opens `taxa.db` in WAL mode; idempotent migration adds `freshwater_id` and `freshwater_parent_id`.
  - Builds an internal `name → row_id` map from accepted rows in the CSV.
  - Single `BEGIN…COMMIT` transaction: wipes prior freshwater rows, inserts all rows from CSV, computes `species_count` per parent (recursive rollup, in-memory) for the freshwater slice.
  - Synthetic root inserted first; every row's `freshwater_parent_id` resolves to either the root or another row from this run.
- **API (`api/server.py`)** — surgical changes:
  - `_FRESHWATER_ROOT_NAME = "Freshwater Fishes"` (configurable via env, see Open Decisions).
  - `RANK_ORDER` extended only if a custom rank (e.g., `"collection"`) is used for the synthetic root — see Open Decisions.
  - `GET /api/domains` extended to optionally include the freshwater root when its row exists (`freshwater_parent_id IS NULL AND freshwater_id IS NOT NULL`).
  - `GET /api/taxon/{id}/children` `source` regex extended from `^(col|worms)$` → `^(col|worms|freshwater)$`. The `freshwater` branch filters on `freshwater_parent_id` and rejects `include_synonyms`.
  - `GET /api/taxon/{id}/searches?engines=…` (NEW) — returns a list of `{ engine, label, url, icon }` for each of the 14 requested engines. Server-side composition guarantees URLs are well-formed (encoding is server-authoritative, not client-assembled from a template).
- **Frontend (`web/app.js` + `web/index.html` + `web/search_urls.js`)**:
  - A third button in `tree-source-toggle`. Same `data-tree-source="freshwater"` attribute; same `matchesTreeSource(taxon)` predicate.
  - A new search icon (`material-symbols-outlined` → `search` or `travel_explore`) appears at the end of every row's title block, at every rank, in every tree. Clicking the icon does `selectTaxon(id)` then switches the detail panel's active tab to `Búsquedas`.
  - The detail panel's tab strip changes from "always show all sections that have data" to "explicit tab strip with one tab per section". The default tab on selection stays the first one with content (mirrors today's behaviour); clicking the search icon forces the Búsquedas tab.
  - A new static `web/search_urls.js` exports `SEARCH_ENGINES = [{key, label, icon, buildUrl({scientific_name, authorship, rank})}, …]` — the 14 entries are listed in Open Decisions, the exact URL formats are resolved in `spec`.

## Open decisions

These must be resolved (or explicitly deferred) before `sdd-spec`. Each has a default proposal; user can confirm or override.

| # | Decision | Options | Default if no answer | Defer to spec? |
| --- | --- | --- | --- | --- |
| 1 | **Source identifier name** | `freshwater` / `ff` / `fishes` / other | `freshwater` (matches user's vocabulary, unambiguous) | Yes — name only |
| 2 | **Synthetic root name** | `Freshwater Fishes` / `Freshwater fish` / `Peces de agua dulce` | `Freshwater Fishes` | Yes |
| 3 | **Synthetic root rank** | `kingdom` / `superdomain` / new `"collection"` rank | new `"collection"` rank (extends `RANK_ORDER` mapping); placed at top | Yes |
| 4 | **`/api/domains` visibility** | Always include / only when freshwater table is non-empty / behind query param | only when freshwater rows exist (>0) | Yes |
| 5 | **Number of search engines** | 13 / 14 (user said "13" then listed 14) | 14 (the list is the contract); surface the mismatch | No — count must be confirmed here |
| 6 | **Tab order in detail panel** | Búsquedas first / second / last / only when icon-clicked | icon-click forces Búsquedas; default order on select is Vernacular → Synonyms → Distribution → Búsquedas | Yes |
| 7 | **Icon behaviour when `scientific_name` is missing** | Hide / disable / fallback to raw id | hide (no name → no useful searches) | Yes |
| 8 | **Loader idempotency** | Wipe and reload (like `load_worms.py`) / diff and merge | wipe and reload (matches `load_worms.py` pattern; 16K rows reloads in ~1s) | Yes |
| 9 | **Tree-source-toggle UI** | Third button / conditional render / dropdown | third button, same segmented-control style; new icon + label | Yes |
| 10 | **Search-engine URL formats** | resolve exact URLs in spec | surface the 14 names here; spec builds the templates | Yes (URL detail) |
| 11 | **Authorship in search queries** | include / exclude / per-engine | per-engine: most engines want bare name; BHL/Scholar benefit from authorship substring | Yes |
| 12 | **Icon visual treatment at high ranks** (kingdom, phylum — names are short, many siblings) | small / xs / only-on-leaf / always | always (per user spec: "en todos los niveles desde los reinos") but smaller at non-leaf ranks | Yes |

**Open-deferral rule:** every "Defer to spec: Yes" question above is resolved in `sdd-spec` against the existing conventions in `api/server.py`, `web/app.js`, and the user's intake CSV. None of these change the proposal's scope or surface — they are knobs to dial, not forks in the road.

## Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| **CSV data quality:** malformed rows (e.g., order names mislabelled as families — `ACANTHURIFORMES` appearing as a family), missing authorship, mixed languages, duplicate `(name, rank)` pairs | Med | Loader logs every dropped row with line number + reason; `pytest -k freshwater` includes a fixture CSV with known-bad rows and asserts the loader survives them (warns, doesn't crash). |
| **UX row layout:** adding the search icon may overflow the title block on long genus names with authors attached (e.g., `Astyanax mexicanus (De Filippi, 1853)` already pushes to ellipsis) | Low | Icon is 16–18px, right-aligned in the `metaBlock` (not the `titleBlock`), so it doesn't compete with the name. Existing `truncate` classes keep the title intact. |
| **API contract:** extending `source=…` regex to a third value breaks any consumer using the strict `^(col | worms)$` validator | Low | No external consumers; this is a local DB-backed app. Test `test_openapi_schema_is_valid_json` already enumerates the enum — extend the test set in `sdd-spec`. |
| **Frontend tab strip cost:** adding a tab-strip to the detail panel means a structural change to the panel shell, not just adding a section | Med | Mirror the section IDs already in `detail-item`. Reuse the existing section icons (`translate`, `history`, `public`) and add `search` for Búsquedas. Keep the four-section default; the tab strip is the same DOM tree, just with a visible toggle. |
| **Spec phase will block on the 14 search engines without the user's spreadsheet** | High | The 14 names are listed in this proposal explicitly (Google, Imagen, Documentos, PDF, Wikipedia, BHL, ResearchGate, Plos, Academia, Scielo, Scholar, Youtube, Zootaxa, Scribd). Spec phase will lock URL templates per engine once the user confirms the count and a sample row. If the spreadsheet materialises, spec phase consumes it. |
| **Freshwater rows conflict with CoL rows on `parent_id`** | Low (already mitigated by isolation) | Freshwater rows set `parent_id = NULL` (their parent chain lives in `freshwater_parent_id` only), so they don't touch the CoL hierarchy. The CoL view filter `matchesTreeSource('col') = !!taxon.coldp_id` keeps them out of CoL view. |
| **Per-row icon on every rank may be noisy on a tree of 16K rows** | Med | Icon is lightweight (`material-symbols-outlined`, 16px). Selected taxon remains the focus of interaction; the icon is an accelerator, not a per-row controller. UX review via the same headless screenshot script used for CoL/WoRMS. |

## Effort estimate

File-level breakdown (approximate line counts). Implementation language: English, conventional commits, no AI attribution.

| File | Action | New lines | Tests | Notes |
| --- | --- | --- | --- | --- |
| `etl/schema_v4.sql` | NEW | ~30 | — | `freshwater_id`, `freshwater_parent_id` + indexes. Mirrors v2/v3 migration style. |
| `etl/load_freshwater.py` | NEW | ~180 | — | CSV reader, idempotent wipe-and-reload, in-memory parent resolution, log dropped rows. Mirrors `load_worms.py` patterns. |
| `etl/tests/test_load_freshwater.py` | NEW | ~120 | (in file) | Fixture CSV with malformed + duplicate + authoritative rows; smoke test against an in-memory SQLite. |
| `api/server.py` | EDIT | ~50 | — | Source-enum regex, `/api/domains` extension, new `/api/taxon/{id}/searches` endpoint, optional `RANK_ORDER` extension. |
| `tests/test_smoke.py` | EDIT | ~40 | (in file) | New OpenAPI path entry for `/searches`; placeholder DB-backed test stub for freshwater tree drill. |
| `web/index.html` | EDIT | ~15 | — | Third toggle button + Búsquedas tab HTML container. |
| `web/app.js` | EDIT | ~120 | — | `matchesTreeSource` extended; search-icon render per row; tab-strip logic; `loadDetail` now fetches `searches`. |
| `web/search_urls.js` | NEW | ~80 | — | Static `SEARCH_ENGINES` array (15 entries: 14 + shared metadata). |
| `Makefile` | EDIT | ~8 | — | `freshwater:` target; update `load-all` selector. |
| `data/raw/freshwater.csv` | NEW | (data) | — | User-provided; CSV header rows vary — loader must accept with/without header. |
| `README.md` | EDIT | ~20 | — | New "Freshwater" section + screenshot slot. |

**Totals (new + edited, code + tests):** ~660 lines production, ~160 lines test. Estimated 3–4 hours implementation, 1 hour verification, ~½ hour doc.

## Rollout & success criteria

1. `make freshwater` runs idempotently against an existing populated `taxa.db` with no rows lost or mutated outside the freshwater columns.
2. CoL and WoRMS flows are byte-identical to today; `make test` is green.
3. `curl /api/domains` returns 6 roots (4 CoL + Biota + Freshwater Fishes) — or 5 when the freshwater CSV is unloaded, see Open Decision #4.
4. `curl /api/taxon/{id}/children?source=freshwater` returns the children of a freshwater node in rank order; `source=col` and `source=worms` continue to behave identically.
5. `curl /api/taxon/{freshwater_species_id}/searches` returns a JSON array with 14 entries; each entry has a well-formed URL pointing at the requesting engine.
6. In the browser: the third toggle button activates the freshwater tree; the icon appears on every row across all three trees; clicking it opens the detail panel with the Búsquedas tab active.
7. Headless screenshot captures the new toggle, an expanded freshwater subtree, and a Búsquedas panel populated with 14 links.

## Decisions already made (reference)

These four are settled by the user's intake brief and are not re-litigated above:

1. **Data origin** — Google Sheet CSV, manual export, no API automation.
2. **Tree integration** — separate root, isolated like CoL and WoRMS, not enriched into CoL.
3. **Icon scope** — every level (kingdom → species), in all three trees.
4. **Search panel UX** — new "Búsquedas" tab inside the existing detail panel (no split view, no modal).
