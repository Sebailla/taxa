# Spec — add-freshwater-and-search

## TL;DR

Add a third tree source (Freshwater Fishes, isolated root, ~16K rows from a
manual Google-Sheet CSV export) and a search-pivot tab (Búsquedas, 14 deep
links to external engines) on every taxon row in every tree. Loader is
wipe-and-reload. Detail panel becomes a tab strip with Búsquedas first.

| Layer | Change |
| --- | --- |
| DB schema | `etl/schema_v4.sql` — adds `freshwater_id` + `freshwater_parent_id` columns + indexes on `taxon` |
| Loader | `etl/load_freshwater.py` — new; idempotent CSV → taxon insert; mirrors `load_worms.py` |
| API | `api/server.py` — `source=` regex `^(col\|worms\|freshwater)$`; new `/api/taxon/{id}/searches` |
| Frontend | `web/index.html` + `web/app.js` — third toggle button, per-row search icon, Búsquedas tab |
| Static asset | `web/search_urls.js` — `SEARCH_ENGINES` table (14 entries) |
| Build | `Makefile` — `freshwater:` target + `load-all` selector update |
| Tests | `tests/test_smoke.py` — new path entry + OpenAPI assertion; new `etl/tests/test_load_freshwater.py` |

## 1. Scope

### In scope

- **Freshwater tree source.** CSV (Google Sheet export) → loader → isolated
  subtree under one synthetic root (`Freshwater Fishes`, rank `collection`).
- **Búsquedas tab.** 14 pre-formatted deep links per taxon.
- **Per-row search icon.** Every taxon row in CoL, WoRMS, and Freshwater trees
  at every rank gets a small search icon that selects the taxon and opens the
  Búsquedas tab.
- **Tab strip on detail panel.** Detail panel switches from "sections stacked
  vertically" to "tabs in this order: Búsquedas, Vernacular names, Synonyms,
  Distribution".
- **API surface.** New endpoint `/api/taxon/{id}/searches`; existing
  `/api/domains` and `/api/taxon/{id}/children?source=…` extended.

### Out of scope

- **NOT** integrating FishBase, GBIF, or any other automated fish source. The
  Google Sheet is canonical.
- **NOT** changing CoL or WoRMS enrichment. Freshwater is *isolated*, like
  WoRMS. Freshwater rows set `parent_id = NULL`; their hierarchy lives in
  `freshwater_parent_id` only.
- **NOT** replacing the detail panel shell. Tabs live inside the same `.detail-card`.
- **NOT** automating Google Sheets ingestion. CSV export is a manual step.
- **NOT** search-engine metadata (thumbnails, snippets, hit counts). Each link
  is a static URL template with `scientific_name` interpolated.
- **NOT** a split view, modal, or popover for search results.
- **NOT** changing `/api/search` ranking or behaviour.

## 2. Data model

### 2.1 New columns on `taxon`

Mirrors the `worms_id` migration in `load_worms.py` (idempotent `PRAGMA table_info`
check + `ALTER TABLE` + partial index).

| Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- |
| `freshwater_id` | INTEGER | yes | NULL | Stable id within the freshwater slice; mirrors the CSV row order or the source-sheet row number. Not unique globally — many freshwater taxa already exist as CoL rows with their own `id`. |
| `freshwater_parent_id` | INTEGER | yes | NULL | Points at the `id` of the parent *within* the freshwater slice. `NULL` only on the synthetic root. Independent of `parent_id` (which stays `NULL` for all freshwater rows so they don't pollute the CoL view). |

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_taxon_freshwater
    ON taxon(freshwater_id) WHERE freshwater_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_taxon_fw_parent
    ON taxon(freshwater_parent_id);
```

### 2.2 Synthetic root row

Inserted first, before any CSV row, inside the same loader transaction.

| Field | Value |
| --- | --- |
| `id` | assigned by SQLite (`cur.lastrowid`) |
| `parent_id` | NULL |
| `rank` | `"collection"` (new value) |
| `status` | `"accepted"` |
| `scientific_name` | `"Freshwater Fishes"` |
| `authorship` | NULL |
| `freshwater_id` | a fixed stable id, e.g. `1` (the loader reserves id 1 for the root) |
| `freshwater_parent_id` | NULL |
| `is_extinct` | 0 |

The freshwater slice's `/api/domains` row IS this root (see §3.2). Every CSV
row's `freshwater_parent_id` either points at this root (top-level rows like
`Characiformes`) or at another CSV row inserted earlier in the same pass.

### 2.3 RANK_ORDER extension

New value `"collection"` sorts *before* `"domain"` so the synthetic root
lands at the top of any rank-ordered listing.

```sql
CASE rank
    WHEN 'collection' THEN -1   -- NEW: synthetic freshwater root
    WHEN 'domain' THEN 0
    WHEN 'kingdom' THEN 1
    -- ... unchanged ...
    ELSE 99
END
```

### 2.4 Migration file: `etl/schema_v4.sql`

```sql
-- taxa.db schema v4 — adds freshwater overlay columns.
-- Idempotent: applied via PRAGMA-detected column checks inside
-- etl/load_freshwater.py (same pattern as load_worms.py / load_coldp.py).
-- For a fresh DB: apply schema.sql → v2 → v3 → v4 in order.

-- (Columns added by the loader via ALTER TABLE; only indexes here.)
CREATE INDEX IF NOT EXISTS idx_taxon_freshwater
    ON taxon(freshwater_id) WHERE freshwater_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_taxon_fw_parent
    ON taxon(freshwater_parent_id);
```

## 3. API contract

### 3.1 Pydantic model additions

`api/server.py` gains one new Pydantic model and two fields on `Taxon`.

```python
class SearchLink(BaseModel):
    engine: str          # one of the 14 keys (e.g. "google", "wikipedia")
    label: str           # display text (e.g. "Google", "Wikipedia")
    url: str             # pre-formatted, URL-encoded
    icon: str            # material-symbols-outlined glyph name


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
    freshwater_id: Optional[int] = None        # NEW
    freshwater_parent_id: Optional[int] = None  # NEW
    is_extinct: bool
    vernaculars: list[Vernacular] = []
```

`_row_to_taxon` is updated to pass the two new fields through. No other
endpoint changes its `Taxon` shape; the new fields are optional so legacy
callers that don't read them continue to work.

### 3.2 Modified: `GET /api/domains`

```http
GET /api/domains
```

Response 200 — `list[Taxon]`. Includes the freshwater synthetic root **only
when freshwater data is loaded** (at least one row exists with
`freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL`).

| Condition | Roots returned |
| --- | --- |
| Freshwater not loaded | `Archaea`, `Bacteria`, `Biota` (WoRMS superdomain), `Eukaryota`, `Viruses` (5 — today) |
| Freshwater loaded | 5 + `Freshwater Fishes` (6 total) |

SQL change — add an `OR` clause to the existing WHERE:

```sql
SELECT * FROM taxon WHERE parent_id IS NULL
AND (
    coldp_id IS NOT NULL
    OR worms_id = 1
    OR (freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL)
)
ORDER BY scientific_name
```

The new clause matches **only the synthetic root** (its
`freshwater_parent_id IS NULL`); no other freshwater row has
`parent_id IS NULL` (all CSV rows have `parent_id = NULL` set explicitly, but
their `freshwater_parent_id` points at another freshwater row).

#### Scenario: domains without freshwater

- **GIVEN** `taxa.db` with CoL + WoRMS loaded, no `freshwater_id` rows
- **WHEN** `GET /api/domains`
- **THEN** response is a 5-element list: `{Archaea, Bacteria, Biota, Eukaryota, Viruses}`
- **AND** no row has `freshwater_id IS NOT NULL`

#### Scenario: domains with freshwater loaded

- **GIVEN** `taxa.db` with CoL + WoRMS + Freshwater loaded; synthetic root with `id=9001`, `freshwater_id=1`, `freshwater_parent_id=NULL`
- **WHEN** `GET /api/domains`
- **THEN** response is a 6-element list including a row with `scientific_name == "Freshwater Fishes"` and `freshwater_id == 1`

### 3.3 Modified: `GET /api/taxon/{id}/children`

```http
GET /api/taxon/{id}/children?source=col|worms|freshwater&include_synonyms=false&limit=200&offset=0
```

- `source` regex: `^(col|worms|freshwater)$` (was `^(col|worms)$`).
- New `source=freshwater` branch filters on `freshwater_parent_id` and **always**
  rejects `include_synonyms` (freshwater rows are not synonyms of CoL taxa by
  construction).
- The `source=col` and `source=worms` branches are **byte-identical** to today.

```python
if source == "worms":
    where = "worms_parent_id = ? AND worms_id IS NOT NULL"
elif source == "freshwater":
    where = "freshwater_parent_id = ? AND freshwater_id IS NOT NULL"
else:
    where = "parent_id = ?"
    if not include_synonyms:
        where += " AND status = 'accepted'"
```

#### Scenario: freshwater children

- **GIVEN** synthetic root `Freshwater Fishes` (`id=9001`) and two CSV-loaded orders under it
- **WHEN** `GET /api/taxon/9001/children?source=freshwater&limit=200`
- **THEN** response is a list of those two orders, ordered by `RANK_ORDER` then `scientific_name`
- **AND** every returned row has `freshwater_id IS NOT NULL` and `freshwater_parent_id == 9001`

#### Scenario: source=worms is unchanged

- **GIVEN** Biota (`worms_id=1`)
- **WHEN** `GET /api/taxon/{biota_id}/children?source=worms&limit=200`
- **THEN** response equals the pre-change response (byte-identical); the new regex accepts `worms` and the `worms_parent_id` branch is unmodified

### 3.4 Modified: `GET /api/taxon/{id}`

Response model gains the two new optional fields. No SQL change to this
endpoint — it already does `SELECT * FROM taxon WHERE id = ?`, so the new
columns ride along automatically.

#### Scenario: taxon with freshwater identity

- **GIVEN** a CSV-loaded species `Astyanax mexicanus` with `freshwater_id=42`, `freshwater_parent_id=37`, `parent_id=NULL`
- **WHEN** `GET /api/taxon/{id}`
- **THEN** `response.freshwater_id == 42`
- **AND** `response.freshwater_parent_id == 37`
- **AND** `response.parent_id is None`

#### Scenario: CoL-only taxon (no freshwater)

- **GIVEN** a CoL taxon that has no freshwater counterpart
- **WHEN** `GET /api/taxon/{id}`
- **THEN** `response.freshwater_id is None`
- **AND** `response.freshwater_parent_id is None`

### 3.5 New: `GET /api/taxon/{id}/searches`

```http
GET /api/taxon/{id}/searches
```

Response 200 — `list[SearchLink]`. **Always exactly 14 entries** in the
fixed order from §6. Each `url` is server-composed; the client never builds
URLs from a template.

If `taxon.scientific_name` is empty/null, the endpoint returns
`HTTP 422` with `detail: "taxon {id} has no scientific_name; cannot build search links"`.

If `taxon` doesn't exist, returns `HTTP 404` (existing pattern).

```json
[
  { "engine": "google",      "label": "Google",      "url": "https://www.google.com/search?q=Homo%20sapiens",              "icon": "search" },
  { "engine": "imagen",      "label": "Imágenes",    "url": "https://www.google.com/search?q=Homo%20sapiens&tbm=isch",     "icon": "image" },
  { "engine": "documentos",  "label": "Documentos",  "url": "https://www.google.com/search?q=Homo%20sapiens+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29", "icon": "description" },
  { "engine": "pdf",         "label": "PDF",         "url": "https://www.google.com/search?q=Homo%20sapiens+filetype%3Apdf", "icon": "picture_as_pdf" },
  { "engine": "wikipedia",   "label": "Wikipedia",   "url": "https://en.wikipedia.org/wiki/Special:Search?search=Homo%20sapiens", "icon": "menu_book" },
  { "engine": "bhl",         "label": "BHL",         "url": "https://www.biodiversitylibrary.org/search?searchTerm=Homo%20sapiens", "icon": "library_books" },
  { "engine": "researchgate","label": "ResearchGate","url": "https://www.researchgate.net/search/publication?q=Homo%20sapiens", "icon": "science" },
  { "engine": "plos",        "label": "PLOS",        "url": "https://journals.plos.org/plosone/search?query=Homo%20sapiens", "icon": "article" },
  { "engine": "academia",    "label": "Academia.edu","url": "https://www.academia.edu/search?q=Homo%20sapiens", "icon": "school" },
  { "engine": "scielo",      "label": "Scielo",      "url": "https://search.scielo.org/?q=Homo%20sapiens", "icon": "travel_explore" },
  { "engine": "scholar",     "label": "Scholar",     "url": "https://scholar.google.com/scholar?q=Homo%20sapiens", "icon": "school" },
  { "engine": "youtube",     "label": "YouTube",     "url": "https://www.youtube.com/results?search_query=Homo%20sapiens", "icon": "play_circle" },
  { "engine": "zootaxa",     "label": "Zootaxa",     "url": "https://www.biotaxa.org/Zootaxa/search?query=Homo%20sapiens", "icon": "bug_report" },
  { "engine": "scribd",      "label": "Scribd",      "url": "https://www.scribd.com/search?query=Homo%20sapiens", "icon": "auto_stories" }
]
```

Implementation: imports `urllib.parse.quote_plus`, iterates the 14-entry
`SEARCH_ENGINES` table (single source of truth, shared with `web/search_urls.js`
via the JSON contract — see §6.5), composes each URL.

#### Scenario: returns 14 entries

- **GIVEN** taxon `Homo sapiens` (`id=1`)
- **WHEN** `GET /api/taxon/1/searches`
- **THEN** response has length 14
- **AND** entries appear in the fixed order from §6
- **AND** every `url` is well-formed (parses with `urllib.parse.urlparse` without raising)

#### Scenario: 404 on unknown id

- **WHEN** `GET /api/taxon/999999999/searches`
- **THEN** response is `404 Not Found`

#### Scenario: 422 on missing scientific_name

- **GIVEN** a taxon row with `scientific_name = ""` (defensive — should never happen, but possible after a bad loader run)
- **WHEN** `GET /api/taxon/{id}/searches`
- **THEN** response is `422 Unprocessable Entity` with `detail` mentioning `scientific_name`

#### Scenario: authorship is appended on BHL/Scholar

- **GIVEN** taxon `Astyanax mexicanus (De Filippi, 1853)`
- **WHEN** the URL is composed
- **THEN** the BHL and Scholar URLs include the authorship substring (`%20%28De%20Filippi%2C%201853%29`)
- **AND** the Wikipedia, YouTube, Imagen, and PDF URLs do **not** include authorship (engines where it pollutes results)

## 4. Loader behaviour

### 4.1 CSV input schema

`data/raw/freshwater.csv` — header row optional (loader auto-detects by
checking whether the first row's first field contains a digit or matches a
known rank word).

Expected columns (in order, comma-delimited, UTF-8):

| # | Field | Required | Example | Notes |
| --- | --- | --- | --- | --- |
| 0 | `freshwater_id` | yes | `42` | Stable id within the slice; the loader preserves it. |
| 1 | `freshwater_parent_id` | yes (NULL for root) | `37` | Either the synthetic root's id (1) or another CSV row's `freshwater_id`. |
| 2 | `rank` | yes | `order` | Must be a value handled by the loader; unknown ranks cause the row to be logged and dropped. |
| 3 | `scientific_name` | yes | `Characiformes` | Empty → row dropped. |
| 4 | `authorship` | no | `(De Filippi, 1853)` | Empty string when missing. |

### 4.2 Parsing rules

1. **Header detection:** if the first row's `rank` field is not in the
   known-rank set, treat the first row as data (skip header detection). The
   known-rank set mirrors `RANK_ORDER`: `{collection, domain, kingdom, subkingdom,
   phylum, subphylum, class, subclass, order, suborder, family, subfamily,
   genus, subgenus, species, subspecies, variety, form}`.
2. **Root row pre-insertion:** before any CSV row is processed, insert the
   synthetic root with `freshwater_id=1`, `freshwater_parent_id=NULL`,
   `rank="collection"`, `scientific_name="Freshwater Fishes"`. Hold the new
   `taxon.id` as `ROOT_DB_ID`.
3. **Row-level validation:**
   - `freshwater_id` missing or non-integer → drop, log line+reason.
   - `scientific_name` empty → drop.
   - `rank` not in known set → drop.
   - `freshwater_parent_id` resolves to a `taxon.id` that doesn't exist in
     the in-memory map (built so far in this pass) AND isn't `ROOT_DB_ID` →
     drop with WARNING (orphan; will lose the chain).
4. **Insertion:** each valid row → `INSERT INTO taxon (parent_id, rank, status,
   scientific_name, authorship, freshwater_id, freshwater_parent_id, is_extinct)
   VALUES (NULL, ?, 'accepted', ?, ?, ?, ?, 0)`. The new `taxon.id` is added to
   the `freshwater_id → taxon.id` map for subsequent parent lookups.

### 4.3 Idempotency

Mirrors `load_worms.py` lines 41–63: at the start of the run, count rows with
`freshwater_id IS NOT NULL`. If >0, log the count, `DELETE FROM taxon WHERE
freshwater_id IS NOT NULL`. CoL rows (`freshwater_id IS NULL`) and WoRMS rows
(`worms_id IS NOT NULL, freshwater_id IS NULL`) are untouched.

After deletion, the synthetic root must be re-inserted (its previous `id` was
just deleted) — same `freshwater_id=1` reservation.

### 4.4 Output SQL

```sql
-- Inside the loader transaction:
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- Migration (idempotent)
ALTER TABLE taxon ADD COLUMN freshwater_id INTEGER;
ALTER TABLE taxon ADD COLUMN freshwater_parent_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_taxon_freshwater
    ON taxon(freshwater_id) WHERE freshwater_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_taxon_fw_parent
    ON taxon(freshwater_parent_id);

-- Wipe prior freshwater rows
DELETE FROM taxon WHERE freshwater_id IS NOT NULL;

-- Insert synthetic root (returns ROOT_DB_ID via cur.lastrowid)
INSERT INTO taxon
    (parent_id, rank, status, scientific_name, authorship,
     freshwater_id, freshwater_parent_id, is_extinct)
VALUES
    (NULL, 'collection', 'accepted', 'Freshwater Fishes', NULL,
     1, NULL, 0);

-- For each valid CSV row:
INSERT INTO taxon
    (parent_id, rank, status, scientific_name, authorship,
     freshwater_id, freshwater_parent_id, is_extinct)
VALUES
    (NULL, ?, 'accepted', ?, ?, ?, ?, 0);

-- Post-load: roll up species_count per freshwater parent (recursive CTE,
-- same shape as load_worms.py / parse_textree.py — see comment in those
-- files for the rationale).
UPDATE taxon SET species_count = (
    WITH RECURSIVE descendants(id) AS (
        SELECT id FROM taxon WHERE freshwater_parent_id = :ROOT_DB_ID
        UNION ALL
        SELECT t.id FROM taxon t JOIN descendants d
            ON t.freshwater_parent_id = d.id
    )
    SELECT COUNT(*) FROM descendants d
    JOIN taxon t ON t.id = d.id
    WHERE t.rank IN ('species','subspecies')
)
WHERE freshwater_id = 1;
```

### 4.5 Error handling

| Failure | Behaviour |
| --- | --- |
| File not found | Exit 1 with `Usage: python3 etl/load_freshwater.py <path>` |
| Malformed row (missing freshwater_id, empty name, bad rank) | Skip row, log `line N: <reason>`, continue |
| Orphan parent (CSV row's `freshwater_parent_id` doesn't resolve) | Skip row, log WARNING with line number |
| Total rows loaded == 0 | Exit 0 with WARNING `0 rows loaded; check input CSV` |
| DB lock contention (another process holds the writer) | Standard sqlite3.OperationalError; loader exits non-zero, no auto-retry |

### 4.6 Makefile target

```makefile
freshwater: data/raw/freshwater.csv
 .venv/bin/python3 etl/load_freshwater.py data/raw/freshwater.csv

data/raw/freshwater.csv:
 @echo "data/raw/freshwater.csv not found — export the Google Sheet as CSV and place it here"; \
 exit 1

load-all: col worms freshwater
```

## 5. Frontend behaviour

### 5.1 Header — tree-source-toggle

`web/index.html` adds a third button inside `#tree-source-toggle`:

```html
<button
  type="button"
  data-tree-source="freshwater"
  class="tree-source-btn"
  aria-pressed="false"
>Freshwater</button>
```

**Visibility:** the button is rendered **only when at least one root with
`freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL` is returned by
`/api/domains`**. The `boot()` function in `app.js` checks the loaded roots
for a `freshwater_id` and conditionally inserts/removes the button. The
toggle's `display` is `inline-flex` when visible, `none` when not.

### 5.2 `matchesTreeSource(taxon)` extension

```js
function matchesTreeSource(taxon) {
  if (state.treeSource === "col") return !!taxon.coldp_id;
  if (state.treeSource === "worms") return !!taxon.worms_id;
  if (state.treeSource === "freshwater") return taxon.freshwater_id != null;
  return true;
}
```

### 5.3 Tree-source switch invalidation

Switching to `freshwater` clears the same caches as the existing CoL�WoRMS
switch (children, expanded, showAll). Switching away from `freshwater` while
viewing it is the symmetric operation. Existing implementation in
`app.js` (around the `#tree-source-toggle` event listener) handles this once
the regex/match function is updated.

### 5.4 Per-row search icon

In `renderNodeRow`, after `metaBlock` and before the row's outer close, append
a button:

```js
const searchIcon = taxon.scientific_name
  ? el(
      "button",
      {
        class: "material-symbols-outlined text-[16px] text-on-surface-variant hover:text-primary p-1 rounded transition-colors",
        "data-action": "search-from-row",
        "data-taxon-id": taxon.id,
        title: "Search this taxon on the web",
      },
      "search",
    )
  : null;
```

The icon sits at the end of `metaBlock` (right-aligned), does **not** compete
with the truncated `titleBlock`, and is **hidden when
`scientific_name` is empty/null** (no useful search possible).

**Click behaviour:** `selectTaxon(id)` then `state.detailTab = "busquedas"`.
The existing event delegation pattern handles it via a new `action ===
"search-from-row"` branch.

### 5.5 Detail panel — tab strip

The detail panel changes from "stacked sections" to "tab strip + active
section". A new piece of state:

```js
state.detailTab = "busquedas";  // default; overridden by selectTaxon
```

Tabs (in order):

| # | Tab key | Label | Icon |
| --- | --- | --- | --- |
| 1 | `busquedas` | Búsquedas | `travel_explore` |
| 2 | `vernaculars` | Vernáculares | `translate` |
| 3 | `synonyms` | Sinónimos | `history` |
| 4 | `distribution` | Distribución | `public` |

**Tab visibility:** each tab is shown only when its section has data (today's
behaviour) **except** `busquedas`, which is shown whenever a taxon is
selected (it's the default landing tab on selection).

**Default tab on selection:** `busquedas` if the taxon has a
`scientific_name`; otherwise the first non-empty section (preserves today's
behaviour for taxon rows that lack a name).

**Icon click:** forces `detailTab = "busquedas"`.

**Switching tree source:** resets `detailTab = "busquedas"` to match the
new-selection default.

### 5.6 `loadDetail(id)` extension

Existing function fetches vernaculars, synonyms, distribution. New branch
also fetches `searches`:

```js
async function loadDetail(id) {
  state.detailLoading = true;
  try {
    const taxon = state.cache.get(id)?.taxon ?? await loadTaxon(id);
    const [vern, syn, dist, searches] = await Promise.all([
      api(`/api/taxon/${id}/vernaculars?limit=200`),
      api(`/api/taxon/${id}/synonyms?limit=200`),
      api(`/api/taxon/${id}/distribution?limit=200`),
      taxon.scientific_name ? api(`/api/taxon/${id}/searches`) : Promise.resolve([]),
    ]);
    if (state.selected !== id) return;
    state.detail = { vernaculars: vern, synonyms: syn, distribution: dist, searches };
  } catch (e) {
    console.error("detail load failed", e);
    state.detail = { vernaculars: [], synonyms: [], distribution: [], searches: [] };
  } finally {
    state.detailLoading = false;
    render();
  }
}
```

The `taxon.scientific_name ? …` guard mirrors the server-side 422 — the
frontend never even asks for search links for nameless taxa.

### 5.7 New static module: `web/search_urls.js`

Imported by `app.js`. Single source of truth for the 14 engines and their
URL templates. Mirrors the server-side composition (see §6). The frontend
*trusts the server's `url` field* and uses the static table only as a
fallback for icon/label rendering (and as the unit-test fixture).

```js
export const SEARCH_ENGINES = [
  { key: "google",      label: "Google",       icon: "search",          template: "https://www.google.com/search?q={q}" },
  { key: "imagen",      label: "Imágenes",     icon: "image",           template: "https://www.google.com/search?q={q}&tbm=isch" },
  // ... 12 more ...
];

export function buildSearchUrl(engine, scientificName, authorship) {
  // Mirror server logic: include authorship only for bhl/scholar.
  const q = engine.key === "bhl" || engine.key === "scholar"
    ? `${scientificName} ${authorship ?? ""}`.trim()
    : scientificName;
  return engine.template.replace("{q}", encodeURIComponent(q));
}
```

## 6. Search URL formats

### 6.1 The 14 engines, in fixed order

This order is the contract — both server and client iterate it in this order.
Reordering is a breaking API change.

| # | Key | Label | Icon | Template (server) | Authorship appended? |
| --- | --- | --- | --- | --- | --- |
| 1 | `google` | Google | `search` | `https://www.google.com/search?q={q}` | no |
| 2 | `imagen` | Imágenes | `image` | `https://www.google.com/search?q={q}&tbm=isch` | no |
| 3 | `documentos` | Documentos | `description` | `https://www.google.com/search?q={q}+(filetype:doc+OR+filetype:docx+OR+filetype:txt)` | no |
| 4 | `pdf` | PDF | `picture_as_pdf` | `https://www.google.com/search?q={q}+filetype:pdf` | no |
| 5 | `wikipedia` | Wikipedia | `menu_book` | `https://en.wikipedia.org/wiki/Special:Search?search={q}` | no |
| 6 | `bhl` | BHL | `library_books` | `https://www.biodiversitylibrary.org/search?searchTerm={q}` | **yes** |
| 7 | `researchgate` | ResearchGate | `science` | `https://www.researchgate.net/search/publication?q={q}` | no |
| 8 | `plos` | PLOS | `article` | `https://journals.plos.org/plosone/search?query={q}` | no |
| 9 | `academia` | Academia.edu | `school` | `https://www.academia.edu/search?q={q}` | no |
| 10 | `scielo` | Scielo | `travel_explore` | `https://search.scielo.org/?q={q}` | no |
| 11 | `scholar` | Scholar | `school` | `https://scholar.google.com/scholar?q={q}` | **yes** |
| 12 | `youtube` | YouTube | `play_circle` | `https://www.youtube.com/results?search_query={q}` | no |
| 13 | `zootaxa` | Zootaxa | `bug_report` | `https://www.biotaxa.org/Zootaxa/search?query={q}` | no |
| 14 | `scribd` | Scribd | `auto_stories` | `https://www.scribd.com/search?query={q}` | no |

`{q}` is `urllib.parse.quote_plus(scientific_name)` (server) /
`encodeURIComponent(scientific_name)` (client). These produce identical
output for ASCII names; the spec asserts equivalence only for ASCII test
fixtures to avoid UTF-8 edge-case ambiguity.

### 6.2 Worked examples — `Homo sapiens`

| Engine | URL |
| --- | --- |
| google | `https://www.google.com/search?q=Homo%20sapiens` |
| imagen | `https://www.google.com/search?q=Homo%20sapiens&tbm=isch` |
| documentos | `https://www.google.com/search?q=Homo%20sapiens+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29` |
| pdf | `https://www.google.com/search?q=Homo%20sapiens+filetype%3Apdf` |
| wikipedia | `https://en.wikipedia.org/wiki/Special:Search?search=Homo%20sapiens` |
| bhl | `https://www.biodiversitylibrary.org/search?searchTerm=Homo%20sapiens` |
| researchgate | `https://www.researchgate.net/search/publication?q=Homo%20sapiens` |
| plos | `https://journals.plos.org/plosone/search?query=Homo%20sapiens` |
| academia | `https://www.academia.edu/search?q=Homo%20sapiens` |
| scielo | `https://search.scielo.org/?q=Homo%20sapiens` |
| scholar | `https://scholar.google.com/scholar?q=Homo%20sapiens` |
| youtube | `https://www.youtube.com/results?search_query=Homo%20sapiens` |
| zootaxa | `https://www.biotaxa.org/Zootaxa/search?query=Homo%20sapiens` |
| scribd | `https://www.scribd.com/search?query=Homo%20sapiens` |

### 6.3 Worked examples — `Astyanax mexicanus (De Filippi, 1853)`

Authorship substring is appended only for `bhl` and `scholar`. Other engines
get the bare name.

| Engine | URL |
| --- | --- |
| bhl | `https://www.biodiversitylibrary.org/search?searchTerm=Astyanax%20mexicanus%20%28De%20Filippi%2C%201853%29` |
| scholar | `https://scholar.google.com/scholar?q=Astyanax%20mexicanus%20%28De%20Filippi%2C%201853%29` |
| google | `https://www.google.com/search?q=Astyanax%20mexicanus` |

### 6.4 Server-side composition

```python
import urllib.parse

def _build_search_links(taxon) -> list[SearchLink]:
    name = (taxon.scientific_name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail=f"taxon {taxon.id} has no scientific_name")
    auth = (taxon.authorship or "").strip()

    engines = [
        ("google",       "Google",       "search",          f"https://www.google.com/search?q={q}",                                   False),
        ("imagen",       "Imágenes",     "image",           f"https://www.google.com/search?q={q}&tbm=isch",                           False),
        ("documentos",   "Documentos",   "description",     f"https://www.google.com/search?q={q}+(filetype:doc+OR+filetype:docx+OR+filetype:txt)", False),
        ("pdf",          "PDF",          "picture_as_pdf",  f"https://www.google.com/search?q={q}+filetype:pdf",                       False),
        ("wikipedia",    "Wikipedia",    "menu_book",       f"https://en.wikipedia.org/wiki/Special:Search?search={q}",              False),
        ("bhl",          "BHL",          "library_books",   f"https://www.biodiversitylibrary.org/search?searchTerm={q}",            True),
        ("researchgate", "ResearchGate", "science",         f"https://www.researchgate.net/search/publication?q={q}",                 False),
        ("plos",         "PLOS",         "article",         f"https://journals.plos.org/plosone/search?query={q}",                    False),
        ("academia",     "Academia.edu", "school",          f"https://www.academia.edu/search?q={q}",                                 False),
        ("scielo",       "Scielo",       "travel_explore",  f"https://search.scielo.org/?q={q}",                                       False),
        ("scholar",      "Scholar",      "school",          f"https://scholar.google.com/scholar?q={q}",                              True),
        ("youtube",      "YouTube",      "play_circle",     f"https://www.youtube.com/results?search_query={q}",                      False),
        ("zootaxa",      "Zootaxa",      "bug_report",      f"https://www.biotaxa.org/Zootaxa/search?query={q}",                      False),
        ("scribd",       "Scribd",       "auto_stories",    f"https://www.scribd.com/search?query={q}",                               False),
    ]

    out = []
    for key, label, icon, template, with_auth in engines:
        q = urllib.parse.quote_plus(f"{name} {auth}" if with_auth else name)
        out.append(SearchLink(engine=key, label=label, url=template.format(q=q), icon=icon))
    return out
```

### 6.5 Single source of truth

The 14-entry engine list lives in **two** places that MUST stay in sync:

1. `api/server.py` — Python literal (the table above).
2. `web/search_urls.js` — JS export (the same table).

A pytest test (`tests/test_smoke.py::test_search_engine_contract`) opens
both files, parses the entries in order, and asserts the keys, labels, and
authorship flags are byte-identical. This is the **engine contract** test —
it catches accidental drift between server and client.

## 7. Acceptance criteria

Each criterion maps 1:1 to a pytest test or a frontend assertion. Strict TDD
mode is active — implement tests first, watch them fail, then ship the code.

### Loader (`etl/tests/test_load_freshwater.py`)

- **AC-1** Given a CSV with the synthetic root row plus 3 valid orders under
  it, when `load_freshwater` runs against a fresh in-memory SQLite, then the
  `taxon` table contains exactly 4 rows with `freshwater_id` set, and the
  root row has `scientific_name == "Freshwater Fishes"`, `rank == "collection"`,
  `freshwater_parent_id IS NULL`.
- **AC-2** Given a CSV where 2 rows have `freshwater_parent_id` values that
  don't resolve to any row in the same file, when `load_freshwater` runs,
  then those 2 rows are skipped (not inserted) and the loader logs a WARNING
  containing the line number; the remaining rows are inserted.
- **AC-3** Given a CSV with 1 row whose `scientific_name` is empty, when
  `load_freshwater` runs, then that row is skipped and a WARNING is logged;
  the rest of the file loads normally.
- **AC-4** Given a CSV with a duplicate `freshwater_id` (same id twice), when
  `load_freshwater` runs, then the second occurrence is skipped (the first
  wins) and a WARNING is logged.
- **AC-5** Given a populated `taxa.db` with `freshwater_id` already set on
  some rows, when `load_freshwater` runs against the same DB, then those
  prior rows are deleted (count returns to 0) before the new run inserts;
  CoL rows (`freshwater_id IS NULL`) and WoRMS rows (`worms_id IS NOT NULL`)
  are untouched (count unchanged).
- **AC-6** Given a fresh DB without the `freshwater_id` column, when
  `load_freshwater` runs, then the loader adds the column via `ALTER TABLE`
  and the run succeeds; a second run is a no-op on schema (idempotent
  migration).
- **AC-7** Given a valid CSV with N rows, when `load_freshwater` finishes,
  then the synthetic root's `species_count` equals the total number of rows
  in the CSV whose `rank` is `species` or `subspecies` (recursive rollup).

### API (`tests/test_smoke.py` + new `tests/test_api_freshwater.py`)

- **AC-8** `GET /api/domains` against a DB without freshwater rows returns a
  list of length 5 (Archaea, Bacteria, Biota, Eukaryota, Viruses).
- **AC-9** `GET /api/domains` against a DB with the synthetic root inserted
  returns a list of length 6, including a row with
  `scientific_name == "Freshwater Fishes"`.
- **AC-10** `GET /api/taxon/{root_id}/children?source=freshwater&limit=200`
  returns the freshwater children of the synthetic root, ordered by
  `RANK_ORDER` then `scientific_name`.
- **AC-11** `GET /api/taxon/{root_id}/children?source=col&limit=200` (with a
  freshwater root selected) returns the CoL children of that same id (empty
  for the synthetic root since it has `parent_id IS NULL`).
- **AC-12** `GET /api/taxon/{root_id}/children?source=worms&limit=200` (with
  a freshwater root selected) returns an empty list (synthetic root has no
  `worms_parent_id`).
- **AC-13** `GET /api/taxon/{id}` for a freshwater-loaded taxon returns a
  body with non-null `freshwater_id` and `freshwater_parent_id`.
- **AC-14** `GET /api/taxon/{id}` for a CoL-only taxon (no freshwater
  counterpart) returns a body with `freshwater_id is None`.
- **AC-15** `GET /api/taxon/{homo_sapiens_id}/searches` returns a list of
  length 14 in the fixed order from §6.1.
- **AC-16** Each of the 14 URLs in that response parses with
  `urllib.parse.urlparse(url).scheme in {"http", "https"}` (no malformed
  URLs leak through).
- **AC-17** `GET /api/taxon/{astyanax_id}/searches` for `Astyanax mexicanus (De Filippi, 1853)`
  has the BHL entry's URL containing `De%20Filippi` and the Google entry's
  URL **not** containing `De%20Filippi`.
- **AC-18** `GET /api/taxon/{nameless_id}/searches` for a taxon with
  `scientific_name == ""` returns 422.
- **AC-19** `GET /api/taxon/999999999/searches` returns 404.
- **AC-20** `tests/test_smoke.py::test_openapi_schema_is_valid_json` updated
  to include `/api/taxon/{taxon_id}/searches` in the expected paths set.
- **AC-21** `tests/test_smoke.py::test_search_engine_contract` parses the
  14-entry table from `api/server.py` and `web/search_urls.js` and asserts
  the keys, labels, and authorship flags match exactly.

### Frontend (headless / DOM assertions)

- **AC-22** With freshwater loaded, `#tree-source-toggle` contains 3 buttons
  with `data-tree-source` values `col`, `worms`, `freshwater` (in that order);
  the `freshwater` button has `aria-pressed="true"` after click.
- **AC-23** With freshwater NOT loaded, the `freshwater` button is not in
  the DOM (or has `display: none`); only `col` and `worms` are present.
- **AC-24** Clicking the per-row search icon on a taxon row opens the
  detail panel with the `busquedas` tab active (not vernaculars/synonyms/
  distribution even when those sections have data).
- **AC-25** A taxon row whose `scientific_name` is empty renders **no**
  search icon (assert the icon button is not in the row's children).
- **AC-26** With `state.treeSource === "freshwater"`, drilling into
  `Freshwater Fishes` and expanding children calls
  `/api/taxon/{id}/children?source=freshwater&limit=200` exactly once per
  expand (assert via fetch mock / network log).
- **AC-27** After selecting a taxon, the detail panel renders a tab strip
  with tabs `busquedas`, `vernaculars`, `synonyms`, `distribution` (in that
  order); only the tabs with data (plus `busquedas` always) are visible.
- **AC-28** The `busquedas` tab renders exactly 14 anchor elements with
  `target="_blank"` and `href` matching one of the 14 templates from §6.1.
- **AC-29** Switching tree source from `col` to `freshwater` (then back)
  clears the children cache and `state.expanded` (same invalidation rules
  as the existing CoL↔WoRMS toggle).

### Documentation / metadata

- **AC-30** `README.md` has a "Freshwater" subsection under the Data Sources
  heading describing the CSV input and `make freshwater` invocation.
- **AC-31** No commit message contains `Co-Authored-By:` or AI attribution
  (checked by `git log --grep` returning 0 matches for the change's branch).

## 8. Out of scope (restated for clarity)

- **FishBase migration.** Not now. The Google Sheet is canonical.
- **Google Sheets API automation.** Manual CSV export stays.
- **CoL / WoRMS flow changes.** The `worms_id` migration and `/api/taxon/{id}/children?source=worms`
  path are byte-identical to today; only the regex widens.
- **Search ranking changes.** `/api/search` ranking and tier logic are untouched.
- **Search engine metadata.** No thumbnails, snippets, hit counts.
- **Modal / split view for search results.** Tab inside the existing
  detail panel — that's it.
- **Freshwater vernaculars.** The CSV does not include common names;
  `load_freshwater.py` does not write to the `vernacular` table.
- **Multi-language search URLs.** All templates are in English-language
  search portals (the labels are Spanish: "Búsquedas", "Imágenes",
  "Documentos" — but the URL hosts themselves are not localised).

## 9. Open decisions — resolution

These were deferred from the proposal. Each is resolved here against the
existing codebase patterns.

| # | Decision | Resolution |
| --- | --- | --- |
| 1 | Source identifier name | `freshwater` |
| 2 | Synthetic root name | `Freshwater Fishes` |
| 3 | Synthetic root rank | `"collection"`; `RANK_ORDER` maps to `-1` (sorts before `domain`) |
| 4 | `/api/domains` visibility | Only when at least one row with `freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL` exists |
| 5 | Number of search engines | 14 (per user confirmation 2026-08-22) |
| 6 | Tab order | Búsquedas first; Vernaculars, Synonyms, Distribution after |
| 7 | Icon when no `scientific_name` | Hidden (no useful searches) |
| 8 | Loader idempotency | Wipe-and-reload (mirrors `load_worms.py`) |
| 9 | Tree-source-toggle UI | Third "Freshwater" button, segmented-control style, conditional render |
| 10 | Search-engine URL formats | See §6.1; BHL and Scholar append authorship |
| 11 | Authorship in search queries | Per-engine (BHL and Scholar only) |
| 12 | Icon visual treatment at high ranks | 16px `material-symbols-outlined` in `metaBlock`, identical at all ranks; no per-rank sizing |

## 10. Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| CSV with mixed header conventions (some sheets export with header, some without) | Med | Loader auto-detects: if first row's rank field isn't in the known set, skip-as-header and start parsing from row 1 |
| Orphan parents (CSV references a row outside its own file) | Med | Loader skips with WARNING; logged line numbers exposed via `--verbose` |
| Synthetic root id collision with CoL/WoRMS ids | Low | Loader reserves `freshwater_id=1` for the root but uses SQLite's `lastrowid` for the actual `taxon.id`; no conflict possible |
| Per-row icon visual noise on trees of 16K rows | Low | Icon is 16px, hover-only color shift, gated by `scientific_name` presence; existing CSS classes keep row layout intact |
| Search URL drift between server and client | Med | AC-21 enforces byte-identical engine tables; CI fails on drift |
| `/api/taxon/{id}/children?source=freshwater` accidentally returns CoL data | Low | New WHERE branch filters on `freshwater_parent_id` AND `freshwater_id IS NOT NULL`; CoL rows have `freshwater_id IS NULL` by construction |
| Tab strip breaks the existing detail panel layout | Med | Tab strip lives inside the same `.detail-card`; no changes to `.detail-header`, `.detail-section`, or the card's outer shell |

## 11. Next phase

`sdd-design` is the orchestrator's next call. This spec is the input.
