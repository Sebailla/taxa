# Design — add-freshwater-and-search

## TL;DR

Two independent features land in one change: **a third tree source (Freshwater) loaded from a CSV into isolated columns**, and **a Búsquedas tab on the detail panel with 14 server-composed search-engine links**. The loader mirrors `load_worms.py`'s wipe-and-reload pattern, drops the CoL match pass (freshwater is isolated), and adds one synthetic root with a new `collection` rank that sorts above `domain`. The API adds a new `/api/taxon/{id}/searches` endpoint and extends two existing endpoints' regex/clauses. The frontend adds a conditional third toggle button, a per-row search icon, and a tab strip on the detail panel.

| Knob | Decision | Why |
| --- | --- | --- |
| Loader pattern | Single-pass (no CoL match) | No CoL enrichment target; CSV carries explicit `freshwater_id` / `freshwater_parent_id` |
| Migration | `PRAGMA table_info` + `ALTER TABLE` in loader; `schema_v4.sql` holds only indexes | Matches `load_worms.py` / `load_coldp.py`; columns added where the data is known |
| Synthetic root rank | New `"collection"` (sorts `-1`, above `domain`) | Doesn't pollute existing rank vocabulary; lets UI opt-in |
| `/api/domains` extension | Add `OR (freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL)` | Matches only the synthetic root, not all 16K CSV rows (which also have `parent_id=NULL`) |
| `source=` regex | Widen to `^(col\|worms\|freshwater)$`; new branch filters on `freshwater_parent_id` AND `freshwater_id IS NOT NULL` | CoL/WoRMS branches stay byte-identical |
| `get_searches` | Server composes URLs with `urllib.parse.quote_plus`; never trusts client-built URLs | Server is the single source of truth for query encoding |
| Search-engine sync | Static table in **two** files (`api/server.py`, `web/search_urls.js`); AC-21 contract test enforces byte-identical keys/labels/authorship flags | No build step; spec mandates the dual source |
| Freshwater toggle button | Dynamically inserted in `boot()` when at least one freshwater root exists | Hidden by default; appears only when CSV is loaded |
| Detail panel | New `state.detailTab`; tab strip renders 4 buttons; only active tab's content visible; Búsquedas is default on selection | Spec §5.5 |
| Loader schema | `schema_v4.sql` is indexes-only; for fresh DB the user must run all loaders in order so columns exist before `executescript` | Mirrors existing v2/v3 pattern |

---

## Decisions to lock before apply

These are the design's YES/NO knobs. None of them are open forks; each is the resolved answer from the spec, surfaced here so `sdd-apply` doesn't have to re-litigate.

