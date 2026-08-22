"""
Minimal FastAPI server for the taxa tree.

Endpoints
---------
GET  /                                              → redirect to /docs
GET  /api/health                                    → DB stats
GET  /api/domains                                   → top-level domains
GET  /api/taxon/{id}                                → single taxon + breadcrumb
GET  /api/taxon/{id}/children                       → direct children (paginated)
GET  /api/taxon/{id}/vernaculars                    → common names for this taxon
GET  /api/taxon/{id}/searches                       → 14 server-composed search URLs
GET  /api/search?q=                                 → search across scientific name,
                                                           authorship AND vernacular

Run:
    uvicorn api.server:app --reload --port 8765
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# pyright: ignore — pyright can't resolve `etl.migrations` against this
# project's package layout. The import resolves fine at runtime (verified
# by all 14 etl tests); this is a static-checker false positive.
from etl.migrations import CURRENT_SCHEMA_VERSION, get_applied_version  # pyright: ignore

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "taxa.db"
WEB_DIR = Path(__file__).parent.parent / "web"

_logger = logging.getLogger(__name__)


def db() -> sqlite3.Connection:
    """Open a fresh read-only connection. Cheap because of WAL mode."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="taxa.db not ready; ETL running?")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


app = FastAPI(title="Taxa Tree API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    # Local-only API — restrict CORS to localhost / 127.0.0.1 on any port.
    # Same-origin requests (the typical case: frontend served by this app)
    # bypass CORS entirely; this only matters when someone runs the
    # frontend from a different port (e.g. Vite dev server on :5173)
    # during local development. No remote origins are allowed.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/", include_in_schema=False)
def root():
    """Deprecated — the StaticFiles mount at the bottom of this file serves
    the frontend now. Kept as a fallback when the web/ dir is empty."""
    index = WEB_DIR / "index.html"
    if not index.exists():
        return RedirectResponse(url="/docs")
    # The mount will handle this in production; this is a safety net.
    from fastapi.responses import FileResponse
    return FileResponse(str(index))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


class Vernacular(BaseModel):
    id: int
    name: str
    language: Optional[str]
    country: Optional[str]


class Synonym(BaseModel):
    id: int
    rank: str
    scientific_name: str
    authorship: Optional[str]
    status: str  # "synonym", "ambiguous synonym", "misapplied", etc.


class DistributionEntry(BaseModel):
    id: int
    area: str
    gazetteer: Optional[str]
    establishment_means: Optional[str]
    degree_of_establishment: Optional[str]


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
    freshwater_id: Optional[int] = None
    freshwater_parent_id: Optional[int] = None
    is_extinct: bool
    vernaculars: list[Vernacular] = []


class SearchLink(BaseModel):
    """A single pre-composed search-engine link for a taxon.

    The URL is server-composed (urllib.parse.quote_plus) so the frontend
    never has to build search queries itself. The 14 entries are produced
    by `_build_search` from the `_SEARCH_ENGINES` module-level constant.
    """
    engine: str   # one of the 14 keys (e.g. "google", "wikipedia")
    label: str    # display text (e.g. "Google", "Wikipedia")
    url: str      # pre-computed, fully URL-encoded


RANK_ORDER = """
    CASE rank
        WHEN 'collection' THEN -1   -- synthetic root (reserved for "Freshwater Fishes"); sorts above domain
        WHEN 'domain' THEN 0
        WHEN 'kingdom' THEN 1
        WHEN 'phylum' THEN 2
        WHEN 'subphylum' THEN 3
        WHEN 'class' THEN 4
        WHEN 'subclass' THEN 5
        WHEN 'order' THEN 6
        WHEN 'suborder' THEN 7
        WHEN 'family' THEN 8
        WHEN 'subfamily' THEN 9
        WHEN 'genus' THEN 10
        WHEN 'subgenus' THEN 11
        WHEN 'species' THEN 12
        WHEN 'subspecies' THEN 13
        WHEN 'variety' THEN 14
        WHEN 'form' THEN 15
        ELSE 99
    END
"""


def _row_to_taxon(row: sqlite3.Row, vernaculars: list[Vernacular] | None = None) -> Taxon:
    return Taxon(
        id=row["id"],
        parent_id=row["parent_id"],
        rank=row["rank"],
        status=row["status"],
        scientific_name=row["scientific_name"],
        authorship=row["authorship"],
        path=row["path"],
        species_count=row["species_count"],
        coldp_id=row["coldp_id"],
        worms_id=row["worms_id"],
        freshwater_id=row["freshwater_id"],
        freshwater_parent_id=row["freshwater_parent_id"],
        is_extinct=bool(row["is_extinct"]),
        vernaculars=vernaculars or [],
    )


def _vernaculars_for(conn: sqlite3.Connection, taxon_id: int) -> list[Vernacular]:
    # DISTINCT on (name, language) to dedupe rows caused by the non-unique
    # coldp_id mapping (homonym textree taxa map to the same CoL concept).
    rows = conn.execute(
        "SELECT MIN(id) AS id, name, language, country FROM vernacular "
        "WHERE taxon_id = ? "
        "GROUP BY name, language, country "
        "ORDER BY language, country, name LIMIT 50",
        (taxon_id,),
    ).fetchall()
    return [Vernacular(id=r["id"], name=r["name"],
                       language=r["language"], country=r["country"])
            for r in rows]


@app.get("/api/health")
def health():
    """Liveness + DB stats + schema version.

    The schema version fields (db_schema_version / expected_schema_version)
    are how the frontend decides whether to show a "DB outdated" banner.
    A mismatch is logged as a warning but does NOT fail the request — the
    API still serves data (some columns may be missing on older DBs but
    the existing endpoints all guard against that). The recovery is
    `make etl && make coldp && make worms && make freshwater` (or any
    subset that bumps PRAGMA user_version past the expected value).
    """
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
        n_vern = conn.execute("SELECT COUNT(*) FROM vernacular").fetchone()[0]
        n_extinct = conn.execute("SELECT COUNT(*) FROM taxon WHERE is_extinct=1").fetchone()[0]
        try:
            n_dist = conn.execute("SELECT COUNT(*) FROM distribution").fetchone()[0]
        except sqlite3.OperationalError:
            n_dist = 0
        db_version = get_applied_version(conn)
    if db_version < CURRENT_SCHEMA_VERSION:
        _logger.warning(
            "DB schema version %d is older than expected %d; "
            "run `make etl && make coldp` to upgrade",
            db_version, CURRENT_SCHEMA_VERSION,
        )
    return {
        "status": "ok",
        "taxa": n,
        "vernaculars": n_vern,
        "extinct": n_extinct,
        "distribution": n_dist,
        "db": str(DB_PATH),
        "db_schema_version": db_version,
        "expected_schema_version": CURRENT_SCHEMA_VERSION,
        "schema_outdated": db_version < CURRENT_SCHEMA_VERSION,
    }
@app.get("/api/domains", response_model=list[Taxon])
def get_domains():
    """Top-level roots for the tree. Returns:
    - The 4 CoL domains (Archaea, Bacteria, Eukaryota, Viruses)
    - Biota (the WoRMS superdomain, only with worms_id=1)
    - Freshwater Fishes (the synthetic freshwater root, only when the
      freshwater loader has run; identified by freshwater_id=1 AND
      freshwater_parent_id IS NULL so it doesn't drag in CSV rows that
      also have parent_id=NULL).

    Other taxa with parent_id IS NULL (WoRMS-only orphans) are reachable
    only through the toggle's WoRMS view — they were re-parented under
    Biota in the enrichment step so they don't pollute the root list."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM taxon WHERE parent_id IS NULL "
            "AND (coldp_id IS NOT NULL OR worms_id = 1 "
            "     OR (freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL)) "
            "ORDER BY scientific_name"
        ).fetchall()
    return [_row_to_taxon(r) for r in rows]



@app.get("/api/taxon/{taxon_id}", response_model=Taxon)
def get_taxon(taxon_id: int):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM taxon WHERE id = ?", (taxon_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"taxon {taxon_id} not found")
        verns = _vernaculars_for(conn, taxon_id)
    return _row_to_taxon(row, verns)


@app.get("/api/taxon/{taxon_id}/synonyms", response_model=list[Synonym])
def get_synonyms(taxon_id: int, limit: int = Query(default=200, ge=1, le=1000)):
    """Names historically applied to this taxon. In ColDP/TextTree, a synonym
    row's parent_id points at the accepted name — so we look up rows where
    parent_id = {taxon_id} AND status != 'accepted'."""
    with db() as conn:
        rows = conn.execute(
            f"SELECT id, rank, scientific_name, authorship, status "
            f"FROM taxon WHERE parent_id = ? AND status != 'accepted' "
            f"ORDER BY rank, scientific_name LIMIT ?",
            (taxon_id, limit),
        ).fetchall()
    return [Synonym(
        id=r["id"], rank=r["rank"],
        scientific_name=r["scientific_name"],
        authorship=r["authorship"],
        status=r["status"],
    ) for r in rows]


@app.get("/api/taxon/{taxon_id}/distribution", response_model=list[DistributionEntry])
def get_distribution(
    taxon_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    only: Optional[str] = Query(default=None, max_length=20,
                                 description="Filter by establishment_means: 'native', 'introduced', 'uncertain'"),
):
    """Geographic range. Returns free-text area descriptions ('Argentina',
    'USA (Alabama, Colorado, ...)', 'South America')."""
    with db() as conn:
        if only:
            rows = conn.execute(
                f"SELECT id, area, gazetteer, establishment_means, degree_of_establishment "
                f"FROM distribution WHERE taxon_id = ? AND establishment_means = ? "
                f"ORDER BY area LIMIT ?",
                (taxon_id, only, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT id, area, gazetteer, establishment_means, degree_of_establishment "
                f"FROM distribution WHERE taxon_id = ? "
                f"ORDER BY establishment_means, area LIMIT ?",
                (taxon_id, limit),
            ).fetchall()
    return [DistributionEntry(
        id=r["id"], area=r["area"],
        gazetteer=r["gazetteer"],
        establishment_means=r["establishment_means"],
        degree_of_establishment=r["degree_of_establishment"],
    ) for r in rows]


@app.get("/api/taxon/{taxon_id}/vernaculars", response_model=list[Vernacular])
def get_vernaculars(
    taxon_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    language: Optional[str] = Query(default=None, max_length=8),
):
    with db() as conn:
        if language:
            rows = conn.execute(
                "SELECT MIN(id) AS id, name, language, country FROM vernacular "
                "WHERE taxon_id = ? AND language = ? "
                "GROUP BY name, language, country "
                "ORDER BY country, name LIMIT ?",
                (taxon_id, language, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT MIN(id) AS id, name, language, country FROM vernacular "
                "WHERE taxon_id = ? "
                "GROUP BY name, language, country "
                "ORDER BY language, country, name LIMIT ?",
                (taxon_id, limit),
            ).fetchall()
    return [Vernacular(id=r["id"], name=r["name"],
                       language=r["language"], country=r["country"])
            for r in rows]


@app.get("/api/taxon/{taxon_id}/children", response_model=list[Taxon])
def get_children(
    taxon_id: int,
    include_synonyms: bool = Query(default=False),
    source: str = Query(default="col", pattern="^(col|worms|freshwater)$"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Children of a taxon. By default uses CoL's `parent_id` (the global
    backbone). Pass `source=worms` to walk the WoRMS hierarchy via
    `worms_parent_id` so the WoRMS view can drill from Biota down through
    the marine tree (Animalia → Mollusca → ...) using WoRMS's own
    hierarchy, independent of the CoL backbone. Pass `source=freshwater`
    to walk the freshwater overlay (freshwater_parent_id); the freshwater
    rows are isolated, so the CoL/WoRMS branches return empty for a
    freshwater taxon and vice versa."""
    if source == "worms":
        where = "worms_parent_id = ? AND worms_id IS NOT NULL"
    elif source == "freshwater":
        where = "freshwater_parent_id = ? AND freshwater_id IS NOT NULL"
    else:
        where = "parent_id = ?"
        if not include_synonyms:
            where += " AND status = 'accepted'"
    params: list = [taxon_id]
    with db() as conn:
        rows = conn.execute(
            f"SELECT * FROM taxon WHERE {where} "
            f"ORDER BY {RANK_ORDER}, scientific_name LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    return [_row_to_taxon(r) for r in rows]


# ---------------------------------------------------------------------------
# Search-engine URL composition
#
# The server is the source of truth for the 14 pre-composed search URLs
# returned by /api/taxon/{id}/searches. The frontend has a parallel table
# in web/search_urls.js; tests/test_smoke.py::test_search_engine_contract
# (AC-21) enforces byte-identical key/label/with_authorship between the
# two. DO NOT REFORMAT this constant without updating the contract test.
#
# Each entry is a dict:
#   key              — stable id (e.g. "google"); used as SearchLink.engine
#   label            — display text (e.g. "Google"); used as SearchLink.label
#   template         — URL with {name} placeholder, used when authorship is
#                      not appended (most engines)
#   template_with_auth — URL with {name} and {auth} placeholders, used when
#                       the engine should append authorship (bhl, scholar).
#                       None for engines that don't take authorship.
#   with_authorship  — boolean; True iff the engine appends authorship
#   icon             — material-symbols-outlined glyph (UI rendering)
# ---------------------------------------------------------------------------
_SEARCH_ENGINES = [
    {"key": "google",       "label": "Google",        "template": "https://www.google.com/search?q={name}",                                                                          "template_with_auth": None,                                                     "with_authorship": False, "icon": "search"},
    {"key": "imagen",       "label": "Imágenes",      "template": "https://www.google.com/search?q={name}&tbm=isch",                                                               "template_with_auth": None,                                                     "with_authorship": False, "icon": "image"},
    {"key": "documentos",   "label": "Documentos",    "template": "https://www.google.com/search?q={name}+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29",           "template_with_auth": None,                                                     "with_authorship": False, "icon": "description"},
    {"key": "pdf",          "label": "PDF",           "template": "https://www.google.com/search?q={name}+filetype%3Apdf",                                                        "template_with_auth": None,                                                     "with_authorship": False, "icon": "picture_as_pdf"},
    {"key": "wikipedia",    "label": "Wikipedia",     "template": "https://en.wikipedia.org/wiki/Special:Search?search={name}",                                                  "template_with_auth": None,                                                     "with_authorship": False, "icon": "menu_book"},
    {"key": "bhl",          "label": "BHL",           "template": "https://www.biodiversitylibrary.org/search?searchTerm={name}",                                                "template_with_auth": "https://www.biodiversitylibrary.org/search?searchTerm={name}+{auth}", "with_authorship": True,  "icon": "library_books"},
    {"key": "researchgate", "label": "ResearchGate",  "template": "https://www.researchgate.net/search/publication?q={name}",                                                    "template_with_auth": None,                                                     "with_authorship": False, "icon": "science"},
    {"key": "plos",         "label": "PLOS",          "template": "https://journals.plos.org/plosone/search?query={name}",                                                       "template_with_auth": None,                                                     "with_authorship": False, "icon": "article"},
    {"key": "academia",     "label": "Academia.edu",  "template": "https://www.academia.edu/search?q={name}",                                                                    "template_with_auth": None,                                                     "with_authorship": False, "icon": "school"},
    {"key": "scielo",       "label": "Scielo",        "template": "https://search.scielo.org/?q={name}",                                                                         "template_with_auth": None,                                                     "with_authorship": False, "icon": "travel_explore"},
    {"key": "scholar",      "label": "Scholar",       "template": "https://scholar.google.com/scholar?q={name}",                                                                 "template_with_auth": "https://scholar.google.com/scholar?q={name}+{auth}",       "with_authorship": True,  "icon": "school"},
    {"key": "youtube",      "label": "YouTube",       "template": "https://www.youtube.com/results?search_query={name}",                                                         "template_with_auth": None,                                                     "with_authorship": False, "icon": "play_circle"},
    {"key": "zootaxa",      "label": "Zootaxa",       "template": "https://www.biotaxa.org/Zootaxa/search?query={name}",                                                         "template_with_auth": None,                                                     "with_authorship": False, "icon": "bug_report"},
    {"key": "scribd",       "label": "Scribd",        "template": "https://www.scribd.com/search?query={name}",                                                                  "template_with_auth": None,                                                     "with_authorship": False, "icon": "auto_stories"},
]


def _build_search(scientific_name: str, authorship: Optional[str]) -> list[SearchLink]:
    """Compose the 14 SearchLink entries for a single taxon.

    URLs are pre-formatted via urllib.parse.quote_plus (the server is the
    single source of truth for query encoding). The frontend never builds
    URLs from a template.
    """
    from urllib.parse import quote_plus
    name_q = quote_plus(scientific_name or "")
    auth_q = quote_plus(authorship) if authorship else ""
    out: list[SearchLink] = []
    for e in _SEARCH_ENGINES:
        tmpl_with_auth = e.get("template_with_auth")
        if e["with_authorship"] and auth_q and tmpl_with_auth:
            url = tmpl_with_auth.replace("{name}", name_q).replace("{auth}", auth_q)
        else:
            # Name-only template. Defensive: the template might still
            # contain a stray `{auth}` placeholder (it shouldn't), in
            # which case we drop it so the URL doesn't end with a
            # dangling `+` or `{auth}`.
            url = e["template"].replace("{name}", name_q).replace("{auth}", "")
        out.append(SearchLink(engine=e["key"], label=e["label"], url=url))
    return out


@app.get("/api/taxon/{taxon_id}/searches", response_model=list[SearchLink])
def get_searches(taxon_id: int):
    """14 pre-composed search-engine URLs for the taxon.

    Server is the source of truth for the URLs (urllib.parse.quote_plus);
    the frontend trusts the `url` field in each SearchLink and uses
    web/search_urls.js only for icon/label rendering when the response is
    unavailable (offline / 5xx fallback).

    Returns 422 when the taxon has no `scientific_name` — the composed
    URLs would all be empty queries (e.g. `?q=`), which is useless to
    the user; the server surfaces the bad data instead. AC-18.
    """
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
        if not row["scientific_name"]:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"taxon {taxon_id} has no scientific_name; "
                    "cannot compose search URLs"
                ),
            )
    return _build_search(row["scientific_name"], row["authorship"])


