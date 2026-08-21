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
GET  /api/search?q=                                 → search across scientific name,
                                                       authorship AND vernacular

Run:
    uvicorn api.server:app --reload --port 8765
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "taxa.db"
WEB_DIR = Path(__file__).parent.parent / "web"


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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
    is_extinct: bool
    vernaculars: list[Vernacular] = []


RANK_ORDER = """
    CASE rank
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
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
        n_vern = conn.execute("SELECT COUNT(*) FROM vernacular").fetchone()[0]
        n_extinct = conn.execute("SELECT COUNT(*) FROM taxon WHERE is_extinct=1").fetchone()[0]
        try:
            n_dist = conn.execute("SELECT COUNT(*) FROM distribution").fetchone()[0]
        except sqlite3.OperationalError:
            n_dist = 0
    return {"status": "ok", "taxa": n, "vernaculars": n_vern,
            "extinct": n_extinct, "distribution": n_dist, "db": str(DB_PATH)}


@app.get("/api/domains", response_model=list[Taxon])
def get_domains():
    """Top-level roots for the tree. Returns:
    - The 4 CoL domains (Archaea, Bacteria, Eukaryota, Viruses)
    - Biota (the WoRMS superdomain, only with worms_id=1)

    Other taxa with parent_id IS NULL (WoRMS-only orphans) are reachable
    only through the toggle's WoRMS view — they were re-parented under
    Biota in the enrichment step so they don't pollute the root list."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM taxon WHERE parent_id IS NULL "
            "AND (coldp_id IS NOT NULL OR worms_id = 1) "
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
    source: str = Query(default="col", pattern="^(col|worms)$"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Children of a taxon. By default uses CoL's `parent_id` (the global
    backbone). Pass `source=worms` to walk the WoRMS hierarchy via
    `worms_parent_id` so the WoRMS view can drill from Biota down through
    the marine tree (Animalia → Mollusca → ...) using WoRMS's own
    hierarchy, independent of the CoL backbone."""
    if source == "worms":
        where = "worms_parent_id = ? AND worms_id IS NOT NULL"
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