| # | Knob | Answer | Confirms spec section |
| --- | --- | --- | --- |
| 1 | Synthetic root name | `"Freshwater Fishes"` | §2.2 |
| 2 | Synthetic root rank | `"collection"`; `RANK_ORDER` SQL gets `WHEN 'collection' THEN -1`; `RANK_ORDER` JS array gets `"collection"` prepended | §2.3, §5 |
| 3 | `RANK_PLURAL["collection"]` | Unset; falls back to `rankLabel("collection") + "s"` → `"Collections"` | n/a |
| 4 | Search-engine contract marker | Module-level `_SEARCH_ENGINES` constant in `api/server.py`; `export const SEARCH_ENGINES` in `web/search_urls.js`. AC-21 reads both files as text, extracts the array literal, compares key/label/with_authorship (user-facing fields; `template` and `icon` are excluded — `template` is server-only, `icon` is intentionally free to differ between server `material-symbols-outlined` glyphs and the frontend's unicode-equivalent fallback). | §6.5 |
| 5 | Per-row icon position | Appended to `metaBlock` (right of species count, before row close) | §5.4 |
| 6 | Tab strip rendering | All four content sections always in DOM; only active tab's section has `display: ""`, others have `display: "none"`. Switching tabs is O(1), no re-fetch. | §5.5 |

---

## 1. Module structure

File-by-file plan with size estimates (lines are net new or added on top of existing code). Production estimate: ~620 lines. Test estimate: ~280 lines. **Total ~900 lines** — exceeds the 400-line review budget; flagged for `sdd-tasks` (see §9).

### New files

| File | Action | Lines | Purpose |
| --- | --- | --- | --- |
| `etl/load_freshwater.py` | NEW | ~190 | CSV reader, idempotent migration, wipe-and-reload, in-memory parent map, post-load `species_count` rollup, log-and-skip on malformed rows |
| `etl/schema_v4.sql` | NEW | ~15 | Indexes only: `idx_taxon_freshwater` (partial on `freshwater_id IS NOT NULL`), `idx_taxon_fw_parent` |
| `etl/tests/__init__.py` | NEW | 0 | Marks `etl/tests/` as a package so pytest discovers `test_load_freshwater.py` |
| `etl/tests/test_load_freshwater.py` | NEW | ~120 | AC-1..AC-7: in-memory SQLite fixture + representative CSV |
| `tests/test_api_freshwater.py` | NEW | ~110 | AC-8..AC-19: TestClient hits (skipped today unless fixture DB, mirrors `tests/test_smoke.py::TestDbBackedEndpoints`) |
| `web/search_urls.js` | NEW | ~70 | `SEARCH_ENGINES` array (14 entries), `buildSearchUrl(engineKey, sciName, authorship)` helper |

### Modified files

| File | Action | Lines | Purpose |
| --- | --- | --- | --- |
| `etl/load_worms.py` | (untouched) | 0 | Parity reference; do not edit |
| `api/server.py` | EDIT | ~70 | New `SearchLink` model; two new optional fields on `Taxon`; `_row_to_taxon` pass-through; `RANK_ORDER` extended; `get_domains` new OR clause; `get_children` regex widened + new branch; new `get_searches` endpoint; new module-level `_SEARCH_ENGINES` constant |
| `web/index.html` | EDIT | ~25 | Tab strip CSS (`.detail-tabs`, `.detail-tab`, `.detail-tab.active`); Búsquedas section CSS; freshwater toggle button styles |
| `web/app.js` | EDIT | ~140 | `RANK_ORDER` array prepend; `matchesTreeSource` new branch; per-row search icon render + click handler; tab-strip render; `loadDetail` searches fetch; `boot()` conditional toggle button |
| `tests/test_smoke.py` | EDIT | ~25 | AC-20 (OpenAPI path assertion) + AC-21 (search engine contract test) |
| `Makefile` | EDIT | ~10 | `freshwater:` target; `load-all: col worms freshwater` |
| `README.md` | EDIT | ~25 | Freshwater source subsection; Búsquedas tab subsection; updated API endpoint table |

### Unchanged but referenced

| File | Role |
| --- | --- |
| `etl/load_worms.py` | Parity reference (idempotent wipe-and-reload + migration via `PRAGMA table_info`) |
| `etl/load_coldp.py` | Parity reference (`PRAGMA table_info` + `executescript` for migration + indexes) |
| `etl/schema.sql`, `schema_v2.sql`, `schema_v3.sql` | Existing schema stages; `schema_v4.sql` is the next stage |

---

## 2. Database migration path

**Answer: `schema_v4.sql` + runtime `ALTER TABLE` in the loader (mirroring `load_worms.py`). A separate `schema_v4.sql` file IS needed** because the existing v2/v3 convention is "loader applies its own version's indexes via `executescript(schema_v*.sql)`" — keeping `schema_v4.sql` empty would break that pattern. But the file contains **indexes only** (columns are added by the loader at the same step).

### Pattern

```python
# etl/load_freshwater.py — main()
cur.execute("PRAGMA journal_mode = WAL")
cur.execute("PRAGMA synchronous = NORMAL")
cols = {row[1] for row in cur.execute("PRAGMA table_info(taxon)")}
if "freshwater_id" not in cols:
    cur.execute("ALTER TABLE taxon ADD COLUMN freshwater_id INTEGER")
if "freshwater_parent_id" not in cols:
    cur.execute("ALTER TABLE taxon ADD COLUMN freshwater_parent_id INTEGER")
# schema_v4.sql contains only the indexes — apply them after the columns exist.
conn.executescript((Path(__file__).parent / "schema_v4.sql").read_text())
```

### `etl/schema_v4.sql`

```sql
-- taxa.db schema v4 — adds the freshwater overlay (indexes only; columns are
-- added by etl/load_freshwater.py via PRAGMA-detected ALTER TABLE, same
-- pattern as etl/load_worms.py and etl/load_coldp.py).
-- For a fresh DB: run all loaders in order so the columns exist by the time
-- these indexes are applied.

CREATE INDEX IF NOT EXISTS idx_taxon_freshwater
    ON taxon(freshwater_id) WHERE freshwater_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_taxon_fw_parent
    ON taxon(freshwater_parent_id);
```

### Foreign-key considerations

The `taxon` table has `parent_id INTEGER REFERENCES taxon(id) ON DELETE CASCADE`. The new `freshwater_parent_id` column is **deliberately NOT a SQL-level FK** because:

- Freshwater parents are inserted in the same pass; FK enforcement would force the parent insert before the child insert (would work, but the loader's `parent_id` is already `NULL` for every CSV row, so the FK direction doesn't match).
- Cycles or orphans (CSV `freshwater_parent_id` pointing at a row that doesn't exist) would abort the transaction; we want to log-and-skip, not abort.
- `load_worms.py` has the same choice with `worms_parent_id` — confirmed pattern.

`PRAGMA foreign_keys = ON` is the schema default. We do NOT add a `FOREIGN KEY` clause to `freshwater_parent_id`.

### Ordering on a fresh DB

```
make etl      # parse_textree.py  → schema.sql
make coldp    # load_coldp.py     → coldp_id + is_extinct + schema_v2.sql
# load_distribution.py is a no-op in fresh-DB path; distribution.tsv downloads separately
make worms    # load_worms.py     → worms_id + schema_v3.sql (no, v3 is distribution only)
# ↓ fresh-DB order in current Makefile is: etl → coldp → worms
make freshwater  # load_freshwater.py → freshwater_id + freshwater_parent_id + schema_v4.sql
```

Note: `load_worms.py` does not actually apply `schema_v3.sql` (that's the distribution loader's job). The `schema_v3.sql` is applied by `load_distribution.py`. The freshwater loader follows the same split: columns via PRAGMA check, `schema_v4.sql` indexes via `executescript`.

---

## 3. API response schemas

### 3.1 `Taxon` — two new optional fields

```python
class Taxon(BaseModel):
    id: int
    parent_id: Optional[int]
    rank: str
    status: str
    scientific_name: str
    authorship: Optional[str]
    path: Optional[str]
    species_count: Optional[int]
    coldp_id: Optional[str]
    worms_id: Optional[int] = None
    freshwater_id: Optional[int] = None            # NEW
    freshwater_parent_id: Optional[int] = None      # NEW
    is_extinct: bool
    vernaculars: list[Vernacular] = []
```

`_row_to_taxon` adds the two `row["freshwater_id"]` / `row["freshwater_parent_id"]` keyword args. No SQL change for `get_taxon` (already `SELECT *`).

### 3.2 `SearchLink` — new model

```python
class SearchLink(BaseModel):
    engine: str   # one of the 14 keys
    label: str    # display text
    url: str      # pre-formatted, URL-encoded by server
    icon: str     # material-symbols-outlined glyph
```

### 3.3 `GET /api/domains` — modified

Where clause change:

```sql
SELECT * FROM taxon
WHERE parent_id IS NULL
  AND (
    coldp_id IS NOT NULL
    OR worms_id = 1
    OR (freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL)  -- NEW
  )
ORDER BY scientific_name
```

| Condition | Response length | Names |
| --- | --- | --- |
| Freshwater not loaded | 5 | Archaea, Bacteria, Biota, Eukaryota, Viruses |
| Freshwater loaded | 6 | + Freshwater Fishes |

The third OR clause's `freshwater_parent_id IS NULL` is what restricts the match to the synthetic root. CSV rows have `parent_id=NULL` (so they match the outer `parent_id IS NULL`) but their `freshwater_parent_id` is set (so the third OR clause excludes them).

### 3.4 `GET /api/taxon/{id}/children` — modified

```python
source: str = Query(default="col", pattern="^(col|worms|freshwater)$"),
```

```python
if source == "worms":
    where = "worms_parent_id = ? AND worms_id IS NOT NULL"
elif source == "freshwater":                                         # NEW
    where = "freshwater_parent_id = ? AND freshwater_id IS NOT NULL"
else:
    where = "parent_id = ?"
    if not include_synonyms:
        where += " AND status = 'accepted'"
```

`source=freshwater` always rejects `include_synonyms` (freshwater rows are all `status='accepted'` by construction; the WHERE clause's `freshwater_id IS NOT NULL` already filters to accepted rows).

`source=col` and `source=worms` branches are **byte-identical** to today. Verified by `git diff` after apply.

### 3.5 `GET /api/taxon/{id}/searches` — new

Response 200 — `list[SearchLink]`, **always exactly 14 entries** in the fixed order from spec §6.1.

Full response for `Homo sapiens` (id=1, authorship="Linnaeus, 1758"):

```json
[
  { "engine": "google",      "label": "Google",        "url": "https://www.google.com/search?q=Homo%20sapiens", "icon": "search" },
  { "engine": "imagen",      "label": "Imágenes",      "url": "https://www.google.com/search?q=Homo%20sapiens&tbm=isch", "icon": "image" },
  { "engine": "documentos",  "label": "Documentos",    "url": "https://www.google.com/search?q=Homo%20sapiens+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29", "icon": "description" },
  { "engine": "pdf",         "label": "PDF",           "url": "https://www.google.com/search?q=Homo%20sapiens+filetype%3Apdf", "icon": "picture_as_pdf" },
  { "engine": "wikipedia",   "label": "Wikipedia",     "url": "https://en.wikipedia.org/wiki/Special:Search?search=Homo%20sapiens", "icon": "menu_book" },
  { "engine": "bhl",         "label": "BHL",           "url": "https://www.biodiversitylibrary.org/search?searchTerm=Homo%20sapiens", "icon": "library_books" },
  { "engine": "researchgate","label": "ResearchGate",  "url": "https://www.researchgate.net/search/publication?q=Homo%20sapiens", "icon": "science" },
  { "engine": "plos",        "label": "PLOS",          "url": "https://journals.plos.org/plosone/search?query=Homo%20sapiens", "icon": "article" },
  { "engine": "academia",    "label": "Academia.edu",  "url": "https://www.academia.edu/search?q=Homo%20sapiens", "icon": "school" },
  { "engine": "scielo",      "label": "Scielo",        "url": "https://search.scielo.org/?q=Homo%20sapiens", "icon": "travel_explore" },
  { "engine": "scholar",     "label": "Scholar",       "url": "https://scholar.google.com/scholar?q=Homo%20sapiens", "icon": "school" },
  { "engine": "youtube",     "label": "YouTube",       "url": "https://www.youtube.com/results?search_query=Homo%20sapiens", "icon": "play_circle" },
  { "engine": "zootaxa",     "label": "Zootaxa",       "url": "https://www.biotaxa.org/Zootaxa/search?query=Homo%20sapiens", "icon": "bug_report" },
  { "engine": "scribd",      "label": "Scribd",        "url": "https://www.scribd.com/search?query=Homo%20sapiens", "icon": "auto_stories" }
]
```

For `Astyanax mexicanus (De Filippi, 1853)`:

- `bhl.url` → `https://www.biodiversitylibrary.org/search?searchTerm=Astyanax%20mexicanus%20%28De%20Filippi%2C%201853%29` (authorship appended)
- `scholar.url` → `https://scholar.google.com/scholar?q=Astyanax%20mexicanus%20%28De%20Filippi%2C%201853%29` (authorship appended)
- `google.url` → `https://www.google.com/search?q=Astyanax%20mexicanus` (no authorship)

### 3.6 Error responses for `get_searches`

| Condition | Status | Body |
| --- | --- | --- |
| `taxon_id` not in DB | 404 | `{"detail": "taxon {id} not found"}` (same shape as `get_taxon`) |
| `taxon.scientific_name` empty/null | 422 | `{"detail": "taxon {id} has no scientific_name; cannot build search links"}` |
| Otherwise | 200 | `list[SearchLink]` (14 entries) |

---

## 4. Frontend component structure

### 4.1 Tree-source toggle button (third slot, conditional)

`web/index.html` ships with only the two existing buttons (`CoL`, `WoRMS`). `boot()` adds the `Freshwater` button at the end of `#tree-source-toggle` **after** `/api/domains` returns and only if at least one root has `freshwater_id` set:

```js
// in boot(), after state.roots is populated:
const hasFreshwater = roots.some((r) => r.freshwater_id != null);
if (hasFreshwater) {
  const btn = el("button", {
    type: "button",
    "data-tree-source": "freshwater",
    class: "tree-source-btn",
    "aria-pressed": "false",
  }, "Freshwater");
  document.getElementById("tree-source-toggle").appendChild(btn);
}
```

The `.tree-source-btn` CSS already styles the new button — the click delegation loop in `app.js` (the `forEach` over `[data-tree-source]`) binds automatically because it runs on every button in the container at load time, but **we need to re-bind** after dynamically adding. Simplest fix: convert the listener to delegated `document.addEventListener("click", ...)` like the rest of the handlers. See §4.5.

### 4.2 `matchesTreeSource` extension

```js
function matchesTreeSource(taxon) {
  if (state.treeSource === "col") return !!taxon.coldp_id;
  if (state.treeSource === "worms") return !!taxon.worms_id;
  if (state.treeSource === "freshwater") return taxon.freshwater_id != null;  // NEW
  return true;
}
```

### 4.3 Per-row search icon

`renderNodeRow` builds a `metaBlock` (line ~370 area). Append the icon button to the `metaBlock` after the species-count badge:

```js
const searchIcon = taxon.scientific_name
  ? el(
      "button",
      {
        class:
          "material-symbols-outlined text-[16px] text-on-surface-variant " +
          "hover:text-primary p-1 rounded transition-colors",
        "data-action": "search-from-row",
        "data-taxon-id": taxon.id,
        title: "Búsquedas en la web",
      },
      "search",
    )
  : null;

const metaBlock = el(
  "div",
  { class: "flex items-center gap-2 shrink-0" },
  wormsBadge,
  colBadge,
  statusDot(taxon.status),
  taxon.species_count ? el("span", { class: "..." }, speciesCountBadge(...)) : null,
  searchIcon,                                                                    // NEW
);
```

**Click delegation**: when the user clicks the icon, `e.target.closest("[data-action]")` resolves to the icon button (not the row), so the icon's action wins. No risk of double-firing the row's expand/select handler.

```js
// in the click delegation block:
} else if (action === "search-from-row") {
  const id = parseInt(
    e.target.closest("[data-taxon-id]").dataset.taxonId, 10
  );
  state.detailTab = "busquedas";
  selectTaxon(id);
}
```

`selectTaxon` triggers `loadDetail` and `render`; the render sees `state.detailTab === "busquedas"` and shows the Búsquedas content.

### 4.4 Detail panel — tab strip

`renderDetailPanel` is restructured to render a tab strip header + four content sections, with the active tab's content shown and the others hidden via inline `style.display`.

```js
function renderDetailPanel() {
  // ... existing early-exit when no detail, plus `if (!hasAny && !state.detailLoading) return;` (unchanged) ...

  // Tab strip — only tabs with data are visible, but Búsquedas is always visible
  // when state.detail.searches is non-empty.
  const hasSearches = state.detail.searches && state.detail.searches.length > 0;
  const tabs = [];
  if (hasSearches) tabs.push({ key: "busquedas", label: "Búsquedas", icon: "travel_explore" });
  if (hasVern)     tabs.push({ key: "vernaculars", label: "Vernáculares", icon: "translate" });
  if (hasSyn)      tabs.push({ key: "synonyms", label: "Sinónimos", icon: "history" });
  if (hasDist)     tabs.push({ key: "distribution", label: "Distribución", icon: "public" });

  // Default tab on first paint for a new selection: busquedas if hasSearches,
  // else first non-empty. Icon click forces busquedas (handled at click site).
  if (!tabs.some((t) => t.key === state.detailTab)) {
    state.detailTab = tabs[0]?.key ?? "busquedas";
  }

  const tabStrip = el(
    "div",
    { class: "detail-tabs flex items-center gap-1 border-b border-outline-variant px-4" },
    ...tabs.map((t) =>
      el(
        "button",
        {
          class:
            "detail-tab flex items-center gap-1.5 px-3 py-2 text-body-sm font-semibold uppercase tracking-wider " +
            (t.key === state.detailTab
              ? "detail-tab-active text-primary border-b-2 border-primary -mb-px"
              : "text-on-surface-variant hover:text-on-surface transition-colors"),
          "data-action": "switch-tab",
          "data-tab": t.key,
        },
        el("span", { class: "material-symbols-outlined text-[16px]" }, t.icon),
        t.label,
      ),
    ),
  );

  // ... build sections as today, wrap each in a div with data-tab-content="<key>"
  //     and style="display: none" for non-active tabs ...

  card.appendChild(tabStrip);
  card.appendChild(busquedasContent);  // data-tab-content="busquedas"
  if (hasVern)   card.appendChild(vernContent);
  if (hasSyn)    card.appendChild(synContent);
  if (hasDist)   card.appendChild(distContent);
  // ... rest unchanged ...
}
```

The `data-action="switch-tab"` handler in the click delegation:

```js
} else if (action === "switch-tab") {
  state.detailTab = e.target.closest("[data-tab]").dataset.tab;
  render();
}
```

`renderDetailPanel` keeps the existing "all sections in DOM, only active visible" pattern — switching tabs is O(1) (no re-fetch, no re-render of cards).

### 4.5 Re-binding the tree-source toggle

The current code does `forEach` over `[data-tree-source]` at script load. Dynamically appended buttons won't get the listener. Two options:

| Option | Pros | Cons |
| --- | --- | --- |
| A. Convert the listener to `document.addEventListener("click", ...)` (delegated) | One handler covers current + future buttons; matches the rest of the click handlers in `app.js` | One small refactor |
| B. Re-bind in `boot()` after appending the button | Smaller diff | Two listeners over time if a hot-reload happens; special-case code |

**Choice: A.** Replace the `forEach` with a `data-action="switch-tree-source"` delegation branch, mirroring the existing `search-from-row` and `switch-tab` patterns. The HTML buttons keep their `data-tree-source` attribute, but a new `data-action="switch-tree-source"` is added (or `e.target.closest("[data-tree-source]")` is the action's heuristic).

### 4.6 CSS additions to `web/index.html`

```css
/* Tab strip */
.detail-tabs {
  background: var(--surface);
}
.detail-tab {
  background: transparent;
  border: 0;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: "Raleway", sans-serif;
  letter-spacing: 0.08em;
}
.detail-tab-active {
  /* color + border applied via Tailwind classes above */
}

/* Búsquedas list */
.busquedas-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  margin: 0 -8px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--primary);
  text-decoration: none;
  transition: background-color 120ms ease-out;
}
.busquedas-link:hover {
  background-color: var(--surface-container-low);
}
.busquedas-link .material-symbols-outlined {
  font-size: 18px;
  color: var(--on-surface-variant);
}
.busquedas-link:hover .material-symbols-outlined {
  color: var(--primary);
}
```

---

## 5. Loader state machine

### 5.1 Flow

```
1. Open taxa.db (WAL mode, autocommit via isolation_level=None)
2. PRAGMA table_info(taxon) → check columns
3. ALTER TABLE if columns missing (idempotent migration)
4. executescript(schema_v4.sql) → indexes
5. SELECT COUNT(*) WHERE freshwater_id IS NOT NULL → log
6. BEGIN
7.   DELETE FROM taxon WHERE freshwater_id IS NOT NULL  -- wipe prior run
8.   INSERT synthetic root → capture ROOT_DB_ID
9.   For each CSV row:
       a. validate (non-empty name, known rank, parseable ints, parent resolves)
       b. if invalid: log + skip + continue
       c. INSERT into taxon with parent_id=NULL
       d. fw_map[freshwater_id] = taxon.id
10.  COMMIT
11. Recursive CTE → UPDATE species_count on the synthetic root
12. Print summary (inserted / skipped / orphans)
13. Close DB
```

The "group by family" in the task description is incorrect — the loader is row-by-row with an in-memory `fw_map: dict[int, int]` for parent resolution. The CSV's column order (spec §4.1) is `freshwater_id, freshwater_parent_id, rank, scientific_name, authorship`, so the parent (whether the synthetic root or an earlier row) is already in `fw_map` by the time the child is processed. Topological order is the user's responsibility in the CSV export.

### 5.2 Single-pass vs. WoRMS two-pass

`load_worms.py` is two-pass because:

1. **Pass 1 needs CoL to already exist** to match WoRMS taxa against CoL rows. Without CoL, every WoRMS row would be a "WoRMS-only" insert — defeating the enrichment pattern.
2. **Pass 2 inserts WoRMS-only taxa** whose parents might be either CoL-matched (Pass 1) or WoRMS-only (earlier in Pass 2). The `aphia_to_db` map fills as we go, so order matters but no second pass over the same row is needed.

Freshwater is single-pass because:

1. **No CoL target to match against.** Freshwater rows are isolated; `parent_id` is set to `NULL` for every row, and the hierarchy lives entirely in `freshwater_parent_id`. There's no enrichment to perform.
2. **CSV is the source of truth.** The user maintains the CSV; the loader doesn't have to discover parent relationships. Every row carries `freshwater_parent_id` directly.
3. **16K rows fit in memory.** No need to stream-join across a 1.4M-row table.

The structural mirror to `load_worms.py` is intentional: same PRAGMA-migration pattern, same `BEGIN…COMMIT` transaction shape, same parent-resolution dictionary, same idempotent wipe. A future maintainer reading both files should immediately see the relationship.

### 5.3 Header detection

Spec §4.2: "if the first row's rank field is not in the known-rank set, treat the first row as data (skip header detection)."

Implementation: read the first row, peek at column index 2, check membership in `KNOWN_RANKS` (a set mirroring `RANK_ORDER`). If not present, advance the file iterator by one. If present, treat it as a data row.

Edge case: a known rank that happens to also be a row label. Mitigation: a stricter heuristic — also check that column 0 (freshwater_id) parses as an int. If it does, the row is data; if it doesn't, it's a header.

### 5.4 Logging convention

Match `load_worms.py` style: `print()` to stdout for milestones, `print(..., file=sys.stderr)` for warnings. Lines start with `  ` (two-space indent) for sub-step output. Final summary line: `print(f"  Inserted {n:,} freshwater taxa ({elapsed:.1f}s)")`.

---

## 6. Search URL composition

### 6.1 The dual-source-of-truth problem

`web/search_urls.js` is the frontend's static table. `api/server.py` is the server's table. They MUST agree on:

- **key** (e.g., `"google"`) — used as `SearchLink.engine`
- **label** (e.g., `"Google"`) — used as display text
- **icon** (e.g., `"search"`) — used as material-symbols-outlined glyph
- **with_authorship** (boolean) — whether the engine's URL gets authorship appended

The URL template itself is server-only (the client trusts `SearchLink.url` from the response). The client uses the static table only as a fallback for icon/label rendering of any client-side preview, plus as the AC-21 fixture.

### 6.2 Server-side composition

`api/server.py`:

```python
# Module-level constant. Marked with a comment so the AC-21 contract test
# can find it without depending on a particular function name.
# Each entry: (key, label, icon, template, with_authorship)
_SEARCH_ENGINES = [
    ("google",       "Google",       "search",          "https://www.google.com/search?q={q}",                                                                                                       False),
    ("imagen",       "Imágenes",     "image",           "https://www.google.com/search?q={q}&tbm=isch",                                                                                            False),
    ("documentos",   "Documentos",   "description",     "https://www.google.com/search?q={q}+(filetype:doc+OR+filetype:docx+OR+filetype:txt)",                                                  False),
    ("pdf",          "PDF",          "picture_as_pdf",  "https://www.google.com/search?q={q}+filetype:pdf",                                                                                        False),
    ("wikipedia",    "Wikipedia",    "menu_book",       "https://en.wikipedia.org/wiki/Special:Search?search={q}",                                                                               False),
    ("bhl",          "BHL",          "library_books",   "https://www.biodiversitylibrary.org/search?searchTerm={q}",                                                                             True),
    ("researchgate", "ResearchGate", "science",         "https://www.researchgate.net/search/publication?q={q}",                                                                                  False),
    ("plos",         "PLOS",         "article",         "https://journals.plos.org/plosone/search?query={q}",                                                                                     False),
    ("academia",     "Academia.edu", "school",          "https://www.academia.edu/search?q={q}",                                                                                                  False),
    ("scielo",       "Scielo",       "travel_explore",  "https://search.scielo.org/?q={q}",                                                                                                       False),
    ("scholar",      "Scholar",      "school",          "https://scholar.google.com/scholar?q={q}",                                                                                               True),
    ("youtube",      "YouTube",      "play_circle",     "https://www.youtube.com/results?search_query={q}",                                                                                       False),
    ("zootaxa",      "Zootaxa",      "bug_report",      "https://www.biotaxa.org/Zootaxa/search?query={q}",                                                                                       False),
    ("scribd",       "Scribd",       "auto_stories",    "https://www.scribd.com/search?query={q}",                                                                                                False),
]

def _build_search_links(taxon: sqlite3.Row) -> list[SearchLink]:
    name = (taxon["scientific_name"] or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail=f"taxon {taxon['id']} has no scientific_name; cannot build search links")
    auth = (taxon["authorship"] or "").strip()
    out = []
    for key, label, icon, template, with_auth in _SEARCH_ENGINES:
        q = f"{name} {auth}".strip() if with_auth else name
        url = template.format(q=urllib.parse.quote_plus(q))
        out.append(SearchLink(engine=key, label=label, url=url, icon=icon))
    return out

@app.get("/api/taxon/{taxon_id}/searches", response_model=list[SearchLink])
def get_searches(taxon_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM taxon WHERE id = ?", (taxon_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"taxon {taxon_id} not found")
        return _build_search_links(row)
```

### 6.3 Client-side table

`web/search_urls.js`:

```js
// 14-entry search-engine catalog. KEPT IN SYNC with api/server.py
// _SEARCH_ENGINES via tests/test_smoke.py::test_search_engine_contract
// (AC-21). The server is the source of truth for URLs; the client uses
// this table only for icon/label rendering when the server response is
// unavailable (offline / cache miss / 5xx fallback).
export const SEARCH_ENGINES = [
  { key: "google",       label: "Google",       icon: "search",          template: "https://www.google.com/search?q={q}" },
  { key: "imagen",       label: "Imágenes",     icon: "image",           template: "https://www.google.com/search?q={q}&tbm=isch" },
  { key: "documentos",   label: "Documentos",   icon: "description",     template: "https://www.google.com/search?q={q}+(filetype:doc+OR+filetype:docx+OR+filetype:txt)" },
  { key: "pdf",          label: "PDF",          icon: "picture_as_pdf",  template: "https://www.google.com/search?q={q}+filetype:pdf" },
  { key: "wikipedia",    label: "Wikipedia",    icon: "menu_book",       template: "https://en.wikipedia.org/wiki/Special:Search?search={q}" },
  { key: "bhl",          label: "BHL",          icon: "library_books",   template: "https://www.biodiversitylibrary.org/search?searchTerm={q}", with_authorship: true },
  { key: "researchgate", label: "ResearchGate", icon: "science",         template: "https://www.researchgate.net/search/publication?q={q}" },
  { key: "plos",         label: "PLOS",         icon: "article",         template: "https://journals.plos.org/plosone/search?query={q}" },
  { key: "academia",     label: "Academia.edu", icon: "school",          template: "https://www.academia.edu/search?q={q}" },
  { key: "scielo",       label: "Scielo",       icon: "travel_explore",  template: "https://search.scielo.org/?q={q}" },
  { key: "scholar",      label: "Scholar",      icon: "school",          template: "https://scholar.google.com/scholar?q={q}", with_authorship: true },
  { key: "youtube",      label: "YouTube",      icon: "play_circle",     template: "https://www.youtube.com/results?search_query={q}" },
  { key: "zootaxa",      label: "Zootaxa",      icon: "bug_report",      template: "https://www.biotaxa.org/Zootaxa/search?query={q}" },
  { key: "scribd",       label: "Scribd",       icon: "auto_stories",    template: "https://www.scribd.com/search?query={q}" },
];
```

`app.js` imports it: `import { SEARCH_ENGINES } from "./search_urls.js";`. Used only for the `icon` and `label` fallback; the `url` is taken from the API response.

### 6.4 Sync mechanism (AC-21)

`tests/test_smoke.py::test_search_engine_contract`:

1. Read `api/server.py` as text. Find the marker `_SEARCH_ENGINES = [`, slice from `[` to the matching `]`. Parse the slice with `ast.literal_eval` (after substituting `True`/`False` for `True`/`False`).
2. Read `web/search_urls.js` as text. Find the marker `export const SEARCH_ENGINES = [`, slice from `[` to the matching `]`. Parse each entry as a regex match against `\{ key: "...", label: "...", icon: "...", template: "...", with_authorship: (true|false) \}`.
3. Assert the two parsed lists have the same length, the same `key` in the same order, the same `label` in the same order, and the same `with_authorship` (or its absence, which means False) in the same order.
4. Failure: emit a diff showing which entry/field drifted.

This is the **engine contract** test. It catches accidental drift between server and client. The `template` field is server-only; AC-21 only checks `key`, `label`, `with_authorship` (the user-facing fields).

---

## 7. Error handling

| Failure | Layer | Behaviour |
| --- | --- | --- |
| `data/raw/freshwater.csv` not found | Loader | `print(f"Usage: {sys.argv[0]} <path>")` → `sys.exit(1)` |
| CSV row with non-integer `freshwater_id` | Loader | Log `line N: <reason>`, skip, continue |
| CSV row with empty `scientific_name` | Loader | Log `line N: empty scientific_name`, skip |
| CSV row with unknown `rank` (not in `KNOWN_RANKS`) | Loader | Log `line N: unknown rank '<rank>'`, skip |
| CSV row with orphan `freshwater_parent_id` (not in `fw_map` and not `1`) | Loader | Log WARNING `line N: orphan parent <id>`, skip |
| CSV row with duplicate `freshwater_id` (already in `fw_map`) | Loader | Log `line N: duplicate freshwater_id <id>`, skip (first wins) |
| Loader produced 0 rows | Loader | `print("WARNING: 0 rows loaded; check input CSV")`, exit 0 |
| `DB_PATH` doesn't exist | Loader | `print(f"DB not found: {DB_PATH}")`, exit 1 |
| `taxon_id` not in DB | API `get_searches` | 404 with `{"detail": "taxon {id} not found"}` |
| `taxon.scientific_name` empty/null | API `get_searches` | 422 with `{"detail": "taxon {id} has no scientific_name; cannot build search links"}` |
| `source` query param not in `^(col\|worms\|freshwater)$` | API `get_children` | 422 (FastAPI Query validation) |
| `scientific_name` empty on a tree row | Frontend | No search icon button in the row (rendered conditionally) |
| `state.treeSource === "freshwater"` but `/api/domains` returned no freshwater root | Frontend | `matchesTreeSource` returns `false` for all rows → tree empty. Mitigated by the conditional button: if the toggle wasn't inserted, the user can't enter the broken state. |
| Per-row icon click while no taxon is selected yet | Frontend | `selectTaxon(id)` triggers `loadDetail` which fetches `searches`; if `taxon.scientific_name` is empty the `taxon.scientific_name ?` guard skips the fetch, and the Búsquedas tab shows an empty state. |

---

## 8. Test plan

Each AC maps to a test name. Strict TDD is active: tests are written first, watched to fail, then the implementation is written to make them pass.

### Loader tests — `etl/tests/test_load_freshwater.py`

| AC | Test name | Setup | Assertion |
| --- | --- | --- | --- |
| AC-1 | `test_load_freshwater_inserts_synthetic_root_and_orders` | 4-row CSV: synthetic root + 3 orders | In-memory SQLite has 4 rows with `freshwater_id` set; root has `rank == "collection"` and `freshwater_parent_id IS NULL` |
| AC-2 | `test_load_freshwater_skips_orphan_parents` | CSV with 5 valid + 2 orphan rows; capture logs | 5 valid rows in DB; WARNING for each orphan with line number |
| AC-3 | `test_load_freshwater_skips_empty_scientific_name` | CSV with 3 valid + 1 row where `scientific_name == ""` | 3 valid rows; WARNING for the empty row |
| AC-4 | `test_load_freshwater_skips_duplicate_freshwater_id` | CSV with 4 rows, two of which share `freshwater_id` | 3 distinct rows in DB; WARNING for the duplicate |
| AC-5 | `test_load_freshwater_is_idempotent` | Run loader twice against the same DB | First run inserts N rows; second run returns to N rows; CoL and WoRMS row counts unchanged |
| AC-6 | `test_load_freshwater_adds_columns_on_fresh_db` | Drop a fresh DB without `freshwater_id` column; run loader | Columns added; no error; second run is a no-op |
| AC-7 | `test_load_freshwater_rolls_up_species_count` | CSV with 5 species + 3 genus + 2 family | Root's `species_count` == 5 after loader finishes |

### API tests — `tests/test_api_freshwater.py`

| AC | Test name | Setup | Assertion |
| --- | --- | --- | --- |
| AC-8 | `test_domains_without_freshwater` | DB with CoL + WoRMS only, no `freshwater_id` rows | 5 domains; no `freshwater_id` non-null |
| AC-9 | `test_domains_with_freshwater` | DB with synthetic root inserted | 6 domains; one is `Freshwater Fishes` |
| AC-10 | `test_children_source_freshwater` | Synthetic root + 2 orders | 2 orders returned, sorted by `RANK_ORDER`; all have `freshwater_id` non-null and `freshwater_parent_id == root_id` |
| AC-11 | `test_children_source_col_with_freshwater_root` | Synthetic root selected | Empty list (root has `parent_id IS NULL`) |
| AC-12 | `test_children_source_worms_with_freshwater_root` | Synthetic root selected | Empty list (root has no `worms_parent_id`) |
| AC-13 | `test_taxon_includes_freshwater_id` | CSV-loaded species | `response.freshwater_id == 42`, `response.freshwater_parent_id == 37`, `response.parent_id is None` |
| AC-14 | `test_taxon_without_freshwater_id` | CoL-only taxon | `response.freshwater_id is None` |
| AC-15 | `test_searches_returns_14_entries` | `Homo sapiens` (id=1) | Length 14, order matches spec §6.1 |
| AC-16 | `test_searches_urls_are_well_formed` | `Homo sapiens` | All 14 URLs parse with `urlparse(...).scheme in {"http", "https"}` |
| AC-17 | `test_searches_authorship_on_bhl_and_scholar_only` | `Astyanax mexicanus (De Filippi, 1853)` | `bhl.url` contains `De%20Filippi`; `scholar.url` contains it; `google.url` does NOT |
| AC-18 | `test_searches_422_on_empty_scientific_name` | Taxon with `scientific_name = ""` | 422 with `detail` mentioning `scientific_name` |
| AC-19 | `test_searches_404_on_unknown_id` | `GET /api/taxon/999999999/searches` | 404 |
| AC-20 | (in `tests/test_smoke.py::test_openapi_schema_is_valid_json`) | Existing test, extended | `expected_paths` includes `/api/taxon/{taxon_id}/searches` |
| AC-21 | (in `tests/test_smoke.py::test_search_engine_contract`) | New test | `api/server.py::_SEARCH_ENGINES` and `web/search_urls.js::SEARCH_ENGINES` have identical `key` / `label` / `with_authorship` in the same order |

### Frontend tests — headless via existing screenshot script + DOM assertions

The repo doesn't yet have a frontend test runner (no Playwright/Jest). The frontend ACs are enforced via the existing `scripts/screenshot.py` and manual visual review. AC-26 requires a fetch mock; we add a small DOM-level assertion that the children endpoint is called with the right `source=` param. If the project later adds Playwright, these tests can move to a dedicated suite.

| AC | Enforcement |
| --- | --- |
| AC-22 | `scripts/screenshot.py` captures the header; new assertion in the script checks the DOM after boot contains 3 buttons with the right `data-tree-source` values |
| AC-23 | New assertion in `scripts/screenshot.py` with freshwater not loaded: only 2 buttons present |
| AC-24 | Manual visual review + the icon click test (screenshot captures the detail panel with Búsquedas active) |
| AC-25 | Unit assertion: `renderNodeRow({...scientific_name: ""})` does NOT produce a `data-action="search-from-row"` element. Run via a tiny Node test or document the contract in the screenshot script |
| AC-26 | In the screenshot script, patch `fetch` to record calls; after expanding the synthetic root, assert `fetch` was called with `?source=freshwater` |
| AC-27 | DOM assertion: 4 tab buttons present, in order, after selecting a taxon with all 4 data types |
| AC-28 | DOM assertion: 14 anchor elements with `target="_blank"` inside `.detail-tab-content[data-tab-content="busquedas"]` |
| AC-29 | DOM assertion: switching tree source clears `state.expanded` and `state.cache` children. Verified by stepping through the click handler in `scripts/screenshot.py` |
| AC-30 | `README.md` contains a "Freshwater" subsection under "Data sources" |
| AC-31 | `git log --grep "Co-Authored-By" --grep "AI " -- <branch-range>` returns 0 matches |

### Test-runner integration

`make test` runs `pytest tests/ -v`. The new `tests/test_api_freshwater.py` is in the same package; pytest discovers it automatically. The loader tests in `etl/tests/` are discovered by adding `etl/tests` to the pytest `testpaths` in `pytest.ini` or by symlinking — see the `sdd-tasks` plan for the chosen approach.

---

## 9. Commit / PR plan

### Commit boundaries (one commit per logical unit)

| # | Commit | Files | Approx. lines |
| --- | --- | --- | --- |
| 1 | `etl: add freshwater loader with idempotent migration` | `etl/load_freshwater.py`, `etl/schema_v4.sql` | 205 |
| 2 | `api: add freshwater slice and searches endpoint` | `api/server.py` | 70 |
| 3 | `web: add Búsquedas tab and per-row search icon` | `web/index.html`, `web/app.js`, `web/search_urls.js` | 235 |
| 4 | `test: cover freshwater loader, api, and frontend` | `tests/test_smoke.py`, `tests/test_api_freshwater.py`, `etl/tests/__init__.py`, `etl/tests/test_load_freshwater.py` | 280 |
| 5 | `build+docs: make freshwater target and readme section` | `Makefile`, `README.md` | 35 |

### Workload signal — **flag for sdd-tasks**

**Total: ~825 lines across 5 commits. Exceeds the 400-line review budget.** The `sdd-tasks` phase must:

1. Load the work-unit-commits skill (per orchestrator's Review Workload Guard).
2. Recommend a delivery strategy: 5 chained PRs (one per commit, `stacked-to-main`) OR 1 mega-PR with a size exception.
3. Pre-flight: which PRs are reviewable independently?

| PR | Reviewable independently? | Notes |
| --- | --- | --- |
| 1 (loader) | ✅ | Standalone; existing `taxa.db` is untouched when no CSV is provided. Reviewers can verify with `python3 -c "import sqlite3; ..."` to inspect column existence |
| 2 (API) | ⚠️ Conditional | Depends on commit 1's schema; without freshwater data, only AC-18, AC-19, AC-20 are testable. Recommend merging with commit 1 |
| 3 (frontend) | ⚠️ Conditional | Depends on commit 2's endpoint and commit 1's data; without freshwater loaded, the toggle button doesn't appear (AC-23). Reviewable in conjunction with 1+2 |
| 4 (tests) | ❌ Fails without 1+2+3 | Tests assert behaviours of code that doesn't exist yet |
| 5 (build + docs) | ✅ | Standalone; `make freshwater` and README are independent of code changes |

### Recommended PR shape

**Option A — Three chained PRs (`stacked-to-main`):**

- **PR1**: commits 1 + 2 + 4 (loader, API, tests for both). Reviewable end-to-end. ~575 lines.
- **PR2**: commits 3 + 4 frontend part (frontend + frontend tests). ~430 lines.
- **PR3**: commit 5 (Makefile + README). ~35 lines.

**Option B — One PR with size exception.** Total ~825 lines, all-in. Reviewers commit to a longer review session.

**Choice deferred to `sdd-tasks` per the orchestrator's `ask-on-risk` delivery strategy.**

---

## 10. Risks and trade-offs

### Implementation-revealed risks (not in the spec)

| Risk | Severity | Mitigation |
| --- | --- | --- |
| **`collection` rank breaks any client code that switches on rank** | Med | Prepend `"collection"` to `RANK_ORDER` JS array (line ~456 in `app.js`) and add `WHEN 'collection' THEN -1` to the SQL CASE in `api/server.py`. Verify no `if (taxon.rank === "kingdom")` checks exist in `app.js`; verified by `grep -n "rank.*===" web/app.js` — only `isSpecies` checks `species`/`subspecies` |
| **`RANK_PLURAL` falls back to `Collections`** | Low | Acceptable; the user has only ever seen `species`/`genus`/`family`/etc. plurals. Document the new rank in the README |
| **Recursive CTE `species_count` rollup only updates the synthetic root, not deeper nodes** | Med | Match `load_worms.py` and `parse_textree.py` precedent. The rollup is expensive (~16K rows); deeper nodes get lazy counts on demand. Document in the loader's docstring |
| **No `FOREIGN KEY` on `freshwater_parent_id`** | Low | Intentional (mirrors `worms_parent_id`). Self-referencing FK would require INSERT order = parent-before-child, but orphans are logged-and-skipped, not aborted |
| **Per-row icon increases tree DOM size** | Low | Icon is a single `<button>` with no children; ~30 bytes per row × 16K rows = ~500KB total. Negligible |
| **`/api/taxon/{id}/searches` always returns 14 entries even for taxa with no useful searches (e.g., a row missing rank data)** | Low | 422 guards only `scientific_name` emptiness. Other invalid states (extremely long name, unicode edge cases) are rare and degrade gracefully (the URL just becomes long) |
| **`encodeURIComponent` (client) vs `urllib.parse.quote_plus` (server) differ on some non-ASCII** | Med | Spec asserts equivalence for ASCII test fixtures only. Documented; not enforced by tests |
| **AC-21 contract test parses `web/search_urls.js` via regex** | Med | Fragile if the file is reformatted. Add a comment in the JS file: "DO NOT REFORMAT — parsed by tests/test_smoke.py::test_search_engine_contract" |
| **Boot dynamic button insertion means the toggle's click listener must be delegated, not bound by `forEach`** | Low | Convert to delegation; affects ~5 lines |
| **`loadDetail` fetches `searches` even when Búsquedas tab is never opened** | Low | Adds 1 small request per selection. Could be lazy (fetch on tab click), but the spec's flow assumes it's pre-fetched. Accept |
| **`make freshwater` fails when the CSV is malformed (e.g., wrong column order)** | Med | The error message must guide the user; log a sample of the first 3 bad rows with their line numbers and the expected column layout |
| **The Makefile's `load-all` target now requires three downloads, but `freshwater` has no URL** | Low | Add the missing-CSV hint: `data/raw/freshwater.csv` target fails fast with a `echo "export the Google Sheet as CSV and place it here"` message, matching the pattern in `load_worms.py` if/when it gets one |

### Design tradeoffs explicitly accepted

| Tradeoff | Why we accept it |
| --- | --- |
| Two static tables (`api/server.py` + `web/search_urls.js`) | No build step is the project's convention. AC-21 catches drift. A generated single source would require a build step or a runtime read of the JS file by Python, both more complex than the test-enforced dual source |
| Dynamic append for the freshwater button | The spec says "conditionally inserts/removes". Static HTML with `display: none` is also viable; dynamic is cleaner (no orphan DOM, no CSS state to keep in sync) |
| All four tab content sections always in DOM | Switching tabs is O(1) with no re-fetch. With ~14 small anchor elements in Búsquedas, the section is < 2KB; no memory concern |
| Loader does not roll up `species_count` for non-root nodes | Matches existing precedent (`load_worms.py`). The recursive CTE is run once for the root; non-root counts are computed on demand in `/api/children` (or are simply NULL for the freshwater slice, which is acceptable) |
| `collection` rank with no FK to `RANK_PLURAL` or `rankLabel` | The rank never appears in a user-visible label outside of the synthetic root's name; the rest of the vocabulary doesn't need to pluralize it |
| Freshwater rows have `parent_id = NULL` | Spec §2.1 mandates this. The CoL view's `matchesTreeSource('col') = !!taxon.coldp_id` filter is what keeps them out of the CoL tree. The `/api/domains` WHERE clause's third OR clause (with `freshwater_parent_id IS NULL`) is what keeps them out of the CoL root list |

---

## Out of scope (restated for clarity)

- **FishBase API integration.** The Google Sheet CSV is the only source. (Spec §8)
- **Google Sheets automation.** Manual export stays. (Spec §8)
- **CoL / WoRMS enrichment changes.** `worms_id` migration and `source=worms` branch are byte-identical. (Spec §8, verified by `git diff` after apply)
- **Search engine metadata.** No thumbnails, snippets, hit counts. (Spec §8)
- **Modal / split view for search results.** Tab inside the existing detail panel. (Spec §8)
- **Freshwater vernaculars.** CSV doesn't include them; `load_freshwater.py` doesn't write to `vernacular`. (Spec §8)
- **Multi-language search URLs.** All templates are English-language search portals; the labels are Spanish. (Spec §8)
- **Search ranking changes.** `/api/search` is untouched. (Spec §8)

---

## Next step

This design is the input for `sdd-tasks`. The orchestrator should:

1. Load the work-unit-commits skill (per the Review Workload Guard — total ~825 lines exceeds the 400-line budget).
2. Decide between **Option A (three chained PRs)** and **Option B (one mega-PR with size exception)**.
3. Convert this design into a `tasks.md` with per-commit checklist items, AC-prefixed test names, and conventional-commit messages.

`status: complete` · `next_recommended: "tasks"`