class SearchHit(BaseModel):
    """A search result, with the matched type so the UI can label it."""
    match_type: str  # "scientific" | "authorship" | "vernacular"
    taxon: Taxon


# Search ranking — BM25 with tier-based ordering.
#
# The naive approach (one FTS5 query per source, concat, sort by FTS rank)
# ranks species with many matching vernaculars above iconic species with few
# short ones. "Tiger" surfaces Scalidognathus tigerinus before Panthera
# tigris because FTS5 scores per-row, not per-taxon.
#
# Fix: classify each taxon into a tier from its vernacular hits:
#   tier 1 — has a vernacular whose name equals the query (case-insensitive)
#   tier 2 — has a vernacular whose name starts with the query
#   tier 3 — has a vernacular that matches only as substring (rare)
# Plus a sci_only bucket for taxa with no vernacular hit but a scientific hit.
#
# Inside each tier we score with BM25 (per vernacular row) × lang_boost and
# sum the top 3 hits per taxon. Tiers are concatenated in order — no global
# re-sort — so a tier-1 hit always beats a tier-2 hit regardless of raw score.
# Taxa whose scientific_name equals the query are promoted to the front
# (e.g. "Homo sapiens", "Quercus"); the previous LIKE-prefix variant was
# dropped because it flooded the top with Wolfkosia/Wolfina on "wolf".
_SEARCH_BOOST_LANGS = {"eng", "spa", "por", "fra", "deu"}


