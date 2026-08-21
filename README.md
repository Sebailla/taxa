# taxa — local Catalogue of Life snapshot

A local snapshot of the [Catalogue of Life](https://www.catalogueoflife.org/)
taxonomy as a single SQLite database, with a tiny FastAPI for navigation,
search, and a vanilla-JS web frontend (port of the Stitch prototype).

Designed as the data backbone for a research web where the tree is the central
search surface for species lookup.

## Status

✅ **Frontend + backend working end-to-end.** Single `make api` and open
`http://127.0.0.1:8765/` — that's the whole loop.

| Stage | Result |
| --- | --- |
| Download TextTree Base | 53 MB compressed → 380 MB uncompressed |
| Parse + rollup + insert | 5,413,595 rows in 273s |
| ColDP enrichments (coldp_id, vernaculars, extinct) | +3.5 min |
| SQLite database | 2.5 GB at `data/db/taxa.db` |
| FastAPI | 7 endpoints, sub-ms latency |
| Frontend | vanilla JS at `web/index.html`, served by FastAPI |

### Counts

- 2,258,977 accepted species
- 2,712,815 synonyms
- 218,821 genera
- 15,055 families
- 1,890 orders
- 147 phyla
- 4 domains (Archaea, Bacteria, Eukaryota, Viruses)
- **327,070 vernacular names** (82,505 distinct taxa, 8+ languages)
- 3,936,783 taxa linked to CoL's own ID (72.7%)
- 111 extinct flags (the ones matched in our subset)

## Quick start

```bash
# 1. Set up Python venv + install deps
make venv

# 2. Download TextTree + build the DB (idempotent; ~5 min)
make etl

# 3. Download ColDP + load vernaculars/coldp_id (~5 min, needs ~2 GB free)
make coldp

# 4. Run the API + frontend
make api
# → http://127.0.0.1:8765
```

## Frontend

Open `http://127.0.0.1:8765/` after `make api`. Single-page app:

- **Sticky header** with title, search box, filters (Source, Extant only),
  nav (Browser/Classification/Settings), and user avatar
- **Breadcrumb** from the taxon's materialized path
- **Tree view** with drill-down navigation, tier-group headers
  ("Phyla (34)" with "Load all" button), rank badges, species counts,
  status dots, and extinct line-through styling
- **Search dropdown** with tier-based BM25 ranking (try "oso", "tiger",
  "wolf", "horse", "homo sapiens") — exact vernacular match wins, then
  prefix match, then substring; lang boost for eng/spa/por/fra/deu. Sub-ms
  latency even at 5.4M taxa.
- **Footer** with API health badge and link to /docs

State is in `web/app.js`; design tokens in `web/index.html`'s Tailwind config
(match the Stitch mockup). No build step.

## API

| Endpoint | Returns |
| --- | --- |
| `GET /api/health` | DB stats: taxa count, vernaculars, extinct |
| `GET /api/domains` | 4 top-level domains |
| `GET /api/taxon/{id}` | Full taxon record + breadcrumb + vernaculars |
| `GET /api/taxon/{id}/children?include_synonyms=&limit=&offset=` | Direct children, sorted by rank |
| `GET /api/taxon/{id}/vernaculars?language=` | Common names (deduped) |
| `GET /api/search?q=&limit=&include_vernacular=` | FTS5 over scientific + authorship + vernaculars |

Visit `http://127.0.0.1:8765/docs` for the live Swagger UI.

### Example: full lineage of *Homo sapiens*

```
GET /api/taxon/2707543
{
  "id": 2707543,
  "rank": "species",
  "scientific_name": "Homo sapiens",
  "authorship": "Linnaeus, 1758",
  "path": "/Eukaryota/Animalia/Chordata/Vertebrata/.../Homo/Homo sapiens",
  "species_count": 1,
  "coldp_id": "7T9XW",
  "is_extinct": false,
  "vernaculars": [
    {"id": 1, "name": "Human", "language": "eng", "country": null},
    ...
  ]
}
```

## Architecture

```
CoL TextTree (53 MB)              CoL ColDP (1 GB)
        ↓                                ↓
etl/parse_textree.py             etl/load_coldp.py
   - in-memory parse                 - stream NameUsage.tsv
   - rollup species_count            - link coldp_id to taxon
   - bulk insert + VACUUM            - load VernacularName.tsv
        ↓                                ↓
        └────────────┬───────────────────┘
                     ↓
            SQLite at data/db/taxa.db
               - taxon (5.4M rows)
               - taxon_fts (FTS5)
               - vernacular (327K rows)
               - vernacular_fts (FTS5)
                     ↓
            FastAPI at api/server.py
               - read-only connections via WAL
               - serves /api/* + web/* from same port
                     ↓
            Frontend at web/
               - index.html (Tailwind CDN)
               - app.js (vanilla, ES modules)
```

## What's NOT here yet (next iterations)

- **Synonym links**: `Synonym.txt` would link synonym names to their accepted
  name (and the reverse, "what are all the names this species has had?").
  Useful for literature searches. ~45 MB.
- **Distribution**: `Distribution.tsv` (122 MB) — geographic range per species.
- **Detail panel** in the frontend: when you click a species, show its
  vernaculars, synonyms, distribution in a side panel.
- **Incremental sync**: CoL releases monthly. `make etl && make coldp` re-runs
  everything in ~10 min. For an automatic workflow, ChecklistBank has a
  job-based incremental mode.

## Data source

Catalogue of Life, Base release 2026-07-14, dataset 315777.
DOI: https://doi.org/10.48580/d37j
License: CC BY 4.0.