def _search_lang_boost(lang):
    if lang in _SEARCH_BOOST_LANGS:
        return 2.0
    # Many CoL vernaculars carry their language tag inline ("Apple (EN)")
    # and have language=NULL. Treat them as a moderate boost — likely
    # eng/spa but we don't pretend to know which.
    if not lang:
        return 1.5
    return 1.0


@app.get("/api/search", response_model=list[SearchHit])
def search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    include_vernacular: bool = Query(default=True),
):
    """
    Combined search across scientific_name, authorship, and vernacular names.

    Ranking is tier-based (BM25 inside each tier):
      tier 1 = exact vernacular match  →  tier 2 = prefix  →
      tier 3 = substring  →  sci_only.
    Exact scientific-name match is forced to #1.
    """
    raw = q.strip()
    pattern = raw if " " in raw or len(raw) > 8 else raw + "*"
    lq = raw.lower()

    with db() as conn:
        # ---- Tier 1/2/3: vernacular hits ---------------------------------
        # FTS5 orders by rowid by default, not by bm25. ORDER BY bm25 plus
        # generous overfetch is required so taxa with only a couple of short
        # exact-match vernaculars (e.g. Panthera tigris → "Tiger") don't fall
        # outside the scan window.
        vern_rows = []
        if include_vernacular:
            vern_overfetch = min(max(limit * 20, 500), 3000)
            vern_rows = conn.execute(
                "SELECT vfts.rowid AS vern_id, bm25(vernacular_fts) AS bm, "
                "       v.taxon_id, v.language, v.name AS vname "
                "FROM vernacular_fts vfts "
                "JOIN vernacular v ON v.id = vfts.rowid "
                "WHERE vernacular_fts MATCH ? "
                "ORDER BY bm25(vernacular_fts) "
                "LIMIT ?",
                (pattern, vern_overfetch),
            ).fetchall()

        # Bucket per taxon.
        by_taxon = {}
        for r in vern_rows:
            row_score = r["bm"] * _search_lang_boost(r["language"])
            by_taxon.setdefault(r["taxon_id"], []).append(
                (row_score, r["vname"], r["language"])
            )

        tier1 = []  # (taxon_id, compound_score)
        tier2 = []
        tier3 = []
        for tid, hits in by_taxon.items():
            has_exact = any(name.lower() == lq for _, name, _ in hits)
            has_prefix = any(name.lower().startswith(lq) for _, name, _ in hits)
            # Sum top-3 (captures "matches in multiple vernaculars" without
            # being skewed by taxa with 20+ weak prefix hits).
            top3 = sorted(hits)[:3]
            compound = sum(s for s, _, _ in top3)
            if has_exact:
                tier1.append((tid, compound))
            elif has_prefix:
                tier2.append((tid, compound))
            else:
                tier3.append((tid, compound))

        # Sort each tier by score (asc = more negative = better).
        tier1.sort(key=lambda x: x[1])
        tier2.sort(key=lambda x: x[1])
        tier3.sort(key=lambda x: x[1])

        # ---- Scientific hits (FTS5) ---------------------------------------
        sci_rows = conn.execute(
            "SELECT fts.rowid AS taxon_id, bm25(taxon_fts) AS bm, t.* "
            "FROM taxon_fts fts "
            "JOIN taxon t ON t.id = fts.rowid "
            "WHERE taxon_fts MATCH ? "
            "ORDER BY bm25(taxon_fts) "
            "LIMIT ?",
            (pattern, limit * 5),
        ).fetchall()
        sci_by_taxon = {}  # taxon_id → (bm, row)
        for r in sci_rows:
            tid = r["taxon_id"]
            bm = r["bm"]
            if tid not in sci_by_taxon or bm < sci_by_taxon[tid][0]:
                sci_by_taxon[tid] = (bm, r)

        # ---- Sci-exact: derived from sci_by_taxon (no extra SQL) -----------
        # The previous implementation ran `LOWER(scientific_name) = LOWER(?)`
        # as a separate query, but that scans all 5.4M rows (~1.5s). Since we
        # already loaded the top sci hits above, we filter those in Python.
        # This still catches the iconic cases ("Homo sapiens", "Quercus")
        # because their FTS5 bm25 score is the highest possible.
        sci_exact = {
            tid for tid, (_, row) in sci_by_taxon.items()
            if row["scientific_name"].lower() == lq
        }

        # ---- Helpers ------------------------------------------------------
        def _match_type(tid):
            # Authorship beats scientific when the pattern matches the
            # authorship field — matches the legacy UI behaviour where an
            # authorship hit shows a purple tag.
            if tid in sci_by_taxon:
                row = sci_by_taxon[tid][1]
                auth = row["authorship"]
                bare = pattern.rstrip("*").lower()
                if auth and bare and bare in auth.lower():
                    return "authorship"
                return "scientific"
            return "vernacular"

        def _hit(tid):
            if tid in sci_by_taxon:
                row = sci_by_taxon[tid][1]
            else:
                row = conn.execute(
                    "SELECT * FROM taxon WHERE id = ?", (tid,)
                ).fetchone()
                if row is None:
                    return None
            return SearchHit(match_type=_match_type(tid), taxon=_row_to_taxon(row))

        # ---- Build ordered list (tier1 + tier2 + tier3 + sci_only) -------
        seen = set()
        combined = []

        for tid, _ in tier1:
            h = _hit(tid)
            if h is not None:
                seen.add(tid)
                combined.append(h)
        for tid, _ in tier2:
            if tid in seen:
                continue
            h = _hit(tid)
            if h is not None:
                seen.add(tid)
                combined.append(h)
        for tid, _ in tier3:
            if tid in seen:
                continue
            h = _hit(tid)
            if h is not None:
                seen.add(tid)
                combined.append(h)

        # sci-only bucket (taxa with no vernacular hit, sorted by bm25 asc).
        sci_only = []
        for tid, (bm, row) in sci_by_taxon.items():
            if tid in seen:
                continue
            sci_only.append((tid, bm, SearchHit(
                match_type=_match_type(tid), taxon=_row_to_taxon(row))))
        sci_only.sort(key=lambda x: x[1])
        for _, _, hit in sci_only:
            seen.add(hit.taxon.id)
            combined.append(hit)

        # ---- Promote sci-exact to the front --------------------------------
        # Exact scientific-name match wins regardless of tier ordering.
        exact_hits = [h for h in combined if h.taxon.id in sci_exact]
        other_hits = [h for h in combined if h.taxon.id not in sci_exact]
        combined = exact_hits + other_hits

        # Apply limit AFTER tier concatenation — a tier-1 hit at position 25
        # must still appear.
        return combined[:limit]


# Mount the web/ directory for static assets (app.js, etc.).
# This is intentionally at the END of the file so /api/* routes take
# precedence over static file serving.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")